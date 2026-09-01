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

"""Sidebar navigation component."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont
from ..styles.sape_design_tokens import (
    SPACING_MD, SPACING_LG, SPACING_SM, SPACING_XL, RADIUS_MD,
    SAPE_PRIMARY, LIGHT_SURFACE, DARK_SURFACE
)
from ..i18n import translate


class Sidebar(QWidget):
    """Left sidebar with menu-style navigation."""

    nav_clicked = pyqtSignal(int)  # page index

    def __init__(self, main_window=None):
        super().__init__(main_window)
        self.main_window = main_window
        self.app = main_window.app if main_window else None
        self.setMaximumWidth(250)
        self.setMinimumWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        layout.setSpacing(SPACING_SM)

        # Section label (will be updated by language changes)
        self.section_label = QLabel()
        section_font = QFont()
        section_font.setPointSize(10)
        section_font.setBold(True)
        self.section_label.setFont(section_font)
        layout.addWidget(self.section_label)

        # Navigation menu items with translation keys
        self.nav_items = [
            ("sidebar.session_log", 0),
            ("sidebar.permissions", 1),
            ("sidebar.settings", 2),
            ("sidebar.legal", 3),
            ("sidebar.help", 4),
            ("sidebar.about", 5),
        ]

        # Emoji icons for each page
        self.nav_icons = ["📋", "🔐", "⚙️", "📜", "❓", "ℹ️"]

        self.button_group = []

        for i, (trans_key, page_index) in enumerate(self.nav_items):
            btn = QPushButton()
            # Will be set by _update_language
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=page_index: self._on_nav(idx))
            btn.setMinimumHeight(36)
            btn.setProperty("page_index", page_index)

            # Menu-style: left-aligned with padding, not centered button
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 20px;
                    border: none;
                    border-radius: 4px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: rgba(28, 63, 240, 0.1);
                }
                QPushButton:checked {
                    background-color: #1C3FF0;
                    color: white;
                    font-weight: bold;
                }
                QPushButton:checked:hover {
                    background-color: #122AD2;
                }
            """)

            layout.addWidget(btn)
            self.button_group.append(btn)

        # Set first button as active by default
        self.button_group[0].setChecked(True)

        layout.addStretch()

        # Connect language change signal
        if self.app:
            self.app.language_changed.connect(self._update_language)

        # Initial language update
        self._update_language(self.app.current_language if self.app else "en-US")

    def _on_nav(self, page_index: int):
        """Handle navigation menu click."""
        # Uncheck all buttons
        for btn in self.button_group:
            btn.setChecked(False)

        # Check the clicked button
        self.button_group[page_index].setChecked(True)

        # Emit signal
        self.nav_clicked.emit(page_index)

    def set_active_page(self, page_index: int):
        """Set active page (programmatically)."""
        if 0 <= page_index < len(self.button_group):
            for btn in self.button_group:
                btn.setChecked(False)
            self.button_group[page_index].setChecked(True)

    def _update_language(self, language: str) -> None:
        """Update sidebar text for the specified language."""
        self.section_label.setText(translate("sidebar.console", language))
        for i, (trans_key, page_index) in enumerate(self.nav_items):
            if i < len(self.button_group):
                label_text = translate(trans_key, language)
                icon = self.nav_icons[i]
                self.button_group[i].setText(f"{icon} {label_text}")
