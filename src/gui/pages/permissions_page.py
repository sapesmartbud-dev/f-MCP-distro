# SAPÉ f-MCP — controlled file system access with granular permissions for LLMs
# Copyright (C) 2026 Luciano Arrezze
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-only

"""Permissions management page."""

import json
import logging
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QDialog, QLineEdit, QCheckBox, QMessageBox,
    QFileDialog
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QTimer

from src.permissions import ACTIONS
from ..i18n import translate
from ..styles.sape_design_tokens import (
    LIGHT_TEXT_PRIMARY, DARK_TEXT_PRIMARY, LIGHT_TEXT_SECONDARY, DARK_TEXT_SECONDARY
)

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages persistent UI configuration (column widths, etc.) in ~/.sape/config.json"""

    def __init__(self):
        """Initialize config manager."""
        self.config_dir = Path.home() / ".sape"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_permissions_table_columns(self) -> dict:
        """Load saved column widths for permissions table.

        Returns:
            dict: Column index -> width (pixels), or empty dict if not found
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    columns = config.get('permissions_table_columns', {})
                    logger.debug(f"Loaded column widths: {columns}")
                    return columns
        except Exception as e:
            logger.warning(f"Error loading column widths: {e}")

        return {}

    def save_permissions_table_columns(self, columns: dict) -> None:
        """Save column widths for permissions table.

        Args:
            columns (dict): Column index -> width (pixels)
        """
        try:
            # Load existing config or create new one
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # Update column widths
            config['permissions_table_columns'] = columns

            # Write back to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved column widths: {columns}")
        except Exception as e:
            logger.error(f"Error saving column widths: {e}")


