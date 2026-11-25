"""Guard the managed contract of the nine combined-cluster KVM scenarios."""

from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = (
    "kvm-combined-patroni-failover",
    "kvm-etcd-quorum",
    "kvm-etcd-leader-failure",
    "kvm-hard-patroni-failure",
    "kvm-network-partition",
    "kvm-quorum-primary-failure",
    "kvm-restart-smoke",
    "kvm-tls-rotation",
    "kvm-etcd-snapshot-restore",
)
GUESTS = ["pg01", "pg02", "pg03"]


def tasks_in(tasks: list) -> list:
    """Flatten block recovery as well as normal tasks for structural assertions."""
    result = []
    for task in tasks:
        result.append(task)
        for section in ("block", "rescue", "always"):
            result.extend(tasks_in(task.get(section, [])))
    return result


class KvmInventoryTargetsTest(unittest.TestCase):
    def test_dual_mode_configuration_preserves_full_topology(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                config = yaml.safe_load(
                    (ROOT / "molecule" / scenario / "molecule.yml").read_text()
                )
                self.assertEqual(config["driver"]["name"], "default")
                self.assertIs(config["driver"]["options"]["managed"], True)
                self.assertEqual(
                    config["driver"]["safe_files"],
                    ["${MOLECULE_EPHEMERAL_DIRECTORY}/collections/*"],
                )
                self.assertNotIn("test_sequence", config.get("scenario", {}))
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
                provisioner = config["provisioner"]
                self.assertEqual(provisioner["name"], "ansible")
                self.assertEqual(provisioner["env"]["IDARSI_MOLECULE_BACKEND"], "kvm")
                self.assertNotIn("inventory", provisioner)
                self.assertEqual(
                    provisioner["playbooks"],
                    {
                        action: "${IDARSI_TEST_ENVIRONMENT}/molecule/managed/"
                        + action
                        + ".yml"
                        for action in ("create", "destroy")
                    },
                )
                self.assertEqual(
                    [platform["name"] for platform in config["platforms"]], GUESTS
                )
                for platform in config["platforms"]:
                    self.assertEqual(platform["ssh_user"], "molecule")
                    self.assertNotIn("network", platform)
                    self.assertNotIn("ipv4_address", platform)
                    self.assertEqual(
                        platform["install_source"], "${IDARSI_TEST_KVM_INSTALL_SOURCE}"
                    )

    def test_no_static_connections_or_private_host_control(self):
        for scenario in SCENARIOS:
            for path in (ROOT / "molecule" / scenario).glob("*.yml"):
                with self.subTest(path=str(path.relative_to(ROOT))):
                    content = path.read_text()
                    self.assertNotIn("192.168.250.", content)
                    self.assertNotIn("ansible_connection:", content)
                    self.assertNotIn("ansible_host:", content)
                    self.assertNotIn("scripts/kvm-vm", content)
                    self.assertNotIn("virsh", content)
                    self.assertNotIn("IDARSI_HANDOFF", content)
                    self.assertNotIn("IDARSI_RUN_ID", content)
                    for record in yaml.safe_load(content) or []:
                        if isinstance(record, dict) and "import_playbook" in record:
                            imported = (
                                path.parent / record["import_playbook"]
                            ).resolve()
                            self.assertTrue(imported.is_relative_to(ROOT / "molecule"))
                            self.assertTrue(imported.is_file(), str(imported))

    def test_cluster_fixtures_use_generated_addresses_and_keep_security(self):
        for scenario in ("kvm-combined-patroni-failover", "kvm-etcd-quorum"):
            directory = ROOT / "molecule" / scenario
            prepare = (directory / "prepare.yml").read_text()
            converge = (directory / "converge.yml").read_text()
            with self.subTest(scenario=scenario):
                for guest in GUESTS:
                    address = "hostvars['" + guest + "'].ansible_host"
                    self.assertIn(address, prepare)
                    self.assertIn(address, converge)
                self.assertIn(
                    "subjectAltName=DNS:pg01,DNS:pg02,DNS:pg03,IP:{{", prepare
                )
                self.assertIn("hostvars[item.0].ansible_host }}/32", prepare)
                self.assertIn("ansible.posix.firewalld:", prepare)
                self.assertIn("disable_gpg_check: false", prepare)
                self.assertIn("validate_certs: true", prepare)
                self.assertNotIn("state: restarted", converge)
                self.assertNotIn("changed_when: true", converge)
                self.assertIn("/32 scram-sha-256", converge)

    def test_hard_failure_requires_owned_api_and_always_restores_guest(self):
        path = ROOT / "molecule" / "kvm-hard-patroni-failure" / "verify.yml"
        content = path.read_text()
        play = yaml.safe_load(content)[0]
        tasks = tasks_in(play["tasks"])
        probe = next(
            task for task in tasks if task.get("register") == "kvm_guest_control"
        )
        self.assertEqual(probe["loop"], ["capabilities", "resolve"])
        self.assertEqual(probe["delegate_to"], "localhost")
        self.assertIs(probe["become"], False)
        self.assertIn("guest_control_protocol == 'owned-kvm-v1'", content)
        self.assertIn(
            "'guest-stop' in (item.stdout | from_json).guest_control_actions", content
        )
        self.assertIn(
            "'guest-start' in (item.stdout | from_json).guest_control_actions", content
        )
        disruption = next(
            task for task in tasks if "block" in task and "always" in task
        )
        stop = next(
            task
            for task in disruption["block"]
            if task.get("register") == "kvm_guest_stopped"
        )
        start = next(
            task
            for task in disruption["always"]
            if task.get("register") == "kvm_guest_started"
        )
        for action, task in (("guest-stop", stop), ("guest-start", start)):
            argv = task["ansible.builtin.command"]["argv"]
            self.assertEqual(argv[0], "{{ kvm_context_helper }}")
            self.assertEqual(argv[1], action)
            self.assertEqual(
                argv[2:],
                [
                    "--backend",
                    "kvm",
                    "--scenario",
                    "{{ kvm_context_scenario }}",
                    "--role",
                    "{{ kvm_context_role }}",
                    "--guest",
                    "{{ kvm_failed_leader }}",
                ],
            )
            self.assertEqual(task["delegate_to"], "localhost")
            self.assertIs(task["become"], False)
            self.assertNotIn("environment", task)
        self.assertIn(
            "(kvm_guest_stopped.stdout | from_json).changed is sameas true", content
        )
        for key in ("action", "guest", "operation", "changed", "state"):
            for result in ("kvm_guest_stopped", "kvm_guest_started"):
                self.assertIn(f"({result}.stdout | from_json).{key}", content)
        self.assertTrue(
            any(
                "ansible.builtin.wait_for_connection" in task
                for task in disruption["always"]
            )
        )
        self.assertIn("kvm_rejoined_after_marker.stdout | trim == 'after'", content)
        self.assertIn("selectattr('host', 'equalto', kvm_failed_leader)", content)


if __name__ == "__main__":
    unittest.main()
