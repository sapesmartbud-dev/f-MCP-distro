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

"""SQLite-backed logging store for tool executions.

The ``logs`` table holds one row per tool execution, with timestamp,
tool name, parameters, result, error, and session ID. Designed for
cross-process access (GUI + CLI) via WAL mode.

Clear logs per session via ``clear_session(session_id)`` (deletes only
that session's rows, leaving others for trimming). Auto-trim when
row count exceeds 10,000 to prevent unbounded growth.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Shared sanitizer for parameters (copied from ToolLogger to avoid circular imports)
def _sanitize_params(params: Dict[str, Any], max_chars: int = 500) -> Dict[str, Any]:
    """
    Sanitize params dict for logging.

    If the serialized JSON is too large, keeps only important fields
    (path, target, action, mode, recursive) to prevent huge log entries.
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


def _now() -> str:
    """Return current time as ISO 8601 string with local timezone."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


SCHEMA = """
CREATE TABLE IF NOT EXISTS logs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL,
    timestamp     TEXT NOT NULL,
    tool_name     TEXT NOT NULL,
    params_json   TEXT,
    result        TEXT,
    error         TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_session_id ON logs(session_id);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
"""


class LogStore:
    """SQLite-backed logging store for cross-process tool execution logs.

    Logs are stored in ~/.sape/log.db with WAL mode enabled for concurrent
    access by GUI and CLI. Each session's logs can be cleared independently,
    and the store auto-trims when row count exceeds 10,000.

    Args:
        db_path: Path to log database. Defaults to ~/.sape/log.db.

    Example:
        store = LogStore()
        store.log_tool("session_1", "create", {"path": "/tmp/file.txt"},
                       result="Created", error=None)
        logs = store.get_logs("session_1")
    """

    def __init__(self, db_path: str | os.PathLike[str] | None = None):
        """
        Initialize log store and create database if missing.

        Args:
            db_path: Path to log database. If None, uses ~/.sape/log.db.

        Raises:
            OSError: If unable to create database directory or file.
            RuntimeError: If WAL mode cannot be enabled on this filesystem.
        """
        if db_path is None:
            db_path = Path.home() / ".sape" / "log.db"
        else:
            db_path = Path(db_path).expanduser()

        self.db_path = db_path.resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Thread lock for write operations within this process
        # (WAL + check_same_thread=False handles cross-process, but we still
        # need to serialize writes within this process)
        self._write_lock = threading.Lock()

        # Open connection with WAL mode enabled
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Enable WAL mode for cross-process access
        # Must be done before CREATE TABLE
        try:
            journal_mode = self.conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if journal_mode.upper() != "WAL":
                raise RuntimeError(
                    f"Failed to enable WAL mode for {self.db_path}. "
                    f"Filesystem may not support shared-memory locking. "
                    f"Got mode: {journal_mode}"
                )
        except sqlite3.Error as e:
            raise RuntimeError(f"Cannot set WAL mode on {self.db_path}: {e}")

        # Create table if missing
        try:
            self.conn.executescript(SCHEMA)
            self.conn.commit()
        except sqlite3.Error as e:
            raise OSError(f"Cannot create log schema in {self.db_path}: {e}")

    def log_tool(
        self,
        session_id: str,
        tool_name: str,
        params: Dict[str, Any],
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Log a tool execution.

        Records the tool invocation with timestamp, sanitized params, and result/error.
        Errors during logging are swallowed to prevent crashes (logged to stderr instead).

        Args:
            session_id: Unique identifier for this session (e.g., UUID).
            tool_name: Name of the tool invoked (e.g., "create", "delete", "list").
            params: Input parameters (will be sanitized and JSON-encoded).
            result: Output from the tool (string, max 1000 chars), or None if error.
            error: Error message if tool failed, or None if successful.

        Notes:
            - Exactly one of result or error should typically be set.
            - Params are sanitized to prevent huge log entries.
            - SQLite locking errors are transient; this method doesn't retry.
            - OSError/OperationalError during insert are caught and logged to stderr.
        """
        # Truncate result/error to 1000 chars
        if result and len(result) > 1000:
            result = result[:1000] + "... (truncated)"
        if error and len(error) > 1000:
            error = error[:1000] + "... (truncated)"

        # Sanitize and JSON-encode params
        sanitized_params = _sanitize_params(params)
        try:
            params_json = json.dumps(sanitized_params, default=str)
        except (TypeError, ValueError):
            params_json = json.dumps({"_error": "unable to serialize params"})

        # Insert with thread safety
        with self._write_lock:
            try:
                self.conn.execute(
                    """
                    INSERT INTO logs
                        (session_id, timestamp, tool_name, params_json, result, error, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        datetime.now().astimezone().isoformat(),
                        tool_name,
                        params_json,
                        result,
                        error,
                        _now(),
                    ),
                )
                self.conn.commit()
            except (sqlite3.OperationalError, OSError) as e:
                # Don't crash the app if logging fails; log to stderr instead
                print(
                    f"[LogStore Warning] Failed to insert log entry to {self.db_path}: {e}",
                    flush=True
                )

    def delete_all(self) -> None:
        """
        Delete all logs from the database.

        Clears the entire logs table without preservation. Called at app
        startup to wipe logs from previous sessions.

        Notes:
            - Safe for cross-process access via WAL.
            - Does not VACUUM; avoids exclusive lock that defeats cross-process access.
        """
        with self._write_lock:
            try:
                self.conn.execute("DELETE FROM logs")
                self.conn.commit()
            except (sqlite3.OperationalError, OSError) as e:
                print(
                    f"[LogStore Warning] Failed to delete all logs: {e}",
                    flush=True
                )

    def clear_session(self, session_id: str) -> None:
        """
        Delete all logs for a given session.

        Removes only rows with the specified session_id, leaving logs from
        other sessions intact (these will be trimmed by trim_if_needed).

        Args:
            session_id: Session ID to clear.

        Notes:
            - Does not call trim_if_needed(); that's done separately at app startup.
            - Safe for cross-process access via WAL.
        """
        with self._write_lock:
            try:
                self.conn.execute("DELETE FROM logs WHERE session_id = ?", (session_id,))
                self.conn.commit()
            except (sqlite3.OperationalError, OSError) as e:
                print(
                    f"[LogStore Warning] Failed to clear session {session_id}: {e}",
                    flush=True
                )

    def trim_if_needed(self) -> None:
        """
        Delete oldest 1000 rows if row count exceeds 10,000.

        Called at app startup to prevent unbounded table growth. Uses
        deterministic ordering by id (not timestamp) to ensure consistent
        behavior across processes with out-of-order timestamps.

        Notes:
            - Does not VACUUM; avoids exclusive lock that defeats cross-process access.
            - Idempotent: if count < 10k, does nothing.
        """
        with self._write_lock:
            try:
                count = self.conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]
                if count > 10000:
                    # Delete first 1000 by id (deterministic, not timestamp)
                    self.conn.execute(
                        """
                        DELETE FROM logs WHERE id IN (
                            SELECT id FROM logs ORDER BY id LIMIT 1000
                        )
                        """
                    )
                    self.conn.commit()
            except (sqlite3.OperationalError, OSError) as e:
                print(
                    f"[LogStore Warning] Failed to trim logs in {self.db_path}: {e}",
                    flush=True
                )

    def get_logs(self, session_id: str) -> list[dict]:
        """
        Fetch all logs for a session, ordered by timestamp.

        Args:
            session_id: Session ID to retrieve logs for.

        Returns:
            List of log dicts, one per row, ordered by timestamp ascending.

        Notes:
            - Returns empty list on database errors (degraded gracefully).
            - Dicts have keys: id, session_id, timestamp, tool_name, params_json,
              result, error, created_at.
            - Commits any pending transaction before SELECT to ensure fresh read.
              This prevents stale snapshot issues in long-lived connections.
        """
        try:
            # Commit any pending transaction to clear stale read snapshot.
            # In Python's sqlite3 with default isolation_level="", a SELECT
            # can leave the connection in an implicit read transaction that pinned
            # an old snapshot. Without committing, later writes are not visible.
            self.conn.commit()

            rows = self.conn.execute(
                "SELECT * FROM logs WHERE session_id = ? ORDER BY timestamp ASC",
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]
        except (sqlite3.OperationalError, OSError) as e:
            print(
                f"[LogStore Warning] Failed to retrieve logs for session {session_id}: {e}",
                flush=True
            )
            return []

    def close(self) -> None:
        """Close the database connection."""
        try:
            self.conn.close()
        except sqlite3.Error:
            pass
