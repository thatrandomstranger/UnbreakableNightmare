from typing import Any

from pg_utils.TwoScreenRenderer import TwoScreenRenderer
import k4pg
from pg_utils.sound.StreamPlayerAbstract import StreamPlayerAbstract
from pg_utils.rom.RomSingleton import RomSingleton
import pygame as pg


class SoundPreview(TwoScreenRenderer):
    def __init__(self, player: StreamPlayerAbstract, snd_obj: Any, name: str):
        super(SoundPreview, self).__init__()

        self.sprite_loader = RomSingleton().get_sprite_loader()
        self.sprite_loader_os = k4pg.SpriteLoaderOS(base_path_os="data_permanent/sprites")
        self.font_loader = RomSingleton().get_font_loader()

        self.now_playing_text = k4pg.Text(position=pg.Vector2(0, -10),
                                          center=pg.Vector2(k4pg.Alignment.CENTER, k4pg.Alignment.BOTTOM))
        self.font_loader.load("font_event", 12, self.now_playing_text)
        self.now_playing_text.text = "Now playing:"

        self.track_name = k4pg.Text(position=pg.Vector2(0, 10),
                                    center=pg.Vector2(k4pg.Alignment.CENTER, k4pg.Alignment.TOP))
        self.font_loader.load("font_event", 12, self.track_name)
        self.track_name.text = name.replace("\\", "/").split("/")[-1]

        self.explanation_text = k4pg.Text(position=pg.Vector2(0, -50))
        self.font_loader.load("font_event", 12, self.explanation_text)
        self.explanation_text.text = "Touch the headphones to play"

        self.play_btn = k4pg.ButtonSprite(pressed_counter=0.09)
        self.sprite_loader_os.load("headphones_play.png", self.play_btn, sprite_sheet=True, convert_alpha=False)
        self.play_btn.color_key = pg.Color(0, 255, 0)

        self.volume_slider = k4pg.Slider(min_value=0, max_value=1, start_value=0.5)
        self.sprite_loader_os.load("slider_main.png", self.volume_slider, sprite_sheet=False)
        self.sprite_loader_os.load("slider_ball.png", self.volume_slider.child, sprite_sheet=False)
        self.volume_slider.center.update(k4pg.Alignment.CENTER, k4pg.Alignment.BOTTOM)
        self.volume_slider.position.y = 192 // 2 - 20

        self.player: StreamPlayerAbstract = player
        self.player.load_sound(snd_obj)
        self.player.set_volume(0.5**2)
        self.playing = False
        if self.check_playable():
            self.explanation_text.text = "Touch the headphones to play"
            self.play_btn.set_tag("OFF")
        else:
            self.explanation_text.text = "Missing dependencies"
            self.play_btn.set_tag("CAN'T BE PLAYED")

    def unload(self):
        super(SoundPreview, self).unload()
        self.player.stop()

    def check_playable(self):
        return self.player.get_playable()

    def toggle_sound(self):
        if not self.check_playable():
            return
        if self.playing:
            self.stop_sound()
        else:
            self.start_sound()

    def start_sound(self):
        self.play_btn.set_tag("ON")
        self.player.unpause()
        self.playing = True

    def stop_sound(self):
        self.play_btn.set_tag("OFF")
        self.player.pause()
        self.playing = False

    def update(self, dt: float):
        if self.play_btn.get_pressed(self.btm_camera):
            self.toggle_sound()
        self.play_btn.animate(dt)
        if self.playing:
            self.player.update(dt)
        super(SoundPreview, self).update(dt)

    def draw(self):
        self.top_camera.clear(pg.Color(40, 40, 40))
        self.btm_camera.clear(pg.Color(40, 40, 40))
        self.now_playing_text.draw(self.top_camera)
        self.track_name.draw(self.top_camera)
        self.play_btn.draw(self.btm_camera)
        self.explanation_text.draw(self.btm_camera)
        slider_value, changed = self.volume_slider.get_value(self.btm_camera)
        if changed:
            self.player.set_volume(slider_value**2)  # ^2 to smooth volume slider (0-1)
        self.volume_slider.draw(self.btm_camera)
        super(SoundPreview, self).draw()
