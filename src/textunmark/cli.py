from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys

from . import __version__
from .batch import process_path
from .compare import compare_texts
from .config import Settings, load_config
from .detectors.registry import available_detectors, run_detectors
from .pipeline import analyze_text
from .report import render_analysis_html
from .sanitize import sanitize_text
from .sarif import scan_to_sarif
from .unicode_scan import inspect_text


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def _write_text(path: str | None, text: str) -> None:
    if path is None or path == "-":
        sys.stdout.write(text)
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _json_dump(data: object, stream=sys.stdout) -> None:
    json.dump(data, stream, ensure_ascii=False, indent=2)
    stream.write("\n")


def _write_json(path: str | None, data: object) -> None:
    if path is None or path == "-":
        _json_dump(data)
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _print_inspection(report: dict[str, object]) -> None:
    print(f"Length: {report['length']}")
    print(f"UTF-8 bytes: {report['utf8_bytes']}")
    print(f"Lines: {report['line_count']}")
    print(f"Findings: {report['finding_count']}")
    print(f"Context-sensitive: {report['context_sensitive_count']}")
    findings = report["findings"]
    if not findings:
        print("No suspicious Unicode markers found.")
        return
    print()
    for item in findings:
        flag = " [context-sensitive]" if item["context_sensitive"] else ""
        location = f"{item['line']}:{item['column']}"
        print(
            f"{location:>10}  idx={item['index']:<6} {item['codepoint']}  {item['name']}"
            f"  ({item['reason']}){flag}"
        )


def _add_config_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        help="TOML config path; defaults to ./textunmark.toml when present",
    )


def _add_profile_args(parser: argparse.ArgumentParser) -> None:
    _add_config_arg(parser)
    parser.add_argument(
        "--profile",
        choices=["conservative", "strict"],
        default=None,
        help="Override config profile; strict can alter emoji, bidi text, and some scripts",
    )
    parser.add_argument(
        "--normalization",
        choices=["none", "NFC", "NFKC"],
        default=None,
        help="Override config normalization",
    )


def _settings(args: argparse.Namespace) -> Settings:
    return load_config(getattr(args, "config", None))


def _profile_values(args: argparse.Namespace, settings: Settings) -> tuple[str, str]:
    return args.profile or settings.profile, args.normalization or settings.normalization


