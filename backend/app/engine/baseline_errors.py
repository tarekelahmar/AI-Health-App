"""
Baseline computation error types and handling.

Risk #5: Baseline recomputation can silently fail, destabilizing the whole insights loop.
This module provides explicit error types and handling.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BaselineErrorType(str, Enum):
    """Types of baseline computation errors."""
    INSUFFICIENT_DATA = "insufficient_data"
    TABLE_MISSING = "table_missing"
    METRIC_NOT_FOUND = "metric_not_found"
    DATABASE_ERROR = "database_error"
    COMPUTATION_ERROR = "computation_error"


@dataclass
class BaselineError:
    """Structured baseline computation error."""
    error_type: BaselineErrorType
    message: str
    user_id: int
    metric_key: str
    recoverable: bool = True  # If True, can retry later


class BaselineUnavailable(Exception):
    """Raised when baseline cannot be computed or retrieved."""
    
    def __init__(self, error: BaselineError):
        self.error = error
        super().__init__(error.message)

