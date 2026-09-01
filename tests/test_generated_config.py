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

"""The configuration the wizard hands the user has to start a server.

Asserting on the shape of the JSON is not enough — the previous version looked
plausible and named a module that does not exist, an interpreter that need not
have the dependencies, and no ``--cli``, so the command opened the GUI instead
of speaking the protocol. So this launches what the wizard produces and talks
MCP to it.
"""

from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading

from pathlib import Path

import pytest

from src.mcp_config_generator import MCPConfigGenerator


TIMEOUT = 60  # generous: the child imports Qt before it reaches the server


@pytest.fixture(scope="module")
def installation():
    detected = MCPConfigGenerator().detect_installation()
    if not detected.is_valid:
        pytest.fail(f"installation not detected: {detected.error_message}")
    return detected


@pytest.fixture
def config(installation, tmp_path: Path) -> dict:
    """The mcpServers entry the wizard would show, pointed at a scratch database."""
    return MCPConfigGenerator().generate_config(installation, db_path=tmp_path / "permissions.db")


class Client:
    """Just enough JSON-RPC over stdio to prove the server is really there."""

    def __init__(self, command: list[str]):
        self.proc = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._lines: queue.Queue[str | None] = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()
        self._id = 0

    def _pump(self) -> None:
        for line in self.proc.stdout:  # type: ignore[union-attr]
            self._lines.put(line)
        self._lines.put(None)

    def call(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        message: dict[str, object] = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message) + "\n")  # type: ignore[union-attr]
        self.proc.stdin.flush()  # type: ignore[union-attr]
        while True:
            try:
                line = self._lines.get(timeout=TIMEOUT)
            except queue.Empty:
                pytest.fail(f"no reply to {method} within {TIMEOUT}s")
            if line is None:
                pytest.fail(f"server exited before replying to {method}")
            if not line.strip():
                continue
            try:
                reply = json.loads(line)
            except json.JSONDecodeError:
                continue  # not protocol traffic
            if reply.get("id") == self._id:
                return reply

    def notify(self, method: str, params: dict | None = None) -> None:
        message: dict[str, object] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.proc.stdin.write(json.dumps(message) + "\n")  # type: ignore[union-attr]
        self.proc.stdin.flush()  # type: ignore[union-attr]

    def close(self) -> None:
        try:
            self.proc.stdin.close()  # type: ignore[union-attr]
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()


def test_command_is_an_interpreter_that_can_import_the_package(config: dict) -> None:
    """A bare 'python' would be resolved in the client environment, not ours."""
    assert Path(config["command"]).is_absolute()
    assert Path(config["command"]).exists()


def test_config_carries_cli_or_it_would_open_the_gui(config: dict) -> None:
    assert "--cli" in config["args"]
    assert config["args"][config["args"].index("--transport") + 1] == "stdio"


def test_config_names_the_database_the_gui_is_using(config: dict, tmp_path: Path) -> None:
    assert config["args"][config["args"].index("--db") + 1] == str(tmp_path / "permissions.db")


def version_command(config: dict) -> list[str]:
    """The generated command with --version in place of the server flags."""
    args = config["args"]
    script = [args[0]] if args and not args[0].startswith("--") else []
    return [config["command"], *script, "--version"]


def test_version_flag_exists(config: dict) -> None:
    """detect_installation and the dialog's Test Connection both rely on it."""
    done = subprocess.run(
        version_command(config), capture_output=True, text=True, timeout=TIMEOUT
    )
    assert done.returncode == 0, done.stderr
    assert "f-MCP" in done.stdout


def test_generated_config_actually_starts_a_server(config: dict) -> None:
    """The blocker itself: launch what the wizard emits and speak MCP to it."""
    client = Client([config["command"], *config["args"]])
    try:
        reply = client.call(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "sape-config-test", "version": "1"},
            },
        )
        assert "result" in reply, reply
        client.notify("notifications/initialized", {})

        listed = client.call("tools/list", {})
        names = {tool["name"] for tool in listed["result"]["tools"]}
        assert names == {
            "create", "delete", "move", "copy", "list", "edit",
            "chmod", "read", "download", "upload", "show-permissions",
        }
    finally:
        client.close()


@pytest.mark.skipif(sys.platform != "win32", reason="pythonw is Windows-only")
def test_windows_gui_interpreter_is_mapped_to_the_console_one() -> None:
    """A GUI started via pythonw.exe must still hand the client python.exe."""
    launcher = MCPConfigGenerator._launcher()
    assert launcher.name.lower() != "pythonw.exe"


def test_settings_page_offers_the_same_config_as_the_wizard(
    installation, tmp_path: Path
) -> None:
    """The Settings box used to show a five-key reference document under the
    label "Copy this JSON to your LLM's configuration file" — four of those keys
    are not valid in a client config, and it named two servers. It now shows the
    wizard's entry verbatim, under the wizard's name, so what the tests above
    launch is what the page hands the user."""
    from src.config_json_generator import ConfigJSONGenerator

    class Permissions:
        db_path = str(tmp_path / "permissions.db")

    class Server:
        permissions = Permissions()
        port = 8089

    shown = json.loads(ConfigJSONGenerator(Server()).to_client_config_string())
    expected = MCPConfigGenerator().generate_config(
        installation, db_path=Permissions.db_path
    )

    assert shown == {"mcpServers": {"sape-f-mcp": expected}}
    assert "--cli" in shown["mcpServers"]["sape-f-mcp"]["args"]
    # Nothing a client would reject: no reference keys, no unknown fields.
    assert list(shown) == ["mcpServers"]
    assert set(shown["mcpServers"]["sape-f-mcp"]) == {"command", "args", "env"}
