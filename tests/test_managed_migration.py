"""Repository-owned managed matrix checks without infrastructure or the TUI."""

import json
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
LANES = {"ansible-min", "ansible-current", "ansible-next"}


class ManagedMigrationTest(unittest.TestCase):
    def test_logical_names_match_shared_native_helper_contract(self):
        # Shared isolated_runs/backends.py validate_platforms: alphabetic
        # start, safe inventory characters, maximum 40 characters. This checks
        # declared logical names, not generated physical backend identities.
        for path in ROOT.glob("molecule/*/molecule.yml"):
            config = yaml.safe_load(path.read_text())
            for platform in config["platforms"]:
                with self.subTest(scenario=path.parent.name, name=platform["name"]):
                    self.assertRegex(
                        platform["name"], r"\A[a-zA-Z][a-zA-Z0-9_-]{0,39}\Z"
                    )

    def test_complete_matrix_uses_whole_topologies(self):
        metadata = json.loads((ROOT / "role-test.json").read_text())
        scenarios = {
            path.parent.name: yaml.safe_load(path.read_text())
            for path in ROOT.glob("molecule/*/molecule.yml")
        }
        self.assertEqual(metadata["schema_version"], 1)
        self.assertEqual(len(scenarios), 25)
        self.assertEqual(set(metadata["scenarios"]), set(scenarios))
        for scenario, config in scenarios.items():
            with self.subTest(scenario=scenario):
                entry = metadata["scenarios"][scenario]
                backend = "podman" if scenario == "podman-validation" else "kvm"
                self.assertEqual(
                    entry["execution"],
                    {"backend": backend, "min_ansible_core": "2.19"},
                )
                self.assertEqual(set(entry["environments"]), LANES)
                minimum = entry["environments"]["ansible-min"]
                self.assertEqual(set(minimum), {"unsupported_reason"})
                self.assertIn("2.19.12", minimum["unsupported_reason"])
                platforms = [platform["name"] for platform in config["platforms"]]
                for lane in ("ansible-current", "ansible-next"):
                    self.assertEqual(
                        entry["environments"][lane], {"platforms": platforms}
                    )
                self.assertEqual(config["driver"]["name"], "default")
                self.assertIs(config["driver"]["options"]["managed"], True)
                self.assertEqual(
                    config["driver"]["safe_files"],
                    ["${MOLECULE_EPHEMERAL_DIRECTORY}/collections/*"],
                )
                self.assertEqual(config["dependency"]["name"], "shell")
                self.assertEqual(
                    config["dependency"]["command"],
                    'python3 "${MOLECULE_PROJECT_DIRECTORY}/tests/dependency.py" '
                    '--scenario-directory "${MOLECULE_SCENARIO_DIRECTORY}" '
                    '--ephemeral-directory "${MOLECULE_EPHEMERAL_DIRECTORY}" '
                    '--molecule-file "${MOLECULE_FILE}" '
                    '--env-file "${MOLECULE_ENV_FILE}" '
                    '--helper-directory "${IDARSI_TEST_ENVIRONMENT}"',
                )
                self.assertNotIn("test_sequence", config.get("scenario", {}))
                env = config["provisioner"]["env"]
                self.assertEqual(env["IDARSI_MOLECULE_BACKEND"], backend)
                self.assertEqual(
                    env["ANSIBLE_COLLECTIONS_PATH"],
                    "${MOLECULE_EPHEMERAL_DIRECTORY}/collections",
                )
                for action in ("create", "destroy"):
                    self.assertEqual(
                        config["provisioner"]["playbooks"][action],
                        "${IDARSI_TEST_ENVIRONMENT}/molecule/managed/"
                        + action
                        + ".yml",
                    )
                for platform in config["platforms"]:
                    for forbidden in (
                        "privileged",
                        "volumes",
                        "network",
                        "published_ports",
                        "ipv4_address",
                        "libvirt_uri",
                        "cap_add",
                    ):
                        self.assertNotIn(forbidden, platform)
                if backend == "podman":
                    self.assertEqual(
                        config["platforms"][0]["command"], ["sleep", "infinity"]
                    )

    def test_consolidated_os_playbooks_keep_separate_targeting(self):
        variants = {
            "kvm-full": {
                "rocky9": "instance-idarsi-rl9",
                "rhel9": "instance-idarsi-rhel9",
            },
            "kvm-baseline": {
                "rocky10": "instance-idarsi-rl10",
                "rhel10": "instance-idarsi-rhel10",
                "fedora43": "instance-idarsi-fedora43",
                "fedora44": "instance-idarsi-fedora44",
            },
        }
        for scenario, targets in variants.items():
            directory = ROOT / "molecule" / scenario
            for phase in ("converge", "verify"):
                imports = yaml.safe_load((directory / f"{phase}.yml").read_text())
                self.assertEqual(len(imports), len(targets))
                for variant, target in targets.items():
                    name = f"{variant}-{phase}.yml"
                    self.assertIn(
                        name,
                        [play["ansible.builtin.import_playbook"] for play in imports],
                    )
                    plays = yaml.safe_load((directory / name).read_text())
                    self.assertTrue(plays)
                    self.assertTrue(all(play["hosts"] == target for play in plays))

    def test_multihost_resources_remain_indivisible(self):
        metadata = json.loads((ROOT / "role-test.json").read_text())["scenarios"]
        expected = {
            "kvm-full": 2,
            "kvm-baseline": 4,
            "kvm-replication": 2,
            "kvm-timescaledb": 8,
            "kvm-patroni-membership": 6,
            "kvm-patroni-failover": 6,
        }
        for scenario, count in expected.items():
            self.assertEqual(
                len(metadata[scenario]["environments"]["ansible-current"]["platforms"]),
                count,
            )


if __name__ == "__main__":
    unittest.main()
