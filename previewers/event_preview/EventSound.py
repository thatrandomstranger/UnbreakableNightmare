from .abstracts.EventSoundAbstract import EventSoundAbstract
import pygame_utils.sound.SADLStreamPlayer
import pygame_utils.sound.SMDLStreamPlayer
from pygame_utils.rom.rom_extract import load_sadl, load_smd


class EventSound(EventSoundAbstract):
    def __init__(self):
        super().__init__()
        self.sadl_player = pygame_utils.sound.SADLStreamPlayer.SADLStreamPlayer()
        self.bg_player = pygame_utils.sound.SMDLStreamPlayer.SMDLStreamPlayer()
        self.loops = False

    def play_smdl(self, path, volume=0.5):
        smd_obj, presets = load_smd(path)
        self.bg_player.set_preset_dict(presets)
        self.bg_player.start_sound(smd_obj, volume=volume)

    def stop_smdl(self):
        self.bg_player.stop()

    def play_sadl(self, path, volume=0.5):
        sadl = load_sadl(path)
        self.sadl_player.start_sound(sadl, self.loops, volume=volume)

    def stop_sadl(self):
        self.sadl_player.stop()

    def update_(self):
        self.sadl_player.update_()
        self.bg_player.update_()
