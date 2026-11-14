#!/usr/bin/env python3
"""Synthetic tests for the bounded compiler-backed failure-flow capture."""

import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import host_module_failure_flows as flows  # noqa: E402
import host_module_failure_sites as sites  # noqa: E402


class StrictInputTests(unittest.TestCase):
    def test_duplicate_json_keys_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "capture.json"
            path.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
            with self.assertRaisesRegex(flows.FlowError, "duplicate JSON key"):
                flows.read_json(path)

    def test_digest_validation_rejects_non_sha256(self):
        with self.assertRaises(flows.FlowError):
            flows.require_digest("abc", "synthetic digest")

    def test_errno_namespace_excludes_e_prefixed_non_errno_tokens(self):
        self.assertEqual(
            flows.errno_names_in(
                "EXPORT_SYMBOL(value); ERR_PTR(value); EINVAL; ERESTARTSYS;"
            ),
            ["EINVAL", "ERESTARTSYS"],
        )

    def test_each_error_pointer_marker_has_an_exact_source_column(self):
        text = "if (IS_ERR(a) || IS_ERR_OR_NULL(b)) return PTR_ERR(ERR_PTR(-5));"
        self.assertEqual(
            [(macro, role) for _, macro, role in flows.flow_markers(text)],
            [
                ("IS_ERR", "error_pointer_guard"),
                ("IS_ERR_OR_NULL", "error_pointer_or_null_guard"),
                ("PTR_ERR", "error_pointer_translation"),
                ("ERR_PTR", "error_pointer_encoding"),
            ],
        )
        columns = [column for column, _, _ in flows.flow_markers(text)]
        self.assertEqual(len(columns), len(set(columns)))

    def test_errno_context_uses_lexical_return_and_real_comparisons(self):
        self.assertEqual(
            flows.errno_token_role("__return_syscall(value, -ERESTARTSYS);"),
            "errno_token_value_context",
        )
        self.assertEqual(
            flows.errno_token_role("r->ret = -EIO;"),
            "errno_token_value_context",
        )
        self.assertEqual(
            flows.errno_token_role("if (r->ret == -EIO)"),
            "errno_token_comparison_context",
        )
        for non_comparison in ("r->ret", "value << 2", "value >>= 1", "value <<= 1"):
            self.assertFalse(flows.has_comparison_operator(non_comparison))
        for comparison in ("value < 2", "value >= 1", "value != 0"):
            self.assertTrue(flows.has_comparison_operator(comparison))

    def test_masked_comment_cannot_create_error_pointer_return_role(self):
        raw = "return 0; /* ERR_PTR(-EIO) */"
        masked = sites.mask_non_code(raw, "c")
        self.assertEqual(
            flows.role_for_return(masked, [], []), "non_failure_constant_return"
        )

    def test_schema_v1_can_never_claim_exhaustive(self):
        self.assertEqual(
            flows.ANALYSIS_CLAIM,
            {
                "credit_eligible": False,
                "exhaustive": False,
                "fp_0006_status": "IN_PROGRESS",
                "reason": "schema v1 is a bounded compiler checkpoint with unresolved paths and no per-flow executable-test map",
                "test_mapped": False,
            },
        )
        stderr = StringIO()
        with redirect_stderr(stderr):
            result = flows.main(
                [
                    "--build-dir", "/not/used",
                    "--kernel-dir", "/not/used",
                    "--failure-sites", "/not/used/capture.json",
                    "--output", "/not/used/output.json",
                    "--require-exhaustive",
                ]
            )
        self.assertEqual(result, 1)
        self.assertIn("FP-0006 remains IN_PROGRESS", stderr.getvalue())

    def test_failure_site_identity_mutation_fails_closed(self):
        expected = [
            {
                "module": module,
                "language": language,
                "source": source,
                "command_file": command,
            }
            for module, language, source, command in sites.EXPECTED_SOURCES
        ]
        for record in expected:
            record["compile_argv"] = ["gcc", record["source"]]
            record["digests"] = {
                key: "a" * 64
                for key in (
                    "command_file_sha256",
                    "compiler_sha256",
                    "config_sha256",
                    "effective_source_sha256",
                    "preprocessed_sha256",
                    "preprocessing_argv_sha256",
                    "target_preprocessed_sha256",
                )
            }
        identity = {
            "column": 8,
            "errno": "EINVAL",
            "language": "c",
            "line": 10,
            "module": expected[0]["module"],
            "source": expected[0]["source"],
            "source_sha256": "a" * 64,
        }
        identity_digest = flows.sha256_bytes(flows.canonical_bytes(identity))
        site = dict(identity)
        site.update(
            {
                "active_source_sha256": "a" * 64,
                "classification": "explicit_negative_errno_token",
                "end_column": 15,
                "expression": "-EINVAL",
                "id": "HFS-" + identity_digest[:24].upper(),
                "identity_sha256": identity_digest,
                "line_sha256": "b" * 64,
            }
        )
        capture = {
            "schema_version": sites.SCHEMA_VERSION,
            "profile": sites.PROFILE,
            "sources": expected,
            "failure_sites": [site],
            "coverage": {
                "by_errno": {"EINVAL": 1},
                "by_language": {"c": 1},
                "by_module": {expected[0]["module"]: 1},
                "source_count": len(expected),
                "failure_site_count": 1,
            },
        }
        flows.validate_input_shape(capture)
        capture["failure_sites"][0]["line"] = 11
        with self.assertRaisesRegex(flows.FlowError, "identity digest"):
            flows.validate_input_shape(capture)

    def test_first_stage_mapping_includes_flow_and_unresolved_rust_ids(self):
        mapped = flows.collect_first_stage_ids(
            [
                {
                    "origin": {
                        "first_stage_site_ids": ["HFS-" + "A" * 24]
                    }
                }
            ],
            [
                {
                    "kind": "rust_mir_and_cfg_not_captured",
                    "first_stage_site_ids": ["HFS-" + "B" * 24],
                }
            ],
        )
        self.assertEqual(
            mapped, {"HFS-" + "A" * 24, "HFS-" + "B" * 24}
        )

    def test_authoritative_input_symlink_and_escape_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "root"
            root.mkdir()
            real = root / "real.json"
            real.write_text("{}\n", encoding="utf-8")
            link = root / "capture.json"
            link.symlink_to(real)
            with self.assertRaisesRegex(flows.FlowError, "must not be a symlink"):
                flows.require_regular_within(link, root, "capture")
            outside = Path(temporary) / "outside.json"
            outside.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(flows.FlowError, "escapes"):
                flows.require_regular_within(outside, root, "capture")


