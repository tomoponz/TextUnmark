from __future__ import annotations

from pathlib import Path
from typing import Any

from .batch import iter_text_files
from .unicode_scan import inspect_text


def _line_col(text: str, index: int) -> tuple[int, int]:
    prefix = text[:index]
    line = prefix.count("\n") + 1
    last_newline = prefix.rfind("\n")
    column = index + 1 if last_newline < 0 else index - last_newline
    return line, column


def scan_to_sarif(root: Path) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    base = root.parent if root.is_file() else root

    for path in iter_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        report = inspect_text(text)
        for finding in report["findings"]:
            line, column = _line_col(text, int(finding["index"]))
            relative = str(path.relative_to(base)).replace("\\", "/")
            level = "warning" if finding["context_sensitive"] else "note"
            results.append(
                {
                    "ruleId": f"unicode/{finding['reason']}",
                    "level": level,
                    "message": {
                        "text": f"{finding['codepoint']} {finding['name']} ({finding['reason']})"
                    },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": relative},
                                "region": {
                                    "startLine": line,
                                    "startColumn": column,
                                    "endColumn": column + 1,
                                },
                            }
                        }
                    ],
                    "properties": {
                        "codepoint": finding["codepoint"],
                        "contextSensitive": finding["context_sensitive"],
                    },
                }
            )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "TextUnmark",
                        "informationUri": "https://github.com/tomoponz/TextUnmark",
                        "rules": [],
                    }
                },
                "results": results,
            }
        ],
    }
