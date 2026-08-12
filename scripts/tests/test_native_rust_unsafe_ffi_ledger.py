#!/usr/bin/env python3
"""Mutation and synthetic tests for the fail-closed RS-011 ledger."""

from __future__ import print_function

import ast
import copy
import json
import os
import shutil
import stat
import sys
import tempfile
import types
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import native_rust_unsafe_ffi_ledger as ledger  # noqa: E402


def load_committed():
    return ledger.read_json(
        os.path.join(REPO_ROOT, ledger.LEDGER_PATH), "committed RS-011 ledger"
    )


def write_json(path, value):
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w", encoding="utf-8") as stream:
        stream.write(ledger.pretty(value))


def make_source(text):
    raw = text.encode("utf-8")
    return ledger.discover_sites("fixture.rs", raw, text)[0]


class CurrentLedgerTests(unittest.TestCase):
    def test_committed_ledger_is_exact_complete_and_fail_closed(self):
        value = load_committed()
        discovery = ledger.validate_ledger(value, REPO_ROOT)
        self.assertEqual(len(discovery["inputs"]), 8)
        self.assertEqual(len(discovery["sites"]), 21)
        self.assertEqual(value["coverage"]["by_crate"], {
            "ihk": 14,
            "ihk_smp_x86_64": 5,
            "mcctrl": 2,
        })
        self.assertEqual(value["readiness"]["gate_status"], "NOT_READY")
        self.assertFalse(value["readiness"]["technical_complete"])
        self.assertFalse(value["readiness"]["credit_eligible"])
        self.assertTrue(value["gate"]["self_attestation_forbidden"])
        for site in value["sites"]:
            self.assertTrue(site["safety_comment"]["text"].startswith("SAFETY:"))
            self.assertTrue(site["caller_obligations"])
            self.assertTrue(site["context_constraints"])
            self.assertTrue(site["owner"]["component"])
            self.assertEqual(site["compiler_capture"]["status"], "not_captured")
            self.assertEqual(site["independent_review"]["status"], "pending")
        queue_sites = [
            site
            for site in value["sites"]
            if site["path"] == "host-kernel/native-rust/ikc_queue.rs"
        ]
        self.assertEqual(
            [site["id"] for site in queue_sites],
            ["RS011-IHK-%04d" % index for index in range(4, 15)],
        )
        self.assertTrue(
            any(
                "no remote dequeue owner" in obligation
                for site in queue_sites
                for obligation in site["caller_obligations"]
            )
        )
        roots = {item["crate"]: item for item in value["crate_roots"]}
        self.assertEqual(
            roots["ihk"]["transitive_inputs"],
            [
                "host-kernel/native-rust/abi/x86_64.rs",
                "host-kernel/native-rust/ihk.rs",
                "host-kernel/native-rust/ihk_ioctl.rs",
                "host-kernel/native-rust/ikc_master.rs",
                "host-kernel/native-rust/ikc_queue.rs",
                "host-kernel/native-rust/os_registry.rs",
            ],
        )
        self.assertEqual(
            [item["id"] for item in value["sites"] if "ihk" in item["crate_roots"]],
            ["RS011-IHK-%04d" % index for index in range(1, 15)],
        )

    def test_checker_and_tests_parse_with_python_3_6_grammar(self):
        paths = (
            os.path.join(REPO_ROOT, "scripts/native_rust_unsafe_ffi_ledger.py"),
            os.path.abspath(__file__),
        )
        for path in paths:
            with open(path, "r", encoding="utf-8") as stream:
                source = stream.read()
            try:
                tree = ast.parse(source, filename=path, feature_version=(3, 6))
            except TypeError:
                tree = ast.parse(source, filename=path, feature_version=6)
            self.assertFalse(
                any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree)),
                path + " uses f-strings",
            )
            forbidden_attributes = {
                "is_relative_to",
                "readlink",
                "removeprefix",
                "removesuffix",
            }
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, forbidden_attributes)
                if isinstance(node, ast.Call):
                    for keyword in node.keywords:
                        self.assertNotIn(keyword.arg, {"capture_output", "text"})


