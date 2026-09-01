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

"""Main application window (QMainWindow)."""

import logging
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon

from .server_thread import ServerThread, DEFAULT_PORT
from .components.sidebar import Sidebar
from .components.header import Header
from .components.status_bar import StatusBar
from .pages.session_log_page import SessionLogPage
from .pages.permissions_page import PermissionsPage
from .pages.settings_page import SettingsPage
from .pages.legal_page import LegalPage
from .pages.help_page import HelpPage
from .pages.about_page import AboutPage
from .i18n import translate

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, server, transport, app):
        super().__init__()

        self.server = server
        self.transport = transport
        self.app = app
        self.server_thread = None
        self.config_dir = Path.home() / ".sape"

        self.setWindowTitle(translate("window.title", self.app.current_language))
        self.setGeometry(100, 100, 1280, 800)
        self.setMinimumSize(900, 600)

        # Load and set window icon (multi-resolution for better taskbar display)
        icon_path = Path(__file__).parent.parent.parent / "gui_resources" / "icons" / "dark.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
            logger.info(f"Window icon loaded from: {icon_path}")
        else:
            logger.warning(f"Icon file not found: {icon_path}")

        # Connect language change signal
        self.app.language_changed.connect(self._update_language)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== HEADER =====
        self.header = Header(self)
        self.header.theme_toggled.connect(self._on_theme_changed)
        self.header.language_changed.connect(self._on_language_changed)
        main_layout.addWidget(self.header)

        # ===== CONTENT AREA (SIDEBAR + PAGES) =====
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar(self)
        self.sidebar.nav_clicked.connect(self._on_page_change)
        content_layout.addWidget(self.sidebar)

        # Stacked widget for pages
        self.pages = QStackedWidget()

        self.session_log_page = SessionLogPage(self.server, self.app, self.app.session_id, self.app.log_store)
        self.permissions_page = PermissionsPage(self.server, self.app)
        self.settings_page = SettingsPage(self)
        self.legal_page = LegalPage(self.app)
        self.help_page = HelpPage(self.app)
        self.about_page = AboutPage(self.app)

        self.pages.addWidget(self.session_log_page)     # 0
        self.pages.addWidget(self.permissions_page)     # 1
        self.pages.addWidget(self.settings_page)        # 2
        self.pages.addWidget(self.legal_page)           # 3
        self.pages.addWidget(self.help_page)            # 4
        self.pages.addWidget(self.about_page)           # 5

        # Show session log by default
        self.pages.setCurrentIndex(0)
        content_layout.addWidget(self.pages, 1)

        # Add content to main layout
        content_widget = QWidget()
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget, 1)

        # ===== STATUS BAR =====
        self.status_bar_widget = StatusBar(self)
        self.status_bar_widget.start_clicked.connect(self._on_start_server)
        self.status_bar_widget.stop_clicked.connect(self._on_stop_server)
        main_layout.addWidget(self.status_bar_widget)

        # Restore window state (position, size, minimized state)
        self._restore_window_state()

        logger.info("Main window created")

    def _on_page_change(self, page_index: int):
        """Handle page navigation."""
        self.pages.setCurrentIndex(page_index)
        logger.debug(f"Switched to page: {page_index}")

    def _on_theme_changed(self, theme: str):
        """Handle theme toggle from header."""
        self.app.theme_manager.set_theme(theme)
        logger.info(f"Theme changed to: {theme}")

    def _on_language_changed(self, language: str):
        """Handle language change from header."""
        self.app.set_language(language)
        logger.info(f"Language changed to: {language}")

    def _update_language(self, language: str):
        """Update window title when language changes.

        Args:
            language (str): New language code
        """
        self.setWindowTitle(translate("window.title", language))
        # Update language button in header to reflect current selection
        if hasattr(self, 'header'):
            self.header.update_language_button(language)

    def _on_start_server(self):
        """Start the MCP server using streamable-http transport.

        Streamable-HTTP allows the server to run in a QThread without hanging
        on stdin. It listens on localhost:8089 for client connections.
        """
        if self.server_thread is None or not self.server_thread.isRunning():
            logger.info("Starting MCP server...")
            # Use streamable-http for GUI mode (non-blocking HTTP transport)
            # Keep stdio only for CLI mode (when called with --cli flag)
            transport = "streamable-http" if self.transport == "stdio" else self.transport

            self.server_thread = ServerThread(
                self.server,
                transport=transport,
                host="127.0.0.1",
                port=DEFAULT_PORT
            )
            self.server_thread.started.connect(self._on_server_started)
            self.server_thread.finished.connect(self._on_server_stopped)
            self.server_thread.error.connect(self._on_server_error)
            self.server_thread.port_changed.connect(self._on_server_port_changed)
            self.server_thread.tool_executed.connect(self.session_log_page.log_tool_call)
            self.server_thread.start()

    def _on_stop_server(self):
        """Stop the MCP server."""
        if self.server_thread and self.server_thread.isRunning():
            logger.info("Stopping MCP server...")
            self.server_thread.stop()

    def _on_server_started(self):
        """Called when server starts."""
        logger.info("Server started")
        self.status_bar_widget.set_running(True)
        # Show default port (8089) unless port_changed signal was emitted
        if self.server_thread:
            self.status_bar_widget.set_port_info(self.server_thread.port, default_port=DEFAULT_PORT)

    def _on_server_stopped(self):
        """Called when server stops."""
        logger.info("Server stopped")
        self.status_bar_widget.set_running(False)

    def _on_server_port_changed(self, port: int):
        """Called when server uses a different port than requested.

        This happens when the default port (8089) is already in use.
        """
        logger.info(f"Server using port {port} (default 8089 was busy)")
        self.status_bar_widget.set_port_info(port, default_port=DEFAULT_PORT)

    def _on_server_error(self, error: str):
        """Called when server encounters an error.

        Resets UI state and shows error dialog to user.
        """
        logger.error(f"Server error: {error}")
        # Reset UI state to "Stopped" since server failed to start
        self.status_bar_widget.set_running(False)
        # Show error dialog to user with translated text
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(translate("main_window.server_error_title", self.app.current_language))
        msg_box.setText(f"{translate('main_window.server_error_message', self.app.current_language)}\n\n{error}")
        msg_box.addButton(translate("common.ok", self.app.current_language), QMessageBox.ButtonRole.AcceptRole)
        msg_box.exec()

    def _save_window_state(self):
        """Save window position, size, and state to config."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            config_file = self.config_dir / "config.json"

            # Load existing config
            config = {}
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)

            # Save window state
            window_state = {
                "geometry": {
                    "x": self.geometry().x(),
                    "y": self.geometry().y(),
                    "width": self.geometry().width(),
                    "height": self.geometry().height(),
                },
                "is_maximized": self.isMaximized(),
                "is_minimized": self.isMinimized(),
            }
            config["window_state"] = window_state

            # Write back to file
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            logger.debug(f"Window state saved to {config_file}")
        except Exception as e:
            logger.error(f"Error saving window state: {e}")

    def _restore_window_state(self):
        """Restore window position, size, and state from config."""
        try:
            config_file = self.config_dir / "config.json"
            if not config_file.exists():
                logger.debug("No saved window state found")
                return

            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            window_state = config.get("window_state", {})
            if not window_state:
                logger.debug("No window state in config")
                return

            # Restore geometry
            geom = window_state.get("geometry", {})
            if geom:
                x = geom.get("x", 100)
                y = geom.get("y", 100)
                w = geom.get("width", 1280)
                h = geom.get("height", 800)

                # Validate that window is not off-screen (basic check)
                # For now, accept any valid geometry
                if w >= 900 and h >= 600:  # Respect minimum size
                    self.setGeometry(x, y, w, h)
                    logger.debug(f"Restored window geometry: {x}, {y}, {w}x{h}")

            # Restore maximized state
            if window_state.get("is_maximized", False):
                self.showMaximized()
                logger.debug("Window restored as maximized")

            logger.info("Window state restored")
        except Exception as e:
            logger.error(f"Error restoring window state: {e}")

    def closeEvent(self, event):
        """Handle window close event."""
        # Save window state before closing
        self._save_window_state()
        event.accept()

    def set_theme(self, theme: str):
        """Propagate theme change to application."""
        self.app.set_theme(theme)
