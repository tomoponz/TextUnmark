from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .compare import compare_texts
from .detectors.registry import run_detectors
from .sanitize import sanitize_text
from .unicode_scan import inspect_text


@dataclass(frozen=True)
class AnalysisResult:
    inspection: dict[str, Any]
    sanitized: dict[str, Any]
    comparison: dict[str, Any]
    detectors_before: list[dict[str, Any]]
    detectors_after: list[dict[str, Any]]

    def to_dict(self, *, include_text: bool = False) -> dict[str, Any]:
        result = asdict(self)
        if not include_text:
            result["sanitized"].pop("text", None)
        return result


def analyze_text(
    text: str,
    *,
    profile: str = "conservative",
    normalization: str = "NFC",
    detector_ids: list[str] | None = None,
) -> AnalysisResult:
    inspection = inspect_text(text)
    sanitized_result = sanitize_text(
        text,
        profile=profile,
        normalization=normalization,
    )
    before_results = [r.to_dict() for r in run_detectors(text, detector_ids)]
    after_results = [r.to_dict() for r in run_detectors(sanitized_result.text, detector_ids)]
    return AnalysisResult(
        inspection=inspection,
        sanitized=sanitized_result.to_dict(include_text=True),
        comparison=compare_texts(text, sanitized_result.text),
        detectors_before=before_results,
        detectors_after=after_results,
    )
