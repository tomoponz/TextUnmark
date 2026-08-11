from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DetectionResult:
    detector_id: str
    label: str
    detected: bool
    score: float
    confidence: float | None
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Detector(ABC):
    """Stable adapter interface for provider or research detectors."""

    detector_id: str
    label: str
    description: str

    @abstractmethod
    def detect(self, text: str) -> DetectionResult:
        raise NotImplementedError
