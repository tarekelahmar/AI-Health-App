import json
from datetime import datetime, timedelta

class ProtocolGenerator:
    """Converts health assessments into personalized weekly protocols"""
    
    def __init__(self, ontology_path: str = "health_ontology.json"):
        with open(ontology_path) as f:
            self.ontology = json.load(f)
    
    def generate_protocol(self, user_id: int, dysfunctions: list) -> dict:
        """
        Generate a personalized weekly protocol.
        
        Args:
            dysfunctions: List of detected dysfunctions with severity
        
        Returns:
            {
                'week': 1,
                'start_date': '2025-01-15',
                'interventions': [
                    {
                        'intervention': 'Sleep Hygiene',
                        'daily_actions': [],
                        'rationale': '',
                        'priority': 1,
                        'adherence_target': 0.8
                    }
                ]
            }
        """
        
        protocol = {
            'user_id': user_id,
            'week': 1,
            'start_date': datetime.utcnow().isoformat(),
            'end_date': (datetime.utcnow() + timedelta(days=7)).isoformat(),
            'interventions': []
        }
        
        # Priority interventions by dysfunction severity
        priority = 1
        for dysfunction in sorted(dysfunctions, key=lambda x: x['confidence'], reverse=True):
            dysfunction_spec = next(
                (d for d in self.ontology['dysfunctions'] 
                 if d['id'] == dysfunction['dysfunction_id']),
                None
            )
            
            if not dysfunction_spec:
                continue
            
            for intervention in dysfunction_spec['interventions'][:2]:  # Top 2 per dysfunction
                protocol['interventions'].append({
                    'dysfunction': dysfunction['dysfunction_id'],
                    'intervention_name': intervention['name'],
                    'type': intervention.get('type', 'unknown'),
                    'priority': priority,
                    'daily_actions': self._create_daily_actions(intervention),
                    'rationale': f"Addresses {dysfunction['dysfunction_id']} detected at {dysfunction['severity']} severity",
                    'adherence_target': 0.8 if priority == 1 else 0.6,
                    'metrics_to_track': self._get_tracking_metrics(dysfunction['dysfunction_id'])
                })
                priority += 1
        
        return protocol
    
    def _create_daily_actions(self, intervention: dict) -> list:
        """Convert intervention into daily actionable steps"""
        
        actions = {
            'Sleep Hygiene Protocol': [
                '✓ Ensure bedroom is dark and cool (65-68°F)',
                '✓ No screens 1 hour before bed',
                '✓ Aim for consistent sleep/wake times',
                '✓ Log sleep quality on scale 1-10'
            ],
            'Magnesium Glycinate': [
                f'✓ Take {intervention.get("dose", "200-400mg")} {intervention.get("timing", "evening")}',
                '✓ Take with food if stomach sensitive',
                '✓ Avoid within 2 hours of other supplements'
            ],
            'Chromium Supplementation': [
                f'✓ Take {intervention.get("dose", "200mcg")} daily with meals',
                '✓ Preferably with protein + carbs',
                '✓ Track fasting glucose daily'
            ]
        }
        
        return actions.get(intervention['name'], ['✓ Follow protocol as outlined'])
    
    def _get_tracking_metrics(self, dysfunction_id: str) -> list:
        """Metrics to track for this dysfunction"""
        
        metrics = {
            'sleep_disorder': ['sleep_duration', 'sleep_quality_score', 'wake_count'],
            'blood_sugar_dysregulation': ['fasting_glucose', 'postprandial_glucose'],
            'low_hrv': ['hrv_msec', 'resting_heart_rate']
        }
        
        return metrics.get(dysfunction_id, [])
