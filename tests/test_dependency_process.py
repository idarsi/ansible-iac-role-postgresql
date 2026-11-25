"""Exercise installed Molecule's real dependency subprocess with fake I/O.

No native helper/backend or Galaxy installer runs. Run this module under each
existing controller interpreter to test that lane's installed shell plugin.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FAKE_HELPER = """#!/usr/bin/env python3
import json, os, pathlib, sys
assert sys.argv[1] == 'resolve', 'Only allocation-free resolution is permitted'
role = sys.argv[sys.argv.index('--role') + 1]
scenario = sys.argv[sys.argv.index('--scenario') + 1]
backend = sys.argv[sys.argv.index('--backend') + 1]
ephemeral = os.environ['MOLECULE_EPHEMERAL_DIRECTORY']
assert os.environ['MOLECULE_PROJECT_DIRECTORY'] == role
assert os.environ['MOLECULE_SCENARIO_DIRECTORY'] == role + '/molecule/' + scenario
assert os.environ['MOLECULE_SCENARIO_NAME'] == scenario
assert pathlib.Path(os.environ['MOLECULE_FILE']).parent == pathlib.Path(ephemeral)
record = {'argv': sys.argv[1:], 'scenario': scenario, 'backend': backend,
          'ephemeral': ephemeral, 'env_file': os.environ['MOLECULE_ENV_FILE'],
          'markers': {k: v for k, v in os.environ.items()
                      if k == 'IDARSI_RUN_ID' or k.startswith('IDARSI_HANDOFF')}}
pathlib.Path(os.environ['DEPENDENCY_TEST_RESOLVE_RECORD']).write_text(json.dumps(record))
if record['markers']:
    sys.exit('Fixture helper rejects partial supervised context')
print(json.dumps({'schema': 'idarsi.scenario-context/v1', 'role': role,
      'scenario': scenario, 'backend': backend, 'mode': 'direct',
      'lifecycle_modes': ['direct', 'supervised'], 'generation': None,
      'effective_config_validated': True, 'ephemeral_directory': ephemeral,
      'collections_directory': ephemeral + '/collections'}))
"""
FAKE_GALAXY = """#!/usr/bin/env python3
import json, os, pathlib, sys
if sys.argv[1:3] == ['collection', 'list']:
    print('{}')
    sys.exit(0)
assert sys.argv[1:3] == ['collection', 'install'], 'Unexpected Galaxy operation'
import yaml
destination = pathlib.Path(sys.argv[sys.argv.index('-p') + 1])
assert os.environ['ANSIBLE_COLLECTIONS_PATH'] == str(destination)
assert os.environ['ANSIBLE_COLLECTIONS_SCAN_SYS_PATH'] == 'false'
manifest = pathlib.Path(sys.argv[sys.argv.index('-r') + 1])
for record in yaml.safe_load(manifest.read_text())['collections']:
    namespace, name = record['name'].split('.')
    directory = destination / 'ansible_collections' / namespace / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'MANIFEST.json').write_text(json.dumps({'collection_info': {
        'namespace': namespace, 'name': name, 'version': record['version']}}))
    (directory / 'FILES.json').write_text('{}')
with pathlib.Path(os.environ['DEPENDENCY_TEST_GALAXY_RECORD']).open('a') as stream:
    stream.write(json.dumps(sys.argv[1:]) + '\\n')
