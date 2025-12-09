import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models

class DysfunctionDetector:
    """Detects health dysfunctions based on patterns in user data"""
    
    def __init__(self, ontology_path: str = "health_ontology.json"):
        with open(ontology_path) as f:
            self.ontology = json.load(f)
    
    def detect_dysfunctions(self, user_id: int, db: Session, days: int = 30) -> list:
        """
        Detect dysfunctions based on recent health data.
        
        Returns: [
            {
                'dysfunction_id': 'sleep_disorder',
                'severity': 'moderate',
                'evidence': {...},
                'score': 0.75
            }
        ]
        """
        
        # Get last N days of data
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        data_points = db.query(models.HealthDataPoint).filter(
            models.HealthDataPoint.user_id == user_id,
            models.HealthDataPoint.timestamp >= cutoff_date
        ).all()
        
        # Group by data type and calculate averages
        data_summary = {}
        for dp in data_points:
            if dp.data_type not in data_summary:
                data_summary[dp.data_type] = []
            data_summary[dp.data_type].append(dp.value)
        
        averages = {
            dtype: sum(vals) / len(vals) 
            for dtype, vals in data_summary.items()
        }
        
        # Check each dysfunction
        detected = []
        for dysfunction in self.ontology['dysfunctions']:
            severity, confidence = self._assess_dysfunction(
                dysfunction, 
                averages
            )
            
            if severity:  # If not None, dysfunction was detected
                detected.append({
                    'dysfunction_id': dysfunction['id'],
                    'name': dysfunction['name'],
                    'severity': severity,
                    'confidence': confidence,
                    'evidence': averages
                })
        
        # Sort by confidence
        detected.sort(key=lambda x: x['confidence'], reverse=True)
        return detected
    
    def _assess_dysfunction(self, dysfunction: dict, data_summary: dict) -> tuple:
        """
        Assess if dysfunction is present.
        Returns: (severity, confidence_score) or (None, 0)
        """
        thresholds = dysfunction['assessment_thresholds']
        detected_markers = []
        
        for severity_level in ['mild', 'moderate', 'severe']:
            if severity_level not in thresholds:
                continue
            
            threshold_dict = thresholds[severity_level]
            
            for data_type, expected_range in threshold_dict.items():
                if data_type in data_summary:
                    value = data_summary[data_type]
                    min_val, max_val = expected_range
                    
                    # If value is outside normal range, dysfunction detected
                    if not (min_val <= value <= max_val):
                        detected_markers.append({
                            'data_type': data_type,
                            'value': value,
                            'threshold': severity_level
                        })
        
        if not detected_markers:
            return None, 0
        
        # Determine severity from markers
        if any(m['threshold'] == 'severe' for m in detected_markers):
            severity = 'severe'
            confidence = 0.85
        elif any(m['threshold'] == 'moderate' for m in detected_markers):
            severity = 'moderate'
            confidence = 0.70
        else:
            severity = 'mild'
            confidence = 0.60
        
        return severity, confidence
