import logging
import threading
from typing import List, Optional

import k4pg
import pygame as pg
from formats import gds
from formats.event import Event
from .EventCharacter import EventCharacter
from .EventBG import EventBG
from .EventSound import EventSound
from .EventWaiter import EventWaiter
from .EventDialogue import EventDialogue
from pg_utils.rom.RomSingleton import RomSingleton
from pg_utils.TwoScreenRenderer import TwoScreenRenderer


class EventPlayer(TwoScreenRenderer):
    def __init__(self, event: Event):
        super(EventPlayer, self).__init__()
        self.event = event
        self.current_command = 0
        self.next_voice = -1
        self.next_dialogue_sfx = -1

        self.sprite_loader = RomSingleton().get_sprite_loader()
        self.font_loader = RomSingleton().get_font_loader()

        self.top_bg = EventBG(self.sprite_loader, "top")
        self.btm_bg = EventBG(self.sprite_loader, "btm")

        self.waiter = EventWaiter()
        self.event_sound = EventSound()

        self.characters: List[Optional[EventCharacter]] = [None]*8
        self.initial_character_states = []

        for i in range(8):
            if self.event.characters[i] == 0:
                self.characters[i] = None
                continue
            char_id = self.event.characters[i]
            slot = self.event.characters_pos[i]
            anim = self.event.characters_anim_index[i]
            visibility = self.event.characters_shown[i]
            char = EventCharacter(char_id, slot, anim, visibility, self.sprite_loader)
            self.characters[i] = char
            self.initial_character_states.append(char.copy_state())

        self.dialogue = EventDialogue(self, position=pg.Vector2(0, 192//2 + 3),
                                      center=pg.Vector2(k4pg.Alignment.CENTER, k4pg.Alignment.BOTTOM))
        self.sprite_loader.load("data_lt2/ani/event/twindow.ani", self.dialogue, True)
        self.dialogue.init_text(self.font_loader)

        self.inp = k4pg.Input()

        self.reset_all(False)

        self.edit_command_i = None

        self.pushed_character_states = []
        self.pushed_top_bg_state = None
        self.pushed_btm_bg_state = None

        self.loading_lock = threading.Lock()

    def reset_all(self, instant: bool):
        self.current_command = 0
        self.next_voice = -1
        self.next_dialogue_sfx = -1

        self.top_bg.load_background(f"data_lt2/bg/map/main{self.event.map_bottom_id}.arc", instant)
        self.top_bg.fade(2, None, True, False)
        self.top_bg.set_tint((0, 0, 0, 0), instant)

        self.btm_bg.load_background(f"data_lt2/bg/map/main{self.event.map_bottom_id}.arc", instant)
        self.btm_bg.fade(2, None, True, False)
        self.btm_bg.set_tint((15, 5, 0, 120), instant)

        for i in range(8):
            if self.characters[i] is None:
                break
            self.characters[i].load_state(self.initial_character_states[i])
            print(self.initial_character_states[i])

        if self.dialogue.on_dialogue:
            self.dialogue.end()

    def enter_edit_mode(self, edit_command, force_reload: bool):
        self.loading_lock.acquire()

        if edit_command is None:
            self.edit_command_i = 0
        else:
            if self.edit_command_i is not None and not force_reload:
                if self.event.gds.commands[self.edit_command_i] is edit_command:
                    return
            self.edit_command_i = self.event.gds.commands.index(edit_command)

        if self.edit_command_i < self.current_command or force_reload:
            self.reset_all(True)
        else:
            if self.dialogue.on_dialogue:
                self.dialogue.end()

        while self.current_command < self.edit_command_i:
            command = self.event.gds.commands[self.current_command]
            self.execute_gds_command(command, True, True)
            self.current_command += 1

        self.pushed_character_states = []
        for character in self.characters:
            if character is None:
                break
            self.pushed_character_states.append(character.copy_state())

        self.pushed_top_bg_state = self.top_bg.copy_state()
        self.pushed_btm_bg_state = self.btm_bg.copy_state()

        self.top_bg.sync_state(True)
        self.btm_bg.sync_state(True)

        command = self.event.gds.commands[self.current_command]
        self.execute_gds_command(command, False, True)
        self.loading_lock.release()

    def command_has_changed(self):
        self.top_bg.load_state(self.pushed_top_bg_state, True)
        self.btm_bg.load_state(self.pushed_btm_bg_state, True)
        for i, char_state in enumerate(self.pushed_character_states):
            self.characters[i].load_state(char_state)

        self.current_command = self.edit_command_i
        command = self.event.gds.commands[self.current_command]
        self.execute_gds_command(command, False, True)

    def run_events_until_busy(self):
        while True:
            if self.current_command >= len(self.event.gds.commands):
                return
            command = self.event.gds.commands[self.current_command]
            self.current_command += 1

            self.execute_gds_command(command)

            if self.is_busy():
                break
        self.gm.tick()

    def execute_gds_command(self, command: gds.GDSCommand, instant=False, editing=False):
        fade_out = 1
        fade_in = 2
        if command.command == 0x2:
            self.top_bg.fade(fade_in, None, instant, editing)
            self.btm_bg.fade(fade_in, None, instant, editing)
        elif command.command == 0x3:
            self.top_bg.fade(fade_out, None, instant, editing)
            self.btm_bg.fade(fade_out, None, instant, editing)
        elif command.command == 0x4:
            if len(command.params) == 0:
                return
            dialogue_gds = self.event.get_text(command.params[0])
            if len(dialogue_gds.params) != 5:
                return
            character = None
            for char in self.characters:
                if char is None:
                    continue
                if char.get_char_id() == dialogue_gds.params[0]:
                    character = char
                    break
            self.dialogue.start_dialogue(character, dialogue_gds.params[1], dialogue_gds.params[4], self.next_voice,
                                         self.next_dialogue_sfx, self.sprite_loader)
            if instant:
                self.dialogue.end()
            self.next_voice = -1
            self.next_dialogue_sfx = -1
        elif command.command == 0x5:
            logging.info(f"[EventPlayer]    Setting room: {command.params[0]}")
        elif command.command == 0x6:
            logging.info(f"[EventPlayer]    Setting mode: {command.params[0]}")
        elif command.command == 0x7:
            logging.info(f"[EventPlayer]    Setting next mode: {command.params[0]}")
        elif command.command == 0x8:
            logging.info(f"[EventPlayer]    Setting movie: {command.params[0]}")
        elif command.command == 0x9:
            logging.info(f"[EventPlayer]    Setting event: {command.params[0]}")
        elif command.command == 0xb:
            logging.info(f"[EventPlayer]    Setting puzzle: {command.params[0]}")
        elif command.command == 0x21:
            bg_path = command.params[0]
            self.btm_bg.load_background(f"data_lt2/bg/{bg_path}", instant)
            self.btm_bg.set_tint((0, 0, 0, 0), instant)
        elif command.command == 0x22:
            bg_path = command.params[0]
            self.top_bg.load_background(f"data_lt2/bg/{bg_path}", instant)
            self.top_bg.set_tint((0, 0, 0, 0), instant)
        elif command.command == 0x2a:
            if 0 <= command.params[0] <= 7:
                if char := self.characters[command.params[0]]:
                    char.show()
        elif command.command == 0x2b:
            if 0 <= command.params[0] <= 7:
                if char := self.characters[command.params[0]]:
                    char.hide()
        elif command.command == 0x2c:
            # Still not clue about why it works like this
            if 0 <= command.params[0] <= 7:
                if char := self.characters[command.params[0]]:
                    char.set_opacity(command.params[1] > 0, instant)
        elif command.command == 0x2d:
            # show chapter
            pass
        elif command.command == 0x30:
            if 0 <= command.params[0] <= 7:
                if char := self.characters[command.params[0]]:
                    char.set_slot(command.params[1])
        elif command.command == 0x31:
            self.waiter.wait(command.params[0])
        elif command.command == 0x32:
            self.btm_bg.fade(fade_in, None, instant, editing)
        elif command.command == 0x33:
            self.btm_bg.fade(fade_out, None, instant, editing)
        elif command.command == 0x37:
            self.btm_bg.set_tint(tuple(command.params), instant)
        elif command.command == 0x3f:
            character = None
            for char in self.characters:
                if char is None:
                    continue
                if char.get_char_id() == command.params[0]:
                    character = char
                    break
            if character:
                character.set_anim(command.params[1])
        elif command.command == 0x5c:
            self.next_voice = command.params[0]
        elif command.command == 0x5d:
            self.event_sound.play_sadl(f"data_lt2/stream/ST_{str(command.params[0]).zfill(3)}.SAD")
        elif command.command == 0x5e:
            logging.info(f"[EventPlayer]    Playing SED sfx: {command.params[0]}")
        elif command.command == 0x62:
            self.event_sound.play_smdl(f"data_lt2/sound/BG_{str(command.params[0]).zfill(3)}.SMD", command.params[1])
        elif command.command == 0x69:
            self.waiter.do_wait_tap()
        elif command.command == 0x6a:
            self.btm_bg.shake()
        elif command.command == 0x6b:
            self.top_bg.shake()
        elif command.command == 0x6c:
            self.waiter.wait(command.params[0])
            self.waiter.do_wait_tap()
        elif command.command == 0x70:
            logging.info(f"[EventPlayer]    Unlocking diary entry: {command.params[0]}")
        elif command.command == 0x71:
            # Reveal mystery -> hides all character
            for char in self.characters:
                if char:
                    char.hide()
        elif command.command == 0x72:
            self.top_bg.fade(fade_out, command.params[0], instant, editing)
            self.btm_bg.fade(fade_out, command.params[0], instant, editing)
        elif command.command == 0x73:
            logging.info(f"[EventPlayer]    Starting tea hint: {command.params[0]} solution: {command.params[1]}")
        elif command.command == 0x7f:
            self.btm_bg.fade(fade_out, command.params[0], instant, editing)
        elif command.command == 0x80:
            self.top_bg.fade(fade_in, command.params[0], instant, editing)
            self.btm_bg.fade(fade_in, command.params[0], instant, editing)
        elif command.command == 0x81:
            self.btm_bg.fade(fade_in, command.params[0], instant, editing)
        elif command.command == 0x87:
            self.top_bg.fade(fade_out, command.params[0], instant, editing)
        elif command.command == 0x88:
            self.top_bg.fade(fade_in, command.params[0], instant, editing)
        elif command.command == 0x8a:
            self.event_sound.fade(False, command.params[1])
        elif command.command == 0x8b:
            self.event_sound.fade(True, command.params[0])
        elif command.command == 0x99:
            self.next_dialogue_sfx = command.params[0]
        else:
            logging.info(f"[EventPlayer]    Command {hex(command.command)} not recognised (skipped). ")

    def execute_str_command(self, command):
        logging.debug(f"[EventPlayer]    String command {command}")
        command_split = command.split(" ")
        if command_split[0] == "setani":
            try:
                int(command_split[1])
            except ValueError:
                return
            character = None
            for char in self.characters:
                if char is None:
                    continue
                char: EventCharacter
                if char.get_char_id() == int(command_split[1]):
                    character = char
                    break
            if character:
                character.set_anim(command_split[2].replace("_", " "))

    def update(self, dt: float):
        self.loading_lock.acquire()
        for character in self.characters:
            if character is not None:
                character.update_fade(dt)
        self.waiter.update_(dt)
        self.event_sound.update_(dt)
        self.top_bg.update_(dt)
        self.btm_bg.update_(dt)
        self.dialogue.interact(self.btm_camera, dt)
        for character in self.characters:
            if character:
                character.animate(dt)
        if not self.is_busy():
            self.run_events_until_busy()
        super(EventPlayer, self).update(dt)
        self.loading_lock.release()

    def draw(self):
        self.top_bg.draw_back(self.top_camera)
        self.top_bg.draw_front(self.top_camera)

        self.btm_bg.draw_back(self.btm_camera)
        for character in self.characters:
            if character:
                character.draw(self.btm_camera)
        self.dialogue.draw(self.btm_camera)
        self.btm_bg.draw_front(self.btm_camera)
        super(EventPlayer, self).draw()

    def unload(self):
        self.dialogue.unload()
        self.event_sound.stop_smdl()
        self.event_sound.stop_sadl()

    def is_busy(self):
        for character in self.characters:
            if character is not None:
                if character.busy():
                    return True
        return self.top_bg.busy() or self.btm_bg.busy() or self.waiter.busy() or self.dialogue.busy()
