"""Guard KVM Molecule inventory connection targets."""

from pathlib import Path
import re
import unittest

try:
    import yaml
except ImportError:
    yaml = None


class KvmInventoryTargetsTest(unittest.TestCase):
    def test_all_kvm_scenarios_define_targets_in_provisioner_inventory(self):
        scenarios = sorted(Path("molecule").glob("kvm_*/molecule.yml"))
        self.assertEqual(len(scenarios), 9)
        for path in scenarios:
            with self.subTest(scenario=path.parent.name):
                content = path.read_text()
                expected = {"pg01": "192.168.250.201", "pg02": "192.168.250.202", "pg03": "192.168.250.203"}
                if yaml is not None:
                    config = yaml.safe_load(content)
                    provisioner = config["provisioner"]
                    self.assertIn("create", provisioner["playbooks"])
                    self.assertIn("destroy", provisioner["playbooks"])
                    self.assertEqual(
                        {name: vars_["ansible_host"] for name, vars_ in provisioner["inventory"]["host_vars"].items()},
                        expected,
                    )
                    self.assertEqual(
                        {platform["name"]: platform["ipv4_address"] for platform in config["platforms"]},
                        expected,
                    )
                else:
                    self.assertEqual(
                        dict(re.findall(r'(?m)^      (pg\d+):\n        ansible_host: "([\d.]+)"$', content)),
                        expected,
                    )
                    self.assertEqual(
                        dict(re.findall(r"(?m)^- name: (pg\d+)\n(?:.*\n)*?  ipv4_address: ([\d.]+)$", content)),
                        expected,
                    )
                    self.assertEqual(len(re.findall(r"(?m)^provisioner:$", content)), 1)


if __name__ == "__main__":
    unittest.main()
