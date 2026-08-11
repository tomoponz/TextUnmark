from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import Counter
import unicodedata


# Characters that are commonly used as invisible or non-standard text markers.
# Context-sensitive characters are reported but preserved by conservative cleanup.
KNOWN_CHARACTERS: dict[int, tuple[str, str, bool]] = {
    0x00A0: ("NO-BREAK SPACE", "non-standard-space", False),
    0x00AD: ("SOFT HYPHEN", "invisible-format", False),
    0x061C: ("ARABIC LETTER MARK", "bidi-control", True),
    0x2007: ("FIGURE SPACE", "non-standard-space", False),
    0x200B: ("ZERO WIDTH SPACE", "zero-width", False),
    0x200C: ("ZERO WIDTH NON-JOINER", "join-control", True),
    0x200D: ("ZERO WIDTH JOINER", "join-control", True),
    0x200E: ("LEFT-TO-RIGHT MARK", "bidi-control", True),
    0x200F: ("RIGHT-TO-LEFT MARK", "bidi-control", True),
    0x202F: ("NARROW NO-BREAK SPACE", "non-standard-space", False),
    0x2060: ("WORD JOINER", "invisible-format", False),
    0xFEFF: ("ZERO WIDTH NO-BREAK SPACE / BOM", "zero-width", False),
}

BIDI_RANGES = (
    range(0x202A, 0x202F),  # embeddings, overrides, PDF
    range(0x2066, 0x206A),  # isolates
)


@dataclass(frozen=True)
class Finding:
    index: int
    codepoint: str
    character: str
    name: str
    category: str
    reason: str
    context_sensitive: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _classify(ch: str) -> tuple[str, bool] | None:
    cp = ord(ch)
    if cp in KNOWN_CHARACTERS:
        _, reason, context_sensitive = KNOWN_CHARACTERS[cp]
        return reason, context_sensitive

    if any(cp in r for r in BIDI_RANGES):
        return "bidi-control", True

    if 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF:
        return "variation-selector", True

    if 0xE0000 <= cp <= 0xE007F:
        return "unicode-tag", True

    category = unicodedata.category(ch)
    if category == "Cf":
        return "format-control", True

    if category == "Cc" and ch not in "\n\r\t":
        return "control-character", True

    return None


def inspect_text(text: str) -> dict[str, object]:
    findings: list[Finding] = []

    for index, ch in enumerate(text):
        classification = _classify(ch)
        if classification is None:
            continue

        reason, context_sensitive = classification
        cp = ord(ch)
        fallback_name = KNOWN_CHARACTERS.get(cp, ("UNKNOWN", "", False))[0]
        name = unicodedata.name(ch, fallback_name)
        findings.append(
            Finding(
                index=index,
                codepoint=f"U+{cp:04X}",
                character=ch,
                name=name,
                category=unicodedata.category(ch),
                reason=reason,
                context_sensitive=context_sensitive,
            )
        )

    by_reason = Counter(item.reason for item in findings)
    by_codepoint = Counter(item.codepoint for item in findings)

    return {
        "length": len(text),
        "finding_count": len(findings),
        "context_sensitive_count": sum(item.context_sensitive for item in findings),
        "by_reason": dict(sorted(by_reason.items())),
        "by_codepoint": dict(sorted(by_codepoint.items())),
        "findings": [item.to_dict() for item in findings],
    }
