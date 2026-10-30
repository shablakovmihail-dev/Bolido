"""
Bolido Core - Detection engine, models and compute backends.
"""

from bolido.core.models import BoundingBox, CandidateDetection, MeteorEvent, Point
from bolido.core.detector import MeteorDetector

__all__ = ["BoundingBox", "Point", "CandidateDetection", "MeteorEvent", "MeteorDetector"]
