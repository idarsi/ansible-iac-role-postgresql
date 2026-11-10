"""Guard KVM Molecule inventory connection targets."""

from pathlib import Path
import re
import unittest


class KvmInventoryTargetsTest(unittest.TestCase):
    def test_all_kvm_scenarios_define_targets_in_provisioner_inventory(self):
        scenarios = sorted(Path("molecule").glob("kvm_*/molecule.yml"))
        configured = [path for path in scenarios if "ipv4_address:" in path.read_text()]
        self.assertEqual(len(configured), 9)
        for path in configured:
            with self.subTest(scenario=path.parent.name):
                content = path.read_text()
                self.assertRegex(content, r"(?m)^  inventory:\s*\n    host_vars:")
                for name, address in re.findall(
                    r"(?m)^- name: (pg\d+)\n.*?^  ipv4_address: ([\d.]+)",
                    content,
                    re.DOTALL,
                ):
                    mapping = rf"(?m)^      {name}:\n        ansible_host: \"{re.escape(address)}\"$"
                    self.assertRegex(content, mapping)


if __name__ == "__main__":
    unittest.main()
