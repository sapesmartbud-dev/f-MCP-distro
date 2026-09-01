# SAPÉ f-MCP — Disclaimer & Risk Notice

**Version 2.0**
**Effective Date:** 2026-08-23
**Scope:** This notice applies to **SAPÉ f-MCP** (the program), not to SAPÉ (the brand) or any other SAPÉ products.

---

## The Authoritative Disclaimer Is in the License

SAPÉ f-MCP is free software licensed under the **GNU General Public License, version 3 only (GPL-3.0-only)**. The binding warranty disclaimer and liability limitation are **sections 15, 16 and 17 of that license**, which you can read in the [`LICENSE`](LICENSE) file at the root of the source distribution.

In summary, as GPL-3.0 §15 puts it:

> THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY APPLICABLE LAW. […] THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND PERFORMANCE OF THE PROGRAM IS WITH YOU.

And as §16 puts it:

> IN NO EVENT UNLESS REQUIRED BY APPLICABLE LAW […] WILL ANY COPYRIGHT HOLDER, OR ANY OTHER PARTY WHO MODIFIES AND/OR CONVEYS THE PROGRAM AS PERMITTED ABOVE, BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY GENERAL, SPECIAL, INCIDENTAL OR CONSEQUENTIAL DAMAGES ARISING OUT OF THE USE OR INABILITY TO USE THE PROGRAM.

**This document adds nothing to and takes nothing away from those terms.** Nothing here restricts the rights the GPL grants you — to run, study, modify, and redistribute this program. Where anything in this document could be read as conflicting with the license, the license governs.

---

## No Obligation to Support or Maintain

SAPÉ f-MCP is offered without any commitment to provide:

- technical support
- bug fixes or patches
- feature updates
- security updates
- long-term compatibility with future operating systems or LLM clients

Updates, when they happen, are at the author's discretion and carry no warranty or continuing obligation. Because this is free software, you are also entitled to fix, maintain, or fork it yourself — see the license for the terms.

---

## What This Program Actually Does — Read This Part

The sections below are not legal boilerplate. They describe real, specific ways SAPÉ f-MCP can lead to data loss or unauthorized access if you misconfigure it. Read them before granting permissions.

### 1. It grants an LLM controlled write access to your file system

SAPÉ f-MCP exposes file operations — create, delete, move, copy, list, edit, chmod, read, download, upload — as MCP tools. Every path is checked against the permission rules in the local SQLite database before any work happens, and paths no rule covers are refused. But **the rules are only as good as you write them.** A rule granted too broadly (a whole home directory, a whole drive) means the LLM client can delete or overwrite anything under it.

### 2. It is a permission system, not a sandbox

This is the single most important thing to understand. SAPÉ f-MCP enforces path-based access control inside its own tool calls. It does **not** provide:

- kernel-level enforcement or mandatory access control
- protection against privilege escalation
- a security boundary against a compromised or adversarial LLM client
- malware detection

The MCP server runs with your user privileges. If an LLM client is compromised or acts against your interests, SAPÉ f-MCP will keep refusing operations outside the rules you set — but everything **inside** those rules remains reachable. Grant narrowly.

### 3. Links are handled, but understand how

Operations that dereference (`create`, `edit`, `copy`, `list`, `chmod`, `read`, `download`, `upload`) require that the **resolved target** also be authorized, so a link planted inside an allowed directory cannot be used to reach a path no rule covers. The check compares resolved paths rather than asking whether something is a link, which is what makes it cover Windows directory junctions as well as symlinks — `is_symlink()` reports `False` for a junction.

`copy` and `download` authorize every entry of a directory tree before copying it, because the copy follows links out of the tree; `delete` and `chmod` do the same for their recursive forms. **`move` of a directory is the exception**: it is authorized on the source and destination only, not on each entry inside. `delete` and `move` act on a link itself rather than its target, and are checked against the link's own path. It is worth knowing which category an operation falls into before you rely on it.

### 4. The session log is not an archive

**The graphical interface deletes the entire session-log database every time it starts**, including records of denied operations from earlier sessions. Nothing is evicted *during* a session, so the log grows unbounded while the application is open and is then discarded at the next launch. There is no configurable capacity.

If you need an audit trail for forensics or compliance, export before closing the application, or use `tool_log.jsonl` — written next to `permissions.db` — which is append-only and is not wiped. Neither is a substitute for a real audit system.

### 5. Third-party LLM clients are outside this program's control

SAPÉ f-MCP may be used with Claude, ChatGPT, or any other MCP client. The security, privacy, and data-handling practices of those systems are theirs, not this program's. What you expose to an LLM client through SAPÉ f-MCP may be transmitted to that client's provider. See [`DATA-PROTECTION.md`](DATA-PROTECTION.md) for what this program itself stores and where.

### 6. `chmod` behaves differently across platforms

POSIX permission semantics apply on Linux and macOS. On Windows, `chmod` support is partial and does not map cleanly onto ACLs. Do not rely on it as a security control on Windows.

### 7. Rule matching is case-sensitive on macOS and Linux

Paths are compared case-sensitively on POSIX systems. On a **case-insensitive filesystem — which is the macOS default** — `~/Secret` and `~/secret` are the same directory but not the same rule. A narrow rule carved out of a broader grant to restrict a subdirectory can therefore be sidestepped by changing the case of a path component. Windows is unaffected, because its path comparison is already case-insensitive.

Until this is addressed, on macOS prefer granting narrowly to granting broadly and carving out exceptions.

### 8. The HTTP transports are unauthenticated

When the graphical interface starts the server it listens on `127.0.0.1:8089`. Requests carrying a browser origin are rejected, but **any other local process can connect and use every tool your rules allow**, with no credential. The `stdio` transport has no such exposure, because only the client that spawned the process can talk to it. Prefer `stdio` unless you specifically need HTTP.

---

## What You Are Responsible For

- **Permission configuration** — understanding the scope of each rule you create, and granting the narrowest scope that works
- **Backups** — of anything you grant write or delete access to
- **Log retention** — exporting session logs before closing the application, if you need an audit trail
- **System security** — OS patches, antivirus, account hygiene
- **Your LLM client** — vetting what you connect this server to

---

## Governing Law

To the extent any part of this document is enforceable separately from the license, it is governed by Spanish law, jurisdiction of Arenys de Mar, Spain. This does not affect the GPL's own terms, which apply as written.

If any provision of this document is found invalid or unenforceable, it is severed and the rest remains in effect.

---

## Contact

**SAPÉ smart bud**
Email: info@sapebud.com
Location: Arenys de Mar, Spain

