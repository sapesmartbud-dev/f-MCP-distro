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

"""Legal documents page with inline markdown viewing and document navigation."""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, QLabel
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path

from ..styles.sape_design_tokens import (
    SAPE_PRIMARY, SPACING_MD, SPACING_LG, SPACING_SM,
    LIGHT_BG, LIGHT_SURFACE, LIGHT_TEXT_PRIMARY, LIGHT_TEXT_SECONDARY, LIGHT_BORDER,
    DARK_BG, DARK_SURFACE, DARK_TEXT_PRIMARY, DARK_TEXT_SECONDARY, DARK_BORDER,
)
from ..i18n import translate
from ...legal_document_loader import LegalDocumentLoader

logger = logging.getLogger(__name__)


class LegalDocumentViewer(QScrollArea):
    """Scrollable markdown document viewer with theme support."""

    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.setWidgetResizable(True)
        self.setStyleSheet("QScrollArea { border: none; }")

        # Create content widget with markdown display
        self.content_widget = QLabel()
        self.content_widget.setWordWrap(True)
        self.content_widget.setOpenExternalLinks(True)
        self.content_widget.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setWidget(self.content_widget)

        # Connect to theme changes
        if self.app:
            self.app.theme_manager.theme_changed.connect(self._update_theme)

        # Initial theme
        self._update_theme()

    def set_content(self, markdown_text: str):
        """Set the markdown content for display.

        Args:
            markdown_text: Markdown content as string
        """
        # Convert markdown to plain text with basic formatting
        # For now, display as-is (PyQt6 doesn't have built-in markdown,
        # but we can use basic text formatting)
        self.content_widget.setText(markdown_text)
        self.content_widget.setStyleSheet("""
            QLabel {
                padding: 16px;
                line-height: 1.6;
                font-family: 'IBM Plex Sans';
                font-size: 11pt;
                white-space: pre-wrap;
            }
        """)

    def _update_theme(self):
        """Update colors based on current theme."""
        if self.app:
            theme = self.app.current_theme
            if theme == "light":
                bg_color = LIGHT_SURFACE.name()
                text_color = LIGHT_TEXT_PRIMARY.name()
                border_color = LIGHT_BORDER.name()
            else:
                bg_color = DARK_SURFACE.name()
                text_color = DARK_TEXT_PRIMARY.name()
                border_color = DARK_BORDER.name()

            self.setStyleSheet(f"""
                QScrollArea {{
                    background-color: {bg_color};
                    border: 1px solid {border_color};
                }}
            """)
            self.content_widget.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg_color};
                    color: {text_color};
                    padding: 16px;
                    line-height: 1.6;
                    font-family: 'IBM Plex Sans';
                    font-size: 11pt;
                    white-space: pre-wrap;
                }}
            """)


class LegalPage(QWidget):
    """Display legal documents with sidebar navigation."""

    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.loader = LegalDocumentLoader()
        self.current_language = "en-US"
        self.current_document = "license"
        self.document_buttons = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ===== LEFT SIDEBAR: Document list =====
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        left_layout.setSpacing(SPACING_SM)
        left_panel.setMaximumWidth(250)
        left_panel.setMinimumWidth(200)

        # Section label (will be updated by language changes)
        self.section_label = QLabel()
        section_font = QFont("IBM Plex Sans", 10, QFont.Weight.Bold)
        self.section_label.setFont(section_font)
        left_layout.addWidget(self.section_label)

        # Document list. Four documents since the move to GPL-3.0-only: the
        # proprietary, terms-of-use, intellectual-property and legal-compliance
        # documents asserted terms that GPL-3.0 section 7 voids as further
        # restrictions, so they were removed rather than rewritten. Their
        # legal.* translation keys are left in the catalogue unused.
        self.documents_list = [
            ("license", "legal.license"),
            ("disclaimer", "legal.disclaimer"),
            ("data-protection", "legal.data"),
            ("legal-readme", "legal.legal_readme"),
        ]

        for doc_key, trans_key in self.documents_list:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(36)
            btn.clicked.connect(lambda checked, key=doc_key: self._on_document_selected(key))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 12px;
                    border: none;
                    border-radius: 4px;
                    font-size: 12px;
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
            left_layout.addWidget(btn)
            self.document_buttons[doc_key] = (btn, trans_key)

        left_layout.addStretch()
        layout.addWidget(left_panel)

        # ===== RIGHT PANEL: Document viewer =====
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        right_layout.setSpacing(SPACING_LG)

        # Title label (current document name)
        self.title_label = QLabel()
        title_font = QFont("IBM Plex Sans", 16, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {SAPE_PRIMARY.name()};")
        right_layout.addWidget(self.title_label)

        # Document viewer
        self.viewer = LegalDocumentViewer(app)
        right_layout.addWidget(self.viewer, 1)

        right_panel = QWidget()
        right_panel.setLayout(right_layout)
        layout.addWidget(right_panel, 1)

        # Connect language change signal
        if self.app:
            self.app.language_changed.connect(self._update_language)
            self.app.theme_manager.theme_changed.connect(self._update_theme)

        # Initial language update
        language = self.app.current_language if self.app else "en-US"
        self._update_language(language)

        # Select first document by default
        self._on_document_selected("license")

    def _on_document_selected(self, doc_key: str):
        """Handle document selection from sidebar."""
        self.current_document = doc_key

        # Update button states
        for key, (btn, _) in self.document_buttons.items():
            btn.setChecked(key == doc_key)

        # Load and display document
        self._load_and_display_document(doc_key)

        # Update title
        if doc_key in self.document_buttons:
            _, trans_key = self.document_buttons[doc_key]
            title = translate(trans_key, self.current_language)
            self.title_label.setText(title)

    def _load_and_display_document(self, doc_key: str):
        """Load and display a legal document."""
        # Map document keys to file names expected by LegalDocumentLoader
        doc_filename_map = {
            "license": "LICENSE.md",
            "disclaimer": "DISCLAIMER.md",
            "data-protection": "DATA-PROTECTION.md",
            "legal-readme": "LEGAL-README.md",
        }

        filename = doc_filename_map.get(doc_key, "LICENSE.md")

        try:
            content = self.loader.get_document(self.current_language, filename)
            self.viewer.set_content(content)
        except Exception as e:
            logger.error(f"Failed to load document {doc_key}: {e}")
            error_msg = translate("legal.doc_not_available_message", self.current_language)
            self.viewer.set_content(error_msg)

    def _update_language(self, language: str):
        """Update all text labels and reload documents."""
        self.current_language = language

        # Update section label
        self.section_label.setText(translate("legal.documents", language))

        # Update document button labels
        for doc_key, (btn, trans_key) in self.document_buttons.items():
            btn.setText(translate(trans_key, language))

        # Reload current document
        self._load_and_display_document(self.current_document)

    def _update_theme(self):
        """Update styling based on theme."""
        if self.app:
            theme = self.app.current_theme
            if theme == "light":
                bg_color = LIGHT_BG.name()
                border_color = LIGHT_BORDER.name()
            else:
                bg_color = DARK_BG.name()
                border_color = DARK_BORDER.name()

            # Update left panel styling
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {bg_color};
                }}
            """)
