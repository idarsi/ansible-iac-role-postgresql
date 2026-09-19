#!/usr/bin/env python3
"""Check native Patroni image preflights in both Molecule workflow paths."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
workflow = yaml.safe_load((ROOT / ".github/workflows/tests.yml").read_text())


def main():
    for job_name in ("molecule-fast", "molecule-daily"):
        steps = workflow["jobs"][job_name]["steps"]
        names = [step.get("name") for step in steps]
        run_index = names.index("Run Molecule scenario")
        native_index = names.index("Fail closed unless Patroni image runs on native amd64 Podman")
        image_index = names.index("Preflight the pinned Patroni base image")
        assert native_index < image_index < run_index, f"{job_name}: Patroni preflight ordering changed"

        native = steps[native_index]
        assert native["if"] == "matrix.scenario == 'patroni_config'"
        native_run = native["run"]
        for requirement in (
            'test "$(uname -m)" = "x86_64"',
            'test "$(id -u)" != "0"',
            "Host.Security.Rootless",
            "Host.Arch",
        ):
            assert requirement in native_run, f"{job_name}: missing {requirement} host guard"

        image = steps[image_index]
        assert image["if"] == "matrix.scenario == 'patroni_config'"
        image_run = image["run"]
        assert "podman pull --quiet --platform linux/amd64" in image_run
        assert "podman image inspect" in image_run
        assert "{{.Architecture}}" in image_run
        assert "b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5" in image_run

        molecule_run = steps[run_index]["run"]
        patroni_position = molecule_run.find('python -m molecule test -s "${{ matrix.scenario }}"')
        assert patroni_position >= 0, f"{job_name}: normal Molecule path disappeared"


if __name__ == "__main__":
    main()
    print("Patroni workflow preflight ordering: PASS")
