from sqlalchemy import Column, Integer, Float, String, DateTime, Index, Boolean
from sqlalchemy.sql import func
from app.core.database import Base


class Baseline(Base):
    """
    Personal baseline for a health metric.

    Phase 2.1: Extended with robust estimation metadata.
    - mean/std renamed conceptually to center/spread (columns unchanged for compatibility)
    - Added confidence intervals and estimation method
    """

    __tablename__ = "baselines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    metric_type = Column(String, index=True, nullable=False)

    # Core estimates (mean/std kept for backward compatibility, now represent center/spread)
    mean = Column(Float, nullable=False)  # Center estimate (robust or simple mean)
    std = Column(Float, nullable=False)  # Spread estimate (MAD or std)

    # Phase 2.1: Estimation metadata
    method = Column(String, nullable=True, default="simple_mean")  # median_mad, trimmed_mean, huber
    n_samples = Column(Integer, nullable=True)  # Number of data points used

    # Phase 2.1: Confidence intervals
    ci_80_low = Column(Float, nullable=True)
    ci_80_high = Column(Float, nullable=True)
    ci_95_low = Column(Float, nullable=True)
    ci_95_high = Column(Float, nullable=True)

    # Phase 2.1: Stability indicators
    is_stable = Column(Boolean, nullable=True, default=False)  # ≥14 days of data
    outliers_detected = Column(Integer, nullable=True, default=0)

    window_days = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_baseline_user_metric", "user_id", "metric_type", unique=True),
    )

    @property
    def center(self) -> float:
        """Alias for mean (robust center estimate)."""
        return self.mean

    @property
    def spread(self) -> float:
        """Alias for std (robust spread estimate)."""
        return self.std

    @property
    def confidence_interval_80(self) -> tuple:
        """80% confidence interval for center."""
        if self.ci_80_low is not None and self.ci_80_high is not None:
            return (self.ci_80_low, self.ci_80_high)
        return (self.mean, self.mean)

    @property
    def confidence_interval_95(self) -> tuple:
        """95% confidence interval for center."""
        if self.ci_95_low is not None and self.ci_95_high is not None:
            return (self.ci_95_low, self.ci_95_high)
        return (self.mean, self.mean)
