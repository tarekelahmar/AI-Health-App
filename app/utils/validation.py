"""Health data validation utilities"""
import json
from app.core.config import HEALTH_ONTOLOGY_PATH


def validate_health_data(data_type: str, value: float, unit: str, ontology_path: str = None) -> dict:
    """Validate health data against ontology"""
    if ontology_path is None:
        ontology_path = HEALTH_ONTOLOGY_PATH
    """Basic validation against health ontology"""
    with open(ontology_path) as f:
        ontology = json.load(f)
    
    # Check if data type exists in ontology
    valid_types = ontology['data_types']
    if data_type not in valid_types:
        return {"valid": False, "error": f"Unknown data type: {data_type}"}
    
    # Check if value is within reasonable range
    data_spec = valid_types[data_type]
    min_val, max_val = data_spec['range']
    
    if not (min_val <= value <= max_val):
        return {
            "valid": False,
            "error": f"{data_type} value {value} outside acceptable range [{min_val}, {max_val}]"
        }
    
    return {"valid": True}

