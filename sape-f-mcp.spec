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

"""PyInstaller build spec for the SAPÉ f-MCP desktop application.

Build with::

    pyinstaller sape-f-mcp.spec

from the project root, or let ``_distro/Windows/build_windows.ps1`` and
``_distro/Linux/build_linux.sh`` do it. Produces a one-directory bundle under
``dist/sape-f-mcp/`` whose executable is ``dist/sape-f-mcp/sape-f-mcp``
(``.exe`` on Windows).

Every runtime resource is found relative to a module's ``__file__``
(``Path(__file__).parent.parent / "gui_resources"`` and so on). In a
PyInstaller >=6.0 onedir bundle the modules of ``src`` report a ``__file__``
under ``sys._MEIPASS`` (``dist/sape-f-mcp/_internal/``), so the data trees
below are placed at the same relative positions there that they have in the
checkout:

* ``gui_resources/`` — flags, icons and logos.
* ``legal-documents/`` — the legal document bodies read by
  ``legal_document_loader.py``.
* ``src/gui/styles/*.qss`` — the stylesheets ``src/gui/app.py`` loads from
  ``Path(__file__).parent / "styles"``.

The permissions database also defaults to a path next to ``main.py``, which
in a frozen bundle is inside ``_internal/`` — read-only under ``/opt`` and
replaced on every Windows upgrade. The installers' launchers therefore always
point it at a per-user data directory (``--db`` / ``$FILE_MCP_DB``).
"""

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

# `SPECPATH` is injected by PyInstaller: the directory this .spec lives in.
PROJECT_ROOT = Path(SPECPATH)  # noqa: F821 — injected by PyInstaller

block_cipher = None

# The mcp server stack picks its transport at run time (stdio, SSE,
# streamable HTTP); uvicorn in particular selects its protocol and loop
# implementations by import string, which a static import-graph walk misses.
# mcp.cli is the `mcp` developer command (needs the optional `typer` extra and
# calls sys.exit when it is absent); the server never imports it.
hidden_imports = [
    *collect_submodules("mcp", filter=lambda name: not name.startswith("mcp.cli")),
    *collect_submodules("uvicorn"),
]

a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / "gui_resources"), "gui_resources"),
        (str(PROJECT_ROOT / "legal-documents"), "legal-documents"),
        (str(PROJECT_ROOT / "src" / "gui" / "styles" / "*.qss"), "src/gui/styles"),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="sape-f-mcp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Console-subsystem, not windowed: main.py hides the console window itself
    # on Windows unless --cli is given, and --cli needs inherited stdio for the
    # MCP stdio transport.
    console=True,
    icon=str(PROJECT_ROOT / "gui_resources" / "icons" / "trans.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="sape-f-mcp",
)
