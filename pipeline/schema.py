"""Common activity model + sport-name normalization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

# Map Garmin's many sport keys onto a tidy family for display/filtering.
_SPORT_FAMILY = {
    "running": "run", "trail_running": "run", "treadmill_running": "run",
    "track_running": "run", "virtual_run": "run", "indoor_running": "run",
    "cycling": "ride", "road_biking": "ride", "mountain_biking": "ride",
    "gravel_cycling": "ride", "indoor_cycling": "ride", "virtual_ride": "ride",
    "cyclocross": "ride", "emountain_biking": "ride", "commuting": "ride",
    "lap_swimming": "swim", "open_water_swimming": "swim", "swimming": "swim",
    "walking": "walk", "casual_walking": "walk", "speed_walking": "walk",
    "hiking": "hike",
    "rowing": "row", "indoor_rowing": "row",
    "strength_training": "strength",
    "yoga": "yoga", "pilates": "yoga", "breathwork": "yoga", "meditation": "yoga",
    "indoor_cardio": "workout", "cardio": "workout", "hiit": "workout",
    "elliptical": "workout", "stair_climbing": "workout",
    "bouldering": "climb", "rock_climbing": "climb", "indoor_climbing": "climb",
}
_KNOWN = {"run", "ride", "swim", "walk", "hike", "row", "strength", "workout", "yoga", "climb"}


def canonical_sport(raw_type: Optional[str]) -> str:
    if not raw_type:
        return "other"
    key = str(raw_type).strip().lower().replace(" ", "_").replace("-", "_")
    if key in _SPORT_FAMILY:
        return _SPORT_FAMILY[key]
    return key if key in _KNOWN else "other"


def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


@dataclass
class Activity:
    source: str
    source_id: str
    start: Optional[datetime]
    sport: str
    raw_sport: Optional[str] = None
    name: Optional[str] = None
    distance_km: Optional[float] = None
    moving_s: Optional[int] = None
    elapsed_s: Optional[int] = None
    elevation_gain_m: Optional[float] = None
    avg_hr: Optional[float] = None
    max_hr: Optional[float] = None
    avg_watts: Optional[float] = None
    calories: Optional[float] = None
    track_file: Optional[str] = None

    def __post_init__(self):
        self.start = to_utc(self.start)
        if not self.sport:
            self.sport = canonical_sport(self.raw_sport)
