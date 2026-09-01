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

"""Settings page."""

import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QGroupBox, QCheckBox,
    QScrollArea, QPlainTextEdit
)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from ..i18n import translate
from ..styles.sape_design_tokens import (
    LIGHT_TEXT_PRIMARY, LIGHT_TEXT_SECONDARY, LIGHT_SURFACE, LIGHT_BORDER,
    DARK_TEXT_PRIMARY, DARK_TEXT_SECONDARY, DARK_SURFACE, DARK_BORDER,
    FONT_MONO, SPACING_MD, SPACING_LG, SAPE_PRIMARY
)
from ..dialogs.mcp_config_dialog import MCPConfigDialog
from ..._version import __version__

logger = logging.getLogger(__name__)


class SettingsPage(QWidget):
    """Application settings."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.app = main_window.app
        self.config_manager = self.app.config_manager
        self.copy_button_original_text = ""
        self.copy_timer = None
        self.showing_details = False
        self.config_gen = None
        self.client_config_str = ""
        self.details_json_str = ""
        self.config_error = ""

        # Create scroll area to handle content overflow
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        # Create main widget for scroll area
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title (will be updated by language changes)
        self.title = QLabel()
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        self.title.setFont(title_font)
        layout.addWidget(self.title)

        # Subtitle (will be updated by language changes)
        self.subtitle = QLabel()
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_font.setItalic(True)
        self.subtitle.setFont(subtitle_font)
        layout.addWidget(self.subtitle)

        # ===== Configuration Section (MCP JSON) =====
        self.config_group = QGroupBox()
        self.config_group.setFont(QFont("", 10, QFont.Weight.Bold))
        config_layout = QVBoxLayout()

        # Smart Setup Button
        setup_button_layout = QHBoxLayout()
        self.setup_mcp_button = QPushButton()
        self.setup_mcp_button.setMaximumWidth(250)
        self.setup_mcp_button.setStyleSheet(f"background-color: {SAPE_PRIMARY.name()}; color: white; font-weight: bold; padding: 8px;")
        self.setup_mcp_button.clicked.connect(self._on_setup_mcp_config)
        setup_button_layout.addWidget(self.setup_mcp_button)
        setup_button_layout.addStretch()
        config_layout.addLayout(setup_button_layout)

        config_layout.addSpacing(12)

        self.config_desc = QLabel()
        self.config_desc.setWordWrap(True)
        config_layout.addWidget(self.config_desc)

        # JSON display area
        self.config_text = QPlainTextEdit()
        self.config_text.setReadOnly(True)
        self.config_text.setMinimumHeight(280)
        config_layout.addWidget(self.config_text)

        # Copy button, and the reference view the configuration used to hide in
        copy_button_layout = QHBoxLayout()
        self.copy_button = QPushButton()
        self.copy_button.setMaximumWidth(150)
        self.copy_button.clicked.connect(self._on_copy_config)
        copy_button_layout.addWidget(self.copy_button)
        self.details_button = QPushButton()
        self.details_button.setMaximumWidth(200)
        self.details_button.clicked.connect(self._on_toggle_details)
        copy_button_layout.addWidget(self.details_button)
        copy_button_layout.addStretch()
        config_layout.addLayout(copy_button_layout)

        # After the buttons: the loader enables or disables Copy by what it finds
        self._load_config_json()

        self.config_group.setLayout(config_layout)
        layout.addWidget(self.config_group)

        # ===== Theme Section =====
        self.theme_group = QGroupBox()
        self.theme_group.setFont(QFont("", 10, QFont.Weight.Bold))
        theme_layout = QVBoxLayout()

        self.theme_desc = QLabel()
        theme_layout.addWidget(self.theme_desc)

        theme_buttons = QHBoxLayout()

        self.light_btn = QPushButton()
        self.light_btn.setMaximumWidth(150)
        self.light_btn.clicked.connect(lambda: self._on_theme_light())
        theme_buttons.addWidget(self.light_btn)

        self.dark_btn = QPushButton()
        self.dark_btn.setMaximumWidth(150)
        self.dark_btn.clicked.connect(lambda: self._on_theme_dark())
        theme_buttons.addWidget(self.dark_btn)

        theme_buttons.addStretch()
        theme_layout.addLayout(theme_buttons)
        self.theme_group.setLayout(theme_layout)
        layout.addWidget(self.theme_group)

        # ===== Server Section =====
        self.server_group = QGroupBox()
        self.server_group.setFont(QFont("", 10, QFont.Weight.Bold))
        server_layout = QVBoxLayout()

        self.server_desc = QLabel()
        self.server_desc.setWordWrap(True)
        server_layout.addWidget(self.server_desc)

        self.server_info = QLabel()
        self.server_info.setWordWrap(True)
        server_layout.addWidget(self.server_info)

        self.server_group.setLayout(server_layout)
        layout.addWidget(self.server_group)

        # ===== Database Section =====
        self.db_group = QGroupBox()
        self.db_group.setFont(QFont("", 10, QFont.Weight.Bold))
        db_layout = QVBoxLayout()

        self.db_path_label = QLabel(f"Permission Database: {self.main_window.server.permissions.db_path}")
        self.db_path_label.setStyleSheet("font-family: monospace; font-size: 9pt;")
        self.db_path_label.setWordWrap(True)
        db_layout.addWidget(self.db_path_label)

        self.base_dir_label = QLabel(
            f"Base Directory: {self.main_window.server.base_dir or '(current working directory)'}"
        )
        self.base_dir_label.setStyleSheet("font-family: monospace; font-size: 9pt;")
        self.base_dir_label.setWordWrap(True)
        db_layout.addWidget(self.base_dir_label)

        self.db_group.setLayout(db_layout)
        layout.addWidget(self.db_group)

        # ===== Info Section =====
        self.info_group = QGroupBox()
        info_layout = QVBoxLayout()

        self.info_text = QLabel()
        self.info_text.setWordWrap(True)
        info_layout.addWidget(self.info_text)

        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        layout.addStretch()

        # Add scroll widget to scroll area
        scroll_area.setWidget(scroll_widget)
        outer_layout.addWidget(scroll_area)

        # Connect language and theme change signals
        if self.app:
            self.app.language_changed.connect(self._update_language)
            self.app.theme_manager.theme_changed.connect(self._update_theme_colors)

        # Initial language and theme update
        self._update_language(self.app.current_language if self.app else "en-US")
        self._update_theme_colors(self.app.current_theme if self.app else "light")

    def _load_config_json(self) -> None:
        """Load the configuration this box offers for copying.

        What is shown is what a client configuration file can hold verbatim,
        nothing more. There is deliberately no invented fallback: a placeholder
        naming a bare ``python`` and a relative ``main.py`` is the failure
        ``tests/test_generated_config.py`` exists to prevent — it looks
        plausible, and starts either nothing or the GUI. When detection fails,
        the box says so and points at the wizard, which can explain why.
        """
        self.config_error = ""
        self.details_json_str = ""

        try:
            from src.config_json_generator import ConfigJSONGenerator
            self.config_gen = ConfigJSONGenerator(self.app.server)
            self.client_config_str = self.config_gen.to_client_config_string()
        except Exception as exc:
            logger.warning(f"Cannot generate client configuration: {exc}")
            self.config_gen = None
            self.client_config_str = ""
            self.config_error = str(exc)

        self._refresh_config_text()

    def _refresh_config_text(self, language: str | None = None) -> None:
        """Show the configuration, the reference details, or the error.

        Takes the language rather than reading it back off the application, so
        a language change renders in the language it announced.
        """
        if language is None:
            language = self.app.current_language if self.app else "en-US"

        if self.showing_details:
            if not self.details_json_str and self.config_gen is not None:
                try:
                    self.details_json_str = self.config_gen.to_json_string()
                except Exception as exc:
                    logger.warning(f"Cannot generate configuration details: {exc}")
                    self.details_json_str = str(exc)
            self.config_text.setPlainText(self.details_json_str)
            self.copy_button.setEnabled(True)
            return

        if self.client_config_str:
            self.config_text.setPlainText(self.client_config_str)
            self.copy_button.setEnabled(True)
        else:
            message = translate("settings.config_unavailable", language)
            if self.config_error:
                message = f"{message}\n\n{self.config_error}"
            self.config_text.setPlainText(message)
            # Nothing here is pasteable, so offer nothing to paste.
            self.copy_button.setEnabled(False)

    def _on_toggle_details(self) -> None:
        """Swap the box between the configuration and the reference details."""
        self.showing_details = not self.showing_details
        self._refresh_config_text()
        self._update_config_labels(self.app.current_language if self.app else "en-US")

    def _on_copy_config(self) -> None:
        """Copy configuration JSON to clipboard and show feedback."""
        from PyQt6.QtGui import QGuiApplication

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.config_text.toPlainText())

        # Show "Copied!" feedback for 2 seconds
        self.copy_button_original_text = self.copy_button.text()
        self.copy_button.setText(translate("settings.copy_success", self.app.current_language))
        self.copy_button.setEnabled(False)

        # Reset button text after 2 seconds
        if self.copy_timer:
            self.copy_timer.stop()
        self.copy_timer = QTimer()
        self.copy_timer.setSingleShot(True)
        self.copy_timer.timeout.connect(self._reset_copy_button)
        self.copy_timer.start(2000)

    def _reset_copy_button(self) -> None:
        """Reset copy button to original state."""
        self.copy_button.setText(self.copy_button_original_text)
        self.copy_button.setEnabled(True)
        if self.copy_timer:
            self.copy_timer.stop()

    def _update_language(self, language: str) -> None:
        """Update settings page text for the specified language."""
        self.title.setText(f"⚙️ {translate('settings.title', language)}")
        self.subtitle.setText(translate("settings.subtitle", language))

        self._update_config_labels(language)
        # The box can itself hold translated text — the "no configuration" message
        self._refresh_config_text(language)

        self.theme_group.setTitle(translate("settings.appearance_group", language))
        self.theme_desc.setText(translate("settings.theme_desc", language))
        self.light_btn.setText(translate("settings.light_theme", language))
        self.dark_btn.setText(translate("settings.dark_theme", language))

        self.server_group.setTitle(translate("settings.server_group", language))
        self.server_desc.setText(translate("settings.server_desc", language))
        self.server_info.setText(translate("settings.server_info", language))

        self.db_group.setTitle(translate("settings.data_group", language))
        # Update label prefixes for data group
        db_prefix = translate("settings.database_label", language)
        base_prefix = translate("settings.base_dir_label", language)
        self.db_path_label.setText(f"{db_prefix} {self.main_window.server.permissions.db_path}")
        self.base_dir_label.setText(f"{base_prefix} {self.main_window.server.base_dir or '(current working directory)'}")

        self.info_group.setTitle(translate("settings.about_group", language))
        # The version is substituted, never translated: this string used to carry
        # a hardcoded one and drifted two releases behind src/_version.py.
        self.info_text.setText(
            translate("settings.about_text", language).replace("{version}", __version__)
        )

    def _update_config_labels(self, language: str) -> None:
        """Label the configuration section for the view currently on screen.

        The description travels with the view: only one of the two is something
        to paste into a client, and the box must not claim otherwise.
        """
        self.setup_mcp_button.setText(translate("settings.setup_mcp_button", language))
        self.config_group.setTitle(translate("settings.config_group", language))
        self.config_desc.setText(translate(
            "settings.config_details_desc" if self.showing_details else "settings.config_desc",
            language,
        ))
        self.details_button.setText(translate(
            "settings.config_show_config" if self.showing_details else "settings.config_show_details",
            language,
        ))
        self.copy_button_original_text = translate("settings.copy_button", language)
        self.copy_button.setText(self.copy_button_original_text)

    def _on_theme_light(self):
        """Switch to light theme."""
        self.main_window.app.theme_manager.set_theme("light")
        self.main_window.header.update_theme_button("light")

    def _on_theme_dark(self):
        """Switch to dark theme."""
        self.main_window.app.theme_manager.set_theme("dark")
        self.main_window.header.update_theme_button("dark")

    def _on_setup_mcp_config(self):
        """Open MCP configuration setup dialog."""
        dialog = MCPConfigDialog(self, self.app)
        dialog.exec()

    def _update_theme_colors(self, theme: str) -> None:
        """Update text colors based on current theme for WCAG AA contrast."""
        is_dark = theme == "dark"
        text_color = DARK_TEXT_PRIMARY if is_dark else LIGHT_TEXT_PRIMARY
        bg_color = DARK_SURFACE if is_dark else LIGHT_SURFACE
        border_color = DARK_BORDER if is_dark else LIGHT_BORDER

        # Update subtitle and text-based labels
        self.subtitle.setStyleSheet(f"color: {text_color.name()};")
        self.server_info.setStyleSheet(f"color: {text_color.name()}; line-height: 1.6;")
        self.db_path_label.setStyleSheet(f"font-family: monospace; font-size: 9pt; color: {text_color.name()};")
        self.base_dir_label.setStyleSheet(f"font-family: monospace; font-size: 9pt; color: {text_color.name()};")
        self.info_text.setStyleSheet(f"color: {text_color.name()};")

        # Update Configuration section JSON display
        self.config_text.setStyleSheet(
            f"QPlainTextEdit {{\n"
            f"  background-color: {bg_color.name()};\n"
            f"  color: {text_color.name()};\n"
            f"  border: 1px solid {border_color.name()};\n"
            f"  border-radius: 4px;\n"
            f"  font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace;\n"
            f"  font-size: 10pt;\n"
            f"  padding: 8px;\n"
            f"}}\n"
        )
