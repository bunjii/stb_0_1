"""Compare analysis results against recorded golden values.

These tests exist to guard refactors of the linear-system assembly and solve
(for example the move from dense to sparse matrices). They compare numbers, not
formatted output, with a tolerance that absorbs round-off from a different
assembly order but not an actual change in behaviour.

Regenerate the goldens deliberately, and only after reviewing the difference:

    python tools/bench/golden.py check     # see what moved
    python tools/bench/golden.py record    # accept the new values
"""

import os
import sys
import unittest

_STB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BENCH_DIR = os.path.join(_STB_ROOT, "tools", "bench")
if _STB_ROOT not in sys.path:
    sys.path.insert(0, _STB_ROOT)
if _BENCH_DIR not in sys.path:
    sys.path.insert(0, _BENCH_DIR)

import golden


class TestGoldenResults(unittest.TestCase):

    def test_index_is_present(self):
        self.assertTrue(
            os.path.isfile(golden.INDEX_PATH),
            "golden index missing; run: python tools/bench/golden.py record",
        )
        self.assertGreater(len(golden.read_index()), 0)

    def test_recorded_models_still_match(self):
        models = golden.read_index()
        self.assertGreater(len(models), 0)

        for rel_path in models:
            with self.subTest(model=rel_path):
                self.assertTrue(
                    os.path.isfile(golden.golden_path(rel_path)),
                    "no golden recorded for " + rel_path,
                )
                expected = golden.load_golden(rel_path)
                actual = golden.capture(golden.solve_path(rel_path))
                problems = golden.compare(expected, actual)
                self.assertEqual(
                    problems, [],
                    "results changed for {0}:\n  {1}".format(
                        rel_path, "\n  ".join(problems)
                    ),
                )


if __name__ == "__main__":
    unittest.main()
