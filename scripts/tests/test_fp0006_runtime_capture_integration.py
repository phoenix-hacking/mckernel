#!/usr/bin/env python3

from __future__ import print_function

import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from scripts import fp0006_runtime_capture_integration as capture
from scripts import native_rust_runtime_evidence


ROOT = Path(__file__).resolve().parents[2]
LEGACY_WORKFLOW = ROOT / ".github/workflows/rust-x86_64-validation.yml"
NATIVE_WORKFLOW = ROOT / ".github/workflows/native-rust-host-modules-exact-build.yml"
CONTRACT = ROOT / "host-kernel/contracts/fp0006-runtime-capture-integration-v1.json"


def canonical(value):
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("ascii")


def raw_stream():
    return (
        b'{"argument":0,"request":4294967295,"sequence":0,'
        b'"vector_id":"unknown-device-request-ffffffff-arg0"}\n'
        b'{"argument":63,"request":1124609,"sequence":1,'
        b'"vector_id":"destroy-known-empty-minor63"}\n'
    )


def result_stream(surface):
    if surface == "legacy-live-ioctl":
        interface_return = -1
        error = 22
    else:
        interface_return = -22
        error = 0
    rows = []
    for sequence, vector in enumerate(
        ("unknown-device-request-ffffffff-arg0", "destroy-known-empty-minor63")
    ):
        rows.append(
            {
                "errno": error,
                "interface_return": interface_return,
                "normalized_return": -22,
                "sequence": sequence,
                "surface": surface,
                "vector_id": vector,
            }
        )
    return b"".join(canonical(row) for row in rows)


def ledger_stream(surface):
    rows = []
    vectors = (
        "unknown-device-request-ffffffff-arg0",
        "destroy-known-empty-minor63",
    )
    for sequence, vector in enumerate(vectors):
        for phase in ("before", "after"):
            rows.append(
                {
                    "minor63_empty": True,
                    "occupied_minor_bitmap": "0000000000000000",
                    "occupied_minor_count": 0,
                    "phase": phase,
                    "sequence": sequence,
                    "surface": surface,
                    "vector_id": vector,
                }
            )
    return b"".join(canonical(row) for row in rows)


