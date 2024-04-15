from PySide6 import QtCore, QtWidgets, QtGui
from formats.puzzle import PuzzleType, Puzzle


class PuzzleTypeComboBox(QtWidgets.QComboBox):
    PUZZLE_TYPE_DICT = {
        PuzzleType.MULTIPLE_CHOICE: "Multiple Choice",
        PuzzleType.ON_OFF: "On/Off",
        PuzzleType.CIRCLE_ANSWER: "Circle Answer",
        PuzzleType.LINE_DIVIDE: "Line Divide",
        PuzzleType.LINE_DIVIDE_LIMITED: "Line Divide Limited",
        PuzzleType.DRAW_LINE_PLAZA: "Draw Line Plaza?",
        PuzzleType.SORT: "Sort",
        PuzzleType.WEATHER: "Weather?",
        PuzzleType.PILES_OF_PANCAKES: "Piles of Pancakes",
        PuzzleType.WRITE_CHARS: "Write Chars",
        PuzzleType.WRITE_NUM: "Write Numeric",
        PuzzleType.WRITE_ALT: "Write Alternative",
        PuzzleType.WRITE_DATE: "Write Date",
        PuzzleType.KNIGHT_TOUR: "Knight Tour",
        PuzzleType.TILE_ROTATE: "Tile Rotate",
        PuzzleType.TILE_ROTATE_2: "Tile Rotate 2",
        PuzzleType.AREA: "Area",
        PuzzleType.ROSES: "Roses",
        PuzzleType.SLIDE: "Slide",
        PuzzleType.SLIPPERY_CROSSINGS: "Slippery Crossings",
        PuzzleType.DISAPPEARING_ACT: "Disappearing Act",
        PuzzleType.JARS_AND_CANS: "Jars and Cans",
        PuzzleType.LIGHT_THE_WAY: "Light the Way",
        PuzzleType.RICKETY_BRIDGE: "Rickety Bridge",
        PuzzleType.FIND_SHAPE: "Find Shape",
        PuzzleType.PUZZLES_172_202: "Puzzles 172/202?",
        PuzzleType.PUZZLE_173: "Puzzles 173",

        PuzzleType.MATCHSTICK_UNUSED: "Matchstick (UNUSED)",
        PuzzleType.POSITION_TO_SOLVE_UNUSED: "Position to Solve (UNUSED)",
        PuzzleType.POSITION_TO_SOLVE_UNUSED2: "Position to Solve 2 (UNUSED)",
        PuzzleType.CONNECT_TO_ANSWER_UNUSED: "Connect to Answer (UNUSED)",
        PuzzleType.CUPS_UNUSED: "Cups (UNUSED)",
        PuzzleType.UNUSED_1: "UNUSED 1",
        PuzzleType.UNUSED_C: "UNUSED C",
        PuzzleType.UNUSED_E: "UNUSED E",
        PuzzleType.UNUSED_14: "UNUSED 14",
    }

    def __init__(self, *args, **kwargs):
        super(PuzzleTypeComboBox, self).__init__(*args, **kwargs)

        for type_id, name in self.PUZZLE_TYPE_DICT.items():
            self.addItem(name, type_id)

    def set_type(self, type_id: PuzzleType):
        self.setCurrentIndex(list(self.PUZZLE_TYPE_DICT.keys()).index(type_id))

    def get_type(self):
        return self.currentData()


