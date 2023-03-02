import logging

from gui.ui.event.EventWidget import EventWidgetUI
from formats.event import Event
from formats_parsed.gds_parsers.EventGDSParser import EventGDSParser
from formats_parsed.dcc import DCCParser
from formats_parsed.EventScript import EventScript

from previewers.event.EventPlayer import EventPlayer

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gui.MainEditor import MainEditor


from .EventPropertiesWidget import EventPropertiesWidget
from PySide6 import QtCore, QtWidgets
from gui.editor_categories.Events import EventCategory, EventNode
from .CommandListModel import CommandListModel
from .command import get_command_widget
from .command.CommandEditor import CommandEditor


class EventEditor(EventWidgetUI):
    def __init__(self, main_editor):
        super(EventEditor, self).__init__()
        self.event = None
        self.event_node: QtCore.QModelIndex = None
        self.command_model = CommandListModel()
        self.active_editor: [CommandEditor] = None
        self.main_editor: MainEditor = main_editor

    def tab_changed(self, current: int):
        if current != 1:
            self.command_list.clearSelection()

    def get_event_properties_widget(self):
        return EventPropertiesWidget(self)

    def set_event(self, ev: Event, ev_index: QtCore.QModelIndex):
        self.event = ev
        self.event_node = ev_index
        self.character_widget.set_event(ev)

        self.command_model.set_event(self.event)
        self.command_list.setModel(self.command_model)

        dcc_parser = DCCParser()
        EventGDSParser(ev).serialize_into_dcc(ev.gds, dcc_parser)
        serialized = dcc_parser.serialize()
        self.text_editor.setPlainText(serialized)

    def preview_click(self):
        if isinstance(self.active_editor, CommandEditor):
            self.active_editor.save()
        self.main_editor.pg_previewer.start_renderer(EventPlayer(self.event))

    def save_click(self):
        if isinstance(self.active_editor, CommandEditor):
            self.active_editor.save()
        self.event.save_to_rom()
        self.reload_category_preview()
        self.main_editor.pg_previewer.start_renderer(EventPlayer(self.event))

    def preview_dcc_btn_click(self):
        text = self.text_editor.toPlainText()
        dcc_parser = DCCParser()
        dcc_parser.parse(text)
        is_ok, error = EventGDSParser(self.event).parse_from_dcc(self.event.gds, dcc_parser)
        if is_ok:
            self.main_editor.pg_previewer.start_renderer(EventPlayer(self.event))
        else:
            logging.error(f"Error compiling DCC: {error}")

    def save_dcc_btn_click(self):
        text = self.text_editor.toPlainText()
        dcc_parser = DCCParser()
        dcc_parser.parse(text)
        is_ok, error = EventGDSParser(self.event).parse_from_dcc(self.event.gds, dcc_parser)
        if is_ok:
            self.event.save_to_rom()
            self.reload_category_preview()
            self.main_editor.pg_previewer.start_renderer(EventPlayer(self.event))
        else:
            logging.error(f"Error compiling DCC: {error}")

    def reload_category_preview(self):
        event_node: EventNode = self.event_node.internalPointer()
        category: EventCategory = event_node.category
        category.load_event_names()
        self.main_editor.tree_model.dataChanged.emit(self.event_node, self.event_node)

    def command_list_selection(self, selected: QtCore.QModelIndex):
        if self.active_editor is not None:
            self.active_editor: CommandEditor
            self.active_editor.save()
            if isinstance(self.active_editor, QtWidgets.QWidget):
                self.script_layout.removeWidget(self.active_editor)
                self.active_editor.deleteLater()
            self.active_editor = None

        if not selected.isValid():
            return

        self.active_editor = get_command_widget(selected.data(QtCore.Qt.ItemDataRole.UserRole), self.event)
        if isinstance(self.active_editor, QtWidgets.QWidget):
            self.script_layout.addWidget(self.active_editor, 1)
