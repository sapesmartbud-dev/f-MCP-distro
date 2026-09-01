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

"""Language persistence and management for SAPÉ f-Win MCP GUI.

Handles saving/loading language preference to ~/.sape/config.json
and emits signals for language changes across the application.
"""

import json
import locale
import logging
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from .i18n import get_supported_languages

logger = logging.getLogger(__name__)


class LanguageManager(QObject):
    """Manages language persistence and application-wide language signals.

    Saves language preference to ~/.sape/config.json on every change.
    Loads language on startup from config file.
    Emits signals when language changes so all components can update.
    """

    # Signal emitted when language changes: emits language code (e.g., "en-US")
    language_changed = pyqtSignal(str)

    def __init__(self):
        """Initialize language manager and load saved language."""
        super().__init__()

        # Setup config directory and file
        self.config_dir = Path.home() / ".sape"
        self.config_file = self.config_dir / "config.json"

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load saved language or auto-detect system language on first launch
        self._current_language = self._load_language()

        # If no saved language found, detect system language and save it
        if self._current_language == "en-US" and not self.config_file.exists():
            auto_detected = self.detect_system_language()
            if auto_detected != "en-US":
                self._current_language = auto_detected
                self._save_language(auto_detected)
                logger.info(f"Auto-detected system language: {auto_detected}")

        logger.info(f"Language manager initialized with language: {self._current_language}")

    def detect_system_language(self) -> str:
        """Detect system language and return closest supported language code.

        Attempts to match the system locale to supported languages with fallback logic:
        1. Exact match (e.g., de-DE → de-DE)
        2. Language code match (e.g., pt-PT → pt-BR for Portuguese)
        3. Fallback to en-US if no match found

        Returns:
            str: Language code (e.g., "en-US", "es-ES") of a supported language.

        Examples:
            - System: de-DE (German, Germany) → Returns 'de-DE' (exact match)
            - System: pt-PT (Portuguese, Portugal) → Returns 'pt-BR' (language match)
            - System: ja-JP (Japanese) → Returns 'en-US' (unsupported, fallback)
        """
        try:
            # Get system default locale in format like 'de_DE', 'pt_PT', None
            system_locale = locale.getdefaultlocale()[0]

            if not system_locale:
                logger.debug("No system locale detected, using en-US")
                return "en-US"

            # Normalize: de_DE → de-DE (replace underscores with hyphens)
            normalized = system_locale.replace('_', '-')
            logger.debug(f"System locale detected: {system_locale} → normalized: {normalized}")

            # Get supported languages
            supported = get_supported_languages()
            supported_codes = list(supported.keys())

            # Check 1: Exact match
            if normalized in supported_codes:
                logger.info(f"Exact match found for system locale: {normalized}")
                return normalized

            # Check 2: Language code match (first part before hyphen)
            # E.g., 'pt-PT' should match 'pt-BR' (Portuguese variants)
            lang_part = normalized.split('-')[0]  # 'de-DE' → 'de'
            for supported_code in supported_codes:
                if supported_code.startswith(lang_part + '-'):
                    logger.info(f"Language match found: {normalized} → {supported_code}")
                    return supported_code

            # Check 3: Fallback to en-US
            logger.warning(f"No supported language found for system locale: {normalized}, using en-US")
            return "en-US"

        except Exception as e:
            logger.error(f"Error detecting system language: {e}, using en-US")
            return "en-US"

    @property
    def current_language(self) -> str:
        """Get the currently active language.

        Returns:
            str: Language code (e.g., "en-US", "es-ES")
        """
        return self._current_language

    def set_language(self, language: str) -> None:
        """Set language and persist to config file.

        Args:
            language (str): Language code (e.g., "en-US", "es-ES")
        """
        supported = get_supported_languages()
        if language not in supported:
            logger.warning(f"Invalid language: {language}. Using 'en-US' instead.")
            language = "en-US"

        if language == self._current_language:
            logger.debug(f"Language already set to: {language}")
            return

        self._current_language = language
        self._save_language(language)
        self.language_changed.emit(language)
        logger.info(f"Language changed and persisted: {language}")

    def _load_language(self) -> str:
        """Load language from config file.

        Returns:
            str: Saved language code, or "en-US" if not found.
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    language = config.get('language', 'en-US')
                    supported = get_supported_languages()
                    if language in supported:
                        logger.info(f"Loaded language from config: {language}")
                        return language
            else:
                logger.info("Config file not found, using default language: en-US")
        except Exception as e:
            logger.error(f"Error loading language from config: {e}")

        return "en-US"

    def _save_language(self, language: str) -> None:
        """Save language to config file.

        Args:
            language (str): Language code (e.g., "en-US", "es-ES")
        """
        try:
            # Load existing config or create new one
            config = {}
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # Update language
            config['language'] = language

            # Write back to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.info(f"Language persisted to {self.config_file}: {language}")
        except Exception as e:
            logger.error(f"Error saving language to config: {e}")
