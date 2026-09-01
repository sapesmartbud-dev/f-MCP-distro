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

"""Single source of truth for the project version.

Everything that reports a version reads it from here:

* ``pyproject.toml`` via ``[tool.setuptools.dynamic]``
* :mod:`src.sape_f_mcp` and :mod:`src.gui` (``__version__``)
* the version advertised to MCP clients in :class:`src.mcp_server.FileMCPServer`
* the About page in the GUI

Keep this module free of imports so it stays cheap to read and safe for
setuptools to parse statically at build time.
"""

__version__ = "0.2.1.2"
