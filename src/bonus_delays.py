"""
BONUS: Random delivery delays.

ASSUMPTION: the core report.json schema stays exactly as specified in the
PDF (see report.py), so delay data is written to a *separate* file,
report_bonus.json, that includes everything in report.json plus per-agent
delay stats.

Delays are generated with a seeded RNG (default seed=42) purely so runs are
reproducible for grading/debugging -- re-running the script twice on the
same input gives the same "random" delays. The seed is configurable via
--seed on the CLI.

Delay model: each package independently gets a delay drawn uniformly from
0-15 minutes, representing things like traffic or a slow handoff at the
warehouse. This is a simulation add-on only -- it does NOT affect distance,
assignment, or the core report.json.
"""

import random
from typing import Dict

from .models import Package
from .simulator import AgentResult


def make_delay_fn(seed: int = 42, min_minutes: float = 0, max_minutes: float = 15):
    rng = random.Random(seed)

    def delay_fn(package: Package) -> float:
        return round(rng.uniform(min_minutes, max_minutes), 1)

    return delay_fn


def build_bonus_report(report: dict, results: Dict[str, AgentResult]) -> dict:
    """Extends an already-built core report with delay stats per agent."""
    bonus_report = {k: dict(v) if isinstance(v, dict) else v for k, v in report.items()}
    for agent_id, result in results.items():
        if agent_id not in bonus_report:
            continue
        delivered = result.packages_delivered
        bonus_report[agent_id]["total_delay_minutes"] = round(result.total_delay_minutes, 1)
        bonus_report[agent_id]["avg_delay_minutes"] = (
            round(result.total_delay_minutes / delivered, 1) if delivered else None
        )
    return bonus_report
