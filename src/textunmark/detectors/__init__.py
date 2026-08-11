"""Detector plugin API and built-in detectors."""

from .base import DetectionResult, Detector
from .registry import available_detectors, get_detector, run_detectors

__all__ = [
    "DetectionResult",
    "Detector",
    "available_detectors",
    "get_detector",
    "run_detectors",
]
