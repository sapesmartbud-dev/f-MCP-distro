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

"""Flag file mapping for all 18 supported languages.

This module maps language codes to their corresponding flag PNG files
located in gui_resources/flags/. Flag existence is validated at import time.

All flag files are sourced from flagcdn.com and stored as PNG.
"""

from __future__ import annotations

from pathlib import Path


# Mapping from language code to flag PNG filename
FLAG_MAPPING = {
    'en-US': 'england.png',
    'es-ES': 'spain.png',
    'fr-FR': 'france.png',
    'de-DE': 'germany.png',
    'it-IT': 'italy.png',
    'pt-BR': 'brazil.png',
    'nl-NL': 'netherlands.png',
    'sv-SE': 'sweden.png',
    'da-DK': 'denmark.png',
    'fi-FI': 'finland.png',
    'pl-PL': 'poland.png',
    'cs-CZ': 'czech.png',
    'sk-SK': 'slovakia.png',
    'hu-HU': 'hungary.png',
    'ro-RO': 'romania.png',
    'ru-RU': 'russia.png',
    'is-IS': 'iceland.png',
    'zh-CN': 'china.png',
}


def get_flag_path(lang_code: str) -> Path | None:
    """Get path to flag PNG for language code.

    Args:
        lang_code: Language code (e.g., 'es-ES', 'en-US')

    Returns:
        Full path to the flag PNG file, or None if language code not found.
        The path points to gui_resources/flags/ directory.

    Example:
        >>> path = get_flag_path('es-ES')
        >>> path.name
        'spain.png'
        >>> path.parent.name
        'flags'
    """
    flag_file = FLAG_MAPPING.get(lang_code)
    if not flag_file:
        return None

    flags_dir = Path(__file__).parent.parent / 'gui_resources' / 'flags'
    return flags_dir / flag_file


def flag_exists(lang_code: str) -> bool:
    """Check if flag file exists for the given language code.

    Args:
        lang_code: Language code (e.g., 'es-ES', 'en-US')

    Returns:
        True if the flag file exists on disk, False otherwise.

    Example:
        >>> flag_exists('es-ES')
        True
        >>> flag_exists('xx-XX')
        False
    """
    path = get_flag_path(lang_code)
    if path is None:
        return False
    return path.exists()


def get_all_flag_paths() -> dict[str, Path]:
    """Get all flag file paths for all 18 languages.

    Returns:
        Dictionary mapping language codes to their flag file paths.
        Only includes languages that have flag files present on disk.

    Example:
        >>> paths = get_all_flag_paths()
        >>> len(paths)
        18
        >>> paths['es-ES'].name
        'spain.png'
    """
    result = {}
    for lang_code in FLAG_MAPPING.keys():
        path = get_flag_path(lang_code)
        if path and path.exists():
            result[lang_code] = path
    return result


def get_missing_flags() -> list[str]:
    """Get list of language codes whose flag files are missing.

    Returns:
        List of language codes that don't have corresponding flag files
        on disk. Should be empty if all flags are properly installed.

    Example:
        >>> missing = get_missing_flags()
        >>> len(missing)  # Should be 0
        0
    """
    missing = []
    for lang_code in FLAG_MAPPING.keys():
        if not flag_exists(lang_code):
            missing.append(lang_code)
    return missing


def validate_all_flags() -> tuple[bool, list[str]]:
    """Validate that all 18 language flags exist and are accessible.

    Returns:
        Tuple of (all_valid, missing_languages) where:
        - all_valid: True if all 18 flags are present, False otherwise
        - missing_languages: List of language codes with missing flags
            (empty if all_valid is True)

    Example:
        >>> valid, missing = validate_all_flags()
        >>> valid
        True
        >>> missing
        []
    """
    missing = get_missing_flags()
    return len(missing) == 0, missing


def get_flag_file_size(lang_code: str) -> int | None:
    """Get the file size of a flag PNG in bytes.

    Args:
        lang_code: Language code (e.g., 'es-ES')

    Returns:
        File size in bytes, or None if file doesn't exist.

    Example:
        >>> size = get_flag_file_size('es-ES')
        >>> size > 0
        True
    """
    path = get_flag_path(lang_code)
    if path is None or not path.exists():
        return None
    return path.stat().st_size


def get_flag_content(lang_code: str) -> bytes | None:
    """Load the PNG content of a flag file.

    Args:
        lang_code: Language code (e.g., 'es-ES')

    Returns:
        PNG file content as bytes, or None if file doesn't exist.

    Example:
        >>> content = get_flag_content('es-ES')
        >>> content[:4] == b'\\x89PNG'
        True
    """
    path = get_flag_path(lang_code)
    if path is None or not path.exists():
        return None
    return path.read_bytes()


# Validation at module load time
_VALIDATION_RESULT = validate_all_flags()
_ALL_FLAGS_PRESENT = _VALIDATION_RESULT[0]
_MISSING_FLAGS = _VALIDATION_RESULT[1]


def are_all_flags_present() -> bool:
    """Check if all 18 language flags were present at module load time.

    Returns:
        True if all flags were available when the module was imported,
        False if some are missing.

    Note:
        This reflects the state at module import time. If flags are added
        to disk after the module is loaded, this will still return the
        original result. Call validate_all_flags() for a current check.
    """
    return _ALL_FLAGS_PRESENT


def get_missing_flags_at_load_time() -> list[str]:
    """Get list of flags that were missing when the module was imported.

    Returns:
        List of language codes without flag files at import time.
    """
    return _MISSING_FLAGS
