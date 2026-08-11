"""TextUnmark public package API."""

from .compare import compare_texts
from .sanitize import SanitizeResult, sanitize_text
from .unicode_scan import Finding, inspect_text

__all__ = [
    "Finding",
    "SanitizeResult",
    "compare_texts",
    "inspect_text",
    "sanitize_text",
]

__version__ = "0.1.0"
