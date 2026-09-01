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

"""A link inside a granted directory must not lead out of it.

Authorising the path a client sent is not enough when the filesystem will
follow a link somewhere else. Two ways that used to leak:

* ``copy`` and ``download`` authorised only the top of a directory tree, then
  handed it to ``shutil.copytree``, which follows links by default — so a link
  inside a granted directory had its target *content* copied out.
* ``list`` filtered entries by their literal path, and an entry reached through
  a link still looks as though it sits inside the directory being listed.

The tests use a Windows directory junction where one is available. A junction
needs no special privileges (a symlink does), and ``Path.is_symlink()`` reports
False for one, so it is the case an ``is_symlink()``-based guard misses.
"""

from __future__ import annotations

import subprocess
import sys

from pathlib import Path

import pytest

from src.mcp_server import FileMCPServer
from src.permissions import PermissionDenied, PermissionStore


def make_dir_link(link: Path, target: Path) -> None:
    """Point ``link`` at directory ``target``, or skip if the platform refuses."""
    if sys.platform == "win32":
        done = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            text=True,
        )
        if done.returncode != 0 or not link.exists():
            pytest.skip(f"cannot create a junction here: {done.stdout or done.stderr}")
    else:
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as exc:  # no privilege, or a filesystem without links
            pytest.skip(f"cannot create a symlink here: {exc}")


@pytest.fixture
def server(tmp_path: Path):
    """A grant on ``allowed/`` that contains a link out to an ungranted ``secret/``."""
    allowed = tmp_path / "allowed"
    secret = tmp_path / "secret"
    allowed.mkdir()
    secret.mkdir()
    (allowed / "ordinary.txt").write_text("in the grant", encoding="utf-8")
    (secret / "passwords.txt").write_text("TOPSECRET", encoding="utf-8")

    link = allowed / "linked"
    make_dir_link(link, secret)

    db = tmp_path / "permissions.db"
    store = PermissionStore(db_path=str(db))
    store.grant(allowed, actions="all", allow_subfolders=True)
    store.close()

    yield FileMCPServer(db_path=str(db), base_dir=str(allowed))

    # Drop the link before teardown: rmtree follows a junction, and would empty
    # the target rather than just removing the link to it.
    try:
        link.rmdir()
    except OSError:
        pass


def tool(server: FileMCPServer, name: str):
    return server.server._tool_manager._tools[name].fn


def test_recursive_copy_does_not_pull_content_through_the_link(
    server: FileMCPServer, tmp_path: Path
) -> None:
    with pytest.raises(PermissionDenied):
        tool(server, "copy")(
            source=".", destination=str(tmp_path / "allowed" / "clone"), recursive=True
        )
    assert not (tmp_path / "allowed" / "clone" / "linked" / "passwords.txt").exists()
    assert (tmp_path / "secret" / "passwords.txt").read_text(encoding="utf-8") == "TOPSECRET"


def test_download_does_not_stage_content_from_beyond_the_link(server: FileMCPServer) -> None:
    with pytest.raises(PermissionDenied):
        tool(server, "download")(path=".")


def test_listing_hides_entries_reached_through_the_link(server: FileMCPServer) -> None:
    entries = {e["path"] for e in tool(server, "list")(path=".", recursive=True)}
    assert not any("passwords.txt" in e for e in entries)
    assert "ordinary.txt" in entries


def test_reading_straight_through_the_link_is_denied(server: FileMCPServer) -> None:
    with pytest.raises(PermissionDenied):
        tool(server, "read")(path="linked/passwords.txt")


def test_ordinary_tree_operations_still_work(server: FileMCPServer, tmp_path: Path) -> None:
    """The guard must not cost the granted directory its own subtrees."""
    allowed = tmp_path / "allowed"
    (allowed / "sub").mkdir()
    (allowed / "sub" / "note.txt").write_text("kept", encoding="utf-8")

    tool(server, "copy")(source="sub", destination=str(allowed / "subclone"), recursive=True)
    assert (allowed / "subclone" / "note.txt").read_text(encoding="utf-8") == "kept"

    staged = Path(tool(server, "download")(path="sub"))
    assert (staged / "note.txt").read_text(encoding="utf-8") == "kept"
