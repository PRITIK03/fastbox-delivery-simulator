#!/usr/bin/env python3
"""
FastBox Delivery Simulator -- CLI entry point.

Usage:
    python main.py <input_file.json> [options]

Core (always runs):
    python main.py data/base_case.json
        -> writes report.json (repo root, exact schema from the PDF)

Options:
    --output PATH          Where to write the core report (default: report.json)
    --distance-metric NAME  "euclidean" (default, per the PDF) or "manhattan"
    --bonus                 Also run all bonus features:
                               * random delivery delays  -> output/report_bonus.json
                               * ASCII route map/trace    -> output/routes_ascii.txt (+ printed)
                               * CSV export of top agent  -> output/top_performer.csv
                               * workload fairness insight -> output/workload_insight.json
    --seed N                RNG seed for delay simulation (default: 42)
    --new-agents-demo       Run the "new agent joins mid-day" bonus scenario
                            and write output/report_new_agent_demo.json
    --quiet                 Suppress the printed summary/ASCII map to stdout

Examples:
    python main.py data/base_case.json --bonus
    python main.py data/test_cases/test_case_1.json --output output/tc1_report.json --bonus
    python main.py data/base_case.json --distance-metric manhattan
"""

import argparse
import json
import os
import sys

from src.loader import load_scenario, InputFormatError
from src.models import DISTANCE_METRICS
from src.simulator import run_simulation, best_agent
from src.report import build_report, write_report
from src.bonus_delays import make_delay_fn, build_bonus_report
from src.bonus_ascii import render_ascii_map, render_agent_routes
from src.bonus_csv import export_top_performer_csv
from src.bonus_new_agent import parse_new_agents, run_simulation_with_new_agents
from src.bonus_insights import build_workload_insight


def main():
    parser = argparse.ArgumentParser(description="FastBox delivery simulator")
    parser.add_argument("input_file", help="Path to the scenario JSON file")
    parser.add_argument("--output", default="report.json", help="Path for the core report.json")
    parser.add_argument(
        "--distance-metric", choices=sorted(DISTANCE_METRICS), default="euclidean",
        help="Distance function used for assignment and simulation (default: euclidean, "
             "per the assignment spec)",
    )
    parser.add_argument("--bonus", action="store_true", help="Run all bonus features")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for delay simulation")
    parser.add_argument(
        "--new-agents-demo", action="store_true",
        help="Run the mid-day new-agent-joining bonus scenario",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout summary")
    args = parser.parse_args()

    distance_fn = DISTANCE_METRICS[args.distance_metric]

    try:
        warehouses, agents, packages = load_scenario(args.input_file)
    except (InputFormatError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR loading '{args.input_file}': {e}", file=sys.stderr)
        sys.exit(1)

    results, assignment_log = run_simulation(warehouses, agents, packages, distance_fn=distance_fn)
    report = build_report(results)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    write_report(report, args.output)

    if not args.quiet:
        print(f"Simulated {len(packages)} packages across {len(agents)} agents, "
              f"{len(warehouses)} warehouses. (distance metric: {args.distance_metric})")
        print(f"Core report written to: {args.output}")
        print(json.dumps(report, indent=2))

    if args.bonus:
        os.makedirs("output", exist_ok=True)

        # Bonus 1: random delivery delays (re-simulate with a delay function; distances unaffected)
        delay_fn = make_delay_fn(seed=args.seed)
        delay_results, _ = run_simulation(
            warehouses, agents, packages, delay_fn=delay_fn, distance_fn=distance_fn
        )
        bonus_report = build_bonus_report(report, delay_results)
        write_report(bonus_report, os.path.join("output", "report_bonus.json"))

        # Bonus 2: ASCII visualization
        ascii_map = render_ascii_map(warehouses, agents, packages)
        ascii_routes = render_agent_routes(assignment_log)
        ascii_text = ascii_map + "\n\n" + "Agent routes:\n" + ascii_routes
        with open(os.path.join("output", "routes_ascii.txt"), "w", encoding="utf-8") as f:
            f.write(ascii_text + "\n")
        if not args.quiet:
            print("\n" + ascii_text)

        # Bonus 3: CSV export of top performer
        csv_path = export_top_performer_csv(
            results, best_agent(results), os.path.join("output", "top_performer.csv")
        )
        if not args.quiet:
            print(f"\nTop performer CSV: {csv_path or '(no agent delivered anything -- skipped)'}")

        # Creative addition: workload fairness insight (see src/bonus_insights.py)
        insight = build_workload_insight(results)
        with open(os.path.join("output", "workload_insight.json"), "w", encoding="utf-8") as f:
            json.dump(insight, f, indent=4)
            f.write("\n")
        if not args.quiet:
            print(f"\nWorkload insight: {insight['summary']}")

        if not args.quiet:
            print(f"\nBonus report (with delay stats): output/report_bonus.json")

    if args.new_agents_demo:
        with open(args.input_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        new_agent_events = parse_new_agents(raw)

        if not new_agent_events and len(packages) >= 2:
            # No new_agents defined in this file -- inject a small illustrative demo event
            # so the feature is visible even against the shipped inputs, which don't define
            # one. To make the demo actually observable (rather than silently winning zero
            # packages), the demo agent is dropped right at the warehouse of the package
            # immediately AFTER the trigger point, guaranteeing it intercepts that delivery.
            mid_index = len(packages) // 2
            trigger_package = packages[mid_index]
            next_package = packages[mid_index + 1] if mid_index + 1 < len(packages) else None
            if next_package:
                spawn_location = list(warehouses[next_package.warehouse_id].location)
                new_agent_events = [
                    {"id": "A_NEW", "location": spawn_location, "joins_after_package": trigger_package.id}
                ]

        demo_results, demo_log = run_simulation_with_new_agents(
            warehouses, agents, packages, new_agent_events, distance_fn=distance_fn
        )
        demo_report = build_report(demo_results)
        os.makedirs("output", exist_ok=True)
        write_report(demo_report, os.path.join("output", "report_new_agent_demo.json"))
        if not args.quiet:
            print(f"\nNew-agent-mid-day demo report: output/report_new_agent_demo.json")
            print(json.dumps(demo_report, indent=2))


if __name__ == "__main__":
    main()
