"""Garmin Connect source adapter (via the python-garminconnect library).

Resumes from a serialized session token (GARMINTOKENS) so no password is ever
stored. Mint the token once with scripts/garmin_login.py.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from ..schema import Activity, canonical_sport


def _login():
    from garminconnect import Garmin

    tokens = os.environ.get("GARMINTOKENS")
    if tokens:
        g = Garmin()
        g.login(tokens)  # >512-char arg is treated as token data, not a path
        return g
    raise RuntimeError(
        "Garmin: no session token. Run scripts/garmin_login.py once to mint "
        "GARMINTOKENS (handles MFA; no password stored)."
    )


def _parse_start(raw: dict) -> datetime | None:
    s = raw.get("startTimeGMT")  # "2024-08-18 13:00:00" in UTC
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _download_track(g, activity_id, data_dir: str) -> str | None:
    rel = f"tracks/garmin-{activity_id}.gpx"
    if Path(data_dir, rel).exists():
        return rel  # already have it - refreshes stay incremental
    try:
        from garminconnect import Garmin
        data = g.download_activity(activity_id, dl_fmt=Garmin.ActivityDownloadFormat.GPX)
        Path(data_dir, rel).write_bytes(data)
        return rel
    except Exception:
        return None


def fetch(days_back: int = 30, download_tracks: bool = True, data_dir: str = "data") -> list[Activity]:
    g = _login()
    start = (date.today() - timedelta(days=days_back)).isoformat()
    end = date.today().isoformat()
    raw_list = g.get_activities_by_date(start, end)

    out: list[Activity] = []
    for r in raw_list:
        aid = r.get("activityId")
        type_key = (r.get("activityType") or {}).get("typeKey")
        dist_m = r.get("distance")
        out.append(Activity(
            source="garmin",
            source_id=str(aid),
            start=_parse_start(r),
            sport=canonical_sport(type_key),
            raw_sport=type_key,
            name=r.get("activityName"),
            distance_km=(dist_m / 1000.0) if dist_m else None,
            moving_s=int(r["movingDuration"]) if r.get("movingDuration") else (
                int(r["duration"]) if r.get("duration") else None),
            elapsed_s=int(r["duration"]) if r.get("duration") else None,
            elevation_gain_m=r.get("elevationGain"),
            avg_hr=r.get("averageHR"),
            max_hr=r.get("maxHR"),
            avg_watts=r.get("avgPower") or r.get("averagePower"),
            calories=r.get("calories"),
            track_file=_download_track(g, aid, data_dir) if download_tracks else None,
        ))
    return out
