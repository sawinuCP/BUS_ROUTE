"""Text normalization for multilingual place search (Phase 2).

Normalizes queries so spelling variants, punctuation and spacing differences do
not hide results, while **preserving Sinhala/Tamil exactly**: Python's ``\\w``
does not match Indic combining marks (e.g. U+0DDD, U+0DCF are ``isalnum()``
False), so character classes must not decide what is punctuation — Unicode
general categories do. Letters, numbers, marks (M*) and whitespace are kept;
punctuation (P*) and symbols (S*) become spaces. Normalization never
transliterates or translates.
"""

from __future__ import annotations

import re
import unicodedata

_SPACES = re.compile(r"\s+")


def _keep(ch: str) -> bool:
    category = unicodedata.category(ch)
    if category.startswith("M"):  # combining marks: essential to native scripts
        return True
    return not (category.startswith("P") or category.startswith("S"))


def normalize_text(value: str | None) -> str:
    """Fold Latin punctuation away, preserve native scripts, collapse spaces."""
    if not value:
        return ""
    folded = value.casefold()
    cleaned = "".join(ch if _keep(ch) else " " for ch in folded)
    return _SPACES.sub(" ", cleaned).strip()
