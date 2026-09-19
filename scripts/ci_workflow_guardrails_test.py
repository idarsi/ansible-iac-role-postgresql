#!/usr/bin/env python3
"""Require the CI-selected Python interpreter for every Ansible Lint call."""

from pathlib import Path
import yaml


WORKFLOW = Path(__file__).parents[1] / ".github/workflows/tests.yml"


def strings(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
    elif isinstance(value, str):
        yield value


document = yaml.safe_load(WORKFLOW.read_text())
lint_calls = [
    text for text in strings(document) if "ansiblelint" in text or "ansible-lint" in text
]
assert lint_calls, "workflow must retain Ansible Lint coverage"
assert all(
    '"${CI_PYTHON_COMMAND}" -m ansiblelint' in text for text in lint_calls
), "workflow contains an unqualified Ansible Lint invocation"
print("CI Ansible Lint interpreter guardrail passed")
