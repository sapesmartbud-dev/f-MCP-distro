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

# Create a class that implements an MCP server
# File MCP-Server  (create, delete, move, copy, list, edit, chmod)

from __future__ import annotations

import base64
import os
import shutil
import stat
import tempfile
import uuid
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from mcp.server import MCPServer
from mcp.types import ToolAnnotations

from src._version import __version__
from src.permissions import ACTIONS, PermissionStore
from src.tool_logger import ToolLogger

if TYPE_CHECKING:
    from src.log_store import LogStore

_MODE_HELP = "octal permission string, e.g. '644' or '0o755'"

# Operations whose implementation follows a final symlink to its target
# (writes, reads and chmod all dereference). For these the real target must
# be authorised too, otherwise a symlink planted inside an allowed directory
# could be used to reach a path no rule covers. 'delete' and 'move' act on
# the link itself, so they are checked only against the link's own path.
_DEREFERENCING = frozenset({"create", "edit", "copy", "list", "chmod", "read", "download", "upload"})


class FileMCPServer:
    """An MCP server exposing file system operations as tools.

    Access is governed entirely by the ``permissions`` table of a SQLite
    database (see :mod:`src.permissions`). Every path a tool touches is
    resolved to an absolute path and checked against that table before any
    work happens; paths no rule covers are refused. Operations taking two
    paths (move, copy) are checked on both ends.
    """

    def __init__(
        self,
        db_path: str | os.PathLike[str] | None = None,
        base_dir: str | os.PathLike[str] | None = None,
        user: str | None = None,
        name: str = "file-mcp-server",
        log_store: Optional["LogStore"] = None,
        session_id: Optional[str] = None,
    ):
        # base_dir only anchors relative paths; it grants nothing by itself.
        self.base_dir = Path(base_dir or os.environ.get("FILE_MCP_BASE", Path.cwd())).expanduser().resolve()
        # No default rules are seeded: a new database starts empty and
        # authorises nothing until the user grants a path explicitly.
        self.permissions = PermissionStore(db_path, user=user)

        # Initialize logger for tool executions (both JSONL and SQLite if configured)
        # Logs to tool_log.jsonl in the same directory as permissions.db
        # Also logs to SQLite if log_store and session_id are provided
        self.logger = ToolLogger(
            db_path=str(self.permissions.db_path),
            log_store=log_store,
            session_id=session_id
        )

        self.server = MCPServer(
            name=name,
            version=__version__,
            instructions=(
                "File system tools (create, delete, move, copy, list, edit, chmod, read, download, upload). "
                f"Relative paths resolve against {self.base_dir}. Access is restricted to the "
                "paths and operations recorded in the permissions database; anything else is refused."
            ),
        )

        # Callback for when tools are executed (for logging/UI updates)
        self.tool_executed_callback = None

        self._register_tools()

    def set_tool_executed_callback(self, callback):
        """Set a callback to be called when tools are executed.

        Args:
            callback: Function(tool_name, params, result, error) called after each tool execution.
        """
        self.tool_executed_callback = callback

    def set_log_store(self, log_store: "LogStore", session_id: str) -> None:
        """Update the logger to use SQLite logging.

        Called after app initialization to enable SQLite logging.

        Args:
            log_store: LogStore instance for SQLite logging.
            session_id: Session ID for this app instance.

        Raises:
            ValueError: If session_id is not provided.
        """
        if not session_id:
            raise ValueError("session_id is required")
        self.logger.log_store = log_store
        self.logger.session_id = session_id

    # -- helpers ---------------------------------------------------------

    def _emit_tool_executed(self, tool_name: str, params: dict, result: str = None, error: str = None) -> None:
        """Emit tool execution to JSONL logger and callback (if registered).

        Writes to tool_log.jsonl atomically to ensure both the GUI process and
        CLI spawned by Claude Desktop see the same log. The callback is maintained
        for backward compatibility with in-process GUI signal handlers.
        """
        # Write to JSONL logger (always, regardless of callback)
        # This ensures tool executions are logged even if no callback is registered
        try:
            self.logger.log_execution(tool_name, params, result, error)
        except Exception:
            pass  # Don't crash tool execution if logging fails

        # Also emit callback if registered (for in-process GUI signals)
        if self.tool_executed_callback:
            try:
                self.tool_executed_callback(tool_name, params, result, error)
            except Exception:
                pass  # Don't let callback errors break tool execution

    def _resolve(self, path: str) -> Path:
        """Resolve a client-supplied path to an absolute path.

        Everything except the final component is resolved strictly, so that
        ``..`` and symlinked parent directories cannot be used to land
        somewhere the permission check would not see. A final symlink is left
        unresolved so that deleting a link deletes the link itself; a final
        ``..`` is not a symlink, so it is resolved like the rest of the path
        rather than reaching the permission check verbatim — otherwise the
        check would match a rule on the directory the ``..`` was written
        relative to, while the OS acted on its parent.
        """
        if "\x00" in path:
            raise ValueError("path contains a null byte")
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.base_dir / candidate
        if candidate.name == "..":
            # '..' is never a symlink, so resolving it in full matches what the
            # OS will do and keeps the permission check on the real target.
            resolved = candidate.resolve()
        else:
            parent = candidate.parent.resolve()
            resolved = parent if candidate.name in ("", ".") else parent / candidate.name
        if ".." in resolved.parts:  # unreachable; guards future edits
            raise ValueError(f"path could not be normalised: {path!r}")
        return resolved

    def _check_paths(self, action: str, path: Path) -> tuple[Path, ...]:
        """Every path that must be authorised for ``action`` on ``path``.

        An operation that dereferences needs the real target authorised as
        well, or a link planted inside an allowed directory would reach a path
        no rule covers. The comparison is against the resolved path rather than
        ``is_symlink()``, which reports False for a Windows directory junction
        — a reparse point that ``shutil`` and ``glob`` follow like any other
        link.
        """
        if action not in _DEREFERENCING:
            return (path,)
        resolved = path.resolve()
        return (path,) if resolved == path else (path, resolved)

    def _authorize(self, action: str, *paths: Path) -> None:
        """Enforce ``action`` on every path involved in the operation."""
        for path in paths:
            for target in self._check_paths(action, path):
                self.permissions.require(target, action)

    @staticmethod
    def _parse_mode(mode: str) -> int:
        """Parse an octal permission string such as '644' or '0o755'."""
        try:
            value = int(mode, 8)
        except ValueError:
            raise ValueError(f"mode must be an {_MODE_HELP}: got {mode!r}") from None
        if not 0 <= value <= 0o7777:
            raise ValueError(f"mode out of range: {mode}")
        return value

    # -- tools -----------------------------------------------------------

    def _register_tools(self) -> None:
        server = self.server

        @server.tool(
            name="create",
            description=(
                "Create a file (optionally with content) or a directory. "
                "Parent directories are created as needed. Requires 'create' permission."
            ),
            annotations=ToolAnnotations(title="Create file or directory", destructive_hint=False),
        )
        def create(path: str, content: str = "", directory: bool = False, overwrite: bool = False) -> str:
            """Create a file or directory.

            Args:
                path: Destination path.
                content: Text written to the new file. Ignored for directories.
                directory: Create a directory instead of a file.
                overwrite: Allow replacing an existing file.
            """
            try:
                target = self._resolve(path)
                self._authorize("create", target)
                if directory:
                    target.mkdir(parents=True, exist_ok=True)
                    result = f"Created directory {target}"
                else:
                    if target.exists() and not overwrite:
                        raise FileExistsError(f"{target} already exists (pass overwrite=true)")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content, encoding="utf-8")
                    result = f"Created file {target} ({len(content)} chars)"
                self._emit_tool_executed("create", {"path": path, "content": content[:100], "directory": directory, "overwrite": overwrite}, result, None)
                return result
            except Exception as e:
                self._emit_tool_executed("create", {"path": path, "content": content[:100], "directory": directory, "overwrite": overwrite}, None, str(e))
                raise

        @server.tool(
            name="delete",
            description="Delete a file, or a directory when recursive is true. Requires 'delete' permission.",
            annotations=ToolAnnotations(title="Delete path", destructive_hint=True),
        )
        def delete(path: str, recursive: bool = False) -> str:
            """Delete a path.

            Args:
                path: Path to delete.
                recursive: Required to delete a non-empty directory.
            """
            try:
                target = self._resolve(path)
                self._authorize("delete", target)
                if not target.exists() and not target.is_symlink():
                    raise FileNotFoundError(str(target))
                if target.is_dir() and not target.is_symlink():
                    # Every entry below the tree must be deletable too.
                    if recursive:
                        for entry in target.rglob("*"):
                            self._authorize("delete", entry)
                        shutil.rmtree(target)
                    else:
                        target.rmdir()  # raises OSError if not empty
                    result = f"Deleted directory {target}"
                else:
                    target.unlink()
                    result = f"Deleted file {target}"
                self._emit_tool_executed("delete", {"path": path, "recursive": recursive}, result, None)
                return result
            except Exception as e:
                self._emit_tool_executed("delete", {"path": path, "recursive": recursive}, None, str(e))
                raise

        @server.tool(
            name="move",
            description=(
                "Move or rename a file or directory. "
                "Requires 'move' permission on both the source and the destination."
            ),
            annotations=ToolAnnotations(title="Move or rename", destructive_hint=True),
        )
        def move(source: str, destination: str, overwrite: bool = False) -> str:
            """Move or rename a path.

            Args:
                source: Existing path.
                destination: New path. If it is an existing directory, source is moved into it.
                overwrite: Allow replacing an existing destination file.
            """
            try:
                src = self._resolve(source)
                dst = self._resolve(destination)
                if dst.is_dir() and not dst.is_symlink():
                    dst = dst / src.name
                self._authorize("move", src, dst)
                if not src.exists() and not src.is_symlink():
                    raise FileNotFoundError(str(src))
                if dst.exists() and not overwrite:
                    raise FileExistsError(f"{dst} already exists (pass overwrite=true)")
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                result = f"Moved {src} -> {dst}"
                self._emit_tool_executed("move", {"source": source, "destination": destination, "overwrite": overwrite}, result, None)
                return result
            except Exception as e:
                self._emit_tool_executed("move", {"source": source, "destination": destination, "overwrite": overwrite}, None, str(e))
                raise

        @server.tool(
            name="copy",
            description=(
                "Copy a file, or a directory tree when recursive is true. "
                "Requires 'copy' permission on both the source and the destination."
            ),
            annotations=ToolAnnotations(title="Copy path", destructive_hint=False),
        )
        def copy(source: str, destination: str, recursive: bool = False, overwrite: bool = False) -> str:
            """Copy a file or directory.

            Args:
                source: Existing path.
                destination: Target path. If it is an existing directory, source is copied into it.
                recursive: Required to copy a directory.
                overwrite: Allow replacing an existing destination.
            """
            try:
                src = self._resolve(source)
                dst = self._resolve(destination)
                if dst.is_dir() and src.is_file():
                    dst = dst / src.name
                self._authorize("copy", src, dst)
                if not src.exists():
                    raise FileNotFoundError(str(src))
                if dst.exists() and not overwrite:
                    raise FileExistsError(f"{dst} already exists (pass overwrite=true)")
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src.is_dir():
                    if not recursive:
                        raise IsADirectoryError(f"{src} is a directory (pass recursive=true)")
                    # Every entry below the tree is copied too, and copytree
                    # follows links, so each one must be copyable — target
                    # included, or a link inside the tree would pull in content
                    # from a path no rule covers.
                    self._authorize("copy", *src.rglob("*"))
                    shutil.copytree(src, dst, dirs_exist_ok=overwrite)
                    result = f"Copied directory {src} -> {dst}"
                else:
                    shutil.copy2(src, dst)
                    result = f"Copied file {src} -> {dst}"
                self._emit_tool_executed("copy", {"source": source, "destination": destination, "recursive": recursive, "overwrite": overwrite}, result, None)
                return result
            except Exception as e:
                self._emit_tool_executed("copy", {"source": source, "destination": destination, "recursive": recursive, "overwrite": overwrite}, None, str(e))
                raise

        @server.tool(
            name="list",
            description=(
                "List directory entries with type, size and permissions. Requires 'list' permission."
            ),
            annotations=ToolAnnotations(title="List directory", read_only_hint=True),
        )
        def list_dir(path: str = ".", recursive: bool = False, include_hidden: bool = False) -> list[dict]:
            """List a directory.

            Args:
                path: Directory to list.
                recursive: Walk subdirectories as well.
                include_hidden: Include entries whose name starts with a dot.
            """
            try:
                target = self._resolve(path)
                self._authorize("list", target)
                if not target.is_dir():
                    raise NotADirectoryError(str(target))
                entries = sorted(target.rglob("*") if recursive else target.glob("*"))
                listing = []
                for entry in entries:
                    if not include_hidden and any(part.startswith(".") for part in entry.relative_to(target).parts):
                        continue
                    # Hide anything the caller is not allowed to see, including
                    # an entry that only looks as though it sits inside the
                    # listed directory because a link leads out of it.
                    if not all(
                        self.permissions.is_allowed(p, "list")
                        for p in self._check_paths("list", entry)
                    ):
                        continue
                    info = entry.lstat()
                    listing.append(
                        {
                            "path": str(entry.relative_to(target)),
                            "type": "directory" if entry.is_dir() else "symlink" if entry.is_symlink() else "file",
                            "size": info.st_size,
                            "mode": oct(stat.S_IMODE(info.st_mode))[2:].rjust(3, "0"),
                        }
                    )
                result = f"Listed {len(listing)} entries"
                self._emit_tool_executed("list", {"path": path, "recursive": recursive, "include_hidden": include_hidden}, result, None)
                return listing
            except Exception as e:
                self._emit_tool_executed("list", {"path": path, "recursive": recursive, "include_hidden": include_hidden}, None, str(e))
                raise

        @server.tool(
            name="edit",
            description=(
                "Edit a text file: replace an exact string, append, or overwrite the whole file. "
                "Requires 'edit' permission."
            ),
            annotations=ToolAnnotations(title="Edit file", destructive_hint=True),
        )
        def edit(
            path: str,
            content: str = "",
            old_string: str | None = None,
            mode: str = "replace",
            replace_all: bool = False,
        ) -> str:
            """Edit a text file.

            Args:
                path: File to edit.
                content: Replacement text (mode 'replace'/'overwrite') or text to append.
                old_string: Exact text to replace; required for mode 'replace'.
                mode: One of 'replace', 'append', 'overwrite'.
                replace_all: Replace every occurrence instead of requiring a unique match.
            """
            try:
                target = self._resolve(path)
                self._authorize("edit", target)
                if mode not in {"replace", "append", "overwrite"}:
                    raise ValueError(f"unknown mode: {mode}")
                if mode == "overwrite":
                    target.write_text(content, encoding="utf-8")
                    result = f"Overwrote {target} ({len(content)} chars)"
                else:
                    if not target.is_file():
                        raise FileNotFoundError(str(target))
                    text = target.read_text(encoding="utf-8")

                    if mode == "append":
                        target.write_text(text + content, encoding="utf-8")
                        result = f"Appended {len(content)} chars to {target}"
                    else:  # mode == "replace"
                        if not old_string:
                            raise ValueError("old_string is required for mode 'replace'")
                        occurrences = text.count(old_string)
                        if occurrences == 0:
                            raise ValueError(f"old_string not found in {target}")
                        if occurrences > 1 and not replace_all:
                            raise ValueError(
                                f"old_string appears {occurrences} times in {target}; "
                                "make it unique or pass replace_all=true"
                            )
                        target.write_text(text.replace(old_string, content), encoding="utf-8")
                        result = f"Replaced {occurrences if replace_all else 1} occurrence(s) in {target}"
                self._emit_tool_executed("edit", {"path": path, "mode": mode, "replace_all": replace_all}, result, None)
                return result
            except Exception as e:
                self._emit_tool_executed("edit", {"path": path, "mode": mode, "replace_all": replace_all}, None, str(e))
                raise

        @server.tool(
            name="chmod",
            description=(
                f"Change permissions of a file or directory using an {_MODE_HELP}. "
                "Requires 'chmod' permission."
            ),
            annotations=ToolAnnotations(title="Change permissions", destructive_hint=True),
        )
        def chmod(path: str, mode: str, recursive: bool = False) -> str:
            """Change file permissions.

            Args:
                path: Path to modify.
                mode: Octal permission string, e.g. '644' or '0o755'.
                recursive: Apply to every entry below a directory as well.
            """
            try:
                target = self._resolve(path)
                self._authorize("chmod", target)
                if not target.exists():
                    raise FileNotFoundError(str(target))
                bits = self._parse_mode(mode)
                targets = [target]
                if recursive and target.is_dir():
                    subtree = [e for e in target.rglob("*") if not e.is_symlink()]
                    self._authorize("chmod", *subtree)
                    targets.extend(subtree)
                for entry in targets:
                    entry.chmod(bits)
                result = f"Set mode {oct(bits)[2:].rjust(3, '0')} on {len(targets)} path(s) under {target}"
                self._emit_tool_executed("chmod", {"path": path, "mode": mode, "recursive": recursive}, result, None)
                return result
            except Exception as e:
                self._emit_tool_executed("chmod", {"path": path, "mode": mode, "recursive": recursive}, None, str(e))
                raise

        @server.tool(
            name="read",
            description="Read file content and return as text or base64. Requires 'read' permission.",
            annotations=ToolAnnotations(title="Read file", read_only_hint=True),
        )
        def read(path: str, encoding: str = "utf-8") -> str:
            """Read a file and return its content.

            Args:
                path: Path to the file to read.
                encoding: Text encoding (default 'utf-8'). Specify 'base64' for binary files.
            """
            try:
                target = self._resolve(path)
                self._authorize("read", target)
                if not target.is_file():
                    raise FileNotFoundError(str(target))

                file_size = target.stat().st_size
                truncated = file_size > 1024 * 1024  # >1MB

                if encoding == "base64":
                    # Read as binary and encode to base64
                    with open(target, "rb") as f:
                        content = f.read()
                    result_content = base64.b64encode(content).decode("ascii")
                    result_msg = f"Read {file_size} bytes from {target} (base64)"
                    if truncated:
                        result_msg += " [file >1MB]"
                else:
                    # Try to read as text
                    try:
                        with open(target, "r", encoding=encoding) as f:
                            result_content = f.read()
                        result_msg = f"Read {len(result_content)} chars from {target} ({encoding})"
                        if truncated:
                            result_msg += " [file >1MB]"
                    except UnicodeDecodeError as e:
                        # If text decoding fails, fall back to base64
                        with open(target, "rb") as f:
                            content = f.read()
                        result_content = base64.b64encode(content).decode("ascii")
                        result_msg = f"Read {file_size} bytes from {target} (base64, text decode failed)"
                        if truncated:
                            result_msg += " [file >1MB]"

                self._emit_tool_executed("read", {"path": path, "encoding": encoding}, result_msg, None)
                return result_content
            except Exception as e:
                self._emit_tool_executed("read", {"path": path, "encoding": encoding}, None, str(e))
                raise

        @server.tool(
            name="download",
            description=(
                "Copy a file or directory to a staging directory for LLM access. "
                "Requires 'download' permission."
            ),
            annotations=ToolAnnotations(title="Download file", read_only_hint=False),
        )
        def download(path: str) -> str:
            """Download a file or directory to a staging location.

            Args:
                path: Path to download.
            """
            try:
                src = self._resolve(path)
                self._authorize("download", src)
                if not src.exists() and not src.is_symlink():
                    raise FileNotFoundError(str(src))

                # Create staging directory with unique ID
                staging_base = Path(tempfile.gettempdir()) / "sape_download"
                staging_base.mkdir(parents=True, exist_ok=True)
                staging_dir = staging_base / str(uuid.uuid4())
                staging_dir.mkdir(parents=True, exist_ok=True)

                if src.is_dir() and not src.is_symlink():
                    # Copy directory tree recursively. Like copy, every entry
                    # below the tree leaves the permission model with it, so
                    # each one has to be authorised first.
                    self._authorize("download", *src.rglob("*"))
                    dst = staging_dir / src.name
                    shutil.copytree(src, dst)
                    result_msg = f"Downloaded directory {src} to {dst}"
                else:
                    # Copy file (or symlink target)
                    dst = staging_dir / src.name
                    shutil.copy2(src, dst)
                    result_msg = f"Downloaded file {src} to {dst}"

                self._emit_tool_executed("download", {"path": path}, result_msg, None)
                return str(dst)
            except Exception as e:
                self._emit_tool_executed("download", {"path": path}, None, str(e))
                raise

        @server.tool(
            name="upload",
            description=(
                "Write base64-encoded content to a file. "
                "Requires 'upload' permission."
            ),
            annotations=ToolAnnotations(title="Upload file", destructive_hint=False),
        )
        def upload(path: str, content: str, encoding: str = "base64", overwrite: bool = False) -> str:
            """Upload content to a file.

            Args:
                path: Destination path.
                content: File content (base64-encoded if encoding='base64', text if encoding='utf-8').
                encoding: Content encoding ('base64' or 'utf-8', default 'base64').
                overwrite: Allow replacing an existing file.
            """
            try:
                target = self._resolve(path)
                self._authorize("upload", target)

                if target.exists() and not overwrite:
                    raise FileExistsError(f"{target} already exists (pass overwrite=true)")

                # Create parent directories if needed
                target.parent.mkdir(parents=True, exist_ok=True)

                if encoding == "base64":
                    # Decode base64 and write as binary
                    try:
                        decoded = base64.b64decode(content)
                    except Exception as e:
                        raise ValueError(f"invalid base64 content: {e}") from e
                    with open(target, "wb") as f:
                        f.write(decoded)
                    result_msg = f"Uploaded {len(decoded)} bytes to {target}"
                else:
                    # Write as text (interpreted as UTF-8 or other encoding)
                    target.write_text(content, encoding=encoding)
                    result_msg = f"Uploaded {len(content)} chars to {target} ({encoding})"

                self._emit_tool_executed("upload", {"path": path, "encoding": encoding, "overwrite": overwrite}, result_msg, None)
                return result_msg
            except Exception as e:
                self._emit_tool_executed("upload", {"path": path, "encoding": encoding, "overwrite": overwrite}, None, str(e))
                raise

        @server.tool(
            name="show-permissions",
            description=(
                "Show all active permission rules. Returns the paths, allowed actions, "
                "subfolder settings, and audit information for each rule. Useful for understanding "
                "what operations are permitted on which paths."
            ),
            annotations=ToolAnnotations(title="Show all permissions", read_only_hint=True),
        )
        def show_permissions() -> list[dict]:
            """Show all active permission rules.

            Returns a list of all permission rules with their settings and allowed actions.
            Each rule includes the path, which actions are allowed, subfolder scope,
            and audit timestamps.
            """
            try:
                rules = self.permissions.rules()
                transformed_rules = []
                for rule in rules:
                    # Convert can_* columns to allowed_actions list
                    allowed_actions = []
                    for action in ACTIONS:
                        if rule.get(f"can_{action}"):
                            allowed_actions.append(action)

                    transformed = {
                        "path": rule["path"],
                        "allow_subfolders": bool(rule["allow_subfolders"]),
                        "allowed_actions": allowed_actions,
                        "created_at": rule["created_at"],
                        "user_created": rule["user_created"],
                        "updated_at": rule["updated_at"],
                        "user_updated": rule["user_updated"],
                    }
                    transformed_rules.append(transformed)

                self._emit_tool_executed("show-permissions", {}, f"Listed {len(transformed_rules)} permission rules", None)
                return transformed_rules
            except Exception as e:
                self._emit_tool_executed("show-permissions", {}, None, str(e))
                raise

    # -- entry point -----------------------------------------------------

    def run(self, transport: str = "stdio", **kwargs) -> None:
        """Run the server. Transport is 'stdio', 'sse' or 'streamable-http'."""
        self.server.run(transport=transport, **kwargs)
