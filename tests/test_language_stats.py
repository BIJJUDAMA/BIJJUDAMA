import math
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(".github/scripts"))

from language_stats import (
    aggregate_repo_languages,
    build_donut_segments,
    calculate_percentages,
    deduplicate_repositories,
    sort_languages,
)


def repo(repo_id, stars=0, commits=0, edges=None):
    return {
        "id": repo_id,
        "nameWithOwner": f"BIJJUDAMA/{repo_id}",
        "isPrivate": False,
        "stargazerCount": stars,
        "defaultBranchRef": {"target": {"history": {"totalCount": commits}}},
        "languages": {"edges": edges or []},
    }


def edge(name, size, color="#000000"):
    return {"size": size, "node": {"name": name, "color": color}}


class LanguageStatsTests(unittest.TestCase):
    def test_aggregate_across_multiple_repositories(self):
        repos = [
            repo("r1", edges=[edge("Python", 100), edge("Go", 50)]),
            repo("r2", edges=[edge("Python", 25), edge("TypeScript", 75)]),
        ]
        sizes, _ = aggregate_repo_languages(repos)
        self.assertEqual(sizes["Python"], 125)
        self.assertEqual(sizes["Go"], 50)
        self.assertEqual(sizes["TypeScript"], 75)

    def test_pagination_duplicate_repositories_counted_once(self):
        duplicated = repo("r1", edges=[edge("Python", 100), edge("Go", 50)])
        repos = [duplicated, duplicated, repo("r2", edges=[edge("Go", 25)])]
        sizes, _ = aggregate_repo_languages(repos)
        self.assertEqual(sizes["Python"], 100)
        self.assertEqual(sizes["Go"], 75)
        self.assertEqual(len(deduplicate_repositories(repos)), 2)

    def test_percentage_normalization_uses_total_language_bytes(self):
        entries = [("Python", 300), ("Go", 100), ("Jupyter Notebook", 100)]
        percentages = calculate_percentages(entries, total_value=500)
        self.assertAlmostEqual(percentages["Python"], 60.0)
        self.assertAlmostEqual(percentages["Go"], 20.0)
        self.assertAlmostEqual(percentages["Jupyter Notebook"], 20.0)

    def test_deterministic_top_five_sorting(self):
        language_values = {
            "Rust": 10,
            "go": 20,
            "Python": 20,
            "C": 5,
            "Zig": 2,
            "JavaScript": 20,
        }
        top = sort_languages(language_values, limit=5)
        self.assertEqual(
            [name for name, _ in top],
            ["go", "JavaScript", "Python", "Rust", "C"],
        )

    def test_empty_and_zero_total_cases(self):
        sizes, _ = aggregate_repo_languages([repo("r1", edges=[])])
        self.assertEqual(sizes, {})
        percentages = calculate_percentages([("Python", 0)], total_value=0)
        self.assertEqual(percentages["Python"], 0.0)

    def test_displayed_percentages_match_chart_segments(self):
        data = [("Python", 60), ("Go", 40)]
        segments = build_donut_segments(data, total_value=100)
        for name, value, pct, angle in segments:
            self.assertAlmostEqual(angle, pct * 3.6)
            self.assertEqual(value, dict(data)[name])

    def test_percentages_sum_to_approximately_100_before_rounding(self):
        repos = [
            repo("r1", edges=[edge("Python", 333), edge("Go", 333)]),
            repo("r2", edges=[edge("Jupyter Notebook", 334)]),
        ]
        sizes, _ = aggregate_repo_languages(repos)
        sorted_entries = sort_languages(sizes, limit=len(sizes))
        percentages = calculate_percentages(sorted_entries, total_value=sum(sizes.values()))
        self.assertTrue(math.isclose(sum(percentages.values()), 100.0, rel_tol=0, abs_tol=1e-9))


if __name__ == "__main__":
    unittest.main()
