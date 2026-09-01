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

"""Status bar component showing server status and controls."""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont
from ..styles.sape_design_tokens import (
    SPACING_MD, SPACING_LG, COLOR_SUCCESS, DARK_SURFACE,
    DARK_TEXT_SECONDARY, DARK_BORDER
)
from ..i18n import translate


class StatusBar(QWidget):
    """Status bar showing service status and controls."""

    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.app = main_window.app
        self.is_running = False
        self._port = None  # Cache the port number
        self._default_port = 8089  # Cache the default port

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        layout.setSpacing(SPACING_MD)

        # Status indicator with emoji
        self.status_dot = QLabel("⭕")
        self.status_dot.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.status_dot)

        # Status label (will be updated by language changes)
        self.status_label = QLabel()
        status_font = QFont()
        status_font.setPointSize(10)
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)

        # Port label (shown when server is running, will be updated by language changes)
        self.port_label = QLabel("")
        port_font = QFont()
        port_font.setPointSize(9)
        self.port_label.setFont(port_font)
        self.port_label.setStyleSheet("color: #2D3139;")
        layout.addWidget(self.port_label)

        # Spacer
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding))

        # Start button (will be updated by language changes)
        self.start_btn = QPushButton()
        self.start_btn.setMinimumHeight(32)
        self.start_btn.setMaximumWidth(110)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self._on_start)
        layout.addWidget(self.start_btn)

        # Stop button (disabled by default, will be updated by language changes)
        self.stop_btn = QPushButton()
        self.stop_btn.setMinimumHeight(32)
        self.stop_btn.setMaximumWidth(110)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._on_stop)
        layout.addWidget(self.stop_btn)

        # Connect language change signal
        if self.app:
            self.app.language_changed.connect(self._update_language)

        # Initial language update
        self._update_language(self.app.current_language if self.app else "en-US")

    def set_running(self, is_running: bool):
        """Update status indicator."""
        self.is_running = is_running
        language = self.app.current_language if self.app else "en-US"

        if is_running:
            self.status_dot.setText("🟢")
            self.status_label.setText(f"✓ {translate('status.service_running', language)}")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            # Port label is set separately via set_port_info()
            # Re-render port label if we have cached port info
            if self._port is not None:
                self._render_port_label(language)
        else:
            self.status_dot.setText("⭕")
            self.status_label.setText(f"○ {translate('status.service_stopped', language)}")
            self.port_label.setText("")  # Clear port label
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def set_port_info(self, port: int, default_port: int = 8089):
        """Set the port info label to show which port is in use.

        Args:
            port: The actual port number the server is using
            default_port: The default port (usually 8089)
        """
        self._port = port
        self._default_port = default_port
        language = self.app.current_language if self.app else "en-US"
        self._render_port_label(language)

    def _render_port_label(self, language: str):
        """Render the port label based on cached port info."""
        if self._port == self._default_port:
            self.port_label.setText(f"{translate('status_bar.port_info', language)} {self._port}")
        else:
            # Use placeholder for non-default port
            alt_text = translate("status_bar.port_info_alt", language)
            self.port_label.setText(f"{translate('status_bar.port_info', language)} {self._port} ({alt_text.format(default=self._default_port)})")

    def _update_language(self, language: str) -> None:
        """Update status bar text for the specified language."""
        self.start_btn.setText(f"▶ {translate('status.start_button', language)}")
        self.stop_btn.setText(f"■ {translate('status.stop_button', language)}")

        # Update status label based on current state
        if self.is_running:
            self.status_label.setText(f"✓ {translate('status.service_running', language)}")
        else:
            self.status_label.setText(f"○ {translate('status.service_stopped', language)}")

        # Re-render port label with new language
        if self._port is not None:
            self._render_port_label(language)

    def _on_start(self):
        """Handle start button click."""
        self.start_clicked.emit()

    def _on_stop(self):
        """Handle stop button click."""
        self.stop_clicked.emit()
