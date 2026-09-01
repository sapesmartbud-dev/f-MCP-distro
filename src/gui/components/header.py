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

"""Header component with logo, title, and theme toggle."""

import logging
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy, QComboBox
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor
from PyQt6.QtCore import QSize
from pathlib import Path
from ..styles.sape_design_tokens import (
    SPACING_MD, SPACING_LG, SPACING_XL,
    FONT_FAMILY,
    LIGHT_TEXT_PRIMARY, DARK_TEXT_PRIMARY
)
from ..i18n import translate, get_supported_languages
from ...language_registry import LanguageRegistry

logger = logging.getLogger(__name__)


class Header(QWidget):
    """Application header with logo, title, and controls."""

    theme_toggled = pyqtSignal(str)  # "light" or "dark"
    language_changed = pyqtSignal(str)  # "en-US" or "es-ES"

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.app = main_window.app
        self.current_theme = self.app.current_theme

        # Cache for flag icons (load once, reuse)
        self.flag_icon_cache = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_MD, SPACING_LG, SPACING_MD)
        layout.setSpacing(SPACING_MD)

        # Logo as SVG image (left side) - 75px height with automatic width scaling
        # Native aspect ratio: 3660x920 = 3.978:1, so width = 75 * 3.978 ≈ 299px
        self.logo_label = QLabel()
        self.logo_label.setMaximumWidth(300)
        self.logo_label.setMaximumHeight(75)
        self.logo_label.setMinimumHeight(75)
        self.logo_label.setScaledContents(False)
        self._load_logo(self.current_theme)
        layout.addWidget(self.logo_label)

        # Title "f-MCP" in IBM Plex Sans, 22pt
        self.title_label = QLabel("f-MCP")
        title_font = QFont(FONT_FAMILY)
        title_font.setPointSize(22)
        title_font.setWeight(QFont.Weight.Normal)  # Weight 400
        self.title_label.setFont(title_font)
        self._update_title_color(self.current_theme)
        self.title_label.setStyleSheet("padding-top: 5px;")
        layout.addWidget(self.title_label)

        # Add 20px gap between title and spacer
        layout.addSpacing(SPACING_XL)

        # Spacer
        layout.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding))

        # Theme toggle button with SVG icon
        self.theme_btn = QPushButton()
        self._update_theme_icon(self.current_theme)
        self.theme_btn.setMaximumWidth(40)
        self.theme_btn.setMaximumHeight(40)
        self.theme_btn.setMinimumHeight(32)
        self.theme_btn.setToolTip(translate("header.theme_toggle", self.app.current_language))
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        layout.addWidget(self.theme_btn)

        # Language selector with QComboBox - supports all 18 languages
        self.language_combo = QComboBox()
        self.language_combo.setMaximumWidth(630)  # Extra wide for longer native names
        self.language_combo.setMinimumHeight(32)
        self.language_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.language_combo.setMaxVisibleItems(10)  # Scroll after 10 items
        self.language_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        # Populate combo box with all 18 languages sorted by native name
        # Get all languages sorted alphabetically by native name
        all_langs_sorted = LanguageRegistry.get_all_languages_sorted()

        for lang_code, native_name in all_langs_sorted:
            # Add language with native name and flag icon
            self.language_combo.addItem(native_name, lang_code)
            idx = self.language_combo.count() - 1
            # Load and cache flag icon
            flag_icon = self._get_flag_icon_cached(lang_code)
            if flag_icon:
                self.language_combo.setItemIcon(idx, flag_icon)

        # Sync to current language without triggering signal during init
        current_index = self.language_combo.findData(self.app.current_language)
        if current_index < 0:
            current_index = 0  # Fallback to first item
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(current_index)
        self.language_combo.blockSignals(False)

        # Connect to activated (not currentIndexChanged) to avoid spurious emits
        self.language_combo.activated.connect(self._on_language_selected)
        layout.addWidget(self.language_combo)

    def _load_logo(self, theme: str) -> None:
        """Load logo image and display as QPixmap.

        Args:
            theme (str): "dark" or "light" theme selection.
        """
        logo_filename = "sape-logo-h-dark.png" if theme == "dark" else "sape-logo-h-light.png"
        # Path: src/gui/components/header.py -> up 4 levels to root -> gui_resources/logos
        logo_path = Path(__file__).parent.parent.parent.parent / "gui_resources" / "logos" / logo_filename

        if logo_path.exists():
            logo_pixmap = QPixmap(str(logo_path))
            if not logo_pixmap.isNull():
                logger.info(f"Loaded logo: {logo_filename}")
                self.logo_label.setPixmap(logo_pixmap)
            else:
                logger.error(f"Failed to load pixmap: {logo_path}")
                self.logo_label.setText("SAPÉ")
        else:
            logger.error(f"Logo file not found: {logo_path}")
            self.logo_label.setText("SAPÉ")

    def _update_title_color(self, theme: str) -> None:
        """Update title text color based on theme.

        Args:
            theme (str): "dark" or "light" theme selection.
        """
        text_color = DARK_TEXT_PRIMARY if theme == "dark" else LIGHT_TEXT_PRIMARY
        self.title_label.setStyleSheet(f"color: {text_color.name()};")

    def _toggle_theme(self):
        """Toggle between dark and light theme."""
        new_theme = self.app.theme_manager.toggle_theme()
        self.current_theme = new_theme
        self._load_logo(new_theme)  # Update logo when theme changes
        self._update_title_color(new_theme)  # Update title text color when theme changes
        self._update_theme_icon(new_theme)  # Update theme button icon
        self.theme_toggled.emit(new_theme)

    def _update_theme_icon(self, theme: str) -> None:
        """Load and set theme icon (sun when dark mode = click for light, moon when light mode = click for dark).

        Args:
            theme (str): "dark" or "light" theme selection.
        """
        icon_filename = "sun.svg" if theme == "dark" else "moon.svg"
        # Path: src/gui/components/header.py -> up 4 levels to root -> gui_resources/icons
        icon_path = Path(__file__).parent.parent.parent.parent / "gui_resources" / "icons" / icon_filename

        if icon_path.exists():
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                logger.info(f"Loaded theme icon: {icon_filename}")
                self.theme_btn.setIcon(icon)
                self.theme_btn.setIconSize(QSize(32, 32))
            else:
                logger.error(f"Failed to load icon: {icon_path}")
                self.theme_btn.setText("?" if theme == "dark" else "!")
        else:
            logger.error(f"Icon file not found: {icon_path}")
            self.theme_btn.setText("?" if theme == "dark" else "!")

    def _get_flag_icon_cached(self, lang_code: str) -> QIcon | None:
        """Get flag icon for language, with caching for performance.

        Loads flag icons once and caches them to avoid repeated file I/O
        when dealing with 18 languages.

        Args:
            lang_code (str): Language code (e.g., "en-US", "zh-CN")

        Returns:
            QIcon if loaded successfully, None if not found or failed to load.
        """
        # Return cached icon if available
        if lang_code in self.flag_icon_cache:
            return self.flag_icon_cache[lang_code]

        # Get flag path from LanguageRegistry
        flag_path = LanguageRegistry.get_flag_path(lang_code)

        if flag_path and flag_path.exists():
            icon = QIcon(str(flag_path))
            if not icon.isNull():
                logger.debug(f"Loaded flag for {lang_code}")
                # Cache for future use
                self.flag_icon_cache[lang_code] = icon
                return icon
            else:
                logger.error(f"Failed to load icon from {flag_path}")
        else:
            logger.debug(f"Flag file not found for {lang_code}")

        # Cache None so we don't retry
        self.flag_icon_cache[lang_code] = None
        return None

    def update_theme_button(self, theme: str):
        """Update theme button, logo, and title text to reflect current theme.

        Args:
            theme (str): "dark" or "light"
        """
        self.current_theme = theme
        self._load_logo(theme)  # Update logo
        self._update_title_color(theme)  # Update title text color
        self._update_theme_icon(theme)

    def set_logo(self, theme: str):
        """Set the logo based on theme.

        Args:
            theme (str): "dark" or "light" theme selection.
        """
        self._load_logo(theme)

    def _on_language_selected(self, index: int):
        """Handle language selection from combo box."""
        language_code = self.language_combo.itemData(index)
        self.language_changed.emit(language_code)

    def update_language_button(self, language: str):
        """Update language combo box to reflect current language.

        Args:
            language (str): Language code (e.g., "en-US", "es-ES")
        """
        index = self.language_combo.findData(language)
        if index >= 0:
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(index)
            self.language_combo.blockSignals(False)
