from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.entities import Profile
from utils.config import PROFILES_DIR


def _profile_path(profile_id: str) -> Path:
    return PROFILES_DIR / f"{profile_id}.json"


def load_profiles() -> list[Profile]:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profiles: list[Profile] = []
    for path in sorted(PROFILES_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        profiles.append(Profile(**payload))
    return profiles


def get_profile(profile_id: str) -> Profile:
    path = _profile_path(profile_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Profile(**payload)


def save_profile(payload: dict[str, Any]) -> Profile:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    profile = Profile(**payload)
    _profile_path(profile.id).write_text(
        json.dumps(profile.to_dict(), indent=2),
        encoding="utf-8",
    )
    return profile


def delete_profile(profile_id: str) -> None:
    path = _profile_path(profile_id)
    if path.exists():
        path.unlink()