def _detector_values(args: argparse.Namespace, settings: Settings) -> list[str] | None:
    explicit = getattr(args, "detectors", None)
    if explicit:
        return explicit
    return list(settings.detectors) or None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="textunmark",
        description="Inspect, normalize, scan, and report hidden Unicode markers in UTF-8 text.",
    )
    parser.add_argument("--version", action="version", version=f"TextUnmark {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect", help="Inspect suspicious Unicode characters")
    inspect_parser.add_argument("input", help="UTF-8 file path or - for stdin")
    inspect_parser.add_argument("--json", action="store_true", help="Emit JSON report")
    inspect_parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit 1 when one or more findings are present",
    )

    sanitize_parser = sub.add_parser("sanitize", help="Normalize text")
    sanitize_parser.add_argument("input", help="UTF-8 file path or - for stdin")
    sanitize_parser.add_argument("-o", "--output", help="Output path; defaults to stdout")
    _add_profile_args(sanitize_parser)
    sanitize_parser.add_argument("--report", help="Optional JSON report path. Use - for stderr.")
    sanitize_parser.add_argument(
        "--check", action="store_true", help="Exit 1 when sanitization would change text"
    )

    compare_parser = sub.add_parser("compare", help="Compare two UTF-8 text files")
    compare_parser.add_argument("before")
    compare_parser.add_argument("after")
    compare_parser.add_argument("--json", action="store_true", help="Emit full JSON report")

    analyze_parser = sub.add_parser("analyze", help="Run inspection, sanitization preview, and detectors")
    analyze_parser.add_argument("input")
    _add_profile_args(analyze_parser)
    analyze_parser.add_argument("--detector", action="append", dest="detectors")
    analyze_parser.add_argument("--json", action="store_true")
    analyze_parser.add_argument("-o", "--output", help="Write JSON analysis to a file")
    analyze_parser.add_argument("--include-text", action="store_true", help="Include sanitized text in JSON")

    detect_parser = sub.add_parser("detect", help="Run registered detector adapters")
    detect_parser.add_argument("input")
    _add_config_arg(detect_parser)
    detect_parser.add_argument("--detector", action="append", dest="detectors")
    detect_parser.add_argument("--json", action="store_true")

    sub.add_parser("detectors", help="List registered detectors")

    batch_parser = sub.add_parser("batch", help="Recursively inspect/sanitize supported text files")
    batch_parser.add_argument("root")
    _add_profile_args(batch_parser)
    destination = batch_parser.add_mutually_exclusive_group()
    destination.add_argument("--output-dir", help="Write changed files under this directory")
    destination.add_argument("--in-place", action="store_true", help="Modify changed files in place")
    batch_parser.add_argument("--dry-run", action="store_true", help="Never write text files")
    batch_parser.add_argument("--json", action="store_true")
    batch_parser.add_argument("--report", help="Write batch JSON report to file")
    batch_parser.add_argument(
        "--fail-on-change",
        action="store_true",
        help="Exit 1 when one or more files would change (errors still exit 2)",
    )
    batch_parser.add_argument(
        "--ext",
        action="append",
        dest="extensions",
        help="Limit to extension; repeatable, e.g. --ext .md --ext .py",
    )

    scan_parser = sub.add_parser("scan", help="Scan a file or tree and emit SARIF")
    scan_parser.add_argument("root")
    scan_parser.add_argument("-o", "--output", default="-", help="SARIF output path or - for stdout")
    scan_parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit 1 when the SARIF result contains findings",
    )

    report_parser = sub.add_parser("report", help="Generate a standalone local HTML analysis report")
    report_parser.add_argument("input")
    report_parser.add_argument("-o", "--output", required=True)
    _add_profile_args(report_parser)
    report_parser.add_argument("--detector", action="append", dest="detectors")
    report_parser.add_argument("--title", default="TextUnmark analysis report")

    doctor_parser = sub.add_parser("doctor", help="Show local runtime and detector availability")
    _add_config_arg(doctor_parser)

    config_parser = sub.add_parser("config", help="Show resolved TextUnmark configuration")
    _add_config_arg(config_parser)
    config_parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "inspect":
        report = inspect_text(_read_text(args.input))
        _json_dump(report) if args.json else _print_inspection(report)
        if args.fail_on_findings and report["finding_count"]:
            return 1
        return 0

    if args.command == "sanitize":
        settings = _settings(args)
        profile, normalization = _profile_values(args, settings)
        source = _read_text(args.input)
        result = sanitize_text(source, profile=profile, normalization=normalization)
        if args.report:
            report = result.to_dict(include_text=False)
            if args.report == "-":
                _json_dump(report, stream=sys.stderr)
            else:
                _write_json(args.report, report)
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

    if args.command == "analyze":
        settings = _settings(args)
        profile, normalization = _profile_values(args, settings)
        result = analyze_text(
            _read_text(args.input),
            profile=profile,
            normalization=normalization,
            detector_ids=_detector_values(args, settings),
        )
        report = result.to_dict(include_text=args.include_text)
        if args.output:
            _write_json(args.output, report)
        elif args.json:
            _json_dump(report)
        else:
            comparison = report["comparison"]
            print(f"Findings: {report['inspection']['finding_count']}")
            print(f"Changed by profile: {report['sanitized']['changed']}")
            print(f"Similarity: {comparison['similarity_ratio']:.6f}")
            for detector in report["detectors_before"]:
                print(f"Detector {detector['detector_id']}: score={detector['score']:.6f} detected={detector['detected']}")
        return 0

    if args.command == "detect":
        settings = _settings(args)
        results = [
            r.to_dict()
            for r in run_detectors(_read_text(args.input), _detector_values(args, settings))
        ]
        if args.json:
            _json_dump(results)
        else:
            for result in results:
                print(
                    f"{result['detector_id']}: detected={result['detected']} "
                    f"score={result['score']:.6f}"
                )
        return 0

    if args.command == "detectors":
        for detector in available_detectors():
            print(f"{detector['id']:<20} {detector['label']}\n  {detector['description']}")
        return 0

    if args.command == "batch":
        settings = _settings(args)
        profile, normalization = _profile_values(args, settings)
        configured_extensions = args.extensions or list(settings.extensions)
        extensions = None
        if configured_extensions:
            extensions = {
                ext if ext.startswith(".") else f".{ext}" for ext in configured_extensions
            }
        report = process_path(
            Path(args.root),
            output_dir=Path(args.output_dir) if args.output_dir else None,
            in_place=args.in_place,
            dry_run=args.dry_run,
            profile=profile,
            normalization=normalization,
            extensions=extensions,
        )
        if args.report:
            _write_json(args.report, report)
        if args.json:
            _json_dump(report)
        else:
            print(f"Files: {report['file_count']}")
            print(f"Changed: {report['changed_count']}")
            print(f"Errors: {report['error_count']}")
            print(f"Findings: {report['finding_count_before']} -> {report['finding_count_after']}")
        if report["error_count"]:
            return 2
        if args.fail_on_change and report["changed_count"]:
            return 1
        return 0

    if args.command == "scan":
        sarif = scan_to_sarif(Path(args.root))
        _write_json(args.output, sarif)
        finding_count = len(sarif["runs"][0]["results"])
        if args.fail_on_findings and finding_count:
            return 1
        return 0

    if args.command == "report":
        settings = _settings(args)
        profile, normalization = _profile_values(args, settings)
        result = analyze_text(
            _read_text(args.input),
            profile=profile,
            normalization=normalization,
            detector_ids=_detector_values(args, settings),
        )
        html = render_analysis_html(args.title, result.to_dict(include_text=False))
        _write_text(args.output, html)
        print(f"Wrote {args.output}")
        return 0

    if args.command == "doctor":
        settings = _settings(args)
        print(f"TextUnmark: {__version__}")
        print(f"Python: {platform.python_version()}")
        print(f"Platform: {platform.platform()}")
        print("Runtime dependencies: none")
        print(f"Config: {settings.source or '(defaults)'}")
        print("Detectors:")
        for detector in available_detectors():
            print(f"  - {detector['id']}: {detector['label']}")
        return 0

    if args.command == "config":
        settings = _settings(args)
        if args.json:
            _json_dump(settings.to_dict())
        else:
            print(f"Source: {settings.source or '(defaults)'}")
            print(f"Profile: {settings.profile}")
            print(f"Normalization: {settings.normalization}")
            print(f"Detectors: {', '.join(settings.detectors) or '(all built-ins)'}")
            print(f"Extensions: {', '.join(settings.extensions) or '(built-in defaults)'}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
