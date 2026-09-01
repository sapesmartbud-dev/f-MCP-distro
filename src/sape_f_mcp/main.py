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

"""SAPÉ f-MCP entry point for pip-installed command."""

import sys
from pathlib import Path

# Add parent directory to path so we can import main.py from root
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Import and call the actual main.py
from main import main

def run():
    """Entry point for sape-f-mcp command."""
    sys.exit(main())

if __name__ == "__main__":
    run()
