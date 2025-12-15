from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.providers.whoop.whoop_adapter import WhoopAdapter
from app.providers.base import NormalizedPoint
from app.domain.metric_registry import get_metric_spec, METRICS
from app.domain.repositories.health_data_repository import HealthDataRepository
from app.domain.models.health_data_point import HealthDataPoint
from app.domain.models.data_provenance import DataProvenance
from app.engine.quality.data_quality_service import DataQualityService
from app.core.invariants import validate_provider_ingestion_invariants, InvariantViolation

logger = logging.getLogger(__name__)


class ProviderSyncService:
    def __init__(self, db: Session):
        self.db = db
        self.health_repo = HealthDataRepository(db)

    def sync_whoop(self, user_id: int, since: Optional[datetime] = None) -> dict:
        """
        Sync WHOOP data for a user.
        
        STEP R: Includes provenance tracking and quality scoring.
        Safety: Never partially ingest data. All points are validated before any insertion.
        If any critical error occurs, no data is inserted.
        """
        # Generate unique ingestion run ID
        ingestion_run_id = f"whoop_{user_id}_{datetime.utcnow().isoformat()}_{uuid.uuid4().hex[:8]}"
        ingestion_time = datetime.utcnow()
        
        try:
            adapter = WhoopAdapter(self.db)
            pts: List[NormalizedPoint] = adapter.fetch_and_normalize(user_id=user_id, since=since)
        except RuntimeError as e:
            # Safety: If credentials are missing or adapter fails, return early with no partial data
            logger.error(f"WHOOP sync failed for user_id={user_id}: {e}")
            return {"provider": "whoop", "inserted": 0, "rejected": 0, "errors": [{"reason": "adapter_error", "error": str(e)}]}

        # STEP R: Compute quality score for batch
        quality_service = DataQualityService()
        metric_specs = {k: v for k, v in METRICS.items()}
        quality_score = quality_service.compute_quality_score(
            points=pts,
            metric_specs=metric_specs,
            ingestion_time=ingestion_time,
        )

        inserted = 0
        rejected = 0
        errors = []
        existing_timestamps: Dict[str, List[datetime]] = {}  # Track duplicates per metric

        # Safety: Validate all points before any insertion (never partially ingest)
        to_create = []
        provenances = []  # Track provenance records
        
        for p in pts:
            # Track timestamps for duplicate detection
            if p.metric_type not in existing_timestamps:
                existing_timestamps[p.metric_type] = []
            
            try:
                spec = get_metric_spec(p.metric_type)
                
                # X1: Validate invariants (metric registry, unit, range)
                try:
                    validate_provider_ingestion_invariants(
                        user_id=user_id,
                        metric_type=p.metric_type,
                        value=p.value,
                        unit=p.unit,
                        source=p.source,
                    )
                except InvariantViolation as e:
                    # Hard-fail: reject point and log error
                    rejected += 1
                    errors.append({"metric_type": p.metric_type, "reason": "invariant_violation", "error": str(e)})
                    continue
                
                # STEP R: Quality gates (hard stops)
                should_reject, reject_reason = quality_service.should_reject_point(
                    point=p,
                    metric_spec=spec,
                    existing_timestamps=existing_timestamps[p.metric_type],
                )
                
                if should_reject:
                    rejected += 1
                    errors.append({"metric_type": p.metric_type, "reason": reject_reason})
                    continue
                
                # Add timestamp to tracking
                existing_timestamps[p.metric_type].append(p.timestamp)
                
                # STEP R: Create provenance record
                provenance = DataProvenance(
                    user_id=user_id,
                    source_type="wearable",
                    source_name="whoop",
                    source_record_id=p.metadata.get("whoop_sleep_id") or p.metadata.get("whoop_recovery_id"),
                    ingestion_run_id=ingestion_run_id,
                    received_at=ingestion_time,
                    is_validated=True,
                    validation_errors=None,
                    quality_score=quality_score.to_dict(),
                )
                self.db.add(provenance)
                self.db.flush()  # Get provenance.id
                provenances.append(provenance)
                
                # Determine if point should be flagged (quality < 0.6)
                is_flagged = quality_score.overall < 0.6
                
                to_create.append(
                    {
                        "user_id": user_id,
                        "data_type": p.metric_type,
                        "value": float(p.value),
                        "unit": p.unit,
                        "timestamp": p.timestamp,
                        "source": p.source,
                        "data_provenance_id": provenance.id,
                        "quality_score": quality_score.to_dict(),
                        "is_flagged": is_flagged,
                    }
                )
            except Exception as e:
                rejected += 1
                errors.append({"metric_type": p.metric_type, "reason": "exception", "error": str(e)})

        # Safety: Only commit if we have valid points to insert (never partially ingest)
        if to_create:
            try:
                for row in to_create:
                    # Use HealthDataPoint model directly (metric_type maps to data_type column)
                    point = HealthDataPoint(
                        user_id=row["user_id"],
                        metric_type=row["data_type"],
                        value=row["value"],
                        unit=row["unit"],
                        timestamp=row["timestamp"],
                        source=row["source"],
                        data_provenance_id=row["data_provenance_id"],
                        quality_score=row["quality_score"],
                        is_flagged=row["is_flagged"],
                    )
                    self.db.add(point)
                    inserted += 1
                self.db.commit()
                logger.info(f"WHOOP sync for user_id={user_id}: inserted={inserted}, rejected={rejected}, quality={quality_score.overall}")
            except Exception as e:
                # Safety: Rollback on any error to prevent partial ingestion
                self.db.rollback()
                logger.error(f"WHOOP sync failed for user_id={user_id} during insertion: {e}")
                return {"provider": "whoop", "inserted": 0, "rejected": len(pts), "errors": [{"reason": "insertion_error", "error": str(e)}]}

        return {
            "provider": "whoop",
            "inserted": inserted,
            "rejected": rejected,
            "errors": errors,
            "ingestion_run_id": ingestion_run_id,
            "quality_score": quality_score.to_dict(),
        }

