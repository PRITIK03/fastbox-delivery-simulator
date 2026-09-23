"""
Loads and normalizes the FastBox input JSON.

ASSUMPTION (documented, see README "Assumptions" section):
The files shipped with the assignment use two different, but equally
valid, JSON shapes for the same data:

  Shape 1 (used by the assignment PDF's example and all test_case_*.json):
      {
        "warehouses": {"W1": [0, 0], ...},
        "agents": {"A1": [5, 5], ...},
        "packages": [{"id": "P1", "warehouse": "W1", "destination": [30, 40]}]
      }

  Shape 2 (used by base_case.json):
      {
        "warehouses": [{"id": "W1", "location": [0, 0]}, ...],
        "agents": [{"id": "A1", "location": [5, 5]}, ...],
        "packages": [{"id": "P1", "warehouse_id": "W1", "destination": [30, 40]}]
      }

Rather than assume the grader will only ever hand us one shape, this
loader detects and normalizes both into the same internal models, so
the rest of the codebase never has to think about input format again.

The assignment PDF also references a "data.json" filename, but no file
in the shipped assignment is actually named that -- so instead of
hardcoding a filename, the loader (and main.py) accept any file path.
"""

import json
from typing import Dict, List

from .models import Agent, Package, Warehouse


class InputFormatError(ValueError):
    """Raised when the input JSON doesn't match either supported shape."""


def load_scenario(path: str):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    for key in ("warehouses", "agents", "packages"):
        if key not in raw:
            raise InputFormatError(f"Input JSON is missing required key: '{key}'")

    warehouses = _parse_warehouses(raw["warehouses"])
    agents = _parse_agents(raw["agents"])
    packages = _parse_packages(raw["packages"])

    _validate_references(warehouses, packages)

    return warehouses, agents, packages


def _as_point(value) -> tuple:
    if not (isinstance(value, (list, tuple)) and len(value) == 2):
        raise InputFormatError(f"Expected a [x, y] coordinate pair, got: {value!r}")
    x, y = value
    try:
        return (float(x), float(y))
    except (TypeError, ValueError) as e:
        raise InputFormatError(
            f"Expected numeric [x, y] coordinates, got: {value!r}"
        ) from e


def _parse_warehouses(data) -> Dict[str, Warehouse]:
    warehouses: Dict[str, Warehouse] = {}
    if isinstance(data, dict):
        # Shape 1: {"W1": [x, y], ...}
        for wid, loc in data.items():
            warehouses[wid] = Warehouse(id=wid, location=_as_point(loc))
    elif isinstance(data, list):
        # Shape 2: [{"id": "W1", "location": [x, y]}, ...] -- unlike a JSON
        # object's keys, a list can contain a duplicate "id" by mistake, so
        # this is checked explicitly rather than silently letting the later
        # entry clobber the earlier one.
        for entry in data:
            wid = entry["id"]
            if wid in warehouses:
                raise InputFormatError(f"Duplicate warehouse id: '{wid}'")
            warehouses[wid] = Warehouse(id=wid, location=_as_point(entry["location"]))
    else:
        raise InputFormatError("'warehouses' must be an object or a list")
    if not warehouses:
        raise InputFormatError("'warehouses' must contain at least one warehouse")
    return warehouses


def _parse_agents(data) -> Dict[str, Agent]:
    agents: Dict[str, Agent] = {}
    if isinstance(data, dict):
        for aid, loc in data.items():
            agents[aid] = Agent(id=aid, location=_as_point(loc))
    elif isinstance(data, list):
        for entry in data:
            aid = entry["id"]
            if aid in agents:
                raise InputFormatError(f"Duplicate agent id: '{aid}'")
            agents[aid] = Agent(id=aid, location=_as_point(entry["location"]))
    else:
        raise InputFormatError("'agents' must be an object or a list")
    if not agents:
        raise InputFormatError("'agents' must contain at least one agent")
    return agents


def _parse_packages(data) -> List[Package]:
    if not isinstance(data, list):
        raise InputFormatError("'packages' must be a list")
    packages = []
    for entry in data:
        pid = entry["id"]
        # Shape 1 uses "warehouse", Shape 2 uses "warehouse_id"
        warehouse_id = entry.get("warehouse", entry.get("warehouse_id"))
        if warehouse_id is None:
            raise InputFormatError(
                f"Package '{pid}' has neither 'warehouse' nor 'warehouse_id'"
            )
        if "destination" not in entry:
            raise InputFormatError(f"Package '{pid}' is missing required key: 'destination'")
        packages.append(
            Package(
                id=pid,
                warehouse_id=warehouse_id,
                destination=_as_point(entry["destination"]),
            )
        )
    return packages


def _validate_references(warehouses, packages):
    """Fail fast and clearly if a package points at a warehouse that doesn't exist,
    or if package IDs are duplicated -- both are silent-corruption risks otherwise."""
    seen_ids = set()
    for p in packages:
        if p.id in seen_ids:
            raise InputFormatError(f"Duplicate package id: '{p.id}'")
        seen_ids.add(p.id)
        if p.warehouse_id not in warehouses:
            raise InputFormatError(
                f"Package '{p.id}' references unknown warehouse '{p.warehouse_id}'"
            )
