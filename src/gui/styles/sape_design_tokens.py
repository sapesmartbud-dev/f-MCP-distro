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

"""SAPÉ Design System tokens for PyQt6."""

from PyQt6.QtGui import QColor, QPalette, QFont
from PyQt6.QtCore import Qt

# ===== COLORS =====
SAPE_PRIMARY = QColor("#1C3FF0")
SAPE_PRIMARY_DARK = QColor("#122AD2")
SAPE_ACCENT = QColor("#2E86FF")
SAPE_GRAPHITE = QColor("#212832")
SAPE_GRAPHITE_LIGHT = QColor("#6B7280")

# Light theme colors
LIGHT_BG = QColor("#F4F6FA")
LIGHT_SURFACE = QColor("#FFFFFF")
LIGHT_TEXT_PRIMARY = QColor("#212832")
LIGHT_TEXT_SECONDARY = QColor("#4B5563")
LIGHT_BORDER = QColor("#E1E5EA")

# Dark theme colors
DARK_BG = QColor("#0A0C10")
DARK_SURFACE = QColor("#15181D")
DARK_TEXT_PRIMARY = QColor("#E0E2E7")
DARK_TEXT_SECONDARY = QColor("#A7ACB3")
DARK_BORDER = QColor("#2D3139")

# Semantic colors
COLOR_SUCCESS = QColor("#10B981")
COLOR_ERROR = QColor("#EF4444")
COLOR_WARNING = QColor("#F59E0B")
COLOR_INFO = QColor("#3B82F6")

# Action type colors
ACTION_CREATE = QColor("#10B981")    # Green
ACTION_READ = QColor("#3B82F6")      # Blue
ACTION_WRITE = QColor("#F59E0B")     # Amber
ACTION_DELETE = QColor("#EF4444")    # Red
ACTION_MOVE = QColor("#8B5CF6")      # Purple
ACTION_COPY = QColor("#06B6D4")      # Cyan
ACTION_CHMOD = QColor("#EC4899")     # Pink
ACTION_ERROR = QColor("#DC2626")     # Dark Red

# Typography
FONT_FAMILY = "IBM Plex Sans"
FONT_MONO = "JetBrains Mono"

# Spacing (4px base unit)
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 20
SPACING_2XL = 24
SPACING_3XL = 28
SPACING_4XL = 32

# Border radius
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 8
RADIUS_XL = 12

# ===== LIGHT THEME PALETTE =====
def create_light_palette() -> QPalette:
    """Create light theme palette."""
    palette = QPalette()

    # Windows/background
    palette.setColor(QPalette.ColorRole.Window, LIGHT_BG)
    palette.setColor(QPalette.ColorRole.Base, LIGHT_SURFACE)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F9FAFB"))

    # Text
    palette.setColor(QPalette.ColorRole.WindowText, LIGHT_TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.Text, LIGHT_TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.PlaceholderText, LIGHT_TEXT_SECONDARY)

    # Buttons
    palette.setColor(QPalette.ColorRole.Button, LIGHT_SURFACE)
    palette.setColor(QPalette.ColorRole.ButtonText, LIGHT_TEXT_PRIMARY)

    # Highlights and selection
    palette.setColor(QPalette.ColorRole.Highlight, SAPE_PRIMARY)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))

    # Links
    palette.setColor(QPalette.ColorRole.Link, SAPE_PRIMARY)
    palette.setColor(QPalette.ColorRole.LinkVisited, SAPE_PRIMARY_DARK)

    # Disabled
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText,
                     QColor("#9CA3AF"))

    return palette


# ===== DARK THEME PALETTE =====
def create_dark_palette() -> QPalette:
    """Create dark theme palette."""
    palette = QPalette()

    # Windows/background
    palette.setColor(QPalette.ColorRole.Window, DARK_BG)
    palette.setColor(QPalette.ColorRole.Base, DARK_SURFACE)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#1F2329"))

    # Text
    palette.setColor(QPalette.ColorRole.WindowText, DARK_TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.Text, DARK_TEXT_PRIMARY)
    palette.setColor(QPalette.ColorRole.PlaceholderText, DARK_TEXT_SECONDARY)

    # Buttons
    palette.setColor(QPalette.ColorRole.Button, DARK_SURFACE)
    palette.setColor(QPalette.ColorRole.ButtonText, DARK_TEXT_PRIMARY)

    # Highlights and selection
    palette.setColor(QPalette.ColorRole.Highlight, SAPE_PRIMARY)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))

    # Links
    palette.setColor(QPalette.ColorRole.Link, SAPE_ACCENT)
    palette.setColor(QPalette.ColorRole.LinkVisited, SAPE_PRIMARY_DARK)

    # Disabled
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText,
                     QColor("#6B7280"))

    return palette


LIGHT_THEME_PALETTE = create_light_palette()
DARK_THEME_PALETTE = create_dark_palette()
