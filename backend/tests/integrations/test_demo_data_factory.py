from datetime import datetime

from app.integrations.data_factory import HealthDataFactory, PersonalProfile


def test_generate_day_keys_and_ranges():
    factory = HealthDataFactory(profile=PersonalProfile(), seed=123)
    today = datetime.utcnow()
    day = factory.generate_day(today)

    # Core keys should be present
    for key in ["sleep_duration", "sleep_efficiency", "hrv_rmssd", "resting_hr"]:
        assert key in day

    assert isinstance(day["sleep_duration"], float)
    assert isinstance(day["hrv_rmssd"], float)


def test_generate_range_length_and_dates():
    factory = HealthDataFactory(seed=123)
    start = datetime(2024, 1, 1)
    out = factory.generate_range(start_date=start, days=5)
    assert len(out) == 5
    # Dates should be consecutive ISO strings
    dates = [row["date"] for row in out]
    assert dates[0].startswith("2024-01-01")
    assert dates[-1].startswith("2024-01-05")


