from __future__ import annotations

from .base import DetectionResult, Detector
from ..unicode_scan import inspect_text


class UnicodeArtifactDetector(Detector):
    detector_id = "unicode-artifact"
    label = "Unicode artifact detector"
    description = (
        "Reports suspicious invisible/control Unicode artifacts. It is not a "
        "provider watermark detector."
    )

    def detect(self, text: str) -> DetectionResult:
        report = inspect_text(text)
        findings = int(report["finding_count"])
        length = max(int(report["length"]), 1)
        density = findings / length
        # A bounded convenience score for dashboards; not a probability.
        score = min(1.0, density * 100.0)
        return DetectionResult(
            detector_id=self.detector_id,
            label=self.label,
            detected=findings > 0,
            score=score,
            confidence=None,
            details={
                "finding_count": findings,
                "density": density,
                "by_reason": report["by_reason"],
                "note": "Score is an artifact-density indicator, not watermark probability.",
            },
        )
