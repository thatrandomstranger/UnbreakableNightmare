import logging
import os
from typing import Callable

from gui.ui.stream.StreamWidget import StreamWidgetUI
from formats.sound.sadl import SADL, Coding
from formats_parsed.sound.wav import WAV
from gui.SettingsManager import SettingsManager
from PySide6 import QtWidgets, QtCore
from typing import TYPE_CHECKING

from pg_utils.sound.SADLStreamPlayer import SADLStreamPlayer
from previewers import SoundPreview

if TYPE_CHECKING:
    from gui.MainEditor import MainEditor


class StreamEditor(StreamWidgetUI):
    def __init__(self, main_editor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_editor: MainEditor = main_editor
        self.sadl: [SADL] = None
        self.name = None

    def set_sadl(self, sad: SADL, name: str):
        self.sadl = sad
        self.name = name
        self.import_file_name.setText("")
        self.export_file_name.setText("")
        if self.sadl.coding == Coding.INT_IMA:
            self.encoding_combo_box.setCurrentIndex(0)
        elif self.sadl.coding == Coding.NDS_PROCYON:
            self.encoding_combo_box.setCurrentIndex(1)

    def import_open_clicked(self):
        import_path = SettingsManager().import_file(None, "Import WAV...", "WAV Files (*.wav)")
        self.import_file_name.setText(import_path)

    def export_open_clicked(self):
        filename = self.name + ".wav"
        export_path = SettingsManager().export_file(None, "Export WAV...", filename, "WAV Files (*.wav)")
        self.export_file_name.setText(export_path)

    def import_clicked(self):
        import_path = self.import_file_name.text()
        if import_path == "":
            return

        logging.info(f"Importing streamed {import_path} to {self.name} (coding {self.sadl.coding})")

        wav_file = WAV()
        try:
            with open(import_path, "rb") as wav_f:
                wav_file.read_stream(wav_f)
        except FileNotFoundError:
            logging.info(f"File {import_path} not found")
            QtWidgets.QMessageBox.warning(self, "File not found",
                                          f"File {import_path} wasn't found.",
                                          buttons=QtWidgets.QMessageBox.StandardButton.Ok)
            return

        progress_dialog = QtWidgets.QProgressDialog("Encoding WAV...", "Abort", 0, 100, None)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)

        def update_progress(value, maximum):
            progress_dialog.setMaximum(maximum)
            progress_dialog.setValue(value)
            return progress_dialog.wasCanceled()

        progress_dialog.setValue(0)
        self.sadl.coding = self.encoding_combo_box.currentData(QtCore.Qt.ItemDataRole.UserRole)
        if wav_file.to_sadl(self.sadl, progress_callback=update_progress):
            self.sadl.save()

        self.main_editor.pg_previewer.start_renderer(
            SoundPreview(SADLStreamPlayer(), self.sadl, self.name)
        )

        QtWidgets.QMessageBox.information(self, "WAV Imported",
                                          "WAV file was imported successfully",
                                          buttons=QtWidgets.QMessageBox.StandardButton.Ok)

    def export_clicked(self):
        export_path = self.export_file_name.text()
        if export_path == "":
            return

        logging.info(f"Exporting streamed {self.name} to {export_path} (coding {self.sadl.coding})")

        progress_dialog = QtWidgets.QProgressDialog("Decoding SADL...", "Abort", 0, 100, None)
        progress_dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)

        def update_progress(value, maximum):
            progress_dialog.setMaximum(maximum)
            progress_dialog.setValue(value)
            return progress_dialog.wasCanceled()

        with open(export_path, "wb") as export_file:
            wav_file, successful = WAV.from_sadl(self.sadl, progress_callback=update_progress)
            if not successful:
                return
            wav_file.write_stream(export_file)

        QtWidgets.QMessageBox.information(self, "WAV Exported",
                                          "WAV file was exported successfully",
                                          buttons=QtWidgets.QMessageBox.StandardButton.Ok)