"""


class DependencyProcessTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="postgresql-dependency-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.role = self.directory / "ansible-iac-role-postgresql"
        (self.role / "tests").mkdir(parents=True)
        for name in ("dependency.py", "collections.yml"):
            shutil.copyfile(ROOT / "tests" / name, self.role / "tests" / name)
        shutil.copyfile(ROOT / "role-test.json", self.role / "role-test.json")
        for scenario in ("podman-validation", "kvm-replication"):
            destination = self.role / "molecule" / scenario
            destination.mkdir(parents=True)
            shutil.copyfile(
                ROOT / "molecule" / scenario / "molecule.yml",
                destination / "molecule.yml",
            )
            (destination / "collections.yml").write_text("---\ncollections: []\n")
        self.helper = self.directory / "helper"
        (self.helper / "scripts").mkdir(parents=True)
        (self.helper / "scripts/scenario-context").write_text(FAKE_HELPER)
        (self.helper / "scripts/scenario-context").chmod(0o700)
        self.binary = self.directory / "bin"
        self.binary.mkdir()
        (self.binary / "ansible-galaxy").write_text(FAKE_GALAXY)
        (self.binary / "ansible-galaxy").chmod(0o700)
        self.resolve_record = self.directory / "resolve.json"
        self.galaxy_record = self.directory / "galaxy.jsonl"
        self.cli_arguments = []
        self.environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("MOLECULE_")
            and not key.startswith("IDARSI_HANDOFF")
            and key != "IDARSI_RUN_ID"
        }
        self.environment.update(
            {
                "HOME": str(self.directory),
                "XDG_CACHE_HOME": str(self.directory / "cache"),
                "IDARSI_TEST_ENVIRONMENT": str(self.helper),
                "DEPENDENCY_TEST_RESOLVE_RECORD": str(self.resolve_record),
                "DEPENDENCY_TEST_GALAXY_RECORD": str(self.galaxy_record),
                "PATH": str(self.binary)
                + os.pathsep
                + str(Path(sys.prefix) / "bin")
                + os.pathsep
                + os.environ["PATH"],
            }
        )

    def run_dependency(self, scenario):
        molecule = Path(sys.prefix) / "bin/molecule"
        self.assertTrue(
            molecule.is_file(), "Use an existing approved Molecule controller"
        )
        return subprocess.run(
            [str(molecule), *self.cli_arguments, "dependency", "-s", scenario],
            cwd=self.role,
            env=self.environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
            check=False,
        )

    def assert_private_install(self, scenario, backend):
        result = self.run_dependency(scenario)
        self.assertEqual(result.returncode, 0, result.stdout)
        record = json.loads(self.resolve_record.read_text())
        self.assertEqual(record["argv"][0], "resolve")
        self.assertEqual(record["scenario"], scenario)
        self.assertEqual(record["backend"], backend)
        self.assertEqual(record["markers"], {})
        destination = Path(record["ephemeral"]) / "collections"
        self.assertTrue(destination.is_relative_to(self.directory))
        self.assertTrue((destination / ".postgresql-galaxy.lock").is_file())
        installs = [
            json.loads(line) for line in self.galaxy_record.read_text().splitlines()
        ]
        self.assertEqual(len(installs), 2)
        for command in installs:
            self.assertEqual(command[-2:], ["-p", str(destination)])
        self.assertNotIn("MOLECULE_SCENARIO_NAME", self.environment)
        return record

    def test_default_direct_context_without_computed_environment(self):
        self.assert_private_install("podman-validation", "podman")

    def test_explicit_retained_context_and_env_file(self):
        retained = self.directory / "retained"
        env_file = self.role / "retained-env.yml"
        env_file.write_text(
            "---\nDEPENDENCY_FIXTURE: retained\nIDARSI_TEST_ENVIRONMENT: "
            + json.dumps(str(self.helper))
            + "\n"
        )
        self.cli_arguments = ["--env-file", str(env_file)]
        self.environment.pop("IDARSI_TEST_ENVIRONMENT")
        self.environment["MOLECULE_EPHEMERAL_DIRECTORY"] = str(retained)
        record = self.assert_private_install("kvm-replication", "kvm")
        self.assertEqual(record["ephemeral"], str(retained))
        self.assertEqual(Path(record["env_file"]), env_file)

    def test_partial_handoff_reaches_helper_and_cannot_install(self):
        self.environment["IDARSI_HANDOFF"] = ""
        result = self.run_dependency("podman-validation")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        record = json.loads(self.resolve_record.read_text())
        self.assertEqual(record["markers"], {"IDARSI_HANDOFF": ""})
        self.assertFalse(self.galaxy_record.exists())


if __name__ == "__main__":
    unittest.main()