class NewRuleDialog(QDialog):
    """Dialog for creating/editing a permission rule.

    When editing an existing rule, pass existing_rule dict.
    When creating new, existing_rule is None.
    """

    def __init__(self, parent=None, language="en-US", existing_rule=None, theme="light"):
        super().__init__(parent)
        self.language = language
        self.existing_rule = existing_rule
        self.theme = theme

        # Set title based on new vs edit
        if existing_rule:
            self.setWindowTitle(translate("permissions.edit_rule_title", language))
        else:
            self.setWindowTitle(translate("permissions.new_rule_title", language))

        # Larger geometry to accommodate 10 actions in groups
        self.setGeometry(200, 150, 600, 650)
        self.path = None
        self.allow_subfolders = False
        self.actions = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Path input with Browse button
        layout.addWidget(QLabel(translate("permissions.new_rule_path_label", language)))
        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(translate("permissions.new_rule_path_placeholder", language))
        if existing_rule:
            self.path_input.setText(existing_rule['path'])
            self.path_input.setReadOnly(True)  # Prevent changing path on edit
        path_layout.addWidget(self.path_input)

        browse_btn = QPushButton(translate("permissions.new_rule_browse", language))
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self._on_browse_folder)
        browse_btn.setEnabled(not existing_rule)  # Disable browse when editing
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        # Allow subfolders checkbox
        self.subfolder_checkbox = QCheckBox(translate("permissions.new_rule_allow_subfolders", language))
        if existing_rule:
            self.subfolder_checkbox.setChecked(bool(existing_rule['allow_subfolders']))
        else:
            self.subfolder_checkbox.setChecked(True)
        layout.addWidget(self.subfolder_checkbox)

        # Actions checkboxes - organized by category
        layout.addWidget(QLabel(translate("permissions.new_rule_actions_label", language)))
        self.action_checkboxes = {}

        # Define action categories: action_name -> (category_label, tooltip)
        # Categories will be shown as grouped sections
        action_metadata = {
            "list": ("read", "permissions.action_list_tooltip"),
            "read": ("read", "permissions.action_read_tooltip"),
            "download": ("read", "permissions.action_download_tooltip"),
            "create": ("write", "permissions.action_create_tooltip"),
            "edit": ("write", "permissions.action_edit_tooltip"),
            "upload": ("write", "permissions.action_upload_tooltip"),
            "delete": ("write", "permissions.action_delete_tooltip"),
            "move": ("write", "permissions.action_move_tooltip"),
            "copy": ("write", "permissions.action_copy_tooltip"),
            "chmod": ("control", "permissions.action_chmod_tooltip"),
        }

        # Default to read-only for new rules (list, edit checked)
        readonly_actions = {"list", "edit"}

        # Group actions by category
        categories = {}
        for action in ACTIONS:
            category, tooltip_key = action_metadata.get(action, ("other", ""))
            if category not in categories:
                categories[category] = []
            categories[category].append((action, tooltip_key))

        # Render categories in order: read, write, control, other
        category_order = ["read", "write", "control", "other"]

        for category in category_order:
            if category not in categories:
                continue

            # Category header
            cat_label = QLabel(f"<b>{category.capitalize()} Operations</b>")
            text_color = DARK_TEXT_PRIMARY if self.theme == "dark" else LIGHT_TEXT_PRIMARY
            cat_label.setStyleSheet(f"color: {text_color.name()}; margin-top: 8px; margin-bottom: 6px;")
            layout.addWidget(cat_label)

            # 2-column grid for checkboxes in this category
            cat_grid = QGridLayout()
            cat_grid.setSpacing(8)
            cat_grid.setContentsMargins(16, 0, 0, 0)

            for col_idx, (action, tooltip_key) in enumerate(categories[category]):
                cb = QCheckBox(action.capitalize())

                # Set checked state: edit mode uses existing rule, new mode uses readonly_actions
                if existing_rule:
                    cb.setChecked(bool(existing_rule[f'can_{action}']))
                else:
                    cb.setChecked(action in readonly_actions)

                # Add tooltip if translation key exists
                if tooltip_key:
                    tooltip_text = translate(tooltip_key, language)
                    if tooltip_text != tooltip_key:  # Check if translation succeeded
                        cb.setToolTip(tooltip_text)

                self.action_checkboxes[action] = cb

                # Place in 2-column grid
                row = col_idx // 2
                col = col_idx % 2
                cat_grid.addWidget(cb, row, col)

            layout.addLayout(cat_grid)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton(translate("common.cancel", language))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        # Use different label for edit vs new
        btn_text = translate("permissions.edit_rule_grant", language) if existing_rule else translate("permissions.new_rule_grant", language)
        grant_btn = QPushButton(btn_text)
        grant_btn.clicked.connect(self._on_grant)
        grant_btn.setStyleSheet("background-color: #1C3FF0; color: white; font-weight: bold;")
        button_layout.addWidget(grant_btn)

        layout.addStretch()
        layout.addLayout(button_layout)

    def _on_browse_folder(self):
        """Open folder browser dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            ""
        )
        if folder:
            self.path_input.setText(folder)

    def _on_grant(self):
        """Validate and accept the dialog."""
        path = self.path_input.text().strip()
        if not path:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle(translate("permissions.validation_error_title", self.language))
            msg_box.setText(translate("permissions.validation_error_message", self.language))
            msg_box.addButton(translate("common.ok", self.language), QMessageBox.ButtonRole.AcceptRole)
            msg_box.exec()
            return

        self.path = path
        self.allow_subfolders = self.subfolder_checkbox.isChecked()
        self.actions = [action for action, cb in self.action_checkboxes.items() if cb.isChecked()]

        self.accept()


class PermissionsPage(QWidget):
    """Permission matrix editor."""

    def __init__(self, server, app=None):
        super().__init__()
        self.server = server
        self.app = app
        self.config_manager = ConfigManager()
        self._saving_widths = False  # Guard to prevent recursion during load
        self._save_timer = QTimer()  # Debounce timer for column resize
        self._save_timer.timeout.connect(self._save_column_widths)
        self._save_timer.setSingleShot(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Icon + Title (will be updated by language changes)
        self.title_container = QLabel()
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title_container.setFont(title_font)
        layout.addWidget(self.title_container)

        # Subtitle (will be updated by language changes)
        self.subtitle = QLabel()
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_font.setItalic(True)
        self.subtitle.setFont(subtitle_font)
        layout.addWidget(self.subtitle)

        # Content area (table + buttons)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Left panel: Rules table (1.5:1 ratio)
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(0, 0, 0, 0)
        left_panel.setSpacing(8)

        # Table (headers will be updated by language changes)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self._update_table_headers()
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        # Increase row height by 50% (from ~30px to ~45px for better readability)
        self.table.verticalHeader().setDefaultSectionSize(45)

        # Increase table height by 20% (set minimum height)
        self.table.setMinimumHeight(320)  # 20% increase from typical height

        # Connect column resize signal with debouncing
        self.table.horizontalHeader().sectionResized.connect(self._on_column_resized)

        left_panel.addWidget(self.table)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        content_layout.addWidget(left_widget, stretch=3)

        # Right panel: Action buttons
        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(0, 0, 0, 0)
        right_panel.setSpacing(8)

        self.new_rule_btn = QPushButton()
        self.new_rule_btn.setMinimumHeight(40)
        self.new_rule_btn.setStyleSheet("background-color: #1C3FF0; color: white; font-weight: bold;")
        self.new_rule_btn.clicked.connect(self._on_new_rule)
        right_panel.addWidget(self.new_rule_btn)

        self.refresh_btn = QPushButton()
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.clicked.connect(self._refresh_table)
        right_panel.addWidget(self.refresh_btn)

        self.help_btn = QPushButton()
        self.help_btn.setMinimumHeight(40)
        self.help_btn.clicked.connect(self._on_help)
        right_panel.addWidget(self.help_btn)

        right_panel.addStretch()

        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        right_widget.setMaximumWidth(120)
        content_layout.addWidget(right_widget, stretch=1)

        layout.addLayout(content_layout, 1)

        # Connect language and theme change signals
        if self.app:
            self.app.language_changed.connect(self._update_language)
            self.app.theme_manager.theme_changed.connect(self._update_theme)

        # Initial language and theme update
        self._update_language(self.app.current_language if self.app else "en-US")
        self._update_theme(self.app.current_theme if self.app else "light")

        # Load initial table
        self._refresh_table()

    def _refresh_table(self):
        """Load rules from database and populate table."""
        self.table.setRowCount(0)
        rules = self.server.permissions.rules()

        if not rules:
            # Show "No permissions" message
            language = self.app.current_language if self.app else "en-US"
            self.table.setRowCount(1)
            item = QTableWidgetItem(translate("permissions.no_rules", language))
            self.table.setItem(0, 0, item)
            # Still load column widths for consistency
            self._load_column_widths()
            return

        self.table.setRowCount(len(rules))

        for row_idx, rule in enumerate(rules):
            # Path column
            path_item = QTableWidgetItem(rule['path'])
            self.table.setItem(row_idx, 0, path_item)

            # Subfolders column
            subfolder_icon = "✓" if rule['allow_subfolders'] else "○"
            subfolder_item = QTableWidgetItem(subfolder_icon)
            subfolder_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 1, subfolder_item)

            # Actions column (count or list)
            allowed_actions = [a for a in ACTIONS if rule[f'can_{a}']]
            actions_text = f"{len(allowed_actions)}/{len(ACTIONS)}"
            actions_item = QTableWidgetItem(actions_text)
            actions_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, actions_item)

            # Created column
            created_item = QTableWidgetItem(rule['created_at'][:10])  # Date only
            self.table.setItem(row_idx, 3, created_item)

            # User column
            user_item = QTableWidgetItem(rule['user_created'])
            self.table.setItem(row_idx, 4, user_item)

            # Action column (edit and delete buttons)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(4)

            # Edit button
            edit_btn = QPushButton("✎")
            edit_btn.setMaximumWidth(36)
            edit_btn.setToolTip(translate("permissions.edit_button_tooltip", self.app.current_language if self.app else "en-US"))
            edit_btn.setStyleSheet("background-color: #1C3FF0; color: white;")
            edit_btn.clicked.connect(lambda checked, path=rule['path']: self._on_edit_rule(path))
            actions_layout.addWidget(edit_btn)

            # Delete button
            delete_btn = QPushButton("✕")
            delete_btn.setMaximumWidth(36)
            delete_btn.setToolTip(translate("permissions.delete_button_tooltip", self.app.current_language if self.app else "en-US"))
            delete_btn.setStyleSheet("background-color: #EF4444; color: white;")
            delete_btn.clicked.connect(lambda checked, path=rule['path']: self._on_delete_rule(path))
            actions_layout.addWidget(delete_btn)

            self.table.setCellWidget(row_idx, 5, actions_widget)

        # Resize columns to content, then apply saved widths if available
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(0, 250)  # Path column wider

        # Load and apply saved column widths
        self._load_column_widths()

    def _on_new_rule(self):
        """Open dialog to create new rule."""
        language = self.app.current_language if self.app else "en-US"
        theme = self.app.current_theme if self.app else "light"
        dialog = NewRuleDialog(self, language, existing_rule=None, theme=theme)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.server.permissions.grant(
                    dialog.path,
                    actions=dialog.actions,
                    allow_subfolders=dialog.allow_subfolders
                )
                logger.info(f"Permission granted for: {dialog.path}")
                self._refresh_table()
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle(translate("permissions.grant_success_title", language))
                msg_box.setText(f"{translate('permissions.grant_success_message', language)}\n{dialog.path}")
                msg_box.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
                msg_box.exec()
            except Exception as e:
                logger.error(f"Failed to grant permission: {e}")
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle(translate("permissions.grant_error_title", language))
                msg_box.setText(f"{translate('permissions.grant_error_message', language)}\n{str(e)}")
                msg_box.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
                msg_box.exec()

    def _on_edit_rule(self, path: str):
        """Open dialog to edit an existing rule."""
        language = self.app.current_language if self.app else "en-US"

        # Find the exact rule for this path (don't use rule_for which returns ancestors)
        rules = self.server.permissions.rules()
        existing_rule = None
        for rule in rules:
            if rule['path'] == path:
                existing_rule = rule
                break

        if not existing_rule:
            logger.error(f"Rule not found for editing: {path}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle(translate("permissions.edit_error_title", language))
            msg_box.setText(translate("permissions.edit_error_message", language))
            msg_box.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
            msg_box.exec()
            return

        theme = self.app.current_theme if self.app else "light"
        dialog = NewRuleDialog(self, language, existing_rule=existing_rule, theme=theme)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                # Grant with all checkbox states from dialog
                # Note: grant() REPLACES all actions, so we send the complete set of checked boxes
                self.server.permissions.grant(
                    dialog.path,
                    actions=dialog.actions,
                    allow_subfolders=dialog.allow_subfolders
                )
                logger.info(f"Permission updated for: {dialog.path}")
                self._refresh_table()
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle(translate("permissions.edit_success_title", language))
                msg_box.setText(f"{translate('permissions.edit_success_message', language)}\n{dialog.path}")
                msg_box.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
                msg_box.exec()
            except Exception as e:
                logger.error(f"Failed to update permission: {e}")
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle(translate("permissions.edit_error_title", language))
                msg_box.setText(f"{translate('permissions.edit_error_message', language)}\n{str(e)}")
                msg_box.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
                msg_box.exec()

    def _on_delete_rule(self, path: str):
        """Delete a permission rule."""
        language = self.app.current_language if self.app else "en-US"

        # Use explicit QMessageBox for confirmation
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle(translate("permissions.delete_confirm_title", language))
        msg_box.setText(f"{translate('permissions.delete_confirm_message', language)}\n{path}")
        yes_btn = msg_box.addButton(translate("common.yes", language), QMessageBox.ButtonRole.YesRole)
        msg_box.addButton(translate("common.no", language), QMessageBox.ButtonRole.NoRole)
        msg_box.exec()

        if msg_box.clickedButton() == yes_btn:
            try:
                self.server.permissions.revoke(path)
                logger.info(f"Permission revoked for: {path}")
                self._refresh_table()
                msg_box2 = QMessageBox(self)
                msg_box2.setIcon(QMessageBox.Icon.Information)
                msg_box2.setWindowTitle(translate("permissions.delete_success_title", language))
                msg_box2.setText(f"{translate('permissions.delete_success_message', language)}\n{path}")
                msg_box2.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
                msg_box2.exec()
            except Exception as e:
                logger.error(f"Failed to revoke permission: {e}")
                msg_box2 = QMessageBox(self)
                msg_box2.setIcon(QMessageBox.Icon.Critical)
                msg_box2.setWindowTitle(translate("permissions.delete_error_title", language))
                msg_box2.setText(f"{translate('permissions.delete_error_message', language)}\n{str(e)}")
                msg_box2.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
                msg_box2.exec()

    def _on_column_resized(self, logical_index: int, old_size: int, new_size: int):
        """Handle column resize event with debouncing."""
        # Debounce: restart timer to delay save until user stops resizing
        self._save_timer.stop()
        self._save_timer.start(300)  # 300ms debounce delay

    def _load_column_widths(self) -> None:
        """Load and apply saved column widths from config."""
        if self._saving_widths:
            return  # Guard against recursion

        self._saving_widths = True
        try:
            saved_widths = self.config_manager.load_permissions_table_columns()

            # Apply saved widths to table columns
            for col_idx, width in saved_widths.items():
                try:
                    col_idx = int(col_idx)  # Config stores as strings, convert back
                    if 0 <= col_idx < self.table.columnCount():
                        self.table.setColumnWidth(col_idx, width)
                except (ValueError, IndexError):
                    pass  # Skip invalid column indices

            logger.debug(f"Applied saved column widths: {saved_widths}")
        finally:
            self._saving_widths = False

    def _save_column_widths(self) -> None:
        """Save current column widths to config."""
        if self._saving_widths:
            return  # Guard against recursion

        self._saving_widths = True
        try:
            # Collect current column widths
            widths = {}
            for col_idx in range(self.table.columnCount()):
                width = self.table.columnWidth(col_idx)
                widths[str(col_idx)] = width  # Store as strings for JSON

            self.config_manager.save_permissions_table_columns(widths)
            logger.debug(f"Saved column widths: {widths}")
        finally:
            self._saving_widths = False

    def _on_help(self):
        """Show help dialog."""
        language = self.app.current_language if self.app else "en-US"
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setWindowTitle(translate("permissions.help_title", language))
        msg_box.setText(translate("permissions.help_text", language))
        msg_box.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
        msg_box.exec()

    def _update_table_headers(self):
        """Update table headers with translation keys."""
        language = self.app.current_language if self.app else "en-US"
        headers = [
            translate("permissions.table_header_path", language),
            translate("permissions.table_header_subfolders", language),
            translate("permissions.table_header_actions", language),
            translate("permissions.table_header_created", language),
            translate("permissions.table_header_user", language),
            translate("permissions.table_header_action", language),
        ]
        self.table.setHorizontalHeaderLabels(headers)

    def _update_language(self, language: str) -> None:
        """Update page text for the specified language."""
        self.title_container.setText(translate("permissions.title", language))
        self.subtitle.setText(translate("permissions.subtitle", language))
        self.new_rule_btn.setText(translate("permissions.new_rule_button", language))
        self.refresh_btn.setText(translate("permissions.refresh_button", language))
        self.help_btn.setText(translate("permissions.help_button", language))
        self._update_table_headers()

    def _update_theme(self, theme: str) -> None:
        """Update colors for the specified theme."""
        text_color = DARK_TEXT_SECONDARY if theme == "dark" else LIGHT_TEXT_SECONDARY
        self.subtitle.setStyleSheet(f"color: {text_color.name()};")

