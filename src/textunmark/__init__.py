"""TextUnmark public package API."""

from .compare import compare_texts
from .pipeline import AnalysisResult, analyze_text
from .sanitize import SanitizeResult, sanitize_text
from .unicode_scan import Finding, inspect_text

__all__ = [
    "AnalysisResult",
    "Finding",
    "SanitizeResult",
    "analyze_text",
    "compare_texts",
    "inspect_text",
    "sanitize_text",
]

__version__ = "0.2.0"
