"""Health data repository - data access layer for HealthDataPoint model"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from app.domain.models.health_data_point import HealthDataPoint


class HealthDataRepository:
    """Repository for HealthDataPoint domain model (legacy compatibility)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        user_id: int,
        data_type: str,
        value: float,
        unit: str,
        source: str,
        timestamp: Optional[datetime] = None
    ) -> HealthDataPoint:
        """Create a new health data point"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        db_point = HealthDataPoint(
            user_id=user_id,
            data_type=data_type,
            value=value,
            unit=unit,
            source=source,
            timestamp=timestamp
        )
        self.db.add(db_point)
        self.db.commit()
        self.db.refresh(db_point)
        return db_point
    
    def bulk_create(self, user_id: int, data_points: List[Dict[str, Any]]) -> List[HealthDataPoint]:
        """Bulk insert health data points (for wearable sync, lab imports, etc.)"""
        db_points = []
        for point_data in data_points:
            db_point = HealthDataPoint(
                user_id=user_id,
                data_type=point_data.get("data_type"),
                value=point_data.get("value"),
                unit=point_data.get("unit"),
                source=point_data.get("source", "manual"),
                timestamp=point_data.get("timestamp", datetime.utcnow())
            )
            db_points.append(db_point)
            self.db.add(db_point)
        
        self.db.commit()
        for point in db_points:
            self.db.refresh(point)
        return db_points
    
    def get_by_id(self, point_id: int) -> Optional[HealthDataPoint]:
        """Get health data point by ID"""
        return self.db.query(HealthDataPoint).filter(HealthDataPoint.id == point_id).first()
    
    def get_by_user(
        self,
        user_id: int,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[HealthDataPoint]:
        """Get health data points for a user with optional filters"""
        query = self.db.query(HealthDataPoint).filter(HealthDataPoint.user_id == user_id)
        
        if data_type:
            query = query.filter(HealthDataPoint.data_type == data_type)
        if source:
            query = query.filter(HealthDataPoint.source == source)
        
        return (
            query.order_by(desc(HealthDataPoint.timestamp))
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_latest(
        self,
        user_id: int,
        data_type: Optional[str] = None
    ) -> Optional[HealthDataPoint]:
        """Get latest health data point"""
        query = self.db.query(HealthDataPoint).filter(HealthDataPoint.user_id == user_id)
        
        if data_type:
            query = query.filter(HealthDataPoint.data_type == data_type)
        
        return query.order_by(desc(HealthDataPoint.timestamp)).first()
    
    def get_by_time_range(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
        data_type: Optional[str] = None,
        source: Optional[str] = None
    ) -> List[HealthDataPoint]:
        """Get health data points within time range"""
        query = self.db.query(HealthDataPoint).filter(
            and_(
                HealthDataPoint.user_id == user_id,
                HealthDataPoint.timestamp >= start_date,
                HealthDataPoint.timestamp <= end_date
            )
        )
        
        if data_type:
            query = query.filter(HealthDataPoint.data_type == data_type)
        if source:
            query = query.filter(HealthDataPoint.source == source)
        
        return query.order_by(desc(HealthDataPoint.timestamp)).all()
    
    def list_for_user_in_range(
        self,
        user_id: int,
        data_type: str,
        start: datetime,
        end: datetime,
    ) -> List[HealthDataPoint]:
        """Alias for get_by_time_range to match analytics layer interface"""
        return self.get_by_time_range(
            user_id=user_id,
            start_date=start,
            end_date=end,
            data_type=data_type
        )
    
    def get_recent(self, user_id: int, days: int = 30, data_type: Optional[str] = None) -> List[HealthDataPoint]:
        """Get recent health data points (within last N days)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return self.get_by_time_range(user_id, cutoff_date, datetime.utcnow(), data_type)
    
    def get_average(
        self,
        user_id: int,
        data_type: str,
        days: int = 30
    ) -> Optional[float]:
        """Calculate average value for a data type over time period"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        result = (
            self.db.query(func.avg(HealthDataPoint.value))
            .filter(
                and_(
                    HealthDataPoint.user_id == user_id,
                    HealthDataPoint.data_type == data_type,
                    HealthDataPoint.timestamp >= cutoff_date
                )
            )
            .scalar()
        )
        return float(result) if result else None
    
    def get_trend(
        self,
        user_id: int,
        data_type: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Calculate trend (improving, declining, stable) for a data type"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        points = self.get_by_time_range(user_id, cutoff_date, datetime.utcnow(), data_type)
        
        if len(points) < 2:
            return {"trend": "insufficient_data", "slope": 0.0, "confidence": 0.0}
        
        # Simple linear trend: compare first half vs second half
        mid_point = len(points) // 2
        first_half_avg = sum(p.value for p in points[:mid_point]) / mid_point
        second_half_avg = sum(p.value for p in points[mid_point:]) / (len(points) - mid_point)
        
        slope = second_half_avg - first_half_avg
        change_percent = (slope / first_half_avg * 100) if first_half_avg > 0 else 0
        
        if abs(change_percent) < 5:
            trend = "stable"
        elif change_percent > 0:
            trend = "improving"
        else:
            trend = "declining"
        
        return {
            "trend": trend,
            "slope": slope,
            "change_percent": change_percent,
            "confidence": min(len(points) / 30, 1.0)  # More data = higher confidence
        }
    
    def delete(self, point_id: int) -> bool:
        """Delete health data point by ID"""
        point = self.get_by_id(point_id)
        if point:
            self.db.delete(point)
            self.db.commit()
            return True
        return False