class LexerAndSiteTests(unittest.TestCase):
    def test_masks_comments_strings_chars_and_raw_strings(self):
        text = (
            'const A: &str = r#"unsafe { extern \\"C\\" }"#;\n'
            'const B: &str = "unsafe impl Send for Fake {}";\n'
            "// unsafe { ignored(); }\n"
            "/* extern \"C\" { fn ignored(); } */\n"
            "// SAFETY: real operation is bounded.\n"
            "unsafe { real(); }\n"
        )
        sites = make_source(text)
        self.assertEqual([(item["kind"], item["line_start"]) for item in sites], [("unsafe_block", 6)])

    def test_discovers_every_supported_site_kind_and_macro_context(self):
        text = (
            "struct X;\n"
            "// SAFETY: marker one.\nunsafe impl Send for X {}\n"
            "// SAFETY: marker two.\nunsafe fn unsafe_call() {}\n"
            "// SAFETY: marker three.\nunsafe trait UnsafeTrait {}\n"
            "// SAFETY: marker four.\nextern \"C\" { fn foreign(); }\n"
            "// SAFETY: marker five.\nextern \"C\" fn callback() {}\n"
            "// SAFETY: marker six.\n#[export_name = \"exported\"] pub fn exported() {}\n"
            "// SAFETY: marker seven.\nstatic mut STORAGE: u8 = 0;\n"
            "// SAFETY: marker eight.\nunsafe {\n"
            "  // SAFETY: marker nine.\n  asm!(\"nop\");\n}\n"
            "// SAFETY: marker ten.\nglobal_asm!(\"nop\");\n"
            "macro_rules! demo { () => {\n"
            "  // SAFETY: marker eleven.\n  unsafe { work(); }\n"
            "}; }\n"
        )
        sites = make_source(text)
        kinds = [item["kind"] for item in sites]
        self.assertEqual(
            kinds,
            [
                "unsafe_impl",
                "unsafe_function",
                "unsafe_trait",
                "foreign_block",
                "extern_function",
                "ffi_export",
                "mutable_static",
                "unsafe_block",
                "inline_asm",
                "global_asm",
                "unsafe_block",
            ],
        )
        self.assertEqual(sites[-1]["macro_context"], "demo")

    def test_expression_digest_ignores_formatting_but_source_digest_does_not(self):
        first = make_source("// SAFETY: bounded.\nunsafe { call(a, b); }\n")[0]
        second = make_source("// SAFETY: bounded.\nunsafe{call( a ,b ) ;}\n")[0]
        self.assertEqual(first["expression_sha256"], second["expression_sha256"])
        self.assertNotEqual(first["source_sha256"], second["source_sha256"])

    def test_missing_safety_comment_and_unknown_unsafe_syntax_fail_closed(self):
        with self.assertRaisesRegex(ledger.LedgerError, "SAFETY"):
            make_source("unsafe { work(); }\n")
        with self.assertRaisesRegex(ledger.LedgerError, "unclassified unsafe"):
            make_source("// SAFETY: future syntax.\nunsafe move || work();\n")


class SyntheticClosureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = self.temporary.name
        self.native = os.path.join(self.repo, ledger.NATIVE_SOURCE_ROOT)
        os.makedirs(self.native)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, relative, text):
        path = os.path.join(self.repo, relative)
        parent = os.path.dirname(path)
        if not os.path.isdir(parent):
            os.makedirs(parent)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)
        return path

    def manifest(self):
        modules = []
        for crate in ledger.EXPECTED_CRATES:
            relative = ledger.EXPECTED_ROOTS[crate]
            modules.append(
                {
                    "crate": crate,
                    "source": {
                        "repository_path": relative,
                        "destination": os.path.basename(relative),
                        "sha256": ledger.sha256_file(os.path.join(self.repo, relative)),
                    },
                }
            )
        self.write(ledger.STAGE_MANIFEST_PATH, ledger.pretty({"modules": modules}))

    def test_literal_mod_and_include_closure_is_transitive_and_shared(self):
        self.write(ledger.EXPECTED_ROOTS["ihk"], 'mod child; include!("shared.rs");\n')
        self.write(ledger.EXPECTED_ROOTS["ihk_smp_x86_64"], "const SMP: u8 = 1;\n")
        self.write(ledger.EXPECTED_ROOTS["mcctrl"], 'include!(r"shared.rs");\n')
        self.write(ledger.NATIVE_SOURCE_ROOT + "/child.rs", "mod nested;\n")
        self.write(ledger.NATIVE_SOURCE_ROOT + "/child/nested.rs", "const N: u8 = 2;\n")
        self.write(ledger.NATIVE_SOURCE_ROOT + "/shared.rs", "const S: u8 = 3;\n")
        self.manifest()
        discovery = ledger.discover(self.repo)
        roots = {item["crate"]: item for item in discovery["roots"]}
        self.assertEqual(len(roots["ihk"]["transitive_inputs"]), 4)
        self.assertEqual(len(roots["mcctrl"]["transitive_inputs"]), 2)
        shared = [item for item in discovery["inputs"] if item["path"].endswith("shared.rs")][0]
        self.assertEqual(shared["crate_roots"], ["ihk", "mcctrl"])

    def test_dynamic_include_ambiguous_module_and_escape_fail_closed(self):
        cases = (
            ('include!(concat!("x", ".rs"));\n', None),
            ("mod child;\n", "ambiguous"),
            ('#[path = "../escape.rs"] mod escape;\n', "escape"),
        )
        for source, fixture in cases:
            with self.subTest(source=source):
                shutil.rmtree(self.native)
                os.makedirs(self.native)
                self.write(ledger.EXPECTED_ROOTS["ihk"], source)
                self.write(ledger.EXPECTED_ROOTS["ihk_smp_x86_64"], "const SMP: u8 = 1;\n")
                self.write(ledger.EXPECTED_ROOTS["mcctrl"], "const MCC: u8 = 1;\n")
                if fixture == "ambiguous":
                    self.write(ledger.NATIVE_SOURCE_ROOT + "/child.rs", "const A: u8 = 1;\n")
                    self.write(ledger.NATIVE_SOURCE_ROOT + "/child/mod.rs", "const B: u8 = 2;\n")
                if fixture == "escape":
                    self.write("host-kernel/escape.rs", "const E: u8 = 1;\n")
                self.manifest()
                with self.assertRaises(ledger.LedgerError):
                    ledger.discover(self.repo)

    def test_symlink_module_is_never_followed(self):
        self.write(ledger.EXPECTED_ROOTS["ihk"], "mod child;\n")
        self.write(ledger.EXPECTED_ROOTS["ihk_smp_x86_64"], "const SMP: u8 = 1;\n")
        self.write(ledger.EXPECTED_ROOTS["mcctrl"], "const MCC: u8 = 1;\n")
        outside = self.write("outside.rs", "const OUT: u8 = 1;\n")
        os.symlink(outside, os.path.join(self.native, "child.rs"))
        self.manifest()
        with self.assertRaises(ledger.LedgerError):
            ledger.discover(self.repo)


