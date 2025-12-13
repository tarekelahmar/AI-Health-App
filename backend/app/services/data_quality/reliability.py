def score_reliability(source: str) -> float:
    return {
        "wearable": 0.7,
        "lab": 0.9,
        "questionnaire": 0.5,
        "manual": 0.4,
    }.get(source, 0.3)

