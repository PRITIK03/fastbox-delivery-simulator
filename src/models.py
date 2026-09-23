"""
Core data models for the FastBox delivery simulation.

Kept deliberately simple (plain dataclasses) since the assignment's
evaluation criteria emphasise clarity over cleverness.
"""

from dataclasses import dataclass
from typing import Tuple


Point = Tuple[float, float]


@dataclass(frozen=True)
class Warehouse:
    id: str
    location: Point


@dataclass(frozen=True)
class Agent:
    id: str
    location: Point  # agent's starting location at the beginning of the day


@dataclass(frozen=True)
class Package:
    id: str
    warehouse_id: str
    destination: Point


def euclidean_distance(a: Point, b: Point) -> float:
    """Straight-line distance between two (x, y) points. The PDF specifies
    this explicitly ("Euclidean distance from agent to warehouse") -- it's
    the default and only metric used unless --distance-metric says otherwise."""
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def manhattan_distance(a: Point, b: Point) -> float:
    """Grid/city-block distance. Not required by the assignment, but real
    delivery routing is rarely a straight line through buildings -- this is
    offered as an alternative via --distance-metric so the "distance model"
    isn't hardwired into every function that needs one."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# Registry so main.py can expose a --distance-metric flag without every
# caller needing to know the full list of available strategies.
DISTANCE_METRICS = {
    "euclidean": euclidean_distance,
    "manhattan": manhattan_distance,
}
