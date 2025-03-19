import json
from datetime import datetime
from fastapi import HTTPException
from models.location import Location


def parse_location(location: str) -> Location:
    """
    Parses the location JSON string into a Location model.
    """
    try:
        location_data = json.loads(location)  # Convert JSON string to dict
        return Location(**location_data)  # Validate with Pydantic
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid location format")


def parse_lost_date(lost_date: str) -> datetime:
    """
    Converts a lost_date string (ISO format) to a datetime object.
    """
    try:
        return datetime.fromisoformat(lost_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
