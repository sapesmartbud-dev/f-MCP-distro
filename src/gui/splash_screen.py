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

"""Splash screen shown on application startup.

Professional SAPÉ f-Win MCP splash screen with:
- Logo-only design (no text)
- Theme-aware SVG logo loading
- Dark and light theme support
- 5-second display duration (adjustable)
- Clean, minimal aesthetic
"""

from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import (
    QPixmap, QColor, QPainter
)
from PyQt6.QtCore import Qt, QTimer
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SAPESplashScreen(QSplashScreen):
    """SAPÉ branded splash screen with logo-only design.

    Features:
    - SVG logo scaled to reasonable window size (50% of native 3660x920)
    - Centered logo on theme-matched background
    - No text, no decorations - pure minimal design
    - Frameless, stays on top, auto-closes after 5 seconds
    """

    # SVG native dimensions
    SVG_NATIVE_WIDTH = 3660
    SVG_NATIVE_HEIGHT = 920
    SCALE_FACTOR = 0.2  # 20% of native size for screen real estate

    def __init__(self, theme="dark", parent_window=None):
        """Initialize splash screen with specified theme.

        Args:
            theme (str): "dark" or "light" theme selection.
            parent_window: Optional reference to main window (not used for initial positioning).
        """
        self.theme = theme
        self.parent_window = parent_window
        self._timer = None

        # Setup theme colors
        if theme == "dark":
            self.bg_color = QColor("#0A0C10")  # Dark background
            logo_file = "sape-logo-h-dark.svg"
        else:
            self.bg_color = QColor("#F4F6FA")  # Light background
            logo_file = "sape-logo-h-light.svg"

        # Resolve logo path
        logo_path = Path(__file__).parent.parent.parent / "gui_resources" / "logos" / logo_file

        if not logo_path.exists():
            logger.error(f"Logo file not found: {logo_path}")
            raise FileNotFoundError(f"Logo file not found: {logo_path}")

        # Calculate scaled dimensions
        scaled_width = int(self.SVG_NATIVE_WIDTH * self.SCALE_FACTOR)
        scaled_height = int(self.SVG_NATIVE_HEIGHT * self.SCALE_FACTOR)

        # Load SVG and scale to pixmap
        pixmap = QPixmap(str(logo_path))
        if pixmap.isNull():
            logger.error(f"Failed to load SVG logo: {logo_path}")
            raise RuntimeError(f"Failed to load SVG logo: {logo_path}")

        # Scale pixmap to desired size (high quality)
        pixmap = pixmap.scaledToWidth(scaled_width, Qt.TransformationMode.SmoothTransformation)

        # Create canvas with background color
        canvas = QPixmap(scaled_width, scaled_height)
        canvas.fill(self.bg_color)

        # Calculate centered position for logo on canvas
        logo_x = (scaled_width - pixmap.width()) // 2
        logo_y = (scaled_height - pixmap.height()) // 2

        # Composite logo onto canvas
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(logo_x, logo_y, pixmap)
        painter.end()

        # Initialize splash screen with composed pixmap
        super().__init__(canvas)
        self.setWindowFlags(
            Qt.WindowType.SplashScreen |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )

        logger.info(f"Splash screen created with theme: {theme} (size: {scaled_width}x{scaled_height})")

    def show_and_wait(self, duration_ms: int = 5000) -> QTimer:
        """Display splash screen for specified duration then auto-close.

        The splash screen is centered on the primary screen.

        Args:
            duration_ms (int): Display duration in milliseconds (default: 5000).

        Returns:
            QTimer: The timer instance used for auto-closing.
        """
        # Center splash screen on primary screen
        screen_geometry = QApplication.primaryScreen().geometry()
        splash_width = self.width()
        splash_height = self.height()

        x = (screen_geometry.width() - splash_width) // 2 + screen_geometry.x()
        y = (screen_geometry.height() - splash_height) // 2 + screen_geometry.y()

        self.move(x, y)
        logger.info(f"Splash screen centered on screen at ({x}, {y})")

        self.show()
        QApplication.processEvents()
        logger.info(f"Splash screen displayed for {duration_ms}ms")

        # Setup auto-close timer
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close_splash)
        self._timer.start(duration_ms)

        return self._timer

    def close_splash(self) -> None:
        """Close the splash screen and cleanup resources."""
        if self._timer:
            self._timer.stop()
            self._timer.deleteLater()
            self._timer = None

        self.close()
        logger.info("Splash screen closed")
