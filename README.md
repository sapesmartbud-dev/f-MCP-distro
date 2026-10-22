# SAPÉ f-MCP

**Controlled file system access for LLMs, with a permission database you actually manage.**

SAPÉ f-MCP is a [Model Context Protocol](https://modelcontextprotocol.io) server that exposes file operations to an LLM client — Claude Desktop, or anything else that speaks MCP — and refuses any path that isn't covered by an explicit rule. It ships with a desktop GUI for writing those rules and watching what the model actually did.

**This is version 0.2.1.2**
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

---

## What it does

Eleven MCP tools: ten file operations plus one for introspecting your own rules.

| Tool | What it does |
|---|---|
| `create` | Create a file (with content) or a directory |
| `read` | Read a text file |
| `edit` | Replace, insert, or append within a file |
| `delete` | Delete a file or directory (`recursive` opt-in) |
| `move` | Move or rename |
| `copy` | Copy a file or tree |
| `list` | List a directory (`recursive`, `include_hidden`) |
| `chmod` | Change POSIX permission bits |
| `download` | Stage a copy of a file or tree for the client |
| `upload` | Write a file from base64 or text |
| `show-permissions` | Return the current rule set |

Every path is resolved to an absolute path and checked against a SQLite `permissions` table before any work happens. **Paths that no rule covers are refused** — there is no implicit grant, and `--base-dir` only anchors relative paths, it doesn't authorize anything.

Rules are per-path, per-action, with an `allow_subfolders` flag. The ten actions are granted independently, so "read but never delete" is a rule you can actually write.

### Links, and what a path really points at

A path is authorized as the thing the filesystem will actually act on, not as the string the client sent. Two consequences:

* A path ending in `..` is resolved before it is checked, so it cannot be used to reach the parent of a granted directory.
* Operations that dereference — `create`, `edit`, `copy`, `list`, `chmod`, `read`, `download`, `upload` — require the **resolved target** to be authorized too. A link planted inside an allowed directory can't be used to reach a path no rule covers. This covers Windows directory junctions, not only symlinks: `Path.is_symlink()` reports `False` for a junction, so the check compares resolved paths instead of asking whether something is a link.
* `copy` and `download` authorize **every entry** of a directory tree before copying it, because the copy follows links out of the tree. `delete` and `chmod` do the same for their recursive forms.

`delete` and `move` act on the link itself rather than its target, so they are checked against the link's own path. `move` of a directory is checked on the source and destination only — see [Known limitations](#known-limitations).

---

## Requirements

- Python 3.10 or newer
- `mcp` 2.0 or newer (the server uses the 2.x `MCPServer` API; 1.x fails at import)
- PyQt6 — **only for the GUI**. `main.py --cli` runs headless and never imports it.

### Platform support

| Platform | Status |
|---|---|
| **Windows** | Verified — Windows 11, Python 3.12, mcp 2.0.0, PyQt6 6.11 |
| **Linux** | Verified — Ubuntu 24.04 (WSL2), Python 3.12, mcp 2.1.1, PyQt6 6.11 |
| **macOS** | **Not verified** — no macOS machine was available for testing |

On Windows and Linux the full test suite passes, all eleven tools were exercised over a real MCP stdio session, and the GUI renders every page. `chmod` was confirmed to set POSIX bits on Linux; on Windows it only toggles the read-only attribute and shouldn't be relied on as a control.

macOS is POSIX like Linux and nothing in the code is expected to fail there, but "expected" is not "tested". One macOS-specific caveat is described under [Known limitations](#known-limitations); please read it before relying on a deny-exception rule.

---

## Running it

```bash
cd f-mcp
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

python main.py
```

That launches the GUI. `python main.py --cli` starts the server headless on stdio without one.

For a **server-only install** — which is all an MCP client needs — PyQt6 is unnecessary:

```bash
pip install "mcp>=2.0"
python main.py --cli
```

> **A note on packaging:** the wheel built from `pyproject.toml` does not currently install correctly — the package layout ships as a top-level `src` package and omits the GUI subpackages and the data directories, so the `sape-f-mcp` console script fails on a clean install. Run from source until that's fixed; PyPI publication and MCP-registry listing are waiting on it. The MCP configuration wizard detects a broken console script and generates a source-based configuration instead of failing.

### Command line

```
python main.py [--db PATH] [--base-dir DIR] [--transport {stdio,sse,streamable-http}]
               [--show-permissions] [--cli] [--version]
```

| Flag | Meaning |
|---|---|
| `--db` | SQLite permissions database. Defaults to `$FILE_MCP_DB`, else `./permissions.db` next to the script |
| `--base-dir` | Directory that relative paths resolve against. Defaults to `$FILE_MCP_BASE`, else the cwd. **Grants nothing by itself** |
| `--transport` | Transport to serve on. Default `stdio` |
| `--show-permissions` | Print the rule set and exit |
| `--cli` | Start the server immediately, no GUI |
| `--version` | Print the version and exit |

### Connecting an MCP client

The GUI generates this for you: **Settings → MCP Configuration**. It detects how this copy is installed, names the interpreter it is itself running on, and pins `--db` to the database you are editing, so the process your client spawns enforces the rules you see on screen. Copy the JSON and merge it into your client's config:

| Client | Config file |
|---|---|
| Claude Desktop (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Desktop (Linux) | `~/.config/Claude/claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "sape-f-mcp": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": [
        "/absolute/path/to/f-mcp/main.py",
        "--cli", "--transport", "stdio",
        "--db", "/absolute/path/to/f-mcp/permissions.db"
      ],
      "env": {}
    }
  }
}
```

On Windows the command is `...\.venv\Scripts\python.exe`. **Merge** this into the file — don't replace it, or you will drop the other servers you have configured. Restart the client afterwards.

Use an absolute path to a Python that has `mcp` installed. A bare `"python"` is resolved in the client's environment, which is usually not the one you installed into.

---

## First run

**The permission list starts empty, and an empty list authorizes nothing.** No default rule is created — not for your home directory, not for the working directory, not for anything. Until you add a rule yourself, every tool call is refused.

Open the Permissions page, click **New Rule**, and grant the narrowest path that does the job — a single project directory rather than a home directory, and only the actions you actually want. "Read and list, never delete" is a rule you can write, and it is usually the right one to start from.

Nothing is ever granted behind your back: rules only come from this page, and they are stored in `permissions.db`, which you can inspect at any time with `python main.py --show-permissions`.

---

## The GUI

PyQt6 desktop app, dark and light themes, system tray, 18 selectable interface languages.

- **Permissions** — add, edit, and remove rules; per-action checkboxes; subfolder toggle
- **Session Log** — every tool call as it happens, allowed and denied
- **Settings** — theme, language, and the MCP configuration wizard
- **Help / Legal / About** — documentation and the license

**On the languages:** all 18 are selectable and the Spanish translation is complete, but the other seventeen are roughly 60% untranslated — those strings fall back to English. Treat anything other than English and Spanish as a work in progress.

**On the session log:** it is **not** an archive and not a rolling window. The GUI **deletes the entire log database on every start**, and nothing is evicted during a session. If you need a durable audit trail, export before closing the application, or read `tool_log.jsonl` (written next to `permissions.db`), which is append-only and is not wiped.

---

## What this is not

**It's a permission system, not a sandbox.** It enforces path-based access control inside its own tool calls. It does not give you kernel-level enforcement, protection against privilege escalation, or a security boundary against an adversarial LLM client. The server runs with your user privileges: everything *inside* the rules you wrote stays reachable. Grant narrowly.

See [DISCLAIMER.md](DISCLAIMER.md) for the full risk notice and [DATA-PROTECTION.md](DATA-PROTECTION.md) for what's stored locally (nothing leaves your machine).

### Known limitations

Things worth knowing before you rely on this. None of them is a secret; they are listed here rather than discovered later.

- **`move` of a directory** is authorized on the source and destination only, not on each entry inside it. `delete`, `chmod`, `copy` and `download` do check every entry.
- **`read` does not truncate.** A very large file is returned in full, which can overwhelm a client.
- **`download` stages copies in the system temp directory** (`%TEMP%\sape_download`, `/tmp/sape_download`) and never cleans them up. Those copies sit outside the permission model, and on Linux the staging directory is world-readable by default.
- **The HTTP transports have no authentication.** When the GUI starts the server it listens on `127.0.0.1:8089`. Browser-origin requests are rejected, but any local process can connect and use every tool the rules allow. `stdio` has no such exposure — prefer it.
- **macOS, and any case-insensitive filesystem:** rule matching compares paths case-sensitively on POSIX. On a case-insensitive volume `~/Secret` and `~/secret` are the same directory but not the same rule, so a narrow deny-exception carved out of a broader grant can be sidestepped by changing the case of a path component. Windows is unaffected (its path comparison is already case-insensitive). Until this is addressed, prefer *granting narrowly* over granting broadly and carving exceptions out.
- **`chmod` on Windows** only toggles the read-only attribute.

---

## Development

```
main.py                  Entry point — GUI, or --cli for headless
src/mcp_server.py        The MCP server and the eleven tools
src/permissions.py       SQLite permission store, path authorization
src/log_store.py         Session log storage
src/tool_logger.py       JSONL + SQLite tool-call logging
src/mcp_config_generator.py   Client configuration for this installation
src/_version.py          Single source of truth for the version
src/gui/                 PyQt6 application
tests/                   pytest suite
legal-documents/en-US/   Legal documents shown in the GUI
gui_resources/           Icons, logos, flags
```

### Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

The suite covers the permission boundary specifically: path resolution and the trailing-`..` escape, links leading out of a granted tree (using a junction on Windows, a symlink elsewhere; it skips itself where the platform refuses to create one), and an end-to-end check that the configuration the GUI generates actually launches a server and lists all eleven tools.

---

## License

**GPL-3.0-only.** SAPÉ f-MCP is free software: you may run, study, modify, and redistribute it, including commercially, provided you pass on the same freedoms under the same license and make corresponding source available. The full text is in [LICENSE](LICENSE); [LEGAL-README.md](LEGAL-README.md) has a plain-language guide and a redistributor checklist.

"Version 3 only" — the "or any later version" clause is not granted.

This program links **PyQt6**, which is itself GPL-licensed. A fork therefore cannot be relicensed under permissive or proprietary terms while keeping PyQt6.

**SAPÉ** and **SAPÉ f-MCP** are the author's marks. The GPL is a copyright license and doesn't transfer them — fork freely, but give your fork its own name.

Legal documents are maintained in English only: the GNU GPL is legally authoritative in English and the FSF publishes no binding translations, so a translated license would carry no legal force. The interface itself stays localized.

---

## Author

**SAPÉ smart bud** — [sapebud.com](https://sapebud.com)

Copyright © 2026 Luciano Arrezze. This program comes with ABSOLUTELY NO WARRANTY; see sections 15–17 of the [LICENSE](LICENSE).
