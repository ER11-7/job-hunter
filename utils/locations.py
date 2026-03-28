from __future__ import annotations


DELHI_NCR_VARIANTS = (
    "delhi",
    "new delhi",
    "delhi ncr",
    "gurgaon",
    "gurugram",
    "noida",
    "faridabad",
    "ghaziabad",
)
BENGLAURU_VARIANTS = (
    "bengaluru",
    "bangalore",
)
ALLOWED_LOCATION_VARIANTS = DELHI_NCR_VARIANTS + BENGLAURU_VARIANTS


def is_target_location(location: str) -> bool:
    location = (location or "").lower()
    return any(token in location for token in ALLOWED_LOCATION_VARIANTS)


def canonical_locations() -> list[str]:
    return ["Delhi NCR", "Bengaluru"]
