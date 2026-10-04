"""Guard the validation endpoint-collision assertions against YAML regressions."""

from pathlib import Path
import subprocess
import shutil

import yaml


ROOT = Path(__file__).parents[1]
CONVERGE = ROOT / "molecule" / "validation" / "converge.yml"


def main():
    plays = yaml.safe_load(CONVERGE.read_text())
    collision_play = next(
        play for play in plays
        if play.get("name") == "Reject canonical-equivalent Patroni endpoints before mutation"
    )
    check = next(
        task for task in collision_play["tasks"]
        if task.get("name") == "Checking canonical endpoint collision fails before mutation"
    )
    rescue = check["rescue"]
    assertion = next(task for task in rescue if "ansible.builtin.assert" in task)
    conditions = assertion["ansible.builtin.assert"]["that"]
    assert len(conditions) == 3
    assert any("pg_validation_expected_collision_message" in condition for condition in conditions)
    assert any('"2001:db8::1"' in condition for condition in conditions)

    ansible_playbook = shutil.which("ansible-playbook")
    assert ansible_playbook, "ansible-playbook is required for the syntax guard"
    result = subprocess.run(
        [ansible_playbook, "--syntax-check", "-i", "localhost,", "-c", "local", str(CONVERGE)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    print("validation endpoint collision YAML/syntax guardrails: PASS")


if __name__ == "__main__":
    main()