class CompilerArgvTests(unittest.TestCase):
    def test_analysis_argv_confines_outputs_and_preserves_optimization(self):
        original = [
            "gcc",
            "-DMODULE",
            "-Wp,-MMD,/old/.demo.o.d",
            "-MF",
            "/old/demo.d",
            "-MT",
            "/old/demo.o",
            "-O2",
            "-c",
            "-o",
            "/old/demo.o",
            "/src/demo.c",
        ]
        output = Path("/tmp/bounded-flow/output.o")
        argv = flows.reconstruct_ir_argv(original, original.index("/src/demo.c"), output)
        self.assertEqual(argv[0], "gcc")
        self.assertEqual(argv[-1], "/src/demo.c")
        self.assertEqual(argv.count("-o"), 1)
        self.assertIn(str(output), argv)
        self.assertIn("-fdump-tree-cfg-lineno", argv)
        self.assertIn("-fdump-tree-ssa-lineno", argv)
        self.assertIn("-fdump-ipa-cgraph-lineno", argv)
        self.assertEqual([word for word in argv if word.startswith("-O")], ["-O2"])
        for removed in (
            "-Wp,-MMD,/old/.demo.o.d",
            "-MF",
            "-MT",
            "/old/demo.o",
        ):
            self.assertNotIn(removed, argv)

    def test_existing_dump_or_ambiguous_source_fails_closed(self):
        for unsafe in (
            "-fdump-tree-cfg",
            "-dumpdir=/tmp/escape",
            "-S",
            "-flto",
        ):
            with self.assertRaises(flows.FlowError):
                flows.reconstruct_ir_argv(
                    ["gcc", unsafe, "-c", "a.c"], 3, Path("out.o")
                )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "a.c"
            source.write_text("int f(void) { return 0; }\n", encoding="utf-8")
            with self.assertRaisesRegex(flows.FlowError, "2 times"):
                flows.source_index_in_argv(
                    ["gcc", str(source), str(source)], source, root
                )

    def test_analysis_argv_rejects_code_loading_and_output_escape_options(self):
        for unsafe in (
            "-fplugin=/tmp/plugin.so",
            "-fplugin-arg-demo-output=/tmp/escape",
            "-fprofile-generate=/tmp/profile",
            "-fprofile-use=/tmp/profile",
            "-fauto-profile=/tmp/profile.afdo",
            "-fbranch-probabilities",
            "-fprofile-arcs",
            "-ftest-coverage",
            "--coverage",
            "-fopt-info=/tmp/escape",
            "-wrapper",
            "-wrapper=/tmp/wrapper",
            "-specs=/tmp/escape.specs",
            "--specs=/tmp/escape.specs",
            "-B",
            "-B/tmp/tool-prefix",
            "-iplugindir=/tmp/plugins",
            "-Wa,@/tmp/assembler-options",
            "-Wp,@/tmp/preprocessor-options",
            "-Xassembler",
            "-Xpreprocessor",
            "-Xlinker",
            "@/tmp/compiler-options",
        ):
            with self.subTest(unsafe=unsafe):
                with self.assertRaisesRegex(flows.FlowError, "unsafe replay option"):
                    flows.reconstruct_ir_argv(
                        ["gcc", unsafe, "-c", "a.c"], 3, Path("out.o")
                    )

    def test_phi_predecessor_edges_are_not_indirect_callbacks(self):
        self.assertEqual(flows.calls_in("PHI <_6(3), _5(4)>"), ([], []))
        self.assertEqual(
            flows.calls_in("callback.1_2 ()"),
            ([], ["callback.1_2"]),
        )


