import json
import unittest
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from boundarybench import (
    ScenarioValidationError,
    load_scenario,
    negative_control_variant,
    parse_scenario,
)


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

    def test_every_corpus_scenario_matches_the_published_json_schema(self):
        schema = json.loads(Path("schemas/scenario.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        for path in sorted(Path("scenarios").rglob("*.yaml")):
            with self.subTest(path=path):
                document = yaml.safe_load(path.read_text(encoding="utf-8"))
                errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
                self.assertEqual(errors, [])

    def test_every_corpus_scenario_builds_a_clean_negative_control(self):
        files = sorted(Path("scenarios").rglob("*.yaml"))
        self.assertEqual(len(files), 11)
        for path in files:
            with self.subTest(path=path):
                scenario = load_scenario(path)
                control = negative_control_variant(scenario)
                self.assertEqual(control.id, f"{scenario.id}-NC")
                self.assertEqual(control.metadata["parent_scenario"], scenario.id)
                self.assertIsNone(control.negative_control)

    def test_archive_negative_control_removes_traversal_member(self):
        scenario = load_scenario("scenarios/filesystem/BB-FS-003-archive-traversal.yaml")
        control = negative_control_variant(scenario)
        files = control.fixture["resources"][0]["state"]["files"]
        archive = next(item for item in files if item["path"].endswith("input.tar"))
        self.assertEqual(
            [member["name"] for member in archive["archive_members"]],
            ["docs/readme.txt", "docs/notes.txt"],
        )
