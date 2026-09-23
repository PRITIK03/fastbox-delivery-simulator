"""
Unit tests (stdlib unittest -- no extra dependencies needed).

Run with:  python -m unittest discover -s tests -v
       or:  python -m pytest tests/   (pytest can run unittest-style tests too)

These target the specific logic decisions this project made, not just
"does it run": tie-breaking, zero-delivery handling, both input schemas,
and the validation errors the loader is supposed to catch.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import Agent, Package, Warehouse, euclidean_distance, manhattan_distance
from src.loader import load_scenario, InputFormatError
from src.simulator import run_simulation, nearest_agent_id, best_agent
from src.report import build_report


class TestDistanceFunctions(unittest.TestCase):
    def test_euclidean_known_value(self):
        self.assertAlmostEqual(euclidean_distance((0, 0), (3, 4)), 5.0)

    def test_euclidean_same_point_is_zero(self):
        self.assertEqual(euclidean_distance((5, 5), (5, 5)), 0.0)

    def test_manhattan_known_value(self):
        self.assertEqual(manhattan_distance((0, 0), (3, 4)), 7)


class TestLoaderBothSchemas(unittest.TestCase):
    def _write(self, obj):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        json.dump(obj, f)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_dict_schema_matches_list_schema(self):
        dict_shape = {
            "warehouses": {"W1": [0, 0]},
            "agents": {"A1": [1, 1]},
            "packages": [{"id": "P1", "warehouse": "W1", "destination": [5, 5]}],
        }
        list_shape = {
            "warehouses": [{"id": "W1", "location": [0, 0]}],
            "agents": [{"id": "A1", "location": [1, 1]}],
            "packages": [{"id": "P1", "warehouse_id": "W1", "destination": [5, 5]}],
        }
        w1, a1, p1 = load_scenario(self._write(dict_shape))
        w2, a2, p2 = load_scenario(self._write(list_shape))

        self.assertEqual(w1["W1"].location, w2["W1"].location)
        self.assertEqual(a1["A1"].location, a2["A1"].location)
        self.assertEqual(p1[0].warehouse_id, p2[0].warehouse_id)
        self.assertEqual(p1[0].destination, p2[0].destination)

    def test_missing_top_level_key_raises(self):
        bad = {"warehouses": {}, "agents": {}}  # no "packages"
        with self.assertRaises(InputFormatError):
            load_scenario(self._write(bad))

    def test_duplicate_package_id_raises(self):
        bad = {
            "warehouses": {"W1": [0, 0]},
            "agents": {"A1": [0, 0]},
            "packages": [
                {"id": "P1", "warehouse": "W1", "destination": [1, 1]},
                {"id": "P1", "warehouse": "W1", "destination": [2, 2]},
            ],
        }
        with self.assertRaises(InputFormatError):
            load_scenario(self._write(bad))

    def test_package_referencing_unknown_warehouse_raises(self):
        bad = {
            "warehouses": {"W1": [0, 0]},
            "agents": {"A1": [0, 0]},
            "packages": [{"id": "P1", "warehouse": "W_GHOST", "destination": [1, 1]}],
        }
        with self.assertRaises(InputFormatError):
            load_scenario(self._write(bad))

    def test_empty_warehouses_raises(self):
        bad = {"warehouses": {}, "agents": {"A1": [0, 0]}, "packages": []}
        with self.assertRaises(InputFormatError):
            load_scenario(self._write(bad))


class TestAssignmentAndSimulation(unittest.TestCase):
    def setUp(self):
        self.warehouses = {
            "W1": Warehouse("W1", (0, 0)),
            "W2": Warehouse("W2", (100, 100)),
        }

    def test_nearest_agent_picks_closer_agent(self):
        agents = {"A1": Agent("A1", (1, 1)), "A2": Agent("A2", (99, 99))}
        self.assertEqual(nearest_agent_id(agents, (0, 0)), "A1")
        self.assertEqual(nearest_agent_id(agents, (100, 100)), "A2")

    def test_tie_break_is_lowest_agent_id(self):
        # Both agents exactly equidistant from the warehouse at (0, 0)
        agents = {"A2": Agent("A2", (5, 0)), "A1": Agent("A1", (0, 5))}
        self.assertEqual(nearest_agent_id(agents, (0, 0)), "A1")

    def test_all_packages_get_delivered_exactly_once(self):
        agents = {"A1": Agent("A1", (0, 0)), "A2": Agent("A2", (100, 100))}
        packages = [
            Package("P1", "W1", (10, 10)),
            Package("P2", "W2", (90, 90)),
            Package("P3", "W1", (5, 5)),
        ]
        results, _ = run_simulation(self.warehouses, agents, packages)
        total_delivered = sum(r.packages_delivered for r in results.values())
        self.assertEqual(total_delivered, len(packages))

    def test_zero_delivery_agent_has_null_efficiency(self):
        # Both packages route through W1; A2 sits right next to W2 and gets nothing.
        agents = {"A1": Agent("A1", (0, 0)), "A2": Agent("A2", (100, 100))}
        packages = [Package("P1", "W1", (1, 1)), Package("P2", "W1", (2, 2))]
        results, _ = run_simulation(self.warehouses, agents, packages)

        self.assertEqual(results["A2"].packages_delivered, 0)
        self.assertIsNone(results["A2"].efficiency)

        report = build_report(results)
        self.assertIsNone(report["A2"]["efficiency"])

    def test_best_agent_excludes_zero_delivery_agents(self):
        agents = {"A1": Agent("A1", (0, 0)), "A2": Agent("A2", (100, 100))}
        packages = [Package("P1", "W1", (1, 1))]
        results, _ = run_simulation(self.warehouses, agents, packages)
        # A1 delivered, A2 didn't -- A2 must never be "best" by default.
        self.assertEqual(best_agent(results), "A1")

    def test_best_agent_is_none_when_nobody_delivers(self):
        agents = {"A1": Agent("A1", (0, 0))}
        results, _ = run_simulation(self.warehouses, agents, packages=[])
        self.assertIsNone(best_agent(results))

    def test_cumulative_distance_uses_updated_position(self):
        # A single agent, two packages from the same warehouse: the second
        # leg should start from the FIRST package's destination, not from
        # the agent's original starting point.
        agents = {"A1": Agent("A1", (0, 0))}
        warehouses = {"W1": Warehouse("W1", (0, 0))}
        packages = [Package("P1", "W1", (10, 0)), Package("P2", "W1", (10, 10))]
        results, log = run_simulation(warehouses, agents, packages)

        # Expected: (0,0)->(0,0)=0, (0,0)->(10,0)=10  => first leg = 10
        # then (10,0)->(0,0)=10, (0,0)->(10,10)=14.14  => second leg ~= 24.14
        self.assertAlmostEqual(log[0]["leg_distance"], 10.0, places=2)
        self.assertAlmostEqual(log[1]["leg_distance"], 24.14, places=2)


if __name__ == "__main__":
    unittest.main()
