"""Cheap dependency bootstrap tests; no Galaxy or backend commands execute."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "dependency", Path(__file__).with_name("dependency.py")
)
dependency = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dependency)
ROOT = Path(__file__).resolve().parents[1]


class DependencyTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.ephemeral = Path(self.temporary.name)
        self.destination = self.ephemeral / "collections"
        helper = self.ephemeral / "helper"
        helper.mkdir()
        self.argv = [
            "--scenario-directory",
            str(ROOT / "molecule/kvm-replication"),
            "--ephemeral-directory",
            str(self.ephemeral),
            "--molecule-file",
            str(self.ephemeral / "molecule.yml"),
            "--env-file",
            "None",
            "--helper-directory",
            str(helper),
        ]
        self.context = {
            "schema": "idarsi.scenario-context/v1",
            "effective_config_validated": True,
            "lifecycle_modes": ["direct", "supervised"],
            "role": str(ROOT),
            "scenario": "kvm-replication",
            "backend": "kvm",
            "mode": "direct",
            "ephemeral_directory": str(self.ephemeral),
            "collections_directory": str(self.destination),
            "generation": None,
        }
        self.environment = patch.dict(
            os.environ,
            {
                "MOLECULE_SCENARIO_NAME": "kvm-replication",
                "IDARSI_TEST_ENVIRONMENT": str(self.ephemeral / "helper"),
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def runner(self):
        def run(command, **kwargs):
            if command[0] == "ansible-galaxy":
                manifest = Path(command[command.index("-r") + 1])
                for record in dependency.required_collections(manifest):
                    namespace, name = record["name"].split(".")
                    directory = (
                        self.destination / "ansible_collections" / namespace / name
                    )
                    directory.mkdir(parents=True, exist_ok=True)
                    (directory / "MANIFEST.json").write_text(
                        json.dumps(
                            {
                                "collection_info": {
                                    "namespace": namespace,
                                    "name": name,
                                    "version": record["version"],
                                }
                            }
                        )
                    )
                    (directory / "FILES.json").write_text("{}")
            return subprocess.CompletedProcess(
                command, 0, stdout=json.dumps(self.context)
            )

        return patch.object(
            dependency.subprocess,
            "run",
            side_effect=run,
        )

    def test_resolve_before_private_install_without_generation_allocation(self):
        with self.runner() as run:
            dependency.main(self.argv)
        calls = [call.args[0] for call in run.call_args_list]
        self.assertEqual(calls[0][1], "resolve")
        self.assertNotIn("init", calls[0])
        helper_env = run.call_args_list[0].kwargs["env"]
        self.assertEqual(helper_env["MOLECULE_SCENARIO_NAME"], "kvm-replication")
        self.assertEqual(
            helper_env["MOLECULE_EPHEMERAL_DIRECTORY"], str(self.ephemeral)
        )
        self.assertEqual(len(calls), 3)
        for command in calls[1:]:
            self.assertEqual(command[:3], ["ansible-galaxy", "collection", "install"])
            self.assertEqual(command[-2:], ["-p", str(self.destination)])
        self.assertTrue((self.destination / ".postgresql-galaxy.lock").is_file())

    def test_invalid_contract_cannot_install(self):
        for key, value in (
            ("schema", "unknown"),
            ("effective_config_validated", False),
            ("lifecycle_modes", ["supervised"]),
            ("scenario", "another"),
            ("backend", "podman"),
            ("mode", "legacy"),
            ("collections_directory", str(self.ephemeral / "foreign")),
        ):
            with self.subTest(key=key):
                original = self.context[key]
                self.context[key] = value
                with self.runner() as run, self.assertRaises(ValueError):
                    dependency.main(self.argv)
                self.assertEqual(run.call_count, 1)
                self.context[key] = original

    def test_helper_rejection_cannot_install_or_fall_back(self):
        with patch.object(
            dependency.subprocess,
            "run",
            side_effect=subprocess.CalledProcessError(1, ["scenario-context"]),
        ) as run, self.assertRaises(subprocess.CalledProcessError):
            dependency.main(self.argv)
        self.assertEqual(run.call_count, 1)
        self.assertFalse(self.destination.exists())

    def test_symlink_destination_is_rejected_before_install(self):
        foreign = self.ephemeral / "foreign"
        foreign.mkdir()
        self.destination.symlink_to(foreign, target_is_directory=True)
        with self.runner() as run, self.assertRaises(ValueError):
            dependency.main(self.argv)
        self.assertEqual(run.call_count, 1)

    def test_other_writable_destination_is_rejected(self):
        self.destination.mkdir(mode=0o777)
        self.destination.chmod(0o777)
        with self.runner() as run, self.assertRaises(ValueError):
            dependency.main(self.argv)
        self.assertEqual(run.call_count, 1)

    def test_unsafe_lock_is_rejected(self):
        self.destination.mkdir(mode=0o700)
        lock = self.destination / ".postgresql-galaxy.lock"
        lock.touch(mode=0o666)
        lock.chmod(0o666)
        with self.runner() as run, self.assertRaises(ValueError):
            dependency.main(self.argv)
        self.assertEqual(run.call_count, 1)

    def test_explicit_binding_works_without_computed_environment(self):
        with patch.dict(os.environ), self.runner() as run:
            os.environ.pop("MOLECULE_SCENARIO_NAME", None)
            dependency.main(self.argv)
        self.assertEqual(run.call_count, 3)

    def test_conflicting_inherited_binding_is_not_overwritten(self):
        with patch.dict(os.environ, {"MOLECULE_SCENARIO_NAME": "another"}):
            with self.runner() as run, self.assertRaises(ValueError):
                dependency.main(self.argv)
        run.assert_not_called()

    def test_genuine_handoff_is_inherited_unchanged(self):
        self.context["mode"] = "supervised"
        markers = {"IDARSI_RUN_ID": "fixture-run", "IDARSI_HANDOFF": "v1"}
        with patch.dict(os.environ, markers), self.runner() as run:
            dependency.main(self.argv)
        helper_env = run.call_args_list[0].kwargs["env"]
        for key, value in markers.items():
            self.assertEqual(helper_env[key], value)
            self.assertEqual(run.call_args_list[1].kwargs["env"][key], value)

    def test_supervised_markers_cannot_accept_direct_response(self):
        with patch.dict(os.environ, {"IDARSI_HANDOFF": ""}):
            with self.runner() as run, self.assertRaises(ValueError):
                dependency.main(self.argv)
        self.assertEqual(run.call_count, 1)

    def test_response_ephemeral_must_match_explicit_effective_binding(self):
        self.context["ephemeral_directory"] = str(self.ephemeral / "foreign")
        self.context["collections_directory"] = str(
            self.ephemeral / "foreign/collections"
        )
        with self.runner() as run, self.assertRaises(ValueError):
            dependency.main(self.argv)
        self.assertEqual(run.call_count, 1)

    def test_cli_scenario_and_cached_file_cannot_escape_context(self):
        for flag, value in (
            ("--scenario-directory", str(self.ephemeral)),
            ("--molecule-file", str(self.ephemeral.parent / "foreign.yml")),
        ):
            argv = list(self.argv)
            argv[argv.index(flag) + 1] = value
            with self.subTest(flag=flag), self.runner() as run:
                with self.assertRaises(ValueError):
                    dependency.main(argv)
            run.assert_not_called()

    def test_installer_discovery_is_strictly_private_without_changing_parent(self):
        inherited = {
            "ANSIBLE_COLLECTIONS_PATH": "/external/collections",
            "ANSIBLE_COLLECTIONS_PATHS": "/obsolete/external",
            "ANSIBLE_COLLECTIONS_SCAN_SYS_PATH": "true",
        }
        with patch.dict(os.environ, inherited), self.runner() as run:
            dependency.main(self.argv)
            self.assertEqual(
                os.environ["ANSIBLE_COLLECTIONS_PATH"],
                inherited["ANSIBLE_COLLECTIONS_PATH"],
            )
        for call in run.call_args_list[1:]:
            child = call.kwargs["env"]
            self.assertEqual(child["ANSIBLE_COLLECTIONS_PATH"], str(self.destination))
            self.assertEqual(child["ANSIBLE_COLLECTIONS_SCAN_SYS_PATH"], "false")
            self.assertNotIn("ANSIBLE_COLLECTIONS_PATHS", child)

    def test_successful_noop_installer_cannot_claim_private_installation(self):
        with patch.object(
            dependency.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                [], 0, stdout=json.dumps(self.context)
            ),
        ), self.assertRaisesRegex(ValueError, "Private collection"):
            dependency.main(self.argv)


if __name__ == "__main__":
    unittest.main()
