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

"""Entry point: Launch PyQt6 GUI with MCP server control."""

from __future__ import annotations

import argparse
import sys
import logging
from pathlib import Path
import os

# Allow running this script from any working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src._version import __version__  # noqa: E402
from src.mcp_server import FileMCPServer  # noqa: E402

# The GUI is imported inside main(), not here: --cli is a headless server and
# must not need PyQt6 installed. Importing it at module level made the server
# unstartable anywhere Qt is absent, which is the normal case on a server or in
# a minimal container.

# Hide console window on Windows (GUI-only application). Not in --cli mode:
# there the process is a server, it inherits the console of whoever launched it,
# and hiding that would take the user's own terminal window with it.
if sys.platform == "win32" and "--cli" not in sys.argv:
    try:
        import ctypes
        # Get the window handle of the console
        whnd = ctypes.windll.kernel32.GetConsoleWindow()
        if whnd != 0:
            # Hide the console window (SW_HIDE = 0)
            ctypes.windll.user32.ShowWindow(whnd, 0)
    except (AttributeError, OSError):
        pass  # Not running on Windows or console handle not available

# Setup logging - suppress console output for GUI-only mode
logging.basicConfig(
    level=logging.CRITICAL,  # Only critical errors to stderr
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.NullHandler()  # Suppress all console output
    ]
)
logger = logging.getLogger(__name__)


def _get_default_db_path() -> str:
    """Get default database path.

    Resolves in order:
    1. $FILE_MCP_DB environment variable
    2. ./permissions.db relative to script location
    """
    import os
    env_db = os.getenv("FILE_MCP_DB")
    if env_db:
        return env_db
    script_dir = Path(__file__).resolve().parent
    return str(script_dir / "permissions.db")


def _get_default_base_dir() -> str | None:
    """Get default base directory.

    Resolves in order:
    1. $FILE_MCP_BASE environment variable
    2. None (defaults to cwd at runtime, but can be overridden)
    """
    import os
    return os.getenv("FILE_MCP_BASE")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SAPÉ f-MCP — Permission Manager")
    parser.add_argument(
        "--version",
        action="version",
        version=f"SAPÉ f-MCP {__version__}",
        help="Print the version and exit.",
    )
    parser.add_argument(
        "--db",
        default=_get_default_db_path(),
        help="SQLite permissions database (default: $FILE_MCP_DB, else ./permissions.db relative to script).",
    )
    parser.add_argument(
        "--base-dir",
        default=_get_default_base_dir(),
        help="Directory relative paths resolve against (default: $FILE_MCP_BASE, else cwd). "
        "Grants no access by itself.",
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="Transport to serve on (default: stdio).",
    )
    parser.add_argument(
        "--show-permissions",
        action="store_true",
        help="Print the permission rules and exit without launching GUI.",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode (start server immediately, no GUI).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        server = FileMCPServer(db_path=args.db, base_dir=args.base_dir)
    except (NotADirectoryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.show_permissions:
        from src.permissions import ACTIONS

        print(f"database: {server.permissions.db_path}")
        for rule in server.permissions.rules():
            allowed = ",".join(a for a in ACTIONS if rule[f"can_{a}"]) or "-none-"
            print(
                f"  {rule['path']}  subfolders={bool(rule['allow_subfolders'])}  "
                f"allowed={allowed}  created_at={rule['created_at']} by {rule['user_created']}"
            )
        return 0

    if args.cli:
        # CLI mode: start server immediately without GUI
        # Also enable SQLite logging so Claude Desktop tool calls appear in the GUI
        logger.info("Starting SAPÉ f-MCP server in CLI mode...")
        from src.log_store import LogStore
        import uuid
        try:
            cli_log_store = LogStore()
            cli_session_id = "cli"  # Use well-known session_id for external CLI calls
            server.set_log_store(cli_log_store, cli_session_id)
            logger.info("CLI logging enabled")
        except Exception as e:
            logger.warning(f"Failed to enable CLI logging: {e}")
        server.run(transport=args.transport)
        return 0

    # GUI mode (default)
    logger.info("Launching SAPÉ f-MCP GUI...")
    try:
        from src.gui.app import SAPEApplication
        from src.gui.splash_screen import SAPESplashScreen
    except ImportError as exc:
        print(
            f"error: the graphical interface needs PyQt6, which is not installed ({exc}).\n"
            "       Install it, or run the server headless with --cli.",
            file=sys.stderr,
        )
        return 1

    app = SAPEApplication(server=server, transport=args.transport)

    # Update server logger with app's log store and session ID for SQLite logging
    try:
        server.set_log_store(app.log_store, app.session_id)
    except Exception as e:
        logger.warning(f"Failed to enable SQLite logging: {e}")

    # Show splash screen (centered on screen, not dependent on main window)
    # Use the app's current theme for splash screen
    splash = SAPESplashScreen(theme=app.current_theme)
    splash.show_and_wait(duration_ms=5000)

    return app.run(splash=None)


if __name__ == "__main__":
    raise SystemExit(main())
