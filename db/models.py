"""
db/models.py — GoGenie Data Models
Defines Customer and Booking dataclasses used across DB and tools.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Customer:
    name: str
    email: str
    phone: str
    customer_id: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Booking:
    customer_id: str
    booking_type: str         # Flight / Train / Bus
    from_city: str
    to_city: str
    date: str
    time: str
    selected_option: str
    status: str               = "confirmed"
    booking_id: Optional[str] = None
    created_at: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id":              self.booking_id,
            "customer_id":     self.customer_id,
            "booking_type":    self.booking_type,
            "from_city":       self.from_city,
            "to_city":         self.to_city,
            "date":            self.date,
            "time":            self.time,
            "selected_option": self.selected_option,
            "status":          self.status,
            "created_at":      self.created_at,
        }
