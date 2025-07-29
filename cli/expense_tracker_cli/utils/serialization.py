"""
JSON serialization utilities for the CLI.
"""
import json
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


class ExpenseTrackerJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Expense Tracker data types."""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)