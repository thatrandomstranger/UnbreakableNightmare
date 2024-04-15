from PySide6 import QtCore, QtWidgets, QtGui

from formats.sound.sound_types import Program
from .LFOEditWidget import LFOEditWidgetUI
from .SplitEditWidget import SplitEditWidgetUI


class ProgramEditWidgetUI(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(ProgramEditWidgetUI, self).__init__(*args, **kwargs)
        self.program: [Program] = None

        self.form_layout = QtWidgets.QFormLayout()
        self.setLayout(self.form_layout)

        # TODO: Sliders instead of spinbox?
        self.volume = QtWidgets.QSpinBox()
        self.volume.setRange(0, 127)
        self.form_layout.addRow("Volume", self.volume)

        self.pan = QtWidgets.QSpinBox()
        self.pan.setRange(0, 127)
        self.form_layout.addRow("Pan", self.pan)

        self.lfo_v_layout = QtWidgets.QVBoxLayout()
        self.form_layout.addRow(self.lfo_v_layout)

        self.lfo_label = QtWidgets.QLabel("LFOs")
        self.lfo_v_layout.addWidget(self.lfo_label)

        self.lfo_h_layout = QtWidgets.QHBoxLayout()
        self.lfo_v_layout.addLayout(self.lfo_h_layout)

        self.lfo_list = QtWidgets.QListView()
        self.lfo_list.selectionChanged = self.lfo_list_selection_ui
        self.lfo_h_layout.addWidget(self.lfo_list, 1)

        self.lfo_edit = self.get_lfo_edit_widget()
        self.lfo_edit.hide()
        self.lfo_h_layout.addWidget(self.lfo_edit, 2)

        self.split_v_layout = QtWidgets.QVBoxLayout()
        self.form_layout.addRow(self.split_v_layout)

        self.split_label = QtWidgets.QLabel("Splits")
        self.split_v_layout.addWidget(self.split_label)

        self.split_h_layout = QtWidgets.QHBoxLayout()
        self.split_v_layout.addLayout(self.split_h_layout)

        self.split_list = QtWidgets.QListView()
        self.split_list.selectionChanged = self.split_list_selection_ui
        self.split_h_layout.addWidget(self.split_list, 1)

        self.split_edit = self.get_split_edit_widget()
        self.split_edit_scroll = QtWidgets.QScrollArea()
        self.split_edit_scroll.setWidget(self.split_edit)
        self.split_edit_scroll.setWidgetResizable(True)
        self.split_edit.hide()
        self.split_h_layout.addWidget(self.split_edit_scroll, 2)

    def set_program(self, program: Program):
        self.program = program

        self.volume.setValue(self.program.volume)
        self.pan.setValue(self.program.pan)

        self.lfo_list.setCurrentIndex(QtCore.QModelIndex())
        self.split_list.setCurrentIndex(QtCore.QModelIndex())

    def get_lfo_edit_widget(self):
        return LFOEditWidgetUI()

    def get_split_edit_widget(self):
        return SplitEditWidgetUI()

    def lfo_list_selection_ui(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection):
        QtWidgets.QListView.selectionChanged(self.lfo_list, selected, deselected)
        if selected.indexes():
            self.lfo_list_selection(selected.indexes()[0])
        else:
            self.lfo_list_selection(QtCore.QModelIndex())

    def lfo_list_selection(self, selected: QtCore.QModelIndex):
        pass

    def split_list_selection_ui(self, selected: QtCore.QItemSelection, deselected: QtCore.QItemSelection):
        QtWidgets.QListView.selectionChanged(self.split_list, selected, deselected)
        if selected.indexes():
            self.split_list_selection(selected.indexes()[0])
        else:
            self.split_list_selection(QtCore.QModelIndex())

    def split_list_selection(self, selected: QtCore.QModelIndex):
        pass
