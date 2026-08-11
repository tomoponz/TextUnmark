# TextUnmark

TextUnmark is a local-first toolkit for inspecting suspicious Unicode markers, normalizing text, and comparing before/after results.

It is designed as a foundation for AI-text watermark analysis. Today it focuses on text-level artifacts that can be inspected deterministically: zero-width characters, unusual spaces, format controls, bidi controls, join controls, variation selectors, Unicode tag characters, and related code points.

> **Current scope:** TextUnmark does **not** claim to detect or remove Anthropic's announced model-level watermark. Anthropic has not yet published enough technical detail for a verified implementation. A provider-specific detector should only be added after a reproducible public specification or detector becomes available.

## Features

- Inspect invisible and unusual Unicode characters with exact indexes and code points.
- Distinguish ordinary suspicious markers from context-sensitive Unicode used by emoji, bidi text, and some writing systems.
- Conservative text sanitization that avoids removing context-sensitive characters by default.
- Optional strict sanitization for controlled experiments.
- NFC or opt-in NFKC Unicode normalization.
- Before/after comparison with SHA-256 hashes, similarity, edit operations, and marker counts.
- JSON output for reproducible experiments and automation.
- No runtime dependencies; runs locally on Python 3.11+.

## Install

```bash
python -m pip install -e .
```

This installs the `textunmark` command.

## Inspect text

```bash
textunmark inspect input.txt
```

Read from standard input:

```bash
printf 'A\u200bB\n' | textunmark inspect -
```

Machine-readable output:

```bash
textunmark inspect input.txt --json
```

Example finding:

```text
     1  U+200B  ZERO WIDTH SPACE  (zero-width)
```

## Sanitize text

The default profile is intentionally conservative:

```bash
textunmark sanitize input.txt -o cleaned.txt
```

It currently:

- removes ZERO WIDTH SPACE, WORD JOINER, SOFT HYPHEN, and BOM/ZWNBSP;
- converts common no-break/figure spaces to an ordinary space;
- normalizes line endings;
- applies NFC normalization by default;
- preserves ZWJ, ZWNJ, bidi controls, and variation selectors.

Generate a JSON report while writing cleaned text:

```bash
textunmark sanitize input.txt -o cleaned.txt --report report.json
```

Check whether sanitization would change a file without writing output:

```bash
textunmark sanitize input.txt --check
```

Exit status is `1` when a change would be made and `0` otherwise.

### Strict profile

```bash
textunmark sanitize input.txt -o cleaned.txt --profile strict
```

`strict` also removes several context-sensitive formatting characters. **It can change emoji presentation, bidirectional text, and text in scripts that use join controls.** Use it for controlled experiments, not as a blind cleanup step.

NFKC is also opt-in because compatibility normalization can change the representation of text:

```bash
textunmark sanitize input.txt -o cleaned.txt --normalization NFKC
```

## Compare before and after

```bash
textunmark compare input.txt cleaned.txt
```

Full machine-readable report:

```bash
textunmark compare input.txt cleaned.txt --json
```

The report includes:

- SHA-256 hashes;
- character lengths;
- `SequenceMatcher` similarity;
- insert/delete/replace operations;
- suspicious-character counts before and after.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

GitHub Actions runs the test suite and CLI smoke tests on Python 3.11, 3.12, and 3.13.

## Roadmap

- Provider-specific detector adapter interface.
- Reproducible watermark robustness benchmark datasets.
- Detection-score comparison when vendors publish supported detector APIs/specifications.
- HTML/Web UI that performs Unicode inspection locally in the browser.
- Code-oriented tests for formatter/refactor workflows.

## Design principles

1. **Do not guess watermark mechanisms.** A vendor-specific detector is labeled supported only when it can be independently reproduced.
2. **Show every text mutation.** Sanitization is deterministic and before/after comparison is available.
3. **Preserve meaning by default.** Characters with legitimate linguistic or emoji uses are reported rather than silently removed.
4. **Local first.** The initial implementation sends no text to an external service.
5. **Measure instead of claim.** Future watermark support should report detection scores and robustness results rather than claiming guaranteed removal.

## License

No open-source license has been selected yet. Add one before distributing or accepting external contributions if you want others to have explicit rights to use, modify, and redistribute the code.
