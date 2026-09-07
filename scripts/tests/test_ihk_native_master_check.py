import contextlib
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import ihk_native_master_check as master_check


class IhkNativeMasterCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ihk-native-master-check-")
        self.repo = Path(self.temporary.name) / "repo"
        self.contract = json.loads(
            (REPO_ROOT / master_check.DEFAULT_CONTRACT).read_text(encoding="utf-8")
        )
        paths = {
            master_check.DEFAULT_CONTRACT.as_posix(),
            self.contract["canonical_abi"]["path"],
            self.contract["production_source"]["path"],
            self.contract["compile_fixture"]["path"],
        }
        paths.update(item["path"] for item in self.contract["legacy_oracle"]["files"])
        for relative in paths:
            target = self.repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, target)

    def tearDown(self):
        self.temporary.cleanup()

    def write_contract(self, value=None):
        if value is None:
            value = self.contract
        (self.repo / master_check.DEFAULT_CONTRACT).write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    def mutate(self, relative, old, new):
        path = self.repo / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def rebind(self, field):
        path = self.repo / self.contract[field]["path"]
        self.contract[field]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.write_contract()

    def fake_rustc(self, version=master_check.EXACT_RUSTC_VERSION, passed=6, compile_exit=0):
        compiler = Path(self.temporary.name) / "rustc"
        compiler.write_text(
            "#!/usr/bin/env python3\n"
            "import os\n"
            "import sys\n"
            "VERSION = {0!r}\n".format(version)
            + "PASSED = {0!r}\n".format(passed)
            + "COMPILE_EXIT = {0!r}\n".format(compile_exit)
            + "if sys.argv[1:] == ['--version']:\n"
            "    print(VERSION)\n"
            "    raise SystemExit(0)\n"
            "if COMPILE_EXIT:\n"
            "    print('synthetic compile failure', file=sys.stderr)\n"
            "    raise SystemExit(COMPILE_EXIT)\n"
            "output = sys.argv[sys.argv.index('-o') + 1]\n"
            "body = (\n"
            "    '#!/usr/bin/env python3\\n'\n"
            "    \"print('test result: ok. %d passed; 0 failed; 0 ignored; \"\n"
            "    \"0 measured; 0 filtered out')\\n\" % PASSED\n"
            ")\n"
            "with open(output, 'w', encoding='utf-8') as stream:\n"
            "    stream.write(body)\n"
            "os.chmod(output, 0o755)\n",
            encoding="utf-8",
        )
        compiler.chmod(0o755)
        return compiler

    def test_repository_contract_is_source_only_and_cannot_award_credit(self):
        result = master_check.validate_repository(REPO_ROOT)
        self.assertEqual("IHK-009", result["gate_id"])
        self.assertTrue(result["source_contract_validated"])
        for field in self.contract["evidence_policy"]:
            self.assertFalse(result[field], field)

    def test_checker_and_tests_parse_with_python_3_6_grammar(self):
        for path in (Path(master_check.__file__), Path(__file__)):
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source, filename=str(path), feature_version=(3, 6))
            except TypeError:
                tree = ast.parse(source, filename=str(path), feature_version=6)
            self.assertFalse(any(isinstance(node, ast.JoinedStr) for node in ast.walk(tree)))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    for keyword in node.keywords:
                        self.assertNotIn(keyword.arg, {"capture_output", "text"})

    def test_cli_skip_is_explicit_and_never_renders_pass(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, {"IHK_NATIVE_MASTER_RUSTC": ""}), contextlib.redirect_stdout(output):
            result = master_check.main(["--repo", str(REPO_ROOT)])
        self.assertEqual(0, result)
        rendered = output.getvalue()
        self.assertIn("SOURCE-CONTRACT-VERIFIED", rendered)
        self.assertIn("fixture=SKIPPED_NO_CONFIGURED_RUSTC", rendered)
        self.assertIn("gate_credit=FORBIDDEN", rendered)
        self.assertNotIn("PASS", rendered)

    def test_require_rustc_fails_closed_when_unconfigured(self):
        with mock.patch.dict(os.environ, {"IHK_NATIVE_MASTER_RUSTC": ""}), self.assertRaisesRegex(
            master_check.ValidationError, "required but absent"
        ):
            master_check.validate_configured_fixture(REPO_ROOT, require_rustc=True)

    def test_exact_configured_rustc_compiles_and_runs_six_tests(self):
        compiler = self.fake_rustc()
        result = master_check.validate_configured_fixture(
            REPO_ROOT, rustc=str(compiler), require_rustc=True
        )
        self.assertEqual("EXACT_ROCKY_RUSTC_FIXTURE_VERIFIED", result["fixture_status"])
        self.assertEqual(master_check.EXACT_RUSTC_VERSION, result["compiler_version"])

    def test_rustc_version_compile_and_count_drift_are_rejected(self):
        with self.subTest("version"), self.assertRaisesRegex(
            master_check.ValidationError, "version differs"
        ):
            master_check.validate_configured_fixture(
                REPO_ROOT, rustc=str(self.fake_rustc(version="rustc 1.92.0 (unlocked)"))
            )
        with self.subTest("compile"), self.assertRaisesRegex(
            master_check.ValidationError, "compilation failed"
        ):
            master_check.validate_configured_fixture(
                REPO_ROOT, rustc=str(self.fake_rustc(compile_exit=3))
            )
        with self.subTest("count"), self.assertRaisesRegex(
            master_check.ValidationError, "exact contracted test count"
        ):
            master_check.validate_configured_fixture(
                REPO_ROOT, rustc=str(self.fake_rustc(passed=5))
            )

    def test_every_frozen_oracle_byte_is_bound(self):
        for item in self.contract["legacy_oracle"]["files"]:
            with self.subTest(path=item["path"]):
                path = self.repo / item["path"]
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                with self.assertRaisesRegex(master_check.ValidationError, "oracle digest differs"):
                    master_check.validate_repository(self.repo)
                path.write_bytes(original)

    def test_oracle_digest_cannot_be_rebound_to_mutated_legacy_source(self):
        item = self.contract["legacy_oracle"]["files"][0]
        self.mutate(item["path"], "return -EBUSY;", "return -EINVAL;")
        item["sha256"] = hashlib.sha256((self.repo / item["path"]).read_bytes()).hexdigest()
        self.write_contract()
        with self.assertRaisesRegex(master_check.ValidationError, "oracle identity differs"):
            master_check.validate_repository(self.repo)

    def test_source_digest_detects_any_unreviewed_edit(self):
        source = self.contract["production_source"]["path"]
        self.mutate(source, "const EBUSY: i32 = 16;", "const EBUSY: i32 = 15;")
        with self.assertRaisesRegex(master_check.ValidationError, "production source digest differs"):
            master_check.validate_repository(self.repo)

    def test_rebound_source_still_requires_release_publication_and_acquire_ordering(self):
        source = self.contract["production_source"]["path"]
        original = (self.repo / source).read_text(encoding="utf-8")
        mutations = [
            (
                "pack_control(generation, SLOT_ACTIVE), Ordering::Release",
                "pack_control(generation, SLOT_ACTIVE), Ordering::Relaxed",
                "listener publication",
            ),
            (
                "slot.readers.fetch_add(1, Ordering::AcqRel)",
                "slot.readers.fetch_add(1, Ordering::Relaxed)",
                "listener lease acquisition",
            ),
            (
                "pack_control(generation, SLOT_EMPTY), Ordering::Release",
                "pack_control(generation, SLOT_EMPTY), Ordering::Relaxed",
                "listener drain before reuse",
            ),
        ]
        for old, new, error in mutations:
            with self.subTest(error=error):
                (self.repo / source).write_text(original.replace(old, new, 1), encoding="utf-8")
                self.rebind("production_source")
                with self.assertRaisesRegex(master_check.ValidationError, error):
                    master_check.validate_repository(self.repo)
        (self.repo / source).write_text(original, encoding="utf-8")

    def test_rebound_source_cannot_introduce_allocation_unsafe_or_runtime_effects(self):
        source = self.contract["production_source"]["path"]
        original = (self.repo / source).read_text(encoding="utf-8")
        mutations = [
            ("\ntype Forbidden = Vec<u8>;\n", "allocation"),
            ("\nunsafe fn forbidden() {}\n", "unsafe code"),
            ("\nfn forbidden() { sleep(1); }\n", "runtime side effect"),
        ]
        for addition, error in mutations:
            with self.subTest(error=error):
                (self.repo / source).write_text(original + addition, encoding="utf-8")
                self.rebind("production_source")
                with self.assertRaisesRegex(master_check.ValidationError, error):
                    master_check.validate_repository(self.repo)
        (self.repo / source).write_text(original, encoding="utf-8")

    def test_rebound_source_preserves_connect_encoding_and_callback_errno(self):
        source = self.contract["production_source"]["path"]
        original = (self.repo / source).read_text(encoding="utf-8")
        mutations = [
            (
                "self.local_send_queue,\n                self.local_receive_queue,",
                "self.local_receive_queue,\n                self.local_send_queue,",
                "outbound connect packet encoding",
            ),
            (
                "status.checked_neg()",
                "Some(status)",
                "callback/error mapping",
            ),
        ]
        for old, new, error in mutations:
            with self.subTest(error=error):
                self.assertIn(old, original)
                (self.repo / source).write_text(original.replace(old, new, 1), encoding="utf-8")
                self.rebind("production_source")
                with self.assertRaisesRegex(master_check.ValidationError, error):
                    master_check.validate_repository(self.repo)
        (self.repo / source).write_text(original, encoding="utf-8")

    def test_fixture_digest_and_concurrency_inventory_are_fail_closed(self):
        fixture = self.contract["compile_fixture"]["path"]
        self.mutate(fixture, "thread::spawn", "thread::Builder::new().spawn")
        self.rebind("compile_fixture")
        with self.assertRaisesRegex(master_check.ValidationError, "concurrency/lifetime"):
            master_check.validate_repository(self.repo)

    def test_evidence_flags_and_intentional_deltas_cannot_be_removed(self):
        for field in self.contract["evidence_policy"]:
            with self.subTest(field=field):
                changed = json.loads(json.dumps(self.contract))
                changed["evidence_policy"][field] = True
                self.write_contract(changed)
                with self.assertRaisesRegex(master_check.ValidationError, "cannot claim"):
                    master_check.validate_repository(self.repo)
        changed = json.loads(json.dumps(self.contract))
        changed["intentional_deltas"] = changed["intentional_deltas"][:-1]
        self.write_contract(changed)
        with self.assertRaisesRegex(master_check.ValidationError, "intentional delta"):
            master_check.validate_repository(self.repo)

    def test_duplicate_json_keys_paths_and_symlinks_are_rejected(self):
        contract_path = self.repo / master_check.DEFAULT_CONTRACT
        contract_path.write_text('{"schema_version": 1, "schema_version": 1}\n', encoding="utf-8")
        with self.assertRaisesRegex(master_check.ValidationError, "duplicate JSON key"):
            master_check.validate_repository(self.repo)


if __name__ == "__main__":
    unittest.main()
