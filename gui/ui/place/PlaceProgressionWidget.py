from PySide6 import QtCore, QtWidgets, QtGui
from formats.placeflag import PlaceFlagComparator


class PlaceProgressionWidgetUI(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.form_layout = QtWidgets.QFormLayout()
        self.setLayout(self.form_layout)

        self.range_layout = QtWidgets.QHBoxLayout()
        self.form_layout.addRow("Story Step Range", self.range_layout)

        self.lower_bound_spin = QtWidgets.QSpinBox()
        self.lower_bound_spin.setRange(0, 1000)
        self.range_layout.addWidget(self.lower_bound_spin)
        self.lower_bound_spin.valueChanged.connect(self.lower_range_edit)

        self.upper_bound_spin = QtWidgets.QSpinBox()
        self.upper_bound_spin.setRange(0, 1000)
        self.range_layout.addWidget(self.upper_bound_spin)
        self.upper_bound_spin.valueChanged.connect(self.upper_range_edit)

        self.place_flag_checkbox = QtWidgets.QCheckBox("Check place flag")
        self.form_layout.addRow(self.place_flag_checkbox)
        self.place_flag_checkbox.stateChanged.connect(self.place_flag_checkbox_edit)

        self.place_flag_layout = QtWidgets.QHBoxLayout()
        self.form_layout.addRow(self.place_flag_layout)

        self.place_flag_id_spin = QtWidgets.QSpinBox()
        self.place_flag_id_spin.setRange(0, 100)
        self.place_flag_layout.addWidget(self.place_flag_id_spin)
        self.place_flag_id_spin.valueChanged.connect(self.place_flag_id_spin_edit)

        self.place_flag_id_comparator = QtWidgets.QComboBox()
        self.place_flag_id_comparator.addItem(
            "==", userData=PlaceFlagComparator.EQUALS
        )
        self.place_flag_id_comparator.addItem(
            "!=", userData=PlaceFlagComparator.NOT_EQUALS
        )
        self.place_flag_id_comparator.addItem(
            ">=", userData=PlaceFlagComparator.GREATER_THAN_OR_EQUALS
        )
        self.place_flag_layout.addWidget(self.place_flag_id_comparator)
        self.place_flag_id_comparator.currentIndexChanged.connect(self.place_flag_id_comparator_edit)

        self.place_flag_value_spin = QtWidgets.QSpinBox()
        self.place_flag_value_spin.setRange(0, 100)
        self.place_flag_layout.addWidget(self.place_flag_value_spin)
        self.place_flag_value_spin.valueChanged.connect(self.place_flag_value_spin_edit)

        # TODO: Add behaviour to all changed.

    def lower_range_edit(self, state: int) -> None:
        pass

    def upper_range_edit(self, state: int) -> None:
        pass

    def place_flag_checkbox_edit(self, state: int) -> None:
        pass

    def place_flag_id_spin_edit(self, state: int) -> None:
        pass

    def place_flag_id_comparator_edit(self, state: int) -> None:
        pass

    def place_flag_value_spin_edit(self, state: int) -> None:
        pass
