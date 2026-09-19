#!/usr/bin/env python3
"""Exercise path normalization through Ansible, including rejection ordering."""

import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
TASKS = ROOT / "tasks/validate/normalize_path.yml"


def run_play(path_values, expect_success):
    paths = repr(path_values)
    playbook = f"""---
- hosts: localhost
  gather_facts: false
  connection: local
  vars:
    pg_normalized: []
  tasks:
    - ansible.builtin.include_tasks: {TASKS}
      loop: {paths}
      loop_control:
        loop_var: test_path
      vars:
        pg_path_normalize_input: "{{{{ test_path }}}}"
        pg_path_normalize_result_fact: "pg_current_path"
        pg_path_normalize_accumulator: "pg_normalized"
    - ansible.builtin.assert:
        that:
          - pg_normalized == ['/var/lib/postgresql', '/etc/postgresql']
"""
    with tempfile.TemporaryDirectory() as directory:
        playbook_path = Path(directory) / "path.yml"
        playbook_path.write_text(playbook)
        result = subprocess.run(
            ["ansible-playbook", "-i", "localhost,", str(playbook_path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    assert (result.returncode == 0) is expect_success, result.stdout + result.stderr
    return result


def main():
    run_play(["/var/lib/../lib/postgresql", "/etc/postgresql"], False)
    run_play(["/var/lib/postgresql", r"/etc\postgresql"], False)
    # Dot components remain safely canonicalized, and the accumulator stays a list.
    run_play(["/var/lib/./postgresql", "/etc/postgresql"], True)
    print("path normalization runtime guardrails: PASS")


if __name__ == "__main__":
    main()
