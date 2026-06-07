import csv
from datetime import datetime, timezone

from pipeline.schema import Activity, canonical_sport, to_utc
from pipeline.writer import _avg_speed_ms, _num, write_dataset

UTC = timezone.utc


def test_canonical_sport_maps_families():
    assert canonical_sport("running") == "run"
    assert canonical_sport("cycling") == "ride"
    assert canonical_sport("lap_swimming") == "swim"
    assert canonical_sport("yoga") == "yoga"
    assert canonical_sport("HIIT") == "workout"
    assert canonical_sport("some_unknown_thing") == "other"
    assert canonical_sport(None) == "other"


def test_num_rounds_and_blanks():
    assert _num(6.289410156, 3) == 6.289
    assert _num(160.0, 0) == 160          # integer, no trailing .0
    assert _num(None, 3) == ""


def test_avg_speed():
    a = Activity(source="garmin", source_id="1", start=datetime(2026, 6, 1, tzinfo=UTC),
                 sport="run", distance_km=10, moving_s=3000)
    assert round(_avg_speed_ms(a), 2) == 3.33  # 10000 m / 3000 s


def test_naive_datetime_is_treated_as_utc():
    assert to_utc(datetime(2026, 6, 1, 6, 30)).tzinfo == UTC


def test_write_dataset_roundtrip(tmp_path):
    acts = [
        Activity(source="garmin", source_id="1", start=datetime(2026, 6, 1, 6, 30, tzinfo=UTC),
                 sport="run", raw_sport="running", name="Morning Run",
                 distance_km=10.123456, moving_s=3000, avg_hr=160, calories=600),
        Activity(source="garmin", source_id="2", start=datetime(2026, 5, 20, 8, 0, tzinfo=UTC),
                 sport="ride", raw_sport="cycling", name="Long Ride",
                 distance_km=40, moving_s=7200, avg_hr=140, calories=1200),
    ]
    summary = write_dataset(acts, str(tmp_path))
    assert summary["activities_written"] == 2

    rows = list(csv.DictReader(open(tmp_path / "activities.csv")))
    assert len(rows) == 2
    assert rows[0]["Activity Name"] == "Morning Run"   # newest first
    assert rows[0]["Activity Type"] == "Run"           # sport, title-cased
    assert rows[0]["Distance"] == "10.123"             # rounded to 3 dp
    assert rows[0]["Source"] == "garmin"
