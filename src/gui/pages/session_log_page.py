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

"""Session log page."""

import logging
import csv
import json
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
    QFileDialog, QMessageBox
)
from PyQt6.QtGui import QFont, QTextCursor, QTextCharFormat, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer

from ..i18n import translate
from ..styles.sape_design_tokens import (
    LIGHT_TEXT_SECONDARY, DARK_TEXT_SECONDARY
)

logger = logging.getLogger(__name__)


class QPlainTextEditHandler(logging.Handler):
    """Custom logging handler that outputs to a QPlainTextEdit."""

    def __init__(self, text_edit):
        super().__init__()
        self.text_edit = text_edit
        self.max_lines = 1000

    def emit(self, record):
        """Emit a log record to the text edit."""
        try:
            message = self.format(record)
            self.text_edit.appendPlainText(message)

            # Limit to max_lines for performance
            doc = self.text_edit.document()
            if doc.blockCount() > self.max_lines:
                # Remove old lines
                cursor = self.text_edit.textCursor()
                cursor.movePosition(cursor.MoveOperation.Start)
                for _ in range(doc.blockCount() - self.max_lines):
                    cursor.select(cursor.SelectionType.BlockUnderCursor)
                    cursor.removeSelectedText()
        except Exception as e:
            self.handleError(record)


