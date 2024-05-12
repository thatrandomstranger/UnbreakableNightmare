import logging
from dataclasses import dataclass, field
from io import BytesIO
from math import floor, ceil, log
from typing import *
from typing import BinaryIO

import ndspy.color
import numpy as np
from PIL.ImageQt import ImageQt
from PySide6 import QtGui
from PIL import Image

from formats.binary import BinaryReader, BinaryWriter, SEEK_CUR
from formats.filesystem import FileFormat


# Calculate and write the sections
def get_nearest_power_of_2(x: int):
    """
    Gets the nearest power of 2 to x.

    Examples
    --------
    >>> get_nearest_power_of_2(10)
    8

    >>> get_nearest_power_of_2(324)
    256
    """
    possible_results = floor(log(x, 2)), ceil(log(x, 2))
    if x - 2 ** possible_results[1] < -7:
        return max(8, int(2 ** possible_results[0]))
    else:
        return max(8, int(2 ** possible_results[1]))


def calculate_power_of_2_steps(x: int):
    """
    Calculate how many powers of two are required to get to a number.

    Notes
    -----
    This method is equivalent to counting the number of 1s in the binary
    representation of the number.

    Examples
    --------
    >>> calculate_power_of_2_steps(142)
    4

    For 142, we need to add 2 + 4 + 8 + 128 = 142, so 4 steps.
    """
    ret = 0
    while x > 0:
        ret += 1
        x -= get_nearest_power_of_2(x)
    return ret


def generate_palette(images: List[Image.Image], maximum_color_count: int):
    """
    Generate the palette for a list of images, respecting a maximum number of colors.

    Parameters
    ----------
    images : List[Image.Image]
        List of Pillow images for which to generate the palette.
    maximum_color_count : int
        Number of allowed colors in total.

    Returns
    -------
    Tuple[np.ndarray, List[np.ndarray]]
        A tuple representing the palette and the images converted to the palette.

        The first element is the palette as an ndarray of shape (color_count, 4).
        The second element are the images as a list of ndarrays. The images are represented
        row-first, so they are accessed images[image_index][row][column].
    """
    comb_w = max([img.width for img in images])
    comb_h = sum([img.height for img in images])
    comb = Image.new("RGBA", (comb_w, comb_h))
    comb_y = 0
    for i in range(len(images)):
        comb.paste(images[i], (0, comb_y))
        comb_y += images[i].height
    comb = comb.convert("P", colors=(maximum_color_count - 1))
    colors = np.frombuffer(comb.palette.palette, np.uint8).reshape((-1, 4))
    indexes = np.asarray(comb, np.uint8)

    # add the regular transparent color
    colors = np.concatenate(([[0, 255, 0, 0]], colors[:(maximum_color_count - 1)]))
    indexes = indexes + 1  # we added our transparent color at the front of the palette
    for i, (*_, a) in enumerate(colors):
        if a < 128:
            indexes[indexes == i] = 0  # transparent color, change to the transparent type

    palette = np.zeros((len(colors), 4), np.uint8)
    palette[:len(colors)] = colors

    images_numpy = []

    comb_y = 0
    for i in range(len(images)):
        h, w = images[i].height, images[i].width
        image_numpy = indexes[comb_y:comb_y + h, :w]
        images_numpy.append(image_numpy)
        comb_y += h

    return palette, images_numpy


@dataclass
class AnimationFrame:
    """
    Dataclass representing a frame of an animation.
    """
    next_frame_index: int
    """Frame to play after this one."""
    duration: int
    """Duration of the frame in frames."""
    image_index: int
    """Index of the image which should play when this frame is active."""


@dataclass
class Animation:
    """
    Dataclass representing an animation.
    """
    name: str = "Create an Animation"
    """The name of the animation."""
    frames: List[AnimationFrame] = field(default_factory=list)
    """List of frames in this animation."""
    child_image_x: int = 0
    """Position of the child image in the X axis."""
    child_image_y: int = 0
    """Position of the child image in the Y axis."""
    child_image_animation_index: int = 0
    """Animation index that the child should play."""


