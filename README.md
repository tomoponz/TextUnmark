# TextUnmark

TextUnmark is a local-first toolkit for inspecting suspicious Unicode markers, normalizing text, scanning repositories, generating reproducible reports, and experimenting with text-watermark detectors through a stable plugin interface.

It currently focuses on text-level artifacts that can be inspected deterministically: zero-width characters, unusual spaces, format controls, bidi controls, join controls, variation selectors, Unicode tag characters, and related code points.

> **Current scope:** TextUnmark does **not** claim to detect or remove Anthropic's announced model-level watermark. Anthropic has not yet published enough technical detail for a verified implementation. Provider-specific support should be added only after a reproducible public specification or detector is available.

## Highlights

- Local-first CLI with no runtime dependencies on Python 3.11+.
- Browser UI under `web/` that performs inspection and sanitization entirely on-device.
- Exact Unicode findings with code point, index, line, column, UTF-8 offset, category, and reason.
- Conservative and strict sanitization profiles.
- NFC / opt-in NFKC normalization.
- SHA-256, similarity, edit-operation, and before/after marker comparison.
- Detector plugin API with a built-in Unicode artifact detector.
- Recursive batch processing for text, Markdown, source code, JSON, YAML, HTML, CSS, and more.
- SARIF output for repository/code-scanning workflows.
- Standalone HTML analysis reports.
- JSON output throughout for reproducible experiments and automation.
- TOML configuration via `textunmark.toml`.
- GitHub Actions tests on Python 3.11, 3.12, and 3.13 plus browser JavaScript syntax validation.

## Install

```bash
python -m pip install -e .
```

This installs the `textunmark` command.

```bash
textunmark --version
textunmark doctor
```

## Quick start

Inspect a file:

```bash
textunmark inspect input.txt
textunmark inspect input.txt --json
```

Sanitize conservatively:

```bash
textunmark sanitize input.txt -o cleaned.txt
```

Compare the original and cleaned files:

```bash
textunmark compare input.txt cleaned.txt
```

Run the complete analysis pipeline:

```bash
textunmark analyze input.txt
textunmark analyze input.txt --json
```

Generate a standalone HTML report:

```bash
textunmark report input.txt -o report.html
```

## Inspect

`inspect` reports suspicious/invisible characters without changing the input.

```bash
printf 'A\u200bB\n' | textunmark inspect -
```

Example:

```text
     1  U+200B  ZERO WIDTH SPACE  (zero-width)
```

The JSON representation also contains line, column, UTF-8 byte offset, Unicode category, and whether the character is context-sensitive.

## Sanitization profiles

The default `conservative` profile removes or normalizes a small set of broadly non-semantic text artifacts while preserving characters that may be meaningful in emoji, bidirectional text, or some writing systems.

```bash
textunmark sanitize input.txt -o cleaned.txt
```

It currently:

- removes ZERO WIDTH SPACE, WORD JOINER, SOFT HYPHEN, and BOM/ZWNBSP;
- converts common no-break/figure spaces to ordinary spaces;
- normalizes line endings;
- applies NFC by default;
- preserves ZWJ, ZWNJ, bidi controls, and variation selectors.

Generate a JSON report:

```bash
textunmark sanitize input.txt -o cleaned.txt --report sanitize.json
```

Check without writing output:

```bash
textunmark sanitize input.txt --check
```

`strict` removes additional context-sensitive formatting characters and is intended for controlled experiments:

```bash
textunmark sanitize input.txt -o cleaned.txt --profile strict
```

**Strict mode can change emoji presentation, bidirectional text, and scripts that rely on join controls.**

NFKC is also explicit because compatibility normalization can change representation:

```bash
textunmark sanitize input.txt -o cleaned.txt --normalization NFKC
```

## Analyze

`analyze` combines inspection, a sanitization preview, before/after comparison, and all configured detectors.

```bash
textunmark analyze input.txt
textunmark analyze input.txt --json
textunmark analyze input.txt --include-text --json
```

The output includes:

