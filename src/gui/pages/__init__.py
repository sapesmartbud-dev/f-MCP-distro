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

"""GUI pages package."""

from .session_log_page import SessionLogPage
from .permissions_page import PermissionsPage
from .settings_page import SettingsPage
from .legal_page import LegalPage
from .help_page import HelpPage
from .about_page import AboutPage

__all__ = [
    "SessionLogPage",
    "PermissionsPage",
    "SettingsPage",
    "LegalPage",
    "HelpPage",
    "AboutPage",
]
