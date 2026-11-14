#!/usr/bin/env python3
"""Provenance checks for the all-push completion tracker workflow."""

from __future__ import print_function

import ast
import os
import subprocess
import tempfile
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

    def test_frozen_ihk_source_uses_committed_bundle_restoration(self):
        steps = self.workflow["jobs"]["tracker"]["steps"]
        names = [step.get("name") for step in steps]
        restore_index = names.index("Restore frozen IHK source")
        script = steps[restore_index]["run"]
        self.assertEqual(
            script,
            'set -euo pipefail\n'
            'python3 -B scripts/restore_ihk_source.py \\\n'
            '  --repo "$GITHUB_WORKSPACE" \\\n'
            '  --destination "$GITHUB_WORKSPACE/ihk"\n',
        )
        self.assertNotIn("git submodule update", self.text)
        self.assertLess(names.index("Verify exact candidate identity"), restore_index)
        for consumer in (
            "Validate frozen host-module inventory",
            "Validate locked scope, policy, and behavior contract",
        ):
            self.assertLess(restore_index, names.index(consumer))

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

    def test_development_markdown_only_omits_frozen_host_checks(self):
        steps = self.workflow["jobs"]["tracker"]["steps"]
        selector = next(step for step in steps if step.get("id") == "host-scope")
        cases = (
            ("pull_request", ("docs/development/plan.md",), False),
            ("push", ("docs/development/nested/plan.md",), False),
            ("pull_request", ("docs/development/plan.md", "kernel/syscall.c"), True),
            ("pull_request", ("docs/development/criteria.json",), True),
            ("pull_request", ("docs/verification/evidence.md",), True),
            ("pull_request", (), True),
            ("workflow_dispatch", ("docs/development/plan.md",), True),
            ("new_branch", ("docs/development/plan.md",), True),
        )
        for event, paths, expected in cases:
            with self.subTest(event=event, paths=paths):
                with tempfile.TemporaryDirectory(prefix="tracker-change-scope-") as temporary:
                    root = Path(temporary)
                    repo = root / "repo"
                    repo.mkdir()

                    def git(*args):
                        completed = subprocess.run(
                            ["git", "-c", "user.name=Workflow test", "-c",
                             "user.email=workflow-test@example.invalid"] + list(args),
                            cwd=str(repo), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        )
                        self.assertEqual(0, completed.returncode,
                                         completed.stderr.decode("utf-8", "replace"))
                        return completed.stdout.decode("utf-8").strip()

                    git("init", "--quiet")
                    (repo / "baseline.txt").write_text("baseline\n", encoding="utf-8")
                    git("add", "--all")
                    git("commit", "--quiet", "-m", "baseline")
                    base = git("rev-parse", "HEAD")
                    for name in paths:
                        path = repo / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text("changed\n", encoding="utf-8")
                    git("add", "--all")
                    git("commit", "--quiet", "--allow-empty", "-m", "candidate")
                    env = os.environ.copy()
                    env.update({
                        "EVENT_NAME": "push" if event == "new_branch" else event,
                        "BASE_SHA": "0" * 40 if event == "new_branch" else base,
                        "EXPECTED_HEAD_SHA": git("rev-parse", "HEAD"),
                        "RUNNER_TEMP": str(root),
                        "GITHUB_OUTPUT": str(root / "output"),
                        "GITHUB_STEP_SUMMARY": str(root / "summary"),
                    })
                    completed = subprocess.run(
                        ["bash", "-c", selector["run"]], cwd=str(repo), env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    )
                    self.assertEqual(0, completed.returncode,
                                     completed.stderr.decode("utf-8", "replace"))
                    self.assertEqual("required=" + str(expected).lower() + "\n",
                                     (root / "output").read_text(encoding="utf-8"))

        frozen = {
            "Restore frozen IHK source",
            "Validate frozen host-module inventory",
            "Validate locked scope, policy, and behavior contract",
        }
        for step in steps:
            if step.get("name") in frozen:
                self.assertEqual("steps.host-scope.outputs.required == 'true'", step["if"])
            elif step.get("name", "").startswith(("Validate tracker", "Prove ")):
                self.assertNotIn("if", step)
        inventory = next(step for step in steps
                         if step.get("name") == "Validate frozen host-module inventory")
        self.assertIn("python3 -m unittest discover -s scripts/tests -v", inventory["run"])

    def test_bounded_host_workflows_keep_compilers_and_new_regressions(self):
        for filename, job_name, timeout in (
            ("m14-focused.yml", "focused", 10),
            ("m14-f06-qualification.yml", "f06", 15),
        ):
            path = WORKFLOW_PATH.parent / filename
            text = path.read_text(encoding="utf-8")
            workflow = yaml.safe_load(text)
            events = workflow.get("on", workflow.get(True))
            self.assertIn("codex/local-native-staging-repair", events["push"]["branches"])
            self.assertEqual("${{ github.event_name == 'pull_request' }}",
                             workflow["concurrency"]["cancel-in-progress"])
            self.assertIn("${{ github.workflow }}", workflow["concurrency"]["group"])
            job = workflow["jobs"][job_name]
            self.assertEqual("ubuntu-24.04", job["runs-on"])
            self.assertEqual(timeout, job["timeout-minutes"])
            self.assertIn("nightly-2026-02-19", text)
            self.assertIn("scripts/run_m14_focused_checks.py --json-output", text)
            for step in job["steps"]:
                if "run" not in step:
                    continue
                completed = subprocess.run(["bash", "-n"], input=step["run"].encode("utf-8"),
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(0, completed.returncode,
                                 completed.stderr.decode("utf-8", "replace"))
            if job_name == "focused":
                regressions = next(step["run"] for step in job["steps"]
                                   if step.get("name") == "Run source runner and metadata reuse regressions")
                self.assertIn("scripts.tests.test_run_m14_focused_checks", regressions)
                self.assertIn("scripts.tests.test_m14_metadata_reuse", regressions)
            else:
                for event in ("push", "pull_request"):
                    for dependency in ("CMakeLists.txt", "config.h.in", "ihk",
                                       "executer/user/mcexec.c", "executer/user/rust/mcexec_helpers.rs"):
                        self.assertIn(dependency, events[event]["paths"])
                self.assertIn("scripts/m14_f06_qualify.py --ihk-source", text)

    def test_file_parses_as_python_3_6(self):
        source = Path(__file__).read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=__file__, feature_version=(3, 6))
        except TypeError:
            ast.parse(source, filename=__file__, feature_version=6)


if __name__ == "__main__":
    unittest.main()
