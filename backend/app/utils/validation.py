"""Health data validation utilities"""
import json
from pathlib import Path
from typing import Optional
from importlib.resources import files
from app.config.settings import get_settings

settings = get_settings()


def validate_health_data(data_type: str, value: float, unit: str, ontology_path: Optional[str] = None) -> dict:
    """Validate health data against ontology"""
    if ontology_path is None:
        # Use default from config, but resolve robustly
        ontology_path = settings.HEALTH_ONTOLOGY_PATH
    
    # Robust path resolution
    ontology_file = Path(ontology_path)
    # If relative path doesn't exist, try package resource
    if not ontology_file.exists() and not ontology_file.is_absolute():
        ontology_file = files("app.core").joinpath("health_ontology.json")
    
    """Basic validation against health ontology"""
    with open(ontology_file, "r") as f:
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

