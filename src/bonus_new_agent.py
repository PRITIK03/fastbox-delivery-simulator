"""
BONUS: Handle a new agent joining mid-day.

ASSUMPTION: none of the shipped input files define this scenario, and the
PDF gives no schema for it, so we define a minimal, backward-compatible
extension: an OPTIONAL "new_agents" list in the input JSON --

    "new_agents": [
        {"id": "A4", "location": [50, 50], "joins_after_package": "P3"}
    ]

-- meaning agent A4 starts at [50, 50] and becomes available for
assignment starting with the package immediately AFTER P3 is processed
(in input file order). If "new_agents" is absent (true for every file
in this assignment), behavior is identical to the standard simulation --
this is purely additive.

This lives in its own module rather than modifying simulator.py's main
path, to keep the required core simulation simple and demonstrably
unaffected by this optional feature. It reuses simulator.deliver_package()
for the actual delivery-leg math so this bonus can never silently drift
out of sync with the core distance/assignment logic.
"""

from typing import Dict, List

from .models import Agent, Warehouse, euclidean_distance
from .simulator import AgentResult, DistanceFn, deliver_package, nearest_agent_id


def parse_new_agents(raw: dict) -> List[dict]:
    return raw.get("new_agents", [])


def run_simulation_with_new_agents(
    warehouses: Dict[str, Warehouse],
    agents: Dict[str, Agent],
    packages,
    new_agent_events: List[dict],
    delay_fn=None,
    distance_fn: DistanceFn = euclidean_distance,
):
    """Same algorithm as simulator.run_simulation, extended so that agents
    listed in `new_agent_events` are added to the live agent pool partway
    through the day, right after the package named in "joins_after_package"
    has been processed."""
    agents = dict(agents)  # local copy; don't mutate caller's dict
    results: Dict[str, AgentResult] = {aid: AgentResult(aid) for aid in agents}
    current_position = {aid: a.location for aid, a in agents.items()}

    pending_joins = {e["joins_after_package"]: e for e in new_agent_events}
    assignment_log = []

    for package in packages:
        warehouse = warehouses[package.warehouse_id]
        chosen_id = nearest_agent_id(agents, warehouse.location, distance_fn=distance_fn)

        entry = deliver_package(
            chosen_id, package, warehouse, current_position, results,
            distance_fn=distance_fn, delay_fn=delay_fn,
        )
        assignment_log.append(entry)

        # If a new agent is scheduled to join right after this package, add it now.
        if package.id in pending_joins:
            event = pending_joins.pop(package.id)
            new_agent = Agent(id=event["id"], location=tuple(event["location"]))
            agents[new_agent.id] = new_agent
            current_position[new_agent.id] = new_agent.location
            results[new_agent.id] = AgentResult(new_agent.id)
            assignment_log.append(
                {"event": "agent_joined", "agent_id": new_agent.id, "after_package": package.id}
            )

    return results, assignment_log
