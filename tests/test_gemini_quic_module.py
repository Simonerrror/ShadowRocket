from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE = REPO_ROOT / "modules" / "gemini_quic_reject.module"
GEMINI_SOURCE = REPO_ROOT / "distillate" / "text" / "domain" / "gemini.txt"
MODULE_URL = (
    "https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/"
    "modules/gemini_quic_reject.module"
)

REQUIRED_MATCHERS = {
    ("DOMAIN", "ai.google.dev"),
    ("DOMAIN", "alkalimakersuite-pa.clients6.google.com"),
    ("DOMAIN", "makersuite.google.com"),
    ("DOMAIN-SUFFIX", "bard.google.com"),
    ("DOMAIN-SUFFIX", "deepmind.com"),
    ("DOMAIN-SUFFIX", "deepmind.google"),
    ("DOMAIN-SUFFIX", "gemini.google.com"),
    ("DOMAIN-SUFFIX", "generativeai.google"),
    ("DOMAIN-SUFFIX", "proactivebackend-pa.googleapis.com"),
    ("DOMAIN-KEYWORD", "generativelanguage"),
}

SOURCE_PREFIXES = {
    "full": "DOMAIN",
    "domain": "DOMAIN-SUFFIX",
    "keyword": "DOMAIN-KEYWORD",
}


def section_lines(path: Path, section: str) -> list[str]:
    lines: list[str] = []
    in_section = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == f"[{section}]":
            in_section = True
            continue
        if in_section and line.startswith("[") and line.endswith("]"):
            break
        if in_section and line and not line.startswith("#"):
            lines.append(line)
    return lines


def source_matchers() -> set[tuple[str, str]]:
    matchers: set[tuple[str, str]] = set()
    for raw_line in GEMINI_SOURCE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        prefix, value = line.split(":", 1)
        if prefix in SOURCE_PREFIXES:
            matchers.add((SOURCE_PREFIXES[prefix], value))
    return matchers


def parse_and_rule(rule: str) -> tuple[tuple[str, str], tuple[str, str], tuple[str, str], str]:
    match = re.fullmatch(
        r"AND,\(\(([^(),]+),([^()]+)\),\(([^(),]+),([^()]+)\),\(([^(),]+),([^()]+)\)\),([^,]+)",
        rule,
    )
    if match is None:
        raise AssertionError(f"not an AND rule with exactly three matchers: {rule}")
    matcher_values = match.groups()
    return (
        (matcher_values[0], matcher_values[1]),
        (matcher_values[2], matcher_values[3]),
        (matcher_values[4], matcher_values[5]),
        matcher_values[6],
    )


class GeminiQuicModuleTests(unittest.TestCase):
    def test_module_metadata_and_rules_match_gemini_quic_contract(self) -> None:
        self.assertTrue(MODULE.is_file(), f"missing module: {MODULE}")
        content = MODULE.read_text(encoding="utf-8")
        lines = content.splitlines()
        rules = section_lines(MODULE, "Rule")

        self.assertIn(f"#!url={MODULE_URL}", lines)
        self.assertRegex(content, r"(?m)^#!name=.*[А-Яа-яЁё].*$")
        self.assertRegex(content, r"(?m)^#!desc=.*[А-Яа-яЁё].*$")
        self.assertGreaterEqual(len(rules), len(REQUIRED_MATCHERS))

        parsed_rules = [parse_and_rule(rule) for rule in rules]
        actual_matchers: set[tuple[str, str]] = set()
        for index, (first, second, third, policy) in enumerate(parsed_rules):
            rule = rules[index]
            self.assertEqual("REJECT-NO-DROP", policy, msg=rule)
            matchers = (first, second, third)
            domain_matchers = [matcher for matcher in matchers if matcher[0] in SOURCE_PREFIXES.values()]
            self.assertEqual(1, len(domain_matchers), msg=rule)
            self.assertEqual(("PROTOCOL", "UDP"), first, msg=rule)
            self.assertEqual(("DEST-PORT", "443"), second, msg=rule)
            self.assertEqual(domain_matchers[0], third, msg=rule)
            self.assertEqual(3, len(set(matchers)), msg=rule)
            actual_matchers.add(domain_matchers[0])

        self.assertTrue(REQUIRED_MATCHERS.issubset(actual_matchers))
        self.assertTrue(actual_matchers.issubset(REQUIRED_MATCHERS))
        self.assertTrue(actual_matchers.issubset(source_matchers()))

        forbidden = (
            ("DOMAIN", "google.com"),
            ("DOMAIN-SUFFIX", "google.com"),
            ("DOMAIN-KEYWORD", "google"),
            ("DOMAIN-SUFFIX", "youtube.com"),
            ("DOMAIN-KEYWORD", "youtube"),
            ("DOMAIN-KEYWORD", "colab"),
            ("DOMAIN-KEYWORD", "developerprofiles"),
        )
        self.assertTrue(actual_matchers.isdisjoint(forbidden))

        for rule in rules:
            self.assertNotIn("RULE-SET", rule)
            self.assertNotIn("PROTOCOL,UDP),REJECT-NO-DROP", rule)
            self.assertNotIn("DEST-PORT,443),REJECT-NO-DROP", rule)


if __name__ == "__main__":
    unittest.main()
