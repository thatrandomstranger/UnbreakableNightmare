import logging
from typing import BinaryIO

import PIL.Image

from formats.filesystem import FileFormat
from formats.binary import BinaryReader, BinaryWriter

from PIL import Image
from PIL.ImageQt import ImageQt
from PySide6 import QtGui
import numpy as np
import ndspy.color


class BGImage(FileFormat):
    """
    Background file on the Layton ROM.
    """
    image: np.ndarray = np.zeros((192, 256), np.uint8)
    """
    Array representing the image.

    The image is represented row-first, so that it's accessed image[row][column].
    All entries on the image represent a color in the palette.
    """
    palette: np.ndarray = np.zeros((256, 4), np.uint8)
    """
    Array of colors used in the image.

    Each color is RGBA, all colors having alpha 255 except color 0, which is
    transparent.
    """

    _compressed_default = 2
    
    def __init__(self, filename: str = None, **kwargs):
        self._compressed_default = 2
        if filename is not None:
            if filename.endswith(".arb"):
                self._compressed_default = 0
        super().__init__(filename=filename, **kwargs)

    def read_stream(self, stream: BinaryIO):
        if isinstance(stream, BinaryReader):
            rdr = stream
        else:
            rdr = BinaryReader(stream)
        rdr.seek(0)

        palette_length = rdr.read_uint32()
        self.palette = np.zeros((palette_length, 4), np.uint8)
        self.palette[1:, -1] = 1
        for color_i in range(palette_length):
            self.palette[color_i, :3] = ndspy.color.unpack(rdr.read_uint16())[:3]

        n_tiles = rdr.read_uint32()
        # Read tiles and assemble image
        tiles = np.frombuffer(rdr.read(n_tiles * 0x40), np.uint8).reshape((-1, 8, 8))

        map_w = rdr.read_uint16()
        map_h = rdr.read_uint16()

        img_w = map_w * 8
        img_h = map_h * 8

        self.image = np.zeros((img_h, img_w), np.uint8)

        for map_y in range(map_h):
            for map_x in range(map_w):
                img_y = map_y * 8
                img_x = map_x * 8

                self.image[img_y:img_y + 8, img_x:img_x + 8] = tiles[rdr.read_uint16()]

    def write_stream(self, stream):
        if isinstance(stream, BinaryWriter):
            wtr = stream
        else:
            wtr = BinaryWriter(stream)

        wtr.write_uint32(len(self.palette))
        for color in self.palette:
            color: np.ndarray
            wtr.write_uint16(ndspy.color.pack(color[0], color[1], color[2], a=0))

        img_h, img_w = self.image.shape
        map_h, map_w = img_h // 8, img_w // 8

        # Get all 8x8 unique tiles
        tiles = np.asarray([self.image[y * 8:y * 8 + 8, x * 8:x * 8 + 8] for y in range(map_h) for x in range(map_w)])
        unique_tiles, tile_map = np.unique(tiles, return_inverse=True, axis=0)
        wtr.write_uint32(len(unique_tiles))
        wtr.write(unique_tiles.tobytes())

        wtr.write_uint16(map_w)
        wtr.write_uint16(map_h)
        wtr.write(tile_map.astype(np.uint16).tobytes())

    def extract_image_qt(self) -> QtGui.QPixmap:
        """
        Extract image as a QPixmap.

        Returns
        -------
        QPixmap
            The image converted to a QPixmap.
        """
        image = self.extract_image_pil()
        width, height = image.size
        image = image.resize((width * 2, height * 2), resample=Image.Resampling.NEAREST)
        image.save("tests/test2.png")
        qim = ImageQt(image)
        return QtGui.QPixmap.fromImage(qim)

    def extract_image_pil(self) -> Image.Image:
        """
        Extract image as a Pillow image.

        Returns
        -------
        Image.Image
            The image converted to a Pillow image.
        """
        return Image.fromarray(self.palette_rgb[self.image].astype(np.uint8), "RGBA")

    def import_image_pil(self, image: Image.Image):
        """
        Import a Pillow image.

        Parameters
        ----------
        image : Image.Image
            The Pillow image to replace the current image.

        Notes
        -----
        This function also reworks the palette of the BGImage.
        """
        # Find out why palette breaks close to 256 colors (keeping at 200 colors for consistency w/ the game)
        # 199 colors + 1 transparent

        def convert_image_to_palette(img: Image.Image):
            _img = img.resize((256, 192)).convert("RGBA")
            _img_np = np.asarray(_img, dtype=np.uint16)  # 16 bits for color conversion overflow
            _img_np = np.copy(_img_np)  # Copy array for it to be writable
            _img_np = np.reshape(_img_np, (-1, 4))

            # Color conversion (check ndspy.contract function).
            _img_np[:, :3] = ((_img_np[:, :3] + 4) << 2) // 33
            _img_np[:, 3] = (_img_np[:, 3] > 127) * 1

            # Set transparent colors.
            _img_np[(_img_np == 0)[:, -1], :] = (0, 0b11111, 0, 0)

            # Create the palette and the image using the palette
            _palette, _img_palette = np.unique(_img_np, axis=0, return_inverse=True)
            _palette: np.ndarray
            # Add one because color 0 is reserved for transparency.
            _img_palette = np.reshape(_img_palette, (192, 256)) + 1

            # Remove the pure green transparent color (it's color 0 of the palette).
            if (_palette == np.asarray([0, 0b11111, 0, 0])).all(axis=1).any():
                _idx_transparent = np.where(np.all(_palette == [0, 0b11111, 0, 0], axis=1))[0][0]
                _palette = np.delete(_palette, _idx_transparent, axis=0)
                _img_palette[_img_palette == _idx_transparent + 1] = 0
                _img_palette[_img_palette > _idx_transparent + 1] -= 1

            # Add the transparent color back in.
            _palette = np.insert(_palette, 0, [0, 0b11111, 0, 0], axis=0)
            return _palette, _img_palette

        palette, img_palette = convert_image_to_palette(image)

        if len(palette) > 199:
            logging.warning("Must quantize image (maximum colors are 199 + 1 transparent)."
                            "This might distort the image. Any transparencies will be removed.")
            image = image.convert('RGB').quantize(199, method=Image.MAXCOVERAGE, dither=Image.Dither.NONE)
            palette, img_palette = convert_image_to_palette(image)

        logging.info(f"Replacing background {self._last_filename} with image of size {image.size} and palette of "
                     f"length {len(palette)}")

        self.image[:] = img_palette

        self.palette = np.zeros((len(palette), 4), np.uint8)
        self.palette[:] = palette[:]
        self.palette[1:, 3] = 1
        self.extract_image_pil().save("tests/test.png")

    @property
    def palette_rgb(self):
        palette = np.asarray([ndspy.color.expand(*c) for c in self.palette])
        palette[1:, 3] = 255
        palette[0, 3] = 0
        return palette
