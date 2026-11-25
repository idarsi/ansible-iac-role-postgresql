"""Evaluate helper-result guards with fake results, without commands or guests."""

import json
from pathlib import Path
import unittest

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "molecule/kvm-hard-patroni-failure"


class GuestControlDiagnosticsTest(unittest.TestCase):
    def setUp(self):
        self.tasks = yaml.safe_load((SCENARIO / "helper_result.yml").read_text())
        self.environment = Environment(undefined=StrictUndefined)
        self.parse_calls = 0

        def from_json(value):
            self.parse_calls += 1
            return json.loads(value)

        self.environment.filters["from_json"] = from_json

    def assert_task(self, task, variables):
        arguments = task["ansible.builtin.assert"]
        for condition in arguments["that"]:
            if not self.environment.compile_expression(condition)(**variables):
                return self.environment.from_string(arguments["fail_msg"]).render(
                    **variables
                )
        return None

    def validate(self, result):
        variables = {
            "kvm_helper_action": "guest-stop",
            "kvm_helper_result": result,
        }
        error = self.assert_task(self.tasks[0], variables)
        if error:
            return error
        decode = self.tasks[1]
        expression = decode["block"][0]["ansible.builtin.set_fact"][
            "kvm_helper_payload"
        ]
        try:
            variables["kvm_helper_payload"] = self.environment.compile_expression(
                expression.removeprefix("{{").removesuffix("}}").strip()
            )(**variables)
        except (ValueError, TypeError):
            message = decode["rescue"][0]["ansible.builtin.fail"]["msg"]
            return self.environment.from_string(message).render(**variables)
        return self.assert_task(self.tasks[2], variables)

    def test_nonzero_rc_preserves_stderr_without_attempting_json(self):
        for stdout in ("", "not JSON", '{"schema":"idarsi.scenario-context/v1"}'):
            with self.subTest(stdout=stdout):
                message = self.validate(
                    {
                        "rc": 1,
                        "stdout": stdout,
                        "stderr": "Effective scenario configuration changed; retain owned context",
                    }
                )
                self.assertIn("rc=1", message)
                self.assertIn("Effective scenario configuration changed", message)
                self.assertIn("guest-stop", message)
                self.assertEqual(self.parse_calls, 0)

    def test_empty_success_stdout_fails_before_decoding(self):
        for result in (
            {"rc": 0, "stdout": "", "stderr": "Empty response diagnostic"},
            {"rc": 0, "stdout": " \n", "stderr": "Empty response diagnostic"},
            {"rc": 0, "stderr": "Empty response diagnostic"},
        ):
            with self.subTest(result=result):
                message = self.validate(result)
                self.assertIn("empty stdout", message)
                self.assertIn("Empty response diagnostic", message)
                self.assertEqual(self.parse_calls, 0)

    def test_invalid_json_preserves_helper_diagnostic(self):
        message = self.validate(
            {
                "rc": 0,
                "stdout": "not JSON",
                "stderr": "Original helper warning",
            }
        )
        self.assertIn("invalid JSON", message)
        self.assertIn("Original helper warning", message)
        self.assertEqual(self.parse_calls, 1)

    def test_missing_stderr_uses_command_diagnostic_without_json_parse(self):
        for stderr in ("", None):
            with self.subTest(stderr=stderr):
                message = self.validate(
                    {
                        "rc": 1,
                        "stdout": "",
                        "stderr": stderr,
                        "msg": "Unable to execute the pinned helper",
                    }
                )
                self.assertIn("Unable to execute the pinned helper", message)
                self.assertEqual(self.parse_calls, 0)

    def test_valid_success_and_invalid_envelopes(self):
        self.assertIsNone(
            self.validate(
                {
                    "rc": 0,
                    "stdout": json.dumps({"schema": "idarsi.scenario-context/v1"}),
                    "stderr": "",
                }
            )
        )
        for payload in ([], {}, {"schema": "unknown"}):
            with self.subTest(payload=payload):
                message = self.validate(
                    {
                        "rc": 0,
                        "stdout": json.dumps(payload),
                        "stderr": "Envelope diagnostic",
                    }
                )
                self.assertIn("invalid response envelope", message)
                self.assertIn("Envelope diagnostic", message)

    def test_all_helper_results_are_guarded_before_protocol_or_changed_decoding(self):
        play = yaml.safe_load((SCENARIO / "verify.yml").read_text())[0]
        probe, probe_guard, probe_assert = play["tasks"][:3]
        self.assertEqual(probe["register"], "kvm_guest_control")
        self.assertIs(probe["changed_when"], False)
        self.assertIs(probe["failed_when"], False)
        self.assertEqual(
            probe_guard["ansible.builtin.include_tasks"], "helper_result.yml"
        )
        self.assertEqual(probe_guard["loop"], "{{ kvm_guest_control.results }}")
        self.assertIn("ansible.builtin.assert", probe_assert)
        disruption = next(task for task in play["tasks"] if "always" in task)
        for section, result in (
            ("block", "kvm_guest_stopped"),
            ("always", "kvm_guest_started"),
        ):
            tasks = disruption[section]
            command, guard, assertion = tasks[:3]
            self.assertEqual(command["register"], result)
            self.assertIs(command["changed_when"], False)
            self.assertIs(command["failed_when"], False)
            self.assertEqual(
                guard["ansible.builtin.include_tasks"], "helper_result.yml"
            )
            self.assertEqual(guard["vars"]["kvm_helper_result"], "{{ " + result + " }}")
            self.assertIn("ansible.builtin.assert", assertion)
            self.assertIn("from_json", assertion["changed_when"])


if __name__ == "__main__":
    unittest.main()
