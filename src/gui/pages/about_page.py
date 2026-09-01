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

"""About page with fancy branded design and i18n support."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtGui import QFont, QPixmap, QColor
from PyQt6.QtCore import Qt
from pathlib import Path
from ..styles.sape_design_tokens import (
    SAPE_PRIMARY, SAPE_ACCENT, SPACING_MD, SPACING_LG, SPACING_2XL,
    LIGHT_TEXT_PRIMARY, LIGHT_TEXT_SECONDARY,
    DARK_TEXT_PRIMARY, DARK_TEXT_SECONDARY,
    LIGHT_BORDER, DARK_BORDER
)
from PyQt6.QtCore import Qt
from ..i18n import translate
from ..._version import __version__


class AboutPage(QWidget):
    """About SAPÉ f-MCP with fancy branded design and multi-language support."""

    def __init__(self, app=None):
        super().__init__()
        self.app = app
        self.logo_label = None

        # Store all text labels as instance variables for language updates
        self.title_label = None
        self.tagline_label = None
        self.mission_title_label = None
        self.mission_desc_label = None
        self.why_title_label = None
        self.tech_title_label = None
        self.benefit_labels = []
        self.tech_labels = []
        self.author_label = None
        self.copyright_label = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(SPACING_LG)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(SPACING_LG)

        # Logo (centered, large)
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._load_icon()
        self.scroll_layout.addWidget(self.logo_label)
        self.scroll_layout.addSpacing(SPACING_MD)

        # Main title
        self.title_label = QLabel()
        title_font = QFont("IBM Plex Sans", 24, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(f"color: {SAPE_PRIMARY.name()}; margin: 0;")
        self.scroll_layout.addWidget(self.title_label)

        # Tagline
        self.tagline_label = QLabel()
        tagline_font = QFont("IBM Plex Sans", 11)
        tagline_font.setItalic(True)
        self.tagline_label.setFont(tagline_font)
        self.tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tagline_label.setStyleSheet("margin: 0; line-height: 1.4;")
        self.scroll_layout.addWidget(self.tagline_label)

        # Separator (will be updated by theme change)
        self.separator = QLabel()
        self.separator.setFixedHeight(1)
        self.scroll_layout.addWidget(self.separator)

        # Version
        self.version_label = QLabel(f"Version {__version__}")
        version_font = QFont("IBM Plex Sans", 9)
        self.version_label.setFont(version_font)
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_layout.addWidget(self.version_label)

        self.scroll_layout.addSpacing(SPACING_MD)

        # Mission section
        self.mission_title_label = QLabel()
        mission_title_font = QFont("IBM Plex Sans", 13, QFont.Weight.Bold)
        self.mission_title_label.setFont(mission_title_font)
        self.mission_title_label.setStyleSheet(f"color: {SAPE_PRIMARY.name()}; margin-bottom: 4px;")
        self.scroll_layout.addWidget(self.mission_title_label)

        self.mission_desc_label = QLabel()
        self.mission_desc_label.setWordWrap(True)
        self.mission_desc_label.setStyleSheet("line-height: 1.6; margin: 8px 0 16px 0;")
        self.scroll_layout.addWidget(self.mission_desc_label)

        # Why SAPÉ section
        self.why_title_label = QLabel()
        self.why_title_label.setFont(mission_title_font)
        self.why_title_label.setStyleSheet(f"color: {SAPE_PRIMARY.name()}; margin-bottom: 8px;")
        self.scroll_layout.addWidget(self.why_title_label)

        # Benefit labels (will be created in _update_language)
        self.benefits_container = QVBoxLayout()
        self.scroll_layout.addLayout(self.benefits_container)

        self.scroll_layout.addSpacing(SPACING_MD)

        # Tech Stack section
        self.tech_title_label = QLabel()
        self.tech_title_label.setFont(mission_title_font)
        self.tech_title_label.setStyleSheet(f"color: {SAPE_PRIMARY.name()}; margin-bottom: 8px;")
        self.scroll_layout.addWidget(self.tech_title_label)

        # Tech labels (will be created in _update_language)
        self.tech_container = QVBoxLayout()
        self.scroll_layout.addLayout(self.tech_container)

        self.scroll_layout.addSpacing(SPACING_MD)

        # Separator (will be updated by theme change)
        self.separator2 = QLabel()
        self.separator2.setFixedHeight(1)
        self.scroll_layout.addWidget(self.separator2)

        # Author section
        self.author_label = QLabel()
        author_font = QFont("IBM Plex Sans", 10, QFont.Weight.Bold)
        self.author_label.setFont(author_font)
        self.author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.author_label.setStyleSheet(f"color: {SAPE_PRIMARY.name()}; margin: 12px 0 0 0;")
        self.scroll_layout.addWidget(self.author_label)

        self.email_label = QLabel("info@sapebud.com")
        email_font = QFont("IBM Plex Sans", 9)
        self.email_label.setFont(email_font)
        self.email_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.email_label.setStyleSheet("margin: 0;")
        self.scroll_layout.addWidget(self.email_label)

        # Carries the GPL-3.0 section 5(d) legal notice as well as the
        # copyright line, so it needs to wrap rather than widen the layout.
        self.copyright_label = QLabel()
        copyright_font = QFont("IBM Plex Sans", 8)
        self.copyright_label.setFont(copyright_font)
        self.copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.copyright_label.setWordWrap(True)
        self.copyright_label.setStyleSheet("margin-top: 12px;")
        self.scroll_layout.addWidget(self.copyright_label)

        # Separator (will be updated by theme change)
        self.separator3 = QLabel()
        self.separator3.setFixedHeight(1)
        self.scroll_layout.addWidget(self.separator3)

        # SAPÉ Community link
        self.sapebud_link = QLabel()
        sapebud_font = QFont("IBM Plex Sans", 9)
        self.sapebud_link.setFont(sapebud_font)
        self.sapebud_link.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sapebud_link.setOpenExternalLinks(True)
        self.sapebud_link.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sapebud_link.setStyleSheet(f"margin-top: 12px; color: {SAPE_PRIMARY.name()};")
        self.scroll_layout.addWidget(self.sapebud_link)

        self.scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Connect signals
        if self.app:
            self.app.theme_manager.theme_changed.connect(self._on_theme_changed)
            self.app.language_changed.connect(self._update_language)

        # Initial language and theme update
        self._update_language(self.app.current_language if self.app else "en-US")
        self._update_theme_colors(self.app.current_theme if self.app else "light")

    def _load_icon(self) -> None:
        """Load and display icon based on current theme."""
        theme = "light" if self.app and self.app.current_theme == "light" else "dark"
        icon_filename = "trans-256.png" if theme == "light" else "dark-256.png"
        icon_path = Path(__file__).parent.parent.parent.parent / "gui_resources" / "icons" / icon_filename

        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            scaled_pixmap = pixmap.scaledToWidth(128, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            self.logo_label.setText("SAPÉ")
            self.logo_label.setFont(QFont("IBM Plex Sans", 48, QFont.Weight.Bold))

    def _on_theme_changed(self, theme: str) -> None:
        """Handle theme change."""
        self._load_icon()
        self._update_theme_colors(theme)

    def _update_language(self, language: str) -> None:
        """Update all text labels to the specified language.

        Args:
            language (str): "en-US" or "es-ES"
        """
        self.title_label.setText(translate("about.title", language))
        self.tagline_label.setText(translate("about.tagline", language))
        self.mission_title_label.setText(translate("about.mission_title", language))
        self.mission_desc_label.setText(translate("about.mission_desc", language))
        self.why_title_label.setText(translate("about.why_title", language))
        self.tech_title_label.setText(translate("about.tech_title", language))
        self.author_label.setText(translate("about.author", language))
        self.copyright_label.setText(translate("about.copyright", language))

        # Update SAPÉ Community link
        link_text = translate("about.sapebud_link", language)
        self.sapebud_link.setText(f'<a href="https://sapebud.com">{link_text}</a>')
        self.sapebud_link.setToolTip(translate("about.sapebud_link_tooltip", language))

        # Clear and rebuild benefit labels
        while self.benefits_container.count():
            item = self.benefits_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.benefit_labels = []

        benefits = [
            ("about.benefit_security", "about.benefit_security_desc"),
            ("about.benefit_performance", "about.benefit_performance_desc"),
            ("about.benefit_auditability", "about.benefit_auditability_desc")
        ]

        for title_key, desc_key in benefits:
            title_text = translate(title_key, language)
            desc_text = translate(desc_key, language)
            benefit_label = QLabel(f"• {title_text}: {desc_text}")
            benefit_label.setWordWrap(True)
            benefit_label.setStyleSheet("line-height: 1.6; margin: 6px 0; padding-left: 12px;")
            self.benefits_container.addWidget(benefit_label)
            self.benefit_labels.append(benefit_label)

        # Clear and rebuild tech labels
        while self.tech_container.count():
            item = self.tech_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.tech_labels = []

        tech_keys = [
            "about.tech_python",
            "about.tech_pyqt",
            "about.tech_sqlite",
            "about.tech_mcp",
            "about.tech_design"
        ]

        for tech_key in tech_keys:
            tech_text = translate(tech_key, language)
            tech_label = QLabel(f"• {tech_text}")
            tech_label.setWordWrap(True)
            tech_label.setStyleSheet("line-height: 1.6; margin: 4px 0; padding-left: 12px;")
            self.tech_container.addWidget(tech_label)
            self.tech_labels.append(tech_label)

    def _update_theme_colors(self, theme: str) -> None:
        """Update text colors based on current theme for WCAG AA contrast."""
        is_dark = theme == "dark"
        text_color = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
        secondary_color = DARK_TEXT_SECONDARY if is_dark else LIGHT_TEXT_SECONDARY
        border_color = DARK_BORDER if is_dark else LIGHT_BORDER

        # Update tagline and descriptions
        self.tagline_label.setStyleSheet(f"color: {text_color.name()}; margin: 0; line-height: 1.4;")
        self.mission_desc_label.setStyleSheet(f"line-height: 1.6; margin: 8px 0 16px 0; color: {text_color.name()};")

        # Update separators
        self.separator.setStyleSheet(f"border-top: 1px solid {border_color.name()}; margin: 16px 0;")
        self.separator2.setStyleSheet(f"border-top: 1px solid {border_color.name()}; margin: 16px 0;")
        self.separator3.setStyleSheet(f"border-top: 1px solid {border_color.name()}; margin: 16px 0;")

        # Update version and contact info
        self.version_label.setStyleSheet(f"color: {secondary_color.name()};")
        self.email_label.setStyleSheet(f"color: {secondary_color.name()}; margin: 0;")
        self.copyright_label.setStyleSheet(f"color: {secondary_color.name()}; margin-top: 12px;")

        # Update SAPÉ Community link color (use primary accent for links)
        link_color = SAPE_ACCENT.name() if is_dark else SAPE_PRIMARY.name()
        self.sapebud_link.setStyleSheet(f"margin-top: 12px; color: {link_color};")

        # Update benefit labels
        for benefit_label in self.benefit_labels:
            benefit_label.setStyleSheet(f"line-height: 1.6; margin: 6px 0; padding-left: 12px; color: {text_color.name()};")

        # Update tech labels
        for tech_label in self.tech_labels:
            tech_label.setStyleSheet(f"line-height: 1.6; margin: 4px 0; padding-left: 12px; color: {text_color.name()};")
