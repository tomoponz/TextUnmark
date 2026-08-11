from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .compare import compare_texts
from .sanitize import sanitize_text
from .unicode_scan import inspect_text


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _write_text(path: str | None, text: str) -> None:
    if path is None or path == "-":
        sys.stdout.write(text)
        return
    Path(path).write_text(text, encoding="utf-8")


def _json_dump(data: object, stream=sys.stdout) -> None:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def _print_inspection(report: dict[str, object]) -> None:
    print(f"Length: {report['length']}")
    print(f"Findings: {report['finding_count']}")
    print(f"Context-sensitive: {report['context_sensitive_count']}")
    findings = report["findings"]
    if not findings:
        print("No suspicious Unicode markers found.")
        return
    print()
    for item in findings:
        flag = " [context-sensitive]" if item["context_sensitive"] else ""
        print(
            f"{item['index']:>6}  {item['codepoint']}  {item['name']}"
            f"  ({item['reason']}){flag}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textunmark",
        description="Inspect and normalize hidden Unicode markers in UTF-8 text.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect", help="Inspect suspicious Unicode characters")
    inspect_parser.add_argument("input", help="UTF-8 file path or - for stdin")
    inspect_parser.add_argument("--json", action="store_true", help="Emit JSON report")

    sanitize_parser = sub.add_parser("sanitize", help="Normalize text conservatively")
    sanitize_parser.add_argument("input", help="UTF-8 file path or - for stdin")
    sanitize_parser.add_argument("-o", "--output", help="Output path; defaults to stdout")
    sanitize_parser.add_argument(
        "--profile",
        choices=["conservative", "strict"],
        default="conservative",
        help="strict can alter emoji, bidi text, and some scripts",
    )
    sanitize_parser.add_argument(
        "--normalization",
        choices=["none", "NFC", "NFKC"],
        default="NFC",
    )
    sanitize_parser.add_argument(
        "--report",
        help="Optional JSON report path. Use - to write report to stderr.",
    )
    sanitize_parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write output; exit 1 when sanitization would change text",
    )

    compare_parser = sub.add_parser("compare", help="Compare two UTF-8 text files")
    compare_parser.add_argument("before")
    compare_parser.add_argument("after")
    compare_parser.add_argument("--json", action="store_true", help="Emit full JSON report")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "inspect":
        report = inspect_text(_read_text(args.input))
        if args.json:
            _json_dump(report)
        else:
            _print_inspection(report)
        return 0

    if args.command == "sanitize":
        source = _read_text(args.input)
        result = sanitize_text(
            source,
            profile=args.profile,
            normalization=args.normalization,
        )
        if args.report:
            if args.report == "-":
                _json_dump(result.to_dict(include_text=False), stream=sys.stderr)
            else:
                Path(args.report).write_text(
                    json.dumps(result.to_dict(include_text=False), ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        if args.check:
            return 1 if result.changed else 0
        _write_text(args.output, result.text)
        return 0

    if args.command == "compare":
        report = compare_texts(_read_text(args.before), _read_text(args.after))
        if args.json:
            _json_dump(report)
        else:
            print(f"Identical: {report['identical']}")
            print(f"Similarity: {report['similarity_ratio']:.6f}")
            print(
                "Findings: "
                f"{report['before_inspection']['finding_count']} -> "
                f"{report['after_inspection']['finding_count']}"
            )
            print(f"SHA-256 before: {report['before_sha256']}")
            print(f"SHA-256 after:  {report['after_sha256']}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
