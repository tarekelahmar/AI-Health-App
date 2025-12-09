import requests
from datetime import datetime, timedelta
import json

class FitbitIntegration:
    """Fitbit API integration for wearable data"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.fitbit.com/1.2/user"
    
    def get_sleep_data(self, access_token: str, date: str = None) -> dict:
        """Fetch sleep data from Fitbit"""
        if date is None:
            date = datetime.today().strftime("%Y-%m-%d")
        
        url = f"{self.base_url}/{date}/sleep.json"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return {
                "sleep_duration": sum(s["duration"] for s in data.get("sleep", [])) / 3600000,  # ms to hours
                "sleep_quality": data.get("sleep", [{}]).get("efficiency", 0),
                "timestamp": date
            }
        return None
    
    def get_hrv_data(self, access_token: str, date: str = None) -> dict:
        """Fetch HRV from Fitbit"""
        if date is None:
            date = datetime.today().strftime("%Y-%m-%d")
        
        url = f"{self.base_url}/-1d/hrv.json"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            hrv_data = data.get("hrv", [{}])
            return {
                "hrv_msec": hrv_data.get("dailyRmssd", 0),
                "timestamp": date
            }
        return None

class OuraIntegration:
    """Oura Ring API integration"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.ouraring.com/v2/usercollection"
    
    def get_sleep_data(self, date: str = None) -> dict:
        """Fetch Oura sleep data"""
        if date is None:
            date = datetime.today().strftime("%Y-%m-%d")
        
        url = f"{self.base_url}/daily_sleep"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"date": date}
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                sleep = data["data"]
                return {
                    "sleep_duration": sleep.get("total_sleep_duration", 0) / 3600,
                    "sleep_quality": sleep.get("sleep_score", 0),
                    "timestamp": date
                }
        return None

class WearableDataSynchronizer:
    """Sync wearable data to health_app database"""
    
    def __init__(self, fitbit: FitbitIntegration, oura: OuraIntegration):
        self.fitbit = fitbit
        self.oura = oura
    
    def sync_user_data(self, user_id: int, wearable_tokens: dict, db_session) -> dict:
        """Sync all wearable data for a user"""
        from app.models.database import HealthDataPoint
        
        synced = {"fitbit": 0, "oura": 0, "errors": []}
        
        # Fitbit
        if "fitbit_token" in wearable_tokens:
            try:
                sleep_data = self.fitbit.get_sleep_data(wearable_tokens["fitbit_token"])
                if sleep_data:
                    dp = HealthDataPoint(
                        user_id=user_id,
                        data_type="sleep_duration",
                        value=sleep_data["sleep_duration"],
                        unit="hours",
                        source="fitbit",
                        timestamp=datetime.fromisoformat(sleep_data["timestamp"])
                    )
                    db_session.add(dp)
                    synced["fitbit"] += 1
            except Exception as e:
                synced["errors"].append(f"Fitbit sync failed: {str(e)}")
        
        # Oura
        if "oura_token" in wearable_tokens:
            try:
                sleep_data = self.oura.get_sleep_data()
                if sleep_data:
                    dp = HealthDataPoint(
                        user_id=user_id,
                        data_type="sleep_duration",
                        value=sleep_data["sleep_duration"],
                        unit="hours",
                        source="oura",
                        timestamp=datetime.fromisoformat(sleep_data["timestamp"])
                    )
                    db_session.add(dp)
                    synced["oura"] += 1
            except Exception as e:
                synced["errors"].append(f"Oura sync failed: {str(e)}")
        
        db_session.commit()
        return synced
