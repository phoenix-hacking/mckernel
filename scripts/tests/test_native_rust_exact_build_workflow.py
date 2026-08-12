#!/usr/bin/env python3

from __future__ import print_function

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github/workflows/native-rust-host-modules-exact-build.yml"
PATCH = REPO_ROOT / "host-kernel/kbuild/patches/0002-rust-bindings-expose-module-parameters.patch"
CONFIG = REPO_ROOT / "host-kernel/rocky/configs/native-rust-evidence.config"


class NativeRustExactBuildWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

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
        self.assertIn("-j2 bzImage modules", self.workflow)
        self.assertIn(
            'cp "$NATIVE_BUILD_DIR/arch/x86/boot/bzImage" "$EVIDENCE_DIR/bzImage"',
            self.workflow,
        )
        self.assertIn('> "$EVIDENCE_DIR/kernel.release"', self.workflow)
        self.assertIn("include-hidden-files: true", self.workflow)

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
        self.assertIn("#include <linux/moduleparam.h>", patch)
        self.assertNotIn("mckernel", patch.lower())

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
        project = self.workflow.index(
            "0001-drivers-misc-add-mckernel-rust-host-modules.patch",
            clang_warning_policy,
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
        self.assertLess(clang_warning_policy, project)

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
        self.assertIn('printf \'%s\\n\' "$status"', self.workflow)
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


if __name__ == "__main__":
    unittest.main()
