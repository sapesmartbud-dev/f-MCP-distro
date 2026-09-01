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

"""SQLite-backed permission store for the File MCP server.

The ``permissions`` table holds one row per authorised path. A row grants a
set of operations on that exact path and, when ``allow_subfolders`` is set,
on everything beneath it. Anything not covered by a row is denied: the store
is default-deny, so an empty database means the server can do nothing.

Two points on how rows combine:

* Rows only ever *grant*. ``allow_subfolders=0`` limits the reach of that
  row; it does not deny anything, so a broader ancestor row with
  ``allow_subfolders=1`` still applies further down.
* The most specific applicable row wins. To carve an exception out of a
  broad grant, add a deeper row with the operations you want (or none at
  all, to deny everything there).
"""

from __future__ import annotations

import getpass
import os
import sqlite3
from datetime import datetime
from pathlib import Path

# Operation names exposed as tools. Stored as the boolean columns
# can_create, can_delete, ... ("create" is a reserved SQL keyword, so the
# columns carry a can_ prefix).
ACTIONS: tuple[str, ...] = ("create", "delete", "move", "copy", "list", "edit", "chmod", "read", "download", "upload")

_COLUMNS = ", ".join(f"can_{a} INTEGER NOT NULL DEFAULT 0" for a in ACTIONS)

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS permissions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    path              TEXT    NOT NULL UNIQUE,
    allow_subfolders  INTEGER NOT NULL DEFAULT 0,
    {_COLUMNS},
    created_at        TEXT    NOT NULL,
    user_created      TEXT    NOT NULL,
    updated_at        TEXT    NOT NULL,
    user_updated      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_permissions_path ON permissions(path);
