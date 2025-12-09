import json
import re
from datetime import datetime

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_health_data(data_type: str, value: float, unit: str) -> dict:
    """Validate health data against ontology"""
    try:
        with open('app/core/health_ontology.json') as f:
            ontology = json.load(f)
    except FileNotFoundError:
        return {"valid": False, "error": "Ontology not found"}
    
    if data_type not in ontology['data_types']:
        return {"valid": False, "error": f"Unknown data type: {data_type}"}
    
    spec = ontology['data_types'][data_type]
    min_val, max_val = spec['range']
    
    if not (min_val <= value <= max_val):
        return {
            "valid": False,
            "error": f"{data_type} {value}{unit} outside range [{min_val}, {max_val}]"
        }
    
    return {"valid": True}

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    pattern = r'^\+?1?\d{9,15}$'
    return re.match(pattern, phone.replace(" ", "").replace("-", "")) is not None
