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

"""Help page with i18n support."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from ..i18n import translate
from ..styles.sape_design_tokens import (
    LIGHT_TEXT_PRIMARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_PRIMARY, DARK_TEXT_SECONDARY
)


class HelpPage(QWidget):
    """Help and documentation with multi-language support."""

    def __init__(self, app=None):
        super().__init__()
        self.app = app

        # Create scroll area for long content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(16)

        # Store labels for language updates
        self.title_label = None
        self.subtitle_label = None
        self.started_title_label = None
        self.started_label = None
        self.perm_title_label = None
        self.perm_label = None
        self.mcp_title_label = None
        self.mcp_label = None
        self.faq_title_label = None
        self.faq_label = None

        # Create layout (will be populated in _update_language)
        self._build_layout()

        scroll.setWidget(content_widget)

        # Main layout for this page
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

        # Connect language and theme change signals
        if self.app:
            self.app.language_changed.connect(self._update_language)
            self.app.theme_manager.theme_changed.connect(self._update_theme_colors)

        # Initial language and theme update
        self._update_language(self.app.current_language if self.app else "en-US")
        self._update_theme_colors(self.app.current_theme if self.app else "light")

    def _build_layout(self):
        """Build the basic layout structure."""
        # Title
        self.title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.layout.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel()
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_font.setItalic(True)
        self.subtitle_label.setFont(subtitle_font)
        self.layout.addWidget(self.subtitle_label)

        # Getting Started
        self.started_title_label = QLabel()
        started_title_font = QFont()
        started_title_font.setPointSize(12)
        started_title_font.setBold(True)
        self.started_title_label.setFont(started_title_font)
        self.layout.addWidget(self.started_title_label)

        self.started_label = QLabel()
        self.started_label.setWordWrap(True)
        self.started_label.setStyleSheet("line-height: 1.6; margin: 12px 0;")
        self.layout.addWidget(self.started_label)

        # Permissions Guide
        self.perm_title_label = QLabel()
        self.perm_title_label.setFont(started_title_font)
        self.layout.addWidget(self.perm_title_label)

        self.perm_label = QLabel()
        self.perm_label.setWordWrap(True)
        self.perm_label.setStyleSheet("line-height: 1.6; margin: 12px 0;")
        self.layout.addWidget(self.perm_label)

        # MCP Server
        self.mcp_title_label = QLabel()
        self.mcp_title_label.setFont(started_title_font)
        self.layout.addWidget(self.mcp_title_label)

        self.mcp_label = QLabel()
        self.mcp_label.setWordWrap(True)
        self.mcp_label.setStyleSheet("line-height: 1.6; margin: 12px 0;")
        self.layout.addWidget(self.mcp_label)

        # FAQ
        self.faq_title_label = QLabel()
        self.faq_title_label.setFont(started_title_font)
        self.layout.addWidget(self.faq_title_label)

        self.faq_label = QLabel()
        self.faq_label.setWordWrap(True)
        self.faq_label.setStyleSheet("line-height: 1.8; margin: 12px 0;")
        self.layout.addWidget(self.faq_label)

        self.layout.addStretch()

    def _update_language(self, language: str) -> None:
        """Update all text labels to the specified language.

        Args:
            language (str): "en-US" or "es-ES"
        """
        self.title_label.setText(translate("help.title", language))
        self.subtitle_label.setText(translate("help.subtitle", language))
        self.started_title_label.setText(translate("help.started", language))
        self.started_label.setText(translate("help.started_text", language))
        self.perm_title_label.setText(translate("help.permission", language))
        self.perm_label.setText(translate("help.permission_text", language))
        self.mcp_title_label.setText(translate("help.mcp", language))
        self.mcp_label.setText(translate("help.mcp_text", language))
        self.faq_title_label.setText(translate("help.faq", language))
        self.faq_label.setText(translate("help.faq_text", language))

    def _update_theme_colors(self, theme: str) -> None:
        """Update text colors based on current theme for WCAG AA contrast."""
        is_dark = theme == "dark"
        text_color = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY

        # Update subtitle and text-based labels
        self.subtitle_label.setStyleSheet(f"color: {text_color.name()};")
        self.perm_label.setStyleSheet(f"line-height: 1.6; margin: 12px 0; color: {text_color.name()};")
        self.mcp_label.setStyleSheet(f"line-height: 1.6; margin: 12px 0; color: {text_color.name()};")
        self.faq_label.setStyleSheet(f"line-height: 1.8; margin: 12px 0; color: {text_color.name()};")
