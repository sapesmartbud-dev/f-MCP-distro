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

"""Legal document loader.

Loads the program's legal documents, with automatic fallback to English when a
locale-specific version is unavailable.

The documents are maintained in **English only**: SAPÉ f-MCP is licensed under
GPL-3.0-only, the GNU GPL is legally authoritative in English, and the Free
Software Foundation does not publish binding translations. A translated license
would carry no legal force. The interface itself stays localized -- the document
*labels* come from the i18n catalogue, only the document *bodies* are English.

The directory structure keeps its per-locale shape so a locale can be added
later without a code change; today only ``en-US`` is populated and every other
language resolves to it through the fallback in :meth:`get_document`.

    legal-documents/
        en-US/
            LICENSE.md          (verbatim GNU GPL v3)
            DISCLAIMER.md
            DATA-PROTECTION.md
            LEGAL-README.md
"""

from __future__ import annotations

from pathlib import Path


class LegalDocumentLoader:
    """Load and manage the program's legal documents."""

    # The legal documents shipped with the program. PROPRIETARY.md,
    # TERMS-OF-USE.md, INTELLECTUAL-PROPERTY.md and LEGAL-COMPLIANCE.md were
    # removed when the project moved to GPL-3.0-only: each asserted terms
    # ("may not modify", "may not redistribute") that GPL-3.0 section 7 makes
    # void as further restrictions, so keeping them would have been misleading
    # rather than merely stale.
    DOCUMENT_TYPES = [
        'LICENSE.md',
        'DISCLAIMER.md',
        'DATA-PROTECTION.md',
        'LEGAL-README.md',
    ]

    def __init__(self, legal_docs_dir: str | Path | None = None):
        """Initialize loader with path to legal-documents folder.

        Args:
            legal_docs_dir: Path to the legal-documents directory. If None,
                defaults to project root / legal-documents.

        Example:
            >>> loader = LegalDocumentLoader()
            >>> loader = LegalDocumentLoader('/custom/path/to/legal-documents')
        """
        if legal_docs_dir is None:
            # Default: project root / legal-documents
            legal_docs_dir = Path(__file__).parent.parent / 'legal-documents'
        self.legal_docs_dir = Path(legal_docs_dir)

    def get_document(self, lang_code: str, doc_type: str) -> str:
        """Load document content for language, fallback to English if not found.

        Args:
            lang_code: Language code (e.g., 'es-ES', 'en-US')
            doc_type: Document file name (e.g., 'LICENSE.md', 'DISCLAIMER.md')

        Returns:
            Document content as string. Returns fallback English version if the
            requested language is not available. Returns a "not found" message
            if neither the requested language nor English fallback exists.

        Example:
            >>> loader = LegalDocumentLoader()
            >>> content = loader.get_document('es-ES', 'LICENSE.md')
            >>> content.splitlines()[0].strip()
            'GNU GENERAL PUBLIC LICENSE'
        """
        # Try requested language
        doc_path = self.legal_docs_dir / lang_code / doc_type
        if doc_path.exists():
            return doc_path.read_text(encoding='utf-8')

        # Fallback to English
        fallback_path = self.legal_docs_dir / 'en-US' / doc_type
        if fallback_path.exists():
            return fallback_path.read_text(encoding='utf-8')

        # Not found in either language
        return f"Document not found: {doc_type} (requested: {lang_code}, fallback: en-US)"

    def get_all_documents(self, lang_code: str) -> dict[str, str]:
        """Load all documents for a language as a dictionary.

        Args:
            lang_code: Language code (e.g., 'es-ES', 'en-US')

        Returns:
            Dictionary with document keys (lowercase, without .md extension)
            mapping to their content. Keys are:
            'license', 'disclaimer', 'data-protection', 'legal-readme'

        Example:
            >>> loader = LegalDocumentLoader()
            >>> docs = loader.get_all_documents('es-ES')
            >>> 'license' in docs
            True
            >>> len(docs)
            4
        """
        docs = {}
        for doc_type in self.DOCUMENT_TYPES:
            # Convert LICENSE.md -> license (for dict keys)
            key = doc_type.replace('.md', '').lower()
            docs[key] = self.get_document(lang_code, doc_type)
        return docs

    def get_document_list(self) -> list[str]:
        """Return list of document type names (for UI navigation).

        Returns:
            List of document names without .md extension, in lowercase.
            Example: ['license', 'disclaimer', 'data-protection', 'legal-readme']

        Example:
            >>> loader = LegalDocumentLoader()
            >>> docs = loader.get_document_list()
            >>> 'license' in docs
            True
            >>> len(docs)
            4
        """
        return [d.replace('.md', '').lower() for d in self.DOCUMENT_TYPES]

    def get_supported_languages(self) -> list[str]:
        """Get list of language codes that have legal documents.

        Returns:
            List of language codes with existing legal-documents folders.
            Only 'en-US' is populated (see the module docstring); every other
            language reaches these documents through the English fallback.

        Example:
            >>> loader = LegalDocumentLoader()
            >>> langs = loader.get_supported_languages()
            >>> 'en-US' in langs
            True
        """
        if not self.legal_docs_dir.exists():
            return []

        langs = []
        for item in self.legal_docs_dir.iterdir():
            # Only include items that look like language codes (e.g., en-US, es-ES)
            if item.is_dir() and '-' in item.name and len(item.name) == 5:
                langs.append(item.name)

        return sorted(langs)

    def document_exists(self, lang_code: str, doc_type: str) -> bool:
        """Check if a document exists for the given language.

        Args:
            lang_code: Language code
            doc_type: Document file name (e.g., 'LICENSE.md')

        Returns:
            True if document exists in the requested language (not fallback),
            False otherwise.

        Example:
            >>> loader = LegalDocumentLoader()
            >>> loader.document_exists('en-US', 'LICENSE.md')
            True
        """
        doc_path = self.legal_docs_dir / lang_code / doc_type
        return doc_path.exists()

    def get_document_path(self, lang_code: str, doc_type: str) -> Path | None:
        """Get the file path for a document (for direct file access if needed).

        Args:
            lang_code: Language code
            doc_type: Document file name (e.g., 'LICENSE.md')

        Returns:
            Path object if document exists in the requested language,
            None otherwise (no fallback).

        Example:
            >>> loader = LegalDocumentLoader()
            >>> path = loader.get_document_path('en-US', 'LICENSE.md')
            >>> path.name
            'LICENSE.md'
        """
        doc_path = self.legal_docs_dir / lang_code / doc_type
        if doc_path.exists():
            return doc_path
        return None

    def get_base_dir(self) -> Path:
        """Get the root legal-documents directory.

        Returns:
            Path to the legal-documents directory.
        """
        return self.legal_docs_dir
