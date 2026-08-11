from __future__ import annotations

from .base import DetectionResult, Detector
from .unicode_artifact import UnicodeArtifactDetector


_BUILTINS: dict[str, type[Detector]] = {
    UnicodeArtifactDetector.detector_id: UnicodeArtifactDetector,
}


def available_detectors() -> list[dict[str, str]]:
    return [
        {
            "id": detector_id,
            "label": detector_type.label,
            "description": detector_type.description,
        }
        for detector_id, detector_type in sorted(_BUILTINS.items())
    ]


def get_detector(detector_id: str) -> Detector:
    try:
        return _BUILTINS[detector_id]()
    except KeyError as exc:
        choices = ", ".join(sorted(_BUILTINS))
        raise ValueError(f"unknown detector '{detector_id}'; available: {choices}") from exc


def run_detectors(text: str, detector_ids: list[str] | None = None) -> list[DetectionResult]:
    ids = detector_ids or sorted(_BUILTINS)
    return [get_detector(detector_id).detect(text) for detector_id in ids]