"""


def current_user() -> str:
    """Best-effort login name of the user running the server."""
    try:
        return getpass.getuser()
    except Exception:  # no password entry / no LOGNAME in some containers
        return os.environ.get("USER") or f"uid:{os.getuid()}"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class PermissionDenied(PermissionError):
    """Raised when no rule authorises an operation on a path."""


class PermissionStore:
    """Reads and enforces the ``permissions`` table."""

    def __init__(self, db_path: str | os.PathLike[str] | None = None, user: str | None = None):
        self.db_path = Path(
            db_path or os.environ.get("FILE_MCP_DB", Path(__file__).resolve().parent.parent / "permissions.db")
        ).expanduser()
        self.user = user or current_user()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._migrate_schema()

    def _migrate_schema(self) -> None:
        """Ensure all expected columns exist, adding missing ones via ALTER TABLE.

        This method enables schema evolution without breaking existing permissions.db
        files. When new actions are added to the ACTIONS tuple, this method
        automatically adds the corresponding can_* columns with defaults to all
        existing rows (default: 0 = not granted).

        Safe against concurrent access: SQLite's locking ensures migrations are
        serialized. Idempotent: repeatedly calling on an already-migrated DB is a
        no-op (no missing columns to add).

        If migration fails (e.g. read-only database), the database is still
        functional for read-only queries; writes will fail as expected.
        """
        # Get existing columns from the permissions table
        existing_cols = {row[1] for row in self.conn.execute("PRAGMA table_info(permissions)")}

        # Determine which can_* columns we should have based on ACTIONS
        expected_cols = {f"can_{a}" for a in ACTIONS}

        # Find missing columns
        missing_cols = expected_cols - existing_cols

        # Add each missing column (sorted for determinism and consistency across runs)
        for col in sorted(missing_cols):
            try:
                # ALTER TABLE ADD COLUMN sets NOT NULL column to DEFAULT for all existing rows
                self.conn.execute(
                    f"ALTER TABLE permissions ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0"
                )
                self.conn.commit()
            except sqlite3.OperationalError as e:
                # If database is read-only, provide a clear error message.
                # Database-locked errors are transient and SQLite will retry.
                if "read-only" in str(e).lower():
                    raise RuntimeError(
                        f"Cannot migrate permissions.db: database is read-only. "
                        "Check file permissions."
                    ) from e
                raise

    # -- writes ----------------------------------------------------------

    def grant(
        self,
        path: str | os.PathLike[str],
        actions: list[str] | tuple[str, ...] | str = "all",
        allow_subfolders: bool = True,
    ) -> None:
        """Insert or update the rule for ``path``.

        ``actions`` is "all" or a list of names from :data:`ACTIONS`. On an
        update, created_at/user_created are preserved and only the
        updated_at/user_updated pair moves.
        """
        granted = set(ACTIONS) if actions == "all" else set(actions)
        unknown = granted - set(ACTIONS)
        if unknown:
            raise ValueError(f"unknown action(s): {sorted(unknown)}")

        resolved = str(Path(path).expanduser().resolve())
        now = _now()
        columns = ", ".join(f"can_{a}" for a in ACTIONS)
        placeholders = ", ".join("?" for _ in ACTIONS)
        updates = ", ".join(f"can_{a}=excluded.can_{a}" for a in ACTIONS)
        self.conn.execute(
            f"""
            INSERT INTO permissions
                (path, allow_subfolders, {columns}, created_at, user_created, updated_at, user_updated)
            VALUES (?, ?, {placeholders}, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                allow_subfolders=excluded.allow_subfolders,
                {updates},
                updated_at=excluded.updated_at,
                user_updated=excluded.user_updated
            """,
            (
                resolved,
                int(allow_subfolders),
                *(int(a in granted) for a in ACTIONS),
                now,
                self.user,
                now,
                self.user,
            ),
        )
        self.conn.commit()

    def revoke(self, path: str | os.PathLike[str]) -> bool:
        """Delete the rule for ``path``. Returns True if a row was removed."""
        resolved = str(Path(path).expanduser().resolve())
        cur = self.conn.execute("DELETE FROM permissions WHERE path = ?", (resolved,))
        self.conn.commit()
        return cur.rowcount > 0

    # There is deliberately no seeding of default rules. A new database starts
    # empty, and an empty database authorises nothing: every path the user
    # wants reachable has to be granted explicitly.

    # -- reads -----------------------------------------------------------

    def rules(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM permissions ORDER BY path").fetchall()
        return [dict(r) for r in rows]

    def rule_for(self, path: str | os.PathLike[str]) -> dict | None:
        """Return the most specific rule covering ``path``, or None.

        An exact path match always wins; otherwise the deepest ancestor whose
        rule sets ``allow_subfolders`` applies.

        ``path`` must already be absolute and free of ``..``: a component the
        filesystem would collapse but :class:`~pathlib.Path` keeps would make
        this comparison match a rule that does not cover the real target.
        Callers resolve first (see ``FileMCPServer._resolve``); anything else
        is refused rather than guessed at.
        """
        target = Path(path)
        if not target.is_absolute() or ".." in target.parts:
            raise ValueError(
                f"permission checks require a normalised absolute path, got {str(path)!r}"
            )
        best: dict | None = None
        best_depth = -1
        for row in self.conn.execute("SELECT * FROM permissions"):
            rule_path = Path(row["path"])
            if target == rule_path:
                applies = True
            elif row["allow_subfolders"] and rule_path in target.parents:
                applies = True
            else:
                applies = False
            if applies:
                depth = len(rule_path.parts)
                if depth > best_depth:
                    best, best_depth = dict(row), depth
        return best

    def is_allowed(self, path: str | os.PathLike[str], action: str) -> bool:
        if action not in ACTIONS:
            raise ValueError(f"unknown action: {action}")
        rule = self.rule_for(path)
        return bool(rule and rule[f"can_{action}"])

    def require(self, path: str | os.PathLike[str], action: str) -> None:
        """Raise :class:`PermissionDenied` unless ``action`` is allowed on ``path``."""
        if action not in ACTIONS:
            raise ValueError(f"unknown action: {action}")
        rule = self.rule_for(path)
        if rule is None:
            raise PermissionDenied(f"no permission rule covers {path}")
        if not rule[f"can_{action}"]:
            raise PermissionDenied(f"'{action}' is not permitted on {path} (rule: {rule['path']})")

    def close(self) -> None:
        self.conn.close()
