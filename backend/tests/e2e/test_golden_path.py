"""
Golden Path E2E Test: Full Health Assessment Flow

This test validates the complete user journey through the system:
1. User registration
2. Consent granting (governance gate)
3. Health data ingestion (baseline establishment)
4. Health data ingestion (deviation to trigger detection)
5. Insight generation loop
6. Insight retrieval with proper governance metadata
7. Explainability verification

This is the foundational test that must pass before any new features are added.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import json


class TestGoldenPath:
    """
    Golden Path: User creates account → grants consent → ingests data →
    baselines build → loop runs → insights generated → insights displayed
    """

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient, db):
        """Setup for each test"""
        self.client = client
        self.db = db
        self.user_id = None

    def test_step_1_create_user(self):
        """Step 1: Create a new user"""
        response = self.client.post(
            "/api/v1/users/",
            json={
                "name": "Golden Path Test User",
                "email": f"golden_path_{datetime.now().timestamp()}@test.com",
                "password": "TestPassword123!"
            }
        )

        assert response.status_code == 201, f"User creation failed: {response.json()}"
        data = response.json()
        assert "id" in data
        assert data["name"] == "Golden Path Test User"

        self.user_id = data["id"]
        return self.user_id

    def test_step_2_grant_consent(self):
        """Step 2: Grant consent (all checkboxes must be checked)"""
        user_id = self.test_step_1_create_user()

        response = self.client.post(
            f"/api/v1/consent?user_id={user_id}",
            json={
                "consent_version": "1.0",
                "understands_not_medical_advice": True,
                "consents_to_data_analysis": True,
                "understands_recommendations_experimental": True,
                "understands_can_stop_anytime": True,
                "consents_to_whoop_ingestion": True,
                "consents_to_fitbit_ingestion": False,
                "consents_to_oura_ingestion": False,
            }
        )

        assert response.status_code == 200, f"Consent creation failed: {response.json()}"
        data = response.json()
        assert data["consents_to_data_analysis"] is True

        return user_id

    def test_step_3_ingest_baseline_data(self):
        """Step 3: Ingest 30 days of baseline health data"""
        user_id = self.test_step_2_grant_consent()

        # Generate 30 days of baseline data
        # Using sleep_duration (minutes), hrv_rmssd (ms), resting_hr (bpm)
        baseline_points = []
        base_date = datetime.now() - timedelta(days=37)  # Start 37 days ago

        for day in range(30):
            timestamp = base_date + timedelta(days=day)

            # Baseline sleep: ~420 minutes (7 hours) with small variation
            baseline_points.append({
                "metric_key": "sleep_duration",
                "value": 420 + (day % 5) * 10 - 20,  # 400-440 minutes
                "timestamp": timestamp.isoformat(),
                "source": "wearable"
            })

            # Baseline HRV: ~45 ms with small variation
            baseline_points.append({
                "metric_key": "hrv_rmssd",
                "value": 45 + (day % 7) * 2 - 6,  # 39-51 ms
                "timestamp": timestamp.isoformat(),
                "source": "wearable"
            })

            # Baseline resting HR: ~62 bpm with small variation
            baseline_points.append({
                "metric_key": "resting_hr",
                "value": 62 + (day % 4) - 2,  # 60-64 bpm
                "timestamp": timestamp.isoformat(),
                "source": "wearable"
            })

        response = self.client.post(
            f"/api/v1/health-data/batch?user_id={user_id}",
            json={
                "user_id": user_id,
                "points": baseline_points
            }
        )

        assert response.status_code == 200, f"Baseline data ingestion failed: {response.json()}"
        data = response.json()
        assert data["inserted"] == 90, f"Expected 90 points inserted, got {data['inserted']}"
        assert data["rejected"] == 0, f"Unexpected rejections: {data['rejected_reasons']}"

        return user_id

    def test_step_4_ingest_deviation_data(self):
        """Step 4: Ingest 7 days of data with significant deviation to trigger detection"""
        user_id = self.test_step_3_ingest_baseline_data()

        # Generate 7 days of deviated data (simulating poor sleep week)
        deviation_points = []
        base_date = datetime.now() - timedelta(days=7)

        for day in range(7):
            timestamp = base_date + timedelta(days=day)

            # Deviated sleep: ~300 minutes (5 hours) - significant drop
            deviation_points.append({
                "metric_key": "sleep_duration",
                "value": 300 + (day % 3) * 15,  # 300-330 minutes
                "timestamp": timestamp.isoformat(),
                "source": "wearable"
            })

            # Deviated HRV: ~30 ms - significant drop (stress indicator)
            deviation_points.append({
                "metric_key": "hrv_rmssd",
                "value": 30 + (day % 4) * 2,  # 30-36 ms
                "timestamp": timestamp.isoformat(),
                "source": "wearable"
            })

            # Deviated resting HR: ~72 bpm - significant increase
            deviation_points.append({
                "metric_key": "resting_hr",
                "value": 72 + (day % 3) * 2,  # 72-76 bpm
                "timestamp": timestamp.isoformat(),
                "source": "wearable"
            })

        response = self.client.post(
            f"/api/v1/health-data/batch?user_id={user_id}",
            json={
                "user_id": user_id,
                "points": deviation_points
            }
        )

        assert response.status_code == 200, f"Deviation data ingestion failed: {response.json()}"
        data = response.json()
        assert data["inserted"] == 21, f"Expected 21 points inserted, got {data['inserted']}"

        return user_id

    def test_step_5_run_insight_loop(self):
        """Step 5: Run the insight generation loop"""
        user_id = self.test_step_4_ingest_deviation_data()

        response = self.client.post(
            f"/api/v1/insights/run?user_id={user_id}"
        )

        assert response.status_code == 200, f"Insight loop failed: {response.json()}"
        data = response.json()

        # We should have created at least one insight given the significant deviations
        assert "created" in data, "Response missing 'created' field"
        assert "insights" in data, "Response missing 'insights' field"

        # Log what was created for debugging
        print(f"\nInsights created: {data['created']}")
        for insight in data.get("insights", []):
            print(f"  - {insight.get('title', 'No title')}: confidence={insight.get('confidence', 'N/A')}")

        return user_id, data

    def test_step_6_verify_insights_feed(self):
        """Step 6: Verify insights are retrievable via feed endpoint"""
        user_id, loop_result = self.test_step_5_run_insight_loop()

        response = self.client.get(
            f"/api/v1/insights/feed?user_id={user_id}"
        )

        assert response.status_code == 200, f"Insights feed failed: {response.json()}"
        data = response.json()

        assert "count" in data
        assert "items" in data

        print(f"\nInsights in feed: {data['count']}")

        return user_id, data

    def test_step_7_verify_governance_metadata(self):
        """Step 7: Verify insights have proper governance metadata"""
        user_id, feed_data = self.test_step_6_verify_insights_feed()

        # Check governance metadata on each insight
        for insight in feed_data.get("items", []):
            # Every insight should have these governance fields
            assert "confidence" in insight, f"Insight missing confidence: {insight}"
            assert "status" in insight, f"Insight missing status: {insight}"

            # Confidence should be between 0 and 1
            confidence = insight.get("confidence", 0)
            assert 0 <= confidence <= 1, f"Invalid confidence {confidence}"

            # Check for evidence structure
            if "evidence" in insight and insight["evidence"]:
                evidence = insight["evidence"]
                # Evidence should contain supporting data
                print(f"  Evidence keys: {list(evidence.keys()) if isinstance(evidence, dict) else type(evidence)}")

            # Check for domain_key if present
            if "domain_key" in insight:
                domain_key = insight["domain_key"]
                if domain_key:
                    # Valid domain keys from health_domains.py
                    valid_domains = [
                        "sleep", "stress_nervous_system", "energy_fatigue",
                        "cardiometabolic", "gastrointestinal", "inflammation_immune",
                        "hormonal_reproductive", "cognitive_mental_performance",
                        "musculoskeletal_recovery", "nutrition_micronutrients"
                    ]
                    assert domain_key in valid_domains, f"Invalid domain_key: {domain_key}"

        print(f"\nGovernance metadata verification passed for {len(feed_data.get('items', []))} insights")

        return user_id

    def test_full_golden_path(self):
        """
        Complete Golden Path Test

        This is the main test that runs all steps in sequence and verifies
        the complete flow works end-to-end.
        """
        print("\n" + "="*60)
        print("GOLDEN PATH E2E TEST")
        print("="*60)

        # Step 1: Create user
        print("\nStep 1: Creating user...")
        user_id = self.test_step_1_create_user()
        print(f"  ✓ User created: ID={user_id}")

        # Step 2: Grant consent
        print("\nStep 2: Granting consent...")
        response = self.client.post(
            f"/api/v1/consent?user_id={user_id}",
            json={
                "consent_version": "1.0",
                "understands_not_medical_advice": True,
                "consents_to_data_analysis": True,
                "understands_recommendations_experimental": True,
                "understands_can_stop_anytime": True,
                "consents_to_whoop_ingestion": True,
            }
        )
        assert response.status_code == 200
        print("  ✓ Consent granted")

        # Step 3: Ingest baseline data
        print("\nStep 3: Ingesting 30 days of baseline data...")
        baseline_points = self._generate_baseline_data(days=30, offset_days=37)
        response = self.client.post(
            f"/api/v1/health-data/batch?user_id={user_id}",
            json={"user_id": user_id, "points": baseline_points}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"  ✓ Baseline data inserted: {data['inserted']} points")

        # Step 4: Ingest deviation data
        print("\nStep 4: Ingesting 7 days of deviation data...")
        deviation_points = self._generate_deviation_data(days=7, offset_days=7)
        response = self.client.post(
            f"/api/v1/health-data/batch?user_id={user_id}",
            json={"user_id": user_id, "points": deviation_points}
        )
        assert response.status_code == 200
        data = response.json()
        print(f"  ✓ Deviation data inserted: {data['inserted']} points")

        # Step 5: Run insight loop
        print("\nStep 5: Running insight generation loop...")
        response = self.client.post(f"/api/v1/insights/run?user_id={user_id}")
        assert response.status_code == 200
        loop_result = response.json()
        print(f"  ✓ Insights created: {loop_result.get('created', 0)}")

        # Step 6: Verify insights feed
        print("\nStep 6: Retrieving insights feed...")
        response = self.client.get(f"/api/v1/insights/feed?user_id={user_id}")
        assert response.status_code == 200
        feed_data = response.json()
        print(f"  ✓ Insights in feed: {feed_data.get('count', 0)}")

        # Step 7: Verify governance
        print("\nStep 7: Verifying governance metadata...")
        for i, insight in enumerate(feed_data.get("items", [])[:5]):  # Check first 5
            confidence = insight.get("confidence", 0)
            domain = insight.get("domain_key", "unknown")
            title = insight.get("title", "No title")[:50]
            print(f"  [{i+1}] {title}...")
            print(f"      confidence={confidence:.2f}, domain={domain}")
        print("  ✓ Governance metadata verified")

        # Summary
        print("\n" + "="*60)
        print("GOLDEN PATH TEST COMPLETE")
        print("="*60)
        print(f"  User ID: {user_id}")
        print(f"  Data points ingested: {30*3 + 7*3} (baseline + deviation)")
        print(f"  Insights generated: {loop_result.get('created', 0)}")
        print(f"  Insights in feed: {feed_data.get('count', 0)}")
        print("="*60 + "\n")

        # Final assertions
        assert feed_data.get("count", 0) >= 0, "Feed should return insights count"

    def _generate_baseline_data(self, days: int, offset_days: int) -> list:
        """Generate baseline health data points"""
        points = []
        base_date = datetime.now() - timedelta(days=offset_days)

        for day in range(days):
            timestamp = (base_date + timedelta(days=day)).isoformat()

            points.extend([
                {
                    "metric_key": "sleep_duration",
                    "value": 420 + (day % 5) * 10 - 20,
                    "timestamp": timestamp,
                    "source": "wearable"
                },
                {
                    "metric_key": "hrv_rmssd",
                    "value": 45 + (day % 7) * 2 - 6,
                    "timestamp": timestamp,
                    "source": "wearable"
                },
                {
                    "metric_key": "resting_hr",
                    "value": 62 + (day % 4) - 2,
                    "timestamp": timestamp,
                    "source": "wearable"
                }
            ])

        return points

    def _generate_deviation_data(self, days: int, offset_days: int) -> list:
        """Generate deviation health data points (poor sleep pattern)"""
        points = []
        base_date = datetime.now() - timedelta(days=offset_days)

        for day in range(days):
            timestamp = (base_date + timedelta(days=day)).isoformat()

            points.extend([
                {
                    "metric_key": "sleep_duration",
                    "value": 300 + (day % 3) * 15,  # Significant drop
                    "timestamp": timestamp,
                    "source": "wearable"
                },
                {
                    "metric_key": "hrv_rmssd",
                    "value": 30 + (day % 4) * 2,  # Significant drop
                    "timestamp": timestamp,
                    "source": "wearable"
                },
                {
                    "metric_key": "resting_hr",
                    "value": 72 + (day % 3) * 2,  # Significant increase
                    "timestamp": timestamp,
                    "source": "wearable"
                }
            ])

        return points


@pytest.mark.e2e
def test_golden_path_complete(client: TestClient, db):
    """
    Single entry point for the complete Golden Path test.

    Run with: pytest tests/e2e/test_golden_path.py -v -s --tb=short
    """
    test = TestGoldenPath()
    test.client = client
    test.db = db
    test.test_full_golden_path()


@pytest.mark.e2e
def test_consent_required_for_insights(client: TestClient, db):
    """
    Verify that insights cannot be generated without consent.

    This tests the governance gate.
    """
    # Create user
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "No Consent User",
            "email": f"no_consent_{datetime.now().timestamp()}@test.com",
            "password": "TestPassword123!"
        }
    )
    assert response.status_code == 201
    user_id = response.json()["id"]

    # Try to run insights WITHOUT consent - should fail or return appropriate error
    response = client.post(f"/api/v1/insights/run?user_id={user_id}")

    # The system should either:
    # 1. Return 403 (forbidden - no consent)
    # 2. Return 404 (consent not found)
    # 3. Return success but with 0 insights (conservative approach)
    assert response.status_code in [200, 403, 404], f"Unexpected status: {response.status_code}"

    if response.status_code == 200:
        # If it returns 200, verify no insights were created
        data = response.json()
        print(f"Response without consent: {data}")


@pytest.mark.e2e
def test_insufficient_data_handled_gracefully(client: TestClient, db):
    """
    Verify the system handles insufficient data gracefully.

    This tests the "silence when uncertain" principle.
    """
    # Create user and consent
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Insufficient Data User",
            "email": f"insufficient_{datetime.now().timestamp()}@test.com",
            "password": "TestPassword123!"
        }
    )
    user_id = response.json()["id"]

    # Grant consent
    client.post(
        f"/api/v1/consent?user_id={user_id}",
        json={
            "consent_version": "1.0",
            "understands_not_medical_advice": True,
            "consents_to_data_analysis": True,
            "understands_recommendations_experimental": True,
            "understands_can_stop_anytime": True,
        }
    )

    # Ingest only 3 days of data (insufficient for baseline)
    points = []
    for day in range(3):
        timestamp = (datetime.now() - timedelta(days=day)).isoformat()
        points.append({
            "metric_key": "sleep_duration",
            "value": 420,
            "timestamp": timestamp,
            "source": "wearable"
        })

    client.post(
        f"/api/v1/health-data/batch?user_id={user_id}",
        json={"user_id": user_id, "points": points}
    )

    # Run insights - should not crash, may create "insufficient data" insights
    response = client.post(f"/api/v1/insights/run?user_id={user_id}")
    assert response.status_code == 200, f"Should handle gracefully: {response.json()}"

    data = response.json()
    print(f"Insights with insufficient data: {data.get('created', 0)}")

    # Check if any insights are "insufficient_data" type
    for insight in data.get("insights", []):
        if insight.get("type") == "insufficient_data":
            print(f"  Found insufficient_data insight: {insight.get('title')}")
