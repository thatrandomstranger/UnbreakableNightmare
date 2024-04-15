from PySide6 import QtCore, QtWidgets, QtGui

from formats.sound.sound_types import Sample

import numpy as np
import pygame as pg
from formats.sound import sample_transform


class SampleEditWidgetUI(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(SampleEditWidgetUI, self).__init__(*args, **kwargs)
        self.sample: [Sample] = None

        self.form_layout = QtWidgets.QFormLayout()
        self.setLayout(self.form_layout)

        # TODO: Sliders instead of spinbox?
        self.fine_tune = QtWidgets.QSpinBox()
        self.fine_tune.setToolTip("Pitch fine tuning in cents.")
        self.fine_tune.setRange(-128, 127)
        self.form_layout.addRow("Fine Tune", self.fine_tune)

        self.coarse_tune = QtWidgets.QSpinBox()
        self.coarse_tune.setToolTip("Pitch coarse tuning in semitones (default -7)")
        self.coarse_tune.setRange(-128, 127)
        self.form_layout.addRow("Coarse Tune", self.coarse_tune)

        self.root_key = QtWidgets.QSpinBox()
        self.root_key.setRange(-128, 127)
        self.form_layout.addRow("Root Key", self.root_key)

        self.volume = QtWidgets.QSpinBox()
        self.volume.setRange(0, 127)
        self.form_layout.addRow("Volume", self.volume)

        self.pan = QtWidgets.QSpinBox()
        self.pan.setRange(0, 127)
        self.form_layout.addRow("Pan", self.pan)

        self.loop_enabled = QtWidgets.QCheckBox("Loop Enabled")
        self.form_layout.addRow(self.loop_enabled)

        # TODO: Sample format?

        self.sample_rate = QtWidgets.QSpinBox()
        self.sample_rate.setRange(0, 16_777_215)
        self.form_layout.addRow("Sample Rate", self.sample_rate)

        # TODO: Loop live preview?
        self.loop_beginning = QtWidgets.QSpinBox()
        self.loop_beginning.setRange(0, 16_777_215)
        self.form_layout.addRow("Loop Beginning", self.loop_beginning)

        self.loop_length = QtWidgets.QSpinBox()
        self.loop_length.setRange(0, 16_777_215)
        self.form_layout.addRow("Loop Length", self.loop_length)

        self.enable_envelope = QtWidgets.QCheckBox("Enable Envelope")
        self.form_layout.addRow(self.enable_envelope)

        self.attack_volume = QtWidgets.QSpinBox()
        self.attack_volume.setRange(0, 127)
        self.form_layout.addRow("Attack Volume", self.attack_volume)

        self.attack = QtWidgets.QSpinBox()
        self.attack.setRange(0, 127)
        self.form_layout.addRow("Attack", self.attack)

        self.decay = QtWidgets.QSpinBox()
        self.decay.setRange(0, 127)
        self.form_layout.addRow("Decay", self.decay)

        self.decay2 = QtWidgets.QSpinBox()
        self.decay2.setRange(0, 127)
        self.form_layout.addRow("Decay2", self.decay2)

        self.sustain = QtWidgets.QSpinBox()
        self.sustain.setRange(0, 127)
        self.form_layout.addRow("Sustain", self.sustain)

        self.hold = QtWidgets.QSpinBox()
        self.hold.setRange(0, 127)
        self.form_layout.addRow("Hold", self.hold)

        self.release = QtWidgets.QSpinBox()
        self.release.setRange(0, 127)
        self.form_layout.addRow("Release", self.release)

        self.button_layout = QtWidgets.QHBoxLayout()
        self.form_layout.addRow(self.button_layout)

        play_pixmap = QtWidgets.QStyle.StandardPixmap.SP_MediaPlay
        play_icon = self.style().standardIcon(play_pixmap)
        self.play_button = QtWidgets.QPushButton(play_icon, "Play")
        self.play_button.clicked.connect(self.play_click)
        self.button_layout.addWidget(self.play_button)

        self.import_button = QtWidgets.QPushButton("Import")
        self.button_layout.addWidget(self.import_button)

        self.export_button = QtWidgets.QPushButton("Export")
        self.button_layout.addWidget(self.export_button)

    def set_sample(self, sample: Sample):
        self.sample = sample
        self.play_button.setEnabled(not sample.empty())
        # self.import_button.setEnabled(not sample.empty())
        self.import_button.setEnabled(False)
        # self.export_button.setEnabled(not sample.empty())
        self.export_button.setEnabled(False)

        self.fine_tune.setValue(self.sample.fine_tune)
        self.coarse_tune.setValue(self.sample.coarse_tune)
        self.root_key.setValue(self.sample.root_key)
        self.volume.setValue(self.sample.volume)
        self.pan.setValue(self.sample.pan)
        self.loop_enabled.setChecked(self.sample.loop_enabled)
        self.sample_rate.setValue(self.sample.sample_rate)
        self.loop_beginning.setValue(self.sample.loop_beginning)
        self.loop_length.setValue(self.sample.loop_length)
        self.enable_envelope.setChecked(self.sample.envelope_on)
        self.attack_volume.setValue(self.sample.attack_volume)
        self.attack.setValue(self.sample.attack)
        self.decay.setValue(self.sample.decay)
        self.decay2.setValue(self.sample.decay2)
        self.sustain.setValue(self.sample.sustain)
        self.hold.setValue(self.sample.hold)
        self.release.setValue(self.sample.release)

    def play_click(self):
        sample = self.sample.pcm16
        sample_pcm = np.reshape(sample, (1, sample.shape[0]))
        target_rate = pg.mixer.get_init()[0]
        target_channels = pg.mixer.get_init()[2]
        sample_pcm = sample_transform.change_sample_rate(sample_pcm, self.sample.sample_rate, target_rate)
        sample_pcm = sample_transform.change_channels(sample_pcm, target_channels)
        sample_pcm = sample_pcm.swapaxes(0, 1)
        sample_pcm = np.ascontiguousarray(sample_pcm)
        sound = pg.sndarray.make_sound(sample_pcm)
        sound.set_volume(0.5)
        sound.play()
