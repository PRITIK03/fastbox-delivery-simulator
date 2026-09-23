"""
Core simulation: assign packages to agents and simulate the day's deliveries.

DOCUMENTED ASSUMPTIONS (also summarised in README.md):

1. Agent-to-warehouse "nearest agent" lookup (the PDF's step 2) is computed
   from each agent's FIXED STARTING location, exactly as literally stated
   ("Euclidean distance from agent to warehouse"). It is computed once and
   does not change as agents move during the day.

2. Total distance traveled (the PDF's step 3, "simulate delivery ... compute
   total distance traveled") is a CUMULATIVE PATH per agent: the agent starts
   at its initial location, and for each package assigned to it (processed in
   the order packages appear in the input file) it travels
       current_position -> warehouse -> destination
   and its "current position" becomes that destination for the next package.
   This models a real delivery run rather than resetting to the start after
   every parcel.

3. Tie-break when two or more agents are exactly equidistant from a
   warehouse: the agent with the lexicographically smallest ID wins. None of
   the shipped test cases actually produce a tie, but hidden inputs might.

4. Agents that end the day with zero deliveries get "efficiency": null
   (can't divide by zero) and are excluded from best_agent consideration.
   If NO agent delivered anything, "best_agent" is null.

5. "efficiency" = total_distance / packages_delivered (average distance per
   delivery). Lower is better. This matches the ratio implied by the PDF's
   sample report (85.32/2 = 42.66, etc.), even though the sample's absolute
   numbers don't reconcile with its own sample input coordinates -- that
   sample report looks like it exists to show the JSON shape, not results
   to reproduce exactly.

6. Distance metric defaults to Euclidean (as the PDF specifies) but is
   swappable via `distance_fn` / the CLI's --distance-metric, rather than
   hardcoded inline -- see models.DISTANCE_METRICS.
"""

from typing import Callable, Dict, List, Optional

from .models import Agent, Package, Warehouse, euclidean_distance

DistanceFn = Callable[[tuple, tuple], float]


class AgentResult:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.packages_delivered = 0
        self.total_distance = 0.0
        self.delivered_package_ids: List[str] = []
        self.total_delay_minutes = 0.0  # bonus: populated only if delays are simulated

    @property
    def efficiency(self) -> Optional[float]:
        if self.packages_delivered == 0:
            return None
        return self.total_distance / self.packages_delivered


def nearest_agent_id(
    agents: Dict[str, Agent],
    point,
    distance_fn: DistanceFn = euclidean_distance,
    exclude=frozenset(),
) -> str:
    """Return the id of the agent whose STARTING location is nearest to `point`.
    Ties broken by lowest agent id (assumption #3 above)."""
    candidates = [a for a in agents.values() if a.id not in exclude]
    if not candidates:
        raise ValueError("No agents available to assign to")
    best = min(candidates, key=lambda a: (distance_fn(a.location, point), a.id))
    return best.id


def deliver_package(
    agent_id: str,
    package: Package,
    warehouse: Warehouse,
    current_position: Dict[str, tuple],
    results: Dict[str, AgentResult],
    distance_fn: DistanceFn = euclidean_distance,
    delay_fn=None,
) -> dict:
    """Simulates one agent delivering one package: moves the agent from its
    current position to the warehouse, then to the destination, updating
    `results[agent_id]` and `current_position[agent_id]` in place.

    Shared by run_simulation() and the mid-day-new-agent bonus so both use
    identical delivery-leg math instead of two copies drifting apart.

    Returns a log entry describing the leg (used by the ASCII route bonus).
    """
    pos = current_position[agent_id]
    leg_to_warehouse = distance_fn(pos, warehouse.location)
    leg_to_destination = distance_fn(warehouse.location, package.destination)
    leg_total = leg_to_warehouse + leg_to_destination

    result = results[agent_id]
    result.packages_delivered += 1
    result.total_distance += leg_total
    result.delivered_package_ids.append(package.id)
    if delay_fn is not None:
        result.total_delay_minutes += delay_fn(package)

    current_position[agent_id] = package.destination

    return {
        "package_id": package.id,
        "warehouse_id": warehouse.id,
        "agent_id": agent_id,
        "from": pos,
        "via_warehouse": warehouse.location,
        "to_destination": package.destination,
        "leg_distance": round(leg_total, 2),
    }


def run_simulation(
    warehouses: Dict[str, Warehouse],
    agents: Dict[str, Agent],
    packages: List[Package],
    delay_fn=None,
    distance_fn: DistanceFn = euclidean_distance,
):
    """
    Runs the full day: assigns every package to its nearest agent (by fixed
    starting position) and simulates the cumulative delivery path per agent.

    `delay_fn`, if provided, is called as delay_fn(package) -> minutes and is
    used purely for the bonus "random delivery delay" reporting; it never
    affects distance or assignment.

    Returns: (results: Dict[str, AgentResult], assignment_log: List[dict])
    """
    results: Dict[str, AgentResult] = {aid: AgentResult(aid) for aid in agents}
    current_position = {aid: agent.location for aid, agent in agents.items()}
    assignment_log = []

    for package in packages:
        warehouse = warehouses[package.warehouse_id]
        chosen_agent_id = nearest_agent_id(agents, warehouse.location, distance_fn=distance_fn)
        entry = deliver_package(
            chosen_agent_id, package, warehouse, current_position, results,
            distance_fn=distance_fn, delay_fn=delay_fn,
        )
        assignment_log.append(entry)

    return results, assignment_log


def best_agent(results: Dict[str, AgentResult]) -> Optional[str]:
    """Most efficient agent = lowest average distance per delivery,
    among agents who delivered at least one package."""
    delivering = [r for r in results.values() if r.packages_delivered > 0]
    if not delivering:
        return None
    return min(delivering, key=lambda r: (r.efficiency, r.agent_id)).agent_id
