from gui.ui.sound_bank.KeyGroupEditWidget import KeyGroupEditWidgetUI
from formats.sound.sound_types import KeyGroup


class KeyGroupEditor(KeyGroupEditWidgetUI):
    def __init__(self):
        super(KeyGroupEditor, self).__init__()

    def set_key_group(self, key_group: KeyGroup):
        super().set_key_group(key_group)
