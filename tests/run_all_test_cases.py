#!/usr/bin/env python3
"""
Runs the simulator against base_case.json and all 10 shipped test_case_*.json
files, per the assignment's note: "Test your code with different JSON
inputs. Make sure total packages delivered matches total packages."

For each file this prints a one-line summary and asserts the core
invariant (sum of packages_delivered across agents == total packages in
the input). Per-file reports are written to output/test_reports/ so they
can be inspected individually.

Run with:  python tests/run_all_test_cases.py
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.loader import load_scenario
from src.simulator import run_simulation
from src.report import build_report, write_report

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output", "test_reports")


def find_input_files():
    files = [os.path.join(DATA_DIR, "base_case.json")]
    files += sorted(
        glob.glob(os.path.join(DATA_DIR, "test_cases", "test_case_*.json")),
        key=lambda p: int(os.path.basename(p).split("_")[-1].split(".")[0]),
    )
    return files


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = find_input_files()

    all_passed = True
    print(f"{'file':<28} {'#wh':>4} {'#agents':>8} {'#pkgs':>6} {'delivered':>10} {'best_agent':>11}  status")
    print("-" * 90)

    for path in files:
        name = os.path.basename(path)
        try:
            warehouses, agents, packages = load_scenario(path)
            results, _ = run_simulation(warehouses, agents, packages)
            report = build_report(results)

            total_delivered = sum(r["packages_delivered"] for aid, r in report.items() if aid != "best_agent")
            ok = total_delivered == len(packages)
            all_passed &= ok
            status = "OK" if ok else "MISMATCH!"

            out_path = os.path.join(OUTPUT_DIR, f"{os.path.splitext(name)[0]}_report.json")
            write_report(report, out_path)

            print(f"{name:<28} {len(warehouses):>4} {len(agents):>8} {len(packages):>6} "
                  f"{total_delivered:>10} {str(report.get('best_agent')):>11}  {status}")
        except Exception as e:
            all_passed = False
            print(f"{name:<28} FAILED: {e}")

    print("-" * 90)
    if all_passed:
        print(f"All {len(files)} input files processed successfully. "
              f"Per-file reports saved to {OUTPUT_DIR}/")
    else:
        print("One or more files failed or had a packages_delivered mismatch. See above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
