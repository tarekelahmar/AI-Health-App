"""
Pattern Manager - Phase 3.2

Lifecycle management for personal health patterns.

Detects new patterns from insight data, confirms/disproves them
with new observations, and manages the hypothesis→confirmed→deprecated
lifecycle.

Confidence update rule:
  - New observation confirming: confidence += (1 - confidence) * 0.15
  - New observation contradicting: confidence -= confidence * 0.2
  - Pattern confirmed at confidence >= 0.7 with >= 3 confirmations
  - Pattern disproven at confidence < 0.15
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.models.personal_pattern import PersonalPattern
from app.domain.repositories.personal_pattern_repository import (
    PersonalPatternRepository,
)

logger = logging.getLogger(__name__)

# Thresholds for pattern lifecycle
CONFIRM_CONFIDENCE = 0.7
CONFIRM_MIN_OBSERVATIONS = 3
DISPROVE_CONFIDENCE = 0.15

# Confidence update rates
CONFIRM_RATE = 0.15   # How much confidence increases per confirmation
CONTRADICT_RATE = 0.2  # How much confidence decreases per contradiction


@dataclass(frozen=True)
class PatternDetection:
    """Result of attempting to detect/update a pattern."""
    pattern: PersonalPattern
    action: str  # created | confirmed | contradicted | already_exists
    previous_confidence: Optional[float]
    new_confidence: float
    status_changed: bool


class PatternManager:
    """
    Manages the lifecycle of personal health patterns.

    Responsibilities:
    - Detect new patterns from insight evidence
    - Confirm existing patterns with new observations
    - Invalidate patterns that are contradicted
    - Promote hypothesis → confirmed when threshold met
    - Get active patterns for a user
    """

    def __init__(self, db: Session):
        self.db = db
        self.repo = PersonalPatternRepository(db)

    def detect_or_update_pattern(
        self,
        user_id: int,
        pattern_type: str,
        input_signals: List[str],
        output_signal: str,
        confirmed: bool = True,
        relationship: Optional[dict] = None,
        typical_lag_hours: Optional[float] = None,
        source_insight_ids: Optional[List[int]] = None,
    ) -> PatternDetection:
        """
        Detect a new pattern or update an existing one.

        If a matching pattern exists, record a new observation.
        Otherwise, create a new hypothesis.
        """
        existing = self.repo.find_matching(
            user_id=user_id,
            pattern_type=pattern_type,
            input_signals=input_signals,
            output_signal=output_signal,
        )

        if existing:
            return self._update_existing(existing, confirmed, relationship)
        else:
            pattern = self.repo.create(
                user_id=user_id,
                pattern_type=pattern_type,
                input_signals=input_signals,
                output_signal=output_signal,
                relationship=relationship,
                current_confidence=0.3,
                typical_lag_hours=typical_lag_hours,
                source_insight_ids=source_insight_ids,
            )
            return PatternDetection(
                pattern=pattern,
                action="created",
                previous_confidence=None,
                new_confidence=0.3,
                status_changed=False,
            )

    def _update_existing(
        self,
        pattern: PersonalPattern,
        confirmed: bool,
        relationship_update: Optional[dict],
    ) -> PatternDetection:
        """Update an existing pattern with a new observation."""
        prev_confidence = pattern.current_confidence
        prev_status = pattern.status

        if confirmed:
            new_confidence = prev_confidence + (1 - prev_confidence) * CONFIRM_RATE
            action = "confirmed"
        else:
            new_confidence = prev_confidence - prev_confidence * CONTRADICT_RATE
            action = "contradicted"

        new_confidence = max(0.0, min(1.0, new_confidence))

        self.repo.increment_observation(
            pattern_id=pattern.id,
            confirmed=confirmed,
            new_confidence=new_confidence,
            relationship_update=relationship_update,
        )

        # Check for status transitions
        status_changed = False
        if (
            pattern.status == "hypothesis"
            and new_confidence >= CONFIRM_CONFIDENCE
            and (pattern.times_confirmed + (1 if confirmed else 0)) >= CONFIRM_MIN_OBSERVATIONS
        ):
            self.repo.update_status(pattern.id, "confirmed")
            status_changed = True
            logger.info(
                f"Pattern {pattern.id} promoted to confirmed "
                f"(confidence={new_confidence:.2f}, confirmations={pattern.times_confirmed})"
            )
        elif new_confidence < DISPROVE_CONFIDENCE:
            self.repo.update_status(pattern.id, "disproven")
            status_changed = True
            logger.info(
                f"Pattern {pattern.id} disproven (confidence={new_confidence:.2f})"
            )

        # Refresh to get updated state
        pattern = self.repo.get_by_id(pattern.id)

        return PatternDetection(
            pattern=pattern,
            action=action,
            previous_confidence=prev_confidence,
            new_confidence=new_confidence,
            status_changed=status_changed,
        )

    def invalidate_pattern(
        self, pattern_id: int, reason: str = "manual"
    ) -> Optional[PersonalPattern]:
        """Explicitly invalidate a pattern."""
        pattern = self.repo.get_by_id(pattern_id)
        if not pattern:
            return None

        logger.info(f"Pattern {pattern_id} invalidated: {reason}")
        return self.repo.update_status(pattern_id, "deprecated")

    def get_active_patterns(
        self,
        user_id: int,
        pattern_type: Optional[str] = None,
        output_signal: Optional[str] = None,
    ) -> List[PersonalPattern]:
        """Get all active patterns (hypothesis or confirmed)."""
        return self.repo.list_active(
            user_id=user_id,
            pattern_type=pattern_type,
            output_signal=output_signal,
        )

    def get_confirmed_patterns(
        self, user_id: int
    ) -> List[PersonalPattern]:
        """Get only confirmed patterns."""
        return self.repo.list_confirmed(user_id=user_id)

    def get_patterns_for_signal(
        self, user_id: int, signal: str
    ) -> List[PersonalPattern]:
        """Get all patterns that predict a given output signal."""
        return self.repo.list_active(
            user_id=user_id,
            output_signal=signal,
        )
