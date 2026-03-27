from backend.profile_manager import load_profiles
from services.worker import scheduler_loop


if __name__ == "__main__":
    profiles = load_profiles()
    if not profiles:
        raise SystemExit("No profiles found in data/profiles.")
    scheduler_loop(profiles[0], interval_minutes=30)
