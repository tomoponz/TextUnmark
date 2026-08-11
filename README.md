# TextUnmark

TextUnmark is a **browser-first, local-first** toolkit for inspecting invisible Unicode, unusual spaces, control characters, and other explicit text artifacts before deciding whether to normalize them.

The primary product is the static Web app in `web/`. The Python CLI remains available for experiments, automation, repository scanning, and reference testing.

> **Current scope:** TextUnmark does **not** claim to detect or remove Anthropic's announced model-level watermark. Anthropic-specific support should only be added after a reproducible public specification or detector becomes available. The current browser detector reports explicit Unicode artifacts and labels Anthropic detection as unavailable.

## Browser app

The Web app runs without a backend. Text pasted into the editor and text files opened through the file picker are processed locally in the browser by JavaScript and a Web Worker.

### Features

- Paste text and inspect it immediately.
- Drag and drop one or more UTF-8 text/source files.
- File audit table with finding counts and line counts.
- 10 MB per-file guard and basic binary/NUL rejection.
- Exact finding positions using Unicode code-point index, UTF-16 index, UTF-8 byte offset, line, and column.
- Detection of known zero-width characters, special spaces, bidi controls, join controls, variation selectors, Unicode tags, and generic Unicode `Cf` / `Cc` controls.
- Three explicit modes:
  - **Inspect only** — no text mutation.
  - **Standard cleanup** — normalizes a limited set of invisible characters and spaces, with every mutation shown before copying/downloading.
  - **Aggressive cleanup** — also removes context-sensitive formatting characters; this can change presentation or meaning.
- Per-finding context previews.
- Exact mutation list instead of a guessed edit-count metric.
- Detector panel that separates descriptive Unicode findings from provider watermark detection.
- Copy result, download TXT, and export a JSON report.
- Responsive layout for desktop and mobile.
- No third-party runtime dependencies.

### Run locally

From the repository root:

```bash
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/
```

The root `index.html` forwards to `web/`.

You can also serve only the Web directory:

```bash
python -m http.server 8000 -d web
```

### GitHub Pages

The repository now contains a static root entry point plus the complete app under `web/`, so it is ready to be served from a static host such as GitHub Pages. This repository does not automatically enable or publish GitHub Pages; deployment can be configured separately when desired.

## Web architecture

```text
web/
  index.html       UI shell
  styles.css       responsive UI
  app.mjs          browser workflow, files, rendering, downloads
  engine.mjs       Unicode inspection, cleanup, detector registry
  worker.mjs       background analysis
  engine.test.mjs  Node-based browser-engine tests
```

The analysis engine is deliberately separated from the DOM layer so the same logic can be called from the Web Worker and test suite.

## Cleanup behavior

TextUnmark defaults to **Inspect only** in the browser. No text is changed until a cleanup mode is selected.

`Standard cleanup` currently handles a limited set of explicit characters such as ZERO WIDTH SPACE, SOFT HYPHEN, WORD JOINER, BOM/ZWNBSP, NO-BREAK SPACE, FIGURE SPACE, and NARROW NO-BREAK SPACE, plus newline and NFC normalization. These changes can still affect line breaking or typography, so the app exposes every mutation instead of calling the mode lossless.

`Aggressive cleanup` additionally removes context-sensitive findings such as join/bidi controls and variation selectors. Use it only after reviewing the change list.

## Detector model

The browser detector registry currently contains:

- `unicode-artifact` — available; reports explicit Unicode findings and descriptive metrics such as finding count and artifact density. It is **not** an AI-watermark probability.
- `anthropic` — intentionally unavailable placeholder until a reproducible public detector/specification can be integrated.

Future detector implementations should preserve this distinction rather than converting unrelated metrics into a generic probability-like score.

## Python CLI (secondary)

Python 3.11+ is still supported for automation and experiments:

```bash
python -m pip install -e .
textunmark inspect input.txt
textunmark analyze input.txt --json
textunmark batch . --dry-run
textunmark scan . -o textunmark.sarif
```

The CLI includes repository batch processing, SARIF output, HTML reports, TOML configuration, and the Python detector adapter interface.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m compileall -q src
node --check web/engine.mjs
node --check web/worker.mjs
node --check web/app.mjs
node --test web/engine.test.mjs
```

GitHub Actions runs Python tests on 3.11, 3.12, and 3.13 and runs the browser-engine checks/tests on Node 22.

## Design principles

1. **Browser first.** A normal user should be able to open a URL, paste text, inspect it, and export a result without installing Python.
2. **Local processing.** The included Web app has no TextUnmark backend and does not upload the inspected text to one.
3. **Inspect before mutate.** Browser default is non-mutating; cleanup is explicit and previewed.
4. **Show exact changes.** Mutation records identify removal, replacement, or normalization instead of presenting an unreliable edit count.
5. **Do not guess provider watermarks.** Unsupported provider detectors remain visibly unavailable.
6. **Do not present descriptive artifact metrics as authorship probabilities.**

## License

No open-source license has been selected yet. Add one before accepting external contributions if you want others to have explicit rights to use, modify, and redistribute the code.
