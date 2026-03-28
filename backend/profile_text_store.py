from __future__ import annotations

from pathlib import Path

from utils.config import PROFILES_DIR


PROFILE_TEXT_PATH = PROFILES_DIR / "active_profile.txt"


def save_profile_text(profile_text: str) -> None:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_TEXT_PATH.write_text(profile_text, encoding="utf-8")


def load_profile_text() -> str | None:
    if not PROFILE_TEXT_PATH.exists():
        return None
    return PROFILE_TEXT_PATH.read_text(encoding="utf-8")


def clear_profile_text() -> None:
    if PROFILE_TEXT_PATH.exists():
        PROFILE_TEXT_PATH.unlink()


def is_profile_text_available() -> bool:
    return PROFILE_TEXT_PATH.exists()
