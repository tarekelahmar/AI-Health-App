RED_FLAGS = {
    "sleep_duration": {
        "critical_low": 240,  # <4h sleep
        "message": "Very low sleep detected for multiple days. Consider seeking medical advice."
    },
    "resting_hr": {
        "critical_high": 100,
        "message": "Persistently elevated resting heart rate detected."
    },
    "hrv_rmssd": {
        "critical_low": 20,
        "message": "Very low HRV detected over multiple days."
    },
}

