from dataclasses import dataclass

from datetime import datetime


@dataclass
class Signal:
    user_id: int
    metric_key: str
    value: float
    unit: str
    timestamp: datetime
    source: str          # wearable | lab | questionnaire | manual
    reliability: float   # 0.0 – 1.0

