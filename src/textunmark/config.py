from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Any


@dataclass(frozen=True)
class Settings:
    profile: str = "conservative"
    normalization: str = "NFC"
    detectors: tuple[str, ...] = ()
    extensions: tuple[str, ...] = ()
    source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "normalization": self.normalization,
            "detectors": list(self.detectors),
            "extensions": list(self.extensions),
            "source": self.source,
        }


def _validate_profile(value: str) -> str:
    if value not in {"conservative", "strict"}:
        raise ValueError("config profile must be conservative or strict")
    return value


def _validate_normalization(value: str) -> str:
    if value not in {"none", "NFC", "NFKC"}:
        raise ValueError("config normalization must be one of: none, NFC, NFKC")
    return value


def _string_list(value: Any, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"config {key} must be an array of strings")
    return tuple(value)


def discover_config(explicit: str | None = None) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path
    candidate = Path("textunmark.toml")
    return candidate if candidate.is_file() else None


def load_config(path: str | None = None) -> Settings:
    config_path = discover_config(path)
    if config_path is None:
        return Settings()
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)
    section = data.get("textunmark", {})
    if not isinstance(section, dict):
        raise ValueError("[textunmark] must be a TOML table")

    profile = _validate_profile(str(section.get("profile", "conservative")))
    normalization = _validate_normalization(str(section.get("normalization", "NFC")))
    detectors = _string_list(section.get("detectors"), "detectors")
    extensions = _string_list(section.get("extensions"), "extensions")
    return Settings(
        profile=profile,
        normalization=normalization,
        detectors=detectors,
        extensions=extensions,
        source=str(config_path),
    )
