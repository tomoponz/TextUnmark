from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from .unicode_scan import inspect_text


SPACE_REPLACEMENTS = {
    "\u00A0": " ",  # NO-BREAK SPACE
    "\u2007": " ",  # FIGURE SPACE
    "\u202F": " ",  # NARROW NO-BREAK SPACE
}

CONSERVATIVE_REMOVALS = {
    "\u00AD",  # SOFT HYPHEN
    "\u200B",  # ZERO WIDTH SPACE
    "\u2060",  # WORD JOINER
    "\uFEFF",  # BOM / ZERO WIDTH NO-BREAK SPACE
}

STRICT_EXTRA_REMOVALS = {
    "\u061C",  # ARABIC LETTER MARK
    "\u200C",  # ZERO WIDTH NON-JOINER
    "\u200D",  # ZERO WIDTH JOINER
    "\u200E",  # LEFT-TO-RIGHT MARK
    "\u200F",  # RIGHT-TO-LEFT MARK
    *[chr(cp) for cp in range(0x202A, 0x202F)],
    *[chr(cp) for cp in range(0x2066, 0x206A)],
    *[chr(cp) for cp in range(0xFE00, 0xFE10)],
}


@dataclass(frozen=True)
class SanitizeResult:
    text: str
    changed: bool
    change_count: int
    normalization: str
    profile: str
    before: dict[str, object]
    after: dict[str, object]

    def to_dict(self, include_text: bool = False) -> dict[str, object]:
        result: dict[str, object] = {
            "changed": self.changed,
            "change_count": self.change_count,
            "normalization": self.normalization,
            "profile": self.profile,
            "before": self.before,
            "after": self.after,
        }
        if include_text:
            result["text"] = self.text
        return result


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def sanitize_text(
    text: str,
    *,
    profile: str = "conservative",
    normalization: str = "NFC",
    normalize_newlines: bool = True,
) -> SanitizeResult:
    """Normalize non-semantic Unicode markers without claiming watermark removal.

    conservative:
        Replaces unusual spaces and removes a small set of broadly safe invisible
        formatting characters. It preserves bidi controls, join controls, and
        variation selectors because those can carry real linguistic/emoji meaning.

    strict:
        Also removes several context-sensitive formatting characters. This can
        visibly or semantically alter mixed-direction text, emoji, and some scripts.
    """
    if profile not in {"conservative", "strict"}:
        raise ValueError("profile must be 'conservative' or 'strict'")
    if normalization not in {"none", "NFC", "NFKC"}:
        raise ValueError("normalization must be one of: none, NFC, NFKC")

    before = inspect_text(text)
    working = _normalize_newlines(text) if normalize_newlines else text

    if normalization != "none":
        working = unicodedata.normalize(normalization, working)

    removals = set(CONSERVATIVE_REMOVALS)
    if profile == "strict":
        removals.update(STRICT_EXTRA_REMOVALS)

    output: list[str] = []
    for ch in working:
        if ch in SPACE_REPLACEMENTS:
            output.append(SPACE_REPLACEMENTS[ch])
        elif ch in removals:
            continue
        else:
            output.append(ch)

    cleaned = "".join(output)
    after = inspect_text(cleaned)

    # The count is deliberately simple and deterministic: number of positions in
    # the original/cleaned pair that no longer match, plus any length difference.
    common = min(len(text), len(cleaned))
    positional_changes = sum(text[i] != cleaned[i] for i in range(common))
    change_count = positional_changes + abs(len(text) - len(cleaned))

    return SanitizeResult(
        text=cleaned,
        changed=cleaned != text,
        change_count=change_count,
        normalization=normalization,
        profile=profile,
        before=before,
        after=after,
    )