class PuzzlePropertiesWidgetUI(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super(PuzzlePropertiesWidgetUI, self).__init__(*args, **kwargs)
        self.puzzle: Puzzle = None

        self.form_layout = QtWidgets.QFormLayout()

        self.number_spin = QtWidgets.QSpinBox(self)
        self.number_spin.setMaximum(65535)
        self.number_spin.valueChanged.connect(self.number_spin_edit)
        self.form_layout.addRow("Number", self.number_spin)

        self.title_input = QtWidgets.QLineEdit(self)
        self.title_input.textChanged.connect(self.title_input_edit)
        self.form_layout.addRow("Title", self.title_input)

        self.type_combo = PuzzleTypeComboBox(self)
        self.type_combo.currentIndexChanged.connect(self.type_combo_edit)
        self.form_layout.addRow("Type", self.type_combo)

        self.bg_btm_id_spin = QtWidgets.QSpinBox(self)
        self.bg_btm_id_spin.setMaximum(255)
        self.bg_btm_id_spin.valueChanged.connect(self.bg_btm_id_spin_edit)
        self.form_layout.addRow("Background Bottom ID", self.bg_btm_id_spin)

        self.bg_location_id_spin = QtWidgets.QSpinBox(self)
        self.bg_location_id_spin.setMaximum(255)
        self.bg_location_id_spin.valueChanged.connect(self.bg_location_id_spin_edit)
        self.form_layout.addRow("Background Location ID", self.bg_location_id_spin)

        self.location_id_spin = QtWidgets.QSpinBox(self)
        self.location_id_spin.setMaximum(255)
        self.location_id_spin.valueChanged.connect(self.location_id_spin_edit)
        self.form_layout.addRow("Location ID", self.location_id_spin)

        self.reward_id_spin = QtWidgets.QSpinBox(self)
        self.reward_id_spin.setMaximum(255)
        self.reward_id_spin.valueChanged.connect(self.reward_id_spin_edit)
        self.form_layout.addRow("Reward ID", self.reward_id_spin)

        self.tutorial_id_spin = QtWidgets.QSpinBox(self)
        self.tutorial_id_spin.setMaximum(255)
        self.tutorial_id_spin.valueChanged.connect(self.tutorial_id_spin_edit)
        self.form_layout.addRow("Tutorial ID", self.tutorial_id_spin)

        self.picarat_decay_layout = QtWidgets.QHBoxLayout()

        self.picarat_label = QtWidgets.QLabel("Picarat decay", self)
        self.picarat_decay_layout.addWidget(self.picarat_label)

        self.picarat_decay_spins = []
        for i in range(3):
            picarat_decay_spin = QtWidgets.QSpinBox(self)
            picarat_decay_spin.setMaximum(255)
            picarat_decay_spin.valueChanged.connect(lambda value, idx=i: self.picarat_decay_edit(idx, value))
            self.picarat_decay_layout.addWidget(picarat_decay_spin)
            self.picarat_decay_spins.append(picarat_decay_spin)

        self.form_layout.addRow(self.picarat_decay_layout)

        self.text_input = QtWidgets.QPlainTextEdit(self)
        self.text_input.textChanged.connect(self.text_input_edit)
        self.form_layout.addRow("Question", self.text_input)

        self.correct_input = QtWidgets.QPlainTextEdit(self)
        self.correct_input.textChanged.connect(self.correct_input_edit)
        self.form_layout.addRow("Correct Response", self.correct_input)

        self.incorrect_input = QtWidgets.QPlainTextEdit(self)
        self.incorrect_input.textChanged.connect(self.incorrect_input_edit)
        self.form_layout.addRow("Incorrect Response", self.incorrect_input)

        self.hint_1_input = QtWidgets.QPlainTextEdit(self)
        self.hint_1_input.textChanged.connect(self.hint_1_input_edit)
        self.form_layout.addRow("Hint 1", self.hint_1_input)

        self.hint_2_input = QtWidgets.QPlainTextEdit(self)
        self.hint_2_input.textChanged.connect(self.hint_2_input_edit)
        self.form_layout.addRow("Hint 2", self.hint_2_input)

        self.hint_3_input = QtWidgets.QPlainTextEdit(self)
        self.hint_3_input.textChanged.connect(self.hint_3_input_edit)
        self.form_layout.addRow("Hint 3", self.hint_3_input)

        self.bg_lang_checkbox = QtWidgets.QCheckBox("Background Language Dependant", self)
        self.bg_lang_checkbox.stateChanged.connect(self.bg_lang_checkbox_edit)
        self.form_layout.addRow(self.bg_lang_checkbox)

        self.has_answer_bg_checkbox = QtWidgets.QCheckBox("Has Answer Background", self)
        self.has_answer_bg_checkbox.stateChanged.connect(self.has_answer_bg_checkbox_edit)
        self.form_layout.addRow(self.has_answer_bg_checkbox)

        self.ans_bg_lang_checkbox = QtWidgets.QCheckBox("Answer Background Language Dependant", self)
        self.ans_bg_lang_checkbox.stateChanged.connect(self.ans_bg_lang_checkbox_edit)
        self.form_layout.addRow(self.ans_bg_lang_checkbox)

        self.flag_2_bit_checkbox = QtWidgets.QCheckBox("Flag 2 bit (Unknown)", self)
        self.flag_2_bit_checkbox.stateChanged.connect(self.flag_2_bit_checkbox_edit)
        self.form_layout.addRow(self.flag_2_bit_checkbox)

        # TODO: Judge character

        self.judge_character_input = QtWidgets.QSpinBox(self)
        self.judge_character_input.setMaximum(3)
        self.judge_character_input.valueChanged.connect(self.judge_character_input_edit)
        self.form_layout.addRow("Judge Character (DEBUG)", self.judge_character_input)

        self.unk0_input = QtWidgets.QSpinBox(self)
        self.unk0_input.setMaximum(65535)
        self.unk0_input.valueChanged.connect(self.unk0_edit)
        self.form_layout.addRow("Unk0", self.unk0_input)

        self.unk1_input = QtWidgets.QSpinBox(self)
        self.unk1_input.setMaximum(65535)
        self.unk1_input.valueChanged.connect(self.unk1_edit)
        self.form_layout.addRow("Unk1 (112?)", self.unk1_input)

        self.setLayout(self.form_layout)

    def set_puzzle_view(self, puzzle: Puzzle, is_advanced: bool):
        self.puzzle = puzzle
        self.number_spin.setValue(self.puzzle.number)
        self.title_input.setText(self.puzzle.title)
        self.type_combo.set_type(self.puzzle.type)
        self.bg_btm_id_spin.setValue(self.puzzle.bg_btm_id)
        self.bg_location_id_spin.setValue(self.puzzle.bg_location_id)
        self.location_id_spin.setValue(self.puzzle.location_id)
        self.reward_id_spin.setValue(self.puzzle.reward_id)
        self.tutorial_id_spin.setValue(self.puzzle.tutorial_id)
        for i in range(3):
            self.picarat_decay_spins[i].setValue(self.puzzle.picarat_decay[i])
        self.text_input.setPlainText(self.puzzle.text)
        self.correct_input.setPlainText(self.puzzle.correct_answer)
        self.incorrect_input.setPlainText(self.puzzle.incorrect_answer)
        self.hint_1_input.setPlainText(self.puzzle.hint1)
        self.hint_2_input.setPlainText(self.puzzle.hint2)
        self.hint_3_input.setPlainText(self.puzzle.hint3)
        self.bg_lang_checkbox.setChecked(self.puzzle.bg_lang)
        self.ans_bg_lang_checkbox.setChecked(self.puzzle.ans_bg_lang)
        self.has_answer_bg_checkbox.setChecked(self.puzzle.has_answer_bg)
        self.judge_character_input.setValue(self.puzzle.judge_char)
        self.ans_bg_lang_checkbox.setEnabled(self.puzzle.has_answer_bg)

        if is_advanced:
            self.flag_2_bit_checkbox.setChecked(self.puzzle.flag_bit2)
            self.unk0_input.setValue(self.puzzle.unk0)
            self.unk1_input.setValue(self.puzzle.unk1)

    def number_spin_edit(self, value: int):
        pass

    def title_input_edit(self, value: str):
        pass

    def type_combo_edit(self, _index: int):
        pass

    def bg_btm_id_spin_edit(self, value: int):
        pass

    def bg_location_id_spin_edit(self, value: int):
        pass

    def location_id_spin_edit(self, value: int):
        pass

    def reward_id_spin_edit(self, value: int):
        pass

    def tutorial_id_spin_edit(self, value: int):
        pass

    def picarat_decay_edit(self, idx: int, value: int):
        pass

    def bg_lang_checkbox_edit(self, state: int):
        pass

    def ans_bg_lang_checkbox_edit(self, state: int):
        pass

    def flag_2_bit_checkbox_edit(self, state: int):
        pass

    def has_answer_bg_checkbox_edit(self, state: int):
        pass

    def text_input_edit(self):
        pass

    def correct_input_edit(self):
        pass

    def incorrect_input_edit(self):
        pass

    def hint_1_input_edit(self):
        pass

    def hint_2_input_edit(self):
        pass

    def hint_3_input_edit(self):
        pass

    def judge_character_input_edit(self, value: int):
        pass

    def unk0_edit(self, value: int):
        pass

    def unk1_edit(self, value: int):
        pass