class FP0006RuntimeCaptureIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        cls.legacy_workflow = LEGACY_WORKFLOW.read_text(encoding="utf-8")
        cls.native_workflow = NATIVE_WORKFLOW.read_text(encoding="utf-8")
        cls.head = capture._git_head(ROOT)
        cls.repository = "phoenix-hacking/mckernel"
        cls.base_sha = "1" * 40
        cls.github_sha = "2" * 40
        cls.workflow_sha = "3" * 40
        cls.event_name = "pull_request"
        cls.ref = "refs/pull/1/merge"

    def _github(self, run_id):
        return capture._github_observation(
            self.head, self.repository, str(run_id), "1", self.event_name,
            self.ref, self.github_sha, self.workflow_sha, self.base_sha,
        )

    @staticmethod
    def _native_tools():
        return (
            b"rust-0:1.92.0-1.el10.x86_64\n"
            b"gcc-0:14.2.1-7.el10.x86_64\n"
            b"coreutils-0:9.5-6.el10.x86_64\n"
            + b"a" * 64 + b"  /usr/bin/rustc\n"
            + b"b" * 64 + b"  /usr/bin/gcc\n"
            + b"c" * 64 + b"  /usr/bin/timeout\n"
            b"rustc 1.92.0 (ded5c06cf 2025-12-08) (Red Hat 1.92.0-1.el10)\n"
            b"binary: rustc\n"
            + b"commit-hash: ded5c06cf" + b"0" * 31 + b"\n"
            b"commit-date: 2025-12-08\n"
            b"host: x86_64-unknown-linux-gnu\n"
            b"release: 1.92.0\n"
            b"LLVM version: 21.1.6\n"
            b"gcc (GCC) 14.2.1 20250110\n"
            b"Copyright (C) Free Software Foundation, Inc.\n"
            b"timeout (GNU coreutils) 9.5\n"
            b"Copyright (C) Free Software Foundation, Inc.\n"
        )

    @staticmethod
    def _legacy_tools():
        return (
            b"gcc-0:8.5.0-22.el8_10.x86_64\n"
            b"coreutils-0:8.30-15.el8.x86_64\n"
            + b"b" * 64 + b"  /usr/bin/gcc\n"
            + b"c" * 64 + b"  /usr/bin/timeout\n"
            b"gcc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)\n"
            b"Copyright (C) Free Software Foundation, Inc.\n"
            b"timeout (GNU coreutils) 8.30\n"
            b"Copyright (C) Free Software Foundation, Inc.\n"
        )

    def _replace_once(self, baseline, needle, replacement):
        self.assertEqual(1, baseline.count(needle), "hostile mutation needle is stale")
        mutated = baseline.replace(needle, replacement, 1)
        self.assertNotEqual(baseline, mutated, "hostile mutation must change bytes")
        return mutated

    def test_contract_and_all_claims_are_noncrediting(self):
        result = capture.validate_contract(ROOT)
        self.assertEqual("required-missing", result["result_authority"])
        self.assertFalse(result["durable"])
        self.assertTrue(all(value is False for value in result["claims"].values()))
        self.assertFalse(result["claims"]["exact_native_linker_provenance"])
        self.assertFalse(result["claims"]["exact_toolchain_proven"])
        self.assertFalse(result["claims"]["exact_workflow_run_provenance"])

    def test_tool_owner_grammar_is_surface_specific(self):
        legacy = self._legacy_tools()
        native = self._native_tools()
        legacy_observation = capture._validate_tool_report(
            legacy, "legacy-live-ioctl"
        )
        native_observation = capture._validate_tool_report(
            native, "native-rust-source-fixture"
        )
        self.assertEqual(
            "gcc-0:8.5.0-22.el8_10.x86_64", legacy_observation["gcc_owner"]
        )
        self.assertEqual(
            "coreutils-0:8.30-15.el8.x86_64",
            legacy_observation["timeout_owner"],
        )
        self.assertEqual(
            "gcc-0:14.2.1-7.el10.x86_64", native_observation["gcc_owner"]
        )
        for surface, report in (
            (
                "legacy-live-ioctl",
                self._replace_once(legacy, b".el8_10.x86_64", b".el10.x86_64"),
            ),
            (
                "legacy-live-ioctl",
                self._replace_once(legacy, b".el8.x86_64", b".el10.x86_64"),
            ),
            (
                "native-rust-source-fixture",
                self._replace_once(
                    native,
                    b"gcc-0:14.2.1-7.el10.x86_64",
                    b"gcc-0:14.2.1-7.el8_10.x86_64",
                ),
            ),
            (
                "native-rust-source-fixture",
                self._replace_once(
                    native,
                    b"coreutils-0:9.5-6.el10.x86_64",
                    b"coreutils-0:9.5-6.el8.x86_64",
                ),
            ),
        ):
            with self.subTest(surface=surface, report=report[:64]):
                with self.assertRaises(capture.CaptureError):
                    capture._validate_tool_report(report, surface)

    def test_false_authority_claims_cannot_be_promoted(self):
        original = CONTRACT.read_bytes()
        for key in (
            "exact_legacy_compiler_provenance", "exact_linker_provenance",
            "exact_native_linker_provenance", "exact_toolchain_proven",
            "exact_workflow_run_provenance", "gate_pass", "tracker_credit",
        ):
            needle = ('"{0}": false'.format(key)).encode("ascii")
            self.assertEqual(1, original.count(needle))
            mutated = original.replace(
                needle, ('"{0}": true'.format(key)).encode("ascii"), 1
            )
            with self.subTest(key=key), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory)
                target = repo / CONTRACT.relative_to(ROOT)
                target.parent.mkdir(parents=True)
                target.write_bytes(mutated)
                with self.assertRaises(capture.CaptureError):
                    capture.validate_contract(repo)
        self.assertEqual("IN_PROGRESS", self.contract["gate"]["status"])
        self.assertEqual(0, self.contract["gate"]["points_awarded"])

    def test_retention_disclosure_is_honest(self):
        policy = self.contract["artifact_policy"]
        self.assertEqual(30, policy["dedicated_actions_retention_days"])
        self.assertEqual(90, policy["hosted_containing_artifact_retention_days"])
        self.assertEqual(
            "hosted-rocky-boot-${{ github.run_id }}-${{ github.run_attempt }}",
            policy["hosted_containing_artifact_name_template"],
        )
        self.assertTrue(policy["hosted_contains_same_legacy_envelope"])
        self.assertFalse(policy["durable"])
        self.assertEqual(
            "fp0006-native-rust-first-failure-${{ github.run_id }}-${{ github.run_attempt }}",
            policy["dedicated_native_first_failure_artifact_name_template"],
        )
        self.assertEqual(
            [
                "capture-envelope-created-unreviewed",
                "capture-envelope-required-missing",
            ],
            policy["dedicated_native_first_failure_statuses"],
        )
        self.assertEqual(
            "workflow-state", policy["dedicated_native_first_failure_member"]
        )
        limitations = " ".join(self.contract["limitations"])
        self.assertIn("90 days", limitations)
        self.assertIn("same envelope", limitations)

    def test_five_frozen_witness_files_match(self):
        files = self.contract["base_witness"]["files"]
        self.assertEqual(5, len(files))
        for name, binding in files.items():
            with self.subTest(name=name):
                data = (ROOT / binding["path"]).read_bytes()
                self.assertEqual(binding["size"], len(data))
                self.assertEqual(binding["sha256"], hashlib.sha256(data).hexdigest())

    def test_every_bound_identity_is_real_and_independently_recomputed(self):
        for name, binding in self.contract["bound_files"].items():
            with self.subTest(name=name):
                self.assertRegex(binding["sha256"], r"^[0-9a-f]{64}$")
                self.assertNotEqual("0" * 64, binding["sha256"])
                self.assertGreater(binding["size"], 0)
                data = (ROOT / binding["path"]).read_bytes()
                self.assertEqual(binding["size"], len(data))
                self.assertEqual(binding["sha256"], hashlib.sha256(data).hexdigest())
        source = (ROOT / "scripts/fp0006_runtime_capture_integration.py").read_text(encoding="utf-8")
        runtime = (ROOT / "scripts/native_rust_runtime_evidence.py").read_text(encoding="utf-8")
        self.assertNotIn("__FINAL_", source)
        self.assertNotIn("__FINAL_", runtime)

    def test_workflow_parsers_accept_only_frozen_bytes(self):
        policy = self.contract["workflow_policy"]
        capture._validate_legacy_workflow(self.legacy_workflow, policy)
        capture._validate_native_workflow(self.native_workflow, policy)
        bootstrap_start = (
            "      - name: Install pinned Rust and identify the observed FP-0006 linker\n"
            "        run: |\n"
            "          set -euo pipefail\n"
        )
        native_install = (
            "          dnf -y --allowerasing --setopt=install_weak_deps=False install \\\n"
            "            coreutils\n"
        )
        native_steps_start = (
            "  fp0006-native-rust-capture:\n"
            "    name: Capture FP-0006 native Rust fixture (credit forbidden)\n"
            "    needs: exact-build\n"
            "    if: >-\n"
            "      ${{ github.event_name != 'pull_request' ||\n"
            "          github.event.pull_request.head.repo.full_name == github.repository }}\n"
            "    runs-on: ubuntu-24.04\n"
            "    timeout-minutes: 30\n"
            "    container:\n"
            "      image: rockylinux/rockylinux:10.2@sha256:e372170ca8630f0f03e9b70fdd0bf4a3ce3426b0de7cdba615f06337389de176\n"
            "    defaults:\n"
            "      run:\n"
            "        shell: bash\n"
            "\n"
            "    steps:\n"
        )
        native_upload = (
            "          name: fp0006-native-rust-source-fixture-${{ github.run_id }}-${{ github.run_attempt }}\n"
            "          path: ${{ runner.temp }}/fp0006-native-rust-capture/fp0006-runtime-capture-v1.tar\n"
            "          if-no-files-found: error\n"
            "          retention-days: 30\n"
            "          compression-level: 0\n"
        )
        native_failure_upload = (
            "          name: fp0006-native-rust-first-failure-${{ github.run_id }}-${{ github.run_attempt }}\n"
            "          path: ${{ runner.temp }}/fp0006-native-rust-first-failure/workflow-state\n"
            "          if-no-files-found: error\n"
            "          retention-days: 30\n"
            "          compression-level: 0\n"
        )
        legacy_trust_preamble = (
            "  hosted-boot-smoke:\n"
            "    name: Hosted Rocky QEMU boot and mcexec\n"
            "    needs: rocky-build\n"
            "    if: >-\n"
            "      ${{ github.event_name == 'pull_request' &&\n"
            "          github.event.pull_request.head.repo.full_name == github.repository }}\n"
            "    runs-on: ubuntu-24.04\n"
        )
        legacy_steps_start = (
            "      ROCKY_IMAGE_SHA256: e56066c58606191e96184de9a9183a3af33c59bcbd8740d8b10ca054a7a89c14\n"
            "      ROCKY_IMAGE_BYTES: 2065760256\n"
            "\n"
            "    steps:\n"
        )
        legacy_upload = (
            "          name: fp0006-legacy-live-ioctl-${{ github.run_id }}-${{ github.run_attempt }}\n"
            "          path: ${{ runner.temp }}/mckernel-hosted-boot-${{ github.run_id }}-${{ github.run_attempt }}/qemu/guest-evidence/fp0006-legacy-live-ioctl/fp0006-runtime-capture-v1.tar\n"
            "          if-no-files-found: error\n"
            "          retention-days: 30\n"
            "          compression-level: 0\n"
        )
        mutations = (
            (capture._validate_native_workflow, self._replace_once(self.native_workflow, bootstrap_start, bootstrap_start + "          exit 0\n")),
            (capture._validate_native_workflow, self._replace_once(self.native_workflow, bootstrap_start, bootstrap_start + "          trap 'exit 0' ERR\n")),
            (capture._validate_native_workflow, self._replace_once(
                self.native_workflow,
                native_install,
                native_install.replace("coreutils\n", "coreutils-single\n"),
            )),
            (capture._validate_native_workflow, self._replace_once(
                self.native_workflow,
                "            /usr/bin/timeout --signal=TERM --kill-after=5s 30s \\\n",
                "          if false; then\n            /usr/bin/timeout --signal=TERM --kill-after=5s 30s \\\n",
            )),
            (capture._validate_native_workflow, self._replace_once(
                self.native_workflow,
                native_upload,
                native_upload.replace("compression-level: 0", "compression-level: 9"),
            )),
            (capture._validate_native_workflow, self._replace_once(
                self.native_workflow,
                native_failure_upload,
                native_failure_upload.replace("compression-level: 0", "compression-level: 9"),
            )),
            (capture._validate_native_workflow, self._replace_once(self.native_workflow, "            /usr/bin/timeout --signal=TERM --kill-after=5s 30s \\\n", "")),
            (capture._validate_native_workflow, self._replace_once(
                self.native_workflow,
                native_steps_start,
                native_steps_start + "    \"runs-on\": self-hosted\n",
            )),
            (capture._validate_legacy_workflow, self._replace_once(
                self.legacy_workflow,
                legacy_trust_preamble,
                legacy_trust_preamble.replace(
                    "    runs-on: ubuntu-24.04\n", "    runs-on: [self-hosted]\n"
                ),
            )),
            (capture._validate_legacy_workflow, self._replace_once(
                self.legacy_workflow,
                legacy_trust_preamble,
                legacy_trust_preamble.replace(
                    "    if: >-\n"
                    "      ${{ github.event_name == 'pull_request' &&\n"
                    "          github.event.pull_request.head.repo.full_name == github.repository }}\n",
                    "    if: ${{ false }}\n",
                ),
            )),
            (capture._validate_legacy_workflow, self._replace_once(
                self.legacy_workflow,
                legacy_steps_start,
                legacy_steps_start + "    \"if\": ${{ always() }}\n",
            )),
            (capture._validate_legacy_workflow, self._replace_once(
                self.legacy_workflow,
                legacy_upload,
                legacy_upload.replace("compression-level: 0", "compression-level: 9"),
            )),
        )
        for index, (validator, mutation) in enumerate(mutations):
            with self.subTest(index=index):
                with self.assertRaises(capture.CaptureError):
                    validator(mutation, policy)

    def test_qemu_and_rocky_boundaries_are_active(self):
        rocky = (ROOT / "scripts/rocky-rust-validation.sh").read_text(
            encoding="utf-8"
        )
        capture._validate_rocky_script(rocky)
        rocky_capture = "\tcapture_fp0006_legacy_negative_dispatch\n"
        rocky_live_mutations = (
            self._replace_once(
                rocky,
                rocky_capture,
                "\tif false; then\n"
                "\t\tcapture_fp0006_legacy_negative_dispatch\n"
                "\tfi\n",
            ),
            self._replace_once(
                rocky,
                rocky_capture,
                "\ttrap 'exit 0' ERR\n" + rocky_capture,
            ),
            self._replace_once(
                rocky,
                rocky_capture,
                "\treturn 0\n" + rocky_capture,
            ),
        )
        preflight_pair = (
            "preflight_fp0006_legacy_negative_dispatch\n"
            "update_submodules\n"
        )
        rocky_preflight_mutations = (
            self._replace_once(
                rocky,
                preflight_pair,
                "if false; then\n" + preflight_pair + "fi\n",
            ),
            self._replace_once(
                rocky,
                preflight_pair,
                "update_submodules\n"
                "preflight_fp0006_legacy_negative_dispatch\n",
            ),
        )
        for index, mutation in enumerate(
            rocky_live_mutations + rocky_preflight_mutations
        ):
            with self.subTest(source="rocky", index=index):
                with self.assertRaises(capture.CaptureError):
                    capture._validate_rocky_script(mutation)
        wrapper = (ROOT / "scripts/qemu-rocky-rust-validation.sh").read_text(
            encoding="utf-8"
        )
        runner = (ROOT / "scripts/qemu-mckernel-guest.sh").read_text(
            encoding="utf-8"
        )
        capture._validate_qemu_sources(wrapper, runner)
        wrapper_exec = 'exec "$QEMU_RUNNER" "${qemu_args[@]}"\n'
        wrapper_stage_order = (
            "\t--guest-evidence-dir /tmp/mckernel-validation-evidence\n"
            "\t--stage-dir \"$SOURCE_DIR:/tmp/mckernel-hostshare\"\n"
        )
        wrapper_mutations = (
            self._replace_once(
                wrapper, wrapper_exec,
                '# exec "$QEMU_RUNNER" "${qemu_args[@]}"\ntrue\n',
            ),
            self._replace_once(
                wrapper, wrapper_exec,
                'if false; then\n\texec "$QEMU_RUNNER" "${qemu_args[@]}"\nfi\n',
            ),
            self._replace_once(
                wrapper, wrapper_exec,
                "trap 'exit 0' ERR\n" + wrapper_exec,
            ),
            self._replace_once(
                wrapper, wrapper_exec, "exit 0\n" + wrapper_exec,
            ),
            self._replace_once(
                wrapper,
                wrapper_stage_order,
                "\t--stage-dir \"$SOURCE_DIR:/tmp/mckernel-hostshare\"\n"
                "\t--guest-evidence-dir /tmp/mckernel-validation-evidence\n",
            ),
        )
        for index, mutation in enumerate(wrapper_mutations):
            with self.subTest(source="wrapper", index=index):
                with mock.patch.object(
                    capture,
                    "EXPECTED_QEMU_WRAPPER_ACTIVE_SHA256",
                    capture._active_digest(mutation),
                ):
                    with self.assertRaises(capture.CaptureError):
                        capture._validate_qemu_sources(mutation, runner)

        runner_remove = '\t\trm -f "$OVERLAY"\n'
        runner_trap_and_create = (
            "trap cleanup EXIT\n"
            "\n"
            "say \"Preparing disposable guest overlay\"\n"
            "qemu-img create -f qcow2 -F \"$BASE_FORMAT\" -b \"$IMAGE\" \"$OVERLAY\" >/dev/null\n"
        )
        runner_mutations = (
            self._replace_once(
                runner, runner_remove, '\t\t# rm -f "$OVERLAY"\n\t\ttrue\n',
            ),
            self._replace_once(
                runner, runner_remove,
                '\t\tif false; then\n\t\t\trm -f "$OVERLAY"\n\t\tfi\n',
            ),
            self._replace_once(
                runner, "trap cleanup EXIT\n", "trap 'exit 0' ERR\ntrap cleanup EXIT\n",
            ),
            self._replace_once(
                runner, "trap cleanup EXIT\n", "exit 0\ntrap cleanup EXIT\n",
            ),
            self._replace_once(
                runner,
                runner_trap_and_create,
                "say \"Preparing disposable guest overlay\"\n"
                "qemu-img create -f qcow2 -F \"$BASE_FORMAT\" -b \"$IMAGE\" \"$OVERLAY\" >/dev/null\n"
                "trap cleanup EXIT\n",
            ),
        )
        for index, mutation in enumerate(runner_mutations):
            with self.subTest(source="runner", index=index):
                with mock.patch.object(
                    capture,
                    "EXPECTED_QEMU_RUNNER_ACTIVE_SHA256",
                    capture._active_digest(mutation),
                ):
                    with self.assertRaises(capture.CaptureError):
                        capture._validate_qemu_sources(wrapper, mutation)

    def test_native_runtime_validator_rejects_active_command_decoys(self):
        native_rust_runtime_evidence._validate_exact_build_workflow(
            self.native_workflow
        )
        bootstrap_start = (
            "      - name: Install pinned Rust and identify the observed FP-0006 linker\n"
            "        run: |\n"
            "          set -euo pipefail\n"
        )
        native_install = (
            "          dnf -y --allowerasing --setopt=install_weak_deps=False install \\\n"
            "            coreutils\n"
        )
        for mutation in (
            self._replace_once(
                self.native_workflow,
                bootstrap_start,
                bootstrap_start + "          exit 0\n",
            ),
            self._replace_once(
                self.native_workflow,
                bootstrap_start,
                bootstrap_start + "          trap 'exit 0' ERR\n",
            ),
            self._replace_once(
                self.native_workflow,
                native_install,
                native_install.replace("coreutils\n", "coreutils-single\n"),
            ),
            self._replace_once(
                self.native_workflow,
                "            /usr/bin/timeout --signal=TERM --kill-after=5s 30s \\\n",
                "            if false; then\n            /usr/bin/timeout --signal=TERM --kill-after=5s 30s \\\n",
            ),
        ):
            with self.assertRaises(native_rust_runtime_evidence.EvidenceError):
                native_rust_runtime_evidence._validate_exact_build_workflow(mutation)

    def test_workflow_control_checks_survive_coherent_rebinding(self):
        policy = self.contract["workflow_policy"]
        native_capture_start = (
            "      - name: Produce and review the FP-0006 native envelope\n"
            "        run: |\n"
            "          set -euo pipefail\n"
        )
        timeout_start = (
            "          if /usr/bin/env -i HOME=/nonexistent LANG=C LC_ALL=C PATH=/usr/bin:/bin \\\n"
            "            /usr/bin/timeout --signal=TERM --kill-after=5s 30s \\\n"
        )
        timeout_end = "          fi\n          {\n"
        native_outer_if = self._replace_once(
            self.native_workflow,
            timeout_start,
            "          if false; then\n" + timeout_start,
        )
        native_outer_if = self._replace_once(
            native_outer_if,
            timeout_end,
            "          fi\n          fi\n          {\n",
        )
        native_mutations = (
            native_outer_if,
            self._replace_once(
                self.native_workflow,
                native_capture_start,
                native_capture_start + "          trap 'exit 0' ERR\n",
            ),
            self._replace_once(
                self.native_workflow,
                native_capture_start,
                native_capture_start + "          exit 0\n",
            ),
            self._replace_once(
                self.native_workflow,
                native_capture_start,
                native_capture_start + "          return 0\n",
            ),
        )
        native_separator = "\n  fp0006-native-rust-capture:\n"
        capture_separator = "\n  rk006-full-source-build-capture:\n"
        for index, mutation in enumerate(native_mutations):
            mutated_job = capture._extract_job(
                mutation, policy["native_job"], "mutated native workflow"
            )
            _, mutated_steps = capture._extract_steps(
                mutated_job, "mutated native job"
            )
            _, native_tail = mutation.split(native_separator, 1)
            native_body, _ = native_tail.split(capture_separator, 1)
            runtime_job = "  fp0006-native-rust-capture:\n" + native_body
            with self.subTest(surface="native", index=index):
                with mock.patch.object(
                    capture,
                    "EXPECTED_NATIVE_WORKFLOW_SHA256",
                    hashlib.sha256(mutation.encode("utf-8")).hexdigest(),
                ), mock.patch.object(
                    capture,
                    "EXPECTED_NATIVE_CAPTURE_ACTIVE_SHA256",
                    capture._active_digest(
                        mutated_steps[policy["native_capture_step"]]
                    ),
                ):
                    with self.assertRaises(capture.CaptureError):
                        capture._validate_native_workflow(mutation, policy)
                with mock.patch.object(
                    native_rust_runtime_evidence,
                    "EXPECTED_FP0006_NATIVE_JOB_SHA256",
                    hashlib.sha256(runtime_job.encode("utf-8")).hexdigest(),
                ):
                    with self.assertRaises(
                        native_rust_runtime_evidence.EvidenceError
                    ):
                        native_rust_runtime_evidence._validate_exact_build_workflow(
                            mutation
                        )

        legacy_boot_start = (
            "      - name: Boot disposable Rocky guest and run mcexec\n"
            "        shell: bash\n"
            "        run: |\n"
            "          set -euo pipefail\n"
        )
        legacy_boot_end = (
            "            2>&1 | tee \"$HOSTED_BOOT_DIR/run.log\"\n\n"
        )
        legacy_boot_if = self._replace_once(
            self.legacy_workflow,
            legacy_boot_start,
            legacy_boot_start + "          if false; then\n",
        )
        legacy_boot_if = self._replace_once(
            legacy_boot_if,
            legacy_boot_end,
            legacy_boot_end.rstrip("\n") + "\n          fi\n\n",
        )
        legacy_finalize_start = (
            "      - name: Finalize and verify FP-0006 legacy envelope on the clean host\n"
            "        shell: bash\n"
            "        run: |\n"
            "          set -euo pipefail\n"
        )
        legacy_mutations = (
            (policy["legacy_boot_step"], "EXPECTED_LEGACY_BOOT_ACTIVE_SHA256", legacy_boot_if),
            (
                policy["legacy_boot_step"],
                "EXPECTED_LEGACY_BOOT_ACTIVE_SHA256",
                self._replace_once(
                    self.legacy_workflow,
                    legacy_boot_start,
                    legacy_boot_start + "          trap 'exit 0' ERR\n",
                ),
            ),
            (
                policy["legacy_boot_step"],
                "EXPECTED_LEGACY_BOOT_ACTIVE_SHA256",
                self._replace_once(
                    self.legacy_workflow,
                    legacy_boot_start,
                    legacy_boot_start + "          exit 0\n",
                ),
            ),
            (
                policy["legacy_boot_step"],
                "EXPECTED_LEGACY_BOOT_ACTIVE_SHA256",
                self._replace_once(
                    self.legacy_workflow,
                    legacy_boot_start,
                    legacy_boot_start + "          return 0\n",
                ),
            ),
            (
                policy["legacy_finalize_step"],
                "EXPECTED_LEGACY_FINALIZE_ACTIVE_SHA256",
                self._replace_once(
                    self.legacy_workflow,
                    legacy_finalize_start,
                    legacy_finalize_start + "          trap 'exit 0' ERR\n",
                ),
            ),
            (
                policy["legacy_finalize_step"],
                "EXPECTED_LEGACY_FINALIZE_ACTIVE_SHA256",
                self._replace_once(
                    self.legacy_workflow,
                    legacy_finalize_start,
                    legacy_finalize_start + "          exit 0\n",
                ),
            ),
            (
                policy["legacy_finalize_step"],
                "EXPECTED_LEGACY_FINALIZE_ACTIVE_SHA256",
                self._replace_once(
                    self.legacy_workflow,
                    legacy_finalize_start,
                    legacy_finalize_start + "          return 0\n",
                ),
            ),
        )
        for index, (step_name, digest_name, mutation) in enumerate(
            legacy_mutations
        ):
            mutated_job = capture._extract_job(
                mutation, policy["legacy_job"], "mutated legacy workflow"
            )
            _, mutated_steps = capture._extract_steps(
                mutated_job, "mutated legacy job"
            )
            with self.subTest(surface="legacy", index=index):
                with mock.patch.object(
                    capture,
                    "EXPECTED_LEGACY_WORKFLOW_SHA256",
                    hashlib.sha256(mutation.encode("utf-8")).hexdigest(),
                ), mock.patch.object(
                    capture,
                    digest_name,
                    capture._active_digest(mutated_steps[step_name]),
                ):
                    with self.assertRaises(capture.CaptureError):
                        capture._validate_legacy_workflow(mutation, policy)

    def test_ustar_round_trip_is_exact(self):
        members = [("a", b"one\n"), ("b", b"two\n")]
        archive = capture._build_tar(members)
        self.assertEqual(dict(members), capture._parse_tar(archive, ("a", "b")))
        self.assertEqual(0, len(archive) % capture.TAR_RECORD)

    def test_ustar_rejects_order_metadata_and_trailing_attacks(self):
        archive = capture._build_tar((("a", b"one"), ("b", b"two")))
        attacks = []
        attacks.append(archive + b"\0" * capture.TAR_RECORD)
        changed_mode = bytearray(archive)
        changed_mode[100:108] = b"0000644\0"
        attacks.append(bytes(changed_mode))
        changed_type = bytearray(archive)
        changed_type[156:157] = b"2"
        attacks.append(bytes(changed_type))
        changed_trailer = bytearray(archive)
        changed_trailer[-1] = 1
        attacks.append(bytes(changed_trailer))
        for index, value in enumerate(attacks):
            with self.subTest(index=index):
                with self.assertRaises(capture.CaptureError):
                    capture._parse_tar(value, ("a", "b"))
        with self.assertRaises(capture.CaptureError):
            capture._parse_tar(archive, ("b", "a"))

    def test_transport_zip_is_only_an_envelope_carrier(self):
        envelope = capture._build_tar((("a", b"one"),))
        with tempfile.TemporaryDirectory() as directory:
            good = Path(directory) / "good.zip"
            with zipfile.ZipFile(str(good), "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(capture.ENVELOPE_NAME, envelope)
            self.assertEqual(envelope, capture._artifact_tar_bytes(good))
            bad = Path(directory) / "bad.zip"
            with zipfile.ZipFile(str(bad), "w") as archive:
                archive.writestr(capture.ENVELOPE_NAME, envelope)
                archive.writestr("extra", b"x")
            with self.assertRaises(capture.CaptureError):
                capture._artifact_tar_bytes(bad)

    def _capture_dir(self, parent, surface):
        root = Path(parent) / ("capture-" + surface)
        root.mkdir(mode=0o700)
        values = {
            "raw.jsonl": raw_stream(),
            "result.jsonl": result_stream(surface),
            "state-ledger.jsonl": ledger_stream(surface),
        }
        for name, value in values.items():
            path = root / name
            path.write_bytes(value)
            path.chmod(0o444)
        return root, values

    def _native_lane(self, parent, run_id="10"):
        root = Path(parent)
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        capture_dir, _ = self._capture_dir(root, "native-rust-source-fixture")
        producer = root / "native-producer"
        producer.write_bytes(b"native-binary")
        tool = root / "native-tools"
        tool.write_bytes(self._native_tools())
        compiler_output = root / "native-compiler.log"
        compiler_output.write_bytes(b"")
        output = root / "native-output"
        output.write_bytes(b"")
        producer_log = root / "native-producer.log"
        github = self._github(run_id)
        start = dict(github)
        start.update({
            "binary_sha256": hashlib.sha256(producer.read_bytes()).hexdigest(),
            "event": "producer-start",
            "linker": "/usr/bin/gcc",
            "normalized_command": capture._producer_command("native-rust-source-fixture"),
            "surface": "native-rust-source-fixture",
            "timeout_seconds": 30,
            "tool_report_sha256": hashlib.sha256(tool.read_bytes()).hexdigest(),
        })
        producer_log.write_bytes(
            canonical(start)
            + canonical(
                {
                    "event": "producer-output", "output_bytes": 0,
                    "output_sha256": capture.EMPTY_SHA256,
                    "surface": "native-rust-source-fixture",
                }
            )
            + canonical(
                {"event": "producer-exit", "status": 0, "surface": "native-rust-source-fixture"}
            )
        )
        envelope = root / "native-envelope"
        capture.finalize_lane(
            ROOT, capture_dir, output, producer_log, producer, tool,
            compiler_output, envelope, "native-rust-source-fixture", self.head,
            self.repository, run_id, "1", self.event_name, self.ref,
            self.github_sha, self.workflow_sha, self.base_sha,
        )
        return envelope

    def _legacy_lane(self, parent, run_id="20"):
        root = Path(parent)
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        producer = root / "legacy-producer"
        producer.write_bytes(b"legacy-binary")
        tools = root / "legacy-tools"
        tools.write_bytes(self._legacy_tools())
        compiler_output = root / "legacy-compiler.log"
        compiler_output.write_bytes(b"")
        preflight = root / "preflight.json"
        capture.preflight_legacy(
            ROOT, producer, tools, compiler_output, preflight, self.head,
            self.repository, run_id, "1", self.event_name, self.ref,
            self.github_sha, self.workflow_sha, self.base_sha,
        )
        capture_dir, values = self._capture_dir(root, "legacy-live-ioctl")
        observation = root / "observation"
        observation.mkdir()
        capture_tar = capture._build_tar(
            [(name, values[name]) for name in ("raw.jsonl", "result.jsonl", "state-ledger.jsonl")]
        )
        (observation / "capture.tar").write_bytes(capture_tar)
        (observation / "preflight.json").write_bytes(preflight.read_bytes())
        preflight_value = json.loads(preflight.read_text(encoding="utf-8"))
        github = self._github(run_id)
        start = dict(github)
        start.update({
            "binary_sha256": preflight_value["producer_binary"]["sha256"],
            "device": "/dev/mcd0",
            "event": "producer-start",
            "normalized_command": capture._producer_command("legacy-live-ioctl"),
            "overlay_host_driver_sha256": self.contract["surfaces"]["legacy-live-ioctl"]["expected_overlay_host_driver_sha256"],
            "preflight_sha256": hashlib.sha256(preflight.read_bytes()).hexdigest(),
            "surface": "legacy-live-ioctl",
            "timeout_seconds": 30,
            "tool_report_sha256": preflight_value["compiler_observation"]["sha256"],
        })
        log = (
            canonical(start)
            + canonical(
                {
                    "event": "producer-output", "output_bytes": 0,
                    "output_sha256": capture.EMPTY_SHA256,
                    "surface": "legacy-live-ioctl",
                }
            )
            + canonical({"event": "producer-exit", "status": 0, "surface": "legacy-live-ioctl"})
        )
        (observation / "producer.log").write_bytes(log)
        (observation / "compiler.log").write_bytes(b"")
        (observation / "producer-output.log").write_bytes(b"")
        (observation / "tool-report.txt").write_bytes(tools.read_bytes())
        files = [
            ("capture.tar", capture_tar),
            ("compiler.log", b""),
            ("preflight.json", preflight.read_bytes()),
            ("producer-output.log", b""),
            ("producer.log", log),
            ("tool-report.txt", tools.read_bytes()),
        ]
        (observation / "SHA256SUMS").write_bytes(capture._manifest(files))
        envelope = root / "legacy-envelope"
        capture.finalize_legacy_observation(
            ROOT, observation, envelope, self.head, self.repository, run_id, "1",
            self.event_name, self.ref, self.github_sha, self.workflow_sha,
            self.base_sha,
        )
        return envelope

    def test_native_and_legacy_lane_finalization_remain_noncrediting(self):
        with tempfile.TemporaryDirectory() as directory:
            native = self._native_lane(Path(directory) / "native")
            legacy = self._legacy_lane(Path(directory) / "legacy")
            native_result = capture.review_lane(
                ROOT, native, "native-rust-source-fixture", self.head,
                self.repository, "10", "1",
            )
            legacy_result = capture.review_lane(
                ROOT, legacy, "legacy-live-ioctl", self.head,
                self.repository, "20", "1",
            )
            self.assertTrue(all(value is False for value in native_result["claims"].values()))
            self.assertTrue(all(value is False for value in legacy_result["claims"].values()))

    def test_envelopes_archive_actual_empty_outputs_and_tool_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            native = self._native_lane(Path(directory) / "native")
            files = capture._parse_tar(
                capture._artifact_tar_bytes(native),
                self.contract["artifact_policy"]["envelope_members"],
            )
            self.assertEqual(b"", files["compiler.log"])
            self.assertEqual(b"", files["producer-output.log"])
            self.assertEqual(self._native_tools(), files["tool-report.txt"])
            self.assertIn(b'"exact_toolchain_proven":false', files["authority.json"])

    def test_failed_or_interrupted_review_never_publishes_upload_path(self):
        for target in ("review", "publish"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / target
                patched = (
                    mock.patch.object(
                        capture, "_review_lane_with_contract",
                        side_effect=capture.CaptureError("forced review failure"),
                    )
                    if target == "review"
                    else mock.patch.object(
                        capture, "_publish_candidate",
                        side_effect=capture.CaptureError("forced publication interruption"),
                    )
                )
                with patched, self.assertRaises(capture.CaptureError):
                    self._native_lane(root)
                self.assertFalse((root / "native-envelope").exists())
                self.assertFalse((root / ".native-envelope.candidate").exists())

    def test_preexisting_upload_path_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "native"
            final = root / "native-envelope"
            final.mkdir(parents=True)
            marker = final / "user-data"
            marker.write_bytes(b"preserve")
            with self.assertRaises(capture.CaptureError):
                self._native_lane(root)
            self.assertEqual(b"preserve", marker.read_bytes())

    def test_pair_requires_same_head_repository_and_raw_vectors(self):
        with tempfile.TemporaryDirectory() as directory:
            native = self._native_lane(Path(directory) / "native")
            legacy = self._legacy_lane(Path(directory) / "legacy")
            result = capture.review_pair(
                ROOT, legacy, native, self.head, self.repository
            )
            self.assertTrue(result["artifact_pair_validated"])
            self.assertEqual("required-missing", result["result_authority"])
            self.assertFalse(result["claims"]["gate_pass"])
            with self.assertRaises(capture.CaptureError):
                capture.review_pair(
                    ROOT, legacy, native, self.head, "attacker/example"
                )

    def test_bool_integer_aliases_are_rejected(self):
        with self.assertRaises(capture.CaptureError):
            capture._validate_run_metadata(self.head, self.repository, True, "1")
        with self.assertRaises(capture.CaptureError):
            capture._require_int(False, "boolean alias")
        self.assertEqual(
            "A1/repo.name_2-test",
            capture._validate_run_metadata(
                self.head, "A1/repo.name_2-test", "10", "1"
            )[1],
        )
        for repository in (
            "../repo", "owner/..", ".owner/repo", "owner/repo.",
            "-owner/repo", "owner-/repo", "_owner/repo", "owner_/repo",
            "owner/-repo", "owner/repo-", "owner/_repo", "owner/repo_",
        ):
            with self.subTest(repository=repository):
                with self.assertRaises(capture.CaptureError):
                    capture._validate_run_metadata(
                        self.head, repository, "10", "1"
                    )

    def test_execution_log_rejects_failed_or_nonempty_output(self):
        github = self._github("1")
        start = dict(github)
        start.update({
            "binary_sha256": "a" * 64, "event": "producer-start",
            "linker": "/usr/bin/gcc",
            "normalized_command": capture._producer_command("native-rust-source-fixture"),
            "surface": "native-rust-source-fixture", "timeout_seconds": 30,
            "tool_report_sha256": "b" * 64,
        })
        for output_bytes, status in ((1, 0), (0, 1)):
            log = (
                canonical(start)
                + canonical(
                    {
                        "event": "producer-output", "output_bytes": output_bytes,
                        "output_sha256": capture.EMPTY_SHA256,
                        "surface": "native-rust-source-fixture",
                    }
                )
                + canonical(
                    {"event": "producer-exit", "status": status, "surface": "native-rust-source-fixture"}
                )
            )
            with self.assertRaises(capture.CaptureError):
                capture._validate_execution_log(
                    log, "native-rust-source-fixture", github, "a" * 64, "b" * 64
                )


if __name__ == "__main__":
    unittest.main()
