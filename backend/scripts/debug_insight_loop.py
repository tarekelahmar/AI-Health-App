#!/usr/bin/env python3
"""
Debug script to diagnose why insights aren't being generated.
Run from backend directory: python -m scripts.debug_insight_loop --user-id 1
"""
import argparse
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.domain.models.baseline import Baseline
from app.domain.models.health_data_point import HealthDataPoint
from app.domain.metrics.registry import METRIC_REGISTRY, get_metric_spec
from app.domain.metric_policies import METRIC_POLICIES, get_metric_policy
from app.engine.signal_builder import fetch_recent_values
from app.engine.detectors.change_detector import detect_change


def debug_insight_loop(user_id: int):
    db = SessionLocal()

    print(f"\n{'='*60}")
    print(f"DEBUG: Insight Loop Diagnosis for user_id={user_id}")
    print(f"{'='*60}\n")

    change_window_days = 7

    for metric_key in METRIC_REGISTRY.keys():
        print(f"\n--- {metric_key} ---")

        # 1. Check metric spec
        try:
            spec = get_metric_spec(metric_key)
            print(f"  [OK] Metric spec found: valid_range={spec.valid_range}")
        except KeyError as e:
            print(f"  [SKIP] No metric spec: {e}")
            continue

        # 2. Check metric policy
        try:
            policy = get_metric_policy(metric_key)
            print(f"  [OK] Policy found: allowed_insights={policy.allowed_insights}")
            if policy.change:
                print(f"       change z_threshold={policy.change.z_threshold}")
        except ValueError as e:
            print(f"  [SKIP] No metric policy: {e}")
            continue

        # 3. Check baseline
        baseline = db.query(Baseline).filter(
            Baseline.user_id == user_id,
            Baseline.metric_type == metric_key
        ).one_or_none()

        if baseline is None:
            print(f"  [SKIP] No baseline found!")
            continue
        print(f"  [OK] Baseline: mean={baseline.mean:.2f}, std={baseline.std:.2f}")

        # 4. Check raw values
        raw_values = fetch_recent_values(
            db=db, user_id=user_id, metric_key=metric_key, window_days=change_window_days
        )
        print(f"  [OK] Raw values ({len(raw_values)}): {[f'{v:.1f}' for v in raw_values[:5]]}{'...' if len(raw_values) > 5 else ''}")

        # 5. Filter by valid range
        validated_values = [
            v for v in raw_values
            if spec.valid_range[0] <= v <= spec.valid_range[1]
        ]
        print(f"  [OK] After valid_range filter: {len(validated_values)} values")

        if len(validated_values) < 5:
            print(f"  [SKIP] Insufficient data: {len(validated_values)} < 5")
            continue

        # 6. Check if change detection is allowed
        if "change" not in policy.allowed_insights or not policy.change:
            print(f"  [SKIP] Change detection not allowed for this metric")
            continue

        # 7. Run change detection
        recent_mean = sum(validated_values) / len(validated_values)
        z_score = (recent_mean - baseline.mean) / baseline.std if baseline.std > 0 else 0

        print(f"  [CALC] Recent mean: {recent_mean:.2f}")
        print(f"  [CALC] Z-score: {z_score:.2f} (threshold: {policy.change.z_threshold})")
        print(f"  [CALC] |Z| = {abs(z_score):.2f} {'>' if abs(z_score) > policy.change.z_threshold else '<='} {policy.change.z_threshold}")

        change = detect_change(
            metric_key=metric_key,
            values=validated_values,
            baseline_mean=baseline.mean,
            baseline_std=baseline.std,
            window_days=change_window_days,
            z_threshold=policy.change.z_threshold,
        )

        if change:
            print(f"  [DETECTED] Change: direction={change.direction}, strength={change.strength}")
        else:
            print(f"  [NO CHANGE] Detection returned None")

    print(f"\n{'='*60}")
    print("DEBUG COMPLETE")
    print(f"{'='*60}\n")

    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug insight loop")
    parser.add_argument("--user-id", type=int, required=True, help="User ID to debug")
    args = parser.parse_args()

    debug_insight_loop(args.user_id)
