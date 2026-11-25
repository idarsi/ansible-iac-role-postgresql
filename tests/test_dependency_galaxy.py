"""Offline real-Galaxy regression using only temporary local collection artifacts."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "dependency", Path(__file__).with_name("dependency.py")
)
dependency = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dependency)


class PrivateGalaxyTest(unittest.TestCase):
    def test_external_exact_version_does_not_satisfy_private_destination(self):
        with tempfile.TemporaryDirectory(
            prefix="postgresql-local-galaxy-"
        ) as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / "README.md").write_text("Local offline regression fixture.\n")
            (source / "plugins/modules").mkdir(parents=True)
            (source / "plugins/modules/probe.py").write_text(
                '"""Local fixture; never executed."""\n'
            )
            metadata = {
                "namespace": "fixture",
                "name": "private_probe",
                "version": "1.0.0",
                "readme": "README.md",
                "authors": ["Regression Fixture"],
                "license": ["MIT"],
                "dependencies": {},
            }
            # JSON is a YAML subset accepted by Galaxy; no generated fixture
            # or installed collection is written outside this temporary root.
            (source / "galaxy.yml").write_text(json.dumps(metadata))
            config = root / "ansible.cfg"
            config.write_text("[defaults]\n")
            base = dict(os.environ)
            base.update(
                {
                    "HOME": str(root),
                    "ANSIBLE_HOME": str(root / "ansible-home"),
                    "ANSIBLE_CONFIG": str(config),
                    "ANSIBLE_LOCAL_TEMP": str(root / "local-temp"),
                }
            )
            galaxy = Path(sys.prefix) / "bin/ansible-galaxy"
            self.assertTrue(galaxy.is_file(), "Use an existing approved controller")

            def run(arguments, environment):
                result = subprocess.run(
                    [str(galaxy), "collection", *arguments],
                    cwd=root,
                    env=environment,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout)
                return result.stdout

            run(["build", str(source), "--output-path", str(root)], base)
            archive = root / "fixture-private_probe-1.0.0.tar.gz"
            self.assertTrue(archive.is_file())
            external = root / "external"
            private = root / "private"
            external.mkdir(mode=0o700)
            private.mkdir(mode=0o700)
            install = ["install", str(archive), "--offline", "--no-deps"]
            run(
                [*install, "-p", str(external)],
                dependency.galaxy_environment(external, base),
            )
            dependency.verify_private_collection(
                external, "fixture.private_probe", "1.0.0"
            )
            inherited = dict(base)
            inherited.update(
                {
                    "ANSIBLE_COLLECTIONS_PATH": str(external),
                    "ANSIBLE_COLLECTIONS_SCAN_SYS_PATH": "true",
                    "PYTHONPATH": str(external),
                }
            )
            # Reproduce the old defect with real Galaxy: -p alone still
            # considers the exact externally installed version satisfied.
            output = run([*install, "-p", str(private)], inherited)
            self.assertIn("Nothing to do", output)
            with self.assertRaisesRegex(ValueError, "Private collection"):
                dependency.verify_private_collection(
                    private, "fixture.private_probe", "1.0.0"
                )

            isolated = dependency.galaxy_environment(private, inherited)
            self.assertEqual(isolated["ANSIBLE_COLLECTIONS_PATH"], str(private))
            self.assertEqual(isolated["ANSIBLE_COLLECTIONS_SCAN_SYS_PATH"], "false")
            run([*install, "-p", str(private)], isolated)
            dependency.verify_private_collection(
                private, "fixture.private_probe", "1.0.0"
            )
            self.assertTrue(
                (
                    private
                    / "ansible_collections/fixture/private_probe/plugins/modules/probe.py"
                ).is_file()
            )
            # Private repeat/no-op is valid only because physical metadata
            # remains present in that same destination.
            run([*install, "-p", str(private)], isolated)
            dependency.verify_private_collection(
                private, "fixture.private_probe", "1.0.0"
            )


if __name__ == "__main__":
    unittest.main()
