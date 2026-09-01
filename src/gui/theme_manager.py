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

"""Theme persistence and management for SAPÉ f-Win MCP GUI.

Handles saving/loading theme preference to ~/.sape/config.json
and emits signals for theme changes across the application.
"""

import json
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ThemeManager(QObject):
    """Manages theme persistence and application-wide theme signals.

    Saves theme preference to ~/.sape/config.json on every change.
    Loads theme on startup from config file.
    Emits signals when theme changes so all components can update.
    """

    # Signal emitted when theme changes: emits "dark" or "light"
    theme_changed = pyqtSignal(str)

    def __init__(self):
        """Initialize theme manager and load saved theme."""
        super().__init__()

        # Setup config directory and file
        self.config_dir = Path.home() / ".sape"
        self.config_file = self.config_dir / "config.json"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load saved theme or default to dark
        self._current_theme = self._load_theme()
        logger.info(f"Theme manager initialized with theme: {self._current_theme}")

    @property
    def current_theme(self) -> str:
        """Get the currently active theme.

        Returns:
            str: "dark" or "light"
        """
        return self._current_theme

    def set_theme(self, theme: str) -> None:
        """Set theme and persist to config file.

        Args:
            theme (str): "dark" or "light"
        """
        if theme not in ("dark", "light"):
            logger.warning(f"Invalid theme: {theme}. Using 'dark' instead.")
            theme = "dark"

        if theme == self._current_theme:
            logger.debug(f"Theme already set to: {theme}")
            return

        self._current_theme = theme
        self._save_theme(theme)
        self.theme_changed.emit(theme)
        logger.info(f"Theme changed and persisted: {theme}")

    def _load_theme(self) -> str:
        """Load theme from config file.

        Returns:
            str: Saved theme ("dark" or "light"), or "dark" if not found.
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    theme = config.get('theme', 'dark')
                    if theme in ('dark', 'light'):
                        logger.info(f"Loaded theme from config: {theme}")
                        return theme
            else:
                logger.info("Config file not found, using default theme: dark")
        except Exception as e:
            logger.error(f"Error loading theme from config: {e}")

        return "dark"

    def _save_theme(self, theme: str) -> None:
        """Save theme to config file.

        Args:
            theme (str): "dark" or "light"
        """
        try:
            # Load existing config or create new one
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # Update theme
            config['theme'] = theme

            # Write back to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"Theme persisted to {self.config_file}: {theme}")
        except Exception as e:
            logger.error(f"Error saving theme to config: {e}")

    def toggle_theme(self) -> str:
        """Toggle between dark and light theme.

        Returns:
            str: The new theme ("dark" or "light")
        """
        new_theme = "light" if self._current_theme == "dark" else "dark"
        self.set_theme(new_theme)
        return new_theme
