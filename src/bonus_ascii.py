"""
BONUS: ASCII visualization of the day's routes.

Two views are produced:
  1. A scaled ASCII grid map plotting every warehouse (W), agent start (A),
     and package destination (.), for a bird's-eye-view sanity check.
  2. A per-agent text route trace, e.g.:
        A1: start(5,5) -> W1(0,0) -> P1 dest(30,40) -> W1(0,0) -> P4 dest(10,10)

ASSUMPTION: grid size is fixed at GRID_W x GRID_H characters; coordinates
are linearly scaled to fit regardless of the input's actual coordinate
range, so this works for any input file, not just ones bounded to 0-100.
"""

from typing import Dict, List

from .models import Agent, Warehouse

GRID_W = 60
GRID_H = 25


def _scale(value, in_min, in_max, out_max):
    if in_max == in_min:
        return out_max // 2
    return int(round((value - in_min) / (in_max - in_min) * (out_max - 1)))


def render_ascii_map(warehouses: Dict[str, Warehouse], agents: Dict[str, Agent], packages) -> str:
    xs = [w.location[0] for w in warehouses.values()] + [a.location[0] for a in agents.values()]
    ys = [w.location[1] for w in warehouses.values()] + [a.location[1] for a in agents.values()]
    xs += [p.destination[0] for p in packages]
    ys += [p.destination[1] for p in packages]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    grid = [[" " for _ in range(GRID_W)] for _ in range(GRID_H)]

    def plot(x, y, ch):
        gx = _scale(x, x_min, x_max, GRID_W)
        gy = GRID_H - 1 - _scale(y, y_min, y_max, GRID_H)  # flip so +y is "up"
        gx = min(max(gx, 0), GRID_W - 1)
        gy = min(max(gy, 0), GRID_H - 1)
        grid[gy][gx] = ch

    for p in packages:
        plot(p.destination[0], p.destination[1], ".")
    for w in warehouses.values():
        plot(w.location[0], w.location[1], "W")
    for a in agents.values():
        plot(a.location[0], a.location[1], "A")

    border = "+" + "-" * GRID_W + "+"
    lines = [border]
    for row in grid:
        lines.append("|" + "".join(row) + "|")
    lines.append(border)
    lines.append("Legend: W = warehouse, A = agent start, . = package destination")
    return "\n".join(lines)


def render_agent_routes(assignment_log: List[dict]) -> str:
    routes: Dict[str, List[str]] = {}
    for entry in assignment_log:
        aid = entry["agent_id"]
        routes.setdefault(aid, []).append(
            f"{entry['warehouse_id']}{tuple(round(c) for c in entry['via_warehouse'])} "
            f"-> {entry['package_id']} dest{tuple(round(c) for c in entry['to_destination'])}"
        )

    lines = []
    for aid in sorted(routes):
        lines.append(f"{aid}:")
        for step in routes[aid]:
            lines.append(f"  -> {step}")
    return "\n".join(lines) if lines else "(no deliveries)"
