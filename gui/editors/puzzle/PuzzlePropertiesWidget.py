from gui.ui.puzzle.PuzzlePropertiesWidget import PuzzlePropertiesWidgetUI
from formats.puzzle import Puzzle
from PySide6 import QtCore, QtWidgets, QtGui
from gui.SettingsManager import SettingsManager


class PuzzlePropertiesWidget(PuzzlePropertiesWidgetUI):
    def __init__(self, *args, **kwargs):
        super(PuzzlePropertiesWidget, self).__init__(*args, **kwargs)
        self.puzzle: Puzzle = None
        if not SettingsManager().advanced_mode:
            self.form_layout.removeRow(self.flag_2_bit_checkbox)
            self.form_layout.removeRow(self.unk0_input)
            self.form_layout.removeRow(self.unk1_input)

    def set_puzzle(self, puzzle: Puzzle):
        super().set_puzzle_view(puzzle, SettingsManager().advanced_mode)

    def number_spin_edit(self, value: int):
        self.puzzle.number = value

    def title_input_edit(self, value: str):
        self.puzzle.title = value

    def type_combo_edit(self, _index: int):
        self.puzzle.type = self.type_combo.get_type()

    def bg_btm_id_spin_edit(self, value: int):
        self.puzzle.bg_btm_id = value

    def bg_location_id_spin_edit(self, value: int):
        self.puzzle.bg_location_id = value

    def location_id_spin_edit(self, value: int):
        self.puzzle.location_id = value

    def reward_id_spin_edit(self, value: int):
        self.puzzle.reward_id = value

    def tutorial_id_spin_edit(self, value: int):
        self.puzzle.tutorial_id = value

    def picarat_decay_edit(self, idx: int, value: int):
        self.puzzle.picarat_decay[idx] = value

    def bg_lang_checkbox_edit(self, state: int):
        state = QtCore.Qt.CheckState(state)
        self.puzzle.bg_lang = state == QtCore.Qt.CheckState.Checked

    def ans_bg_lang_checkbox_edit(self, state: int):
        state = QtCore.Qt.CheckState(state)
        self.puzzle.ans_bg_lang = state == QtCore.Qt.CheckState.Checked

    def flag_2_bit_checkbox_edit(self, state: int):
        state = QtCore.Qt.CheckState(state)
        self.puzzle.flag_bit2 = state == QtCore.Qt.CheckState.Checked

    def has_answer_bg_checkbox_edit(self, state: int):
        state = QtCore.Qt.CheckState(state)
        self.puzzle.has_answer_bg = state == QtCore.Qt.CheckState.Checked
        self.ans_bg_lang_checkbox.setEnabled(self.puzzle.has_answer_bg)
        if not self.puzzle.has_answer_bg:
            self.ans_bg_lang_checkbox.setChecked(False)

    def text_input_edit(self):
        self.puzzle.text = self.text_input.toPlainText()

    def correct_input_edit(self):
        self.puzzle.correct_answer = self.correct_input.toPlainText()

    def incorrect_input_edit(self):
        self.puzzle.incorrect_answer = self.incorrect_input.toPlainText()

    def hint_1_input_edit(self):
        self.puzzle.hint1 = self.hint_1_input.toPlainText()

    def hint_2_input_edit(self):
        self.puzzle.hint2 = self.hint_2_input.toPlainText()

    def hint_3_input_edit(self):
        self.puzzle.hint3 = self.hint_3_input.toPlainText()

    def judge_character_input_edit(self, value: int):
        self.puzzle.judge_char = value

    def unk0_edit(self, value: int):
        self.puzzle.unk0 = value

    def unk1_edit(self, value: int):
        self.puzzle.unk1 = value
