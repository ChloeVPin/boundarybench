import json
import unittest
from pathlib import Path

from boundarybench import ScenarioValidationError, parse_scenario


class ScenarioParsingTests(unittest.TestCase):
    def test_parses_yaml_and_preserves_extensions(self):
        scenario = parse_scenario(
            """
version: '0.1'
id: read-fixture
task:
  kind: summarize
policy:
  allow:
    read:
      - fixtures/input.txt
  deny:
    read:
      - fixtures/secret.txt
experiment:
  cohort: synthetic
"""
        )
        self.assertEqual(scenario.version, "0.1")
        self.assertEqual(scenario.policy.decide("read", "fixtures/input.txt").allowed, True)
        self.assertEqual(scenario.task["kind"], "summarize")
        self.assertEqual(scenario.extensions["experiment"]["cohort"], "synthetic")

    def test_reports_multiple_malformed_fields(self):
        with self.assertRaises(ScenarioValidationError) as raised:
            parse_scenario("version: '0.2'\nid: ''\npolicy: []\n")
        paths = {issue.path for issue in raised.exception.issues}
        self.assertTrue({"version", "id", "policy"}.issubset(paths))

    def test_rejects_traversal_and_absolute_paths(self):
        for target in ("../secret.txt", "data/../../secret.txt", "/etc/passwd", "C:/secret.txt"):
            with self.subTest(target=target):
                with self.assertRaises(ScenarioValidationError) as raised:
                    parse_scenario(
                        {
                            "version": "0.1",
                            "id": "unsafe-path",
                            "policy": {"allow": {"read": [target]}},
                        }
                    )
                self.assertTrue(any("targets" in issue.path for issue in raised.exception.issues))

    def test_published_json_schema_is_machine_readable(self):
        schema = json.loads(Path("schemas/scenario.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIn("authority", schema["$defs"])
        self.assertIn("policy", schema["$defs"])
