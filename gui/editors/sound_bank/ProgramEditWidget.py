from gui.ui.sound_bank.ProgramEditWidget import ProgramEditWidgetUI
from formats.sound.sound_types import Program
from .LFOEditWidget import LFOEditor
from .SplitEditWidget import SplitEditor
from PySide6 import QtCore


class LFOModel(QtCore.QAbstractListModel):
    def __init__(self):
        super(LFOModel, self).__init__()
        self.program: [Program] = None

    def set_program(self, program: Program):
        self.layoutAboutToBeChanged.emit()
        self.program = program
        self.layoutChanged.emit()

    def rowCount(self, parent: QtCore.QModelIndex) -> int:
        return len(self.program.lfos)

    def data(self, index: QtCore.QModelIndex, role: int):
        if not index.isValid():
            return None
        if role == QtCore.Qt.ItemDataRole.UserRole:
            return self.program.lfos[index.row()]
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        return f"LFO {index.row()}"


class SplitModel(QtCore.QAbstractListModel):
    def __init__(self):
        super(SplitModel, self).__init__()
        self.program: [Program] = None

    def set_program(self, program: Program):
        self.layoutAboutToBeChanged.emit()
        self.program = program
        self.layoutChanged.emit()

    def rowCount(self, parent: QtCore.QModelIndex) -> int:
        return len(self.program.splits)

    def data(self, index: QtCore.QModelIndex, role: int):
        if not index.isValid():
            return None
        if role == QtCore.Qt.ItemDataRole.UserRole:
            return self.program.splits[index.row()]
        if role != QtCore.Qt.ItemDataRole.DisplayRole:
            return None
        return f"Split {index.row()}"


class ProgramEditor(ProgramEditWidgetUI):
    lfo_edit: LFOEditor
    split_edit: SplitEditor

    def __init__(self):
        super(ProgramEditor, self).__init__()
        self.program: [Program] = None

        self.lfo_model = LFOModel()
        self.split_model = SplitModel()

    def set_program(self, program: Program):
        super().set_program(program)

        self.lfo_model.set_program(program)
        self.split_model.set_program(program)

        self.lfo_list.setModel(self.lfo_model)
        self.split_list.setModel(self.split_model)

    def get_lfo_edit_widget(self):
        return LFOEditor()

    def get_split_edit_widget(self):
        return SplitEditor()

    def lfo_list_selection(self, selected: QtCore.QModelIndex):
        if not selected.isValid():
            self.lfo_edit.hide()
            return
        self.lfo_edit.show()
        self.lfo_edit.set_lfo(selected.data(QtCore.Qt.ItemDataRole.UserRole))

    def split_list_selection(self, selected: QtCore.QModelIndex):
        if not selected.isValid():
            self.split_edit.hide()
            self.split_edit_scroll.hide()
            return
        self.split_edit.show()
        self.split_edit.set_split(selected.data(QtCore.Qt.ItemDataRole.UserRole))
        self.split_edit_scroll.show()
