"""
BONUS: Export the top performer (best_agent) to CSV.

ASSUMPTION: "top performer" = the report's best_agent (lowest average
distance per delivery among agents who delivered at least one package).
If no agent delivered anything, no CSV is written and the caller is told
via the return value (None) so it can skip/report that gracefully instead
of writing a nonsensical empty file.
"""

import csv
from typing import Dict, Optional

from .simulator import AgentResult


def export_top_performer_csv(
    results: Dict[str, AgentResult], best_agent_id: Optional[str], path: str
) -> Optional[str]:
    if best_agent_id is None:
        return None

    result = results[best_agent_id]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["agent_id", "packages_delivered", "total_distance", "efficiency"])
        writer.writerow(
            [
                result.agent_id,
                result.packages_delivered,
                round(result.total_distance, 2),
                round(result.efficiency, 2),
            ]
        )
    return path
