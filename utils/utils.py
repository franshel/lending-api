from datetime import datetime
from typing import Any, Dict, List, Union
import json


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def serialize_pydantic_model(model):
    """
    Recursively serialize a Pydantic model and handle datetime objects for JSONB storage
    """
    if hasattr(model, "dict"):
        # Convert Pydantic model to dict
        model_dict = model.dict()
        # Process each field
        for key, value in model_dict.items():
            model_dict[key] = process_value(value)
        return model_dict
    return process_value(model)


def process_value(value):
    """Process a value for JSON serialization"""
    if isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, list):
        return [process_value(item) for item in value]
    elif isinstance(value, dict):
        return {k: process_value(v) for k, v in value.items()}
    elif hasattr(value, "dict"):
        # Handle nested Pydantic models
        return serialize_pydantic_model(value)
    return value
