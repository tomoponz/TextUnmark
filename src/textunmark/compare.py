from __future__ import annotations

from difflib import SequenceMatcher
import hashlib

from .unicode_scan import inspect_text


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare_texts(before: str, after: str) -> dict[str, object]:
    matcher = SequenceMatcher(a=before, b=after, autojunk=False)
    opcodes = matcher.get_opcodes()

    inserted = 0
    deleted = 0
    replaced_before = 0
    replaced_after = 0

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "insert":
            inserted += j2 - j1
        elif tag == "delete":
            deleted += i2 - i1
        elif tag == "replace":
            replaced_before += i2 - i1
            replaced_after += j2 - j1

    return {
        "identical": before == after,
        "similarity_ratio": matcher.ratio(),
        "before_length": len(before),
        "after_length": len(after),
        "inserted_characters": inserted,
        "deleted_characters": deleted,
        "replaced_before_characters": replaced_before,
        "replaced_after_characters": replaced_after,
        "before_sha256": _sha256(before),
        "after_sha256": _sha256(after),
        "before_inspection": inspect_text(before),
        "after_inspection": inspect_text(after),
        "operations": [
            {
                "tag": tag,
                "before": [i1, i2],
                "after": [j1, j2],
            }
            for tag, i1, i2, j1, j2 in opcodes
            if tag != "equal"
        ],
    }
