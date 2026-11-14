#!/usr/bin/env python3
"""Provenance checks for the all-push completion tracker workflow."""

from __future__ import print_function

import ast
import subprocess
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/final-push-tracker.yml"


class FinalPushTrackerWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW_PATH.read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(cls.text)

    def test_pull_requests_and_pushes_use_the_literal_candidate(self):
        self.assertIn(
            "EXPECTED_HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}",
            self.text,
        )
        checkout = self.text.split("- name: Check out exact candidate", 1)[1].split(
            "- name: Verify exact candidate identity", 1
        )[0]
        self.assertIn("ref: ${{ env.EXPECTED_HEAD_SHA }}", checkout)
        self.assertIn("fetch-depth: 0", checkout)
        self.assertIn("persist-credentials: false", checkout)
        self.assertIn(
            'test "$(git rev-parse HEAD)" = "$EXPECTED_HEAD_SHA"', self.text
        )
        self.assertIn(
            "name: final-push-tracker-${{ env.EXPECTED_HEAD_SHA }}", self.text
        )

    def test_yaml_and_every_shell_step_parse(self):
        self.assertIsInstance(self.workflow, dict)
        for job in self.workflow["jobs"].values():
            for step in job.get("steps", []):
                script = step.get("run")
                if not isinstance(script, str):
                    continue
                completed = subprocess.run(
                    ["bash", "-n"],
                    input=script.encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(
                    0, completed.returncode, completed.stderr.decode("utf-8", "replace")
                )

    def test_behavior_contract_uses_commit_bound_isolated_authority(self):
        step = self.text.split(
            "- name: Validate locked scope, policy, and behavior contract", 1
        )[1].split("- name: Validate tracker implementation", 1)[0]
        self.assertNotIn("python3 scripts/host_module_contracts.py --check", step)
        self.assertIn("/usr/bin/python3 -I -S -B -c", step)
        self.assertIn(
            'launcher=trusted_git([\\"cat-file\\",\\"blob\\",expected_head+'
            '\\":scripts/host_module_failure_sites.py\\"])',
            step,
        )
        self.assertIn("module.isolated_authority_main", step)
        self.assertIn("--authority-target contracts --", step)
        self.assertIn('FP_AUTHORITY_EXPECTED_HEAD="$EXPECTED_HEAD_SHA"', step)
        self.assertIn("git -C ihk apply --check", step)
        self.assertIn("git -C ihk apply", step)
        self.assertIn("scripts/patches/ihk-linux-compat.patch", step)

    def test_authority_predecessors_cannot_leave_repository_bytecode(self):
        self.assertIn('PYTHONDONTWRITEBYTECODE: "1"', self.text)
        self.assertNotIn("python3 -m py_compile", self.text)

    def test_file_parses_as_python_3_6(self):
        source = Path(__file__).read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=__file__, feature_version=(3, 6))
        except TypeError:
            ast.parse(source, filename=__file__, feature_version=6)


if __name__ == "__main__":
    unittest.main()