@unittest.skipUnless(shutil.which("gcc"), "synthetic compiler-backed test needs gcc")
class SyntheticCompilerFlowTests(unittest.TestCase):
    SOURCE = """\
typedef long synthetic_long;
#define EINVAL 22
#define ERR_PTR(error) ((void *)((synthetic_long)(error)))
#define PTR_ERR(pointer) ((synthetic_long)(pointer))
#define IS_ERR(pointer) ((unsigned long)(void *)(pointer) >= (unsigned long)-4095)
#define SYNTHETIC_FAILURE -EFAULT
extern int provider(void);
extern void *pointer_provider(void);
extern int (*callback_provider)(void);

int provider_forward(void)
{
    int ret = provider(); /* -EIO and ERR_PTR are masked across
                             this continued comment. */
    if (ret == -((int)EINVAL))
        return ret;
    if (ret < 0)
        return ret;
    return 0;
}

long translated_pointer(void)
{
    void *pointer = pointer_provider();
    if (IS_ERR(pointer))
        return PTR_ERR(pointer);
    return callback_provider();
}

void *encoded_pointer(void)
{
    return ERR_PTR(-((int)EINVAL));
}

int explicit_errno(void)
{
    return -EINVAL;
}

int repeated_errno(void)
{
    return -EINVAL + EINVAL;
}

int comment_safe(void)
{
    return 0; /* ERR_PTR(-EIO) must stay masked. */
}
"""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "synthetic.c"
        self.source.write_text(self.SOURCE, encoding="utf-8")
        self.roots = (
            ("$REPO", self.root),
            ("$BUILD", self.root / "build"),
            ("$KERNEL", self.root / "kernel"),
        )
        (self.root / "build").mkdir()
        (self.root / "kernel").mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def compile_ir(self):
        argv = [
            shutil.which("gcc"),
            "-Wall",
            "-O2",
            "-c",
            str(self.source),
            "-o",
            str(self.root / "discarded.o"),
        ]
        return flows.run_ir_for_source(argv, 4, self.root, self.roots)

    def analyze(self, source_sha256=None, profile=None):
        data = self.source.read_bytes()
        source_sha256 = source_sha256 or flows.sha256_bytes(data)
        profile = profile or ("a" * 64)
        rows = list(enumerate(self.source.read_text(encoding="utf-8").splitlines(True), 1))
        active = sites.rows_digest(rows)
        explicit = sites.scan_rows(
            "mcctrl", "c", "synthetic.c", source_sha256, active, rows
        )
        return flows.analyze_ir_source(
            "mcctrl",
            "synthetic.c",
            self.source,
            source_sha256,
            profile,
            "b" * 64,
            self.compile_ir(),
            rows,
            explicit,
            self.root,
        )

    def test_compiler_ssa_classifies_provider_callback_and_pointer_flows(self):
        analysis = self.analyze()
        roles = {item["expression_role"] for item in analysis["flows"]}
        for expected in (
            "provider_return_candidate",
            "signed_result_guard_candidate",
            "error_pointer_guard",
            "error_pointer_translation_return",
            "error_pointer_translation",
            "callback_return_candidate",
            "error_pointer_encoding_return",
            "error_pointer_encoding",
            "errno_token_return_context",
            "errno_token_comparison_context",
            "explicit_errno_return",
        ):
            self.assertIn(expected, roles)
        cast_contexts = [
            item
            for item in analysis["flows"]
            if item["expression_role"] == "errno_token_return_context"
            and item["function"] == "encoded_pointer"
            and item["origin"].get("errno") == "EINVAL"
            and not item["origin"].get("first_stage_site_ids")
        ]
        self.assertEqual(len(cast_contexts), 1)
        # ``-((int)EINVAL)`` is outside the first-stage token grammar; the
        # compiler-located errno context still preserves it without pretending
        # that the original HFS capture saw it.
        self.assertEqual(cast_contexts[0]["origin"]["first_stage_site_ids"], [])
        rows = list(
            enumerate(self.source.read_text(encoding="utf-8").splitlines(True), 1)
        )
        digest = flows.sha256_bytes(self.source.read_bytes())
        explicit = sites.scan_rows(
            "mcctrl", "c", "synthetic.c", digest, sites.rows_digest(rows), rows
        )
        mapped = {
            site_id
            for item in analysis["flows"]
            for site_id in item["origin"].get("first_stage_site_ids", [])
        }
        mapped.update(
            site_id
            for item in analysis["unresolved"]
            for site_id in item.get("first_stage_site_ids", [])
        )
        self.assertEqual(mapped, {item["id"] for item in explicit})
        self.assertTrue(
            any(
                item["kind"]
                == "active_errno_token_has_no_unique_compiler_function"
                and item.get("errno") == "EFAULT"
                for item in analysis["unresolved"]
            )
        )
        repeated_line = next(
            number
            for number, text in rows
            if "return -EINVAL + EINVAL" in text
        )
        repeated_contexts = [
            item
            for item in analysis["flows"]
            if item["function"] == "repeated_errno"
            and item["location"]["line"] == repeated_line
            and item["origin"].get("errno") == "EINVAL"
        ]
        self.assertEqual(len(repeated_contexts), 2)
        self.assertEqual(
            sum(bool(item["origin"]["first_stage_site_ids"]) for item in repeated_contexts),
            1,
        )
        self.assertFalse(
            any(item["function"] == "comment_safe" for item in analysis["flows"])
        )

    def test_identity_mutations_cover_every_required_binding(self):
        function = {
            "name": "synthetic",
            "statement_range": {
                "end_column": 9,
                "end_line": 12,
                "kind": "compiler_statement_extent",
                "start_column": 1,
                "start_line": 8,
            },
        }
        statement = {"column": 5, "line": 10}
        base = flows.make_identity_flow(
            "ihk", "synthetic.c", "a" * 64, "b" * 64, "c" * 64,
            function, ["external:synthetic"], statement,
            "provider_return_candidate", {"kind": "external_provider"},
            "return ret;",
        )
        mutations = []
        mutated_function = dict(function)
        mutated_function["statement_range"] = dict(function["statement_range"])
        mutated_function["statement_range"]["end_line"] = 13
        mutations.append(
            flows.make_identity_flow(
                "ihk", "synthetic.c", "a" * 64, "b" * 64, "c" * 64,
                mutated_function, ["external:synthetic"], statement,
                "provider_return_candidate", {"kind": "external_provider"},
                "return ret;",
            )
        )
        mutations.extend(
            [
                flows.make_identity_flow(
                    "ihk", "synthetic.c", "a" * 64, "b" * 64, "d" * 64,
                    function, ["external:synthetic"], statement,
                    "provider_return_candidate", {"kind": "external_provider"},
                    "return ret;",
                ),
                flows.make_identity_flow(
                    "ihk", "synthetic.c", "a" * 64, "b" * 64, "c" * 64,
                    function, ["callback:synthetic"], statement,
                    "provider_return_candidate", {"kind": "external_provider"},
                    "return ret;",
                ),
                flows.make_identity_flow(
                    "ihk", "synthetic.c", "a" * 64, "b" * 64, "c" * 64,
                    function, ["external:synthetic"], statement,
                    "callback_return_candidate", {"kind": "external_provider"},
                    "return ret;",
                ),
            ]
        )
        self.assertEqual(len({base["id"]} | {item["id"] for item in mutations}), 5)

    def test_ids_are_stable_and_bind_source_profile_range_roots_and_provenance(self):
        first = self.analyze()
        second = self.analyze()
        self.assertEqual(
            [item["id"] for item in first["flows"]],
            [item["id"] for item in second["flows"]],
        )
        changed_source = self.analyze(source_sha256="c" * 64)
        changed_profile = self.analyze(profile="d" * 64)
        self.assertNotEqual(
            [item["id"] for item in first["flows"]],
            [item["id"] for item in changed_source["flows"]],
        )
        self.assertNotEqual(
            [item["id"] for item in first["flows"]],
            [item["id"] for item in changed_profile["flows"]],
        )
        for item in first["flows"]:
            self.assertRegex(item["id"], r"^HFF-[0-9A-F]{24}$")
            self.assertRegex(item["identity_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(item["provenance_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(item["function_range"]["kind"], "compiler_statement_extent")
            self.assertTrue(item["reachable_entry_roots"])

    def test_ir_provenance_is_normalized_and_all_functions_are_compiler_roots(self):
        ir = self.compile_ir()
        self.assertNotIn(str(self.root), "\n".join(ir["analysis_argv"]))
        for name in ("cfg", "ssa", "cgraph"):
            self.assertRegex(ir["dumps"][name]["normalized_sha256"], r"^[0-9a-f]{64}$")
        analysis = self.analyze()
        self.assertEqual(
            {item["name"] for item in analysis["functions"]},
            {
                "provider_forward",
                "translated_pointer",
                "encoded_pointer",
                "explicit_errno",
                "repeated_errno",
                "comment_safe",
            },
        )
        for function in analysis["functions"]:
            self.assertIn(
                "external:{0}".format(function["name"]),
                function["reachable_entry_roots"],
            )

    def test_callback_address_taken_is_an_entry_root(self):
        callback_source = self.root / "callback.c"
        callback_source.write_text(
            "static int callback(void) { return -5; }\n"
            "int (*slot)(void) = callback;\n"
            "int entry(void) { return slot(); }\n",
            encoding="utf-8",
        )
        argv = [shutil.which("gcc"), "-c", str(callback_source), "-o", str(self.root / "x.o")]
        ir = flows.run_ir_for_source(argv, 2, self.root, self.roots)
        props = flows.parse_cgraph(ir["dumps"]["cgraph"]["raw_bytes"])
        self.assertTrue(props["callback"]["definition"])
        self.assertTrue(props["callback"]["address_taken"])


class WriterTests(unittest.TestCase):
    def test_atomic_writer_is_canonical_valid_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "nested/capture.json"
            flows.write_capture(output, {"z": 2, "a": 1})
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {"a": 1, "z": 2})
            self.assertTrue(output.read_text(encoding="utf-8").startswith('{\n  "a"'))


if __name__ == "__main__":
    unittest.main()
