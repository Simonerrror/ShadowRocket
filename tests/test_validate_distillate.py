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
    def test_enforces_growth_and_drop_boundaries(self) -> None:
        for domains in (60, 200):
            with self.subTest(domains=domains):
                validate_summary_delta(summary(domains=100), summary(domains=domains))
        for domains, message in ((59, "dropped"), (201, "grew")):
            with self.subTest(domains=domains):
                with self.assertRaisesRegex(ValidationError, message):
                    validate_summary_delta(summary(domains=100), summary(domains=domains))

    def test_large_diff_override_never_allows_empty_category(self) -> None:
        validate_summary_delta(summary(domains=100), summary(domains=1), allow_large_diff=True)
        for allow_large_diff in (False, True):
            with self.subTest(allow_large_diff=allow_large_diff):
                with self.assertRaisesRegex(ValidationError, "became empty"):
                    validate_summary_delta(
                        summary(domains=100),
                        summary(domains=0),
                        allow_large_diff=allow_large_diff,
                    )

    def test_rejects_missing_previous_category(self) -> None:
        with self.assertRaisesRegex(ValidationError, "missing"):
            validate_summary_delta(summary(domains=100), {"published_categories": [], "aggregates": []})


if __name__ == "__main__":
    unittest.main()
