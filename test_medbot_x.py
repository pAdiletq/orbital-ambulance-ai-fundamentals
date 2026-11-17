import unittest

from medbot_x import (
    CHARACTERS, SIZE_CHOICES, THEME_NAMES, TOTAL_LEVELS, bayes_free, bfs,
    generate_floor, level_size, mdp_decision, theme_colors, viterbi,
)


class GameAlgorithmsTest(unittest.TestCase):
    def test_bfs_shortest_route(self):
        route = bfs((0, 2), (4, 0), 5, {(1, 0), (1, 1), (3, 1)})
        self.assertEqual(route[0], (0, 2))
        self.assertEqual(route[-1], (4, 0))
        self.assertEqual(len(route) - 1, 6)
        self.assertTrue(all(abs(a[0]-b[0]) + abs(a[1]-b[1]) == 1
                            for a, b in zip(route, route[1:])))

    def test_bayes_hmm_and_mdp(self):
        clear, first, other = bayes_free("CLEAR", .75, .90, .20)
        alert, _, _ = bayes_free("ALERT", .75, .90, .20)
        self.assertAlmostEqual(clear, .675/.725)
        self.assertAlmostEqual(first, .675)
        self.assertAlmostEqual(other, .05)
        self.assertAlmostEqual(alert, .075/.275)
        self.assertEqual(mdp_decision(clear)[0], "CONTINUE")
        self.assertEqual(mdp_decision(alert)[0], "PAUSE")
        sequence, trace = viterbi(("CLEAR", "CLEAR", "CLEAR"), .75, .90, .20)
        self.assertEqual(sequence, ("free", "free", "free"))
        self.assertEqual(len(trace), 3)

    def test_generated_levels_reachable_and_harder(self):
        for size in (5, 20, 100):
            first = generate_floor(size, 1, 99)
            last = generate_floor(size, TOTAL_LEVELS, 99)
            self.assertGreater(len(last.walls), len(first.walls))
            self.assertLess(last.sensitivity, first.sensitivity)
            for floor in (first, last):
                for goal in floor.wards.values():
                    self.assertTrue(bfs(floor.start, goal, size, floor.walls))

    def test_random_size_and_theme_variety(self):
        sequence = [level_size("Random", level, 123) for level in range(1, 31)]
        self.assertTrue(set(sequence) <= set(SIZE_CHOICES))
        self.assertGreater(len(set(sequence)), 1)
        self.assertTrue(all(a != b for a, b in zip(sequence, sequence[1:])))
        self.assertEqual(CHARACTERS, ("Space Ambulance",))
        self.assertEqual(len(THEME_NAMES), 158)
        self.assertEqual(len({theme_colors(i)["accent"] for i in range(1, 159)}), 158)


if __name__ == "__main__":
    unittest.main()
