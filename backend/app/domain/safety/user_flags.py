from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class UserSafetyFlags:
    """
    MVP: store a few user-level safety flags.
    In production, this should come from onboarding / EHR / clinician.
    """
    pregnant: bool = False
    trying_to_conceive: bool = False
    kidney_disease: bool = False
    bleeding_disorder: bool = False

    # Medication flags (VERY simplified)
    warfarin: bool = False
    anticoagulants: bool = False
    levothyroxine: bool = False
    tetracycline_antibiotics: bool = False
    immunosuppressants: bool = False

    def to_flag_list(self) -> List[str]:
        flags: List[str] = []
        for field, value in self.__dict__.items():
            if value:
                flags.append(field)
        return flags

    @staticmethod
    def from_dict(d: Optional[dict]) -> "UserSafetyFlags":
        if not d:
            return UserSafetyFlags()
        return UserSafetyFlags(**{k: bool(v) for k, v in d.items() if k in UserSafetyFlags().__dict__})

