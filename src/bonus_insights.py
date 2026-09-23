"""
CREATIVE ADDITION (beyond the 4 listed bonus items): workload fairness
insight.

While reviewing the assignment's own test data, every single one of the 10
provided test_case_*.json files produces at least one agent with ZERO
deliveries for the day -- the fleet is consistently oversized relative to
package volume and/or agent starting positions cluster away from where
packages actually originate. That's not a coincidence worth ignoring: a
report that only shows per-agent numbers doesn't surface it, and a human
skimming 3-5 per-agent blocks might not notice either.

This module computes a small, honest "how balanced was today's workload"
summary from the same simulation results the core report already has --
no new inputs, no new assumptions about ambiguous spec details, just an
extra lens on data we already computed. It's written to
output/workload_insight.json (never mixed into the required report.json).
"""

import statistics
from typing import Dict

from .simulator import AgentResult


def build_workload_insight(results: Dict[str, AgentResult]) -> dict:
    counts = [r.packages_delivered for r in results.values()]
    total_agents = len(counts)
    idle_agents = [aid for aid, r in results.items() if r.packages_delivered == 0]
    active_agents = total_agents - len(idle_agents)

    insight = {
        "total_agents": total_agents,
        "idle_agents": sorted(idle_agents),
        "idle_agent_count": len(idle_agents),
        "active_agent_count": active_agents,
        "packages_per_agent": {
            "min": min(counts) if counts else 0,
            "max": max(counts) if counts else 0,
            "mean": round(statistics.mean(counts), 2) if counts else 0,
            "stdev": round(statistics.pstdev(counts), 2) if len(counts) > 1 else 0.0,
        },
    }

    if total_agents == 0:
        insight["summary"] = "No agents in this scenario."
    elif len(idle_agents) == 0:
        insight["summary"] = "Every agent delivered at least one package today."
    else:
        pct = round(len(idle_agents) / total_agents * 100)
        insight["summary"] = (
            f"{len(idle_agents)} of {total_agents} agents ({pct}%) delivered nothing "
            f"today -- the fleet may be oversized for this package volume, or these "
            f"agents are simply positioned far from every warehouse relative to the "
            f"others. Consider this before reading too much into 'best_agent': it's "
            f"the best of only {active_agents} agents who had any packages to compare."
        )

    return insight