class LedgerMutationTests(unittest.TestCase):
    COPY_PATHS = (
        ledger.LEDGER_PATH,
        ledger.STAGE_MANIFEST_PATH,
        ledger.SOURCE_LOCK_PATH,
        ledger.CONFIG_POLICY_PATH,
        ledger.TOOLCHAIN_LOCK_PATH,
        ledger.EXPECTED_ROOTS["ihk"],
        ledger.EXPECTED_ROOTS["ihk_smp_x86_64"],
        ledger.EXPECTED_ROOTS["mcctrl"],
        ledger.NATIVE_SOURCE_ROOT + "/abi/x86_64.rs",
        ledger.NATIVE_SOURCE_ROOT + "/ikc_master.rs",
        ledger.NATIVE_SOURCE_ROOT + "/ikc_queue.rs",
        ledger.NATIVE_SOURCE_ROOT + "/os_registry.rs",
        ledger.NATIVE_SOURCE_ROOT + "/ihk_ioctl.rs",
    )

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = self.temporary.name
        for relative in self.COPY_PATHS:
            source = os.path.join(REPO_ROOT, relative)
            target = os.path.join(self.repo, relative)
            parent = os.path.dirname(target)
            if not os.path.isdir(parent):
                os.makedirs(parent)
            shutil.copy2(source, target)

    def tearDown(self):
        self.temporary.cleanup()

    def value(self):
        return ledger.read_json(os.path.join(self.repo, ledger.LEDGER_PATH), "fixture ledger")

    def resign(self, value):
        value["ledger_sha256"] = ledger.ledger_digest(value)
        write_json(os.path.join(self.repo, ledger.LEDGER_PATH), value)

    def rebind_source_file_only(self, value, crate):
        relative = ledger.EXPECTED_ROOTS[crate]
        path = os.path.join(self.repo, relative)
        digest = ledger.sha256_file(path)
        size = os.path.getsize(path)
        manifest_path = os.path.join(self.repo, ledger.STAGE_MANIFEST_PATH)
        manifest = ledger.read_json(manifest_path, "fixture stage manifest")
        for module in manifest["modules"]:
            if module["crate"] == crate:
                module["source"]["sha256"] = digest
        write_json(manifest_path, manifest)
        value["repository_locks"]["stage_manifest"]["sha256"] = ledger.sha256_file(manifest_path)
        for root in value["crate_roots"]:
            if root["crate"] == crate:
                root["sha256"] = digest
        for item in value["source_inputs"]:
            if item["path"] == relative:
                item["sha256"] = digest
                item["bytes"] = size
        for site in value["sites"]:
            if site["path"] == relative:
                site["file_sha256"] = digest
        value["source_closure_sha256"] = ledger.sha256_bytes(
            ledger.canonical_bytes(value["source_inputs"])
        )

    def test_added_unsafe_site_fails_after_all_outer_digests_are_resigned(self):
        value = self.value()
        path = os.path.join(self.repo, ledger.EXPECTED_ROOTS["ihk"])
        with open(path, "a", encoding="utf-8") as stream:
            stream.write("\n// SAFETY: injected mutation.\nfn mutation() { unsafe { core::hint::unreachable_unchecked(); } }\n")
        self.rebind_source_file_only(value, "ihk")
        self.resign(value)
        with self.assertRaisesRegex(ledger.LedgerError, "site count"):
            ledger.validate_ledger(value, self.repo)

    def test_expression_mutation_fails_after_file_and_envelope_resigning(self):
        value = self.value()
        path = os.path.join(self.repo, ledger.EXPECTED_ROOTS["ihk_smp_x86_64"])
        with open(path, "r", encoding="utf-8") as stream:
            text = stream.read()
        text = text.replace("core::ptr::read_volatile", "core::ptr::read", 1)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(text)
        self.rebind_source_file_only(value, "ihk_smp_x86_64")
        self.resign(value)
        with self.assertRaisesRegex(ledger.LedgerError, "mechanical field"):
            ledger.validate_ledger(value, self.repo)

    def test_missing_site_fails_after_counts_and_digest_are_recomputed(self):
        value = self.value()
        removed = value["sites"].pop()
        ids = [item["id"] for item in value["sites"]]
        value["coverage"]["site_count"] = len(ids)
        value["coverage"]["site_ids_sha256"] = ledger.sha256_bytes(ledger.canonical_bytes(ids))
        value["coverage"]["by_kind"][removed["kind"]] -= 1
        value["coverage"]["by_crate"][removed["crate_roots"][0]] -= 1
        self.resign(value)
        with self.assertRaisesRegex(ledger.LedgerError, "site count"):
            ledger.validate_ledger(value, self.repo)

    def test_empty_owner_duplicate_id_and_self_attested_ready_fail_when_resigned(self):
        mutations = (
            lambda value: value["sites"][0]["owner"].__setitem__("component", ""),
            lambda value: value["sites"][1].__setitem__("id", value["sites"][0]["id"]),
            lambda value: value["readiness"].__setitem__("gate_status", "PASS"),
        )
        for mutate in mutations:
            value = self.value()
            mutate(value)
            value["ledger_sha256"] = ledger.ledger_digest(value)
            with self.assertRaises(ledger.LedgerError):
                ledger.validate_ledger(value, self.repo)


class CompilerCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = self.temporary.name
        self.kernel_source = os.path.join(self.root, "kernel-source")
        self.kernel_build = os.path.join(self.root, "kernel-build")
        self.staged = os.path.join(self.kernel_source, "drivers/misc/mckernel")
        os.makedirs(self.staged)
        os.makedirs(self.kernel_build)
        self.value = load_committed()
        self.rustc = os.path.join(self.root, "rustc")
        with open(self.rustc, "w", encoding="utf-8") as stream:
            stream.write(
                "#!/usr/bin/env python3\n"
                "import sys\n"
                "if sys.argv[1:] == ['-Vv']:\n"
                "    print('rustc 1.92.0 (synthetic)')\n"
                "    print('host: x86_64-unknown-linux-gnu')\n"
                "else:\n"
                "    sys.exit(2)\n"
            )
        os.chmod(self.rustc, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        self.commands = []
        roots = {item["crate"]: item for item in self.value["crate_roots"]}
        for crate in ledger.EXPECTED_CRATES:
            root = roots[crate]
            staged_source = os.path.join(self.staged, root["destination"])
            staged_inputs = []
            for repository_path in root["transitive_inputs"]:
                relative = repository_path[len(ledger.NATIVE_SOURCE_ROOT) + 1 :]
                staged_input = os.path.join(self.staged, relative)
                parent = os.path.dirname(staged_input)
                if not os.path.isdir(parent):
                    os.makedirs(parent)
                shutil.copy2(os.path.join(REPO_ROOT, repository_path), staged_input)
                staged_inputs.append(staged_input)
            dep = os.path.join(self.kernel_build, crate + ".d")
            obj = os.path.join(self.kernel_build, crate + ".o")
            command = os.path.join(self.kernel_build, ".{0}.o.cmd".format(crate))
            with open(obj, "wb") as stream:
                stream.write((crate + " object\n").encode("utf-8"))
            with open(dep, "w", encoding="utf-8") as stream:
                stream.write("{0}: {1}\n".format(obj, " ".join(staged_inputs)))
            with open(command, "w", encoding="utf-8") as stream:
                stream.write(
                    "cmd_{0} := {1} --crate-name {2} --emit=dep-info={3},obj={4} {5}\n"
                    "source_{0} := {5}\n".format(
                        crate, self.rustc, crate, dep, obj, staged_source
                    )
                )
            self.commands.append(crate + "=" + command)
        self.platform_path = os.path.join(self.root, "rs001-platform.json")
        platform_value = {
            "profile": "rocky-10.2-exact-linux-api-evidence-v1",
            "target": {
                "distribution": "Rocky Linux",
                "release": "10.2",
                "architecture": "x86_64",
                "source_rpm_sha256": self.value["target"]["source_rpm_sha256"],
            },
            "source": {"exact_locked_replay": True},
            "configuration": {"selected_config_sha256": "a" * 64},
            "environment": {
                "tools": [
                    {
                        "id": "rustc",
                        "status": "captured",
                        "path": self.rustc,
                        "sha256": ledger.sha256_file(self.rustc),
                        "stdout_sha256": ledger.sha256_bytes(
                            b"rustc 1.92.0 (synthetic)\nhost: x86_64-unknown-linux-gnu\n"
                        ),
                        "stderr_sha256": ledger.sha256_bytes(b""),
                        "version_excerpt": "rustc 1.92.0 (synthetic)\nhost: x86_64-unknown-linux-gnu\n",
                    }
                ]
            },
            "readiness": {"gate_status": "NOT_READY", "credit_eligible": False},
        }
        platform_value["evidence_sha256"] = ledger.evidence_digest(platform_value)
        write_json(self.platform_path, platform_value)

    def tearDown(self):
        self.temporary.cleanup()

    def args(self):
        return types.SimpleNamespace(
            kernel_source=self.kernel_source,
            kernel_build=self.kernel_build,
            staged_root=self.staged,
            command=self.commands,
            platform_evidence=self.platform_path,
        )

    def test_exact_synthetic_compiler_closure_captures_but_never_awards_credit(self):
        evidence = ledger.build_compiler_evidence(self.args(), REPO_ROOT, self.value)
        ledger.validate_compiler_evidence(evidence, self.value)
        self.assertEqual([item["crate"] for item in evidence["crates"]], list(ledger.EXPECTED_CRATES))
        self.assertTrue(evidence["cross_validation"]["compiler_dependency_closure_match"])
        self.assertEqual(evidence["cross_validation"]["compiler_expanded_site_capture"], "missing")
        self.assertEqual(evidence["readiness"]["gate_status"], "NOT_READY")
        self.assertFalse(evidence["readiness"]["credit_eligible"])

    def test_extra_compiler_project_input_fails_closed(self):
        extra = os.path.join(self.staged, "extra.rs")
        with open(extra, "w", encoding="utf-8") as stream:
            stream.write("const EXTRA: u8 = 1;\n")
        dep = os.path.join(self.kernel_build, "ihk.d")
        with open(dep, "r", encoding="utf-8") as stream:
            line = stream.read().rstrip("\n")
        with open(dep, "w", encoding="utf-8") as stream:
            stream.write(line + " " + extra + "\n")
        with self.assertRaisesRegex(ledger.LedgerError, "closure differs"):
            ledger.build_compiler_evidence(self.args(), REPO_ROOT, self.value)

    def test_resigned_compiler_evidence_cannot_claim_expanded_sites_or_readiness(self):
        evidence = ledger.build_compiler_evidence(self.args(), REPO_ROOT, self.value)
        mutations = (
            lambda item: item["cross_validation"].__setitem__("compiler_expanded_site_capture", "complete"),
            lambda item: item["readiness"].__setitem__("gate_status", "PASS"),
            lambda item: item["crates"][0]["project_inputs"].pop(),
        )
        for mutate in mutations:
            changed = copy.deepcopy(evidence)
            mutate(changed)
            changed["evidence_sha256"] = ledger.evidence_digest(changed)
            with self.assertRaises(ledger.LedgerError):
                ledger.validate_compiler_evidence(changed, self.value)


if __name__ == "__main__":
    unittest.main()
