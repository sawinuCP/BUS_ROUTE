"""Search normalization unit tests (Phase 2)."""

from __future__ import annotations

from app.modules.places.normalize import normalize_text


def test_case_and_punctuation_folding() -> None:
    assert normalize_text("Homagama   Junction!!") == "homagama junction"
    assert normalize_text("Kollu-pitiya, (Junction)") == "kollu pitiya junction"


def test_preserves_native_scripts() -> None:
    assert normalize_text("හෝමාගම") == "හෝමාගම"
    assert normalize_text("கொள்ளுப்பிட்டி") == "கொள்ளுப்பிட்டி"


def test_unicode_compatibility_forms() -> None:
    # Trade-off (documented): NFKC folding was removed because it decomposes
    # Sinhala/Tamil combining marks. Full-width Latin is preserved (not folded
    # to ASCII); casefold still applies to it.
    assert normalize_text("Ｈｏｍａｇａｍａ") == "ｈｏｍａｇａｍａ"


def test_empty_and_none() -> None:
    assert normalize_text("") == ""
    assert normalize_text(None) == ""
