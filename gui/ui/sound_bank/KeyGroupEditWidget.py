from PySide6 import QtCore, QtWidgets, QtGui
from formats.sound.sound_types import KeyGroup


class KeyGroupEditWidgetUI(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(KeyGroupEditWidgetUI, self).__init__(*args, **kwargs)
        self.key_group: [KeyGroup] = None

        self.form_layout = QtWidgets.QFormLayout()
        self.setLayout(self.form_layout)

        self.polyphony = QtWidgets.QSpinBox()
        self.polyphony.setRange(0, 255)
        self.form_layout.addRow("Polyphony", self.polyphony)

        self.priority = QtWidgets.QSpinBox()
        self.priority.setRange(0, 255)
        self.form_layout.addRow("Priority", self.priority)

        self.voice_channel_low = QtWidgets.QSpinBox()
        self.voice_channel_low.setRange(0, 255)
        self.form_layout.addRow("Voice channel low", self.voice_channel_low)

        self.voice_channel_high = QtWidgets.QSpinBox()
        self.voice_channel_high.setRange(0, 255)
        self.form_layout.addRow("Voice channel high", self.voice_channel_high)

    def set_key_group(self, key_group: KeyGroup):
        self.key_group = key_group

        self.polyphony.setValue(self.key_group.polyphony)
        self.priority.setValue(self.key_group.priority)
        self.voice_channel_low.setValue(self.key_group.voice_channel_low)
        self.voice_channel_high.setValue(self.key_group.voice_channel_high)
