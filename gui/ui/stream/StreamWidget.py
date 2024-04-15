from PySide6 import QtCore, QtWidgets
from formats.sound.sadl import Coding


class StreamWidgetUI(QtWidgets.QWidget):

    # TODO: Loop
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.form_layout = QtWidgets.QFormLayout()
        self.form_layout.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.form_layout.setContentsMargins(100, 11, 100, 11)
        self.setLayout(self.form_layout)

        self.form_layout.addWidget(
            QtWidgets.QLabel("Importing")
        )

        self.file_layout = QtWidgets.QHBoxLayout()
        self.form_layout.addRow("Input file (WAV)", self.file_layout)

        self.import_file_name = QtWidgets.QLineEdit()
        self.import_file_name.setPlaceholderText("WAV file to encode...")
        self.file_layout.addWidget(self.import_file_name, 2)

        self.file_select_btn = QtWidgets.QPushButton("Choose File")
        self.file_select_btn.clicked.connect(self.import_open_clicked)
        self.file_layout.addWidget(self.file_select_btn, 1)

        self.encoding_combo_box = QtWidgets.QComboBox()
        self.encoding_combo_box.addItem("Ima Adpcm (Layton 1)", userData=Coding.INT_IMA)
        self.encoding_combo_box.addItem("Procyon (Layton 2)", userData=Coding.NDS_PROCYON)
        self.form_layout.addRow("Encoding", self.encoding_combo_box)

        self.import_btn = QtWidgets.QPushButton("Import")
        self.import_btn.clicked.connect(self.import_clicked)
        self.form_layout.addWidget(self.import_btn)

        self.form_layout.addWidget(
            QtWidgets.QLabel("Exporting")
        )

        self.file_export = QtWidgets.QHBoxLayout()
        self.form_layout.addRow("Output file (WAV)", self.file_export)

        self.export_file_name = QtWidgets.QLineEdit()
        self.export_file_name.setPlaceholderText("WAV file to output...")
        self.file_export.addWidget(self.export_file_name, 2)

        self.export_select_btn = QtWidgets.QPushButton("Choose File")
        self.export_select_btn.clicked.connect(self.export_open_clicked)
        self.file_export.addWidget(self.export_select_btn, 1)

        self.export_btn = QtWidgets.QPushButton("Export")
        self.export_btn.clicked.connect(self.export_clicked)
        self.form_layout.addWidget(self.export_btn)

    def import_open_clicked(self):
        pass

    def import_clicked(self):
        pass

    def export_open_clicked(self):
        pass

    def export_clicked(self):
        pass
