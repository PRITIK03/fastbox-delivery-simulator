"""
Builds the report.json exactly matching the schema shown in the assignment
PDF:

    {
        "A1": {"packages_delivered": 2, "total_distance": 85.32, "efficiency": 42.66},
        ...
        "best_agent": "A1"
    }

Kept intentionally minimal/schema-exact -- bonus data (delays, routes, CSV)
is written to separate files (see bonus_*.py) rather than added as extra
keys here, so nothing about the required output format is at risk.
"""

import json
from typing import Dict

from .simulator import AgentResult, best_agent


def build_report(results: Dict[str, AgentResult]) -> dict:
    report = {}
    for agent_id, result in sorted(results.items()):
        report[agent_id] = {
            "packages_delivered": result.packages_delivered,
            "total_distance": round(result.total_distance, 2),
            "efficiency": (
                round(result.efficiency, 2) if result.efficiency is not None else None
            ),
        }
    report["best_agent"] = best_agent(results)
    return report


def write_report(report: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        f.write("\n")