class AniSprite(FileFormat):
    """
    Animation file on the Layton ROM.
    """
    color_depth: int = 8
    """Bits needed to represent a single color (8 or 4)."""
    images: List[np.ndarray] = []
    """
    Images contained in the file, as numpy arrays.

    Each image is represented row-first, so that they are accessed image[row][column].
    Therefore, each image is of shape (height, width).
    All entries on each image represent a color in the palette.
    """
    animations: List[Animation] = [Animation()]
    """List of animations contained in the file, as Animation objects."""
    variable_labels = [f"Var{i}" for i in range(16)]
    """List of 16 strings, each corresponding to the name of a variable."""
    variable_data = [[0] * 8 for i in range(16)]
    """List of the data contained in each variable. Each variable is a list of 8 integers."""
    palette: np.ndarray = np.zeros((256, 4), np.uint8)
    """
    Array of colors used in the images.
    
    Each color is RGBA, all colors having alpha 255 except color 0, which is
    transparent.
    
    TODO: Make it consistent with backgrounds (aka save palette as 5 bits).
    """
    child_image: str = ""
    """Path of the child image, with the ".ani" extension (TODO: check for AniSubSprite)."""

    _compressed_default = 2

    @property
    def variables(self):
        """
        Dictionary representation of variable_labels and variable_data.

        The dict returned by this function is read-only, although any modification made
        to the variable data will change the underlying data, because list objects
        share the same reference.
        """
        var_dict = {}
        for label, values in zip(self.variable_labels, self.variable_data):
            var_dict[label] = values
        return var_dict

    def read_stream(self, stream: BinaryIO):
        if isinstance(stream, BinaryReader):
            rdr = stream
        else:
            rdr = BinaryReader(stream)

        n_images = rdr.read_uint16()
        self.color_depth = 4 if rdr.read_uint16() == 3 else 8

        # import the images
        self.images = []
        for img_i in range(n_images):
            img_w = rdr.read_uint16()
            img_h = rdr.read_uint16()
            n_parts = rdr.read_uint16()

            img = np.zeros((img_h, img_w), np.uint8)

            rdr.seek(2, SEEK_CUR)
            for part_i in range(n_parts):
                part_x = rdr.read_uint16()
                part_y = rdr.read_uint16()
                part_w = 2 ** (3 + rdr.read_uint16())
                part_h = 2 ** (3 + rdr.read_uint16())

                part: np.ndarray
                if self.color_depth == 8:
                    part = np.frombuffer(rdr.read(part_h * part_w), np.uint8)
                    part = part.reshape((part_h, part_w))
                else:
                    bufpart = np.frombuffer(rdr.read(part_h * part_w // 2), np.uint8)
                    part = np.zeros((part_w * part_h), np.uint8)
                    part[0::2] = bufpart & 0xf
                    part[1::2] = bufpart >> 4
                    part = part.reshape((part_h, part_w))

                if (part_x + part_w) > img_w:
                    part_w = img_w - part_x
                if (part_y + part_h) > img_h:
                    part_h = img_h - part_y
                img[part_y:part_y + part_h, part_x:part_x + part_w] = part[:part_h, :part_w]

            self.images.append(img)

        palette_length = rdr.read_uint32()
        self.palette = np.zeros((palette_length, 4), np.uint8)
        for color_i in range(palette_length):
            self.palette[color_i] = ndspy.color.unpack255(rdr.read_uint16())
            if color_i:
                self.palette[color_i, 3] = 255

        rdr.seek(0x1E, SEEK_CUR)
        n_animations = rdr.read_uint32()
        animation_names = rdr.read_string_array(n_animations, 0x1e)
        animation_frame_sets = []
        for i in range(n_animations):
            n_frames = rdr.read_uint32()
            frame_indexes = rdr.read_uint32_array(n_frames)
            frame_durations = rdr.read_uint32_array(n_frames)
            image_indexes = rdr.read_uint32_array(n_frames)
            animation_frame_sets.append([
                AnimationFrame(next_frame_index=frame_indexes[i], duration=frame_durations[i],
                               image_index=image_indexes[i])
                for i in range(n_frames)])
        self.animations = [Animation(name=animation_names[i], frames=animation_frame_sets[i])
                           for i in range(n_animations)]

        if rdr.read_uint16() != 0x1234:
            return  # We hit end of stream

        self.variable_labels = rdr.read_string_array(16, 16)
        self.variable_data = [[] for _ in range(16)]
        for _ in range(8):
            for var_i in range(16):
                self.variable_data[var_i].append(rdr.read_int16())

        for anim in self.animations:
            anim.child_image_x = rdr.read_uint16()
        for anim in self.animations:
            anim.child_image_y = rdr.read_uint16()
        for anim in self.animations:
            anim.child_image_animation_index = rdr.read_uint8()

        self.child_image = rdr.read_string(128)

    def write_stream(self, stream):
        if isinstance(stream, BinaryWriter):
            wtr = stream
        else:
            wtr = BinaryWriter(stream)

        wtr.write_uint16(len(self.images))
        wtr.write_uint16(3 if self.color_depth == 4 else 4)

        for img in self.images:
            img_h, img_w = img.shape
            wtr.write_uint16(img_w)
            wtr.write_uint16(img_h)

            # number of parts
            wtr.write_uint16(calculate_power_of_2_steps(img_w) *
                             calculate_power_of_2_steps(img_h))
            wtr.write_zeros(2)

            w_left, h_left = img_w, img_h
            part_x, part_y = 0, 0
            while h_left > 0:
                part_h = get_nearest_power_of_2(h_left)
                good_h = part_h
                h_left -= part_h
                w_left = img_w
                part_x = 0
                while w_left > 0:
                    part_w = get_nearest_power_of_2(w_left)
                    w_left -= part_w
                    part_h = good_h

                    wtr.write_uint16(part_x)
                    wtr.write_uint16(part_y)
                    wtr.write_uint16(int(log(part_w, 2)) - 3)
                    wtr.write_uint16(int(log(part_h, 2)) - 3)

                    part = np.zeros((part_h, part_w), np.uint8)

                    if part_x + part_w > img_w:
                        part_w = img_w - part_x
                    if part_y + part_h > img_h:
                        part_h = img_h - part_y

                    part[:part_h, :part_w] = img[part_y:part_y + part_h, part_x:part_x + part_w]

                    if self.color_depth == 8:
                        wtr.write(part.tobytes())
                    else:
                        h, w = part.shape
                        bufpart = part.reshape((w * h))
                        part_4bit = np.zeros((h * w // 2), np.uint8)
                        part_4bit[:] = bufpart[0::2] & 0xf | bufpart[1::2] << 4
                        wtr.write(part_4bit.tobytes())

                    part_x += part_w
                part_y += part_h

        wtr.write_uint32(len(self.palette))
        for color_i in range(len(self.palette)):
            self.palette[color_i]: np.ndarray
            self.palette[color_i, 3] = 0
            wtr.write_uint16(ndspy.color.pack255(*self.palette[color_i]))
            if color_i:
                self.palette[color_i, 3] = 255

        wtr.write_zeros(0x1e)
        wtr.write_uint32(len(self.animations))

        for anim in self.animations:
            wtr.write_string(anim.name, 0x1e)
        for anim in self.animations:
            wtr.write_uint32(len(anim.frames))
            wtr.write_uint32_array([frame.next_frame_index for frame in anim.frames])
            wtr.write_uint32_array([frame.duration for frame in anim.frames])
            wtr.write_uint32_array([frame.image_index for frame in anim.frames])

        wtr.write_uint16(0x1234)  # magic number probably

        assert len(self.variable_labels) == 16
        wtr.write_string_array(self.variable_labels, 16)
        for dat_i in range(8):
            for var_l in self.variable_data:
                wtr.write_int16(var_l[dat_i])

        for anim in self.animations:
            wtr.write_uint16(anim.child_image_x)
        for anim in self.animations:
            wtr.write_uint16(anim.child_image_y)
        for anim in self.animations:
            wtr.write_uint8(anim.child_image_animation_index)

        wtr.write_string(self.child_image, 128)

        return stream

    def extract_image_pil(self, image_index: int) -> Image.Image:
        """
        Extract an image as a Pillow image.

        Parameters
        ----------
        image_index : int
            The index of the image to extract.

        Returns
        -------
        Image.Image
            The extracted Pillow image.
        """
        return Image.fromarray(self.palette[self.images[image_index]].astype(np.uint8), "RGBA")

    def extract_image_qt(self, image_index) -> QtGui.QPixmap:
        """
        Extracts an image as a QPixmap.

        Parameters
        ----------
        image_index : int
            The index of the image to extract.

        Returns
        -------
        QtGui.QPixmap
            The extracted QPixmap.
        """
        image = self.extract_image_pil(image_index)
        width, height = image.size
        image = image.resize((width * 2, height * 2), resample=Image.Resampling.NEAREST)
        qim = ImageQt(image)
        return QtGui.QPixmap.fromImage(qim)

    def rework_palette(self):
        """
        Creates the palette again for the images contained in the file.
        """
        logging.info(f"Animation {self._last_filename} reworking palette")
        images_pil = [self.extract_image_pil(i) for i in range(len(self.images))]
        color_count = 256 if self.color_depth == 8 else 16
        self.palette, self.images = generate_palette(images_pil, color_count)

    def replace_image_pil(self, image_index: int, image: Image.Image):
        """
        Replaces an image with a Pillow image, reworking the palette afterwards.

        Parameters
        ----------
        image_index : int
            Index of the image to replace.
        image : Image.Image
            Image with which to replace it.
        """
        logging.info(f"Animation {self._last_filename} replacing image at idx {image_index}")
        images_pil = [self.extract_image_pil(i) for i in range(len(self.images))]
        images_pil[image_index] = image
        color_count = 256 if self.color_depth == 8 else 16
        self.palette, self.images = generate_palette(images_pil, color_count)

    def bulk_import_images(self, images_pil: List[Image.Image]):
        """
        Imports a list of images, removing all current images in the process.

        Parameters
        ----------
        images_pil : List[Image.Image]
            List of all images.
        """
        logging.info(f"Animation {self._last_filename} bulk importing {len(images_pil)} images")
        color_count = 256 if self.color_depth == 8 else 16
        self.palette, self.images = generate_palette(images_pil, color_count)

    def append_image_pil(self, image: Image.Image):
        """
        Appends an image to the end of the image list.

        Parameters
        ----------
        image : Image.Image
            Pillow image to append.
        """
        logging.info(f"Animation {self._last_filename} appending image of size {image.size}")
        self.images.append(np.ndarray((0, 0), np.uint8))
        self.replace_image_pil(-1, image)

    def insert_image_pil(self, image_index: int, image: Image.Image):
        """
        Inserts the given image at image_index.

        Parameters
        ----------
        image_index : int
            Index at which to insert the image.
        image : Image.Image
            Image to insert.
        """
        logging.info(f"Animation {self._last_filename} inserting image of size {image.size} to idx {image_index}")
        self.images.insert(image_index, np.ndarray((0, 0), np.uint8))
        for anim in self.animations:
            for i, frame in enumerate(anim.frames):
                if frame.image_index >= image_index:
                    anim.frames[i].image_index += 1
        self.replace_image_pil(image_index, image)

    def remove_image(self, image_index: int):
        """
        Removes the image at the specified index.

        When removing an image, it also modifies all existing animations to remove
        this image from any frame.

        Parameters
        ----------
        image_index : int
            Index of the image to remove.
        """
        logging.info(f"Animation {self._last_filename} removing image of idx {image_index}")
        self.images.pop(image_index)

        for anim in self.animations:
            frames_to_remove = []
            for i, frame in enumerate(anim.frames):
                if frame.image_index == image_index:
                    frames_to_remove.append(frame)
                elif frame.image_index > image_index:
                    anim.frames[i].image_index -= 1
            for frame in frames_to_remove:
                anim.frames.remove(frame)
        self.rework_palette()  # Recreate palette


class AniSubSprite(AniSprite):
    """
    Animation file on the Layton ROM for images shown on the sub engine.

    For attributes look at base class (AniSprite).
    """

    def read_stream(self, stream: BinaryIO):
        rdr = stream if isinstance(stream, BinaryReader) else BinaryReader(stream)

        n_images = rdr.read_uint16()
        self.color_depth = 4 if rdr.read_uint16() == 3 else 8
        palette_length = rdr.read_uint32()

        # import the images
        self.images = []
        for img_i in range(n_images):
            img_w = rdr.read_uint16()
            img_h = rdr.read_uint16()
            n_parts = rdr.read_uint16()

            img = np.zeros((img_h, img_w), np.uint8)

            rdr.seek(2, SEEK_CUR)
            for part_i in range(n_parts):
                _part_glb_x = rdr.read_uint16()
                _part_glb_y = rdr.read_uint16()
                part_x = rdr.read_uint16()
                part_y = rdr.read_uint16()
                part_w = 2 ** (3 + rdr.read_uint16())
                part_h = 2 ** (3 + rdr.read_uint16())
                part: np.ndarray
                if self.color_depth == 8:
                    part = np.frombuffer(rdr.read(part_h * part_w), np.uint8)
                else:
                    bufpart = np.frombuffer(rdr.read(part_h * part_w // 2), np.uint8)
                    part = np.zeros((part_w * part_h), np.uint8)
                    part[0::2] = bufpart & 0xf
                    part[1::2] = bufpart >> 4
                    part = part.reshape((part_h, part_w))
                part.resize((part_h // 8, part_w // 8, 8, 8))
                part_w = min(img_w - part_x, part_w)
                part_h = min(img_h - part_y, part_h)
                for yt, yslice in enumerate(part):
                    for xt, xslice in enumerate(yslice):
                        offset_y = part_y + yt * 8
                        offset_x = part_x + xt * 8
                        end_y = min(part_y + yt * 8 + 8, part_y + part_h)
                        end_x = min(part_x + xt * 8 + 8, part_x + part_w)
                        copy_h = max(end_y - offset_y, 0)
                        copy_w = max(end_x - offset_x, 0)
                        img[offset_y:end_y,
                            offset_x:end_x] = \
                            xslice[:copy_h, :copy_w]

            self.images.append(img)

        self.palette = np.zeros((palette_length, 4), np.uint8)
        for color_i in range(palette_length):
            self.palette[color_i] = ndspy.color.unpack255(rdr.read_uint16())
            if color_i:
                self.palette[color_i, 3] = 255

        rdr.seek(0x1E, SEEK_CUR)
        n_animations = rdr.read_uint32()
        animation_names = rdr.read_string_array(n_animations, 0x1e)
        animation_frame_sets = []
        for i in range(n_animations):
            n_frames = rdr.read_uint32()
            frame_indexes = rdr.read_uint32_array(n_frames)
            frame_durations = rdr.read_uint32_array(n_frames)
            image_indexes = rdr.read_uint32_array(n_frames)
            animation_frame_sets.append([
                AnimationFrame(next_frame_index=frame_indexes[i], duration=frame_durations[i],
                               image_index=image_indexes[i])
                for i in range(n_frames)])
        self.animations = [Animation(name=animation_names[i], frames=animation_frame_sets[i])
                           for i in range(n_animations)]

        if rdr.read_uint16() != 0x1234:
            return  # We hit end of stream

        self.variable_labels = rdr.read_string_array(16, 16)
        self.variable_data = [[] for _ in range(16)]
        for _ in range(8):
            for var_i in range(16):
                self.variable_data[var_i].append(rdr.read_int16())

        for anim in self.animations:
            anim.child_image_x = rdr.read_int16()
        for anim in self.animations:
            anim.child_image_y = rdr.read_int16()
        for anim in self.animations:
            anim.child_spr_index = rdr.read_uint8()

        self.child_image = rdr.read_string(128)

    def write_stream(self, stream=None):
        wtr = stream if isinstance(stream, BinaryWriter) else BinaryWriter(stream)

        wtr.write_uint16(len(self.images))
        wtr.write_uint16(3 if self.color_depth == 4 else 4)
        wtr.write_uint32(len(self.palette))

        for img in self.images:
            # TODO: Maybe improve algorithm to use less parts

            img_h, img_w = img.shape
            wtr.write_uint16(img_w)
            wtr.write_uint16(img_h)

            count_position = wtr.tell()
            wtr.write_uint16(0)
            wtr.write_zeros(2)

            def get_flags(_part_w, _part_h):
                if _part_w == _part_h:
                    shape = 0
                    if _part_w == 8:
                        size_flag = 0
                    elif _part_w == 16:
                        size_flag = 1
                    elif _part_w == 32:
                        size_flag = 2
                    else:
                        size_flag = 3
                elif _part_w > _part_h:
                    shape = 1
                    if _part_w == 16:
                        size_flag = 0
                    elif _part_w == 32 and _part_h == 8:
                        size_flag = 1
                    elif _part_w == 32 and _part_h == 16:
                        size_flag = 2
                    else:
                        size_flag = 3
                else:
                    shape = 2
                    if _part_h == 16:
                        size_flag = 0
                    elif _part_h == 32 and _part_w == 8:
                        size_flag = 1
                    elif _part_h == 32 and _part_w == 16:
                        size_flag = 2
                    else:
                        size_flag = 3
                return shape << 14, size_flag << 14

            count = 0

            def add_part(_part_x, _part_y, _part_w, _part_h):
                nonlocal count
                shape_flag, size_flag = get_flags(_part_w, _part_h)
                wtr.write_uint16(shape_flag)
                wtr.write_uint16(size_flag)
                wtr.write_uint16(_part_x)
                wtr.write_uint16(_part_y)
                wtr.write_uint16(int(log(_part_w, 2)) - 3)
                wtr.write_uint16(int(log(_part_h, 2)) - 3)

                part = np.zeros((_part_h // 8, _part_w // 8, 8, 8), np.uint8)

                if _part_x + _part_w > img_w:
                    _part_w += img_w - _part_x - _part_w
                if _part_y + _part_h > img_h:
                    _part_h += img_h - _part_y - _part_h

                for yt, yslice in enumerate(part):
                    for xt, xslice in enumerate(yslice):
                        xslice[:_part_h - 8 * yt, :_part_w - 8 * xt] = \
                            img[_part_y + yt * 8:min(_part_y + yt * 8 + 8, _part_y + _part_h),
                                _part_x + xt * 8:min(_part_x + xt * 8 + 8, _part_x + _part_w)]

                if self.color_depth == 8:
                    wtr.write(part.tobytes())
                else:
                    _, hw = part.shape
                    part_4bit: np.ndarray = part[:hw // 2] << 4 | part[hw // 2:]
                    wtr.write(part_4bit.tobytes())
                count += 1

            w_left, h_left = img_w, img_h
            part_x, part_y = 0, 0
            while h_left > 0:
                part_h = min(get_nearest_power_of_2(h_left), 64)
                w_left = img_w
                part_x = 0
                while w_left > 0:
                    part_w = min(get_nearest_power_of_2(w_left), 64)

                    if part_w == 64 and part_h < 32:
                        add_part(part_x, part_y, 32, part_h)
                        add_part(part_x + 32, part_y, 32, part_h)
                    elif part_w < 32 and part_h == 64:
                        add_part(part_x, part_y, part_w, 32)
                        add_part(part_x, part_y + 32, part_w, 32)
                    else:
                        add_part(part_x, part_y, part_w, part_h)

                    part_x += part_w
                    w_left -= part_w
                part_y += part_h
                h_left -= part_h

            last_pos = wtr.tell()
            wtr.seek(count_position)
            wtr.write_uint16(count)
            wtr.seek(last_pos)

        for color_i in range(len(self.palette)):
            self.palette[color_i]: np.ndarray
            self.palette[color_i, 3] = 0
            wtr.write_uint16(ndspy.color.pack255(*self.palette[color_i]))
            if color_i:
                self.palette[color_i, 3] = 255

        wtr.write_zeros(0x1e)
        wtr.write_uint32(len(self.animations))

        for anim in self.animations:
            wtr.write_string(anim.name, 0x1e)
        for anim in self.animations:
            wtr.write_uint32(len(anim.frames))
            wtr.write_uint32_array([frame.next_frame_index for frame in anim.frames])
            wtr.write_uint32_array([frame.duration for frame in anim.frames])
            wtr.write_uint32_array([frame.image_index for frame in anim.frames])

        wtr.write_uint16(0x1234)  # magic number probably

        assert len(self.variable_labels) == 16
        wtr.write_string_array(self.variable_labels, 16)
        for dat_i in range(8):
            for var_l in self.variable_data:
                wtr.write_uint16(var_l[dat_i])

        for anim in self.animations:
            wtr.write_int16(anim.child_image_x)
        for anim in self.animations:
            wtr.write_int16(anim.child_image_y)
        for anim in self.animations:
            wtr.write_uint8(anim.child_image_animation_index)

        wtr.write_string(self.child_image, 128)

        return BinaryReader.data
