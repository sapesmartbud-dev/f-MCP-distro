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

"""Path resolution and the permission boundary that depends on it.

A client-supplied path is authorised as the string ``_resolve`` produces, but
acted on by the OS. If the two disagree the permission table is decorative.
They disagreed for any path ending in ``..``: :class:`~pathlib.Path` keeps that
component, so ``<grant>/..`` matched a rule on ``<grant>`` while the filesystem
read it as the parent — enough to list, chmod and recursively delete one level
above every granted directory.

These tests pin the agreement: what ``_resolve`` returns is normalised, and the
tools refuse anything the rules do not actually cover.
"""

from __future__ import annotations

import os

from pathlib import Path

import pytest

from src.mcp_server import FileMCPServer
from src.permissions import ACTIONS, PermissionDenied, PermissionStore


@pytest.fixture
def server(tmp_path: Path) -> FileMCPServer:
    """A server whose only grant is ``tmp_path/allowed``.

    ``tmp_path/secret`` is the sibling that must stay out of reach, and
    ``tmp_path`` itself is the parent a trailing ``..`` used to reach.
    """
    allowed = tmp_path / "allowed"
    secret = tmp_path / "secret"
    allowed.mkdir()
    secret.mkdir()
    (allowed / "inside.txt").write_text("in the grant", encoding="utf-8")
    (secret / "passwords.txt").write_text("TOPSECRET", encoding="utf-8")

    db = tmp_path / "permissions.db"
    store = PermissionStore(db_path=str(db))
    store.grant(allowed, actions="all", allow_subfolders=True)
    store.close()

    return FileMCPServer(db_path=str(db), base_dir=str(allowed))


def tool(server: FileMCPServer, name: str):
    """The callable registered under ``name``, as an MCP client would reach it."""
    return server.server._tool_manager._tools[name].fn


# -- _resolve ------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["..", "../", ".{sep}..", "a/..", "sub/../..", "", ".", "inside.txt", "../secret"],
)
def test_resolve_never_returns_a_dotdot_component(server: FileMCPServer, path: str) -> None:
    resolved = server._resolve(path.format(sep=os.sep))
    assert ".." not in resolved.parts
    assert resolved.is_absolute()


def test_trailing_dotdot_resolves_to_the_parent(server: FileMCPServer, tmp_path: Path) -> None:
    """The escape itself: '..' must name the parent, not '<grant>/..'."""
    assert server._resolve("..") == tmp_path
    assert server._resolve("a/..") == tmp_path / "allowed"
    assert server._resolve("sub/../..") == tmp_path


def test_absolute_form_of_the_escape_resolves_too(server: FileMCPServer, tmp_path: Path) -> None:
    assert server._resolve(str(tmp_path / "allowed" / "..")) == tmp_path


def test_resolution_inside_the_grant_is_unchanged(server: FileMCPServer, tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    assert server._resolve("inside.txt") == allowed / "inside.txt"
    assert server._resolve("") == allowed
    assert server._resolve(".") == allowed
    assert server._resolve("../secret") == tmp_path / "secret"


def test_null_byte_still_refused(server: FileMCPServer) -> None:
    with pytest.raises(ValueError, match="null byte"):
        server._resolve("inside\x00.txt")


# -- authorisation -------------------------------------------------------


@pytest.mark.parametrize("action", ACTIONS)
def test_no_action_is_authorised_on_the_parent(server: FileMCPServer, action: str) -> None:
    """All ten actions were granted on the directory; none reaches above it."""
    with pytest.raises(PermissionDenied):
        server._authorize(action, server._resolve(".."))


def test_actions_inside_the_grant_are_still_authorised(server: FileMCPServer) -> None:
    for action in ACTIONS:
        server._authorize(action, server._resolve("inside.txt"))


# -- the tools -----------------------------------------------------------


def test_list_of_the_parent_is_denied(server: FileMCPServer) -> None:
    with pytest.raises(PermissionDenied):
        tool(server, "list")(path="..")


def test_recursive_delete_of_the_parent_is_denied(server: FileMCPServer, tmp_path: Path) -> None:
    """The worst case: this used to remove the grant and its siblings."""
    with pytest.raises(PermissionDenied):
        tool(server, "delete")(path="..", recursive=True)

    assert (tmp_path / "secret" / "passwords.txt").exists()
    assert (tmp_path / "allowed" / "inside.txt").exists()


def test_recursive_chmod_of_the_parent_is_denied(server: FileMCPServer) -> None:
    with pytest.raises(PermissionDenied):
        tool(server, "chmod")(path="..", mode="777", recursive=True)


def test_sibling_directory_stays_denied(server: FileMCPServer, tmp_path: Path) -> None:
    """Paths that were already handled correctly must keep behaving."""
    with pytest.raises(PermissionDenied):
        tool(server, "read")(path="../secret/passwords.txt")
    with pytest.raises(PermissionDenied):
        tool(server, "read")(path=str(tmp_path / "secret" / "passwords.txt"))


def test_tools_still_work_inside_the_grant(server: FileMCPServer, tmp_path: Path) -> None:
    assert tool(server, "read")(path="inside.txt") == "in the grant"
    tool(server, "create")(path="made.txt", content="new")
    assert (tmp_path / "allowed" / "made.txt").read_text(encoding="utf-8") == "new"
    assert {e["path"] for e in tool(server, "list")(path=".")} == {"inside.txt", "made.txt"}


# -- the permission store itself -----------------------------------------


def test_rule_for_refuses_an_unnormalised_path(server: FileMCPServer, tmp_path: Path) -> None:
    """Fail closed if a future caller skips _resolve."""
    store = server.permissions
    with pytest.raises(ValueError, match="normalised absolute path"):
        store.rule_for(tmp_path / "allowed" / "..")
    with pytest.raises(ValueError, match="normalised absolute path"):
        store.rule_for("inside.txt")
    with pytest.raises(ValueError, match="normalised absolute path"):
        store.is_allowed(tmp_path / "allowed" / "..", "delete")
    with pytest.raises(ValueError, match="normalised absolute path"):
        store.require(tmp_path / "allowed" / "..", "delete")


def test_rule_for_still_resolves_normal_paths(server: FileMCPServer, tmp_path: Path) -> None:
    rule = server.permissions.rule_for(tmp_path / "allowed" / "inside.txt")
    assert rule is not None
    assert rule["path"] == str(tmp_path / "allowed")


def test_a_new_database_grants_nothing(tmp_path: Path) -> None:
    """No rules are seeded: an empty database authorises nothing at all."""
    server = FileMCPServer(db_path=str(tmp_path / "fresh.db"), base_dir=str(tmp_path))
    assert server.permissions.rules() == []
    for action in ACTIONS:
        with pytest.raises(PermissionDenied):
            server._authorize(action, server._resolve("anything.txt"))
    with pytest.raises(PermissionDenied):
        server._authorize("read", Path.home() / "Documents")
