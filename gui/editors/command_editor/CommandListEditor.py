from typing import Callable

from gui.ui.command_editor.CommandListWidget import CommandListEditorUI
from .CommandListModel import CommandListModel
from .ContextMenu import CommandListContextMenu
from .commands.CommandEditor import CommandEditor
from PySide6 import QtCore, QtWidgets


class CommandListEditor(CommandListEditorUI):
    def __init__(self, get_widget_function, command_parser, context_menu_structure,
                 on_command_selected: Callable = None,
                 on_command_saved: Callable = None,
                 on_cmd_list_changed: Callable = None):
        super().__init__()
        self.active_editor: [CommandEditor] = None
        self.get_widget_func = get_widget_function
        self.on_cmd_list_changed = on_cmd_list_changed
        self.command_model = CommandListModel(
            command_parser,
            on_cmd_list_changed
        )
        self.context_menu = CommandListContextMenu(
            context_menu_structure,
            self.on_update,
            self.command_model.layoutChanged.emit,
            self.clear_selection
        )
        self.on_command_selected = on_command_selected
        self.on_command_saved = on_command_saved

    def on_update(self):
        self.command_model.layoutChanged.emit()
        if self.on_cmd_list_changed:
            self.on_cmd_list_changed()

    def clear_selection(self):
        self.command_list.setCurrentIndex(QtCore.QModelIndex())

    def save(self):
        if isinstance(self.active_editor, CommandEditor):
            self.active_editor.save()

    def set_gds_and_data(self, gds, **kwargs):
        self.command_model.set_gds_and_data(gds, **kwargs)
        self.context_menu.set_gds_and_data(gds, **kwargs)
        self.command_list.setModel(self.command_model)

    def command_list_selection(self, selected: QtCore.QModelIndex):
        if self.active_editor is not None:
            self.active_editor: CommandEditor
            if isinstance(self.active_editor, CommandEditor):
                self.active_editor.save()
            if isinstance(self.active_editor, QtWidgets.QWidget):
                self.h_layout.removeWidget(self.active_editor)
                self.active_editor.deleteLater()
            self.active_editor = None

        if not selected.isValid():
            self.context_menu.hide_remove()
            return
        active_command = selected.data(QtCore.Qt.ItemDataRole.UserRole)

        if self.on_command_selected:
            self.on_command_selected(active_command)

        self.context_menu.show_remove(active_command)

        self.active_editor = self.get_widget_func(
            active_command,
            self.on_command_saved,
            **self.command_model.cmd_data
        )
        if isinstance(self.active_editor, QtWidgets.QWidget):
            self.h_layout.addWidget(self.active_editor, 1)

    def command_list_context_menu(self, point: QtCore.QPoint):
        self.context_menu.exec(self.command_list.mapToGlobal(point))

