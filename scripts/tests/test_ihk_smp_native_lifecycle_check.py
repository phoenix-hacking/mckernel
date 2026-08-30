import contextlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import ihk_smp_native_lifecycle_check as lifecycle


class IhkSmpNativeLifecycleCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ihk-smp-native-lifecycle-")
        self.repo = Path(self.temporary.name) / "repo"
        self.contract = json.loads(
            (REPO_ROOT / lifecycle.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        relative_paths = {
            lifecycle.DEFAULT_CONTRACT.as_posix(),
            self.contract["production_source"],
            self.contract["provider_source"],
            self.contract["kconfig"]["path"],
            self.contract["kbuild"]["path"],
            self.contract["stage_manifest"],
            self.contract["reference_inventory"],
        }
        relative_paths.update(
            parameter["legacy_source"] for parameter in self.contract["parameters"]
        )
        relative_paths.update(
            module["path"] for module in self.contract["crate_modules"]
        )
        relative_paths.update(
            (
                self.contract["resource_foundation"]["fixture"]["positive_path"],
                self.contract["resource_foundation"]["fixture"]["negative_path"],
                self.contract["control_device_shell"]["noncopy_fixture"]["path"],
            )
        )
        for relative in relative_paths:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, target)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def mutate_text(self, relative: str, old: str, new: str) -> None:
        path = self.repo / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def write_json(self, relative: str, value: object) -> None:
        (self.repo / relative).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def test_repository_contract_is_verified_without_runtime_overclaim(self) -> None:
        summary = lifecycle.validate_repository(REPO_ROOT)
        self.assertEqual("SMP-001", summary["gate_id"])
        self.assertEqual("ihk_smp_x86_64", summary["module"])
        self.assertEqual(6, summary["parameters"])
        self.assertEqual(["ihk"], summary["dependencies"])
        self.assertEqual(["MCKERNEL_IHK_V1"], summary["import_namespaces"])
        self.assertFalse(summary["artifact_validated"])
        self.assertFalse(summary["built_symbol_reference_validated"])
        self.assertFalse(summary["rocky_build_load_validated"])
        self.assertTrue(summary["source_symbol_reference_present"])
        self.assertFalse(summary["runtime_symbol_reference_proven"])
        self.assertEqual(
            [
                "ihk_provider_lifecycle_v1",
                "ihk_smp_provider_attach_v2",
                "ihk_smp_provider_detach_v2",
                "ihk_smp_provider_open_v1",
                "ihk_smp_provider_close_v1",
            ],
            summary["provider_symbols"],
        )
        self.assertEqual("TODO", summary["provider_lease_gate_status"])
        self.assertFalse(summary["provider_lease_credit_eligible"])
        self.assertFalse(summary["provider_lease_runtime_proven"])
        self.assertFalse(summary["resource_foundation_credit_eligible"])
        self.assertFalse(summary["resource_foundation_linux_reachable"])
        self.assertEqual(29, summary["resource_foundation_tests"])
        self.assertEqual("mcd0", summary["control_device_name"])
        self.assertTrue(summary["control_device_source_reachable"])
        self.assertEqual("TODO", summary["control_device_gate_status"])
        self.assertFalse(summary["control_device_credit_eligible"])
        self.assertFalse(summary["control_device_runtime_proven"])

    def test_resource_policy_source_digest_and_module_edge_are_fail_closed(self) -> None:
        resource = self.contract["crate_modules"][0]
        self.mutate_text(resource["path"], "SMP_MAX_CPUS: usize = 512", "SMP_MAX_CPUS: usize = 511")
        with self.assertRaisesRegex(lifecycle.ValidationError, "resource policy digest"):
            lifecycle.validate_repository(self.repo)

        shutil.copyfile(REPO_ROOT / resource["path"], self.repo / resource["path"])
        self.mutate_text(
            self.contract["production_source"],
            "#[allow(dead_code)]\nmod smp_resource;",
            "#[allow(dead_code)]\nmod wrong_resource;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "resource-policy edge"):
            lifecycle.validate_repository(self.repo)

    def test_resource_fixture_drift_and_readiness_overclaim_are_rejected(self) -> None:
        fixture = self.contract["resource_foundation"]["fixture"]
        self.mutate_text(fixture["positive_path"], "no_std", "no_stx")
        with self.assertRaisesRegex(lifecycle.ValidationError, "positive fixture digest"):
            lifecycle.validate_repository(self.repo)

        shutil.copyfile(
            REPO_ROOT / fixture["positive_path"], self.repo / fixture["positive_path"]
        )
        self.contract["resource_foundation"]["credit_eligible"] = True
        self.write_json(lifecycle.DEFAULT_CONTRACT.as_posix(), self.contract)
        with self.assertRaisesRegex(lifecycle.ValidationError, "overclaims readiness"):
            lifecycle.validate_repository(self.repo)

    def test_stage_manifest_cannot_omit_smp_resource_policy(self) -> None:
        manifest = json.loads(
            (self.repo / self.contract["stage_manifest"]).read_text(encoding="utf-8")
        )
        manifest["inputs"] = [
            item for item in manifest["inputs"]
            if item.get("destination") != "smp_resource.rs"
        ]
        self.write_json(self.contract["stage_manifest"], manifest)
        with self.assertRaisesRegex(lifecycle.ValidationError, "SMP resource policy"):
            lifecycle.validate_repository(self.repo)

    def test_cli_deliberately_does_not_report_gate_pass(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = lifecycle.main(["--repo", str(REPO_ROOT)])
        self.assertEqual(0, result)
        rendered = output.getvalue()
        self.assertIn("SOURCE-CONTRACT-VERIFIED", rendered)
        self.assertIn("provider_lease=TODO", rendered)
        self.assertIn("provider_lease_runtime=NOT_PROVEN", rendered)
        self.assertIn("control_device=mcd0", rendered)
        self.assertIn("control_device_gate=TODO", rendered)
        self.assertIn("control_device_runtime=NOT_PROVEN", rendered)
        self.assertIn("tracker_credit=FORBIDDEN", rendered)
        self.assertIn("rocky_build_load=NOT_EVALUATED", rendered)
        self.assertNotIn("PASS", rendered)

    def test_each_parameter_name_binding_is_fail_closed(self) -> None:
        source_path = self.repo / self.contract["production_source"]
        original = source_path.read_text(encoding="utf-8")
        for parameter in self.contract["parameters"]:
            with self.subTest(parameter=parameter["name"]):
                old = f'loadable_name_bytes: b"{parameter["name"]}\\0",'
                mutated = original.replace(
                    old, 'loadable_name_bytes: b"wrong_name\\0",', 1
                )
                self.assertNotEqual(original, mutated)
                source_path.write_text(mutated, encoding="utf-8")
                with self.assertRaisesRegex(lifecycle.ValidationError, "descriptor"):
                    lifecycle.validate_repository(self.repo)
        source_path.write_text(original, encoding="utf-8")

    def test_each_builtin_parameter_name_binding_is_fail_closed(self) -> None:
        source_path = self.repo / self.contract["production_source"]
        original = source_path.read_text(encoding="utf-8")
        module = self.contract["module"]["name"]
        for parameter in self.contract["parameters"]:
            with self.subTest(parameter=parameter["name"]):
                old = f'builtin_name_bytes: b"{module}.{parameter["name"]}\\0",'
                mutated = original.replace(
                    old, 'builtin_name_bytes: b"wrong_module.wrong_name\\0",', 1
                )
                self.assertNotEqual(original, mutated)
                source_path.write_text(mutated, encoding="utf-8")
                with self.assertRaisesRegex(lifecycle.ValidationError, "descriptor"):
                    lifecycle.validate_repository(self.repo)
        source_path.write_text(original, encoding="utf-8")

    def test_parameter_name_mode_selection_is_fail_closed(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "const PARAMETER_NAME: &[u8] = $loadable_name_bytes;",
            "const PARAMETER_NAME: &[u8] = $builtin_name_bytes;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "descriptor names by MODULE"):
            lifecycle.validate_repository(self.repo)

    def test_each_parameter_type_and_ops_binding_is_fail_closed(self) -> None:
        source_path = self.repo / self.contract["production_source"]
        original = source_path.read_text(encoding="utf-8")
        for parameter in self.contract["parameters"]:
            with self.subTest(parameter=parameter["name"]):
                old_type = parameter["rust_type"]
                new_type = (
                    "core::ffi::c_ulong"
                    if old_type == "core::ffi::c_uint"
                    else "core::ffi::c_uint"
                )
                marker = f"name: {parameter['name']},"
                start = original.index(marker)
                end = original.index("\n);", start)
                block = original[start:end]
                mutated_block = block.replace(old_type, new_type, 1)
                mutated = original[:start] + mutated_block + original[end:]
                source_path.write_text(mutated, encoding="utf-8")
                with self.assertRaisesRegex(lifecycle.ValidationError, "descriptor"):
                    lifecycle.validate_repository(self.repo)
        source_path.write_text(original, encoding="utf-8")

    def test_each_parameter_default_is_fail_closed(self) -> None:
        source_path = self.repo / self.contract["production_source"]
        original = source_path.read_text(encoding="utf-8")
        for parameter in self.contract["parameters"]:
            with self.subTest(parameter=parameter["name"]):
                marker = f"name: {parameter['name']},"
                start = original.index(marker)
                end = original.index("\n);", start)
                block = original[start:end]
                mutated_block = block.replace("default: 0,", "default: 1,", 1)
                mutated = original[:start] + mutated_block + original[end:]
                source_path.write_text(mutated, encoding="utf-8")
                with self.assertRaisesRegex(lifecycle.ValidationError, "descriptor"):
                    lifecycle.validate_repository(self.repo)
        source_path.write_text(original, encoding="utf-8")

    def test_each_parameter_permission_is_fail_closed(self) -> None:
        source_path = self.repo / self.contract["production_source"]
        original = source_path.read_text(encoding="utf-8")
        for parameter in self.contract["parameters"]:
            with self.subTest(parameter=parameter["name"]):
                marker = f"name: {parameter['name']},"
                start = original.index(marker)
                end = original.index("\n);", start)
                block = original[start:end]
                mutated_block = block.replace("permission: 0o644,", "permission: 0o600,", 1)
                mutated = original[:start] + mutated_block + original[end:]
                source_path.write_text(mutated, encoding="utf-8")
                with self.assertRaisesRegex(lifecycle.ValidationError, "descriptor"):
                    lifecycle.validate_repository(self.repo)
        source_path.write_text(original, encoding="utf-8")

    def test_parameter_description_modinfo_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "parm=ihk_cores:IHK reserved CPU cores\\0",
            "parm=ihk_cores:wrong description\\0",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "modinfo"):
            lifecycle.validate_repository(self.repo)

    def test_parameter_descriptor_section_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            '#[link_section = "__param"]',
            '#[link_section = "wrong_param"]',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "ABI"):
            lifecycle.validate_repository(self.repo)

    def test_provider_symbol_import_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            '#[link_name = "ihk_provider_lifecycle_v1"]',
            '#[link_name = "wrong_provider_symbol"]',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "provider-symbol import"):
            lifecycle.validate_repository(self.repo)

    def test_provider_lease_import_symbols_and_signatures_are_fail_closed(self) -> None:
        source_path = self.repo / self.contract["production_source"]
        original = source_path.read_text(encoding="utf-8")
        cases = (
            (
                '#[link_name = "ihk_smp_provider_attach_v2"]',
                '#[link_name = "wrong_attach"]',
            ),
            (
                "        flags: u32,",
                "        flags: u64,",
            ),
            (
                '#[link_name = "ihk_smp_provider_detach_v2"]',
                '#[link_name = "wrong_detach"]',
            ),
            (
                "fn ihk_smp_provider_detach_v2(token: i64, exit: Option<IhkSmpProviderExitV2>);",
                "fn ihk_smp_provider_detach_v2(token: u64, exit: Option<IhkSmpProviderExitV2>);",
            ),
        )
        for old, new in cases:
            with self.subTest(mutation=old):
                source_path.write_text(original.replace(old, new, 1), encoding="utf-8")
                with self.assertRaisesRegex(
                    lifecycle.ValidationError, "five-symbol provider-symbol import"
                ):
                    lifecycle._validate_rust_source(
                        source_path.read_text(encoding="utf-8"), self.contract
                    )
        source_path.write_text(original, encoding="utf-8")

    def test_provider_lease_errno_mapping_is_exact_and_fail_closed(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        cases = (
            ("_ => -117,", "_ => -22,"),
            ("status as i32", "-117"),
            ("kernel::error::to_result(errno)", "kernel::error::to_result(-117)"),
            ("Ok(()) => EIO,", "Ok(()) => EINVAL,"),
        )
        for old, new in cases:
            with self.subTest(mutation=old), self.assertRaisesRegex(
                lifecycle.ValidationError, "errno adapter"
            ):
                lifecycle._validate_rust_source(source.replace(old, new, 1), self.contract)
        status_line = "-2 | -12 | -16 | -22 | -75 | -116 | -117"
        for status in self.contract["provider_lease"]["errno_statuses"]:
            with self.subTest(missing_status=status), self.assertRaisesRegex(
                lifecycle.ValidationError, "errno adapter"
            ):
                lifecycle._validate_rust_source(
                    source.replace(status_line, status_line.replace(str(status), "-999", 1), 1),
                    self.contract,
                )

    def test_provider_lease_raii_owner_and_teardown_order_are_fail_closed(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        cases = (
            (
                '#[must_use = "the provider lease must remain owned until SMP module teardown"]',
                '#[derive(Copy, Clone)]\n#[must_use = "the provider lease must remain owned until SMP module teardown"]',
                "Copy or Clone",
            ),
            (
                "provider_lease: Option<ProviderLease>,",
                "provider_lease: ProviderLease,",
                "pinned mcd0/provider owners",
            ),
            (
                "provider_lease: Some(provider_lease),",
                "provider_lease: None,",
                "retain the provider lease",
            ),
            (
                "drop(self.provider_lease.take());",
                "let _ = self.provider_lease.take();",
                "registration lifecycle differs",
            ),
        )
        for old, new, error in cases:
            with self.subTest(mutation=old), self.assertRaisesRegex(
                lifecycle.ValidationError, error
            ):
                lifecycle._validate_rust_source(source.replace(old, new, 1), self.contract)

        unload_log = f'"{self.contract["lifecycle_logs"]["unload"]}\\n"'
        detach = "drop(self.provider_lease.take());"
        detach_start = source.index(detach)
        detach_end = detach_start + len(detach)
        without_detach = source[:detach_start] + source[detach_end:]
        unload_literal_start = without_detach.index(unload_log)
        unload_end = without_detach.index("        );", unload_literal_start) + len(
            "        );"
        )
        reordered = (
            without_detach[:unload_end]
            + "\n        "
            + detach
            + without_detach[unload_end:]
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "before provider detach"):
            lifecycle._validate_rust_source(reordered, self.contract)

    def test_commented_provider_detach_cannot_authorize_a_noop_drop(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        old = '''        // SAFETY: This non-Copy owner calls the matching provider function\n        // exactly once with the positive token returned by attach and the\n        // retained exit identity.  The provider fails stop rather than\n        // returning with a live entry or callback.\n        unsafe {\n            ihk_smp_provider_detach_v2(self.token, Some(ihk_smp_provider_exit_v2))\n        };'''
        new = '''        /*\n+        // SAFETY: This non-Copy owner calls the matching provider function\n+        // exactly once with the positive token returned by attach and the\n+        // retained exit identity.  The provider fails stop rather than\n+        // returning with a live entry or callback.\n+        unsafe {\n+            ihk_smp_provider_detach_v2(self.token, Some(ihk_smp_provider_exit_v2))\n+        };\n+        */'''
        self.assertIn(old, source)
        with self.assertRaisesRegex(
            lifecycle.ValidationError, "ownership path|call each imported"
        ):
            lifecycle._validate_rust_source(
                source.replace(old, new, 1), self.contract
            )

    def test_provider_lease_raw_token_diagnostics_are_rejected(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        mutated = source.replace(
            'unsafe {\n            ihk_smp_provider_detach_v2(self.token, Some(ihk_smp_provider_exit_v2))\n        };',
            'pr_err!("provider_lease=raw token={}\\n", self.token);\n'
            '        unsafe {\n            ihk_smp_provider_detach_v2(self.token, Some(ihk_smp_provider_exit_v2))\n        };',
            1,
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "raw lease scalar"):
            lifecycle._validate_rust_source(mutated, self.contract)

    def test_provider_lease_contract_cannot_promote_credit_or_runtime(self) -> None:
        cases = (
            ("credit_eligible", True),
            ("gate_status", "PASS"),
            ("rocky_runtime_validated", True),
            ("runtime_behavior_proven", True),
            ("tracker_credit", True),
            ("callback_payload_reachable", True),
            ("device_node_reachable", True),
            ("raw_token_logged", True),
        )
        for field, value in cases:
            with self.subTest(field=field):
                contract = json.loads(json.dumps(self.contract))
                contract["provider_lease"][field] = value
                with self.assertRaisesRegex(
                    lifecycle.ValidationError, "provider lease differs or overclaims"
                ):
                    lifecycle._validate_contract(contract)

    def test_control_device_contract_is_bounded_and_noncrediting(self) -> None:
        cases = (
            ("credit_eligible", True),
            ("gate_status", "PASS"),
            ("rocky_runtime_validated", True),
            ("runtime_behavior_proven", True),
            ("tracker_credit", True),
            ("provider_operation_callbacks_reachable", True),
            ("provider_attach_before_registration", False),
            ("raw_data_pointer", True),
            ("registration_failure_releases_provider_lease", False),
            ("usercopy_reachable", True),
            ("valid_ioctl_commands", [1]),
        )
        for field, value in cases:
            with self.subTest(field=field):
                contract = json.loads(json.dumps(self.contract))
                contract["control_device_shell"][field] = value
                with self.assertRaisesRegex(
                    lifecycle.ValidationError, "control-device shell differs or overclaims"
                ):
                    lifecycle._validate_contract(contract)
        for gate in ("IHK-003", "IHK-004", "RS-006"):
            with self.subTest(gate=gate):
                contract = json.loads(json.dumps(self.contract))
                contract["control_device_shell"]["gate_claims"][gate] = True
                with self.assertRaisesRegex(
                    lifecycle.ValidationError, "control-device shell differs or overclaims"
                ):
                    lifecycle._validate_contract(contract)
        for field, value in (
            ("concurrent_shared_opens", False),
            ("duplicate_close_detectable_while_other_references_exist", True),
            ("same_generation_token_may_repeat", False),
            ("provider_policy", "single-outstanding-receipt"),
            ("trusted_noncopy_owner_balance_required", False),
        ):
            with self.subTest(open_receipt=field):
                contract = json.loads(json.dumps(self.contract))
                contract["control_device_shell"]["open_receipt"][field] = value
                with self.assertRaisesRegex(
                    lifecycle.ValidationError, "control-device shell differs or overclaims"
                ):
                    lifecycle._validate_contract(contract)

    def test_control_device_scalar_imports_are_exact(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        cases = (
            (
                '#[link_name = "ihk_smp_provider_open_v1"]',
                '#[link_name = "wrong_open"]',
            ),
            (
                "fn ihk_smp_provider_open_v1(minor: u32) -> i64;",
                "fn ihk_smp_provider_open_v1(minor: u64) -> i64;",
            ),
            (
                '#[link_name = "ihk_smp_provider_close_v1"]',
                '#[link_name = "wrong_close"]',
            ),
            (
                "fn ihk_smp_provider_close_v1(receipt: i64);",
                "fn ihk_smp_provider_close_v1(receipt: u64);",
            ),
        )
        for old, new in cases:
            with self.subTest(mutation=old), self.assertRaisesRegex(
                lifecycle.ValidationError, "five-symbol provider-symbol import"
            ):
                lifecycle._validate_rust_source(source.replace(old, new, 1), self.contract)

    def test_control_device_receipt_and_fops_owner_are_fail_closed(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        cases = (
            (
                '#[must_use = "the provider-open receipt must remain owned until file release"]',
                '#[derive(Copy, Clone)]\n#[must_use = "the provider-open receipt must remain owned until file release"]',
                "ProviderOpenLease may not implement Copy or Clone",
            ),
            (
                "const MODULE: &'static ThisModule = &THIS_MODULE;",
                "const MODULE: &'static ThisModule = &OTHER_MODULE;",
                "open-receipt ownership path",
            ),
            (
                'name: c_str!("mcd0"),',
                'name: c_str!("mcd1"),',
                "pinned literal mcd0 registration",
            ),
            (
                "Box::new(ProviderOpenLease::acquire()?, GFP_KERNEL).map_err(|_| ENOMEM)",
                "Box::new(ProviderOpenLease::acquire()?, GFP_KERNEL).map_err(|_| EIO)",
                "open-receipt ownership path",
            ),
            (
                "Box::new(ProviderOpenLease::acquire()?, GFP_KERNEL).map_err(|_| ENOMEM)",
                "Box::new(ProviderOpenLease::acquire()?, GFP_ATOMIC).map_err(|_| ENOMEM)",
                "open-receipt ownership path",
            ),
        )
        for old, new, error in cases:
            with self.subTest(mutation=old), self.assertRaisesRegex(
                lifecycle.ValidationError, error
            ):
                lifecycle._validate_rust_source(source.replace(old, new, 1), self.contract)

        close = "unsafe { ihk_smp_provider_close_v1(self.receipt) };"
        with self.assertRaisesRegex(
            lifecycle.ValidationError, "open-receipt ownership path|call each imported"
        ):
            lifecycle._validate_rust_source(
                source.replace(close, "/* {0} */".format(close), 1), self.contract
            )
        with self.assertRaisesRegex(lifecycle.ValidationError, "raw lease scalar"):
            lifecycle._validate_rust_source(
                source.replace(
                    close,
                    'pr_err!("provider_open receipt={}\\n", self.receipt);\n        '
                    + close,
                    1,
                ),
                self.contract,
            )

    def test_control_device_ioctl_surface_is_uniformly_rejecting(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        first = source.index("        Err(EINVAL)", source.index("fn ioctl("))
        with self.assertRaisesRegex(lifecycle.ValidationError, "rejecting native ioctl"):
            lifecycle._validate_rust_source(
                source[:first] + source[first:].replace("Err(EINVAL)", "Ok(0)", 1),
                self.contract,
            )
        compat = source.index("        Err(EINVAL)", source.index("fn compat_ioctl("))
        with self.assertRaisesRegex(lifecycle.ValidationError, "explicit compat ioctl"):
            lifecycle._validate_rust_source(
                source[:compat] + source[compat:].replace("Err(EINVAL)", "Ok(0)", 1),
                self.contract,
            )
        with self.assertRaisesRegex(lifecycle.ValidationError, "unsupported file operation"):
            lifecycle._validate_rust_source(
                source + "\nfn read() -> Result<usize> { Ok(0) }\n", self.contract
            )
        with self.assertRaisesRegex(lifecycle.ValidationError, "forbidden usercopy"):
            lifecycle._validate_rust_source(
                source + "\nfn hidden_usercopy() { let _ = UserSlice; }\n",
                self.contract,
            )
        with self.assertRaisesRegex(lifecycle.ValidationError, "implicit compat"):
            lifecycle._validate_rust_source(
                source + "\nfn hidden_fallback() { let _ = compat_ptr_ioctl; }\n",
                self.contract,
            )
        custom_release = source.replace(
            "    fn ioctl(\n",
            "    fn release(device: Box<ProviderOpenLease>) {\n"
            "        core::mem::forget(device);\n"
            "    }\n\n"
            "    fn ioctl(\n",
            1,
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "default release"):
            lifecycle._validate_rust_source(custom_release, self.contract)
        forgotten = source.replace(
            "    fn acquire() -> Result<Self> {\n",
            "    fn acquire() -> Result<Self> {\n"
            "        core::mem::forget(ProviderOpenLease { receipt: 1 });\n",
            1,
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "forgets an owned receipt"):
            lifecycle._validate_rust_source(forgotten, self.contract)
        raw_pointer = source.replace(
            "struct IhkSmpControlDevice;",
            "fn hidden_raw_pointer(_pointer: *mut core::ffi::c_void) {}\n\n"
            "struct IhkSmpControlDevice;",
            1,
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "raw pointer"):
            lifecycle._validate_rust_source(raw_pointer, self.contract)

    def test_control_device_registration_rollback_and_teardown_order_are_exact(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        attach_start = source.index("        let provider_lease = ProviderLease::attach()?;")
        attach_end = attach_start + len(
            "        let provider_lease = ProviderLease::attach()?;\n"
        )
        register_start = source.index("        let control_device = Box::pin_init(")
        register_end = source.index("        pr_info!(", register_start)
        registration = source[register_start:register_end]
        attach = source[attach_start:attach_end]
        reordered = (
            source[:attach_start]
            + registration
            + attach
            + source[register_end:]
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "attach, register mcd0"):
            lifecycle._validate_rust_source(reordered, self.contract)

        with self.assertRaisesRegex(
            lifecycle.ValidationError, "pinned literal mcd0 registration"
        ):
            lifecycle._validate_rust_source(
                source.replace(
                    "            GFP_KERNEL,\n        )?;",
                    "            GFP_ATOMIC,\n        )?;",
                    1,
                ),
                self.contract,
            )

        registration_tail = "            GFP_KERNEL,\n        )?;"
        fallible_after_registration = source.replace(
            registration_tail,
            registration_tail
            + "\n        let _late = Box::new(0_u8, GFP_KERNEL).map_err(|_| ENOMEM)?;",
            1,
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "final fallible"):
            lifecycle._validate_rust_source(
                fallible_after_registration, self.contract
            )

        ordered_drop = (
            "drop(self.control_device.take());\n"
            "        drop(self.provider_lease.take());"
        )
        reversed_drop = (
            "drop(self.provider_lease.take());\n"
            "        drop(self.control_device.take());"
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "deregister mcd0"):
            lifecycle._validate_rust_source(
                source.replace(ordered_drop, reversed_drop, 1), self.contract
            )

    def test_control_device_noncopy_fixture_is_bound_and_compile_fails(self) -> None:
        fixture = self.contract["control_device_shell"]["noncopy_fixture"]
        self.assertEqual(
            self.repo / fixture["path"],
            lifecycle._validate_control_device_fixture(self.repo, self.contract),
        )
        self.mutate_text(fixture["path"], "_second_owner", "_second_ownez")
        with self.assertRaisesRegex(lifecycle.ValidationError, "fixture identity differs"):
            lifecycle._validate_control_device_fixture(self.repo, self.contract)

        rustc = shutil.which("rustc")
        if rustc is None:
            self.skipTest("rustc is unavailable for the compile-fail ownership fixture")
        with tempfile.TemporaryDirectory(prefix="ihk-smp-open-noncopy-rustc-") as temporary:
            result = subprocess.run(
                [
                    rustc,
                    "--edition=2021",
                    str(REPO_ROOT / fixture["path"]),
                    "--crate-name",
                    "ihk_smp_provider_open_lease_compile_fail",
                    "--out-dir",
                    temporary,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("use of moved value", result.stderr)

    def test_manual_dependency_modinfo_is_rejected(self) -> None:
        source = self.repo / self.contract["production_source"]
        with source.open("a", encoding="utf-8") as stream:
            stream.write('static WRONG: &[u8] = b"depends=ihk\\0";\n')
        with self.assertRaisesRegex(lifecycle.ValidationError, "let modpost derive"):
            lifecycle.validate_repository(self.repo)

    def test_provider_export_namespace_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["provider_source"],
            'namespace: *b"MCKERNEL_IHK_V1\\0"',
            'namespace: *b"UNVERSIONED_____\\0"',
        )
        with self.assertRaisesRegex(
            lifecycle.ValidationError, "provider anchor|versioned namespace"
        ):
            lifecycle.validate_repository(self.repo)

    def test_provider_lease_exports_are_exact_and_namespaced(self) -> None:
        provider = (self.repo / self.contract["provider_source"]).read_text(
            encoding="utf-8"
        )
        cases = (
            (
                '#[export_name = "ihk_smp_provider_attach_v1"]',
                '#[export_name = "wrong_attach"]',
                "required fragment",
            ),
            (
                'pub extern "C" fn ihk_smp_provider_attach_v1() -> i64',
                'pub extern "C" fn ihk_smp_provider_attach_v1() -> i32',
                "required fragment",
            ),
            (
                "symbol: ihk_smp_provider_attach_v1 as *const () as *const u8",
                "symbol: core::ptr::null()",
                "required fragment",
            ),
            (
                '#[export_name = "ihk_smp_provider_detach_v1"]',
                '#[export_name = "wrong_detach"]',
                "required fragment",
            ),
            (
                'pub extern "C" fn ihk_smp_provider_detach_v1(token: i64)',
                'pub extern "C" fn ihk_smp_provider_detach_v1(token: u64)',
                "required fragment",
            ),
            (
                "symbol: ihk_smp_provider_detach_v1 as *const () as *const u8",
                "symbol: core::ptr::null()",
                "required fragment",
            ),
        )
        for old, new, error in cases:
            with self.subTest(mutation=old), self.assertRaisesRegex(
                lifecycle.ValidationError, error
            ):
                lifecycle._validate_provider_source(
                    provider.replace(old, new, 1), self.contract
                )

    def test_provider_source_rejects_raw_token_logging(self) -> None:
        provider = (self.repo / self.contract["provider_source"]).read_text(
            encoding="utf-8"
        )
        mutated = provider.replace(
            'pr_info!("provider_lease=attach status=live minor=0\\n");',
            'pr_info!("provider_lease=attach token={} status=live minor=0\\n", token);',
            1,
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "raw lease scalar"):
            lifecycle._validate_provider_source(mutated, self.contract)

    def test_provider_source_rejects_additional_ffi_boundaries(self) -> None:
        provider = (self.repo / self.contract["provider_source"]).read_text(
            encoding="utf-8"
        )
        cases = (
            'extern "C" { fn hidden_provider(); }',
            'pub extern "C" fn hidden_provider() {}',
            'extern crate hidden_dependency;',
        )
        for extra in cases:
            with self.subTest(extra=extra), self.assertRaisesRegex(
                lifecycle.ValidationError, "extern boundary"
            ):
                lifecycle._validate_provider_source(provider + "\n" + extra, self.contract)

    def test_provider_export_record_field_order_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["provider_source"],
            "    namespace: [u8; 16],\n    padding: [u8; 4],",
            "    padding: [u8; 4],\n    namespace: [u8; 16],",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "export_symbol record layout"):
            lifecycle.validate_repository(self.repo)

    def test_import_namespace_modinfo_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            "import_ns=MCKERNEL_IHK_V1\\0",
            "import_ns=UNVERSIONED\\0",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "modinfo"):
            lifecycle.validate_repository(self.repo)

    def test_extra_module_metadata_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"],
            '    name: "ihk_smp_x86_64",\n',
            '    name: "ihk_smp_x86_64",\n    author: "not legacy",\n',
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "metadata"):
            lifecycle.validate_repository(self.repo)

    def test_lifecycle_log_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["production_source"], "lifecycle=load", "lifecycle=start"
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "load lifecycle"):
            lifecycle.validate_repository(self.repo)

    def test_unreviewed_ffi_escape_hatch_is_rejected(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        cases = (
            'extern   "C" { fn legacy_smp_init(); }',
            'extern /* gap */ "system" { fn legacy_smp_init(); }',
            "unsafe extern\n{ fn legacy_smp_init(); }",
            'pub extern "C" fn legacy_smp_init() {}',
            "extern crate hidden_dependency;",
        )
        for extra in cases:
            with self.subTest(extra=extra), self.assertRaisesRegex(
                lifecycle.ValidationError, "extern boundary"
            ):
                lifecycle._validate_rust_source(source + "\n" + extra, self.contract)

    def test_unreviewed_macro_escape_hatch_rejects_spelling_variants(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        cases = (
            ("include", 'include \n ! \n ("hidden.rs");'),
            ("include_bytes", 'include_bytes /* gap */ ! ["payload.bin"];'),
            ("asm", 'core::arch::asm\t!\n("nop");'),
            ("global_asm", 'global_asm /* gap */ ! {".byte 0"}'),
            (
                "global_asm",
                'use core::arch::global_asm as emit; emit!(".byte 0");',
            ),
            (
                "include",
                "macro_rules! forward { ($macro:ident) => { $macro!(\"hidden.rs\") } }\n"
                "forward!(include);",
            ),
        )
        for name, extra in cases:
            with self.subTest(macro=name), self.assertRaisesRegex(
                lifecycle.ValidationError, "macro boundary: {0}!".format(name)
            ):
                lifecycle._validate_rust_source(source + "\n" + extra, self.contract)

    def test_escape_hatch_text_in_comments_and_strings_is_inert(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        inert = r'''
// include ! ("comment.rs"); extern "C" { fn comment(); }
/* outer global_asm ! {"comment"}
   /* nested include_bytes ! ("comment.bin") */
   extern "system" { fn comment(); }
*/
const INERT_ORDINARY: &str = "asm ! (\"nop\"); extern \"C\" { fn text(); }";
const INERT_RAW: &str = r###"include ! ("raw.rs"); global_asm ! {"raw"}"###;
const INERT_RAW_BYTES: &[u8] = br##"include_bytes ! ("raw.bin")"##;
fn inert_lifetimes<'a>(value: &'a str) -> &'a str { value }
fn inert_raw_identifier() { let r#extern = b'x'; let _ = r#extern; }
fn áextern() {}
macro_rules! áinclude { () => {} }
'''
        lifecycle._validate_rust_source(source + inert, self.contract)

    def test_exact_provider_extern_rejects_outer_attributes_and_modifiers(self) -> None:
        source = (self.repo / self.contract["production_source"]).read_text(
            encoding="utf-8"
        )
        provider_import = lifecycle._provider_import(self.contract)
        self.assertEqual(1, source.count(provider_import))
        for prefix in (
            '#[link(name = "unreviewed")]\n',
            "#[cfg(any())]\n",
            "pub ",
            "unsafe ",
        ):
            with self.subTest(prefix=prefix), self.assertRaisesRegex(
                lifecycle.ValidationError, "exact audited extern boundary"
            ):
                lifecycle._validate_rust_source(
                    source.replace(provider_import, prefix + provider_import, 1),
                    self.contract,
                )

    def test_kconfig_provider_edge_removal_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["kconfig"]["path"],
            "\tdepends on MCKERNEL_IHK_RUST\n",
            "",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kconfig policy"):
            lifecycle.validate_repository(self.repo)

    def test_shared_kconfig_menu_modules_dependency_is_required(self) -> None:
        self.mutate_text(
            self.contract["kconfig"]["path"],
            "\tdepends on MODULES && m\n",
            "",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kconfig policy"):
            lifecycle.validate_repository(self.repo)

    def test_shared_kconfig_hidden_edge_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["kconfig"]["path"],
            "\nconfig MCKERNEL_IHK_RUST\n",
            "\nchoice\n\nconfig MCKERNEL_IHK_RUST\n",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kconfig policy"):
            lifecycle.validate_repository(self.repo)

    def test_kbuild_output_name_drift_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["kbuild"]["path"],
            "ihk-smp-x86_64.o",
            "ihk_smp_x86_64.o",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kbuild policy"):
            lifecycle.validate_repository(self.repo)

    def test_shared_kbuild_continued_comment_is_rejected(self) -> None:
        self.mutate_text(
            self.contract["kbuild"]["path"],
            "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o\n",
            "# suppress provider mapping \\\n"
            "obj-$(CONFIG_MCKERNEL_IHK_RUST) += ihk.o\n",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "shared native Rust Kbuild policy"):
            lifecycle.validate_repository(self.repo)

    def test_stage_manifest_provider_dependency_drift_is_rejected(self) -> None:
        relative = self.contract["stage_manifest"]
        manifest = json.loads((self.repo / relative).read_text(encoding="utf-8"))
        module = next(item for item in manifest["modules"] if item["crate"] == "ihk_smp_x86_64")
        module["dependencies"] = []
        self.write_json(relative, manifest)
        with self.assertRaisesRegex(lifecycle.ValidationError, "provider dependency"):
            lifecycle.validate_repository(self.repo)

    def test_stage_manifest_import_namespace_drift_is_rejected(self) -> None:
        relative = self.contract["stage_manifest"]
        manifest = json.loads((self.repo / relative).read_text(encoding="utf-8"))
        module = next(item for item in manifest["modules"] if item["crate"] == "ihk_smp_x86_64")
        module["required_import_namespaces"] = []
        self.write_json(relative, manifest)
        with self.assertRaisesRegex(lifecycle.ValidationError, "import namespace"):
            lifecycle.validate_repository(self.repo)

    def test_stale_source_digest_is_rejected(self) -> None:
        relative = self.contract["stage_manifest"]
        manifest = json.loads((self.repo / relative).read_text(encoding="utf-8"))
        module = next(item for item in manifest["modules"] if item["crate"] == "ihk_smp_x86_64")
        module["source"]["sha256"] = "0" * 64
        self.write_json(relative, manifest)
        with self.assertRaisesRegex(lifecycle.ValidationError, "digest is stale"):
            lifecycle.validate_repository(self.repo)

    def test_frozen_source_default_drift_is_rejected(self) -> None:
        parameter = next(item for item in self.contract["parameters"] if item["name"] == "ihk_mem")
        self.mutate_text(
            parameter["legacy_source"],
            "static unsigned long ihk_mem = 0;",
            "static unsigned long ihk_mem = 1;",
        )
        with self.assertRaisesRegex(lifecycle.ValidationError, "does not prove ihk_mem"):
            lifecycle.validate_repository(self.repo)

    def test_reference_binary_dependency_drift_is_rejected(self) -> None:
        relative = self.contract["reference_inventory"]
        inventory = json.loads((self.repo / relative).read_text(encoding="utf-8"))
        inventory["binary_capture"]["modules"]["ihk_smp_x86_64"]["modinfo"]["values"][
            "depends"
        ] = []
        self.write_json(relative, inventory)
        with self.assertRaisesRegex(lifecycle.ValidationError, "provider dependency"):
            lifecycle.validate_repository(self.repo)

    def test_built_artifact_metadata_and_diagnostics_are_checked(self) -> None:
        module = self.repo / "ihk-smp-x86_64.ko"
        module.write_bytes(b"lifecycle=load parameters=\0lifecycle=unload parameters=\0")
        summary = lifecycle.validate_repository(REPO_ROOT)
        contract = json.loads(
            (REPO_ROOT / lifecycle.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        parameters = contract["parameters"]
        raw_records = [
            f"parm={item['name']}:{item['description']}" for item in parameters
        ] + [f"parmtype={item['name']}:{item['type']}" for item in parameters]
        values = {
            "name": ["ihk_smp_x86_64"],
            "license": ["Dual BSD/GPL"],
            "depends": ["ihk"],
            "import_ns": ["MCKERNEL_IHK_V1"],
            "author": [],
            "description": [],
            "version": [],
            "parm": [
                f"{item['name']}:{item['description']} ({item['type']})"
                for item in parameters
            ],
            "parmtype": [f"{item['name']}:{item['type']}" for item in parameters],
        }
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field: values[field]
        ), mock.patch.object(
            lifecycle, "_raw_modinfo_records", return_value=raw_records
        ), mock.patch.object(
            lifecycle,
            "_undefined_symbols",
            return_value=set(lifecycle._provider_symbols(contract)),
        ):
            lifecycle.validate_module_artifact(module, summary, contract)
        self.assertTrue(summary["artifact_validated"])
        self.assertTrue(summary["built_symbol_reference_validated"])
        self.assertFalse(summary["rocky_build_load_validated"])

        expected_symbols = set(lifecycle._provider_symbols(contract))
        for missing in sorted(expected_symbols):
            with self.subTest(missing_provider_symbol=missing), mock.patch.object(
                lifecycle, "_modinfo", side_effect=lambda _path, field: values[field]
            ), mock.patch.object(
                lifecycle, "_raw_modinfo_records", return_value=raw_records
            ), mock.patch.object(
                lifecycle,
                "_undefined_symbols",
                return_value=expected_symbols - {missing},
            ):
                with self.assertRaisesRegex(
                    lifecycle.ValidationError,
                    "lacks provider relocations: {0}".format(missing),
                ):
                    lifecycle.validate_module_artifact(module, summary, contract)

        canonical_parm = list(values["parm"])
        first = parameters[0]
        for label, suffix in (("missing", ""), ("wrong", " (wrong)")):
            with self.subTest(parameter_type_suffix=label):
                values["parm"][0] = f"{first['name']}:{first['description']}{suffix}"
                with mock.patch.object(
                    lifecycle, "_modinfo", side_effect=lambda _path, field: values[field]
                ), mock.patch.object(
                    lifecycle, "_raw_modinfo_records", return_value=raw_records
                ), mock.patch.object(
                    lifecycle,
                    "_undefined_symbols",
                    return_value=set(lifecycle._provider_symbols(contract)),
                ):
                    with self.assertRaisesRegex(
                        lifecycle.ValidationError,
                        "parameter descriptions differ: expected .* got",
                    ):
                        lifecycle.validate_module_artifact(module, summary, contract)
                values["parm"] = list(canonical_parm)

        values["depends"] = []
        with mock.patch.object(
            lifecycle, "_modinfo", side_effect=lambda _path, field: values[field]
        ), mock.patch.object(
            lifecycle, "_raw_modinfo_records", return_value=raw_records
        ), mock.patch.object(
            lifecycle,
            "_undefined_symbols",
            return_value=set(lifecycle._provider_symbols(contract)),
        ):
            with self.assertRaisesRegex(lifecycle.ValidationError, "depends differs"):
                lifecycle.validate_module_artifact(module, summary, contract)

    def test_raw_modinfo_extraction_is_exact_and_fail_closed(self) -> None:
        module = self.repo / "ihk-smp-x86_64.ko"
        module.write_bytes(b"not-an-elf")
        valid = b"parm=ihk_cores:IHK reserved CPU cores\0\0parmtype=ihk_cores:uint\0"

        def dump_result(payload: bytes):
            def run(command, **_kwargs):
                dump_path = Path(command[2].split("=", 1)[1])
                dump_path.write_bytes(payload)
                Path(command[4]).write_bytes(b"disposable output")
                return mock.Mock(returncode=0, stdout=b"", stderr=b"")

            return run

        with mock.patch.object(
            lifecycle.shutil, "which", return_value="/usr/bin/objcopy"
        ), mock.patch.object(
            lifecycle.subprocess, "run", side_effect=dump_result(valid)
        ) as run:
            self.assertEqual(
                [
                    "parm=ihk_cores:IHK reserved CPU cores",
                    "parmtype=ihk_cores:uint",
                ],
                lifecycle._raw_modinfo_records(module),
            )
        self.assertEqual(b"not-an-elf", module.read_bytes())
        run.assert_called_once()
        command = run.call_args[0][0]
        self.assertEqual("/usr/bin/objcopy", command[0])
        self.assertEqual("--dump-section", command[1])
        self.assertRegex(command[2], r"^\.modinfo=.+/modinfo\.bin$")
        self.assertEqual(str(module), command[3])
        self.assertRegex(command[4], r"/module\.copy$")
        self.assertNotEqual(str(module), command[4])
        self.assertEqual(
            {"check": False, "capture_output": True}, run.call_args[1]
        )

        malformed = (
            ("unterminated", valid[:-1], "not NUL terminated"),
            ("no-records", b"\0\0", "has no records"),
            ("non-ascii", b"parm=ihk_cores:\xff\0", "not exact ASCII"),
            ("missing-key-separator", b"parm\0", "record is malformed"),
        )
        for label, payload, error in malformed:
            with self.subTest(raw_section=label), mock.patch.object(
                lifecycle.shutil, "which", return_value="/usr/bin/objcopy"
            ), mock.patch.object(
                lifecycle.subprocess,
                "run",
                side_effect=dump_result(payload),
            ):
                with self.assertRaisesRegex(lifecycle.ValidationError, error):
                    lifecycle._raw_modinfo_records(module)

    def test_built_artifact_rejects_hidden_raw_parameter_record_drift(self) -> None:
        module = self.repo / "ihk-smp-x86_64.ko"
        module.write_bytes(b"lifecycle=load parameters=\0lifecycle=unload parameters=\0")
        summary = lifecycle.validate_repository(REPO_ROOT)
        contract = json.loads(
            (REPO_ROOT / lifecycle.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        parameters = contract["parameters"]
        raw_records = [
            f"parm={item['name']}:{item['description']}" for item in parameters
        ] + [f"parmtype={item['name']}:{item['type']}" for item in parameters]
        values = {
            "name": ["ihk_smp_x86_64"],
            "license": ["Dual BSD/GPL"],
            "depends": ["ihk"],
            "import_ns": ["MCKERNEL_IHK_V1"],
            "author": [],
            "description": [],
            "version": [],
        }
        first_parm = next(
            index for index, record in enumerate(raw_records) if record.startswith("parm=")
        )
        first_type = next(
            index
            for index, record in enumerate(raw_records)
            if record.startswith("parmtype=")
        )
        cases = (
            (
                "duplicate-parm",
                raw_records + [raw_records[first_parm]],
                "raw parameter descriptions differ",
            ),
            (
                "malformed-parm",
                raw_records[:first_parm]
                + ["parm=ihk_cores"]
                + raw_records[first_parm + 1 :],
                "raw parameter descriptions differ",
            ),
            (
                "duplicate-parmtype",
                raw_records + [raw_records[first_type]],
                "raw parameter types differ",
            ),
            (
                "malformed-parmtype",
                raw_records[:first_type]
                + ["parmtype=ihk_cores"]
                + raw_records[first_type + 1 :],
                "raw parameter types differ",
            ),
        )
        for label, records, error in cases:
            with self.subTest(raw_record_drift=label), mock.patch.object(
                lifecycle, "_modinfo", side_effect=lambda _path, field: values[field]
            ), mock.patch.object(
                lifecycle, "_raw_modinfo_records", return_value=records
            ):
                with self.assertRaisesRegex(lifecycle.ValidationError, error):
                    lifecycle.validate_module_artifact(module, summary, contract)


if __name__ == "__main__":
    unittest.main()
