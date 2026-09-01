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

"""Language registry with metadata for all 18 supported languages.

This module provides a centralized registry of supported languages with their
native names, English names, geographic regions, and flag file mappings.

The registry is used by the GUI language selector, legal document loader,
and any other components that need language metadata or validation.
"""

from __future__ import annotations

from pathlib import Path


class LanguageRegistry:
    """Registry of all 18 supported languages with metadata."""

    LANGUAGES = {
        'en-US': {
            'native': 'English',
            'english': 'English',
            'region': 'North America',
            'flag_file': 'england.png',
        },
        'es-ES': {
            'native': 'Español',
            'english': 'Spanish',
            'region': 'Western Europe',
            'flag_file': 'spain.png',
        },
        'fr-FR': {
            'native': 'Français',
            'english': 'French',
            'region': 'Western Europe',
            'flag_file': 'france.png',
        },
        'de-DE': {
            'native': 'Deutsch',
            'english': 'German',
            'region': 'Western Europe',
            'flag_file': 'germany.png',
        },
        'it-IT': {
            'native': 'Italiano',
            'english': 'Italian',
            'region': 'Western Europe',
            'flag_file': 'italy.png',
        },
        'pt-BR': {
            'native': 'Português',
            'english': 'Portuguese',
            'region': 'South America',
            'flag_file': 'brazil.png',
        },
        'nl-NL': {
            'native': 'Nederlands',
            'english': 'Dutch',
            'region': 'Western Europe',
            'flag_file': 'netherlands.png',
        },
        'sv-SE': {
            'native': 'Svenska',
            'english': 'Swedish',
            'region': 'Northern Europe',
            'flag_file': 'sweden.png',
        },
        'da-DK': {
            'native': 'Dansk',
            'english': 'Danish',
            'region': 'Northern Europe',
            'flag_file': 'denmark.png',
        },
        'fi-FI': {
            'native': 'Suomi',
            'english': 'Finnish',
            'region': 'Northern Europe',
            'flag_file': 'finland.png',
        },
        'pl-PL': {
            'native': 'Polski',
            'english': 'Polish',
            'region': 'Eastern Europe',
            'flag_file': 'poland.png',
        },
        'cs-CZ': {
            'native': 'Čeština',
            'english': 'Czech',
            'region': 'Eastern Europe',
            'flag_file': 'czech.png',
        },
        'sk-SK': {
            'native': 'Slovenčina',
            'english': 'Slovak',
            'region': 'Eastern Europe',
            'flag_file': 'slovakia.png',
        },
        'hu-HU': {
            'native': 'Magyar',
            'english': 'Hungarian',
            'region': 'Eastern Europe',
            'flag_file': 'hungary.png',
        },
        'ro-RO': {
            'native': 'Română',
            'english': 'Romanian',
            'region': 'Eastern Europe',
            'flag_file': 'romania.png',
        },
        'ru-RU': {
            'native': 'Русский',
            'english': 'Russian',
            'region': 'Eastern Europe',
            'flag_file': 'russia.png',
        },
        'is-IS': {
            'native': 'Íslenska',
            'english': 'Icelandic',
            'region': 'Northern Europe',
            'flag_file': 'iceland.png',
        },
        'zh-CN': {
            'native': '中文',
            'english': 'Chinese (Simplified)',
            'region': 'Asia',
            'flag_file': 'china.png',
        },
    }

    @classmethod
    def get_all_languages_sorted(cls) -> list[tuple[str, str]]:
        """Return list of (code, native_name) tuples sorted alphabetically by native name.

        Returns:
            List of (language_code, native_name) tuples sorted by native language name.
            Example: [('zh-CN', '中文'), ('cs-CZ', 'Čeština'), ('da-DK', 'Dansk'), ...]

        Example:
            >>> codes_names = LanguageRegistry.get_all_languages_sorted()
            >>> codes_names[0]
            ('zh-CN', '中文')
        """
        items = [(code, meta['native']) for code, meta in cls.LANGUAGES.items()]
        return sorted(items, key=lambda x: x[1])

    @classmethod
    def get_native_name(cls, lang_code: str) -> str:
        """Get native language name for display.

        Args:
            lang_code: Language code (e.g., 'es-ES', 'en-US')

        Returns:
            Native language name, or the lang_code itself if not found.
            Example: 'es-ES' -> 'Español'

        Example:
            >>> LanguageRegistry.get_native_name('es-ES')
            'Español'
        """
        return cls.LANGUAGES.get(lang_code, {}).get('native', lang_code)

    @classmethod
    def get_english_name(cls, lang_code: str) -> str:
        """Get English language name for display.

        Args:
            lang_code: Language code (e.g., 'es-ES', 'en-US')

        Returns:
            English name of the language, or the lang_code itself if not found.
            Example: 'es-ES' -> 'Spanish'

        Example:
            >>> LanguageRegistry.get_english_name('es-ES')
            'Spanish'
        """
        return cls.LANGUAGES.get(lang_code, {}).get('english', lang_code)

    @classmethod
    def get_region(cls, lang_code: str) -> str:
        """Get geographic region for the language.

        Args:
            lang_code: Language code (e.g., 'es-ES', 'en-US')

        Returns:
            Geographic region name, or empty string if not found.

        Example:
            >>> LanguageRegistry.get_region('es-ES')
            'Western Europe'
        """
        return cls.LANGUAGES.get(lang_code, {}).get('region', '')

    @classmethod
    def get_flag_path(cls, lang_code: str) -> Path | None:
        """Get path to flag PNG for language code.

        Args:
            lang_code: Language code (e.g., 'es-ES', 'en-US')

        Returns:
            Full path to the flag PNG file, or None if language not found.
            The path points to gui_resources/flags/ directory.

        Example:
            >>> path = LanguageRegistry.get_flag_path('es-ES')
            >>> path
            PosixPath('...gui_resources/flags/spain.png')
        """
        if lang_code not in cls.LANGUAGES:
            return None

        flag_file = cls.LANGUAGES[lang_code]['flag_file']
        flags_dir = Path(__file__).parent.parent / 'gui_resources' / 'flags'
        return flags_dir / flag_file

    @classmethod
    def is_valid_language(cls, lang_code: str) -> bool:
        """Check if a language code is valid/supported.

        Args:
            lang_code: Language code to validate

        Returns:
            True if the language code is in the registry, False otherwise.

        Example:
            >>> LanguageRegistry.is_valid_language('es-ES')
            True
            >>> LanguageRegistry.is_valid_language('xx-XX')
            False
        """
        return lang_code in cls.LANGUAGES

    @classmethod
    def get_language_count(cls) -> int:
        """Get total number of supported languages.

        Returns:
            Number of languages in the registry (18 for current implementation)
        """
        return len(cls.LANGUAGES)

    @classmethod
    def get_languages_by_region(cls, region: str) -> list[tuple[str, str]]:
        """Get all languages in a specific region, sorted by native name.

        Args:
            region: Region name (e.g., 'Western Europe', 'Asia')

        Returns:
            List of (code, native_name) tuples for languages in that region.

        Example:
            >>> LanguageRegistry.get_languages_by_region('Northern Europe')
            [('da-DK', 'Dansk'), ('fi-FI', 'Suomi'), ('is-IS', 'Íslenska'), ('sv-SE', 'Svenska')]
        """
        items = [
            (code, meta['native'])
            for code, meta in cls.LANGUAGES.items()
            if meta['region'] == region
        ]
        return sorted(items, key=lambda x: x[1])