class SessionLogPage(QWidget):
    """Session log and activity monitoring."""

    # Signal emitted when a tool is called (for external logging)
    tool_called = pyqtSignal(str, dict, str)  # tool_name, params, result/error

    def __init__(self, server, app=None, session_id=None, log_store=None):
        super().__init__()
        self.server = server
        self.app = app
        self.session_id = session_id
        self.log_store = log_store

        # Track the highest log ID we've already displayed
        self._last_log_id = 0

        # Tool log polling timer (parent to self for proper cleanup)
        self.tool_log_timer = QTimer(self)
        self.tool_log_timer.timeout.connect(self._poll_tool_log)
        self.tool_log_timer.start(500)  # Poll every 500ms

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Icon + Title
        self.title_container = QLabel()
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title_container.setFont(title_font)
        layout.addWidget(self.title_container)

        # Subtitle
        self.subtitle = QLabel()
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_font.setItalic(True)
        self.subtitle.setFont(subtitle_font)
        layout.addWidget(self.subtitle)

        # Log display (QPlainTextEdit)
        self.log_display = QPlainTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Courier", 9))
        layout.addWidget(self.log_display, 1)

        # Setup custom logging handler
        self.log_handler = QPlainTextEditHandler(self.log_display)
        self.log_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', datefmt='%H:%M:%S'))

        # Register handler with root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        root_logger.setLevel(logging.INFO)

        logger.info("Session log initialized")

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        self.clear_btn = QPushButton()
        self.clear_btn.setMaximumWidth(100)
        self.clear_btn.clicked.connect(self._on_clear)
        button_layout.addWidget(self.clear_btn)

        self.export_btn = QPushButton()
        self.export_btn.setMaximumWidth(150)
        self.export_btn.clicked.connect(self._on_export)
        button_layout.addWidget(self.export_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Connect language and theme change signals
        if self.app:
            self.app.language_changed.connect(self._update_language)
            self.app.theme_manager.theme_changed.connect(self._update_theme)

        # Initial language and theme update
        self._update_language(self.app.current_language if self.app else "en-US")
        self._update_theme(self.app.current_theme if self.app else "light")

    def closeEvent(self, event):
        """Clean up timer when widget closes."""
        self.tool_log_timer.stop()
        event.accept()

    def _poll_tool_log(self):
        """Poll LogStore for new entries and display them.

        Displays logs from both the current GUI session and CLI sessions (Claude Desktop).
        """
        try:
            # Skip if LogStore is not available
            if not self.log_store or not self.session_id:
                return

            # Get logs from both current session and CLI sessions
            gui_logs = self.log_store.get_logs(self.session_id)
            cli_logs = self.log_store.get_logs("cli")
            logs = sorted(gui_logs + cli_logs, key=lambda x: x["id"])

            if not logs:
                return

            # Append only entries with id > _last_log_id
            appended_ids = []
            for entry in logs:
                if entry["id"] > self._last_log_id:
                    self._append_tool_log_entry(entry)
                    appended_ids.append(entry["id"])

            # Update _last_log_id to the highest ID we've seen
            if appended_ids:
                self._last_log_id = max(appended_ids)

        except Exception as e:
            logger.debug(f"Error polling tool log: {e}")

    def _append_tool_log_entry(self, entry: dict):
        """Format and append a tool log entry to the display.

        Args:
            entry: Dict with keys from LogStore: timestamp, tool_name, params_json, result, error
        """
        try:
            # Extract fields
            timestamp = entry.get('timestamp', '')
            tool_name = entry.get('tool_name', 'unknown')
            result = entry.get('result')
            error = entry.get('error')

            # Parse params from JSON string
            params = {}
            params_json_str = entry.get('params_json')
            if params_json_str:
                try:
                    params = json.loads(params_json_str)
                except (json.JSONDecodeError, TypeError):
                    params = {}

            # Format params string (truncate long values)
            if isinstance(params, dict):
                params_str = ", ".join(
                    f"{k}={repr(v)[:40]}{'...' if len(repr(v)) > 40 else ''}"
                    for k, v in params.items()
                )
            else:
                params_str = str(params)[:100]

            # Parse timestamp to get HH:MM:SS
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M:%S')
            except (ValueError, AttributeError):
                time_str = timestamp.split('T')[1].split('.')[0] if 'T' in timestamp else '??:??:??'

            # Format entry
            if error:
                # Error format: [HH:MM:SS] tool_name (params) × error
                log_text = f"[{time_str}] {tool_name} ({params_str}) × {error}"
                cursor = self.log_display.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.log_display.setTextCursor(cursor)

                # Format error with color
                fmt = QTextCharFormat()
                fmt.setForeground(self._get_error_color())
                cursor.insertText(log_text + '\n', fmt)
            else:
                # Success format: [HH:MM:SS] tool_name (params) → result
                result_display = result[:60] + "..." if result and len(result) > 60 else (result or "")
                log_text = f"[{time_str}] {tool_name} ({params_str}) → {result_display}"
                cursor = self.log_display.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                self.log_display.setTextCursor(cursor)

                # Format success with color
                fmt = QTextCharFormat()
                fmt.setForeground(self._get_success_color())
                cursor.insertText(log_text + '\n', fmt)

            # Limit to max lines for performance
            doc = self.log_display.document()
            max_lines = 1000
            if doc.blockCount() > max_lines:
                cursor = self.log_display.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                for _ in range(doc.blockCount() - max_lines):
                    cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                    cursor.removeSelectedText()

            # Auto-scroll to bottom
            cursor = self.log_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.log_display.setTextCursor(cursor)
            self.log_display.ensureCursorVisible()

        except Exception as e:
            logger.debug(f"Failed to append tool log entry: {e}")

    def _get_error_color(self) -> QColor:
        """Get error text color based on current theme."""
        # Check if dark theme is active
        is_dark = False
        if hasattr(self, 'app') and self.app:
            # Try to detect dark theme from app
            if hasattr(self.app, 'current_theme'):
                is_dark = self.app.current_theme == 'dark'
            elif hasattr(self.app, 'settings'):
                is_dark = self.app.settings.get('theme') == 'dark'

        # Use semantic error color
        if is_dark:
            return QColor('#F0A6AA')  # --sape-color-semantic-error-text (dark)
        else:
            return QColor('#842126')  # --sape-color-semantic-error-text (light)

    def _get_success_color(self) -> QColor:
        """Get success text color based on current theme."""
        # Check if dark theme is active
        is_dark = False
        if hasattr(self, 'app') and self.app:
            if hasattr(self.app, 'current_theme'):
                is_dark = self.app.current_theme == 'dark'
            elif hasattr(self.app, 'settings'):
                is_dark = self.app.settings.get('theme') == 'dark'

        # Use semantic success color
        if is_dark:
            return QColor('#8FD8B7')  # --sape-color-semantic-success-text (dark)
        else:
            return QColor('#0F5C3C')  # --sape-color-semantic-success-text (light)

    def _on_clear(self):
        """Clear the log display (doesn't reset internal state)."""
        self.log_display.clear()
        logger.info("Session log display cleared")

    def _update_language(self, language: str) -> None:
        """Update page text for the specified language."""
        self.title_container.setText(translate("session_log.title", language))
        self.subtitle.setText(translate("session_log.subtitle", language))
        self.clear_btn.setText(translate("session_log.clear_button", language))
        self.export_btn.setText(translate("session_log.export_button", language))

    def _update_theme(self, theme: str) -> None:
        """Update colors for the specified theme."""
        text_color = DARK_TEXT_SECONDARY if theme == "dark" else LIGHT_TEXT_SECONDARY
        self.subtitle.setStyleSheet(f"color: {text_color.name()};")

    def _on_export(self):
        """Export log to CSV file from LogStore."""
        language = self.app.current_language if self.app else "en-US"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            translate("session_log.export_dialog_title", language),
            f"session_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            translate("session_log.export_dialog_filter", language)
        )

        if filename:
            try:
                # Check if we can export
                if not self.log_store or not self.session_id:
                    raise RuntimeError("Log store not available")

                # Get all logs for this session
                logs = self.log_store.get_logs(self.session_id)

                # Write to CSV using proper CSV module
                with open(filename, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Timestamp', 'Tool Name', 'Parameters', 'Result', 'Error'])

                    for entry in logs:
                        timestamp = entry.get('timestamp', '')
                        tool_name = entry.get('tool_name', '')
                        params_json = entry.get('params_json', '{}')
                        result = entry.get('result', '')
                        error = entry.get('error', '')

                        # Parse params_json for display
                        try:
                            params = json.loads(params_json)
                            # Format as compact string
                            params_str = json.dumps(params)
                        except (json.JSONDecodeError, TypeError):
                            params_str = params_json

                        writer.writerow([timestamp, tool_name, params_str, result or '', error or ''])

                logger.info(f"Log exported to: {filename}")
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle(translate("session_log.export_success_title", language))
                msg_box.setText(f"{translate('session_log.export_success_message', language)}\n{filename}")
                msg_box.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
                msg_box.exec()
            except Exception as e:
                logger.error(f"Failed to export log: {e}")
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle(translate("session_log.export_error_title", language))
                msg_box.setText(f"{translate('session_log.export_error_message', language)}\n{str(e)}")
                msg_box.addButton(translate("common.ok", language), QMessageBox.ButtonRole.AcceptRole)
                msg_box.exec()

    def log_tool_call(self, tool_name: str, params: dict, result: str = None, error: str = None):
        """Log a tool call with parameters and result/error.

        This method is called by ServerThread when a tool is invoked.

        Args:
            tool_name: Name of the tool called (e.g., "create", "list", "delete")
            params: Dictionary of parameters passed to the tool
            result: Result string if successful
            error: Error message if the call failed
        """
        try:
            # Format parameters for display (truncate long values)
            params_str = ", ".join(
                f"{k}={repr(v)[:50]}{'...' if len(repr(v)) > 50 else ''}"
                for k, v in params.items()
            )

            if error:
                log_msg = f"TOOL: {tool_name} | PARAMS: {params_str} | ERROR: {error}"
                logger.error(log_msg)
            else:
                # Truncate result if very long
                result_display = result[:100] + "..." if result and len(result) > 100 else result
                log_msg = f"TOOL: {tool_name} | PARAMS: {params_str} | RESULT: {result_display}"
                logger.info(log_msg)

            # Emit signal for external listeners
            self.tool_called.emit(tool_name, params, result or error or "")
        except Exception as e:
            logger.error(f"Failed to log tool call: {e}")
