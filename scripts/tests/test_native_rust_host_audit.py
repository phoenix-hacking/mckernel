#!/usr/bin/env python3
"""Focused mutations for the locked native Rust host input closure."""

from __future__ import print_function

import ast
import copy
import json
import os
import shutil
import sys
import tempfile
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import native_rust_host_audit as host_audit  # noqa: E402


class NativeRustHostAuditTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = self.temporary.name
        self.manifest_relative = "host-kernel/kbuild/stage-manifest.json"
        with open(os.path.join(REPO_ROOT, self.manifest_relative), "r", encoding="utf-8") as stream:
            manifest = json.load(stream)
        self.original_manifest = manifest
        paths = {self.manifest_relative, "host-kernel/kbuild/Kbuild.in"}
        paths.update(item["repository_path"] for item in manifest["inputs"])
        paths.update(item["source"]["repository_path"] for item in manifest["modules"])
        self.original_files = {}
        for relative in paths:
            source = os.path.join(REPO_ROOT, *relative.split("/"))
            target = os.path.join(self.repo, *relative.split("/"))
            parent = os.path.dirname(target)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            shutil.copy2(source, target)
            with open(source, "rb") as stream:
                self.original_files[relative] = stream.read()
        self.manifest = os.path.join(self.repo, *self.manifest_relative.split("/"))
        self.old_root = host_audit.ROOT
        self.old_manifest = host_audit.MANIFEST
        host_audit.ROOT = self.repo
        host_audit.MANIFEST = self.manifest

    def tearDown(self):
        host_audit.ROOT = self.old_root
        host_audit.MANIFEST = self.old_manifest
        self.temporary.cleanup()

    def load_manifest(self):
        with open(self.manifest, "r", encoding="utf-8") as stream:
            return json.load(stream)

    def write_manifest(self, value):
        with open(self.manifest, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")

    def repository_path(self, relative):
        return os.path.join(self.repo, *relative.split("/"))

    def write_resealed_source(self, relative, text):
        for original_relative, data in self.original_files.items():
            with open(self.repository_path(original_relative), "wb") as stream:
                stream.write(data)
        path = self.repository_path(relative)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)
        value = copy.deepcopy(self.original_manifest)
        records = [item["source"] for item in value["modules"]]
        records.extend(value["inputs"])
        matches = [
            item for item in records
            if item.get("repository_path") == relative
        ]
        self.assertEqual(1, len(matches), relative)
        matches[0]["sha256"] = host_audit.sha256(path)
        self.write_manifest(value)

    def mutate_resealed_source(self, relative, old, new):
        original = self.original_files[relative].decode("utf-8")
        self.assertEqual(1, original.count(old), old)
        self.write_resealed_source(relative, original.replace(old, new, 1))

    def append_resealed_source(self, relative, addition):
        original = self.original_files[relative].decode("utf-8")
        self.write_resealed_source(relative, original + addition)

    def test_integrated_repository_closure_passes(self):
        self.assertEqual(0, host_audit.main())

    def test_reviewed_ihk_provider_abi_and_export_records_are_exact(self):
        relative = "host-kernel/native-rust/ihk.rs"
        mutations = (
            (
                'pub extern "C" fn ihk_smp_provider_attach_v1() -> i64 {',
                'pub extern "C" fn ihk_smp_provider_attach_v1() -> u64 {',
            ),
            (
                'pub extern "C" fn ihk_smp_provider_detach_v1(token: i64) {',
                'pub extern "C" fn ihk_smp_provider_detach_v1(token: u64) {',
            ),
            (
                'symbol: ihk_smp_provider_attach_v1 as *const () as *const u8,',
                'symbol: ihk_smp_provider_detach_v1 as *const () as *const u8,',
            ),
            (
                'symbol: ihk_smp_provider_detach_v1 as *const () as *const u8,',
                'symbol: ihk_smp_provider_attach_v1 as *const () as *const u8,',
            ),
            (
                '#[export_name = "ihk_smp_provider_attach_v1"]',
                '#[export_name = "ihk_smp_provider_attach_v2"]',
            ),
            (
                'pub static IHK_SMP_PROVIDER_DETACH_V1_EXPORT: IhkExportSymbolRecord',
                'pub static IHK_SMP_PROVIDER_DETACH_V2_EXPORT: IhkExportSymbolRecord',
            ),
            (
                'type IhkSmpProviderInitV2 = extern "C" fn() -> i32;',
                'type IhkSmpProviderInitV2 = extern "system" fn() -> i32;',
            ),
            (
                'pub extern "C" fn ihk_smp_provider_attach_v2(\n'
                '    callback_abi: u32,',
                'pub extern "C" fn ihk_smp_provider_attach_v2(\n'
                '    callback_abi: u64,',
            ),
            (
                'pub extern "C" fn ihk_smp_provider_detach_v2(\n'
                '    token: i64,\n'
                '    exit: Option<IhkSmpProviderExitV2>,',
                'pub extern "C" fn ihk_smp_provider_detach_v2(\n'
                '    token: i64,\n'
                '    exit: IhkSmpProviderExitV2,',
            ),
            (
                'symbol: ihk_smp_provider_attach_v2 as *const () as *const u8,',
                'symbol: ihk_smp_provider_detach_v2 as *const () as *const u8,',
            ),
            (
                '#[export_name = "__export_symbol_ihk_smp_provider_detach_v2"]',
                '#[export_name = "__export_symbol_ihk_smp_provider_detach_v3"]',
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.mutate_resealed_source(relative, old, new)
                with self.assertRaisesRegex(
                    SystemExit, "reviewed Rust escape block differs"
                ):
                    host_audit.main()

        blocks = dict(host_audit.REVIEWED_RUST_ESCAPE_BLOCKS[relative])
        first_label = "IHK SMP provider attach export record"
        second_label = "IHK SMP provider detach export record"
        first = host_audit.REVIEWED_RUST_BLOCK_PREFIXES[first_label] + blocks[first_label]
        second = host_audit.REVIEWED_RUST_BLOCK_PREFIXES[second_label] + blocks[second_label]
        original = self.original_files[relative].decode("utf-8")
        marker = "__HOST_AUDIT_SWAP_MARKER__"
        swapped = original.replace(first, marker, 1)
        swapped = swapped.replace(second, first, 1).replace(marker, second, 1)
        self.write_resealed_source(relative, swapped)
        with self.assertRaisesRegex(SystemExit, "block order differs"):
            host_audit.main()

    def test_reviewed_smp_v2_callback_c_abi_is_exact(self):
        relative = "host-kernel/native-rust/ihk_smp_x86_64.rs"
        mutations = (
            ('extern "C" {', 'extern "Rust" {'),
            (
                'static IHK_PROVIDER_LIFECYCLE_V1: u8;',
                'static IHK_PROVIDER_LIFECYCLE_V1: i8;',
            ),
            (
                'fn ihk_smp_provider_attach_v2(\n'
                '        callback_abi: u32,',
                'fn ihk_smp_provider_attach_v2(\n'
                '        callback_abi: u64,',
            ),
            (
                'fn ihk_smp_provider_detach_v2(token: i64, exit: Option<IhkSmpProviderExitV2>);',
                'fn ihk_smp_provider_detach_v2(token: u64, exit: Option<IhkSmpProviderExitV2>);',
            ),
            (
                '    fn ihk_smp_provider_detach_v2(token: i64, exit: Option<IhkSmpProviderExitV2>);\n}',
                '    fn ihk_smp_provider_detach_v2(token: i64, exit: Option<IhkSmpProviderExitV2>);\n'
                '    fn unreviewed_provider_call();\n}',
            ),
            (
                'type IhkSmpProviderExitV2 = extern "C" fn();',
                'type IhkSmpProviderExitV2 = extern "system" fn();',
            ),
            (
                'extern "C" fn ihk_smp_provider_init_v2() -> i32 {',
                'extern "C" fn ihk_smp_provider_init_v2(minor: u32) -> i32 {',
            ),
            (
                'extern "C" fn ihk_smp_provider_exit_v2() {',
                'extern "C" fn ihk_smp_provider_exit_v2() -> i32 {',
            ),
        )
        for old, new in mutations:
            with self.subTest(old=old):
                self.mutate_resealed_source(relative, old, new)
                with self.assertRaisesRegex(
                    SystemExit, "reviewed Rust escape block differs"
                ):
                    host_audit.main()

    def test_all_other_rust_escape_hatches_fail_closed_after_reseal(self):
        support = "host-kernel/native-rust/ihk_ioctl.rs"
        cases = (
            (support, '\nextern "C" { fn unreviewed(); }\n'),
            (support, '\nextern "Rust" { fn unreviewed(); }\n'),
            (support, '\n#[link(name = "unreviewed")] extern "C" {}\n'),
            (support, '\n#[link_name = "unreviewed"] static UNREVIEWED: u8;\n'),
            (support, '\n#[link_section = ".unreviewed"] static UNREVIEWED: u8 = 0;\n'),
            (support, '\n#[export_name = "unreviewed"] pub fn escape() {}\n'),
            (support, '\n#[no_mangle] pub fn escape() {}\n'),
            (support, '\nconst _: &[u8] = include_bytes!("unreviewed");\n'),
            (support, '\nconst _: &str = include_str!("unreviewed");\n'),
            (support, '\ninclude!("unreviewed");\n'),
            (support, '\nfn escape() { unsafe { asm!("nop"); } }\n'),
            (support, '\nglobal_asm!("nop");\n'),
            (support, '\nnaked_asm!("nop");\n'),
            (support, '\nextern /* gap */ "system" { fn hidden(); }\n'),
            (support, '\nextern crate hidden;\n'),
            (support, '\ninclude /* gap */ ! ("hidden.rs");\n'),
            (support, '\ncore::arch::asm /* gap */ ! ("nop");\n'),
            (
                support,
                '\nuse core::arch::global_asm as emit; emit!("nop");\n',
            ),
            (support, '\n#[linkage = "external"] static HIDDEN: u8 = 0;\n'),
            (support, '\n#[path = "unreviewed.rs"] mod unreviewed;\n'),
            (support, '\n#[cfg_attr(all(), path = "hidden.rs")] mod hidden;\n'),
            (
                "host-kernel/native-rust/ihk.rs",
                '\nextern "C" { fn unreviewed_ihk_export(); }\n',
            ),
            (
                "host-kernel/native-rust/ihk_smp_x86_64.rs",
                '\nextern "Rust" { fn unreviewed_smp_import(); }\n',
            ),
        )
        for relative, addition in cases:
            with self.subTest(relative=relative, addition=addition.strip()):
                self.append_resealed_source(relative, addition)
                with self.assertRaisesRegex(
                    SystemExit, "unreviewed Rust escape hatch"
                ):
                    host_audit.main()

    def test_inert_escape_spellings_and_raw_extern_identifier_are_ignored(self):
        relative = "host-kernel/native-rust/ihk_ioctl.rs"
        addition = r'''
// extern "C" { fn inert(); } include!("inert.rs");
/* nested comment /* global_asm!("nop"); */ include_bytes!("inert") */
const INERT_ESCAPE_WORDS: &str = r#"extern Rust include! asm! no_mangle"#;
fn inert_raw_identifier() { let r#extern = 1; let _ = r#extern; }
'''
        self.append_resealed_source(relative, addition)
        self.assertEqual(0, host_audit.main())

    def test_reviewed_escape_blocks_must_be_active_and_unmodified_at_top_level(self):
        smp = "host-kernel/native-rust/ihk_smp_x86_64.rs"
        for modifier in ("pub ", "unsafe ", "#[cfg(any())]\n", "#[link(name = \"x\")]\n"):
            with self.subTest(modifier=modifier):
                self.mutate_resealed_source(
                    smp, 'extern "C" {', modifier + 'extern "C" {'
                )
                with self.assertRaisesRegex(SystemExit, "outer"):
                    host_audit.main()

        smp_blocks = dict(host_audit.REVIEWED_RUST_ESCAPE_BLOCKS[smp])
        provider_import = smp_blocks["IHK SMP three-symbol provider import"]
        self.mutate_resealed_source(
            smp,
            provider_import,
            "const HIDDEN_PROVIDER_SCOPE: () = { const SENTINEL: () = ();\n"
            + provider_import
            + "\n};",
        )
        with self.assertRaisesRegex(SystemExit, "block depth differs"):
            host_audit.main()

        for label in (
            "IHK SMP parameter descriptor section",
            "IHK SMP loadable parameter metadata",
            "IHK SMP built-in parameter metadata",
        ):
            with self.subTest(label=label):
                block = smp_blocks[label]
                prefix = host_audit.REVIEWED_RUST_BLOCK_PREFIXES[label]
                full = prefix + block
                self.mutate_resealed_source(
                    smp, full, "#[cfg(any())]\n        " + full
                )
                with self.assertRaisesRegex(SystemExit, "outer attribute"):
                    host_audit.main()

        ihk = "host-kernel/native-rust/ihk.rs"
        label = "IHK SMP provider attach export record"
        block = dict(host_audit.REVIEWED_RUST_ESCAPE_BLOCKS[ihk])[label]
        prefix = host_audit.REVIEWED_RUST_BLOCK_PREFIXES[label]
        full = prefix + block
        self.mutate_resealed_source(ihk, full, "#[cfg(any())]\n" + full)
        with self.assertRaisesRegex(SystemExit, "outer attribute"):
            host_audit.main()

        original = self.original_files[ihk].decode("utf-8")
        decoy = original.replace(full, "", 1) + "\n/*\n" + full + "\n*/\n"
        self.write_resealed_source(ihk, decoy)
        with self.assertRaisesRegex(SystemExit, "not active"):
            host_audit.main()

    def test_preexisting_reviewed_linkage_surfaces_are_still_exact(self):
        mutations = (
            (
                "host-kernel/native-rust/ihk.rs",
                '#[path = "abi/x86_64.rs"]\nmod abi;',
                '#[path = "abi/other.rs"]\nmod abi;',
            ),
            (
                "host-kernel/native-rust/mcctrl.rs",
                'extern "Rust" {\n'
                '    #[link_name = "ihk_provider_lifecycle_v1"]\n'
                '    static IHK_PROVIDER_LIFECYCLE_V1: u8;\n}',
                'extern "C" {\n'
                '    #[link_name = "ihk_provider_lifecycle_v1"]\n'
                '    static IHK_PROVIDER_LIFECYCLE_V1: u8;\n}',
            ),
            (
                "host-kernel/native-rust/mcctrl.rs",
                '#[link_section = ".modinfo"]\n'
                '#[used(compiler)]\n'
                'static MCCTRL_IHK_IMPORT_NAMESPACE: [u8; 26]',
                '#[link_section = ".data"]\n'
                '#[used(compiler)]\n'
                'static MCCTRL_IHK_IMPORT_NAMESPACE: [u8; 26]',
            ),
        )
        for relative, old, new in mutations:
            with self.subTest(relative=relative, old=old):
                self.mutate_resealed_source(relative, old, new)
                with self.assertRaisesRegex(
                    SystemExit, "reviewed Rust escape block differs"
                ):
                    host_audit.main()

    def test_master_omission_and_digest_drift_fail_closed(self):
        value = self.load_manifest()
        value["inputs"] = [
            item for item in value["inputs"] if item.get("destination") != "ikc_master.rs"
        ]
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "IKC master"):
            host_audit.main()

        value = copy.deepcopy(self.original_manifest)
        master = next(
            item for item in value["inputs"]
            if item.get("destination") == "ikc_master.rs"
        )
        master["sha256"] = "0" * 64
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "digest drift"):
            host_audit.main()

    def test_page_support_omission_and_digest_drift_fail_closed(self):
        for destination in ("page_allocator.rs", "page_owner_registry.rs"):
            with self.subTest(destination=destination):
                value = copy.deepcopy(self.original_manifest)
                value["inputs"] = [
                    item for item in value["inputs"]
                    if item.get("destination") != destination
                ]
                self.write_manifest(value)
                with self.assertRaisesRegex(SystemExit, "support input closure"):
                    host_audit.main()

                value = copy.deepcopy(self.original_manifest)
                item = next(
                    entry for entry in value["inputs"]
                    if entry.get("destination") == destination
                )
                item["sha256"] = "0" * 64
                self.write_manifest(value)
                with self.assertRaisesRegex(SystemExit, "digest drift"):
                    host_audit.main()

    def test_device_registry_omission_and_digest_drift_fail_closed(self):
        value = copy.deepcopy(self.original_manifest)
        value["inputs"] = [
            item for item in value["inputs"]
            if item.get("destination") != "device_registry.rs"
        ]
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "support input closure"):
            host_audit.main()

        value = copy.deepcopy(self.original_manifest)
        item = next(
            entry for entry in value["inputs"]
            if entry.get("destination") == "device_registry.rs"
        )
        item["sha256"] = "0" * 64
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "digest drift"):
            host_audit.main()

    def test_ioctl_dispatch_omission_and_digest_drift_fail_closed(self):
        value = copy.deepcopy(self.original_manifest)
        value["inputs"] = [
            item for item in value["inputs"]
            if item.get("destination") != "ihk_ioctl.rs"
        ]
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "support input closure"):
            host_audit.main()

        value = copy.deepcopy(self.original_manifest)
        item = next(
            entry for entry in value["inputs"]
            if entry.get("destination") == "ihk_ioctl.rs"
        )
        item["sha256"] = "0" * 64
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "digest drift"):
            host_audit.main()

    def test_smp_resource_omission_and_digest_drift_fail_closed(self):
        value = copy.deepcopy(self.original_manifest)
        value["inputs"] = [
            item for item in value["inputs"]
            if item.get("destination") != "smp_resource.rs"
        ]
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "support input closure"):
            host_audit.main()

        value = copy.deepcopy(self.original_manifest)
        item = next(
            entry for entry in value["inputs"]
            if entry.get("destination") == "smp_resource.rs"
        )
        item["sha256"] = "0" * 64
        self.write_manifest(value)
        with self.assertRaisesRegex(SystemExit, "digest drift"):
            host_audit.main()

    def test_checker_and_tests_parse_with_python_3_6_grammar(self):
        paths = (host_audit.__file__, os.path.abspath(__file__))
        for path in paths:
            with open(path, "r", encoding="utf-8") as stream:
                source = stream.read()
            try:
                ast.parse(source, filename=path, feature_version=(3, 6))
            except TypeError:
                ast.parse(source, filename=path, feature_version=6)


if __name__ == "__main__":
    unittest.main()
