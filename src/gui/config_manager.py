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

"""Configuration manager for SAPÉ f-MCP GUI.

Handles saving/loading all application preferences to ~/.sape/config.json including:
- Language preference
- Theme preference (light/dark)
- Minimize-on-startup preference
- UI preferences (column widths, etc.)
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ConfigManager:
    """Unified configuration manager for all application settings.

    Loads and saves all app config to ~/.sape/config.json in a structured format.
    """

    # Default configuration structure
    DEFAULT_CONFIG = {
        "language": "en-US",
        "theme": "light",
        "minimize_on_startup": False,
        "permissions_table_columns": {
            "0": 300,
            "1": 100,
            "2": 150,
            "3": 100,
            "4": 80,
            "5": 80,
        },
    }

    def __init__(self):
        """Initialize config manager and load existing configuration."""
        self.config_dir = Path.home() / ".sape"
        self.config_file = self.config_dir / "config.json"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self._config = self._load_config()
        logger.info(f"Config manager initialized with config from {self.config_file}")

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from file, merging with defaults.

        Returns:
            dict: Complete configuration with defaults merged in.
        """
        config = self.DEFAULT_CONFIG.copy()

        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    # Merge file config into defaults (file config takes precedence)
                    config.update(file_config)
                    # Preserve table columns separately
                    if "permissions_table_columns" in file_config:
                        config["permissions_table_columns"] = file_config["permissions_table_columns"]
                    logger.info("Loaded configuration from file")
            else:
                logger.info("Config file not found, using defaults")
        except Exception as e:
            logger.error(f"Error loading configuration: {e}. Using defaults.")

        # Clean up deprecated auto-start fields from existing configs
        self._cleanup_deprecated_fields(config)

        return config

    def _cleanup_deprecated_fields(self, config: dict[str, Any]) -> None:
        """Remove deprecated configuration fields and persist changes.

        Removes deprecated auto-start fields (auto_start_gui, auto_start_server)
        from config if present, and saves the cleaned config back to file.

        Args:
            config (dict): Configuration dictionary to clean
        """
        deprecated_fields = ["auto_start_gui", "auto_start_server"]
        cleaned = False

        for field in deprecated_fields:
            if field in config:
                del config[field]
                cleaned = True
                logger.info(f"Removed deprecated config field: {field}")

        # If we cleaned any fields, persist the change
        if cleaned:
            self._config = config
            self._save_config()

    def _save_config(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")

    # ================== Language Settings ==================

    def get_language(self) -> str:
        """Get saved language preference.

        Returns:
            str: Language code (e.g., "en-US", "es-ES")
        """
        return self._config.get("language", "en-US")

    def set_language(self, language: str) -> None:
        """Set and persist language preference.

        Args:
            language (str): Language code (e.g., "en-US", "es-ES")
        """
        self._config["language"] = language
        self._save_config()
        logger.info(f"Language preference saved: {language}")

    # ================== Theme Settings ==================

    def get_theme(self) -> str:
        """Get saved theme preference.

        Returns:
            str: Theme name ("light" or "dark")
        """
        return self._config.get("theme", "light")

    def set_theme(self, theme: str) -> None:
        """Set and persist theme preference.

        Args:
            theme (str): Theme name ("light" or "dark")
        """
        self._config["theme"] = theme
        self._save_config()
        logger.info(f"Theme preference saved: {theme}")

    # ================== Startup Settings ==================

    def get_minimize_on_startup(self) -> bool:
        """Get minimize-on-startup preference.

        Returns:
            bool: True if window should start minimized
        """
        return self._config.get("minimize_on_startup", False)

    def set_minimize_on_startup(self, enabled: bool) -> None:
        """Set and persist minimize-on-startup preference.

        Args:
            enabled (bool): True to minimize window on startup
        """
        self._config["minimize_on_startup"] = enabled
        self._save_config()
        logger.info(f"Minimize on startup preference saved: {enabled}")

    # ================== UI Settings ==================

    def get_permissions_table_columns(self) -> dict[str, int]:
        """Get saved permissions table column widths.

        Returns:
            dict: Mapping of column index to width
        """
        return self._config.get("permissions_table_columns", self.DEFAULT_CONFIG["permissions_table_columns"].copy())

    def set_permissions_table_columns(self, columns: dict[str, int]) -> None:
        """Set and persist permissions table column widths.

        Args:
            columns (dict): Mapping of column index to width
        """
        self._config["permissions_table_columns"] = columns
        self._save_config()
        logger.debug(f"Permissions table column widths saved")

    # ================== Generic Key-Value Access ==================

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key.

        Args:
            key (str): Configuration key
            default: Default value if key not found

        Returns:
            Any: Configuration value or default
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set and persist a config value.

        Args:
            key (str): Configuration key
            value: Value to set
        """
        self._config[key] = value
        self._save_config()
        logger.debug(f"Config setting saved: {key}={value}")

    def get_all(self) -> dict[str, Any]:
        """Get all configuration values.

        Returns:
            dict: Complete configuration dictionary
        """
        return self._config.copy()
