import json
import tempfile
import unittest
from pathlib import Path

from kai_operator import KaiOperator
from world_puzzle_360 import (
    MissingPuzzle, PuzzleFragment, SourceRef, WorldPuzzle360, parse_fuzzy_date,
)


class WorldPuzzle360Tests(unittest.TestCase):
    @staticmethod
    def fragment(claim, entities, geo, timestamp, sources=None):
        return PuzzleFragment(claim, sources or [], entities=entities, geo=geo,
                              timestamp_event=timestamp)

    def test_source_domain_and_fuzzy_dates_are_normalized(self):
        source = SourceRef("one", "news", url="https://Example.ORG/story")
        self.assertEqual(source.domain, "example.org")
        self.assertIsNotNone(parse_fuzzy_date("April 2026").tzinfo)
        self.assertIsNone(parse_fuzzy_date("2026-99"))

    def test_entities_are_case_insensitive(self):
        puzzle = WorldPuzzle360()
        first = self.fragment("one", ["Port C"], [], "2026-04")
        second = self.fragment("two", ["port c"], [], "2026-04")
        puzzle.add_fragment(first)
        puzzle.add_fragment(second)
        self.assertEqual(first.canonical_entities(puzzle.entity_registry),
                         second.canonical_entities(puzzle.entity_registry))
        self.assertEqual(puzzle.entity_registry.get_canonical("PORT C"), "E0001")

    def test_relation_records_all_weak_dimensions_and_confidence_history(self):
        puzzle = WorldPuzzle360()
        first = self.fragment("one", ["A"], ["North"], "2024-01-01")
        second = self.fragment("two", ["B"], ["South"], "2026-01-01")
        puzzle.add_fragment(first)
        puzzle.add_fragment(second)
        edge_id = puzzle.propose_relation(first.fragment_id, second.fragment_id,
                                          "possible", "test")
        self.assertIsNotNone(edge_id)
        self.assertEqual({item["category"] for item in puzzle.list_missing()},
                         {"independence", "temporal", "entity", "geo"})
        self.assertTrue(puzzle.support_relation(edge_id, "reviewer", "evidence", 0.5))
        self.assertTrue(puzzle.falsify_relation(edge_id, "critic", "counterexample", 1.0))
        self.assertEqual(len(puzzle.get_relation(edge_id)["confidence_history"]), 3)

    def test_trace_path_returns_only_maximal_paths(self):
        puzzle = WorldPuzzle360()
        fragments = [self.fragment(str(i), [str(i)], [], None) for i in range(3)]
        for fragment in fragments:
            puzzle.add_fragment(fragment)
        puzzle.propose_relation(fragments[0].fragment_id, fragments[1].fragment_id, "next", "test")
        puzzle.propose_relation(fragments[1].fragment_id, fragments[2].fragment_id, "next", "test")
        self.assertEqual(puzzle.trace_path(fragments[0].fragment_id),
                         [[fragment.fragment_id for fragment in fragments]])

    def test_export_and_operator_activation(self):
        operator = KaiOperator()
        operator.activate()
        self.assertIsInstance(operator.world_puzzle, WorldPuzzle360)
        self.assertTrue(operator.diagnostics()["WorldPuzzle360"])
        operator.world_puzzle.add_missing(MissingPuzzle("Need source", "source"))
        with tempfile.TemporaryDirectory() as directory:
            output = operator.world_puzzle.export_json(Path(directory) / "state.json")
            state = json.loads(Path(output).read_text(encoding="utf-8"))
            self.assertEqual(state["gap_summary"]["unresolved"], 1)


if __name__ == "__main__":
    unittest.main()
