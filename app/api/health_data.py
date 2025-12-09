"""Health data API endpoints"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import pandas as pd

from app.core.database import get_db
from app import models
from app import schemas

router = APIRouter(prefix="/health-data", tags=["health-data"])


@router.post("/", response_model=schemas.HealthDataPointResponse)
def add_health_data(
    user_id: int,
    data: schemas.HealthDataPointCreate,
    db: Session = Depends(get_db)
):
    """Add a single health data point (lab, symptom, or wearable)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_data = models.HealthDataPoint(
        user_id=user_id,
        data_type=data.data_type,
        value=data.value,
        unit=data.unit,
        source=data.source
    )
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data


@router.post("/batch/")
def upload_health_data_csv(user_id: int, file_path: str, db: Session = Depends(get_db)):
    """
    Upload multiple health data points from a CSV file.
    CSV format:
    data_type,value,unit,source,timestamp
    sleep_duration,7.5,hours,wearable,2025-01-01
    fasting_glucose,105,mg/dL,lab,2025-01-01
    """
    try:
        df = pd.read_csv(file_path)
        
        for _, row in df.iterrows():
            db_data = models.HealthDataPoint(
                user_id=user_id,
                data_type=row['data_type'],
                value=float(row['value']),
                unit=row['unit'],
                source=row['source'],
                timestamp=pd.to_datetime(row['timestamp'])
            )
            db.add(db_data)
        
        db.commit()
        return {"status": "success", "rows_uploaded": len(df)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Upload failed: {str(e)}")


@router.get("/{user_id}")
def get_user_health_data(user_id: int, db: Session = Depends(get_db)):
    """Retrieve all health data for a user"""
    data = db.query(models.HealthDataPoint).filter(
        models.HealthDataPoint.user_id == user_id
    ).all()
    return data

