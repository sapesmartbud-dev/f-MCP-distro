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

"""Generate the MCP client configuration for this installation.

The configuration has to name a command that starts a *server*. Two things
make that easy to get wrong, and both used to be wrong here: the command has to
be an interpreter that can import this package (not whatever ``python`` happens
to mean in the client's environment), and it has to carry ``--cli``, or the
process opens the GUI and never speaks the protocol.

Both are settled by looking at the running process instead of probing the
environment: this module runs inside the application, so ``sys.executable`` is
by definition an interpreter with the dependencies installed.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class InstallationInfo:
    """How this copy of SAPÉ f-MCP was started."""

    install_type: str  # "frozen", "entry_point", "source", "unknown"
    entry_point: Optional[str] = None  # Executable or console script
    python_executable: Optional[str] = None  # Interpreter to name in the config
    main_module: Optional[str] = None  # Path to main.py (source only)
    venv_path: Optional[str] = None  # Active virtual environment, for display
    is_valid: bool = False
    error_message: Optional[str] = None


class MCPConfigGenerator:
    """Generate MCP server configuration with environment detection."""

    CONFIG_METADATA_FILE = Path.home() / ".sape" / "installation.json"

    @classmethod
    def detect_installation(cls) -> InstallationInfo:
        """Describe how to start the server, based on how this process started.

        Order: a frozen bundle, then a console script installed beside the
        running interpreter, then the source checkout — most self-contained
        first.

        A console script is only preferred once it has been *run*. An installed
        entry point can be present and broken (a packaging mistake leaves one
        that exits non-zero), and falling through to the source checkout then
        still produces a configuration that works, which is better than telling
        the user their installation is invalid while the application they are
        clicking in runs perfectly well.
        """
        if getattr(sys, "frozen", False):
            return InstallationInfo(
                install_type="frozen",
                entry_point=sys.executable,
                is_valid=True,
            )

        script = cls._console_script()
        script_error: Optional[str] = None
        if script is not None:
            if cls._validate_command(str(script)):
                return InstallationInfo(
                    install_type="entry_point",
                    entry_point=str(script),
                    python_executable=str(cls._launcher()),
                    venv_path=cls._venv_path(),
                    is_valid=True,
                )
            script_error = f"Ignoring {script}: it is installed but does not run."
            logger.warning(script_error)

        main_module = cls._main_module()
        if main_module.exists():
            return InstallationInfo(
                install_type="source",
                python_executable=str(cls._launcher()),
                main_module=str(main_module),
                venv_path=cls._venv_path(),
                is_valid=True,
            )

        return InstallationInfo(
            install_type="unknown",
            is_valid=False,
            error_message=(
                script_error + " "
                if script_error
                else ""
            ) + (
                f"Could not find main.py (looked in {main_module.parent}) and no "
                "working sape-f-mcp command is installed."
            ),
        )

    @staticmethod
    def _main_module() -> Path:
        """Absolute path to main.py in the source checkout."""
        return Path(__file__).resolve().parent.parent / "main.py"

    @staticmethod
    def _launcher() -> Path:
        """The interpreter to name in the config.

        ``sys.executable`` runs this window, so its environment is known good.
        On Windows a GUI started through ``pythonw.exe`` still has to hand the
        client ``python.exe``: the server talks over stdio, and pythonw has no
        standard handles of its own.
        """
        exe = Path(sys.executable)
        if exe.name.lower() == "pythonw.exe":
            console = exe.with_name("python.exe")
            if console.exists():
                return console
        return exe

    @classmethod
    def _console_script(cls) -> Optional[Path]:
        """The installed ``sape-f-mcp`` script, preferring this environment."""
        name = "sape-f-mcp.exe" if sys.platform == "win32" else "sape-f-mcp"
        candidate = Path(sys.executable).parent / name
        if candidate.exists():
            return candidate
        found = shutil.which("sape-f-mcp")
        return Path(found) if found else None

    @staticmethod
    def _venv_path() -> Optional[str]:
        """The active virtual environment, for display."""
        if sys.prefix != sys.base_prefix:
            return sys.prefix
        return os.environ.get("VIRTUAL_ENV")

    @staticmethod
    def _validate_command(command: str) -> bool:
        """Check that ``command --version`` runs and exits cleanly."""
        try:
            result = subprocess.run(
                [command, "--version"], capture_output=True, timeout=15, text=True
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    @staticmethod
    def client_config_path() -> Path:
        """Where Claude Desktop keeps its configuration on this platform."""
        if sys.platform == "win32":
            roaming = os.environ.get("APPDATA")
            base = Path(roaming) if roaming else Path.home() / "AppData" / "Roaming"
            return base / "Claude" / "claude_desktop_config.json"
        if sys.platform == "darwin":
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "Claude"
                / "claude_desktop_config.json"
            )
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    def generate_config(
        self,
        installation: InstallationInfo,
        db_path: str | os.PathLike[str] | None = None,
        transport: str = "stdio",
    ) -> Dict[str, Any]:
        """Build the ``mcpServers`` entry for ``installation``.

        ``--cli`` is what makes the process a server rather than the GUI, so it
        is never optional. ``db_path`` should be the database the GUI is
        actually using: the client spawns a process of its own, which would
        otherwise fall back to the default location and enforce a different set
        of rules from the ones on screen.
        """
        if not installation.is_valid:
            raise ValueError(f"Invalid installation: {installation.error_message}")

        if installation.install_type in ("frozen", "entry_point"):
            command = installation.entry_point
            args: list[str] = []
        else:
            command = installation.python_executable
            args = [str(installation.main_module)]

        args += ["--cli", "--transport", transport]
        if db_path:
            args += ["--db", str(db_path)]

        return {"command": command, "args": args, "env": {}}

    def save_installation_metadata(self, installation: InstallationInfo) -> None:
        """Save installation metadata to ~/.sape/installation.json for future use."""
        self.CONFIG_METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)

        metadata = {
            "install_type": installation.install_type,
            "entry_point": installation.entry_point,
            "python_executable": installation.python_executable,
            "main_module": installation.main_module,
            "venv_path": installation.venv_path,
            "is_valid": installation.is_valid,
            "detected_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }

        try:
            with open(self.CONFIG_METADATA_FILE, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"Saved installation metadata to {self.CONFIG_METADATA_FILE}")
        except Exception as e:
            logger.error(f"Failed to save installation metadata: {e}")

    @staticmethod
    def load_installation_metadata() -> Optional[InstallationInfo]:
        """Load previously saved installation metadata."""
        config_file = MCPConfigGenerator.CONFIG_METADATA_FILE

        if not config_file.exists():
            return None

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return InstallationInfo(
                install_type=data.get("install_type", "unknown"),
                entry_point=data.get("entry_point"),
                python_executable=data.get("python_executable"),
                main_module=data.get("main_module"),
                venv_path=data.get("venv_path"),
                is_valid=data.get("is_valid", False),
            )
        except Exception as e:
            logger.warning(f"Failed to load installation metadata: {e}")
            return None

    def generate_instructions(self, installation: InstallationInfo) -> str:
        """Human-readable setup instructions for this installation."""
        if installation.install_type == "frozen":
            head = "SAPÉ f-MCP is running from a packaged build."
        elif installation.install_type == "entry_point":
            head = f"SAPÉ f-MCP is installed as a command:\n{installation.entry_point}"
        elif installation.install_type == "source":
            head = (
                "SAPÉ f-MCP is running from source. The configuration names the "
                f"interpreter this window is running on:\n{installation.python_executable}"
            )
        else:
            return installation.error_message or "Installation not detected."

        return (
            f"{head}\n\n"
            f"Paste the JSON below into:\n{self.client_config_path()}\n\n"
            "Merge it with any mcpServers you already have — do not replace the "
            "file — then restart Claude Desktop."
        )
