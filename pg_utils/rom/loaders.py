import logging
import os

import k4pg
from formats import conf
from k4pg import Sprite
from k4pg.sprite.Sprite import Frame, Tag
import pygame as pg
from formats.filesystem import NintendoDSRom
from formats.graphics.ani import AniSprite, AniSubSprite
from formats.graphics.bg import BGImage
from formats.nftr import NFTR
import numpy as np
from utility.path import set_extension


class SpriteLoaderROM(k4pg.SpriteLoaderOS):
    def __init__(self, rom: NintendoDSRom, base_path_rom=None, base_path_os=None):
        super(SpriteLoaderROM, self).__init__(base_path_os=base_path_os)
        self._base_path_rom = base_path_rom
        self.rom = rom

    def load(self, path: str, sprite: Sprite, sprite_sheet=True, convert_alpha=False, do_copy=False):
        # sprite_sheet and convert_alpha are ignored
        if self._base_path_rom is not None:
            path = os.path.join(self._base_path_rom, path).replace("\\", "/")
        sprite_sheet = path.startswith("data_lt2/ani")
        path = path.replace("?", self.rom.lang)
        if path.endswith(".arj"):
            path = set_extension(path, ".arj")
        else:
            path = set_extension(path, ".arc")
        if path not in self.rom.filenames:
            logging.warning(f"Path {path} not found for loading sprite")
            super().load(path + ".png", sprite, sprite_sheet=sprite_sheet, convert_alpha=convert_alpha,
                         do_copy=do_copy)
            return
        frames = []
        tags = []
        vars_ = {}
        if sprite_sheet:
            if path.endswith(".arj"):
                ani_sprite = AniSubSprite(path, rom=self.rom)
            else:
                ani_sprite = AniSprite(path, rom=self.rom)
            w, h = 0, 0
            for img in ani_sprite.images:
                img_h, img_w = img.shape
                h = max(img_h, h)
                frames.append(Frame(w, 0, img_w, img_h))
                w += img_w
            surf = pg.Surface((w, h))
            for i, img in enumerate(ani_sprite.images):
                array_surf = ani_sprite.palette[img][:, :, :-1]
                array_surf = np.swapaxes(array_surf, 0, 1)
                img_surf = pg.surfarray.make_surface(array_surf)
                surf.blit(img_surf, frames[i].position)

            for animation in ani_sprite.animations:
                durations = [f.duration / 60.0 for f in animation.frames]
                if len(durations) != 0:
                    if animation.frames[-1].next_frame_index != 0:
                        durations[-1] = 0  # don't loop animation
                tags.append(Tag(
                    animation.name,
                    [f.image_index for f in animation.frames],
                    durations,
                    child_x=animation.child_image_x,
                    child_y=animation.child_image_y,
                    child_index=animation.child_image_animation_index
                ))

            vars_.update(ani_sprite.variables)
            vars_["child_image"] = ani_sprite.child_image
            color_key = pg.Color(0, 255, 0)
        else:
            bg_sprite = BGImage(path, rom=self.rom)
            img_array = bg_sprite.palette_rgb[bg_sprite.image][:, :, :-1]
            img_array = np.swapaxes(img_array, 0, 1)
            surf = pg.surfarray.make_surface(img_array)
            color_key = None
        sprite.load_sprite(self, surf, frames, tags, vars_=vars_)
        sprite.color_key = color_key


class FontLoaderROM(k4pg.FontLoaderOS):
    def __init__(self, rom, *args, base_path_rom=None, **kwargs):
        super(FontLoaderROM, self).__init__(*args, **kwargs)
        self.rom = rom
        self.base_path_rom = base_path_rom

    def load(self, path: str, size: int, text: k4pg.FontSupportive):
        rom_path = path
        if self.base_path_rom is not None:
            rom_path = os.path.join(self.base_path_rom, path).replace("\\", "/")
        rom_path = rom_path.replace("?", self.rom.lang)
        rom_path = set_extension(rom_path, ".NFTR")
        if rom_path not in self.rom.filenames:
            super().load(path, size, text)
            return

        nftr_file = NFTR(filename=rom_path, rom=self.rom)
        tile_count = len(nftr_file.char_glyph.tile_bitmaps)
        tileset_width = (min(16, tile_count)) * nftr_file.char_glyph.tile_width
        tileset_height = ((tile_count + 15) // 16) * nftr_file.char_glyph.tile_height
        tileset = pg.Surface((tileset_width, tileset_height))
        tileset.fill((255, 255, 255))
        tile_w, tile_h = nftr_file.char_glyph.tile_width, nftr_file.char_glyph.tile_height

        palette = np.array([[255, 255, 255], [0, 0, 0]])

        for i in range(tile_count):
            tile_array: np.ndarray = palette[nftr_file.char_glyph.tile_bitmaps[i]]
            tile_array = tile_array.swapaxes(0, 1)
            tile_surf = pg.surfarray.make_surface(tile_array)
            tile_x = i % 16
            tile_y = i // 16
            tileset.blit(tile_surf, (tile_x*tile_w, tile_y*tile_h))

        current_color = pg.Color(0, 0, 0)
        mask_color = pg.Color(255, 255, 255)
        encoding = nftr_file.get_encoding_str()

        char_map = {}

        width = nftr_file.char_width.width
        left_spacing = nftr_file.char_width.left_spacing
        total_width = nftr_file.char_width.total_width
        for cmap_chunk in nftr_file.char_maps:
            for char, tile in cmap_chunk.char_map.items():
                # WHY
                total_width_ = total_width[tile]
                if width[tile] == 1:
                    total_width_ -= 1

                char_map[char] = k4pg.CharMap(
                    tile,
                    width[tile],
                    left_spacing[tile],
                    total_width_
                )

        color_commands = {
            "r": pg.Color(255, 0, 0),
            "x": pg.Color(0, 0, 0),
            "w": pg.Color(255, 255, 255),
            "g": pg.Color(0, 255, 0)
        }

        text.set_font(k4pg.FontMap(
            tileset, 16, encoding, char_map,
            current_color, mask_color, tile_w, tile_h,
            0, 1, color_commands
        ))
