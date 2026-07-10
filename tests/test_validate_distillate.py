from __future__ import annotations

import unittest

from scripts.validate_distillate import ValidationError, validate_summary_delta


def summary(*, domains: int, ip_cidrs: int = 0) -> dict[str, object]:
    return {
        "published_categories": [
            {
                "name": "sample",
                "domains": domains,
                "ip_cidrs": ip_cidrs,
                "ip_asns": 0,
            }
        ],
        "aggregates": [],
    }


class SummaryDeltaTests(unittest.TestCase):
    def test_allows_drop_at_boundary(self) -> None:
        validate_summary_delta(summary(domains=100), summary(domains=60))

    def test_rejects_drop_over_boundary(self) -> None:
        with self.assertRaisesRegex(ValidationError, "dropped"):
            validate_summary_delta(summary(domains=100), summary(domains=59))

    def test_allows_growth_at_boundary(self) -> None:
        validate_summary_delta(summary(domains=100), summary(domains=200))

    def test_rejects_growth_over_boundary(self) -> None:
        with self.assertRaisesRegex(ValidationError, "grew"):
            validate_summary_delta(summary(domains=100), summary(domains=201))

    def test_rejects_required_category_becoming_empty(self) -> None:
        with self.assertRaisesRegex(ValidationError, "became empty"):
            validate_summary_delta(summary(domains=100), summary(domains=0))

    def test_large_diff_override_does_not_allow_empty_category(self) -> None:
        with self.assertRaisesRegex(ValidationError, "became empty"):
            validate_summary_delta(summary(domains=100), summary(domains=0), allow_large_diff=True)

    def test_large_diff_override_allows_nonempty_anomaly(self) -> None:
        validate_summary_delta(summary(domains=100), summary(domains=1), allow_large_diff=True)

    def test_rejects_missing_previous_category(self) -> None:
        with self.assertRaisesRegex(ValidationError, "missing"):
            validate_summary_delta(summary(domains=100), {"published_categories": [], "aggregates": []})


if __name__ == "__main__":
    unittest.main()
