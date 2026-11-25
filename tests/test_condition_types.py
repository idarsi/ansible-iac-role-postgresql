"""Check decoded Ansible task condition types, including nested recovery blocks."""

from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("when", "until", "failed_when", "changed_when")
TASK_SECTIONS = (
    "tasks",
    "pre_tasks",
    "post_tasks",
    "handlers",
    "block",
    "rescue",
    "always",
    "roles",
)


def condition_errors(document):
    """Inspect task/play structure without mistaking blueprint data for tasks."""
    errors = []

    def check(value, location, allow_boolean):
        values = value if isinstance(value, list) else [value]
        for index, item in enumerate(values):
            if not (
                isinstance(item, str)
                and bool(item.strip())
                or allow_boolean
                and type(item) is bool
            ):
                errors.append(
                    f"{location}[{index}]: expected a condition string"
                    + (" or intentional native boolean" if allow_boolean else "")
                    + f", got {type(item).__name__}"
                )

    def tasks(records, location):
        if not isinstance(records, list):
            return
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            here = f"{location}[{index}]"
            for key in CONDITIONS:
                if key in record:
                    # Native booleans are supported task conditionals, including
                    # intentional changed_when:false and failed_when:false.
                    check(record[key], f"{here}.{key}", allow_boolean=True)
            for module in ("ansible.builtin.assert", "assert"):
                arguments = record.get(module)
                if isinstance(arguments, dict) and "that" in arguments:
                    # This repository expresses assertions as strings; there
                    # are no intentional constant boolean assertions to exempt.
                    check(
                        arguments["that"], f"{here}.{module}.that", allow_boolean=False
                    )
            for section in TASK_SECTIONS:
                if section in record:
                    tasks(record[section], f"{here}.{section}")

    tasks(document, "document")
    return errors


class ConditionTypesTest(unittest.TestCase):
    def test_all_molecule_task_conditions_are_decoded_strings_or_supported_booleans(
        self,
    ):
        paths = sorted((ROOT / "molecule").rglob("*.yml"))
        paths.append(ROOT / "tests/prepare.yml")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertEqual(condition_errors(yaml.safe_load(path.read_text())), [])

    def test_unquoted_colon_assertion_is_rejected_in_rescue(self):
        document = yaml.safe_load(
            "- hosts: all\n"
            "  tasks:\n"
            "    - block: []\n"
            "      rescue:\n"
            "        - ansible.builtin.assert:\n"
            "            that:\n"
            '              - result is search("Unsupported state: bad")\n'
        )
        errors = condition_errors(document)
        self.assertEqual(len(errors), 1)
        self.assertIn(".rescue[0].ansible.builtin.assert.that[0]", errors[0])
        self.assertIn("got dict", errors[0])

    def test_mapping_malformations_are_rejected_for_all_task_condition_fields(self):
        for key in CONDITIONS:
            for value in ({"unexpected": "mapping"}, [{"unexpected": "mapping"}]):
                with self.subTest(key=key, value=value):
                    errors = condition_errors([{"tasks": [{"always": [{key: value}]}]}])
                    self.assertEqual(len(errors), 1)
                    self.assertIn(f".always[0].{key}[0]", errors[0])

    def test_supported_booleans_and_quoted_colon_strings_are_preserved(self):
        document = [
            {
                "tasks": [
                    {
                        "when": [True, "enabled | bool"],
                        "until": "result is succeeded",
                        "failed_when": False,
                        "changed_when": False,
                        "ansible.builtin.assert": {
                            "that": ['result is search("Unsupported state: bad")'],
                        },
                    }
                ],
                "vars": {
                    "iac_blueprint": {"when": {"not": "an Ansible task condition"}}
                },
            }
        ]
        self.assertEqual(condition_errors(document), [])


if __name__ == "__main__":
    unittest.main()
