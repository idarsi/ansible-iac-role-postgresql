"""Keep hosted static checks supplied with isolated, pinned Galaxy collections."""

import ast
from pathlib import Path
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class StaticCiTest(unittest.TestCase):
    def setUp(self):
        self.workflow = yaml.safe_load(
            (ROOT / ".github/workflows/tests.yml").read_text()
        )
        self.job = self.workflow["jobs"]["static"]
        self.steps = self.job["steps"]
        self.bootstrap = next(
            step for step in self.steps if step.get("id") == "static-collections"
        )

    def test_workflow_is_hosted_static_only_without_backend_jobs_or_environments(self):
        self.assertEqual(set(self.workflow["jobs"]), {"static"})
        self.assertEqual(self.job["runs-on"], "ubuntu-latest")
        for key in ("environment", "strategy", "container", "services"):
            self.assertNotIn(key, self.job)
        # PyYAML's YAML 1.1 loader may decode the GitHub `on` key as True.
        triggers = self.workflow.get("on", self.workflow.get(True))
        self.assertEqual(set(triggers), {"workflow_dispatch", "pull_request", "push"})
        for step in self.steps:
            self.assertNotIn("environment", step)
            self.assertNotRegex(
                step.get("run", ""),
                r"\b(?:scripts/test-run|scenario-context|virsh|virt-install|vagrant|podman)\b",
            )
            self.assertNotRegex(
                step.get("run", ""),
                r"\bmolecule\s+(?:test|create|prepare|converge|verify|destroy)\b",
            )
        self.assertTrue(
            any(
                step.get("run") == "python -m unittest discover -s tests -p 'test_*.py'"
                for step in self.steps
            )
        )

    def test_static_collection_search_is_private_for_install_lint_and_syntax(self):
        self.assertEqual(
            self.job["env"]["ANSIBLE_COLLECTIONS_PATH"],
            "${{ runner.temp }}/postgresql-static-collections",
        )
        self.assertEqual(self.job["env"]["ANSIBLE_COLLECTIONS_SCAN_SYS_PATH"], "false")
        self.assertNotIn("ANSIBLE_COLLECTIONS_PATHS", self.job["env"])
        for step in self.steps:
            for key in (
                "ANSIBLE_COLLECTIONS_PATH",
                "ANSIBLE_COLLECTIONS_SCAN_SYS_PATH",
            ):
                self.assertNotIn(key, step.get("env", {}))

    def test_pinned_manifest_bootstrap_precedes_static_consumers(self):
        tools = next(
            index
            for index, step in enumerate(self.steps)
            if "pip install -r requirements-ci.txt" in step.get("run", "")
        )
        bootstrap = self.steps.index(self.bootstrap)
        self.assertLess(tools, bootstrap)
        for command in (
            "python -m unittest discover",
            "ansible-lint --profile production",
            "ansible-playbook --syntax-check",
        ):
            consumer = next(
                index
                for index, step in enumerate(self.steps)
                if command in step.get("run", "")
            )
            self.assertLess(bootstrap, consumer)
        script = self.bootstrap["run"]
        self.assertIn(
            "ansible-galaxy collection install -r tests/collections.yml "
            '-p "$ANSIBLE_COLLECTIONS_PATH"',
            script,
        )
        self.assertNotIn("-r collections.yml", script)
        records = yaml.safe_load((ROOT / "tests/collections.yml").read_text())[
            "collections"
        ]
        self.assertEqual(
            {record["name"] for record in records},
            {"ansible.posix", "containers.podman"},
        )
        for record in records:
            self.assertRegex(record["version"], r"\A\d+\.\d+\.\d+\Z")

    def test_bootstrap_has_valid_shell_and_uses_physical_pin_verification(self):
        script = self.bootstrap["run"]
        self.assertIn("set -euo pipefail", script)
        self.assertIn('install -d -m 0700 "$ANSIBLE_COLLECTIONS_PATH"', script)
        result = subprocess.run(
            ["bash", "-n"],
            input=script,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        python = script.split("PYTHONPATH=tests python - <<'PY'\n", 1)[1].rsplit(
            "\nPY", 1
        )[0]
        tree = ast.parse(python)
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module == "dependency"
            for alias in node.names
        }
        self.assertEqual(
            imported, {"required_collections", "verify_private_collection"}
        )
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(imported <= called)
        self.assertNotIn("scenario-context", script)
        self.assertNotIn("molecule ", script)

    def test_lint_keeps_prepare_and_unknown_module_guard_in_scope(self):
        config = yaml.safe_load((ROOT / ".ansible-lint").read_text())
        exclusions = config.get("exclude_paths", [])
        self.assertNotIn("tests/", exclusions)
        self.assertNotIn("tests/prepare.yml", exclusions)
        self.assertFalse(
            any("syntax-check" in rule for rule in config.get("skip_list", []))
        )
        self.assertTrue(
            any(
                step.get("run") == "ansible-lint --profile production"
                for step in self.steps
            )
        )


if __name__ == "__main__":
    unittest.main()
