from __future__ import annotations

from html import escape
from typing import Any


def _bar(label: str, value: float, max_value: float = 1.0) -> str:
    ratio = 0.0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
    pct = ratio * 100
    return (
        f'<div class="metric"><div class="metric-head"><span>{escape(label)}</span>'
        f'<strong>{value:.4f}</strong></div><div class="bar"><span style="width:{pct:.2f}%"></span></div></div>'
    )


def render_analysis_html(title: str, analysis: dict[str, Any]) -> str:
    inspection = analysis["inspection"]
    comparison = analysis["comparison"]
    sanitized = analysis["sanitized"]
    before_detectors = analysis.get("detectors_before", [])
    after_detectors = analysis.get("detectors_after", [])

    detector_rows = []
    after_by_id = {d["detector_id"]: d for d in after_detectors}
    for before in before_detectors:
        after = after_by_id.get(before["detector_id"], {})
        detector_rows.append(
            "<tr>"
            f"<td>{escape(before['label'])}</td>"
            f"<td>{before['score']:.4f}</td>"
            f"<td>{float(after.get('score', 0.0)):.4f}</td>"
            "</tr>"
        )

    finding_rows = []
    for finding in inspection.get("findings", [])[:500]:
        finding_rows.append(
            "<tr>"
            f"<td>{finding['index']}</td><td><code>{escape(finding['codepoint'])}</code></td>"
            f"<td>{escape(finding['name'])}</td><td>{escape(finding['reason'])}</td>"
            f"<td>{'yes' if finding['context_sensitive'] else 'no'}</td>"
            "</tr>"
        )

    source_hash = comparison["before_sha256"]
    result_hash = comparison["after_sha256"]
    similarity = float(comparison["similarity_ratio"])
    before_count = int(inspection["finding_count"])
    after_count = int(sanitized["after"]["finding_count"])

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
<style>
:root{{font-family:Inter,ui-sans-serif,system-ui,sans-serif;color-scheme:light dark}}
body{{margin:0;background:#0b0d10;color:#e8edf2}}main{{max-width:1100px;margin:auto;padding:32px 20px 64px}}
h1{{font-size:2rem;margin-bottom:8px}}.muted{{color:#9aa6b2}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:24px 0}}
.card{{border:1px solid #29313a;border-radius:14px;background:#11151a;padding:18px}}.big{{font-size:2rem;font-weight:700}}
.metric{{margin:14px 0}}.metric-head{{display:flex;justify-content:space-between;gap:16px}}.bar{{height:9px;background:#252c34;border-radius:999px;overflow:hidden;margin-top:7px}}.bar span{{display:block;height:100%;background:#d5dbe1}}
table{{width:100%;border-collapse:collapse;margin-top:12px}}th,td{{text-align:left;border-bottom:1px solid #29313a;padding:10px 8px;vertical-align:top}}code{{font-family:ui-monospace,SFMono-Regular,monospace}}details{{margin-top:18px}}
.hash{{overflow-wrap:anywhere;font-family:ui-monospace,SFMono-Regular,monospace;font-size:.83rem}}.section{{margin-top:28px}}
</style>
</head>
<body><main>
<h1>{escape(title)}</h1><p class="muted">Generated locally by TextUnmark. Detector scores are only meaningful according to each detector's own definition.</p>
<div class="grid">
<div class="card"><div class="muted">Suspicious markers</div><div class="big">{before_count} → {after_count}</div></div>
<div class="card"><div class="muted">Changed</div><div class="big">{'yes' if sanitized['changed'] else 'no'}</div></div>
<div class="card"><div class="muted">Edit count</div><div class="big">{sanitized['change_count']}</div></div>
<div class="card"><div class="muted">Similarity</div><div class="big">{similarity:.4f}</div></div>
</div>
<div class="card">{_bar('Before/after similarity', similarity)}</div>
<section class="section card"><h2>Detector results</h2><table><thead><tr><th>Detector</th><th>Before</th><th>After</th></tr></thead><tbody>{''.join(detector_rows) or '<tr><td colspan="3">No detectors configured.</td></tr>'}</tbody></table></section>
<section class="section card"><h2>Unicode findings</h2><table><thead><tr><th>Index</th><th>Code point</th><th>Name</th><th>Reason</th><th>Context-sensitive</th></tr></thead><tbody>{''.join(finding_rows) or '<tr><td colspan="5">No findings.</td></tr>'}</tbody></table></section>
<section class="section card"><h2>Integrity</h2><p class="muted">Source SHA-256</p><p class="hash">{source_hash}</p><p class="muted">Result SHA-256</p><p class="hash">{result_hash}</p></section>
<details><summary>Profile details</summary><pre>{escape(str({'profile': sanitized['profile'], 'normalization': sanitized['normalization']}))}</pre></details>
</main></body></html>"""
