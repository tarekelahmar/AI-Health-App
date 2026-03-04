"""Tests for the check-in bridge module."""

import pytest
from datetime import date, datetime

from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.health_data_point import HealthDataPoint
from app.engine.checkin_bridge import (
    sync_checkin_to_datapoints,
    _convert_v1_to_1_5,
    _convert_v2_to_1_5,
)


class TestV1ScaleConversion:
    """Test the V1 0-10 to 1-5 scale conversion."""

    def test_zero_maps_to_one(self):
        assert _convert_v1_to_1_5(0) == 1.0

    def test_five_maps_to_three(self):
        assert _convert_v1_to_1_5(5) == 3.0

    def test_ten_maps_to_five(self):
        assert _convert_v1_to_1_5(10) == 5.0

    def test_intermediate_values(self):
        # 2 -> 1 + (2/10)*4 = 1.8
        assert abs(_convert_v1_to_1_5(2) - 1.8) < 0.001
        # 7 -> 1 + (7/10)*4 = 3.8
        assert abs(_convert_v1_to_1_5(7) - 3.8) < 0.001


class TestV2ScaleConversion:
    """Test the V2 1.0-10.0 to 1-5 scale conversion."""

    def test_one_maps_to_one(self):
        assert _convert_v2_to_1_5(1.0) == 1.0

    def test_five_point_five_maps_to_three(self):
        assert abs(_convert_v2_to_1_5(5.5) - 3.0) < 0.001

    def test_ten_maps_to_five(self):
        assert _convert_v2_to_1_5(10.0) == 5.0

    def test_intermediate_values(self):
        # 3.25 -> 1 + ((3.25-1)/9)*4 = 1 + (2.25/9)*4 = 1 + 1.0 = 2.0
        assert abs(_convert_v2_to_1_5(3.25) - 2.0) < 0.001
        # 7.75 -> 1 + ((7.75-1)/9)*4 = 1 + (6.75/9)*4 = 1 + 3.0 = 4.0
        assert abs(_convert_v2_to_1_5(7.75) - 4.0) < 0.001


class TestSyncCheckinToDatapoints:
    """Test syncing check-in data to HealthDataPoint rows."""

    def test_sync_v1_creates_datapoints(self, db):
        """V1 entry (no overall_wellbeing) uses V1 metric map."""
        checkin = DailyCheckIn(
            user_id=1,
            checkin_date=date(2024, 6, 15),
            energy=7,
            mood=8,
            stress=3,
            focus=6,
            sleep_quality=9,
        )
        db.add(checkin)
        db.commit()

        count = sync_checkin_to_datapoints(db, checkin)

        assert count == 5  # All 5 V1 fields synced

        # Verify data points exist
        dps = db.query(HealthDataPoint).filter(
            HealthDataPoint.user_id == 1,
            HealthDataPoint.source == "checkin",
        ).all()
        assert len(dps) == 5

        # Verify V1 conversion
        energy_dp = next(dp for dp in dps if dp.metric_type == "energy")
        assert abs(energy_dp.value - 3.8) < 0.001  # 7 -> 3.8

        mood_dp = next(dp for dp in dps if dp.metric_type == "mood")
        assert abs(mood_dp.value - 4.2) < 0.001  # 8 -> 4.2

    def test_sync_v2_creates_datapoints(self, db):
        """V2 entry (has overall_wellbeing) uses V2 metric map."""
        checkin = DailyCheckIn(
            user_id=1,
            checkin_date=date(2024, 6, 15),
            overall_wellbeing=7.5,
            energy=8.0,
            mood=6.5,
            focus=7.0,
            connection=5.0,
        )
        db.add(checkin)
        db.commit()

        count = sync_checkin_to_datapoints(db, checkin)

        assert count == 5  # All 5 V2 fields synced

        dps = db.query(HealthDataPoint).filter(
            HealthDataPoint.user_id == 1,
            HealthDataPoint.source == "checkin",
        ).all()
        assert len(dps) == 5

        # Verify V2 conversion: 7.5 -> 1 + ((7.5-1)/9)*4 = 1 + (6.5/9)*4 = 3.889
        wellbeing_dp = next(dp for dp in dps if dp.metric_type == "overall_wellbeing")
        assert abs(wellbeing_dp.value - 3.889) < 0.01

        # 5.0 -> 1 + ((5.0-1)/9)*4 = 1 + (4/9)*4 = 2.778
        connection_dp = next(dp for dp in dps if dp.metric_type == "connection")
        assert abs(connection_dp.value - 2.778) < 0.01

    def test_sync_skips_null_fields(self, db):
        checkin = DailyCheckIn(
            user_id=1,
            checkin_date=date(2024, 6, 15),
            energy=5,
            mood=None,
            stress=None,
            focus=None,
            sleep_quality=None,
        )
        db.add(checkin)
        db.commit()

        count = sync_checkin_to_datapoints(db, checkin)
        assert count == 1  # Only energy synced

    def test_sync_is_idempotent(self, db):
        checkin = DailyCheckIn(
            user_id=1,
            checkin_date=date(2024, 6, 15),
            energy=7,
            mood=8,
        )
        db.add(checkin)
        db.commit()

        # Sync twice
        sync_checkin_to_datapoints(db, checkin)
        sync_checkin_to_datapoints(db, checkin)

        dps = db.query(HealthDataPoint).filter(
            HealthDataPoint.user_id == 1,
            HealthDataPoint.source == "checkin",
        ).all()
        assert len(dps) == 2  # Still only 2, not duplicated

    def test_sync_updates_existing_value(self, db):
        checkin = DailyCheckIn(
            user_id=1,
            checkin_date=date(2024, 6, 15),
            energy=5,
        )
        db.add(checkin)
        db.commit()

        sync_checkin_to_datapoints(db, checkin)

        # Update energy
        checkin.energy = 8
        db.commit()

        sync_checkin_to_datapoints(db, checkin)

        dps = db.query(HealthDataPoint).filter(
            HealthDataPoint.user_id == 1,
            HealthDataPoint.metric_type == "energy",
            HealthDataPoint.source == "checkin",
        ).all()
        assert len(dps) == 1
        assert abs(dps[0].value - 4.2) < 0.001  # 8 -> 4.2

    def test_sync_handles_empty_checkin(self, db):
        count = sync_checkin_to_datapoints(db, None)
        assert count == 0