- Unicode findings;
- sanitization changes;
- SHA-256 hashes;
- `SequenceMatcher` similarity;
- insert/delete/replace operations;
- detector scores before and after sanitization.

## Detector plugins

List available detectors:

```bash
textunmark detectors
```

Run detectors directly:

```bash
textunmark detect input.txt
textunmark detect input.txt --detector unicode-artifact --json
```

The built-in `unicode-artifact` detector is deliberately labeled as an artifact detector. Its score is a bounded marker-density indicator, **not a probability that text contains an AI watermark**.

Provider-specific detectors can implement the stable adapter under `src/textunmark/detectors/` when reproducible public specifications become available.

## Batch processing

Dry-run an entire project:

```bash
textunmark batch . --dry-run
```

Write changed files to a separate tree:

```bash
textunmark batch ./input --output-dir ./cleaned
```

Modify files in place only when explicitly requested:

```bash
textunmark batch ./docs --in-place
```

Limit file extensions:

```bash
textunmark batch . --dry-run --ext .md --ext .py
```

By default, common text/source formats are supported and directories such as `.git`, `.venv`, `node_modules`, `build`, and `dist` are skipped.

## SARIF scanning

Generate SARIF 2.1.0 for repository inspection workflows:

```bash
textunmark scan . -o textunmark.sarif
```

Each finding includes a rule ID such as `unicode/zero-width` and a file/line/column location.

## HTML reports

Create a self-contained local report:

```bash
textunmark report input.txt -o report.html --title "My analysis"
```

The report includes marker counts, before/after similarity, detector scores, findings, and SHA-256 integrity values. It has no remote runtime dependency.

## Configuration

TextUnmark automatically reads `./textunmark.toml` when present. You can also provide an explicit config path with `--config` on commands that use profiles or detectors.

Example (`examples/textunmark.toml`):

```toml
[textunmark]
profile = "conservative"
normalization = "NFC"
detectors = ["unicode-artifact"]
extensions = [".txt", ".md", ".py", ".js", ".json"]
```

Inspect resolved settings:

```bash
textunmark config
textunmark config --json
```

Command-line profile, normalization, detector, and extension options override the corresponding configured values.

## Browser UI

The `web/` directory contains a dependency-free browser version.

For local use, serve the repository directory with any static server, for example:

```bash
python -m http.server 8000 -d web
```

Then open `http://localhost:8000`.

The browser UI supports:

- paste-and-inspect;
- conservative and strict sanitization;
- finding tables;
- TXT download;
- JSON report download;
- clipboard copy.

Text remains in the browser; the included Web UI does not send it to a TextUnmark server.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src
node --check web/app.js
```

GitHub Actions validates Python 3.11, 3.12, and 3.13 and performs smoke tests across the expanded CLI.

## Project structure

```text
src/textunmark/
  batch.py
  cli.py
  compare.py
  config.py
  detectors/
  pipeline.py
  report.py
  sanitize.py
  sarif.py
  unicode_scan.py
web/
  index.html
  styles.css
  app.js
tests/
examples/
```

## Roadmap

- Add provider-specific detector adapters only after reproducible public specifications/detectors exist.
- Add benchmark datasets for watermark robustness research.
- Add code-formatter/refactor robustness test suites.
- Add richer detector calibration and false-positive evaluation.
- Add optional packaged desktop/browser distribution without changing the local-first model.

## Design principles

1. **Do not guess watermark mechanisms.** Provider-specific support is labeled supported only when independently reproducible.
2. **Show mutations.** Sanitization is deterministic and before/after comparison is available.
3. **Preserve meaning by default.** Context-sensitive Unicode is reported instead of silently deleted by the conservative profile.
4. **Local first.** Core functionality runs without sending text to an external service.
5. **Measure instead of claim.** Detector scores and robustness results should be reported rather than treated as proof of authorship.
6. **Safe automation.** Recursive writes require explicit output or in-place options; dry-run is available for inspection-first workflows.

## License

No open-source license has been selected yet. Add one before accepting external contributions if you want others to have explicit rights to use, modify, and redistribute the code.
