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

"""PyQt6 Application setup and main entry point."""

import sys
import logging
import uuid
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from .main_window import MainWindow
from .theme_manager import ThemeManager
from .language_manager import LanguageManager
from .config_manager import ConfigManager
from .styles.sape_design_tokens import DARK_THEME_PALETTE, LIGHT_THEME_PALETTE
from .i18n import get_supported_languages
from src.log_store import LogStore

logger = logging.getLogger(__name__)


class SAPEApplication(QApplication):
    """Main PyQt6 application for SAPÉ f-MCP."""

    # Signals
    theme_changed = pyqtSignal(str)  # "light" or "dark"
    language_changed = pyqtSignal(str)  # "en-US" or "es-ES"

    def __init__(self, server, transport="stdio"):
        super().__init__(sys.argv)

        # Set application icon (affects taskbar and window title bar on Windows)
        # Use dark.ico (multi-resolution) for taskbar display
        icon_path = Path(__file__).parent.parent.parent / "gui_resources" / "icons" / "dark.ico"
        if icon_path.exists():
            from PyQt6.QtGui import QIcon
            icon = QIcon(str(icon_path))
            self.setWindowIcon(icon)

            # On Windows, also set app-level icon for taskbar (ctypes workaround)
            if sys.platform == "win32":
                try:
                    import ctypes
                    # Set Windows-specific icon association
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(u"SAPE.f-MCP")
                    logger.info("Windows app model ID set for taskbar icon")
                except Exception as e:
                    logger.debug(f"Could not set app model ID: {e}")

            logger.info(f"Application icon set: {icon_path}")
        else:
            logger.warning(f"Icon not found: {icon_path}")

        self.server = server
        self.transport = transport

        # Create session ID for this application instance
        self.session_id = str(uuid.uuid4())

        # Initialize SQLite log store
        self.log_store = LogStore()

        # Wipe all logs on startup and trim if needed
        self.log_store.delete_all()
        self.log_store.trim_if_needed()

        # Log application startup
        try:
            self.log_store.log_tool(
                self.session_id,
                "app-startup",
                {},
                "GUI initialized",
                None
            )
        except Exception as e:
            logger.warning(f"Failed to log app startup: {e}")

        # Initialize config manager (unified config for all settings)
        self.config_manager = ConfigManager()

        # Initialize theme manager (loads saved theme from ~/.sape/config.json)
        self.theme_manager = ThemeManager()
        self.current_theme = self.theme_manager.current_theme

        # Initialize language manager (loads saved language from ~/.sape/config.json)
        self.language_manager = LanguageManager()
        self.current_language = self.language_manager.current_language

        # Connect theme manager signals
        self.theme_manager.theme_changed.connect(self._on_theme_changed)

        # Connect language manager signals
        self.language_manager.language_changed.connect(self._on_language_changed_internal)

        # Create main window
        self.main_window = MainWindow(self.server, self.transport, self)

        # Apply saved theme and language
        self.set_theme(self.current_theme)
        # Don't need to emit here, will be done when header initializes

        logger.info("SAPÉ f-MCP GUI initialized")

    def set_theme(self, theme: str):
        """Switch between light and dark theme."""
        if theme == "dark":
            palette = DARK_THEME_PALETTE
            stylesheet_file = "application.qss"
        else:
            palette = LIGHT_THEME_PALETTE
            stylesheet_file = "application_light.qss"

        # Load stylesheet
        stylesheet_path = Path(__file__).parent / "styles" / stylesheet_file
        if stylesheet_path.exists():
            with open(stylesheet_path, 'r', encoding='utf-8') as f:
                stylesheet = f.read()
            self.setStyleSheet(stylesheet)
        else:
            logger.warning(f"Stylesheet not found: {stylesheet_path}")

        self.setPalette(palette)
        self.current_theme = theme
        logger.info(f"Theme changed to: {theme}")

    def set_language(self, language: str):
        """Change the application language and persist to config.

        Args:
            language (str): Language code (e.g., "en-US", "es-ES")
        """
        # Use language manager to set and persist
        self.language_manager.set_language(language)

    def _on_language_changed_internal(self, language: str):
        """Internal handler for language manager changes (from config or set_language)."""
        self.current_language = language
        self.language_changed.emit(language)
        logger.info(f"Application language changed to: {language}")

    def _on_theme_changed(self, theme: str):
        """Internal handler for theme manager changes."""
        self.set_theme(theme)
        # Notify header to update button state
        if hasattr(self.main_window, 'header'):
            self.main_window.header.update_theme_button(theme)

    def run(self, splash=None):
        """Run the application."""
        self.main_window.show()

        # Close splash screen if provided
        if splash:
            splash.close()

        return self.exec()
