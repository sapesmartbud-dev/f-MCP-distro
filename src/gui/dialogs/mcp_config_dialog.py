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

"""MCP Configuration Setup Dialog."""

import json
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
    QGroupBox, QMessageBox, QApplication
)
from PyQt6.QtGui import QFont, QColor, QIcon
from PyQt6.QtCore import Qt, QTimer

from ...mcp_config_generator import MCPConfigGenerator, InstallationInfo
from ..i18n import translate
from ..styles.sape_design_tokens import (
    LIGHT_TEXT_PRIMARY, DARK_TEXT_PRIMARY, LIGHT_SURFACE, DARK_SURFACE,
    LIGHT_BORDER, DARK_BORDER, COLOR_SUCCESS, COLOR_ERROR, SAPE_PRIMARY
)

logger = logging.getLogger(__name__)


class MCPConfigDialog(QDialog):
    """Dialog for generating and displaying MCP configuration."""

    def __init__(self, parent=None, app=None):
        super().__init__(parent)
        self.app = app
        self.generator = MCPConfigGenerator()
        self.installation = None
        self.config_json = None

        self.setWindowTitle("MCP Configuration Setup")
        self.setGeometry(200, 150, 700, 600)
        self.setMinimumWidth(700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("Configure SAPÉ f-MCP for Claude Desktop")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Detection status group
        self.status_group = QGroupBox("Installation Detection")
        status_layout = QVBoxLayout()
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        self.status_group.setLayout(status_layout)
        layout.addWidget(self.status_group)

        # Instructions group
        self.instructions_group = QGroupBox("Setup Instructions")
        instructions_layout = QVBoxLayout()
        self.instructions_text = QPlainTextEdit()
        self.instructions_text.setReadOnly(True)
        self.instructions_text.setMaximumHeight(120)
        instructions_layout.addWidget(self.instructions_text)
        self.instructions_group.setLayout(instructions_layout)
        layout.addWidget(self.instructions_group)

        # Configuration display group
        config_group = QGroupBox("MCP Configuration (mcpServers)")
        config_layout = QVBoxLayout()

        config_desc = QLabel(
            "Copy this JSON and merge it into Claude Desktop's config file.\n"
            f"Location: {MCPConfigGenerator.client_config_path()}"
        )
        config_desc.setWordWrap(True)
        config_layout.addWidget(config_desc)

        self.config_display = QPlainTextEdit()
        self.config_display.setReadOnly(True)
        self.config_display.setFont(QFont("Courier", 9))
        self.config_display.setMinimumHeight(200)
        config_layout.addWidget(self.config_display)

        # Copy button
        copy_layout = QHBoxLayout()
        self.copy_button = QPushButton("Copy JSON to Clipboard")
        self.copy_button.setMaximumWidth(250)
        self.copy_button.clicked.connect(self._on_copy_json)
        copy_layout.addWidget(self.copy_button)
        copy_layout.addStretch()
        config_layout.addLayout(copy_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group, 1)

        # Buttons at bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.test_button = QPushButton("Test Connection")
        self.test_button.setMaximumWidth(150)
        self.test_button.clicked.connect(self._on_test_connection)
        button_layout.addWidget(self.test_button)

        self.close_button = QPushButton("Close")
        self.close_button.setMaximumWidth(150)
        self.close_button.clicked.connect(self.accept)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

        # Perform detection and generate config
        self._perform_setup()

    def _perform_setup(self):
        """Detect installation and generate configuration."""
        try:
            # Detect installation
            self.installation = self.generator.detect_installation()
            self.generator.save_installation_metadata(self.installation)

            # Show detection status
            self._update_status_display()

            # Generate configuration
            if self.installation.is_valid:
                # Name the database the GUI is using, so the process the client
                # spawns enforces the rules shown on the Permissions page
                # rather than falling back to the default location.
                db_path = None
                if self.app is not None and getattr(self.app, "server", None) is not None:
                    db_path = self.app.server.permissions.db_path
                config_dict = self.generator.generate_config(self.installation, db_path=db_path)
                # The client merges this whole object into its config file, so
                # it has to carry the mcpServers wrapper.
                self.config_json = {
                    "mcpServers": {
                        "sape-f-mcp": config_dict
                    }
                }
                self._update_config_display()
                self._update_instructions()
            else:
                self._show_error(self.installation.error_message or "Unknown error")

        except Exception as e:
            logger.error(f"Error during MCP config setup: {e}")
            self._show_error(f"Setup error: {e}")

    def _update_status_display(self):
        """Update detection status display."""
        if not self.installation:
            return

        status_text = f"Installation Type: {self.installation.install_type}\n"

        if self.installation.is_valid:
            status_color = COLOR_SUCCESS
            status_text += "✓ Status: Valid and Ready\n\n"
            if self.installation.entry_point:
                status_text += f"Entry Point: {self.installation.entry_point}\n"
            if self.installation.python_executable:
                status_text += f"Python: {self.installation.python_executable}\n"
            if self.installation.venv_path:
                status_text += f"Virtual Environment: {self.installation.venv_path}\n"
        else:
            status_color = COLOR_ERROR
            status_text += "✗ Status: Invalid\n\n"
            status_text += f"Error: {self.installation.error_message}\n"

        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"color: {status_color.name()};")

        # Update group box border color
        theme = self.app.current_theme if self.app else "light"
        border_color = DARK_BORDER if theme == "dark" else LIGHT_BORDER
        self.status_group.setStyleSheet(f"QGroupBox {{ border: 2px solid {status_color.name()}; }}")

    def _update_config_display(self):
        """Update configuration JSON display."""
        if not self.config_json:
            return

        json_str = json.dumps(self.config_json, indent=2)
        self.config_display.setPlainText(json_str)

    def _update_instructions(self):
        """Update setup instructions."""
        if not self.installation:
            return

        instructions = self.generator.generate_instructions(self.installation)
        self.instructions_text.setPlainText(instructions)

    def _on_copy_json(self):
        """Copy configuration JSON to clipboard."""
        if not self.config_json:
            QMessageBox.warning(self, "Error", "No configuration to copy.")
            return

        try:
            json_str = json.dumps(self.config_json, indent=2)
            clipboard = QApplication.clipboard()
            clipboard.setText(json_str)

            # Temporarily change button text to show success
            original_text = self.copy_button.text()
            self.copy_button.setText("✓ Copied!")
            self.copy_button.setEnabled(False)

            # Reset after 2 seconds
            timer = QTimer()
            timer.timeout.connect(
                lambda: (
                    self.copy_button.setText(original_text),
                    self.copy_button.setEnabled(True),
                    timer.stop()
                )
            )
            timer.start(2000)

            logger.info("MCP configuration copied to clipboard")
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            QMessageBox.critical(self, "Error", f"Failed to copy: {e}")

    def _on_test_connection(self):
        """Test if MCP server can be reached."""
        if not self.installation or not self.installation.is_valid:
            QMessageBox.warning(self, "Error", "Installation is not valid.")
            return

        try:
            import subprocess
            if self.installation.entry_point:
                result = subprocess.run(
                    [self.installation.entry_point, "--version"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
            else:
                result = subprocess.run(
                    [self.installation.python_executable, self.installation.main_module, "--version"],
                    capture_output=True,
                    timeout=5,
                    text=True
                )

            if result.returncode == 0:
                QMessageBox.information(
                    self,
                    "Success",
                    f"SAPÉ f-MCP is working!\n\nOutput:\n{result.stdout}"
                )
            else:
                QMessageBox.warning(
                    self,
                    "Error",
                    f"Command failed with code {result.returncode}:\n{result.stderr}"
                )
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "Timeout", "Command took too long to respond.")
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            QMessageBox.critical(self, "Error", f"Test failed: {e}")

    def _show_error(self, message: str):
        """Show error message and disable config display."""
        error_label = QLabel(f"Setup Error:\n{message}")
        error_label.setStyleSheet(f"color: {COLOR_ERROR.name()};")
        error_label.setWordWrap(True)

        # Clear config display
        self.config_display.setPlainText("(Configuration could not be generated)")
        self.copy_button.setEnabled(False)
        self.test_button.setEnabled(False)

        QMessageBox.critical(self, "Setup Error", message)
