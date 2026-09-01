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

"""
ToolLogger: Thread-safe JSONL logging for file tool executions.

Logs each tool execution to a JSONL file (one JSON object per line).
Optionally also logs to SQLite via LogStore for cross-process access.
Ensures atomic writes to prevent corruption from concurrent access by multiple processes.
"""

import json
import os
import datetime
from pathlib import Path
from typing import Optional, Any, Dict
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.log_store import LogStore


class ToolLogger:
    """
    Thread-safe JSONL logger for file tool executions.

    Logs each tool execution to a JSONL file (one JSON object per line).
    Ensures atomic writes to prevent corruption from concurrent processes.

    Location: {db_dir}/tool_log.jsonl (same directory as permissions.db)
    Format: One JSON object per line, with fields:
        - timestamp: ISO 8601 local timezone timestamp (e.g., "2026-08-01T14:23:45.123456+02:00")
        - tool_name: Name of the tool (e.g., "create", "delete", "list")
        - params: Sanitized input parameters (dict, max 500 chars when serialized)
        - result: Output from the tool (str or null)
        - error: Error message if tool failed (str or null)
    """

    def __init__(
        self,
        db_path: str,
        log_store: Optional["LogStore"] = None,
        session_id: Optional[str] = None
    ):
        """
        Initialize logger with JSONL file and optional SQLite LogStore.

        Args:
            db_path: Path to permissions.db file. Log file will be created
                    as tool_log.jsonl in the same directory.
            log_store: Optional LogStore instance for SQLite logging.
            session_id: Session ID for SQLite logging. Required if log_store is provided.

        Raises:
            OSError: If unable to create log file or parent directory.
            ValueError: If log_store is provided but session_id is not.

        Example:
            logger = ToolLogger(db_path="/path/to/permissions.db")
            # Creates /path/to/tool_log.jsonl

            from src.log_store import LogStore
            store = LogStore()
            logger = ToolLogger(db_path="/path/to/permissions.db",
                              log_store=store, session_id="uuid-123")
            # Creates /path/to/tool_log.jsonl AND logs to SQLite
        """
        if log_store is not None and session_id is None:
            raise ValueError("session_id is required if log_store is provided")

        db_path = Path(db_path).resolve()
        self.log_path = db_path.parent / "tool_log.jsonl"
        self.lock = threading.Lock()  # Protects writes within same process
        self.log_store = log_store
        self.session_id = session_id

        # Ensure log file exists
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            self.log_path.touch(exist_ok=True)
        except OSError as e:
            raise OSError(f"Cannot create log file at {self.log_path}: {e}")

    def _sanitize_params(self, params: Dict[str, Any], max_chars: int = 500) -> Dict[str, Any]:
        """
        Sanitize params dict for logging.

        If the serialized JSON is too large, keeps only important fields
        (path, target, action, mode, recursive) to prevent huge log lines.

        Args:
            params: Dictionary of parameters passed to the tool.
            max_chars: Maximum length of JSON-serialized params (default 500).

        Returns:
            Sanitized params dict, suitable for JSON serialization.

        Notes:
            - Non-serializable objects are converted to strings via default=str
            - If still too large after keeping important fields, a truncation marker is added
            - The result is always JSON-serializable
        """
        try:
            test_json = json.dumps(params, default=str)
        except (TypeError, ValueError):
            return {"_error": "unable to serialize params"}

        # If within limits, return as-is
        if len(test_json) <= max_chars:
            return params

        # Keep only important fields
        important_keys = {"path", "target", "action", "mode", "recursive", "content_length"}
        result = {k: v for k, v in params.items() if k in important_keys}

        # Add back non-important keys that are small
        for k, v in params.items():
            if k not in important_keys:
                try:
                    v_json = json.dumps(v, default=str)
                    if len(v_json) < 50:  # Only keep small non-important fields
                        result[k] = v
                except:
                    pass

        # If still too large, drastically reduce
        if len(json.dumps(result, default=str)) > max_chars:
            result = {
                "path": params.get("path", "?"),
                "action": params.get("action", "?"),
                "_truncated": True
            }

        return result

    def log_execution(
        self,
        tool_name: str,
        params: Dict[str, Any],
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Log a single tool execution to both JSONL file and SQLite (if configured).

        Creates a JSON object with timestamp, tool metadata, and execution result.
        Writes atomically to JSONL to prevent log corruption from concurrent processes.
        Also writes to SQLite LogStore if one was provided during initialization.

        Args:
            tool_name: Name of the tool invoked (e.g., "create", "delete", "list", "edit").
            params: Input parameters passed to the tool (will be sanitized).
            result: Output/result from the tool (string, max 1000 chars), or None if error.
            error: Error message if the tool failed, or None if successful.

        Raises:
            OSError: If unable to write to log file (will be caught and logged as warning).

        Example:
            logger.log_execution(
                "create",
                {"path": "/home/user/file.txt", "recursive": True},
                result="Created file at /home/user/file.txt",
                error=None
            )

            logger.log_execution(
                "delete",
                {"path": "/home/user/missing.txt"},
                result=None,
                error="File not found"
            )

        Notes:
            - Exactly one of result or error should typically be set (not both).
            - Params are automatically sanitized to prevent huge logs.
            - Thread-safe across multiple threads in the same process.
            - Cross-process safety relies on OS-level atomic append with O_APPEND flag.
            - If write fails, a warning is printed but execution continues
              (to avoid crashing the main application just for logging).
            - Logs to both JSONL and SQLite if log_store was provided.
        """
        # Generate ISO 8601 local timezone timestamp
        timestamp = datetime.datetime.now().astimezone().isoformat()

        # Limit result and error strings to 1000 chars each
        if result and len(result) > 1000:
            result = result[:1000] + "... (truncated)"
        if error and len(error) > 1000:
            error = error[:1000] + "... (truncated)"

        # Sanitize params once (used by both JSONL and SQLite)
        sanitized_params = self._sanitize_params(params)

        # Build log entry
        log_entry = {
            "timestamp": timestamp,
            "tool_name": tool_name,
            "params": sanitized_params,
            "result": result,
            "error": error
        }

        # Serialize to JSON
        try:
            json_line = json.dumps(log_entry)
        except (TypeError, ValueError) as e:
            # Fallback if log_entry itself has serialization issues
            log_entry["params"] = {"_error": "log entry serialization failed"}
            json_line = json.dumps(log_entry)

        # Append to JSONL file atomically
        with self.lock:
            self._append_atomically(json_line)

        # Also log to SQLite if configured
        if self.log_store is not None and self.session_id is not None:
            try:
                self.log_store.log_tool(
                    self.session_id,
                    tool_name,
                    sanitized_params,
                    result,
                    error
                )
            except Exception as e:
                # Don't crash tool execution if SQLite logging fails
                print(
                    f"[ToolLogger Warning] Failed to log to SQLite: {e}",
                    flush=True
                )

    def _append_atomically(self, line: str) -> None:
        """
        Append a JSON line to the log file atomically.

        Uses os.open() with O_APPEND flag to ensure:
        - Atomic append operation (guaranteed by OS on POSIX systems)
        - Works across multiple processes without coordination
        - No partial lines corrupting the JSON structure

        Args:
            line: JSON line to append (without trailing newline).

        Notes:
            - On POSIX systems (Linux, macOS), O_APPEND guarantees atomicity at kernel level
            - On Windows, os.open() with O_APPEND should also be atomic for single write operations
            - The newline is added here to ensure each JSON object is on its own line
            - If write fails, a warning is printed but execution continues
              (to avoid crashing the main application just for logging)
        """
        try:
            # Open file with atomic append semantics:
            # - O_WRONLY: write-only mode
            # - O_CREAT: create file if it doesn't exist
            # - O_APPEND: always seek to end before writing (atomic on most OSes)
            flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
            mode = 0o666  # rw-rw-rw- (respects umask)

            fd = os.open(str(self.log_path), flags, mode)
            try:
                # Write JSON line with trailing newline
                # Encoded as UTF-8 to handle any non-ASCII characters
                os.write(fd, (line + "\n").encode("utf-8"))
            finally:
                os.close(fd)

        except OSError as e:
            # Don't crash the main app if logging fails
            # Write warning to stderr so it can be seen but won't interfere
            print(f"[ToolLogger Warning] Failed to write to {self.log_path}: {e}", flush=True)

        except Exception as e:
            # Catch any other unexpected errors
            print(f"[ToolLogger Error] Unexpected error writing log: {e}", flush=True)
