#!/usr/bin/env python3

from __future__ import print_function

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from scripts import native_rust_runtime_evidence as runtime_evidence
from scripts import native_rust_kconfig_policy as kconfig_policy


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/native-rust-host-modules-exact-build.yml"
SOURCE_WORKFLOW = REPO_ROOT / ".github/workflows/rocky-kernel-source-evidence.yml"
PATCH = REPO_ROOT / "host-kernel/kbuild/patches/0002-rust-bindings-expose-module-parameters.patch"
CONFIG = REPO_ROOT / "host-kernel/rocky/configs/native-rust-evidence.config"
RK006_CAPTURE_CONTRACT = (
    REPO_ROOT
    / "host-kernel/rocky/evidence/rk006-full-source-build-capture-contract-v1.json"
)

PROVENANCE_STEP_NAME = "Validate built metadata and capture immutable diagnostics"
PROVENANCE_WORKFLOW_PATH = (
    ".github/workflows/native-rust-host-modules-exact-build.yml"
)
PROVENANCE_ENV_BINDINGS = {
    "PROVENANCE_CALLER_EVENT_NAME": "${{ github.event_name }}",
    "PROVENANCE_CALLER_REF": "${{ github.ref }}",
    "PROVENANCE_CALLER_REPOSITORY": "${{ github.repository }}",
    "PROVENANCE_CALLER_SHA": "${{ github.sha }}",
    "PROVENANCE_CALLER_WORKFLOW_REF": "${{ github.workflow_ref }}",
    "PROVENANCE_CALLER_WORKFLOW_SHA": "${{ github.workflow_sha }}",
    "PROVENANCE_CANDIDATE_SHA": (
        "${{ inputs.validation_sha || github.event.pull_request.head.sha || github.sha }}"
    ),
    "PROVENANCE_DEFINING_WORKFLOW_FILE_PATH": "${{ job.workflow_file_path }}",
    "PROVENANCE_DEFINING_WORKFLOW_REF": "${{ job.workflow_ref }}",
    "PROVENANCE_DEFINING_WORKFLOW_REPOSITORY": "${{ job.workflow_repository }}",
    "PROVENANCE_DEFINING_WORKFLOW_SHA": "${{ job.workflow_sha }}",
}
PROVENANCE_DEFAULT_ENV_FIELDS = ("GITHUB_RUN_ATTEMPT", "GITHUB_RUN_ID")


def provenance_step(workflow_text):
    workflow = yaml.safe_load(workflow_text)
    matches = [
        step
        for step in workflow["jobs"]["exact-build"]["steps"]
        if step.get("name") == PROVENANCE_STEP_NAME
    ]
    if len(matches) != 1:
        raise ValueError("provenance step count differs")
    return matches[0]


def provenance_python_source(workflow_text):
    run = provenance_step(workflow_text)["run"]
    marker = 'EVIDENCE_DIR="$EVIDENCE_DIR" /usr/bin/python3 -E -s <<\'PY\'\n'
    if run.count(marker) != 1:
        raise ValueError("provenance Python marker count differs")
    source = run.split(marker, 1)[1]
    if source.count("\nPY\n") != 1:
        raise ValueError("provenance Python terminator count differs")
    return source.split("\nPY\n", 1)[0] + "\n"


def validate_provenance_structure(workflow_text):
    step = provenance_step(workflow_text)
    observed = {
        name: value
        for name, value in step.get("env", {}).items()
        if name.startswith("PROVENANCE_")
    }
    if observed != PROVENANCE_ENV_BINDINGS:
        raise ValueError("provenance context bindings differ")
    source = provenance_python_source(workflow_text)
    required_fragments = (
        '"caller": {',
        '"candidate": {',
        '"claims": {',
        '"defining_job": {',
        '"evidence_file": executed_workflow_name',
        '"direct_workflow_dispatch": direct_workflow_dispatch',
        '"github_run_attempt": github_run_attempt',
        '"github_run_id": github_run_id',
        '"workflow_file_bytes_equal": True',
        '"fetch",',
        '"--no-tags",',
        '"--depth=1",',
        '"--no-recurse-submodules",',
        '"FETCH_HEAD^{commit}"',
        'fetched_commit == defining_workflow_sha',
        'git_environment["GIT_NO_REPLACE_OBJECTS"] = "1"',
        "caller_event_name in ACCEPTED_EVENT_NAMES",
        "caller_repository == defining_repository",
        "caller_sha == caller_workflow_sha == defining_workflow_sha",
        "caller_workflow_git_ref == caller_ref",
        "defining_workflow_git_ref == caller_ref",
        "PULL_REQUEST_REF_RE.match(value)",
        "BRANCH_OR_TAG_REF_RE.match(value)",
        'candidate_blob_sha1 == defining_blob_sha1',
        'candidate_file_sha256 == defining_file_sha256',
        'candidate_bytes == defining_bytes',
        'candidate_sha == caller_workflow_sha == defining_workflow_sha',
        'required_environment("GITHUB_RUN_ATTEMPT")',
        'required_environment("GITHUB_RUN_ID")',
        "POSITIVE_DECIMAL_RE.match(value)",
        'separators=(",", ":")',
        "sort_keys=True",
        '"workflow-provenance.json"',
        '"executed-build-workflow.yml"',
    )
    for fragment in required_fragments:
        if fragment not in source:
            raise ValueError("provenance fragment missing: " + fragment)
    run = step["run"]
    receipt = run.index('"workflow-provenance.json"')
    precheck = run.index("sha256sum --check --strict PRECHECK_SHA256SUMS")
    final = run.index("sha256sum --check --strict SHA256SUMS")
    if not receipt < precheck < final:
        raise ValueError("provenance receipt is not manifest-bound")
    return source


class NativeRustExactBuildWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.source_workflow = SOURCE_WORKFLOW.read_text(encoding="utf-8")

    def provenance_git(self, repository, *arguments):
        completed = subprocess.run(
            ["git", "-C", str(repository)] + list(arguments),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return completed.stdout.decode("ascii").strip()

    def make_provenance_repository(self, root, matching_workflow_bytes=True):
        repository = root / "repository"
        repository.mkdir()
        self.provenance_git(repository, "init", "-q")
        self.provenance_git(repository, "config", "user.name", "Provenance fixture")
        self.provenance_git(
            repository,
            "config",
            "user.email",
            "provenance-fixture@example.invalid",
        )
        workflow_path = repository / PROVENANCE_WORKFLOW_PATH
        workflow_path.parent.mkdir(parents=True)
        workflow_path.write_bytes(b"name: exact fixture\n")
        self.provenance_git(repository, "add", "--", PROVENANCE_WORKFLOW_PATH)
        self.provenance_git(repository, "commit", "-q", "-m", "definition")
        defining_sha = self.provenance_git(repository, "rev-parse", "HEAD")
        if matching_workflow_bytes:
            (repository / "candidate.txt").write_bytes(b"candidate\n")
            self.provenance_git(repository, "add", "--", "candidate.txt")
        else:
            workflow_path.write_bytes(b"name: mutated candidate fixture\n")
            self.provenance_git(repository, "add", "--", PROVENANCE_WORKFLOW_PATH)
        self.provenance_git(repository, "commit", "-q", "-m", "candidate")
        candidate_sha = self.provenance_git(repository, "rev-parse", "HEAD")
        return repository, candidate_sha, defining_sha

    def provenance_environment(self, root, repository, candidate_sha, defining_sha):
        evidence = root / "evidence"
        evidence.mkdir()
        environment = dict(os.environ)
        environment.update(
            {
                "EVIDENCE_DIR": str(evidence),
                "GITHUB_RUN_ATTEMPT": "1",
                "GITHUB_RUN_ID": "32192199024",
                "GITHUB_WORKSPACE": str(repository),
                "PROVENANCE_CALLER_EVENT_NAME": "pull_request",
                "PROVENANCE_CALLER_REF": "refs/pull/7/merge",
                "PROVENANCE_CALLER_REPOSITORY": "example/project",
                "PROVENANCE_CALLER_SHA": defining_sha,
                "PROVENANCE_CALLER_WORKFLOW_REF": (
                    "example/project/.github/workflows/caller.yml@refs/pull/7/merge"
                ),
                "PROVENANCE_CALLER_WORKFLOW_SHA": defining_sha,
                "PROVENANCE_CANDIDATE_SHA": candidate_sha,
                "PROVENANCE_DEFINING_WORKFLOW_FILE_PATH": PROVENANCE_WORKFLOW_PATH,
                "PROVENANCE_DEFINING_WORKFLOW_REF": (
                    "example/project/"
                    + PROVENANCE_WORKFLOW_PATH
                    + "@refs/pull/7/merge"
                ),
                "PROVENANCE_DEFINING_WORKFLOW_REPOSITORY": "example/project",
                "PROVENANCE_DEFINING_WORKFLOW_SHA": defining_sha,
            }
        )
        return environment, evidence

    def run_provenance_source(self, source, environment, evidence):
        receipt = evidence / "workflow-provenance.json"
        if receipt.exists() or receipt.is_symlink():
            receipt.unlink()
        return subprocess.run(
            ["/usr/bin/python3", "-E", "-s", "-"],
            input=source.encode("utf-8"),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_workflow_provenance_context_bindings_are_exact_and_omission_closed(self):
        source = validate_provenance_structure(self.workflow)
        compile(source, "workflow-provenance.py", "exec")
        for name, binding in sorted(PROVENANCE_ENV_BINDINGS.items()):
            line = "          {0}: {1}\n".format(name, binding)
            self.assertEqual(self.workflow.count(line), 1, name)
            with self.subTest(name=name, attack="omitted"):
                mutation = self.workflow.replace(line, "", 1)
                with self.assertRaisesRegex(ValueError, "context bindings"):
                    validate_provenance_structure(mutation)
            with self.subTest(name=name, attack="retargeted"):
                mutation = self.workflow.replace(
                    line,
                    "          {0}: ${{{{ github.actor }}}}\n".format(name),
                    1,
                )
                with self.assertRaisesRegex(ValueError, "context bindings"):
                    validate_provenance_structure(mutation)

    def test_workflow_provenance_receipt_is_canonical_byte_bound_and_noncrediting(self):
        source = validate_provenance_structure(self.workflow)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, candidate_sha, defining_sha = self.make_provenance_repository(
                root
            )
            environment, evidence = self.provenance_environment(
                root, repository, candidate_sha, defining_sha
            )
            completed = self.run_provenance_source(source, environment, evidence)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", errors="replace"),
            )
            receipt_bytes = (evidence / "workflow-provenance.json").read_bytes()
            receipt = json.loads(receipt_bytes)
            self.assertEqual(
                receipt_bytes,
                (
                    json.dumps(
                        receipt,
                        allow_nan=False,
                        ensure_ascii=True,
                        separators=(",", ":"),
                        sort_keys=True,
                    )
                    + "\n"
                ).encode("ascii"),
            )
            self.assertEqual(receipt["candidate"]["sha"], candidate_sha)
            self.assertEqual(
                receipt["defining_job"]["workflow_sha"], defining_sha
            )
            self.assertEqual(receipt["caller"]["sha"], defining_sha)
            self.assertEqual(receipt["caller"]["workflow_sha"], defining_sha)
            self.assertEqual(
                receipt["caller"]["repository"],
                receipt["defining_job"]["workflow_repository"],
            )
            self.assertTrue(
                receipt["caller"]["workflow_ref"].endswith(
                    "@" + receipt["caller"]["ref"]
                )
            )
            self.assertTrue(
                receipt["defining_job"]["workflow_ref"].endswith(
                    "@" + receipt["caller"]["ref"]
                )
            )
            self.assertNotEqual(candidate_sha, defining_sha)
            self.assertEqual(
                receipt["candidate"]["workflow_file_git_blob_sha1"],
                receipt["defining_job"]["workflow_file_git_blob_sha1"],
            )
            self.assertEqual(
                receipt["candidate"]["workflow_file_sha256"],
                receipt["defining_job"]["workflow_file_sha256"],
            )
            executed_workflow = evidence / "executed-build-workflow.yml"
            self.assertEqual(
                executed_workflow.read_bytes(),
                (repository / PROVENANCE_WORKFLOW_PATH).read_bytes(),
            )
            self.assertEqual(
                stat.S_IMODE(executed_workflow.stat().st_mode), 0o644
            )
            self.assertEqual(
                hashlib.sha256(executed_workflow.read_bytes()).hexdigest(),
                receipt["defining_job"]["workflow_file_sha256"],
            )
            self.assertEqual(
                receipt["defining_job"]["evidence_file"],
                "executed-build-workflow.yml",
            )
            self.assertIs(receipt["workflow_file_bytes_equal"], True)
            self.assertIs(receipt["direct_workflow_dispatch"], False)
            self.assertEqual(receipt["github_run_id"], 32192199024)
            self.assertEqual(receipt["github_run_attempt"], 1)
            self.assertTrue(
                all(value is False for value in receipt["claims"].values())
            )

    def test_workflow_provenance_rejects_every_missing_runtime_field(self):
        source = provenance_python_source(self.workflow)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, candidate_sha, defining_sha = self.make_provenance_repository(
                root
            )
            environment, evidence = self.provenance_environment(
                root, repository, candidate_sha, defining_sha
            )
            for name in sorted(
                tuple(PROVENANCE_ENV_BINDINGS) + PROVENANCE_DEFAULT_ENV_FIELDS
            ):
                with self.subTest(name=name):
                    mutation = dict(environment)
                    del mutation[name]
                    completed = self.run_provenance_source(
                        source, mutation, evidence
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertFalse((evidence / "workflow-provenance.json").exists())

    def test_workflow_provenance_requires_canonical_positive_run_identity(self):
        source = provenance_python_source(self.workflow)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, candidate_sha, defining_sha = self.make_provenance_repository(
                root
            )
            environment, evidence = self.provenance_environment(
                root, repository, candidate_sha, defining_sha
            )
            for name in PROVENANCE_DEFAULT_ENV_FIELDS:
                for value in ("0", "01", "+1", "1 "):
                    with self.subTest(name=name, value=value):
                        mutation = dict(environment)
                        mutation[name] = value
                        completed = self.run_provenance_source(
                            source, mutation, evidence
                        )
                        self.assertNotEqual(completed.returncode, 0)
                        self.assertFalse(
                            (evidence / "workflow-provenance.json").exists()
                        )

    def test_workflow_provenance_rejects_sha_ref_repository_and_path_attacks(self):
        source = provenance_python_source(self.workflow)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, candidate_sha, defining_sha = self.make_provenance_repository(
                root
            )
            environment, evidence = self.provenance_environment(
                root, repository, candidate_sha, defining_sha
            )
            mutations = []
            for name in (
                "PROVENANCE_CANDIDATE_SHA",
                "PROVENANCE_CALLER_SHA",
                "PROVENANCE_CALLER_WORKFLOW_SHA",
                "PROVENANCE_DEFINING_WORKFLOW_SHA",
            ):
                mutations.extend(
                    (
                        (name + "-short", name, "0" * 39),
                        (name + "-nonhex", name, "g" * 40),
                        (name + "-uppercase", name, "A" * 40),
                    )
                )
            mutations.extend(
                (
                    (
                        "event-shape",
                        "PROVENANCE_CALLER_EVENT_NAME",
                        "pull-request",
                    ),
                    ("caller-ref-shape", "PROVENANCE_CALLER_REF", "development"),
                    (
                        "caller-repository-shape",
                        "PROVENANCE_CALLER_REPOSITORY",
                        "example/caller/extra",
                    ),
                    (
                        "caller-workflow-repository",
                        "PROVENANCE_CALLER_WORKFLOW_REF",
                        "attacker/repo/.github/workflows/caller.yml@refs/pull/7/merge",
                    ),
                    (
                        "defining-path-traversal",
                        "PROVENANCE_DEFINING_WORKFLOW_FILE_PATH",
                        "../workflow.yml",
                    ),
                    (
                        "defining-path-retarget",
                        "PROVENANCE_DEFINING_WORKFLOW_FILE_PATH",
                        ".github/workflows/other.yml",
                    ),
                    (
                        "defining-ref-repository",
                        "PROVENANCE_DEFINING_WORKFLOW_REF",
                        "attacker/repo/"
                        + PROVENANCE_WORKFLOW_PATH
                        + "@refs/pull/7/merge",
                    ),
                    (
                        "defining-repository-retarget",
                        "PROVENANCE_DEFINING_WORKFLOW_REPOSITORY",
                        "attacker/repo",
                    ),
                )
            )
            for label, name, value in mutations:
                with self.subTest(attack=label):
                    mutation = dict(environment)
                    mutation[name] = value
                    completed = self.run_provenance_source(
                        source, mutation, evidence
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertFalse((evidence / "workflow-provenance.json").exists())

    def test_workflow_provenance_rejects_nonlocal_event_alignment(self):
        source = provenance_python_source(self.workflow)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, candidate_sha, defining_sha = self.make_provenance_repository(
                root
            )
            environment, evidence = self.provenance_environment(
                root, repository, candidate_sha, defining_sha
            )
            attacks = (
                ("unsupported-event", {"PROVENANCE_CALLER_EVENT_NAME": "schedule"}),
                (
                    "pull-head-ref",
                    {
                        "PROVENANCE_CALLER_REF": "refs/pull/7/head",
                        "PROVENANCE_CALLER_WORKFLOW_REF": (
                            "example/project/.github/workflows/caller.yml"
                            "@refs/pull/7/head"
                        ),
                        "PROVENANCE_DEFINING_WORKFLOW_REF": (
                            "example/project/"
                            + PROVENANCE_WORKFLOW_PATH
                            + "@refs/pull/7/head"
                        ),
                    },
                ),
                (
                    "pull-leading-zero",
                    {
                        "PROVENANCE_CALLER_REF": "refs/pull/07/merge",
                        "PROVENANCE_CALLER_WORKFLOW_REF": (
                            "example/project/.github/workflows/caller.yml"
                            "@refs/pull/07/merge"
                        ),
                        "PROVENANCE_DEFINING_WORKFLOW_REF": (
                            "example/project/"
                            + PROVENANCE_WORKFLOW_PATH
                            + "@refs/pull/07/merge"
                        ),
                    },
                ),
                ("push-pr-ref", {"PROVENANCE_CALLER_EVENT_NAME": "push"}),
                (
                    "dispatch-pr-ref",
                    {"PROVENANCE_CALLER_EVENT_NAME": "workflow_dispatch"},
                ),
                (
                    "repository-mismatch",
                    {
                        "PROVENANCE_CALLER_REPOSITORY": "attacker/project",
                        "PROVENANCE_CALLER_WORKFLOW_REF": (
                            "attacker/project/.github/workflows/caller.yml"
                            "@refs/pull/7/merge"
                        ),
                    },
                ),
                ("caller-sha-mismatch", {"PROVENANCE_CALLER_SHA": "3" * 40}),
                (
                    "caller-workflow-sha-mismatch",
                    {"PROVENANCE_CALLER_WORKFLOW_SHA": "3" * 40},
                ),
                (
                    "defining-workflow-sha-mismatch",
                    {"PROVENANCE_DEFINING_WORKFLOW_SHA": candidate_sha},
                ),
                (
                    "caller-workflow-ref-mismatch",
                    {
                        "PROVENANCE_CALLER_WORKFLOW_REF": (
                            "example/project/.github/workflows/caller.yml"
                            "@refs/heads/development"
                        )
                    },
                ),
                (
                    "defining-workflow-ref-mismatch",
                    {
                        "PROVENANCE_DEFINING_WORKFLOW_REF": (
                            "example/project/"
                            + PROVENANCE_WORKFLOW_PATH
                            + "@refs/heads/development"
                        )
                    },
                ),
            )
            for label, changes in attacks:
                with self.subTest(attack=label):
                    mutation = dict(environment)
                    mutation.update(changes)
                    completed = self.run_provenance_source(
                        source, mutation, evidence
                    )
                    self.assertNotEqual(completed.returncode, 0)
                    self.assertFalse((evidence / "workflow-provenance.json").exists())

    def test_workflow_provenance_direct_dispatch_requires_one_commit(self):
        source = provenance_python_source(self.workflow)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, candidate_sha, defining_sha = self.make_provenance_repository(
                root
            )
            environment, evidence = self.provenance_environment(
                root, repository, candidate_sha, defining_sha
            )
            direct_ref = (
                "example/project/"
                + PROVENANCE_WORKFLOW_PATH
                + "@refs/heads/development"
            )
            environment.update(
                {
                    "PROVENANCE_CALLER_EVENT_NAME": "workflow_dispatch",
                    "PROVENANCE_CALLER_REF": "refs/heads/development",
                    "PROVENANCE_CALLER_REPOSITORY": "example/project",
                    "PROVENANCE_CALLER_SHA": candidate_sha,
                    "PROVENANCE_CALLER_WORKFLOW_REF": direct_ref,
                    "PROVENANCE_CALLER_WORKFLOW_SHA": candidate_sha,
                    "PROVENANCE_DEFINING_WORKFLOW_REF": direct_ref,
                    "PROVENANCE_DEFINING_WORKFLOW_SHA": candidate_sha,
                }
            )
            completed = self.run_provenance_source(source, environment, evidence)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", errors="replace"),
            )
            receipt = json.loads(
                (evidence / "workflow-provenance.json").read_text(encoding="ascii")
            )
            self.assertIs(receipt["direct_workflow_dispatch"], True)
            for name, value in (
                ("PROVENANCE_CANDIDATE_SHA", defining_sha),
                ("PROVENANCE_CALLER_WORKFLOW_SHA", defining_sha),
                ("PROVENANCE_DEFINING_WORKFLOW_SHA", defining_sha),
                (
                    "PROVENANCE_CALLER_WORKFLOW_REF",
                    "example/project/"
                    + PROVENANCE_WORKFLOW_PATH
                    + "@refs/heads/other",
                ),
            ):
                with self.subTest(name=name):
                    mutation = dict(environment)
                    mutation[name] = value
                    completed = self.run_provenance_source(
                        source, mutation, evidence
                    )
                    self.assertNotEqual(completed.returncode, 0)

    def test_workflow_provenance_rejects_candidate_definition_byte_drift(self):
        source = provenance_python_source(self.workflow)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, candidate_sha, defining_sha = self.make_provenance_repository(
                root, matching_workflow_bytes=False
            )
            environment, evidence = self.provenance_environment(
                root, repository, candidate_sha, defining_sha
            )
            completed = self.run_provenance_source(source, environment, evidence)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "blob IDs differ",
                completed.stderr.decode("utf-8", errors="replace"),
            )

    def test_workflow_provenance_fetches_and_verifies_missing_definition_commit(self):
        source = provenance_python_source(self.workflow)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            definition = root / "definition"
            definition.mkdir()
            self.provenance_git(definition, "init", "-q")
            self.provenance_git(definition, "config", "user.name", "Definition")
            self.provenance_git(
                definition,
                "config",
                "user.email",
                "definition@example.invalid",
            )
            definition_workflow = definition / PROVENANCE_WORKFLOW_PATH
            definition_workflow.parent.mkdir(parents=True)
            definition_workflow.write_bytes(b"name: exact fixture\n")
            self.provenance_git(definition, "add", "--", PROVENANCE_WORKFLOW_PATH)
            self.provenance_git(definition, "commit", "-q", "-m", "definition")
            defining_sha = self.provenance_git(definition, "rev-parse", "HEAD")
            self.provenance_git(
                definition, "update-ref", "refs/pull/7/merge", defining_sha
            )

            candidate = root / "candidate"
            candidate.mkdir()
            self.provenance_git(candidate, "init", "-q")
            self.provenance_git(candidate, "config", "user.name", "Candidate")
            self.provenance_git(
                candidate,
                "config",
                "user.email",
                "candidate@example.invalid",
            )
            candidate_workflow = candidate / PROVENANCE_WORKFLOW_PATH
            candidate_workflow.parent.mkdir(parents=True)
            candidate_workflow.write_bytes(b"name: exact fixture\n")
            self.provenance_git(candidate, "add", "--", PROVENANCE_WORKFLOW_PATH)
            self.provenance_git(candidate, "commit", "-q", "-m", "candidate")
            candidate_sha = self.provenance_git(candidate, "rev-parse", "HEAD")
            self.assertNotEqual(candidate_sha, defining_sha)
            missing = subprocess.run(
                [
                    "git",
                    "-C",
                    str(candidate),
                    "cat-file",
                    "-e",
                    defining_sha + "^{commit}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(missing.returncode, 0)
            self.provenance_git(
                candidate,
                "config",
                "url.file://{0}.insteadOf".format(definition),
                "https://github.com/example/project.git",
            )
            environment, evidence = self.provenance_environment(
                root, candidate, candidate_sha, defining_sha
            )
            completed = self.run_provenance_source(source, environment, evidence)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", errors="replace"),
            )
            self.assertEqual(
                self.provenance_git(
                    candidate, "rev-parse", "--verify", defining_sha + "^{commit}"
                ),
                defining_sha,
            )
            forged = dict(environment)
            forged["PROVENANCE_CALLER_SHA"] = "f" * 40
            forged["PROVENANCE_CALLER_WORKFLOW_SHA"] = "f" * 40
            forged["PROVENANCE_DEFINING_WORKFLOW_SHA"] = "f" * 40
            completed = self.run_provenance_source(source, forged, evidence)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn(
                "fetched defining workflow commit differs",
                completed.stderr.decode("utf-8", errors="replace"),
            )

    def test_workflow_provenance_ignores_git_redirection_environment(self):
        source = provenance_python_source(self.workflow)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository, candidate_sha, defining_sha = self.make_provenance_repository(
                root
            )
            environment, evidence = self.provenance_environment(
                root, repository, candidate_sha, defining_sha
            )
            attacker = root / "attacker"
            attacker.mkdir()
            self.provenance_git(attacker, "init", "-q")
            environment.update(
                {
                    "GIT_CONFIG_COUNT": "1",
                    "GIT_CONFIG_KEY_0": "core.repositoryformatversion",
                    "GIT_CONFIG_VALUE_0": "999",
                    "GIT_DIR": str(attacker / ".git"),
                    "GIT_INDEX_FILE": str(attacker / "index"),
                    "GIT_REPLACE_REF_BASE": "refs/attacker/replace/",
                    "GIT_WORK_TREE": str(attacker),
                }
            )
            completed = self.run_provenance_source(source, environment, evidence)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr.decode("utf-8", errors="replace"),
            )

    def test_workflow_provenance_is_in_both_evidence_manifests(self):
        validate_provenance_structure(self.workflow)
        run = provenance_step(self.workflow)["run"]
        receipt = run.index('"workflow-provenance.json"')
        executed_workflow = run.index('"executed-build-workflow.yml"')
        precheck_write = run.index("> PRECHECK_SHA256SUMS")
        final_write = run.index("> SHA256SUMS")
        self.assertLess(receipt, precheck_write)
        self.assertLess(executed_workflow, precheck_write)
        self.assertLess(precheck_write, final_write)
        self.assertIn(
            "! -name PRECHECK_SHA256SUMS ! -name SHA256SUMS",
            run[receipt:precheck_write],
        )
        self.assertIn(
            "find . -maxdepth 1 -type f ! -name SHA256SUMS",
            run[precheck_write:final_write],
        )

    def test_runtime_and_actions_are_digest_pinned(self):
        image = (
            "rockylinux/rockylinux:10.2@sha256:"
            "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
        )
        self.assertGreaterEqual(self.workflow.count(image), 2)
        uses = re.findall(r"^\s*uses:\s*(\S+)", self.workflow, re.MULTILINE)
        self.assertTrue(uses)
        for value in uses:
            self.assertRegex(value, r"^[^@]+@[0-9a-f]{40}$")

    def test_exact_build_job_cannot_skip_or_tolerate_failure(self):
        anchor = "  exact-build:\n"
        mutations = (
            self.workflow.replace(anchor, anchor + "    if: ${{ false }}\n", 1),
            self.workflow.replace(anchor, anchor + '    "if": ${{ false }}\n', 1),
            self.workflow.replace(anchor, anchor + "    continue-on-error: true\n", 1),
            self.workflow.replace(anchor, anchor + "    strategy:\n      fail-fast: false\n", 1),
            self.workflow.replace("    timeout-minutes: 330\n", "    timeout-minutes: 1\n", 1),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError, "job scope differs"
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_every_shell_block_parses(self):
        workflow = yaml.safe_load(self.workflow)
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                script = step.get("run")
                if script:
                    completed = subprocess.run(
                        ["bash", "-n"],
                        input=script.encode("utf-8"),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                    self.assertEqual(
                        completed.returncode,
                        0,
                        "{}: {}".format(
                            step.get("name", "unnamed step"),
                            completed.stderr.decode("utf-8", errors="replace"),
                        ),
                    )

    def test_shell_arrays_are_defined_in_the_same_step_before_use(self):
        workflow = yaml.safe_load(self.workflow)
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                script = step.get("run")
                if not script:
                    continue
                for name in ("kbuild_environment",):
                    use = '"${' + name + '[@]}"'
                    if use not in script:
                        continue
                    match = re.search(
                        r"(?m)^\s*" + re.escape(name) + r"=\(", script
                    )
                    self.assertIsNotNone(match, (step.get("name"), name))
                    self.assertLess(
                        match.start(),
                        script.index(use),
                        (step.get("name"), name),
                    )

    def test_stage_is_explicitly_credit_forbidden(self):
        self.assertIn("--stage-for-evidence", self.workflow)
        self.assertIn("--verify-evidence-stage", self.workflow)
        self.assertNotRegex(self.workflow, r"(?m)^\s+--stage\s")
        self.assertIn("credit forbidden", self.workflow)

    def test_reusable_exact_build_exports_a_bootable_kernel(self):
        self.assertIn("workflow_call:", self.workflow)
        self.assertIn(
            "EXPECTED_HEAD_SHA: ${{ inputs.validation_sha || "
            "github.event.pull_request.head.sha || github.sha }}",
            self.workflow,
        )
        self.assertIn(
            "EXPECTED_KERNEL_RELEASE: " + runtime_evidence.EXPECTED_KERNEL_RELEASE,
            self.workflow,
        )
        self.assertIn(
            "NATIVE_KERNEL_LOCALVERSION: "
            + runtime_evidence.EXPECTED_KERNEL_LOCALVERSION,
            self.workflow,
        )
        self.assertIn(
            '"${kbuild_environment[@]}" /usr/bin/make -C "$NATIVE_SOURCE_ROOT"',
            self.workflow,
        )
        self.assertIn(
            'KBUILD_BUILD_TIMESTAMP="$KBUILD_BUILD_TIMESTAMP"',
            self.workflow,
        )
        self.assertLess(
            self.workflow.index("-j2 bzImage"),
            self.workflow.index(
                '-j2 "${module_targets[@]}"'
            ),
        )
        self.assertNotRegex(self.workflow, r"(?m)^\s*make\s+.*\bmodules\b")
        self.assertIn(
            'cp "$NATIVE_BUILD_DIR/arch/x86/boot/bzImage" "$EVIDENCE_DIR/bzImage"',
            self.workflow,
        )
        self.assertIn(
            'printf \'%s\\n\' "$kernel_release" > "$EVIDENCE_DIR/kernel.release"',
            self.workflow,
        )
        self.assertIn("include-hidden-files: true", self.workflow)

    def test_reproducible_build_identity_is_global_and_retained(self):
        for name in runtime_evidence.EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT_NAMES:
            value = runtime_evidence.EXPECTED_REPRODUCIBLE_BUILD_ENVIRONMENT[name]
            rendered = '"{}"'.format(value) if name in {
                "KBUILD_BUILD_TIMESTAMP",
                "KBUILD_BUILD_VERSION",
                "SOURCE_DATE_EPOCH",
            } else value
            self.assertEqual(
                1,
                len(
                    re.findall(
                        r"(?m)^  {0}: {1}$".format(
                            re.escape(name), re.escape(rendered)
                        ),
                        self.workflow,
                    )
                ),
            )
            self.assertEqual(32, self.workflow.count(name))
            self.assertIn('"{}=${}"'.format(name, name), self.workflow)
        self.assertIn(
            '> "$evidence_dir/build.environment"', self.workflow
        )

    def test_reproducible_build_environment_shadow_and_override_are_rejected(self):
        compile_header = "      - name: Compile the exact kernel and native Rust modules\n"
        compile_start = self.workflow.index(compile_header)
        run_start = self.workflow.index("        run: |\n", compile_start)
        run_marker = self.workflow[compile_start : run_start + len("        run: |\n")]
        runner = '            "${command[@]}"\n'
        make_line = (
            '              "${kbuild_environment[@]}" /usr/bin/make -C "$NATIVE_SOURCE_ROOT" \\\n'
        )
        mutations = (
            self.workflow.replace(
                "    timeout-minutes: 330\n",
                "    timeout-minutes: 330\n"
                "    env:\n"
                "      KBUILD_BUILD_USER: attacker\n",
                1,
            ),
            self.workflow.replace(
                run_marker,
                compile_header + "        env:\n"
                "          KBUILD_BUILD_USER: attacker\n"
                + run_marker[len(compile_header) :],
                1,
            ),
            self.workflow.replace(run_marker, run_marker + "          export KBUILD_BUILD_USER=attacker\n", 1),
            self.workflow.replace(run_marker, run_marker + "          unset KBUILD_BUILD_USER\n", 1),
            self.workflow.replace(
                run_marker,
                run_marker
                + "          printf 'KBUILD_BUILD_USER=attacker\\n' >> \"$GITHUB_ENV\"\n",
                1,
            ),
            self.workflow.replace(
                runner, '            env -u KBUILD_BUILD_USER "${command[@]}"\n', 1
            ),
            self.workflow.replace(
                make_line,
                make_line + '                KBUILD_BUILD_USER=attacker \\\n',
                1,
            ),
        )
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(runtime_evidence.EvidenceError):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_every_later_kbuild_boundary_reasserts_each_canonical_value(self):
        boundaries = (
            (
                "      - name: Resolve the evidence-only module configuration twice\n",
                "      - name: Compile the exact kernel and native Rust modules\n",
            ),
            (
                "      - name: Compile the exact kernel and native Rust modules\n",
                "      - name: Validate built metadata and capture immutable diagnostics\n",
            ),
            (
                "      - name: Validate built metadata and capture immutable diagnostics\n",
                "      - name: Upload compiler evidence or first-failure diagnostics\n",
            ),
        )
        for start, end in boundaries:
            block = self.workflow.split(start, 1)[1].split(end, 1)[0]
            first_make = block.find("make ")
            self.assertGreater(first_make, 0)
            for assertion in runtime_evidence.EXPECTED_REPRODUCIBLE_BUILD_ASSERTION_COMMANDS:
                rendered = "          " + assertion + "\n"
                with self.subTest(boundary=start.strip(), assertion=assertion):
                    self.assertEqual(1, block.count(rendered))
                    self.assertLess(block.index(rendered), first_make)

                    mutation = self.workflow.replace(
                        start + block,
                        start + block.replace(rendered, rendered.replace(" = ", " != "), 1),
                        1,
                    )
                    with self.assertRaises(runtime_evidence.EvidenceError):
                        runtime_evidence._validate_exact_build_workflow(mutation)

    def test_critical_shell_startup_and_command_channels_are_fail_closed(self):
        document = yaml.safe_load(self.workflow)
        loader_keys = {
            "GLIBC_TUNABLES",
            "LD_ASSUME_KERNEL",
            "LD_AUDIT",
            "LD_BIND_NOW",
            "LD_DEBUG",
            "LD_DEBUG_OUTPUT",
            "LD_DYNAMIC_WEAK",
            "LD_HWCAP_MASK",
            "LD_LIBRARY_PATH",
            "LD_ORIGIN_PATH",
            "LD_PREFER_MAP_32BIT_EXEC",
            "LD_PRELOAD",
            "LD_PROFILE",
            "LD_PROFILE_OUTPUT",
        }
        exact_names = {
            "Verify source-only contracts without claiming readiness",
            "Acquire, patch, and credit-forbidden-stage the exact source",
            "Resolve the evidence-only module configuration twice",
            "Compile the exact kernel and native Rust modules",
            "Validate built metadata and capture immutable diagnostics",
        }
        rk006_names = {
            "Verify the frozen non-crediting RK-006 capture contract",
            "Reacquire and capture the full external 26-patch source replay",
            "Finalize the non-crediting build binding",
        }
        for job_name, names in (("exact-build", exact_names), ("rk006-full-source-build-capture", rk006_names)):
            job = document["jobs"][job_name]
            self.assertEqual(
                "/usr/bin/bash --noprofile --norc -p -e -o pipefail {0}",
                job["defaults"]["run"]["shell"],
            )
            steps = {step["name"]: step for step in job["steps"] if "run" in step}
            for name in names:
                with self.subTest(job=job_name, step=name):
                    environment = steps[name]["env"]
                    self.assertEqual({key: "" for key in loader_keys}, {key: environment[key] for key in loader_keys})
                    self.assertNotIn("LD_SHOW_AUXV", environment)
                    self.assertEqual("/usr/sbin:/usr/bin:/sbin:/bin", environment["PATH"])
                    run_lines = [
                        line.strip()
                        for line in steps[name]["run"].splitlines()
                        if line.strip()
                    ]
                    self.assertEqual(
                        ["set -euo pipefail", "unset LD_SHOW_AUXV"],
                        run_lines[:2],
                    )
                    self.assertIn("unset GITHUB_ENV GITHUB_PATH", steps[name]["run"])

        for old, new in (
            ('          LD_AUDIT: ""\n', '          LD_AUDIT: /tmp/attacker.so\n'),
            (
                '          LD_PROFILE_OUTPUT: ""\n',
                '          LD_PROFILE_OUTPUT: ""\n'
                '          LD_SHOW_AUXV: ""\n',
            ),
            ('          PATH: /usr/sbin:/usr/bin:/sbin:/bin\n', '          PATH: /tmp/attacker\n'),
            (
                "          set -euo pipefail\n          unset LD_SHOW_AUXV\n",
                "          set -euo pipefail\n",
            ),
            (
                "          set -euo pipefail\n          unset LD_SHOW_AUXV\n",
                "          unset LD_SHOW_AUXV\n          set -euo pipefail\n",
            ),
            ('          : > "$github_env_file"\n', "          printf 'LD_AUDIT=/tmp/attacker.so\\n' > \"$github_env_file\"\n"),
        ):
            mutation = self.workflow.replace(old, new, 1)
            self.assertNotEqual(self.workflow, mutation)
            with self.assertRaises(runtime_evidence.EvidenceError):
                runtime_evidence._validate_exact_build_workflow(mutation)

    def test_empty_ld_show_auxv_is_startup_active_not_neutral(self):
        command = [
            "/usr/bin/env",
            "-i",
            "PATH=/usr/bin:/bin",
            "/usr/bin/bash",
            "--noprofile",
            "--norc",
            "-p",
            "-c",
            "unset LD_SHOW_AUXV; printf 'payload-only\\n'",
        ]
        clean = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )
        contaminated = subprocess.run(
            command[:3] + ["LD_SHOW_AUXV="] + command[3:],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
        )
        self.assertEqual(b"payload-only\n", clean.stdout)
        self.assertIn(b"AT_EXECFN:", contaminated.stdout)
        self.assertTrue(contaminated.stdout.endswith(b"payload-only\n"))

    def test_packaged_modinfo_symlink_is_exact_and_owner_bound(self):
        document = yaml.safe_load(self.workflow)
        step = next(
            step
            for step in document["jobs"]["exact-build"]["steps"]
            if step.get("name")
            == "Validate built metadata and capture immutable diagnostics"
        )
        script = step["run"]
        sequence = [
            "expected_modinfo_nevra=kmod-31-13.el10.x86_64",
            "expected_modinfo_sha256=7e91f52ed2cd5e2c4f82de4bb07bbaa7179cd5c053b7afcf2fd231056681ed55",
            'modinfo_path="$(command -v modinfo)"',
            "modinfo_target=/usr/bin/kmod",
            'test "$modinfo_path" = /usr/sbin/modinfo',
            "test -x /usr/sbin/modinfo",
            "test -L /usr/sbin/modinfo",
            'test "$(/usr/bin/readlink -- /usr/sbin/modinfo)" = ../bin/kmod',
            'test -x "$modinfo_target"',
            'test ! -L "$modinfo_target"',
            'exec {modinfo_fd}<"$modinfo_target"',
            'modinfo_exec="/proc/self/fd/$modinfo_fd"',
            'test -r "$modinfo_exec"',
            "assert_modinfo_binding() {",
            'test "$modinfo_path" -ef "$modinfo_exec" &&',
            'test "$modinfo_target" -ef "$modinfo_exec" &&',
            'test "$(/usr/bin/sha256sum -- "$modinfo_exec")" = \\',
            'test "$(/usr/bin/rpm -q --qf \'%{NEVRA}\\n\' kmod)" = \\',
            'test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' "$modinfo_path")" = kmod &&',
            'test "$(/usr/bin/rpm -qf --qf \'%{NAME}\\n\' "$modinfo_target")" = kmod',
            "run_modinfo() (",
            'exec -a modinfo "$modinfo_exec" "$@"',
        ]
        positions = [script.index(fragment) for fragment in sequence]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(
            1,
            script.count(
                'run_modinfo "$module" > "$EVIDENCE_DIR/$name.modinfo"'
            ),
        )
        self.assertEqual(
            1,
            script.count('vermagic="$(run_modinfo -F vermagic "$module")"'),
        )
        self.assertNotIn('"$modinfo_path" "$module"', script)
        self.assertNotIn('"$modinfo_path" -F vermagic', script)
        self.assertEqual(3, script.count('--modinfo-fd "$modinfo_fd"'))
        owner_lookup = script.index("/usr/bin/rpm -q --qf")
        binding_calls = [
            match.start()
            for match in re.finditer(r"(?m)^assert_modinfo_binding$", script)
        ]
        self.assertEqual(6, len(binding_calls))
        self.assertLess(owner_lookup, binding_calls[0])
        final_recheck = script.rindex("assert_modinfo_binding")
        close_descriptor = script.index("exec {modinfo_fd}<&-")
        self.assertLess(script.index("vermagic=\"$(run_modinfo"), final_recheck)
        self.assertLess(script.index("scripts/mcctrl_native_lifecycle_check.py"), final_recheck)
        self.assertLess(final_recheck, close_descriptor)
        self.assertIn(
            'kbuild_environment=("${isolated_environment[@]}" PATH=/usr/bin:/bin)',
            script,
        )
        isolated_definition = script.index("isolated_environment=(")
        kbuild_definition = script.index(
            'kbuild_environment=("${isolated_environment[@]}"'
        )
        self.assertLess(isolated_definition, kbuild_definition)
        self.assertNotIn("checker_environment", script)
        self.assertNotIn("checker_tool_dir", script)

        mutations = (
            (
                "          test -L /usr/sbin/modinfo\n",
                "          test -e /usr/sbin/modinfo\n",
            ),
            (
                '          test "$(/usr/bin/readlink -- /usr/sbin/modinfo)" = ../bin/kmod\n',
                '          test -n "$(/usr/bin/readlink -- /usr/sbin/modinfo)"\n',
            ),
            (
                '              test "$modinfo_path" -ef "$modinfo_exec" &&\n',
                "",
            ),
            (
                '              test "$modinfo_target" -ef "$modinfo_exec" &&\n',
                "",
            ),
            (
                (
                    '              test "$(/usr/bin/sha256sum -- "$modinfo_exec")" = \\\n'
                    '              "$expected_modinfo_sha256  $modinfo_exec" &&\n'
                ),
                "",
            ),
            (
                '              exec -a modinfo "$modinfo_exec" "$@"\n',
                '              "$modinfo_path" "$@"\n',
            ),
            (
                '            run_modinfo "$module" > "$EVIDENCE_DIR/$name.modinfo"\n',
                '            "$modinfo_path" "$module" > "$EVIDENCE_DIR/$name.modinfo"\n',
            ),
            (
                (
                    '              test "$(/usr/bin/rpm -q --qf \'%{NEVRA}\\n\' kmod)" = \\\n'
                    '              "$expected_modinfo_nevra" &&\n'
                ),
                "",
            ),
            (
                '            --module "$ihk" --modinfo-fd "$modinfo_fd"\n',
                '            --module "$ihk"\n',
            ),
            (
                '            --module "$smp" --modinfo-fd "$modinfo_fd"\n',
                '            --module "$smp"\n',
            ),
            (
                '            --module "$mcctrl" --modinfo-fd "$modinfo_fd"\n',
                '            --module "$mcctrl"\n',
            ),
            (
                (
                    '            --module "$ihk" --modinfo-fd "$modinfo_fd"\n'
                    '          assert_modinfo_binding\n'
                ),
                '            --module "$ihk" --modinfo-fd "$modinfo_fd"\n',
            ),
            (
                (
                    '          assert_modinfo_binding\n'
                    '          "${kbuild_environment[@]}" /usr/bin/python3 -E -s \\\n'
                    '            scripts/ihk_native_lifecycle_check.py'
                ),
                (
                    '          exec {modinfo_fd}<&-\n'
                    '          "${kbuild_environment[@]}" /usr/bin/python3 -E -s \\\n'
                    '            scripts/ihk_native_lifecycle_check.py'
                ),
            ),
        )
        for old, new in mutations:
            mutation = self.workflow.replace(old, new, 1)
            self.assertNotEqual(self.workflow, mutation)
            with self.subTest(new=new.strip()):
                with self.assertRaises(runtime_evidence.EvidenceError):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_retained_modinfo_descriptor_rejects_namespace_and_content_attacks(self):
        shell = r"""
set -euo pipefail
root=$1
attack=$2
modinfo_path="$root/usr/sbin/modinfo"
modinfo_target="$root/usr/bin/kmod"
attacker="$root/usr/bin/attacker"
exec {modinfo_fd}<"$modinfo_target"
modinfo_exec="/proc/self/fd/$modinfo_fd"
expected_sha256="$(/usr/bin/sha256sum -- "$modinfo_exec")"
assert_binding() {
  test -L "$modinfo_path" &&
  test "$(/usr/bin/readlink -- "$modinfo_path")" = ../bin/kmod &&
  test ! -L "$modinfo_target" &&
  test "$modinfo_path" -ef "$modinfo_exec" &&
  test "$modinfo_target" -ef "$modinfo_exec" &&
  test "$(/usr/bin/sha256sum -- "$modinfo_exec")" = "$expected_sha256"
}
assert_binding
case "$attack" in
  pre-owner-alias-retarget)
    /usr/bin/ln -sfn ../bin/attacker "$modinfo_path"
    ;;
  post-owner-target-replacement)
    : simulated-owner-lookup-complete
    /usr/bin/mv -- "$attacker" "$modinfo_target"
    ;;
  post-owner-content-replacement)
    : simulated-owner-lookup-complete
    /usr/bin/cp -- /usr/bin/false "$modinfo_target"
    ;;
  *) exit 80 ;;
esac
if assert_binding; then
  exit 81
fi
if test "$attack" != post-owner-content-replacement; then
  (exec -a modinfo "$modinfo_exec")
  if "$modinfo_path"; then
    exit 82
  fi
fi
exec {modinfo_fd}<&-
"""
        for attack in (
            "pre-owner-alias-retarget",
            "post-owner-target-replacement",
            "post-owner-content-replacement",
        ):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                binary = root / "usr/bin"
                sbin = root / "usr/sbin"
                binary.mkdir(parents=True)
                sbin.mkdir(parents=True)
                shutil.copy2("/usr/bin/true", binary / "kmod")
                shutil.copy2("/usr/bin/false", binary / "attacker")
                (sbin / "modinfo").symlink_to("../bin/kmod")
                completed = subprocess.run(
                    [
                        "/usr/bin/bash",
                        "--noprofile",
                        "--norc",
                        "-p",
                        "-c",
                        shell,
                        "descriptor-test",
                        str(root),
                        attack,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                self.assertEqual(
                    0,
                    completed.returncode,
                    completed.stderr.decode("utf-8", errors="replace"),
                )

    def test_retained_descriptor_exec_preserves_modinfo_argv0(self):
        shell = r"""
set -euo pipefail
exec {modinfo_fd}</usr/bin/bash
modinfo_exec="/proc/self/fd/$modinfo_fd"
(exec -a modinfo "$modinfo_exec" --noprofile --norc -p -c 'test "$0" = modinfo')
exec {modinfo_fd}<&-
"""
        completed = subprocess.run(
            [
                "/usr/bin/bash",
                "--noprofile",
                "--norc",
                "-p",
                "-c",
                shell,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(
            0,
            completed.returncode,
            completed.stderr.decode("utf-8", errors="replace"),
        )

    def test_each_later_boundary_rejects_prior_github_env_override(self):
        injections = (
            (
                '          printf \'NATIVE_BASELINE_CONFIG=%s\\n\' "$baseline" >> "$github_env_file"\n',
                '          printf \'KBUILD_BUILD_USER=attacker\\n\' >> "$github_env_file"\n',
            ),
            (
                '          printf \'NATIVE_BUILD_DIR=%s\\n\' "$BUILD_DIR" >> "$github_env_file"\n',
                '          printf \'KBUILD_BUILD_HOST=attacker\\n\' >> "$github_env_file"\n',
            ),
            (
                '          printf \'%s\\n\' "$tee_status" > "$evidence_dir/build-log.exit-code"\n',
                '          printf \'SOURCE_DATE_EPOCH=1\\n\' >> "$github_env_file"\n',
            ),
        )
        for anchor, injection in injections:
            mutation = self.workflow.replace(anchor, anchor + injection, 1)
            self.assertNotEqual(self.workflow, mutation)
            with self.subTest(injection=injection.strip()):
                with self.assertRaises(runtime_evidence.EvidenceError):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_module_modpost_cannot_precede_kernel_symbol_universe(self):
        bzimage = "            run_phase bzImage \\\n"
        modules = "            run_phase native-modules \\\n"
        self.assertEqual(1, self.workflow.count(bzimage))
        self.assertEqual(1, self.workflow.count(modules))
        mutation = self.workflow.replace(bzimage, "__BUILD_PHASE__\n", 1)
        mutation = mutation.replace(modules, bzimage, 1)
        mutation = mutation.replace("__BUILD_PHASE__\n", modules, 1)
        with self.assertRaisesRegex(
            runtime_evidence.EvidenceError, "commands are out of order|command scope"
        ):
            runtime_evidence._validate_exact_build_workflow(mutation)

    def test_symbol_universe_failure_cannot_be_downgraded_or_injected(self):
        for forbidden in (
            "modules_prepare",
            "Module.symvers",
            "KBUILD_MODPOST_WARN",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.workflow)

    def test_build_scope_checker_binds_supported_in_tree_single_targets(self):
        runtime_evidence._validate_exact_build_workflow(self.workflow)
        targets = runtime_evidence.BUILD_MODULE_TARGETS
        self.assertEqual(
            [
                "drivers/misc/mckernel/ihk.ko",
                "drivers/misc/mckernel/ihk-smp-x86_64.ko",
                "drivers/misc/mckernel/mcctrl.ko",
            ],
            targets,
        )
        for target in targets:
            self.assertEqual(1, self.workflow.count("            " + target + "\n"))
        for path in (
            "host-kernel/contracts/native-rust-runtime-evidence-v1.json",
            "scripts/native_rust_runtime_evidence.py",
        ):
            self.assertEqual(2, self.workflow.count("      - " + path))
        self.assertIn(
            "/usr/bin/python3 -E -s scripts/native_rust_runtime_evidence.py \\\n"
            '            --repo "$GITHUB_WORKSPACE" --check-contract',
            self.workflow,
        )

    def test_broad_module_build_mutation_is_rejected(self):
        mutation = self.workflow.replace(
            '-j2 "${module_targets[@]}"',
            "-j2 modules",
            1,
        )
        with self.assertRaisesRegex(
            runtime_evidence.EvidenceError,
            "command scope|broad module build",
        ):
            runtime_evidence._validate_exact_build_workflow(mutation)

    def test_partial_module_target_mutation_is_rejected(self):
        mutation = self.workflow.replace(
            "            drivers/misc/mckernel/mcctrl.ko\n", "", 1
        )
        with self.assertRaisesRegex(
            runtime_evidence.EvidenceError, "module target scope"
        ):
            runtime_evidence._validate_exact_build_workflow(mutation)

    def test_build_phase_and_exact_artifact_scope_are_bound(self):
        for fragment in (
            'printf \'%s\\n\' "$phase" > "$evidence_dir/build.phase"',
            'printf \'%s\\n\' "$producer_status" > "$evidence_dir/build.exit-code"',
            'printf \'%s\\n\' "$tee_status" > "$evidence_dir/build-log.exit-code"',
            'tee "$evidence_dir/build.log"',
            "find . -type f -name '*.ko' -printf '%P\\n' | LC_ALL=C sort",
            '> "$EVIDENCE_DIR/built-module-artifacts.txt"',
            'cmp "$EVIDENCE_DIR/module-targets.sorted"',
        ):
            self.assertIn(fragment, self.workflow)

    def test_rustavailable_failure_cannot_be_masked(self):
        for old, new in (
            ("(\n            set -e\n", "(\n            set +e\n"),
            ('            "${command[@]}"\n', '            "${command[@]}" || true\n'),
            (
                '                rustavailable\n',
                '                rustavailable || true\n',
            ),
        ):
            mutation = self.workflow.replace(old, new, 1)
            with self.subTest(mutation=new.strip()):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError,
                    "failure (capture|evidence)|masks a phase failure|command scope",
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_pipeline_status_capture_cannot_be_weakened(self):
        for old, new in (
            ("          set +e\n", ""),
            (
                '          pipeline_status=("${PIPESTATUS[@]}")\n',
                '          pipeline_status=(0 0)\n',
            ),
            (
                '          pipeline_status=("${PIPESTATUS[@]}")\n',
                '          true\n          pipeline_status=("${PIPESTATUS[@]}")\n',
            ),
            (
                "          if (( producer_status != 0 )); then\n",
                "          producer_status=0\n"
                "          if (( producer_status != 0 )); then\n",
            ),
            (
                '          printf \'%s\\n\' "$tee_status" '
                '> "$evidence_dir/build-log.exit-code"\n',
                "",
            ),
        ):
            mutation = self.workflow.replace(old, new, 1)
            with self.subTest(mutation=new.strip() or "removed"):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError, "failure (capture|evidence)"
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_compile_commands_must_be_active_and_compile_step_scoped(self):
        phase_markers = (
            "            run_phase rustavailable \\\n",
            "            run_phase bzImage \\\n",
            "            run_phase native-modules \\\n",
        )
        mutations = []
        for marker in phase_markers:
            self.assertEqual(1, self.workflow.count(marker))
            mutations.append(
                ("commented-" + marker.split()[1], self.workflow.replace(marker, "            # " + marker.lstrip(), 1))
            )
        decoy = self.workflow.replace(
            "      - name: Validate built metadata and capture immutable diagnostics\n",
            "      - name: Decoy build commands\n"
            "        run: |\n"
            "          run_phase bzImage /usr/bin/false\n\n"
            "      - name: Validate built metadata and capture immutable diagnostics\n",
            1,
        )
        conditional_runner = self.workflow.replace(
            '            "${command[@]}"\n',
            "            if false; then\n"
            '              "${command[@]}"\n'
            "            fi\n",
            1,
        )
        mutations.extend((("decoy-step", decoy), ("conditional-runner", conditional_runner)))
        for label, mutation in mutations:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError,
                    "Kbuild release scope|command scope|compile step|failure capture|steps",
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_artifact_scope_must_be_active_and_metadata_step_scoped(self):
        artifact_block = (
            "          (\n"
            '            cd "$NATIVE_BUILD_DIR"\n'
            "            find . -type f -name '*.ko' -printf '%P\\n' | LC_ALL=C sort\n"
            '          ) > "$EVIDENCE_DIR/built-module-artifacts.txt"\n'
            '          LC_ALL=C sort "$EVIDENCE_DIR/module-targets.txt" \\\n'
            '            > "$EVIDENCE_DIR/module-targets.sorted"\n'
            '          cmp "$EVIDENCE_DIR/module-targets.sorted" \\\n'
            '            "$EVIDENCE_DIR/built-module-artifacts.txt"\n'
            '          rm "$EVIDENCE_DIR/module-targets.sorted"\n'
        )
        self.assertEqual(1, self.workflow.count(artifact_block))
        conditional = self.workflow.replace(
            artifact_block,
            "          if false; then\n" + artifact_block + "          fi\n",
            1,
        )
        commented_block = "".join(
            "          # " + line.lstrip() if line.strip() else line
            for line in artifact_block.splitlines(True)
        )
        commented = self.workflow.replace(artifact_block, commented_block, 1)
        decoy = self.workflow.replace(artifact_block, "", 1).replace(
            "      - name: Upload compiler evidence or first-failure diagnostics\n",
            "      - name: Decoy artifact check\n"
            "        run: |\n"
            + artifact_block
            + "\n      - name: Upload compiler evidence or first-failure diagnostics\n",
            1,
        )
        for label, mutation in (
            ("conditional", conditional),
            ("commented", commented),
            ("decoy-step", decoy),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError, "artifact scope differs|steps"
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_failure_upload_step_condition_is_exact(self):
        exact = "        if: ${{ always() }}\n"
        upload_header = (
            "      - name: Upload compiler evidence or first-failure diagnostics\n"
        )
        prefix, compiler_upload = self.workflow.split(upload_header, 1)
        for replacement in ("", "        # if: ${{ always() }}\n", "        if: ${{ success() }}\n"):
            with self.subTest(replacement=replacement.strip() or "removed"):
                mutation = prefix + upload_header + compiler_upload.replace(
                    exact, replacement, 1
                )
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError, "upload scope differs"
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_rk006_capture_is_a_separate_same_run_non_durable_artifact(self):
        contract = json.loads(RK006_CAPTURE_CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(30, contract["artifact_policy"]["actions_retention_days"])
        self.assertFalse(contract["artifact_policy"]["artifact_is_durable"])
        self.assertTrue(all(value is False for value in contract["claims"].values()))
        start = self.workflow.index("  rk006-full-source-build-capture:\n")
        self.assertLess(self.workflow.index("  exact-build:\n"), start)
        job = self.workflow[start:]
        self.assertIn("needs: exact-build", job)
        self.assertNotRegex(job, r"(?m)^    if:")
        capture_command = job.index(
            "rocky_kernel_rk006_full_source_build_capture.py capture"
        )
        download = job.index("actions/download-artifact@", capture_command)
        finalize = job.index("finalize-build", download)
        verify = job.index("verify-capture", finalize)
        upload = job.index("actions/upload-artifact@", verify)
        self.assertLess(capture_command, download)
        self.assertLess(download, finalize)
        self.assertLess(finalize, verify)
        self.assertLess(verify, upload)
        self.assertIn(
            "name: native-rust-exact-build-${{ github.run_id }}-${{ github.run_attempt }}",
            job,
        )
        self.assertIn(
            "name: rk006-full-source-build-capture-${{ github.run_id }}-${{ github.run_attempt }}",
            job,
        )
        self.assertIn("retention-days: 30", job)
        self.assertIn("kmod lld llvm llvm-devel make ncurses-devel", job)
        self.assertNotIn('tar -C "$SOURCE_PARENT" -xf "$archive"', job)
        self.assertIn('test ! -e "$source_root"', job)
        self.assertNotIn("RK-006: PASS", job)

    def test_rk006_capture_contract_checker_tests_and_authority_are_triggered(self):
        paths = (
            "host-kernel/rocky/evidence/rk006-full-source-build-capture-contract-v1.json",
            "host-kernel/rocky/rk006-patch-authority-v1.json",
            "scripts/rocky_kernel_rk006_full_source_build_capture.py",
            "scripts/rocky_kernel_rk006_patch_authority.py",
            "scripts/tests/test_rocky_kernel_rk006_full_source_build_capture.py",
            "scripts/tests/test_rocky_kernel_rk006_patch_authority.py",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(2, self.workflow.count("      - " + path))
        self.assertGreaterEqual(
            self.workflow.count(
                "/usr/bin/python3 -E -s scripts/rocky_kernel_rk006_full_source_build_capture.py"
            ),
            4,
        )

    def test_rk006_capture_job_rejects_missing_extra_reordered_and_decoy_scopes(self):
        header = "  rk006-full-source-build-capture:\n"
        start = self.workflow.index(header)
        capture_job = self.workflow[start:]
        missing = self.workflow[:start].rstrip("\n") + "\n"
        extra = self.workflow + "\n" + capture_job
        conditional = self.workflow.replace(
            "    needs: exact-build\n",
            "    needs: exact-build\n    if: ${{ false }}\n",
            1,
        )
        tolerated = self.workflow.replace(
            "    needs: exact-build\n",
            "    needs: exact-build\n    continue-on-error: true\n",
            1,
        )
        reordered = self.workflow.replace(
            "      - name: Initialize non-durable capture and install exact tools\n",
            "      - name: __FIRST__\n",
            1,
        ).replace(
            "      - name: Check out the exact capture candidate without credentials\n",
            "      - name: Initialize non-durable capture and install exact tools\n",
            1,
        ).replace(
            "      - name: __FIRST__\n",
            "      - name: Check out the exact capture candidate without credentials\n",
            1,
        )
        decoy = self.workflow.replace(
            "            /usr/bin/python3 -E -s scripts/rocky_kernel_rk006_full_source_build_capture.py capture \\\n",
            "            # /usr/bin/python3 -E -s scripts/rocky_kernel_rk006_full_source_build_capture.py capture \\\n",
            1,
        )
        finalize_header = "      - name: Finalize the non-crediting build binding\n"
        finalize_start = self.workflow.index(finalize_header)
        finalize_run = self.workflow.index("        run: |\n", finalize_start)
        finalize_body = finalize_run + len("        run: |\n")
        early_exit = self.workflow[:finalize_body] + "          exit 0\n" + self.workflow[finalize_body:]
        error_trap = self.workflow[:finalize_body] + "          trap 'exit 0' ERR\n" + self.workflow[finalize_body:]
        step_conditional = self.workflow.replace(
            finalize_header,
            finalize_header + "        if: ${{ success() }}\n",
            1,
        )
        unnamed_extra = self.workflow.replace(
            "      - name: Upload RK-006 capture or first-failure diagnostics\n",
            "      - run: exit 0\n"
            "      - name: Upload RK-006 capture or first-failure diagnostics\n",
            1,
        )
        for label, mutation in (
            ("missing", missing),
            ("extra", extra),
            ("conditional", conditional),
            ("tolerated", tolerated),
            ("reordered", reordered),
            ("comment-decoy", decoy),
            ("early-exit", early_exit),
            ("error-trap", error_trap),
            ("step-conditional", step_conditional),
            ("unnamed-extra", unnamed_extra),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError, "RK-006|capture"
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_exact_three_module_config_and_artifacts_are_required(self):
        assignments = kconfig_policy.validate_native_rust_evidence_fragment(
            CONFIG.read_text(encoding="utf-8")
        )
        self.assertEqual(kconfig_policy.EVIDENCE_FRAGMENT_ASSIGNMENTS, assignments)
        for symbol in (
            "CONFIG_MCKERNEL_IHK_RUST",
            "CONFIG_MCKERNEL_IHK_SMP_X86_64_RUST",
            "CONFIG_MCKERNEL_MCCTRL_RUST",
        ):
            self.assertIn(symbol, self.workflow)
            self.assertIn(symbol + "=m", CONFIG.read_text(encoding="utf-8"))
        for output in ("ihk.ko", "ihk-smp-x86_64.ko", "mcctrl.ko"):
            self.assertIn(output, self.workflow)

    def test_ihk_queue_fixture_requires_the_exact_rocky_compiler(self):
        self.assertIn("scripts/ihk_native_queue_check.py", self.workflow)
        self.assertIn('--rustc /usr/bin/rustc --require-rustc', self.workflow)

    def test_both_local_kernel_patches_are_applied(self):
        for name in (
            "0001-drivers-misc-add-mckernel-rust-host-modules.patch",
            "0002-rust-bindings-expose-module-parameters.patch",
        ):
            self.assertIn(name, self.workflow)
        patch = PATCH.read_text(encoding="utf-8")
        self.assertEqual(
            "e01b48d89e4126eb3c31b355491ec95e3f31458de79ffd6e28d1bae71ddec14c",
            hashlib.sha256(PATCH.read_bytes()).hexdigest(),
        )
        self.assertIn("index 84303bf221dd9..5e5c00c655cf 100644", patch)
        self.assertIn(
            " #include <linux/miscdevice.h>\n"
            "+#include <linux/moduleparam.h>\n"
            " #include <linux/phy.h>\n",
            patch,
        )
        self.assertNotIn("mckernel", patch.lower())
        self.assertIn(
            "/usr/bin/python3 -E -s -m unittest -v "
            "scripts.tests.test_rust_target_compatibility_patches",
            self.workflow,
        )
        self.assertIn(
            'MCKERNEL_RUSTC_1_92=/usr/bin/rustc \\\n'
            "            /usr/bin/python3 -E -s -m unittest -v "
            "scripts.tests.test_rust_target_compatibility_patches",
            self.workflow,
        )
        self.assertGreaterEqual(
            self.workflow.count("--fuzz=0 --no-backup-if-mismatch"), 3
        )

    def test_final_config_keeps_warnings_fatal(self):
        second_resolution = self.workflow.index(
            'SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" olddefconfig',
            self.workflow.index("resolved-first.config"),
        )
        werror = self.workflow.index(
            'grep -qx \'CONFIG_WERROR=y\' "$BUILD_DIR/.config"',
            second_resolution,
        )
        compile_step = self.workflow.index(
            "Compile the exact kernel and native Rust modules", werror
        )
        self.assertLess(second_resolution, werror)
        self.assertLess(werror, compile_step)

    def test_final_config_requires_modules_after_stable_resolution(self):
        second_resolution = self.workflow.index(
            'SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" olddefconfig',
            self.workflow.index("resolved-first.config"),
        )
        modules = self.workflow.index(
            'grep -qx \'CONFIG_MODULES=y\' "$BUILD_DIR/.config"',
            second_resolution,
        )
        compile_step = self.workflow.index(
            "Compile the exact kernel and native Rust modules", modules
        )
        self.assertLess(second_resolution, modules)
        self.assertLess(modules, compile_step)

    def test_resolved_modules_check_cannot_be_removed_or_weakened(self):
        exact = 'grep -qx \'CONFIG_MODULES=y\' "$BUILD_DIR/.config"'
        for replacement in ("", 'grep -q \'CONFIG_MODULES=y\' "$BUILD_DIR/.config"',
                            'grep -qx \'CONFIG_MODULES=m\' "$BUILD_DIR/.config"'):
            with self.subTest(replacement=replacement or "removed"):
                mutation = self.workflow.replace(exact, replacement, 1)
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError, "CONFIG_MODULES prerequisite differs|steps"
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_resolved_modules_check_rejects_comment_and_decoy_step_bypasses(self):
        exact_line = '          grep -qx \'CONFIG_MODULES=y\' "$BUILD_DIR/.config"\n'
        commented = self.workflow.replace(exact_line, "          # " + exact_line.lstrip(), 1)
        decoy = self.workflow.replace(exact_line, "", 1).replace(
            "      - name: Compile the exact kernel and native Rust modules\n",
            "      - name: Decoy modules check\n"
            "        run: |\n"
            + exact_line
            + "\n      - name: Compile the exact kernel and native Rust modules\n",
            1,
        )
        conditional = self.workflow.replace(
            exact_line,
            "          if false; then\n" + exact_line + "          fi\n",
            1,
        )
        skipped_step = self.workflow.replace(
            "      - name: Resolve the evidence-only module configuration twice\n"
            "        env:\n",
            "      - name: Resolve the evidence-only module configuration twice\n"
            "        if: ${{ false }}\n"
            "        env:\n",
            1,
        )
        tolerated_failure = self.workflow.replace(
            "      - name: Resolve the evidence-only module configuration twice\n"
            "        env:\n",
            "      - name: Resolve the evidence-only module configuration twice\n"
            "        continue-on-error: true\n"
            "        env:\n",
            1,
        )
        for label, mutation in (
            ("commented", commented),
            ("decoy", decoy),
            ("conditional", conditional),
            ("skipped-step", skipped_step),
            ("tolerated-failure", tolerated_failure),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError, "CONFIG_MODULES prerequisite differs|steps"
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_solver_and_link_closure_are_active_scoped_and_triggered(self):
        for path in (
            "scripts/native_rust_kconfig_solver.py",
            "scripts/tests/test_native_rust_kconfig_solver.py",
            "scripts/native_rust_kbuild_link_closure.py",
            "scripts/tests/test_native_rust_kbuild_link_closure.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(2, self.workflow.count("      - " + path))
        for module in (
            "scripts.tests.test_native_rust_kconfig_solver",
            "scripts.tests.test_native_rust_kbuild_link_closure",
        ):
            self.assertEqual(1, self.workflow.count(module))

        solver_run = "            scripts/native_rust_kconfig_solver.py run \\\n"
        solver_check = "            scripts/native_rust_kconfig_solver.py check \\\n"
        link_output = "            scripts/native_rust_kbuild_link_closure.py \\\n"
        solver_mode = 'chmod 0644 "$EVIDENCE_DIR/kconfig-solver-matrix.json"'
        self.assertEqual(1, self.workflow.count(solver_run))
        self.assertEqual(1, self.workflow.count(solver_check))
        self.assertEqual(1, self.workflow.count(solver_mode))
        self.assertEqual(2, self.workflow.count(link_output))
        self.assertLess(
            self.workflow.index(solver_mode), self.workflow.index(solver_check)
        )
        self.assertLess(
            self.workflow.index(solver_check),
            self.workflow.index("Compile the exact kernel and native Rust modules"),
        )
        self.assertLess(
            self.workflow.index('cp "$module_root/$record" "$EVIDENCE_DIR/$record"'),
            self.workflow.index('--output "$EVIDENCE_DIR/kbuild-link-closure.json"'),
        )
        self.assertLess(
            self.workflow.index('--check-output "$EVIDENCE_DIR/kbuild-link-closure.json"'),
            self.workflow.index("find . -maxdepth 1 -type f ! -name SHA256SUMS"),
        )

        for label, exact in (
            ("solver-run", solver_run),
            ("solver-check", solver_check),
            ("link-output", link_output),
            ("solver-mode", "          " + solver_mode),
        ):
            with self.subTest(label=label):
                mutation = self.workflow.replace(exact, "          # " + exact.lstrip(), 1)
                with self.assertRaises(runtime_evidence.EvidenceError):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_raw_kbuild_record_set_cannot_return_to_broad_discovery(self):
        self.assertNotIn("-name '.*.cmd' -exec cp", self.workflow)
        for record in (
            ".ihk-smp-x86_64.ko.cmd",
            ".ihk-smp-x86_64.mod.cmd",
            ".ihk-smp-x86_64.mod.o.cmd",
            ".ihk-smp-x86_64.o.cmd",
            ".ihk.ko.cmd",
            ".ihk.mod.cmd",
            ".ihk.mod.o.cmd",
            ".ihk.o.cmd",
            ".ihk_smp_x86_64.o.cmd",
            ".mcctrl.ko.cmd",
            ".mcctrl.mod.cmd",
            ".mcctrl.mod.o.cmd",
            ".mcctrl.o.cmd",
        ):
            self.assertEqual(1, self.workflow.count("            " + record + "\n"))
        self.assertEqual(
            1,
            self.workflow.count(
                "          mod_records=(ihk-smp-x86_64.mod ihk.mod mcctrl.mod)\n"
            ),
        )

    def test_kernel_compatibility_series_precedes_project_staging(self):
        self.assertIn("--fuzz=0 --no-backup-if-mismatch", self.workflow)
        debrand = self.workflow.index("1000-debrand-some-messages.patch")
        softfloat = self.workflow.index(
            "0001-x86-rust-set-rustc-abi-x86-softfloat.patch", debrand
        )
        target_spec = self.workflow.index(
            "0002-rust-support-rust-1.91-target-spec.patch", softfloat
        )
        rustc_minimum = self.workflow.index(
            "0003-kbuild-rust-add-rustc-min-version.patch", target_spec
        )
        core_edition = self.workflow.index(
            "0004-rust-compile-libcore-edition-2024.patch", rustc_minimum
        )
        bindgen_lint = self.workflow.index(
            "0005-rust-clean-unnecessary-transmutes-lint.patch", core_edition
        )
        pin_data_lint = self.workflow.index(
            "0006-rust-init-allow-dead-code-rust-1.89.patch", bindgen_lint
        )
        used_compiler = self.workflow.index(
            "0007-rust-use-used-compiler-rust-1.89.patch", pin_data_lint
        )
        receiver_reconciliation = self.workflow.index(
            "0008-rust-enable-arbitrary-self-types-rust-1.92.patch", used_compiler
        )
        block_reconciliation = self.workflow.index(
            "0009-rust-block-drop-removed-merge-flag.patch",
            receiver_reconciliation,
        )
        clang_warning_policy = self.workflow.index(
            "0010-kbuild-disable-default-const-init-unsafe.patch",
            block_reconciliation,
        )
        ksm_clang_21 = self.workflow.index(
            "0011-mm-ksm-fix-clang-21-uninitialized.patch",
            clang_warning_policy,
        )
        netfs_nonstring = self.workflow.index(
            "0012-netfs-mark-nonstring-lookup-tables.patch",
            ksm_clang_21,
        )
        crypto_nonstring = self.workflow.index(
            "0013-lib-crypto-mark-binary-vectors-nonstring.patch",
            netfs_nonstring,
        )
        byte_array_nonstring = self.workflow.index(
            "0014-gcc-15-mark-byte-arrays-nonstring.patch",
            crypto_nonstring,
        )
        warning_demote = self.workflow.index(
            "0015-gcc-15-demote-unterminated-string-warning.patch",
            byte_array_nonstring,
        )
        warning_disable = self.workflow.index(
            "0016-gcc-15-disable-unterminated-string-warning.patch",
            warning_demote,
        )
        warning_helper = self.workflow.index(
            "0017-kbuild-use-cc-disable-warning.patch",
            warning_disable,
        )
        warning_order = self.workflow.index(
            "0018-kbuild-order-unterminated-string-disable.patch",
            warning_helper,
        )
        opaque_init = self.workflow.index(
            "0019-rust-types-add-opaque-try-ffi-init.patch",
            warning_order,
        )
        miscdevice = self.workflow.index(
            "0020-rust-miscdevice-add-base-abstraction.patch",
            opaque_init,
        )
        module_owner = self.workflow.index(
            "0020a-rust-miscdevice-bind-file-operations-to-module.patch",
            miscdevice,
        )
        objtool_noreturn = self.workflow.index(
            "0021-objtool-recognize-rust-1.92-panic-const.patch",
            module_owner,
        )
        pvh_noendbr = self.workflow.index(
            "0022-x86-pvh-annotate-noendbr.patch",
            objtool_noreturn,
        )
        allocator_shim = self.workflow.index(
            "0023-rust-update-no-alloc-shim-marker-rust-1.92.patch",
            pvh_noendbr,
        )
        project = self.workflow.index(
            "0001-drivers-misc-add-mckernel-rust-host-modules.patch",
            allocator_shim,
        )
        self.assertLess(debrand, softfloat)
        self.assertLess(softfloat, target_spec)
        self.assertLess(target_spec, rustc_minimum)
        self.assertLess(rustc_minimum, core_edition)
        self.assertLess(core_edition, bindgen_lint)
        self.assertLess(bindgen_lint, pin_data_lint)
        self.assertLess(pin_data_lint, used_compiler)
        self.assertLess(used_compiler, receiver_reconciliation)
        self.assertLess(receiver_reconciliation, block_reconciliation)
        self.assertLess(block_reconciliation, clang_warning_policy)
        self.assertLess(clang_warning_policy, ksm_clang_21)
        self.assertLess(ksm_clang_21, netfs_nonstring)
        self.assertLess(netfs_nonstring, crypto_nonstring)
        self.assertLess(crypto_nonstring, byte_array_nonstring)
        self.assertLess(byte_array_nonstring, warning_demote)
        self.assertLess(warning_demote, warning_disable)
        self.assertLess(warning_disable, warning_helper)
        self.assertLess(warning_helper, warning_order)
        self.assertLess(warning_order, opaque_init)
        self.assertLess(opaque_init, miscdevice)
        self.assertLess(miscdevice, module_owner)
        self.assertLess(module_owner, objtool_noreturn)
        self.assertLess(objtool_noreturn, pvh_noendbr)
        self.assertLess(pvh_noendbr, allocator_shim)
        self.assertLess(allocator_shim, project)
        self.assertEqual(
            3,
            self.workflow.count("0021-objtool-recognize-rust-1.92-panic-const.patch"),
        )
        self.assertEqual(
            3,
            self.workflow.count("0022-x86-pvh-annotate-noendbr.patch"),
        )
        self.assertEqual(
            3,
            self.workflow.count(
                "0023-rust-update-no-alloc-shim-marker-rust-1.92.patch"
            ),
        )

    def test_rs006_source_substrate_is_checked_without_credit(self):
        self.assertIn("scripts/rs006_miscdevice_substrate.py", self.workflow)
        self.assertIn("--require-source-replay", self.workflow)
        self.assertNotIn("RS-006: PASS", self.workflow)

    def test_failure_log_and_artifact_capture_are_unconditional(self):
        bootstrap = self.workflow.index("Refuse the wrong runtime")
        checkout = self.workflow.index("Check out the exact candidate")
        evidence_init = self.workflow.index(
            'mkdir -p "$evidence_dir"', bootstrap, checkout
        )
        self.assertLess(bootstrap, evidence_init)
        self.assertLess(evidence_init, checkout)
        self.assertIn('> "$evidence_dir/workflow-state"', self.workflow)
        self.assertIn('tee "$evidence_dir/build.log"', self.workflow)
        self.assertIn('printf \'%s\\n\' "$producer_status"', self.workflow)
        self.assertIn('printf \'%s\\n\' "$tee_status"', self.workflow)
        self.assertIn("if: ${{ always() }}", self.workflow)
        self.assertIn("if-no-files-found: error", self.workflow)

    def test_fp0006_bootstrap_failure_has_an_unambiguous_upload_record(self):
        job = self.workflow.split("  fp0006-native-rust-capture:\n", 1)[1].split(
            "  rk006-full-source-build-capture:\n", 1
        )[0]
        self.assertEqual(1, job.count("--allowerasing"))
        self.assertIn(
            "dnf -y --allowerasing --setopt=install_weak_deps=False install \\\n"
            "            coreutils\n",
            job,
        )
        self.assertIn("! /usr/bin/rpm -q coreutils-single", job)
        self.assertIn(
            "dnf -y --setopt=install_weak_deps=False install \\\n"
            "            gcc git-core python3 rust-1.92.0-1.el10",
            job,
        )
        self.assertIn("capture-envelope-required-missing", job)
        self.assertIn("capture-envelope-created-unreviewed", job)
        self.assertIn("credit-forbidden", job)
        self.assertIn(
            "fp0006-native-rust-source-fixture-", job
        )
        self.assertIn(
            "fp0006-native-rust-first-failure-", job
        )
        self.assertIn(
            "${{ runner.temp }}/fp0006-native-rust-first-failure/workflow-state",
            job,
        )
        self.assertIn("if: ${{ failure() }}", job)
        self.assertIn("-C linker=/usr/bin/gcc -C strip=symbols", job)
        self.assertIn(
            'producer_bytes="$(/usr/bin/wc -c < "$producer")"', job
        )
        self.assertIn(
            'if test "$producer_bytes" -le 0 || '
            'test "$producer_bytes" -gt 8388608; then',
            job,
        )
        self.assertIn(
            "FP-0006 native producer binary size observed=%s maximum=8388608",
            job,
        )
        successful_upload = job.split(
            "      - name: Upload FP-0006 native envelope\n", 1
        )[1].split(
            "      - name: Upload FP-0006 first-failure diagnostics\n", 1
        )[0]
        self.assertNotIn("workflow-state", successful_upload)

    def test_built_module_diagnostics_precede_semantic_validation(self):
        validation = self.workflow.index(
            "Validate built metadata and capture immutable diagnostics"
        )
        checker = self.workflow.index(
            "scripts/ihk_native_lifecycle_check.py", validation
        )
        precheck = self.workflow.index(
            'sha256sum --check --strict PRECHECK_SHA256SUMS', validation
        )
        vermagic = self.workflow.index(
            'vermagic="$(run_modinfo -F vermagic "$module")"', validation
        )
        copied_module = self.workflow.index(
            'module="$EVIDENCE_DIR/$name"', precheck
        )
        self.assertLess(precheck, copied_module)
        self.assertLess(copied_module, vermagic)
        self.assertLess(vermagic, checker)
        for fragment in (
            '/usr/bin/git -c safe.directory="$GITHUB_WORKSPACE" rev-parse HEAD',
            '> "$EVIDENCE_DIR/commit.sha"',
            'cp "$module" "$EVIDENCE_DIR/$name"',
            'run_modinfo "$module" > "$EVIDENCE_DIR/$name.modinfo"',
            '/usr/bin/readelf -p .modinfo "$module" '
            '> "$EVIDENCE_DIR/$name.modinfo-section"',
            '/usr/bin/readelf -SWr "$module" > "$EVIDENCE_DIR/$name.readelf"',
            '/usr/bin/nm -A -a "$module" > "$EVIDENCE_DIR/$name.nm"',
            '| sort -z | xargs -0 sha256sum -- > PRECHECK_SHA256SUMS',
            'sha256sum --check --strict PRECHECK_SHA256SUMS',
        ):
            with self.subTest(fragment=fragment):
                diagnostic = self.workflow.index(fragment, validation)
                self.assertLess(diagnostic, checker)
        final_input = self.workflow.index(
            'printf \'%s\\n\' "$kernel_release" > "$EVIDENCE_DIR/kernel.release"',
            checker,
        )
        final_manifest = self.workflow.index(
            '| sort -z | xargs -0 sha256sum -- > SHA256SUMS', checker
        )
        self.assertLess(final_input, final_manifest)
        self.assertIn(
            "! -name PRECHECK_SHA256SUMS ! -name SHA256SUMS",
            self.workflow[validation:checker],
        )

    def test_added_unbound_kbuild_invocation_is_rejected(self):
        marker = (
            "          printf 'NATIVE_BASELINE_CONFIG=%s\\n' \"$baseline\" "
            ">> \"$github_env_file\"\n"
        )
        additions = (
            '          make -C "$NATIVE_SOURCE_ROOT" olddefconfig\n',
            '          (cd "$NATIVE_SOURCE_ROOT" && make olddefconfig)\n',
            '          builder=make; "$builder" -C "$NATIVE_SOURCE_ROOT" olddefconfig\n',
            '          "$MAKE" -C "$NATIVE_SOURCE_ROOT" olddefconfig\n',
        )
        for addition in additions:
            with self.subTest(addition=addition.strip()):
                mutation = self.workflow.replace(marker, marker + addition, 1)
                start = mutation.index(
                    "      - name: Check out the exact candidate without credentials\n"
                )
                end = mutation.index(
                    "      - name: Resolve the evidence-only module configuration twice\n"
                )
                self.assertNotEqual(self.workflow, mutation)
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError,
                    "Kbuild release scope|unbound build tool|prebuild scope",
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_duplicate_or_extra_top_level_release_environment_is_rejected(self):
        marker = (
            "  NATIVE_KERNEL_LOCALVERSION: "
            + runtime_evidence.EXPECTED_KERNEL_LOCALVERSION
            + "\n"
        )
        additions = (
            "  EXPECTED_KERNEL_RELEASE: 6.12.0-attacker\n"
            "  NATIVE_KERNEL_LOCALVERSION: -attacker\n",
            "  EXTRA_RELEASE_AUTHORITY: attacker\n",
        )
        for addition in additions:
            with self.subTest(addition=addition.strip()):
                mutation = self.workflow.replace(marker, marker + addition, 1)
                exact = mutation.split("\n  fp0006-native-rust-capture:\n", 1)[0]
                end = exact.index("\njobs:\n") + 1
                digest = hashlib.sha256(exact[:end].encode("utf-8")).hexdigest()
                with mock.patch.object(
                    runtime_evidence,
                    "EXPECTED_EXACT_BUILD_PREFIX_SHA256",
                    digest,
                ):
                    with self.assertRaisesRegex(
                        runtime_evidence.EvidenceError,
                        "environment mapping differs",
                    ):
                        runtime_evidence._validate_exact_build_workflow(mutation)

    def test_openssl_cli_is_installed_and_verified_before_the_build(self):
        bootstrap = self.workflow.split(
            "      - name: Refuse the wrong runtime and install exact build tools\n",
            1,
        )[1].split(
            "      - name: Check out the exact candidate without credentials\n",
            1,
        )[0]
        install = bootstrap.index(
            "dnf -y --setopt=install_weak_deps=False install \\\n"
        )
        bootstrap = bootstrap[install:]
        package_end = bootstrap.index('openssl_path="$(command -v openssl)"')
        package_tokens = re.findall(r"[A-Za-z0-9_.+-]+", bootstrap[:package_end])
        self.assertEqual(1, package_tokens.count("openssl"))
        self.assertEqual(1, package_tokens.count("openssl-devel"))
        self.assertIn('openssl_path="$(command -v openssl)"', bootstrap)
        self.assertIn('test "$openssl_path" = /usr/bin/openssl', bootstrap)
        self.assertIn("rpm -qf --qf '%{NAME}\\n' \"$openssl_path\"", bootstrap)
        self.assertIn("openssl version", bootstrap)
        self.assertLess(
            bootstrap.index("openssl openssl-devel"),
            bootstrap.index("openssl version"),
        )

    def test_openssl_install_step_rejects_inactive_or_reordered_decoys(self):
        package_line = (
            "            openssl openssl-devel patch perl python3 python3-devel "
            "python3-pyyaml redhat-rpm-config \\\n"
        )
        path_line = '          openssl_path="$(command -v openssl)"\n'
        version_line = "          openssl version\n"
        bootstrap_header = (
            "      - name: Refuse the wrong runtime and install exact build tools\n"
        )
        reordered = self.workflow.replace(path_line, "__OPENSSL_PATH__\n", 1)
        reordered = reordered.replace(version_line, path_line, 1)
        reordered = reordered.replace("__OPENSSL_PATH__\n", version_line, 1)
        mutations = {
            "commented": self.workflow.replace(
                package_line,
                package_line.replace("            openssl", "            # openssl"),
                1,
            ),
            "step-conditional": self.workflow.replace(
                bootstrap_header,
                bootstrap_header + "        if: ${{ false }}\n",
                1,
            ),
            "reordered": reordered,
            "duplicated": self.workflow.replace(
                package_line, package_line + package_line, 1
            ),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError,
                    "OpenSSL CLI closure|OpenSSL out of order|bootstrap scope differs",
                ):
                    runtime_evidence._validate_exact_build_workflow(mutation)

    def test_frozen_legacy_oracle_and_shared_evidence_path_are_available(self):
        self.assertIn("submodules: recursive", self.workflow)
        self.assertIn(
            'test "$(/usr/bin/git -C ihk rev-parse HEAD)" = '
            '"3114d9e7101ad52030eb3effa849a5c108972a1f"',
            self.workflow,
        )
        self.assertGreaterEqual(
            self.workflow.count('$RUNNER_TEMP/native-rust-build-evidence'), 3
        )
        self.assertNotIn(
            'evidence_dir="${{ runner.temp }}/native-rust-build-evidence"',
            self.workflow,
        )

    def test_ihk_registry_contract_and_exact_fixture_are_mandatory(self):
        for path in (
            "host-kernel/contracts/ihk-os-registry-foundation-v1.json",
            "scripts/ihk_os_registry_check.py",
            "scripts/tests/fixtures/ihk_os_registry_compile.rs",
            "scripts/tests/test_ihk_os_registry_check.py",
        ):
            self.assertGreaterEqual(self.workflow.count(path), 2)
        self.assertGreaterEqual(
            self.workflow.count(
                'scripts/ihk_os_registry_check.py --repo "$GITHUB_WORKSPACE"'
            ),
            2,
        )
        self.assertGreaterEqual(
            self.workflow.count('MCKERNEL_RUSTC_1_92=/usr/bin/rustc'), 2
        )
        self.assertGreaterEqual(
            self.workflow.count(
                "/usr/bin/python3 -E -s -m unittest -v scripts.tests.test_ihk_os_registry_check"
            ),
            2,
        )
        self.assertGreaterEqual(
            self.workflow.count(
                "/usr/bin/python3 -E -s scripts/native_rust_unsafe_ffi_ledger.py "
                '--repo "$GITHUB_WORKSPACE" check'
            ),
            1,
        )

    def test_ihk_device_registry_fixture_and_exact_tests_are_mandatory(self):
        trigger_paths = (
            "host-kernel/contracts/ihk-device-registry-foundation-v1.json",
            "host-kernel/native-rust/device_registry.rs",
            "scripts/ihk_device_registry_check.py",
            "scripts/tests/fixtures/ihk_device_registry_compile.rs",
            "scripts/tests/test_ihk_device_registry.py",
            "scripts/tests/test_ihk_device_registry_check.py",
        )
        for path in trigger_paths:
            self.assertEqual(2, self.workflow.count("      - " + path), path)
        workflow = yaml.safe_load(self.workflow)
        scripts = {
            step.get("name"): step.get("run", "")
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if step.get("name")
        }
        for name in (
            "Verify source-only contracts without claiming readiness",
            "Validate built metadata and capture immutable diagnostics",
        ):
            script = scripts[name]
            self.assertIn(
                'scripts/ihk_device_registry_check.py --repo "$GITHUB_WORKSPACE"',
                script,
            )
            self.assertIn("scripts.tests.test_ihk_device_registry", script)
            self.assertIn("scripts.tests.test_ihk_device_registry_check", script)

    def test_raw_semantics_retention_authority_is_triggered_and_executed(self):
        trigger_paths = (
            "scripts/host_module_failure_semantics_v3.py",
            "scripts/host_module_failure_semantics_retention_v3.py",
            "scripts/tests/test_host_module_failure_semantics_retention_v3.py",
        )
        for path in trigger_paths:
            self.assertEqual(2, self.workflow.count("      - " + path), path)
        workflow = yaml.safe_load(self.workflow)
        source_validation = next(
            step.get("run", "")
            for step in workflow["jobs"]["exact-build"]["steps"]
            if step.get("name")
            == "Verify source-only contracts without claiming readiness"
        )
        self.assertEqual(
            1,
            source_validation.count(
                "scripts.tests.test_host_module_failure_semantics_retention_v3"
            ),
        )

    def test_smp_resource_fixtures_and_exact_tests_are_mandatory(self):
        trigger_paths = (
            "host-kernel/native-rust/smp_resource.rs",
            "scripts/tests/fixtures/ihk_smp_resource_compile.rs",
            "scripts/tests/fixtures/ihk_smp_resource_workspace_alias_compile_fail.rs",
            "scripts/tests/test_ihk_smp_resource.py",
        )
        for path in trigger_paths:
            self.assertEqual(2, self.workflow.count("      - " + path), path)
        workflow = yaml.safe_load(self.workflow)
        scripts = {
            step.get("name"): step.get("run", "")
            for job in workflow["jobs"].values()
            for step in job.get("steps", [])
            if step.get("name")
        }
        for name in (
            "Verify source-only contracts without claiming readiness",
            "Validate built metadata and capture immutable diagnostics",
        ):
            self.assertIn("scripts.tests.test_ihk_smp_resource", scripts[name])

    def test_exact_probe_and_shared_abi_checks_and_triggers_are_mandatory(self):
        for path in (
            "host-kernel/contracts/linux-api-exact-probe-v1.json",
            "host-kernel/contracts/linux-api-needs-v1.json",
            "host-kernel/contracts/x86_64-shared-abi-v1.json",
            "host-kernel/rocky/config-policy.json",
            "host-kernel/rocky/patches/series.json",
            "host-kernel/rocky/toolchain-lock.json",
            "scripts/linux_api_exact_probe.py",
            "scripts/tests/fixtures/generate-rust-target-rocky-6.12.rs",
            "scripts/tests/fixtures/rust-core-rocky-6.12/**",
            "scripts/tests/test_linux_api_exact_probe.py",
            "scripts/tests/test_rust_target_compatibility_patches.py",
            "scripts/tests/test_x86_64_shared_abi.py",
            "scripts/x86_64_shared_abi.py",
        ):
            self.assertGreaterEqual(self.workflow.count(path), 2)
        self.assertIn(
            "/usr/bin/python3 -E -s scripts/linux_api_exact_probe.py "
            '--repo "$GITHUB_WORKSPACE" check-contract',
            self.workflow.replace("\\\n            ", ""),
        )
        self.assertIn(
            "/usr/bin/python3 -E -s scripts/x86_64_shared_abi.py "
            '--repo-root "$GITHUB_WORKSPACE" --check',
            self.workflow.replace("\\\n            ", ""),
        )

    def test_ihk_ioctl_dispatch_contract_api_audit_and_fixture_are_mandatory(self):
        for path in (
            "host-kernel/contracts/ihk-ioctl-dispatch-foundation-v1.json",
            "scripts/ihk_ioctl_dispatch_check.py",
            "scripts/tests/fixtures/ihk_ioctl_dispatch_compile.rs",
            "scripts/tests/fixtures/rust-core-rocky-6.12/rust/kernel/ioctl.rs",
            "scripts/tests/fixtures/rust-core-rocky-6.12/rust/kernel/uaccess.rs",
            "scripts/tests/test_ihk_ioctl_dispatch_check.py",
        ):
            self.assertGreaterEqual(self.workflow.count(path), 2)
        self.assertGreaterEqual(
            self.workflow.count(
                'scripts/ihk_ioctl_dispatch_check.py --repo "$GITHUB_WORKSPACE"'
            ),
            3,
        )
        self.assertIn('--kernel-source "$source_root"', self.workflow)
        self.assertGreaterEqual(
            self.workflow.count(
                "/usr/bin/python3 -E -s -m unittest -v scripts.tests.test_ihk_ioctl_dispatch_check"
            ),
            2,
        )

    def test_checkout_includes_frozen_superproject_history_for_shared_abi(self):
        checkout = self.workflow.split(
            "- name: Check out the exact candidate without credentials", 1
        )[1].split("- name: Verify source-only contracts", 1)[0]
        self.assertIn("fetch-depth: 0", checkout)
        self.assertNotIn("fetch-depth: 1", checkout)
        self.assertIn("persist-credentials: false", checkout)

    def test_attached_page_foundations_require_exact_rocky_rustc(self):
        for path in (
            "scripts/ihk_page_allocator_check.py",
            "scripts/ihk_page_owner_registry_check.py",
            "scripts/tests/fixtures/ihk_page_allocator_compile.rs",
            "scripts/tests/fixtures/ihk_page_allocator_lifetime_compile_fail.rs",
            "scripts/tests/fixtures/ihk_page_allocator_must_use_compile_fail.rs",
            "scripts/tests/fixtures/ihk_page_owner_registry_compile.rs",
            "scripts/tests/fixtures/ihk_page_owner_registry_lifetime_compile_fail.rs",
            "scripts/tests/fixtures/ihk_page_owner_registry_sync_compile_fail.rs",
            "scripts/tests/test_ihk_page_allocator_check.py",
            "scripts/tests/test_ihk_page_owner_registry_check.py",
        ):
            self.assertGreaterEqual(self.workflow.count(path), 2)
        self.assertIn(
            'IHK_PAGE_ALLOCATOR_RUSTC=/usr/bin/rustc', self.workflow
        )
        self.assertIn(
            'IHK_PAGE_OWNER_REGISTRY_RUSTC=/usr/bin/rustc', self.workflow
        )
        allocator = self.workflow.index("IHK_PAGE_ALLOCATOR_RUSTC=")
        owner = self.workflow.index("IHK_PAGE_OWNER_REGISTRY_RUSTC=", allocator)
        self.assertIn("--require-rustc", self.workflow[allocator:owner])
        self.assertIn("--require-rustc", self.workflow[owner:])

    def test_central_source_ci_uses_the_same_exact_rocky_compiler_contract(self):
        image = (
            "rockylinux/rockylinux:10.2@sha256:"
            "e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176"
        )
        self.assertIn(image, self.source_workflow)
        self.assertIn("submodules: recursive", self.source_workflow)
        self.assertIn(
            'test "$(git -C ihk rev-parse HEAD)" = \\\n'
            '            "3114d9e7101ad52030eb3effa849a5c108972a1f"',
            self.source_workflow,
        )
        self.assertIn(
            "rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)",
            self.source_workflow,
        )
        for environment, checker in (
            ("IHK_PAGE_ALLOCATOR_RUSTC", "scripts/ihk_page_allocator_check.py"),
            (
                "IHK_PAGE_OWNER_REGISTRY_RUSTC",
                "scripts/ihk_page_owner_registry_check.py",
            ),
        ):
            self.assertIn(environment + '="$(command -v rustc)"', self.source_workflow)
            start = self.source_workflow.index(environment + "=")
            end = self.source_workflow.find("\n", self.source_workflow.index("--require-rustc", start))
            invocation = self.source_workflow[start:end]
            self.assertIn(checker, invocation)
            self.assertIn("--require-rustc", invocation)


if __name__ == "__main__":
    unittest.main()
