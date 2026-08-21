#!/usr/bin/env python3

from __future__ import print_function

import hashlib
import json
import re
import subprocess
import unittest
from pathlib import Path

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


class NativeRustExactBuildWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.source_workflow = SOURCE_WORKFLOW.read_text(encoding="utf-8")

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
        self.assertIn("ARCH=x86_64 LLVM=1 -j2 bzImage", self.workflow)
        self.assertIn(
            'ARCH=x86_64 LLVM=1 -j2 "${module_targets[@]}"', self.workflow
        )
        self.assertLess(
            self.workflow.index("ARCH=x86_64 LLVM=1 -j2 bzImage"),
            self.workflow.index(
                'ARCH=x86_64 LLVM=1 -j2 "${module_targets[@]}"'
            ),
        )
        self.assertNotRegex(self.workflow, r"(?m)^\s*make\s+.*\bmodules\b")
        self.assertIn(
            'cp "$NATIVE_BUILD_DIR/arch/x86/boot/bzImage" "$EVIDENCE_DIR/bzImage"',
            self.workflow,
        )
        self.assertIn('> "$EVIDENCE_DIR/kernel.release"', self.workflow)
        self.assertIn("include-hidden-files: true", self.workflow)

    def test_module_modpost_cannot_precede_kernel_symbol_universe(self):
        bzimage = (
            '            run_phase bzImage \\\n'
            '              make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\\n'
            '                ARCH=x86_64 LLVM=1 -j2 bzImage\n'
        )
        modules = (
            '            run_phase native-modules \\\n'
            '              make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\\n'
            '                ARCH=x86_64 LLVM=1 -j2 "${module_targets[@]}"\n'
        )
        self.assertEqual(1, self.workflow.count(bzimage))
        self.assertEqual(1, self.workflow.count(modules))
        mutation = self.workflow.replace(bzimage, "__BZIMAGE_PHASE__\n", 1)
        mutation = mutation.replace(modules, bzimage, 1)
        mutation = mutation.replace("__BZIMAGE_PHASE__\n", modules, 1)
        with self.assertRaisesRegex(
            runtime_evidence.EvidenceError, "commands are out of order"
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
            "python3 scripts/native_rust_runtime_evidence.py \\\n"
            '            --repo "$GITHUB_WORKSPACE" --check-contract',
            self.workflow,
        )

    def test_broad_module_build_mutation_is_rejected(self):
        mutation = self.workflow.replace(
            'ARCH=x86_64 LLVM=1 -j2 "${module_targets[@]}"',
            "ARCH=x86_64 LLVM=1 -j2 modules",
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
                '                ARCH=x86_64 LLVM=1 rustavailable\n',
                '                ARCH=x86_64 LLVM=1 rustavailable || true\n',
            ),
        ):
            mutation = self.workflow.replace(old, new, 1)
            with self.subTest(mutation=new.strip()):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError,
                    "failure (capture|evidence)|masks a phase failure",
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
        blocks = (
            (
                '            run_phase rustavailable \\\n'
                '              make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\\n'
                "                ARCH=x86_64 LLVM=1 rustavailable\n"
            ),
            (
                '            run_phase bzImage \\\n'
                '              make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\\n'
                "                ARCH=x86_64 LLVM=1 -j2 bzImage\n"
            ),
            (
                '            run_phase native-modules \\\n'
                '              make -C "$NATIVE_SOURCE_ROOT" O="$NATIVE_BUILD_DIR" \\\n'
                '                ARCH=x86_64 LLVM=1 -j2 "${module_targets[@]}"\n'
            ),
        )
        commented = self.workflow
        decoy = self.workflow
        decoy_body = ""
        for block in blocks:
            self.assertEqual(1, commented.count(block))
            collapsed = " ".join(
                line.strip().rstrip("\\").strip() for line in block.splitlines()
            )
            commented = commented.replace(block, "            # " + collapsed + "\n", 1)
            decoy = decoy.replace(block, "", 1)
            decoy_body += block
        decoy = decoy.replace(
            "      - name: Validate built metadata and capture immutable diagnostics\n",
            "      - name: Decoy build commands\n"
            "        run: |\n"
            + decoy_body
            + "\n      - name: Validate built metadata and capture immutable diagnostics\n",
            1,
        )
        conditional_runner = self.workflow.replace(
            '            "${command[@]}"\n',
            "            if false; then\n"
            '              "${command[@]}"\n'
            "            fi\n",
            1,
        )
        for label, mutation in (
            ("commented", commented),
            ("decoy-step", decoy),
            ("conditional-runner", conditional_runner),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    runtime_evidence.EvidenceError,
                    "command scope|compile step|failure capture",
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
                    runtime_evidence.EvidenceError, "artifact scope differs"
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
                "python3 scripts/rocky_kernel_rk006_full_source_build_capture.py"
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
            "          python3 scripts/rocky_kernel_rk006_full_source_build_capture.py capture \\\n",
            "          # python3 scripts/rocky_kernel_rk006_full_source_build_capture.py capture \\\n",
            1,
        )
        finalize_header = "      - name: Finalize the non-crediting build binding\n"
        early_exit = self.workflow.replace(
            finalize_header + "        run: |\n          set -euo pipefail\n",
            finalize_header + "        run: |\n          set -euo pipefail\n          exit 0\n",
            1,
        )
        error_trap = self.workflow.replace(
            finalize_header + "        run: |\n          set -euo pipefail\n",
            finalize_header
            + "        run: |\n          set -euo pipefail\n          trap 'exit 0' ERR\n",
            1,
        )
        step_conditional = self.workflow.replace(
            finalize_header + "        run: |\n",
            finalize_header + "        if: ${{ success() }}\n        run: |\n",
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
        self.assertIn('--rustc "$(command -v rustc)" --require-rustc', self.workflow)

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
            "python3 -m unittest -v "
            "scripts.tests.test_rust_target_compatibility_patches",
            self.workflow,
        )
        self.assertIn(
            'MCKERNEL_RUSTC_1_92="$(command -v rustc)" \\\n'
            "            python3 -m unittest -v "
            "scripts.tests.test_rust_target_compatibility_patches",
            self.workflow,
        )
        self.assertGreaterEqual(
            self.workflow.count("--fuzz=0 --no-backup-if-mismatch"), 3
        )

    def test_final_config_keeps_warnings_fatal(self):
        second_resolution = self.workflow.index(
            'make -C "$NATIVE_SOURCE_ROOT" O="$BUILD_DIR" '
            "ARCH=x86_64 LLVM=1 olddefconfig",
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
            'make -C "$NATIVE_SOURCE_ROOT" O="$BUILD_DIR" '
            "ARCH=x86_64 LLVM=1 olddefconfig",
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
                    runtime_evidence.EvidenceError, "CONFIG_MODULES prerequisite differs"
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
                    runtime_evidence.EvidenceError, "CONFIG_MODULES prerequisite differs"
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

        solver_run = "python3 scripts/native_rust_kconfig_solver.py run \\\n"
        solver_check = "python3 scripts/native_rust_kconfig_solver.py check \\\n"
        link_output = "python3 scripts/native_rust_kbuild_link_closure.py \\\n"
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
            ("solver-run", "          " + solver_run),
            ("solver-check", "          " + solver_check),
            ("link-output", "          " + link_output),
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
        objtool_noreturn = self.workflow.index(
            "0021-objtool-recognize-rust-1.92-panic-const.patch",
            miscdevice,
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
        self.assertLess(miscdevice, objtool_noreturn)
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

    def test_built_module_diagnostics_precede_semantic_validation(self):
        validation = self.workflow.index(
            "Validate built metadata and capture immutable diagnostics"
        )
        checker = self.workflow.index(
            "python3 scripts/ihk_native_lifecycle_check.py", validation
        )
        for fragment in (
            'git -c safe.directory="$GITHUB_WORKSPACE" rev-parse HEAD',
            '> "$EVIDENCE_DIR/commit.sha"',
            'cp "$module" "$EVIDENCE_DIR/$name"',
            'modinfo "$module" > "$EVIDENCE_DIR/$name.modinfo"',
            'readelf -p .modinfo "$module" '
            '> "$EVIDENCE_DIR/$name.modinfo-section"',
            'readelf -SWr "$module" > "$EVIDENCE_DIR/$name.readelf"',
            'nm -A -a "$module" > "$EVIDENCE_DIR/$name.nm"',
            '| sort -z | xargs -0 sha256sum -- > PRECHECK_SHA256SUMS',
            'sha256sum --check --strict PRECHECK_SHA256SUMS',
        ):
            with self.subTest(fragment=fragment):
                diagnostic = self.workflow.index(fragment, validation)
                self.assertLess(diagnostic, checker)
        final_input = self.workflow.index(
            'kernelrelease > "$EVIDENCE_DIR/kernel.release"', checker
        )
        final_manifest = self.workflow.index(
            '| sort -z | xargs -0 sha256sum -- > SHA256SUMS', checker
        )
        self.assertLess(final_input, final_manifest)
        self.assertIn(
            "! -name PRECHECK_SHA256SUMS ! -name SHA256SUMS",
            self.workflow[validation:checker],
        )

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
            'test "$(git -C ihk rev-parse HEAD)" = '
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
                'python3 scripts/ihk_os_registry_check.py --repo "$GITHUB_WORKSPACE"'
            ),
            2,
        )
        self.assertGreaterEqual(
            self.workflow.count('MCKERNEL_RUSTC_1_92="$(command -v rustc)"'), 2
        )
        self.assertGreaterEqual(
            self.workflow.count(
                "python3 -m unittest -v scripts.tests.test_ihk_os_registry_check"
            ),
            2,
        )
        self.assertGreaterEqual(
            self.workflow.count(
                "python3 scripts/native_rust_unsafe_ffi_ledger.py "
                '--repo "$GITHUB_WORKSPACE" check'
            ),
            1,
        )

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
            "python3 scripts/linux_api_exact_probe.py "
            '--repo "$GITHUB_WORKSPACE" check-contract',
            self.workflow.replace("\\\n            ", ""),
        )
        self.assertIn(
            "python3 scripts/x86_64_shared_abi.py "
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
                'python3 scripts/ihk_ioctl_dispatch_check.py --repo "$GITHUB_WORKSPACE"'
            ),
            3,
        )
        self.assertIn('--kernel-source "$source_root"', self.workflow)
        self.assertGreaterEqual(
            self.workflow.count(
                "python3 -m unittest -v scripts.tests.test_ihk_ioctl_dispatch_check"
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
            'IHK_PAGE_ALLOCATOR_RUSTC="$(command -v rustc)"', self.workflow
        )
        self.assertIn(
            'IHK_PAGE_OWNER_REGISTRY_RUSTC="$(command -v rustc)"', self.workflow
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
