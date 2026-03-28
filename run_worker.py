import logging
import time

from backend.profile_text_store import is_profile_text_available, load_profile_text
from services.worker import run_cycle


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    while True:
        if not is_profile_text_available():
            print("No active profile. Skipping job fetch.")
            time.sleep(1800)
            continue
        profile_text = load_profile_text()
        if not profile_text:
            print("Active profile text could not be loaded. Retrying later.")
            time.sleep(1800)
            continue
        run_cycle(profile_text)
        time.sleep(1800)
