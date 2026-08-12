#!/usr/bin/env python3

from __future__ import print_function

import hashlib
import re
import subprocess
import unittest
from pathlib import Path

import yaml

from scripts import native_rust_runtime_evidence as runtime_evidence


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/native-rust-host-modules-exact-build.yml"
SOURCE_WORKFLOW = REPO_ROOT / ".github/workflows/rocky-kernel-source-evidence.yml"
PATCH = REPO_ROOT / "host-kernel/kbuild/patches/0002-rust-bindings-expose-module-parameters.patch"
CONFIG = REPO_ROOT / "host-kernel/rocky/configs/native-rust-evidence.config"


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
            self.workflow.index(
                'ARCH=x86_64 LLVM=1 -j2 "${module_targets[@]}"'
            ),
            self.workflow.index("ARCH=x86_64 LLVM=1 -j2 bzImage"),
        )
        self.assertNotRegex(self.workflow, r"(?m)^\s*make\s+.*\bmodules\b")
        self.assertIn(
            'cp "$NATIVE_BUILD_DIR/arch/x86/boot/bzImage" "$EVIDENCE_DIR/bzImage"',
            self.workflow,
        )
        self.assertIn('> "$EVIDENCE_DIR/kernel.release"', self.workflow)
        self.assertIn("include-hidden-files: true", self.workflow)

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

    def test_exact_three_module_config_and_artifacts_are_required(self):
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
        self.assertGreaterEqual(
            self.workflow.count("--fuzz=0 --no-backup-if-mismatch"), 3
        )

    def test_upstream_rust_compatibility_series_precedes_project_staging(self):
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
        project = self.workflow.index(
            "0001-drivers-misc-add-mckernel-rust-host-modules.patch",
            objtool_noreturn,
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
        self.assertLess(objtool_noreturn, project)

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

    def test_openssl_cli_is_installed_and_verified_before_the_build(self):
        install = self.workflow.index(
            "dnf -y --setopt=install_weak_deps=False install \\\n"
        )
        checkout = self.workflow.index("Check out the exact candidate")
        bootstrap = self.workflow[install:checkout]
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
