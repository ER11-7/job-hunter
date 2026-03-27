from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
PROFILES_DIR = DATA_DIR / "profiles"
EXPORTS_DIR = DATA_DIR / "exports"
DB_PATH = DATA_DIR / "job_agent.db"

load_dotenv(BASE_DIR / ".env")


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


OPENAI_API_KEY = get_env("OPENAI_API_KEY")
OPENAI_MODEL = get_env("OPENAI_MODEL", "gpt-4o-mini")
SMTP_HOST = get_env("SMTP_HOST")
SMTP_PORT = int(get_env("SMTP_PORT", "587"))
SMTP_USER = get_env("SMTP_USER")
SMTP_PASSWORD = get_env("SMTP_PASSWORD")
SMTP_FROM = get_env("SMTP_FROM", "ai-job-agent@example.com")
APP_PASSWORD_SALT = get_env("APP_PASSWORD_SALT", "job-agent-salt")
