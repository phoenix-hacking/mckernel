import ast
import contextlib
import errno
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent / "fixtures/native-lifecycle-model-v1"
FILES = {"README.md", "model.rs", "reference.c", "vectors.json", "expected.json", "harness.py"}
REQUIRED = {
    "preparation-abort", "assigned-tid-abort", "late-clone-abort", "immediate-exit",
    "tid-reuse", "thread-only-exit", "last-thread-exit", "competing-group-orders",
    "inherited-status", "duplicate-terminal", "retained-thread-ref",
    "retained-process-ref", "authority-revoked",
    "ref-resurrection", "zombie-before-after-reap",
    "main-storage-held", "live-sibling-retirement", "vm-held", "launcher-loss",
    "teardown-failure", "buffer-full", "counter-overflow", "attempt-counter-overflow",
    "unfinished-reservation",
    "missing-birth", "missing-end", "active-tid-alias",
    "birth-after-runnable",
    "wrong-raw-terminal", "wrong-capture", "wrong-os-generation",
    "wrong-application", "wrong-process", "wrong-exec", "wrong-domain",
    "application-limit", "process-limit", "thread-limit",
    "end-after-complete-end", "end-after-incomplete-end",
    "operation-after-end", "wrong-key-after-end",
    "launcher-loss-after-end", "teardown-fail-after-end",
}
RAW_ORIGINAL_REQUIRED = {
    "raw-duplicate-key", "raw-nonfinite", "raw-trailing-object",
    "raw-embedded-nul", "raw-129-operations", "raw-oversized-document",
    "raw-unknown-pool", "raw-cyclic-pool", "raw-excess-pool-args",
}
RAW_AUTHORITY_REQUIRED = {
    "raw-authority-retire-a", "raw-authority-retire-b",
    "raw-authority-retire-c", "raw-authority-retire-d",
    "raw-authority-extra-operation-field",
    "raw-authority-extra-vector-field", "raw-authority-unknown-operation",
}
RAW_WIDTH_REQUIRED = {
    "raw-pid-zero", "raw-pid-int32-overflow", "raw-pid-negative",
    "raw-pid-u64-overflow", "raw-pid-integral-float",
    "raw-pid-fractional-float", "raw-pid-boolean", "raw-pid-string",
    "raw-pid-null", "raw-tid-alloc-int32-overflow",
    "raw-tid-assign-zero", "raw-tid-assign-int32-overflow",
}
RAW_DOCUMENT_REQUIRED = {
    "raw-json-truncated", "raw-document-nonobject", "raw-top-missing-field",
    "raw-top-unknown-field", "raw-schema-version-wrong",
    "raw-schema-version-boolean", "raw-schema-version-integral-float",
    "raw-model-only-false", "raw-model-only-integer",
    "raw-corpus-complete-nonboolean", "raw-vectors-nonarray",
    "raw-vector-nonobject", "raw-vector-missing-field",
    "raw-vector-name-empty", "raw-vector-name-nonstring",
    "raw-vector-name-duplicate", "raw-coverage-nonarray",
    "raw-coverage-empty", "raw-coverage-nonstring",
    "raw-coverage-empty-string", "raw-coverage-duplicate",
    "raw-seed-unknown", "raw-seed-nonstring", "raw-operations-nonarray",
    "raw-operations-empty", "raw-operation-nonarray", "raw-operation-short",
    "raw-operation-nonstring-name", "raw-id-zero", "raw-id-gap",
}
RAW_KEY_DOMAIN_REQUIRED = {
    "raw-key-capture-zero", "raw-key-os-generation-zero",
    "raw-key-application-zero", "raw-key-process-zero", "raw-key-exec-zero",
    "raw-key-slot-negative", "raw-key-slot-u64-overflow",
    "raw-key-slot-boolean", "raw-key-slot-fractional",
    "raw-key-slot-string", "raw-key-slot-null",
    "raw-process-subject-thread-domain", "raw-thread-subject-process-domain",
    "raw-subject-null", "raw-subject-scalar", "raw-subject-short",
    "raw-subject-long", "raw-thread-parent-null", "raw-thread-parent-scalar",
    "raw-thread-parent-short", "raw-thread-parent-long",
    "raw-thread-parent-thread-domain", "raw-process-unexpected-parent",
    "raw-tid-assign-unexpected-parent", "raw-capture-subject",
    "raw-capture-parent", "raw-capacity-boolean", "raw-capacity-overflow",
    "raw-abort-stage-zero", "raw-abort-stage-overflow",
}
RAW_POOL_REQUIRED = {
    "raw-pool-map-array", "raw-pool-empty-definition-name",
    "raw-pool-reference-missing-field", "raw-pool-reference-extra-field",
    "raw-pool-reference-name-integer", "raw-pool-args-null",
    "raw-pool-required-args-omitted", "raw-pool-nonzero-arity-excess",
    "raw-pool-placeholder-negative", "raw-pool-placeholder-boolean",
    "raw-pool-placeholder-integral-float", "raw-pool-placeholder-string",
    "raw-pool-placeholder-extra-field", "raw-pool-placeholder-unbound",
    "raw-pool-unused-unknown-reference", "raw-pool-unused-self-cycle",
    "raw-pool-unused-arity-excess", "raw-pool-unused-mutual-cycle",
    "raw-pool-unused-dependency-33-leaf-first",
    "raw-pool-unused-dependency-33-root-first",
    "raw-pool-unused-syntax-depth-33", "raw-pool-expanded-byte-budget-over",
}
RAW_ENVELOPE_REQUIRED = {
    "raw-raw-invalid-nonarray", "raw-mutants-nonobject",
    "raw-nested-raw-invalid",
}
RAW_OPERATION_ARGUMENT_REQUIRED = {
    "raw-operation-id-overflow", "raw-operation-id-fractional",
    "raw-main-flag-overflow", "raw-terminal-raw-overflow",
    "raw-terminal-status-overflow", "raw-terminal-signal-overflow",
    "raw-terminal-branch-zero", "raw-terminal-branch-overflow",
    "raw-unused-p-alloc-b", "raw-unused-p-alloc-c", "raw-unused-p-alloc-d",
    "raw-unused-t-alloc-c", "raw-unused-t-alloc-d",
    "raw-unused-tid-assign-b", "raw-unused-tid-assign-c",
    "raw-unused-tid-assign-d", "raw-unused-abort-b",
    "raw-unused-abort-c", "raw-unused-abort-d",
}
RAW_EXPANDED_NODE_REQUIRED = {"raw-pool-expanded-node-budget-over"}
RAW_EXPANDED_DEPTH_REQUIRED = {"raw-pool-expanded-depth-over"}
RAW_PREFLIGHT_AGGREGATE_BYTE_REQUIRED = {
    "raw-pool-preflight-aggregate-byte-over",
}
RAW_PREFLIGHT_AGGREGATE_NODE_REQUIRED = {
    "raw-pool-preflight-aggregate-node-over",
}
RAW_KEY_CAPTURE_U64_REQUIRED = {"raw-key-capture-u64-overflow"}
RAW_REQUIRED = (RAW_ORIGINAL_REQUIRED | RAW_AUTHORITY_REQUIRED |
                RAW_WIDTH_REQUIRED | RAW_DOCUMENT_REQUIRED |
                RAW_KEY_DOMAIN_REQUIRED | RAW_POOL_REQUIRED |
                RAW_ENVELOPE_REQUIRED | RAW_OPERATION_ARGUMENT_REQUIRED |
                RAW_EXPANDED_NODE_REQUIRED | RAW_EXPANDED_DEPTH_REQUIRED |
                RAW_PREFLIGHT_AGGREGATE_BYTE_REQUIRED |
                RAW_PREFLIGHT_AGGREGATE_NODE_REQUIRED |
                RAW_KEY_CAPTURE_U64_REQUIRED)
RAW_ACCEPTED_28_TEXT_SHA256 = "ad5400098498a5805691e0017f15152f75a540812c6f6cd67fd2318c3abd39c4"

class NativeLifecycleModelSourceTests(unittest.TestCase):
    def test_exact_packet_and_labels(self):
        self.assertEqual({path.name for path in HERE.iterdir() if path.is_file()}, FILES)
        for name in ("README.md", "model.rs", "reference.c", "harness.py"):
            self.assertIn("MODEL_ONLY", (HERE / name).read_text())

    def test_python_syntax_and_named_coverage(self):
        ast.parse((HERE / "harness.py").read_text())
        vectors = json.loads((HERE / "vectors.json").read_text())
        expected = json.loads((HERE / "expected.json").read_text())
        self.assertEqual(vectors["schema_version"], 2)
        self.assertTrue(vectors["model_only"] and expected["model_only"])
        names = {vector["name"] for vector in vectors["vectors"]}
        self.assertTrue(names <= REQUIRED)
        if vectors["corpus_complete"]:
            self.assertEqual(names, REQUIRED)
        else:
            self.assertIn("immediate-exit", names)
        self.assertEqual(names, set(expected["vectors"]))
        raw_names = {record["name"] for record in vectors["raw_invalid"]}
        self.assertEqual(raw_names, RAW_REQUIRED)
        self.assertTrue(raw_names.isdisjoint(names))
        self.assertEqual(vectors["mutants"], {
            "birth-after-runnable": "birth-after-runnable",
            "early-retirement": "retained-thread-ref",
            "silent-loss": "buffer-full",
            "tid-aliasing": "active-tid-alias",
        })

    def test_separate_registries_and_no_production_wiring(self):
        rust = (HERE / "model.rs").read_text()
        cref = (HERE / "reference.c").read_text()
        for token in ("ProcessRow", "ThreadRow", "ExclusiveUnpublished", "full_key"):
            self.assertIn(token, rust)
        for token in ("process_row", "thread_row", "EXCLUSIVE_UNPUBLISHED", "full_key"):
            self.assertIn(token, cref)
        combined = rust + cref
        for forbidden in ("host_schedule_process", "do_fork", "do_exit", "runq_add_thread", "mcctrl"):
            self.assertNotIn(forbidden, combined)

class NativeLifecycleRawDecoderTests(unittest.TestCase):
    @staticmethod
    def harness_module():
        spec = importlib.util.spec_from_file_location("native_lifecycle_harness", HERE / "harness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def decoder(raw):
        return subprocess.run(
            [sys.executable, str(HERE / "harness.py"), "--decode-raw-document"],
            input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=5, check=False,
        )

    @staticmethod
    def document(operations, pools=None):
        return {
            "schema_version": 2,
            "model_only": True,
            "corpus_complete": False,
            "pools": pools or {},
            "vectors": [{
                "name": "valid", "coverage": ["valid"],
                "event_capacity": 256, "seed": "NONE",
                "operations": operations,
            }],
            "raw_invalid": [],
            "mutants": {},
        }

    def assert_decode(self, document, code):
        raw = json.dumps(document, separators=(",", ":")).encode()
        result = self.decoder(raw)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (code, b"", b""))

    def test_positive_decoder_boundaries(self):
        end = [1, "CAPTURE_END", None, None, 0, 0, 0, 0]
        self.assert_decode(self.document({"pool": "O"}, {"O": [end]}), 0)
        self.assert_decode(self.document({"pool": "O", "args": []}, {"O": [end]}), 0)
        self.assert_decode(self.document({"pool": "A", "args": [end]},
                                           {"A": [{"arg": 0}]}), 0)
        operations = [[index, "CAPTURE_END", None, None, 0, 0, 0, 0]
                      for index in range(1, 129)]
        self.assert_decode(self.document(operations), 0)

        process = [1, 0, 1, 1, 1, 0, 1]
        thread = [1, 0, 1, 1, 1, 1, 1]
        end = lambda index: [index, "CAPTURE_END", None, None, 0, 0, 0, 0]
        p_base = [[1, "P_ALLOC", process, None, 100, 0, 0, 0], end(2)]
        t_base = [p_base[0], [2, "T_ALLOC", thread, process, 200, 1, 0, 0], end(3)]
        a_base = [p_base[0], [2, "T_ALLOC", thread, process, 0, 1, 0, 0],
                  [3, "TID_ASSIGN", thread, None, 200, 0, 0, 0], end(4)]
        f_base = [p_base[0], [2, "T_ALLOC", thread, process, 0, 1, 0, 0],
                  [3, "ABORT", thread, None, 1, 0, 0, 0],
                  [4, "RETIRE_BEGIN", thread, None, 0, 0, 0, 0], end(5)]
        for base in (p_base, t_base, a_base, f_base):
            self.assert_decode(self.document(base), 0)
        for pid in (1, (1 << 31) - 1):
            operations = json.loads(json.dumps(p_base)); operations[0][4] = pid
            self.assert_decode(self.document(operations), 0)
        for tid in (0, 1, (1 << 31) - 1):
            operations = json.loads(json.dumps(t_base)); operations[1][4] = tid
            self.assert_decode(self.document(operations), 0)
        for tid in (1, (1 << 31) - 1):
            operations = json.loads(json.dumps(a_base)); operations[2][4] = tid
            self.assert_decode(self.document(operations), 0)

        def raw_positive(operations):
            document = self.document(operations)
            document["vectors"][0]["name"] = "raw-base"
            document["vectors"][0]["coverage"] = ["raw-base"]
            return document
        self.assert_decode(raw_positive([end(1)]), 0)
        complete = raw_positive([end(1)]); complete["corpus_complete"] = True
        self.assert_decode(complete, 0)
        two = raw_positive([end(1)])
        second = json.loads(json.dumps(two["vectors"][0])); second["name"] = "raw-other"
        two["vectors"].append(second)
        self.assert_decode(two, 0)
        coverage = raw_positive([end(1)])
        coverage["vectors"][0]["coverage"] = ["raw-base", "second"]
        self.assert_decode(coverage, 0)
        self.assert_decode(raw_positive([
            [1, "LAUNCHER_LOSS", None, None, 0, 0, 0, 0], end(2)]), 0)

    def test_authority_width_payloads_are_exact_single_mutations(self):
        vectors = json.loads((HERE / "vectors.json").read_text())
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        self.assertTrue(RAW_ORIGINAL_REQUIRED <= set(records))
        self.assertEqual(set(records) & (RAW_AUTHORITY_REQUIRED | RAW_WIDTH_REQUIRED),
                         RAW_AUTHORITY_REQUIRED | RAW_WIDTH_REQUIRED)

        process = [1, 0, 1, 1, 1, 0, 1]
        thread = [1, 0, 1, 1, 1, 1, 1]
        end = lambda index: [index, "CAPTURE_END", None, None, 0, 0, 0, 0]
        bases = {
            "P": [[1, "P_ALLOC", process, None, 100, 0, 0, 0], end(2)],
            "T": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 200, 1, 0, 0], end(3)],
            "A": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 0, 1, 0, 0],
                  [3, "TID_ASSIGN", thread, None, 200, 0, 0, 0], end(4)],
            "F": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 0, 1, 0, 0],
                  [3, "ABORT", thread, None, 1, 0, 0, 0],
                  [4, "RETIRE_BEGIN", thread, None, 0, 0, 0, 0], end(5)],
        }
        def raw_document(operations):
            document = self.document(operations)
            document["vectors"][0]["name"] = "raw-base"
            document["vectors"][0]["coverage"] = ["raw-base"]
            return document
        expected = {}
        for field in range(4):
            operations = json.loads(json.dumps(bases["F"])); operations[3][4 + field] = 1
            expected[f"raw-authority-retire-{'abcd'[field]}"] = raw_document(operations)
        operations = json.loads(json.dumps(bases["F"])); operations[3].append("E")
        expected["raw-authority-extra-operation-field"] = raw_document(operations)
        document = raw_document(json.loads(json.dumps(bases["F"])))
        document["vectors"][0]["authority"] = "E"
        expected["raw-authority-extra-vector-field"] = document
        operations = json.loads(json.dumps(bases["F"])); operations[3][1] = "SET_AUTHORITY"
        expected["raw-authority-unknown-operation"] = raw_document(operations)
        pid_values = [0, 1 << 31, -1, 1 << 64, 1.0, 1.5, True, "100", None]
        pid_suffixes = ["zero", "int32-overflow", "negative", "u64-overflow",
                        "integral-float", "fractional-float", "boolean", "string", "null"]
        for suffix, value in zip(pid_suffixes, pid_values):
            operations = json.loads(json.dumps(bases["P"])); operations[0][4] = value
            expected[f"raw-pid-{suffix}"] = raw_document(operations)
        operations = json.loads(json.dumps(bases["T"])); operations[1][4] = 1 << 31
        expected["raw-tid-alloc-int32-overflow"] = raw_document(operations)
        for suffix, value in (("zero", 0), ("int32-overflow", 1 << 31)):
            operations = json.loads(json.dumps(bases["A"])); operations[2][4] = value
            expected[f"raw-tid-assign-{suffix}"] = raw_document(operations)

        self.assertEqual(set(expected), RAW_AUTHORITY_REQUIRED | RAW_WIDTH_REQUIRED)
        for name, document in expected.items():
            record = records[name]
            self.assertEqual(record["source"]["inline_utf8"],
                             json.dumps(document, separators=(",", ":")))
            family = "forged-authority" if name in RAW_AUTHORITY_REQUIRED else "pid-tid-width"
            self.assertEqual(record["coverage"], [family, name])
            self.assertEqual(record["expected"], {
                "stage": "harness", "exit_code": 2,
                "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
            })
        authority_bool = json.loads(json.dumps(expected["raw-authority-retire-a"]))
        authority_bool["vectors"][0]["operations"][3][4] = True
        self.assertNotEqual(
            json.dumps(authority_bool, separators=(",", ":")),
            records["raw-authority-retire-a"]["source"]["inline_utf8"])
        integral_int = json.loads(json.dumps(expected["raw-pid-integral-float"]))
        integral_int["vectors"][0]["operations"][0][4] = 1
        self.assertNotEqual(
            json.dumps(integral_int, separators=(",", ":")),
            records["raw-pid-integral-float"]["source"]["inline_utf8"])

    def test_document_vector_payloads_are_exact_single_mutations(self):
        vector_text = (HERE / "vectors.json").read_bytes().decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(28):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(),
                         RAW_ACCEPTED_28_TEXT_SHA256)
        self.assertNotEqual(hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
                            RAW_ACCEPTED_28_TEXT_SHA256)
        base = {
            "schema_version": 2, "model_only": True, "corpus_complete": False,
            "pools": {}, "vectors": [{
                "name": "raw-base", "coverage": ["raw-base"],
                "event_capacity": 256, "seed": "NONE",
                "operations": [[1, "CAPTURE_END", None, None, 0, 0, 0, 0]],
            }], "raw_invalid": [], "mutants": {},
        }
        expected = {}
        compact = lambda document: json.dumps(document, separators=(",", ":"))
        expected["raw-json-truncated"] = compact(base)[:-1]
        expected["raw-document-nonobject"] = "[]"
        def mutation(name, apply):
            document = json.loads(json.dumps(base)); apply(document)
            expected[name] = compact(document)
        mutation("raw-top-missing-field", lambda d: d.pop("model_only"))
        mutation("raw-top-unknown-field", lambda d: d.update(extra=0))
        mutation("raw-schema-version-wrong", lambda d: d.update(schema_version=3))
        mutation("raw-schema-version-boolean", lambda d: d.update(schema_version=True))
        mutation("raw-schema-version-integral-float", lambda d: d.update(schema_version=2.0))
        mutation("raw-model-only-false", lambda d: d.update(model_only=False))
        mutation("raw-model-only-integer", lambda d: d.update(model_only=1))
        mutation("raw-corpus-complete-nonboolean", lambda d: d.update(corpus_complete=0))
        mutation("raw-vectors-nonarray", lambda d: d.update(vectors={}))
        mutation("raw-vector-nonobject", lambda d: d.update(vectors=[None]))
        mutation("raw-vector-missing-field", lambda d: d["vectors"][0].pop("seed"))
        mutation("raw-vector-name-empty", lambda d: d["vectors"][0].update(name=""))
        mutation("raw-vector-name-nonstring", lambda d: d["vectors"][0].update(name=0))
        mutation("raw-vector-name-duplicate", lambda d: d["vectors"].append(json.loads(json.dumps(d["vectors"][0]))))
        mutation("raw-coverage-nonarray", lambda d: d["vectors"][0].update(coverage="raw-base"))
        mutation("raw-coverage-empty", lambda d: d["vectors"][0].update(coverage=[]))
        mutation("raw-coverage-nonstring", lambda d: d["vectors"][0].update(coverage=[0]))
        mutation("raw-coverage-empty-string", lambda d: d["vectors"][0].update(coverage=[""]))
        mutation("raw-coverage-duplicate", lambda d: d["vectors"][0].update(coverage=["raw-base", "raw-base"]))
        mutation("raw-seed-unknown", lambda d: d["vectors"][0].update(seed="UNKNOWN"))
        mutation("raw-seed-nonstring", lambda d: d["vectors"][0].update(seed=0))
        mutation("raw-operations-nonarray", lambda d: d["vectors"][0].update(operations=None))
        mutation("raw-operations-empty", lambda d: d["vectors"][0].update(operations=[]))
        mutation("raw-operation-nonarray", lambda d: d["vectors"][0].update(operations=[None]))
        mutation("raw-operation-short", lambda d: d["vectors"][0]["operations"][0].pop())
        mutation("raw-operation-nonstring-name", lambda d: d["vectors"][0]["operations"][0].__setitem__(1, 0))
        mutation("raw-id-zero", lambda d: d["vectors"][0]["operations"][0].__setitem__(0, 0))
        mutation("raw-id-gap", lambda d: d["vectors"][0]["operations"][0].__setitem__(0, 2))
        self.assertEqual(set(expected), RAW_DOCUMENT_REQUIRED)
        for name, raw in expected.items():
            record = records[name]
            self.assertEqual(record["source"]["inline_utf8"], raw)
            self.assertEqual(record["coverage"], ["malformed-schema", name])
            self.assertEqual(record["expected"], {
                "stage": "harness", "exit_code": 2,
                "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
            })
        schema_integer = expected["raw-schema-version-integral-float"].replace("2.0", "2", 1)
        self.assertNotEqual(schema_integer,
                            records["raw-schema-version-integral-float"]["source"]["inline_utf8"])

    def test_key_domain_payloads_and_positive_boundaries(self):
        vector_bytes = (HERE / "vectors.json").read_bytes()
        vector_text = vector_bytes.decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(58):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(),
                         "bf14431f328af1b37777352fa70a24055e7824f0b2fd721c386debb1e4c57741")
        self.assertNotEqual(hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
                            "bf14431f328af1b37777352fa70a24055e7824f0b2fd721c386debb1e4c57741")

        process = [1, 0, 1, 1, 1, 0, 1]
        thread = [1, 0, 1, 1, 1, 1, 1]
        end = lambda index: [index, "CAPTURE_END", None, None, 0, 0, 0, 0]
        bases = {
            "P": [[1, "P_ALLOC", process, None, 100, 0, 0, 0], end(2)],
            "T": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 200, 1, 0, 0], end(3)],
            "A": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 0, 1, 0, 0],
                  [3, "TID_ASSIGN", thread, None, 200, 0, 0, 0], end(4)],
            "F": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 0, 1, 0, 0],
                  [3, "ABORT", thread, None, 1, 0, 0, 0],
                  [4, "RETIRE_BEGIN", thread, None, 0, 0, 0, 0], end(5)],
        }
        def raw_document(operations, capacity=256):
            return {
                "schema_version": 2, "model_only": True, "corpus_complete": False,
                "pools": {}, "vectors": [{
                    "name": "raw-base", "coverage": ["raw-base"],
                    "event_capacity": capacity, "seed": "NONE", "operations": operations,
                }], "raw_invalid": [], "mutants": {},
            }
        compact = lambda document: json.dumps(document, separators=(",", ":"))
        expected = {}
        zero_components = (("capture", 0), ("os-generation", 2),
                           ("application", 3), ("process", 4), ("exec", 6))
        for suffix, component in zero_components:
            operations = json.loads(json.dumps(bases["P"])); operations[0][2][component] = 0
            expected[f"raw-key-{suffix}-zero"] = ("full-key", raw_document(operations))
        slot_values = (("negative", -1), ("u64-overflow", 1 << 64),
                       ("boolean", True), ("fractional", 1.5),
                       ("string", "1"), ("null", None))
        for suffix, value in slot_values:
            operations = json.loads(json.dumps(bases["P"])); operations[0][2][1] = value
            expected[f"raw-key-slot-{suffix}"] = ("full-key", raw_document(operations))
        operations = json.loads(json.dumps(bases["P"])); operations[0][2][5] = 1
        expected["raw-process-subject-thread-domain"] = ("domain-parent-shape", raw_document(operations))
        operations = json.loads(json.dumps(bases["T"])); operations[1][2][5] = 0
        expected["raw-thread-subject-process-domain"] = ("domain-parent-shape", raw_document(operations))
        shapes = (("null", None), ("scalar", "P"),
                  ("short", [1, 0, 1, 1, 1, 0]),
                  ("long", [1, 0, 1, 1, 1, 0, 1, 1]))
        for suffix, value in shapes:
            operations = json.loads(json.dumps(bases["P"])); operations[0][2] = value
            expected[f"raw-subject-{suffix}"] = ("domain-parent-shape", raw_document(operations))
            operations = json.loads(json.dumps(bases["T"])); operations[1][3] = value
            expected[f"raw-thread-parent-{suffix}"] = ("domain-parent-shape", raw_document(operations))
        operations = json.loads(json.dumps(bases["T"])); operations[1][3][5] = 1
        expected["raw-thread-parent-thread-domain"] = ("domain-parent-shape", raw_document(operations))
        operations = json.loads(json.dumps(bases["P"])); operations[0][3] = process
        expected["raw-process-unexpected-parent"] = ("domain-parent-shape", raw_document(operations))
        operations = json.loads(json.dumps(bases["A"])); operations[2][3] = process
        expected["raw-tid-assign-unexpected-parent"] = ("domain-parent-shape", raw_document(operations))
        for suffix, field in (("subject", 2), ("parent", 3)):
            operations = json.loads(json.dumps(bases["P"])); operations[1][field] = process
            expected[f"raw-capture-{suffix}"] = ("domain-parent-shape", raw_document(operations))
        for suffix, value in (("boolean", True), ("overflow", 257)):
            expected[f"raw-capacity-{suffix}"] = ("numeric-bounds", raw_document(json.loads(json.dumps(bases["P"])), value))
        for suffix, value in (("zero", 0), ("overflow", 256)):
            operations = json.loads(json.dumps(bases["F"])); operations[2][4] = value
            expected[f"raw-abort-stage-{suffix}"] = ("numeric-bounds", raw_document(operations))
        self.assertEqual(set(expected), RAW_KEY_DOMAIN_REQUIRED)
        for name, (family, document) in expected.items():
            self.assertEqual(records[name]["source"]["inline_utf8"], compact(document))
            self.assertEqual(records[name]["coverage"], [family, name])
            self.assertEqual(records[name]["expected"], {
                "stage": "harness", "exit_code": 2,
                "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
            })
        bool_as_one = json.loads(json.dumps(expected["raw-key-slot-boolean"][1]))
        bool_as_one["vectors"][0]["operations"][0][2][1] = 1
        self.assertNotEqual(compact(bool_as_one),
                            records["raw-key-slot-boolean"]["source"]["inline_utf8"])

        for operations in bases.values():
            self.assert_decode(raw_document(operations), 0)
        for capacity in (0, 256):
            self.assert_decode(raw_document(json.loads(json.dumps(bases["P"])), capacity), 0)
        for stage in (1, 255):
            operations = json.loads(json.dumps(bases["F"])); operations[2][4] = stage
            self.assert_decode(raw_document(operations), 0)
        for slot in (0, (1 << 64) - 1):
            operations = json.loads(json.dumps(bases["P"])); operations[0][2][1] = slot
            self.assert_decode(raw_document(operations), 0)
        for component in (0, 2, 3, 4, 6):
            for value in (1, (1 << 64) - 1):
                operations = json.loads(json.dumps(bases["P"])); operations[0][2][component] = value
                self.assert_decode(raw_document(operations), 0)
                operations = json.loads(json.dumps(bases["T"]))
                operations[0][2][component] = value
                operations[1][2][component] = value
                operations[1][3][component] = value
                self.assert_decode(raw_document(operations), 0)
        for thread_instance in (1, (1 << 64) - 1):
            operations = json.loads(json.dumps(bases["T"])); operations[1][2][5] = thread_instance
            self.assert_decode(raw_document(operations), 0)

    def test_pool_payloads_errors_and_positive_boundaries(self):
        vector_text = (HERE / "vectors.json").read_bytes().decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(88):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        accepted_hash = "40e35683740716530f59cf73e573b03c6bda7bca7d9db4b35b4e17f47fbe1834"
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(), accepted_hash)
        self.assertNotEqual(hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
                            accepted_hash)

        end = [1, "CAPTURE_END", None, None, 0, 0, 0, 0]
        ordinary = [end]
        def document(pools, operations):
            return {
                "schema_version": 2, "model_only": True, "corpus_complete": False,
                "pools": pools, "vectors": [{
                    "name": "pool-base", "coverage": ["pool-base"],
                    "event_capacity": 256, "seed": "NONE", "operations": operations,
                }], "raw_invalid": [], "mutants": {},
            }
        def chain(count):
            result = {"P00": 0}
            for index in range(1, count):
                result[f"P{index:02d}"] = {"pool": f"P{index - 1:02d}"}
            return result
        def nested(depth):
            result = 0
            for _ in range(depth):
                result = [result]
            return result
        cases = {
            "raw-pool-map-array": ([], ordinary, "pools"),
            "raw-pool-empty-definition-name": ({"": 0}, ordinary, "invalid input"),
            "raw-pool-reference-missing-field": ({}, {"args": []}, "pool reference"),
            "raw-pool-reference-extra-field": ({"O": ordinary}, {"pool": "O", "extra": 0}, "pool reference"),
            "raw-pool-reference-name-integer": ({"O": ordinary}, {"pool": 0}, "pool reference"),
            "raw-pool-args-null": ({"I": {"arg": 0}}, {"pool": "I", "args": None}, "pool arity"),
            "raw-pool-required-args-omitted": ({"I": {"arg": 0}}, {"pool": "I"}, "pool arity"),
            "raw-pool-nonzero-arity-excess": ({"I": {"arg": 0}}, {"pool": "I", "args": [ordinary, ordinary]}, "pool arity"),
            "raw-pool-placeholder-negative": ({"U": {"arg": -1}}, ordinary, "placeholder"),
            "raw-pool-placeholder-boolean": ({"U": {"arg": True}}, ordinary, "placeholder"),
            "raw-pool-placeholder-integral-float": ({"U": {"arg": 0.0}}, ordinary, "placeholder"),
            "raw-pool-placeholder-string": ({"U": {"arg": "0"}}, ordinary, "placeholder"),
            "raw-pool-placeholder-extra-field": ({"U": {"arg": 0, "extra": 0}}, ordinary, "pool reference"),
            "raw-pool-placeholder-unbound": ({}, {"arg": 0}, "placeholder"),
            "raw-pool-unused-unknown-reference": ({"U": {"pool": "MISSING"}}, ordinary, "unknown pool"),
            "raw-pool-unused-self-cycle": ({"U": {"pool": "U"}}, ordinary, "pool cycle or dependency depth"),
            "raw-pool-unused-arity-excess": ({"I": {"arg": 0}, "U": {"pool": "I", "args": [ordinary, ordinary]}}, ordinary, "pool arity"),
            "raw-pool-unused-mutual-cycle": ({"A": {"pool": "B"}, "B": {"pool": "A"}}, ordinary, "pool cycle or dependency depth"),
            "raw-pool-unused-dependency-33-leaf-first": (chain(33), ordinary, "pool dependency depth"),
            "raw-pool-unused-dependency-33-root-first": (dict(reversed(list(chain(33).items()))), ordinary, "pool dependency depth"),
            "raw-pool-unused-syntax-depth-33": ({"U": nested(33)}, ordinary, "pool depth"),
            "raw-pool-expanded-byte-budget-over": ({"D": {"arg": 1}}, {"pool": "D", "args": ["x" * 174736, ordinary]}, "expanded literal budget"),
        }
        self.assertEqual(set(cases), RAW_POOL_REQUIRED)
        module = self.harness_module()
        for name, (pools, operations, message) in cases.items():
            raw = json.dumps(document(pools, operations), separators=(",", ":"))
            record = records[name]
            self.assertEqual(record["source"]["inline_utf8"], raw)
            self.assertEqual(record["coverage"], ["pool-validation", name])
            self.assertEqual(record["expected"], {
                "stage": "harness", "exit_code": 2,
                "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
            })
            with self.assertRaises(module.ValidationError) as raised:
                module.decode_raw_document(raw.encode())
            self.assertEqual(str(raised.exception), message)
        self.assertEqual(len(records["raw-pool-expanded-byte-budget-over"]["source"]["inline_utf8"].encode()),
                         175021)

        positives = [
            document({"O": ordinary}, {"pool": "O"}),
            document({"O": ordinary}, {"pool": "O", "args": []}),
            document({"I": {"arg": 0}, "A": {"pool": "I", "args": [{"arg": 0}]}},
                     {"pool": "A", "args": [ordinary]}),
            document({"U": {"arg": 2}}, ordinary),
            document(chain(32), ordinary),
            document(dict(reversed(list(chain(32).items()))), ordinary),
            document({"U": nested(32)}, ordinary),
            document({"D": {"arg": 1}}, {"pool": "D", "args": ["x" * 174735, ordinary]}),
        ]
        self.assertEqual(len(json.dumps(positives[-1], separators=(",", ":")).encode()), 175020)
        for positive in positives:
            self.assert_decode(positive, 0)

    def test_envelope_payloads_and_input_boundaries(self):
        vector_text = (HERE / "vectors.json").read_bytes().decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(110):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        accepted_hash = "e66175e09519434778e8a91df2913cce7afc0c3eab7a0cdd49f8479069f2ccda"
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(), accepted_hash)
        self.assertNotEqual(hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
                            accepted_hash)
        base = {
            "schema_version": 2, "model_only": True, "corpus_complete": False,
            "pools": {}, "vectors": [{
                "name": "raw-base", "coverage": ["raw-base"],
                "event_capacity": 256, "seed": "NONE",
                "operations": [[1, "CAPTURE_END", None, None, 0, 0, 0, 0]],
            }], "raw_invalid": [], "mutants": {},
        }
        compact = lambda document: json.dumps(document, separators=(",", ":"))
        self.assertEqual(len(compact(base).encode()), 245)
        expected = {}
        document = json.loads(json.dumps(base)); document["raw_invalid"] = {}
        expected["raw-raw-invalid-nonarray"] = (document, "raw cases")
        document = json.loads(json.dumps(base)); document["mutants"] = []
        expected["raw-mutants-nonobject"] = (document, "mutants")
        document = json.loads(json.dumps(base)); document["raw_invalid"] = [None]
        expected["raw-nested-raw-invalid"] = (document, "nested raw cases")
        self.assertEqual(set(expected), RAW_ENVELOPE_REQUIRED)
        module = self.harness_module()
        for name, (document, message) in expected.items():
            raw = compact(document)
            self.assertEqual(records[name]["source"]["inline_utf8"], raw)
            self.assertEqual(records[name]["coverage"], ["malformed-schema", name])
            self.assertEqual(records[name]["expected"], {
                "stage": "harness", "exit_code": 2,
                "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
            })
            with self.assertRaises(module.ValidationError) as raised:
                module.decode_raw_document(raw.encode())
            self.assertEqual(str(raised.exception), message)
        base_bytes = compact(base).encode()
        whitespace = b" \t\r\n" + base_bytes + b"\r\n\t "
        self.assertEqual(len(whitespace), 253)
        result = self.decoder(whitespace)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))
        maximum = base_bytes + (b" " * 1048331)
        self.assertEqual(len(maximum), 1 << 20)
        result = self.decoder(maximum)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))
        mutants = json.loads(json.dumps(base)); mutants["mutants"] = {"unused": "unresolved"}
        self.assert_decode(mutants, 0)

    def test_operation_argument_payloads_and_boundaries(self):
        vector_text = (HERE / "vectors.json").read_bytes().decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(113):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        accepted_hash = "0e0112f4463bba6f04d5b1b9ff5b8fa37f8a767bdde3f5b5dfddb92a256fb428"
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(), accepted_hash)
        self.assertNotEqual(hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
                            accepted_hash)

        process = [1, 0, 1, 1, 1, 0, 1]
        thread = [1, 0, 1, 1, 1, 1, 1]
        end = lambda index: [index, "CAPTURE_END", None, None, 0, 0, 0, 0]
        bases = {
            "P": [[1, "P_ALLOC", process, None, 100, 0, 0, 0], end(2)],
            "T": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 200, 1, 0, 0], end(3)],
            "A": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 0, 1, 0, 0],
                  [3, "TID_ASSIGN", thread, None, 200, 0, 0, 0], end(4)],
            "F": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 0, 1, 0, 0],
                  [3, "ABORT", thread, None, 1, 0, 0, 0],
                  [4, "RETIRE_BEGIN", thread, None, 0, 0, 0, 0], end(5)],
            "H": [[1, "P_ALLOC", process, None, 100, 0, 0, 0],
                  [2, "T_ALLOC", thread, process, 200, 1, 0, 0],
                  [3, "TERMINAL", thread, None, 9472, 37, 0, 1], end(4)],
        }
        def raw_document(operations):
            return {
                "schema_version": 2, "model_only": True, "corpus_complete": False,
                "pools": {}, "vectors": [{
                    "name": "raw-base", "coverage": ["raw-base"],
                    "event_capacity": 256, "seed": "NONE", "operations": operations,
                }], "raw_invalid": [], "mutants": {},
            }
        expected = {}
        operations = json.loads(json.dumps(bases["P"])); operations[0][0] = 129
        expected["raw-operation-id-overflow"] = (operations, "integer")
        operations = json.loads(json.dumps(bases["P"])); operations[0][0] = 1.5
        expected["raw-operation-id-fractional"] = (operations, "literal type")
        operations = json.loads(json.dumps(bases["T"])); operations[1][5] = 2
        expected["raw-main-flag-overflow"] = (operations, "thread arguments")
        for suffix, field, value in (
                ("raw-overflow", 4, 1 << 32), ("status-overflow", 5, 256),
                ("signal-overflow", 6, 256), ("branch-zero", 7, 0),
                ("branch-overflow", 7, 5)):
            operations = json.loads(json.dumps(bases["H"])); operations[2][field] = value
            expected[f"raw-terminal-{suffix}"] = (operations, "integer")
        for suffix, field in (("b", 5), ("c", 6), ("d", 7)):
            operations = json.loads(json.dumps(bases["P"])); operations[0][field] = 1
            expected[f"raw-unused-p-alloc-{suffix}"] = (operations, "unused argument")
        for suffix, field in (("c", 6), ("d", 7)):
            operations = json.loads(json.dumps(bases["T"])); operations[1][field] = 1
            expected[f"raw-unused-t-alloc-{suffix}"] = (operations, "thread arguments")
        for suffix, field in (("b", 5), ("c", 6), ("d", 7)):
            operations = json.loads(json.dumps(bases["A"])); operations[2][field] = 1
            expected[f"raw-unused-tid-assign-{suffix}"] = (operations, "unused argument")
            operations = json.loads(json.dumps(bases["F"])); operations[2][field] = 1
            expected[f"raw-unused-abort-{suffix}"] = (operations, "abort arguments")
        self.assertEqual(set(expected), RAW_OPERATION_ARGUMENT_REQUIRED)
        module = self.harness_module()
        for name, (operations, message) in expected.items():
            raw = json.dumps(raw_document(operations), separators=(",", ":"))
            self.assertEqual(records[name]["source"]["inline_utf8"], raw)
            coverage = "numeric-bounds" if name in {
                "raw-operation-id-overflow", "raw-operation-id-fractional",
                "raw-main-flag-overflow", "raw-terminal-raw-overflow",
                "raw-terminal-status-overflow", "raw-terminal-signal-overflow",
                "raw-terminal-branch-zero", "raw-terminal-branch-overflow",
            } else "unused-arguments"
            self.assertEqual(records[name]["coverage"], [coverage, name])
            self.assertEqual(records[name]["expected"], {
                "stage": "harness", "exit_code": 2,
                "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
            })
            with self.assertRaises(module.ValidationError) as raised:
                module.decode_raw_document(raw.encode())
            self.assertEqual(str(raised.exception), message)

        retained_unused = records["raw-unused-p-alloc-b"]["source"]["inline_utf8"]
        for conflated in (True, 1.0):
            operations = json.loads(json.dumps(bases["P"]))
            operations[0][5] = conflated
            candidate = json.dumps(raw_document(operations), separators=(",", ":"))
            self.assertNotEqual(candidate, retained_unused)

        for operations in bases.values():
            self.assert_decode(raw_document(operations), 0)
        for flag in (0, 1):
            operations = json.loads(json.dumps(bases["T"])); operations[1][5] = flag
            self.assert_decode(raw_document(operations), 0)
        for field, values in ((4, (0, (1 << 32) - 1)), (5, (0, 255)),
                              (6, (0, 255)), (7, (1, 2, 3, 4))):
            for value in values:
                operations = json.loads(json.dumps(bases["H"])); operations[2][field] = value
                self.assert_decode(raw_document(operations), 0)

    def test_expanded_node_budget_payload_and_boundary(self):
        vector_text = (HERE / "vectors.json").read_bytes().decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(132):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        accepted_hash = "37d212189d28e761b8ea978c8fdce4ff60e4c06e26ca4f6f316e1be8ab9a3930"
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(), accepted_hash)
        self.assertNotEqual(hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
                            accepted_hash)

        end = [[1, "CAPTURE_END", None, None, 0, 0, 0, 0]]
        zeros = [0] * 255
        def document(remainder):
            argument = [{"pool": "Z"} for _ in range(1019)] + [0] * remainder
            return {
                "schema_version": 2, "model_only": True, "corpus_complete": False,
                "pools": {"D": {"arg": 1}, "Z": zeros},
                "vectors": [{
                    "name": "pool-base", "coverage": ["pool-base"],
                    "event_capacity": 256, "seed": "NONE",
                    "operations": {"pool": "D", "args": [argument, end]},
                }], "raw_invalid": [], "mutants": {},
            }
        compact = lambda value: json.dumps(value, separators=(",", ":"))
        positive_document = document(238)
        negative_document = document(239)
        positive = compact(positive_document)
        negative = compact(negative_document)
        self.assertEqual((len(positive.encode()), len(negative.encode())), (14523, 14525))
        positive_argument = positive_document["vectors"][0]["operations"]["args"][0]
        negative_argument = negative_document["vectors"][0]["operations"]["args"][0]
        self.assertEqual(negative_argument[:-1], positive_argument)
        self.assertEqual(negative_argument[-1], 0)
        record = records["raw-pool-expanded-node-budget-over"]
        self.assertEqual(record["source"]["inline_utf8"], negative)
        self.assertEqual(record["coverage"],
                         ["pool-validation", "raw-pool-expanded-node-budget-over"])
        self.assertEqual(record["expected"], {
            "stage": "harness", "exit_code": 2,
            "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
        })
        module = self.harness_module()
        with self.assertRaises(module.ValidationError) as raised:
            module.decode_raw_document(negative.encode())
        self.assertEqual(str(raised.exception), "expanded literal budget")
        result = self.decoder(positive.encode())
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))

        budget = module.ExpansionBudget()
        expanded = module.literal_expand(
            positive_document["vectors"][0]["operations"],
            positive_document["pools"], budget=budget)
        self.assertEqual(expanded, end)
        self.assertEqual((budget.nodes, budget.bytes), (0, 1572589))

    def test_expanded_argument_depth_payload_and_boundary(self):
        vector_text = (HERE / "vectors.json").read_bytes().decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(133):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        accepted_hash = "7b84246f678c8239edd5fc504b63c2696dc64c0b5a71075cf3d71a493f0c9db8"
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(), accepted_hash)
        self.assertNotEqual(hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
                            accepted_hash)

        end = [[1, "CAPTURE_END", None, None, 0, 0, 0, 0]]
        def nested(depth):
            value = 0
            for _ in range(depth):
                value = [value]
            return value
        def document(depth):
            return {
                "schema_version": 2, "model_only": True, "corpus_complete": False,
                "pools": {"D": {"arg": 1}},
                "vectors": [{
                    "name": "pool-base", "coverage": ["pool-base"],
                    "event_capacity": 256, "seed": "NONE",
                    "operations": {"pool": "D", "args": [nested(depth), end]},
                }], "raw_invalid": [], "mutants": {},
            }
        compact = lambda value: json.dumps(value, separators=(",", ":"))
        positive_document = document(31)
        negative_document = document(32)
        positive = compact(positive_document)
        negative = compact(negative_document)
        self.assertEqual((len(positive.encode()), len(negative.encode())), (346, 348))
        record = records["raw-pool-expanded-depth-over"]
        self.assertEqual(record["source"]["inline_utf8"], negative)
        self.assertEqual(record["coverage"],
                         ["pool-validation", "raw-pool-expanded-depth-over"])
        self.assertEqual(record["expected"], {
            "stage": "harness", "exit_code": 2,
            "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
        })
        module = self.harness_module()
        with self.assertRaises(module.ValidationError) as raised:
            module.decode_raw_document(negative.encode())
        self.assertIs(type(raised.exception), module.ValidationError)
        self.assertEqual(str(raised.exception), "expansion depth")
        result = self.decoder(positive.encode())
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))

        positive_budget = module.ExpansionBudget()
        expanded = module.literal_expand(
            positive_document["vectors"][0]["operations"],
            positive_document["pools"], budget=positive_budget)
        self.assertEqual(expanded, end)
        self.assertEqual((positive_budget.nodes, positive_budget.bytes),
                         (262090, 2096769))
        negative_budget = module.ExpansionBudget()
        with self.assertRaises(module.ValidationError) as raised:
            module.literal_expand(
                negative_document["vectors"][0]["operations"],
                negative_document["pools"], budget=negative_budget)
        self.assertIs(type(raised.exception), module.ValidationError)
        self.assertEqual(str(raised.exception), "expansion depth")
        self.assertEqual((negative_budget.nodes, negative_budget.bytes),
                         (262111, 2097086))
        self.assertEqual(RAW_EXPANDED_DEPTH_REQUIRED,
                         {"raw-pool-expanded-depth-over"})

    def test_preflight_aggregate_byte_payload_and_boundary(self):
        vector_text = (HERE / "vectors.json").read_bytes().decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(134):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        accepted_hash = "bc3f41f0c386c36b9a3ebd69283c619b7b070c9053fe6df00a10a0234c26b2e5"
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(), accepted_hash)
        self.assertNotEqual(hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
                            accepted_hash)

        end = [[1, "CAPTURE_END", None, None, 0, 0, 0, 0]]
        def document(v_length):
            return {
                "schema_version": 2, "model_only": True, "corpus_complete": False,
                "pools": {"U": "u" * 87381, "V": "v" * v_length},
                "vectors": [{
                    "name": "pool-base", "coverage": ["pool-base"],
                    "event_capacity": 256, "seed": "NONE", "operations": end,
                }], "raw_invalid": [], "mutants": {},
            }
        compact = lambda value: json.dumps(value, separators=(",", ":"))
        positive_document = document(87381)
        negative_document = document(87382)
        positive = compact(positive_document)
        negative = compact(negative_document)
        self.assertEqual((len(positive.encode()), len(negative.encode())),
                         (175022, 175023))
        self.assertEqual(positive_document["pools"]["U"], "u" * 87381)
        self.assertEqual(negative_document["pools"]["V"], "v" * 87382)
        self.assertEqual(negative_document["pools"]["V"][:-1],
                         positive_document["pools"]["V"])
        record = records["raw-pool-preflight-aggregate-byte-over"]
        self.assertEqual(record["source"]["inline_utf8"], negative)
        self.assertEqual(record["coverage"],
                         ["pool-validation", "raw-pool-preflight-aggregate-byte-over"])
        self.assertEqual(record["expected"], {
            "stage": "harness", "exit_code": 2,
            "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
        })
        module = self.harness_module()
        real_budget = module.ExpansionBudget
        negative_budgets = []
        def track_negative_budget():
            budget = real_budget()
            negative_budgets.append(budget)
            return budget
        with mock.patch.object(module, "ExpansionBudget", side_effect=track_negative_budget):
            with self.assertRaises(module.ValidationError) as raised:
                module.decode_raw_document(negative.encode())
        self.assertIs(type(raised.exception), module.ValidationError)
        self.assertEqual(str(raised.exception), "expanded literal budget")
        self.assertEqual([(budget.nodes, budget.bytes) for budget in negative_budgets],
                         [(262142, -8)])
        result = self.decoder(positive.encode())
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))

        positive_budgets = []
        def track_positive_budget():
            budget = real_budget()
            positive_budgets.append(budget)
            return budget
        with mock.patch.object(module, "ExpansionBudget", side_effect=track_positive_budget):
            arities = module.analyze_pools(positive_document["pools"])
        self.assertEqual(arities, {"U": 0, "V": 0})
        self.assertEqual([(budget.nodes, budget.bytes) for budget in positive_budgets],
                         [(262142, 4), (262142, 4)])
        self.assertEqual(RAW_PREFLIGHT_AGGREGATE_BYTE_REQUIRED,
                         {"raw-pool-preflight-aggregate-byte-over"})

    def test_preflight_aggregate_node_payload_and_boundary(self):
        vector_path = HERE / "vectors.json"
        vector_text = vector_path.read_bytes().decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(135):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        accepted_hash = "06f71693885dd79faf7edd1c8b5e33e5170bab3ecb6ed93716b603f8e64aee1d"
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(), accepted_hash)
        self.assertNotEqual(hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
                            accepted_hash)

        end = [[1, "CAPTURE_END", None, None, 0, 0, 0, 0]]
        def document(v_length):
            return {
                "schema_version": 2, "model_only": True, "corpus_complete": False,
                "pools": {"U": [0] * 131071, "V": [0] * v_length},
                "vectors": [{
                    "name": "pool-base", "coverage": ["pool-base"],
                    "event_capacity": 256, "seed": "NONE", "operations": end,
                }], "raw_invalid": [], "mutants": {},
            }
        compact = lambda value: json.dumps(value, separators=(",", ":"))
        positive_document = document(131071)
        negative_document = document(131072)
        positive = compact(positive_document)
        negative = compact(negative_document)
        self.assertEqual((len(positive.encode()), len(negative.encode())),
                         (524542, 524544))
        self.assertEqual(len(positive_document["pools"]["U"]), 131071)
        self.assertEqual(len(negative_document["pools"]["V"]), 131072)
        self.assertEqual(negative_document["pools"]["V"][:-1],
                         positive_document["pools"]["V"])
        self.assertEqual(negative_document["pools"]["V"][-1], 0)
        record = records["raw-pool-preflight-aggregate-node-over"]
        self.assertEqual(record["source"]["inline_utf8"], negative)
        self.assertEqual(record["coverage"],
                         ["pool-validation", "raw-pool-preflight-aggregate-node-over"])
        self.assertEqual(record["expected"], {
            "stage": "harness", "exit_code": 2,
            "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
        })
        self.assertEqual(vector_path.stat().st_size, 1014192)
        self.assertLess(vector_path.stat().st_size, 1 << 20)
        module = self.harness_module()
        real_budget = module.ExpansionBudget
        negative_budgets = []
        def track_negative_budget():
            budget = real_budget()
            negative_budgets.append(budget)
            return budget
        with mock.patch.object(module, "ExpansionBudget", side_effect=track_negative_budget):
            with self.assertRaises(module.ValidationError) as raised:
                module.decode_raw_document(negative.encode())
        self.assertIs(type(raised.exception), module.ValidationError)
        self.assertEqual(str(raised.exception), "expanded literal budget")
        self.assertEqual([(budget.nodes, budget.bytes) for budget in negative_budgets],
                         [(-1, 1572864)])
        result = self.decoder(positive.encode())
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))

        positive_budgets = []
        def track_positive_budget():
            budget = real_budget()
            positive_budgets.append(budget)
            return budget
        with mock.patch.object(module, "ExpansionBudget", side_effect=track_positive_budget):
            arities = module.analyze_pools(positive_document["pools"])
        self.assertEqual(arities, {"U": 0, "V": 0})
        self.assertEqual([(budget.nodes, budget.bytes) for budget in positive_budgets],
                         [(0, 1572866), (0, 1572866)])
        self.assertEqual(RAW_PREFLIGHT_AGGREGATE_NODE_REQUIRED,
                         {"raw-pool-preflight-aggregate-node-over"})

    def test_capture_key_u64_boundary_payload(self):
        vector_path = HERE / "vectors.json"
        vector_text = vector_path.read_bytes().decode("utf-8")
        vectors = json.loads(vector_text)
        records = {record["name"]: record for record in vectors["raw_invalid"]}
        self.assertEqual(len(records), 137)
        self.assertEqual(set(records), RAW_REQUIRED)
        position = vector_text.index('"raw_invalid": [') + len('"raw_invalid": [')
        decoder = json.JSONDecoder()
        for index in range(136):
            while vector_text[position] in " \r\n\t,":
                position += 1
            if index == 0:
                accepted_start = position
            _, position = decoder.raw_decode(vector_text, position)
        accepted_bytes = vector_text[accepted_start:position].encode()
        accepted_hash = "f60081f55283820733933c6efba366385ddd3f557d76a6cd7353bd83845ac297"
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(), accepted_hash)
        self.assertNotEqual(
            hashlib.sha256(accepted_bytes.replace(b"\n", b"\r\n", 1)).hexdigest(),
            accepted_hash)

        def document(capture):
            return {
                "schema_version": 2, "model_only": True, "corpus_complete": False,
                "pools": {}, "vectors": [{
                    "name": "raw-base", "coverage": ["raw-base"],
                    "event_capacity": 256, "seed": "NONE",
                    "operations": [
                        [1, "P_ALLOC", [capture, 0, 1, 1, 1, 0, 1],
                         None, 100, 0, 0, 0],
                        [2, "CAPTURE_END", None, None, 0, 0, 0, 0],
                    ],
                }], "raw_invalid": [], "mutants": {},
            }
        compact = lambda value: json.dumps(value, separators=(",", ":"))
        positive_document = document((1 << 64) - 1)
        negative_document = document(1 << 64)
        positive = compact(positive_document)
        negative = compact(negative_document)
        self.assertEqual((len(positive.encode()), len(negative.encode())), (309, 309))
        self.assertEqual(
            (hashlib.sha256(positive.encode()).hexdigest(),
             hashlib.sha256(negative.encode()).hexdigest()),
            ("d160bba3040ad430b156ae007cbb2dcbd1867b59564d1f9ac9d93470346838c4",
             "f3e2178e2cb748c1c9523b0a97c3bd39d7127aaf2450a32d1a98110b1f518443"))
        old_token = "18446744073709551615"
        new_token = "18446744073709551616"
        self.assertEqual(positive.count(old_token), 1)
        self.assertEqual(positive.count(new_token), 0)
        self.assertEqual(positive.replace(old_token, new_token), negative)
        self.assertIs(type(positive_document["vectors"][0]["operations"][0][2][0]), int)
        self.assertIs(type(negative_document["vectors"][0]["operations"][0][2][0]), int)
        positive_operations = compact(positive_document["vectors"][0]["operations"])
        negative_operations = compact(negative_document["vectors"][0]["operations"])
        self.assertEqual((len(positive_operations.encode()),
                          len(negative_operations.encode())), (101, 101))

        record = records["raw-key-capture-u64-overflow"]
        self.assertEqual(record["source"]["inline_utf8"], negative)
        self.assertEqual(record["coverage"],
                         ["full-key", "raw-key-capture-u64-overflow"])
        self.assertEqual(record["expected"], {
            "stage": "harness", "exit_code": 2,
            "stdout_hex": "", "stderr_hex": "", "model_invocations": 0,
        })
        self.assertEqual(vector_path.stat().st_size, 1014192)
        self.assertLess(vector_path.stat().st_size, 1 << 20)
        module = self.harness_module()
        for source in (positive_document, negative_document):
            budget = module.ExpansionBudget()
            expanded = module.literal_expand(
                source["vectors"][0]["operations"], source["pools"], budget=budget)
            self.assertEqual(expanded, source["vectors"][0]["operations"])
            self.assertEqual((budget.nodes, budget.bytes), (262118, 2096853))
        with self.assertRaises(module.ValidationError) as raised:
            module.decode_raw_document(negative.encode())
        self.assertIs(type(raised.exception), module.ValidationError)
        self.assertEqual(str(raised.exception), "integer")
        for source, outcome in ((positive, 0), (negative, 2)):
            result = self.decoder(source.encode())
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (outcome, b"", b""))
        self.assertEqual(RAW_KEY_CAPTURE_U64_REQUIRED,
                         {"raw-key-capture-u64-overflow"})

    def test_one_hundred_thirty_seven_raw_rejections_without_build_inputs(self):
        result = subprocess.run(
            [sys.executable, str(HERE / "harness.py"), "--check-raw-invalid"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False,
        )
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, b"", b""))

    def test_oversized_artifact_binding(self):
        vectors = json.loads((HERE / "vectors.json").read_text())
        record = next(item for item in vectors["raw_invalid"]
                      if item["name"] == "raw-oversized-document")
        description = record["source"]["artifact"]
        path = HERE.parents[3] / description["path"]
        raw = path.read_bytes()
        self.assertEqual(len(raw), description["size"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), description["sha256"])
        self.assertEqual(self.decoder(raw).returncode, 2)

    def test_artifact_metadata_path_and_symlink_rejections(self):
        module = self.harness_module()
        vectors = json.loads((HERE / "vectors.json").read_text())
        record = next(item for item in vectors["raw_invalid"]
                      if item["name"] == "raw-oversized-document")
        description = record["source"]["artifact"]
        with mock.patch.object(module.os, "open", wraps=os.open) as opener:
            retained = module.artifact_bytes(description)
        final_opens = [call for call in opener.call_args_list
                       if call.args and call.args[0] == "oversized-document.json"]
        self.assertEqual(len(final_opens), 1)
        self.assertEqual(hashlib.sha256(retained).hexdigest(), description["sha256"])
        for mutation in (
            {**description, "size": description["size"] - 1},
            {**description, "sha256": "0" * 64},
            {**description, "path": "scripts/tests/fixtures/native-lifecycle-model-v1/../outside"},
        ):
            with self.assertRaises((AssertionError, OSError)):
                module.artifact_bytes(mutation)
        raw_dir = HERE / "raw-invalid"
        with tempfile.TemporaryDirectory(dir=raw_dir) as temporary:
            link = Path(temporary) / "link"
            link.symlink_to(raw_dir / "oversized-document.json")
            relative = link.relative_to(HERE.parents[3]).as_posix()
            with self.assertRaises(OSError):
                module.artifact_bytes({**description, "path": relative})

    def test_child_timeout_and_output_are_not_rejections(self):
        module = self.harness_module()
        real_popen = subprocess.Popen
        children = []
        def capture(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child
        with mock.patch.object(module.subprocess, "Popen", side_effect=capture):
            with self.assertRaises(AssertionError):
                module.bounded_child(
                    [sys.executable, "-c", "import time; time.sleep(10)"], b"")
            self.assertIsNotNone(children[-1].poll())
            with self.assertRaises(AssertionError):
                module.bounded_child(
                    [sys.executable, "-c", "import os; os.write(1, b'x' * 65537)"], b"")
            self.assertIsNotNone(children[-1].poll())

    def test_recursive_raw_and_build_tripwires(self):
        nested = self.document([[1, "CAPTURE_END", None, None, 0, 0, 0, 0]])
        nested["raw_invalid"] = [{
            "name": "nested", "coverage": ["nested"],
            "source": {"inline_utf8": "{}"},
            "expected": {"stage": "harness", "exit_code": 2,
                         "stdout_hex": "", "stderr_hex": "",
                         "model_invocations": 0},
        }]
        self.assert_decode(nested, 2)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"
            module = self.harness_module()
            with mock.patch.object(module, "build", side_effect=RuntimeError("build called")) as build_call, \
                 mock.patch.object(module, "compiler", side_effect=RuntimeError("compiler called")) as compiler_call, \
                 mock.patch.object(module, "run", side_effect=RuntimeError("model called")) as model_call, \
                 mock.patch.object(module, "raw_child", wraps=module.raw_child) as raw_call, \
                 mock.patch.object(sys, "argv", [str(HERE / "harness.py"),
                                                  "--rustc", "/must/not/resolve/rustc",
                                                  "--cc", "/must/not/resolve/cc",
                                                  "--output", str(output)]):
                with self.assertRaises(AssertionError):
                    module.main()
                self.assertEqual(raw_call.call_count, len(RAW_REQUIRED))
                build_call.assert_not_called()
                compiler_call.assert_not_called()
                model_call.assert_not_called()
            self.assertFalse(output.exists())

class NativeLifecycleArtifactFaultTests(unittest.TestCase):
    @staticmethod
    def harness_module():
        spec = importlib.util.spec_from_file_location(
            "native_lifecycle_artifact_harness", HERE / "harness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def artifact_description():
        vectors = json.loads((HERE / "vectors.json").read_text())
        record = next(item for item in vectors["raw_invalid"]
                      if item["name"] == "raw-oversized-document")
        return record["source"]["artifact"]

    def exercise_artifact(self, fault):
        module = self.harness_module()
        description = self.artifact_description()
        artifact = HERE.parents[3] / description["path"]
        before = (artifact.stat().st_mode, artifact.stat().st_size,
                  artifact.stat().st_mtime_ns,
                  hashlib.sha256(artifact.read_bytes()).hexdigest())
        real_open, real_close = module.os.open, module.os.close
        real_fstat, real_read = module.os.fstat, module.os.read
        acquired, closed, outstanding, events = [], [], {}, []
        injected, fstat_calls, read_calls, leaf_opens = [0], [0], [0], [0]

        def tracked_open(path, *args, **kwargs):
            should_inject = ((fault == "component-open" and path == "tests") or
                             (fault == "leaf-open" and path == "oversized-document.json"))
            if should_inject:
                injected[0] += 1
                raise OSError(errno.EIO, "injected artifact I/O")
            descriptor = real_open(path, *args, **kwargs)
            self.assertNotIn(descriptor, outstanding)
            token = (len(acquired), descriptor)
            acquired.append(token)
            outstanding[descriptor] = token
            events.append(("open", token, str(path)))
            if path == "oversized-document.json":
                leaf_opens[0] += 1
            return descriptor

        def tracked_close(descriptor):
            token = outstanding.pop(descriptor)
            closed.append(token)
            events.append(("close", token, None))
            return real_close(descriptor)

        def tracked_fstat(descriptor):
            fstat_calls[0] += 1
            should_inject = ((fault == "initial-fstat" and fstat_calls[0] == 1) or
                             (fault == "final-fstat" and fstat_calls[0] == 2))
            if should_inject:
                injected[0] += 1
                raise OSError(errno.EIO, "injected artifact I/O")
            return real_fstat(descriptor)

        def tracked_read(descriptor, size):
            read_calls[0] += 1
            if fault == "read" and read_calls[0] == 1:
                injected[0] += 1
                raise OSError(errno.EIO, "injected artifact I/O")
            return real_read(descriptor, size)

        unexpected = RuntimeError("unexpected non-artifact action")
        leaked = None
        result = None
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"
            with mock.patch.object(module.os, "open", side_effect=tracked_open), \
                 mock.patch.object(module.os, "close", side_effect=tracked_close), \
                 mock.patch.object(module.os, "fstat", side_effect=tracked_fstat), \
                 mock.patch.object(module.os, "read", side_effect=tracked_read), \
                 mock.patch.object(module.subprocess, "Popen", side_effect=unexpected) as popen_call, \
                 mock.patch.object(module.subprocess, "run", side_effect=unexpected) as subprocess_call, \
                 mock.patch.object(module, "raw_child", side_effect=unexpected) as raw_child_call, \
                 mock.patch.object(module, "build", side_effect=unexpected) as build_call, \
                 mock.patch.object(module, "compiler", side_effect=unexpected) as compiler_call, \
                 mock.patch.object(module, "run", side_effect=unexpected) as model_call:
                try:
                    if fault is None:
                        result = module.artifact_bytes(description)
                    else:
                        with self.assertRaises(OSError) as raised:
                            module.artifact_bytes(description)
                        self.assertIs(type(raised.exception), OSError)
                        self.assertEqual((raised.exception.errno, raised.exception.strerror),
                                         (errno.EIO, "injected artifact I/O"))
                        self.assertEqual(raised.exception.args,
                                         (errno.EIO, "injected artifact I/O"))
                        self.assertEqual(injected[0], 1)
                        self.assertIsNone(result)
                        if fault == "initial-fstat":
                            self.assertEqual(read_calls[0], 0)
                        if fault == "final-fstat":
                            self.assertGreater(read_calls[0], 0)
                finally:
                    leaked = dict(outstanding)
                    try:
                        self.assertEqual(outstanding, {})
                        self.assertEqual(len(acquired), len(closed))
                        self.assertEqual(sorted(acquired), sorted(closed))
                    finally:
                        for descriptor in list(outstanding):
                            real_close(descriptor)
                            outstanding.pop(descriptor)
                popen_call.assert_not_called()
                subprocess_call.assert_not_called()
                raw_child_call.assert_not_called()
                build_call.assert_not_called()
                compiler_call.assert_not_called()
                model_call.assert_not_called()
            self.assertFalse(output.exists())

        self.assertEqual(leaked, {})
        for descriptor in {token[1] for token in acquired}:
            with self.assertRaises(OSError) as raised:
                real_fstat(descriptor)
            self.assertEqual(raised.exception.errno, errno.EBADF)
        self.assertEqual(len(events), 2 * len(acquired))
        after = (artifact.stat().st_mode, artifact.stat().st_size,
                 artifact.stat().st_mtime_ns,
                 hashlib.sha256(artifact.read_bytes()).hexdigest())
        self.assertEqual(after, before)
        if fault is None:
            self.assertEqual(len(result), 1048577)
            self.assertEqual(hashlib.sha256(result).hexdigest(),
                             "9a6384d7058b15fa74ef39f6bd6e5745a1fbec565abb06491714704d3d88e07c")
            self.assertEqual(leaf_opens[0], 1)
        return acquired, closed

    def test_artifact_component_open_eio(self):
        self.exercise_artifact("component-open")

    def test_artifact_leaf_open_eio(self):
        self.exercise_artifact("leaf-open")

    def test_artifact_initial_fstat_eio(self):
        self.exercise_artifact("initial-fstat")

    def test_artifact_read_eio(self):
        self.exercise_artifact("read")

    def test_artifact_final_fstat_eio(self):
        self.exercise_artifact("final-fstat")

    def test_artifact_positive_control(self):
        self.exercise_artifact(None)

class NativeLifecycleOutputEnvelopeTests(unittest.TestCase):
    @staticmethod
    def harness_module():
        spec = importlib.util.spec_from_file_location(
            "native_lifecycle_output_envelope_harness", HERE / "harness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def literal_row():
        return [
            1, "OK",
            [[1, 1, 1, "PROCESS_ALLOC", [1, 0, 1, 1, 1, 0, 1], None,
              100, None, [0, 0, 0, 0, 0], 1, 1]],
            [[[1, 0, 1, 1, 1, 0, 1], None, 100, "Allocated", 1, "E",
              None, 0, None, False, True, False, None]],
            [], [1, 1, 0, False, False, False, 0],
        ]

    def setUp(self):
        self.fixture_paths = [
            HERE / "harness.py", HERE / "vectors.json", HERE / "expected.json",
            HERE / "raw-invalid/oversized-document.json",
        ]
        self.fixture_hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.fixture_paths
        }

    def tearDown(self):
        self.assertEqual(
            {path: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in self.fixture_paths},
            self.fixture_hashes)

    def payloads(self):
        row = self.literal_row()
        compact = json.dumps(row, separators=(",", ":")).encode()
        self.assertEqual((len(compact), hashlib.sha256(compact).hexdigest()),
                         (192, "4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a"))
        base = compact + b"\n"
        fit = compact + b" " * 1048383 + b"\n"
        over = compact + b" " * 1048384 + b"\n"
        self.assertEqual((len(base), len(fit), len(over)),
                         (193, 1048576, 1048577))
        return row, compact, base, fit, over

    def exercise(self, returncode, stdout, stderr, rejected):
        module = self.harness_module()
        self.assertEqual(module.MAX_OUTPUT, 1048576)
        row, compact, _, _, _ = self.payloads()
        command = ["/model-not-executed"]
        data = b"MODEL2 256 NONE\n"
        completed = subprocess.CompletedProcess(command, returncode, stdout, stderr)
        unexpected = RuntimeError("unexpected output-envelope action")
        actual = None
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"
            with mock.patch.object(module.subprocess, "run", return_value=completed) as run_call, \
                 mock.patch.object(module.subprocess, "Popen", side_effect=unexpected) as popen_call, \
                 mock.patch.object(module, "build", side_effect=unexpected) as build_call, \
                 mock.patch.object(module, "compiler", side_effect=unexpected) as compiler_call, \
                 mock.patch.object(module, "raw_child", side_effect=unexpected) as raw_child_call, \
                 mock.patch.object(module, "strict_bytes", wraps=module.strict_bytes) as strict_call, \
                 mock.patch.object(module, "validate_output_row", wraps=module.validate_output_row) as validate_call:
                if rejected:
                    with self.assertRaises(AssertionError) as raised:
                        module.run(command, data)
                    self.assertIs(type(raised.exception), AssertionError)
                    self.assertEqual(raised.exception.args, ())
                else:
                    actual = module.run(command, data)
                run_call.assert_called_once_with(
                    command, input=data, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=10, check=False)
                popen_call.assert_not_called()
                build_call.assert_not_called()
                compiler_call.assert_not_called()
                raw_child_call.assert_not_called()
                self.assertFalse(output.exists())
                if rejected:
                    strict_call.assert_not_called()
                    validate_call.assert_not_called()
                else:
                    strict_call.assert_called_once_with(stdout.splitlines()[0])
                    validate_call.assert_called_once_with(row, 1)
                    self.assertEqual(actual, [row])
                    module.assert_oracle_match([row], actual, [row])
        return actual, compact

    def test_output_nonzero_status_before_parse(self):
        _, _, base, _, _ = self.payloads()
        self.exercise(1, base, b"", True)

    def test_output_stderr_before_parse(self):
        _, _, base, _, _ = self.payloads()
        self.exercise(0, base, b"x", True)

    def test_output_size_over_before_parse(self):
        _, _, _, _, over = self.payloads()
        self.exercise(0, over, b"", True)

    def test_output_baseline_control(self):
        _, _, base, _, _ = self.payloads()
        self.exercise(0, base, b"", False)

    def test_output_exact_size_limit_control(self):
        _, _, _, fit, _ = self.payloads()
        self.exercise(0, fit, b"", False)


class NativeLifecycleOutputRegistryBooleanTests(unittest.TestCase):
    R1 = b'[1,"OK",[[1,1,1,"PROCESS_ALLOC",[1,0,1,1,1,0,1],null,100,null,[0,0,0,0,0],1,1]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,null,false,true,false,null]],[],[1,1,0,false,false,false,0]]'
    R2 = b'[2,"OK",[[1,2,2,"THREAD_ALLOC",[1,0,1,1,1,1,1],[1,0,1,1,1,0,1],100,200,[0,0,0,0,0],1,2]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,[1,0,1,1,1,1,1],false,true,true,null]],[[[1,0,1,1,1,1,1],[1,0,1,1,1,0,1],100,200,true,"Allocated",1,"E",null,0,null]],[2,2,0,false,false,false,0]]'
    COMPLEMENT_R2 = b'[2,"OK",[[1,2,2,"THREAD_ALLOC",[1,0,1,1,1,1,1],[1,0,1,1,1,0,1],100,200,[0,0,0,0,0],1,2]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,[1,0,1,1,1,1,1],true,false,false,null]],[[[1,0,1,1,1,1,1],[1,0,1,1,1,0,1],100,200,false,"Allocated",1,"E",null,0,null]],[2,2,0,false,false,false,0]]'

    @staticmethod
    def harness_module():
        spec = importlib.util.spec_from_file_location(
            "native_lifecycle_output_registry_boolean_harness", HERE / "harness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def setUp(self):
        self.fixture_paths = [
            HERE / "harness.py", HERE / "vectors.json", HERE / "expected.json",
            HERE / "raw-invalid/oversized-document.json",
        ]
        self.fixture_hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.fixture_paths
        }
        self.assertEqual((len(self.R1), hashlib.sha256(self.R1).hexdigest()),
                         (192, "4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a"))
        self.assertEqual((len(self.R2), hashlib.sha256(self.R2).hexdigest()),
                         (287, "98eced08c345fee134d0326fc57bfec3ba7448b45230b8ece2e2c5b6f81a8183"))
        self.assertEqual(len(self.R1 + b"\n" + self.R2 + b"\n"), 481)

    def tearDown(self):
        self.assertEqual(
            {path: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in self.fixture_paths},
            self.fixture_hashes)

    @classmethod
    def differences(cls, left, right, path=()):
        if type(left) is not type(right) or not isinstance(left, (list, dict)):
            return [] if type(left) is type(right) and left == right else [(path, left, right)]
        if isinstance(left, list):
            if len(left) != len(right):
                return [(path + ("length",), len(left), len(right))]
            result = []
            for index, (old, new) in enumerate(zip(left, right)):
                result.extend(cls.differences(old, new, path + (index,)))
            return result
        if set(left) != set(right):
            return [(path + ("keys",), set(left), set(right))]
        result = []
        for key in left:
            result.extend(cls.differences(left[key], right[key], path + (key,)))
        return result

    def invoke(self, stdout, rejected, process_calls, thread_calls, want=None):
        module = self.harness_module()
        command = ["/model-not-executed"]
        data = b"MODEL2 256 NONE\n"
        completed = subprocess.CompletedProcess(command, 0, stdout, b"")
        unexpected = RuntimeError("unexpected registry-Boolean action")
        actual = None
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"
            with mock.patch.object(module.subprocess, "run", return_value=completed) as run_call, \
                 mock.patch.object(module.subprocess, "Popen", side_effect=unexpected) as popen_call, \
                 mock.patch.object(module, "build", side_effect=unexpected) as build_call, \
                 mock.patch.object(module, "compiler", side_effect=unexpected) as compiler_call, \
                 mock.patch.object(module, "raw_child", side_effect=unexpected) as raw_child_call, \
                 mock.patch.object(module, "strict_bytes", wraps=module.strict_bytes) as strict_call, \
                 mock.patch.object(module, "process_row", wraps=module.process_row) as process_call, \
                 mock.patch.object(module, "thread_row", wraps=module.thread_row) as thread_call, \
                 mock.patch.object(module, "assert_oracle_match", wraps=module.assert_oracle_match) as oracle_call:
                if rejected:
                    with self.assertRaises(AssertionError) as raised:
                        module.run(command, data)
                    self.assertIs(type(raised.exception), AssertionError)
                    self.assertEqual(raised.exception.args, ())
                    oracle_call.assert_not_called()
                else:
                    actual = module.run(command, data)
                    module.assert_oracle_match(want, actual, want)
                    oracle_call.assert_called_once_with(want, actual, want)
                run_call.assert_called_once_with(
                    command, input=data, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=10, check=False)
                self.assertEqual(strict_call.call_count, 2)
                self.assertEqual(process_call.call_count, process_calls)
                self.assertEqual(thread_call.call_count, thread_calls)
                popen_call.assert_not_called()
                build_call.assert_not_called()
                compiler_call.assert_not_called()
                raw_child_call.assert_not_called()
                self.assertFalse(output.exists())
        return actual

    def negative(self, path, replacement, process_calls, thread_calls,
                 old_token, new_token):
        baseline = json.loads(self.R2)
        mutation = json.loads(self.R2)
        target = mutation
        for index in path[:-1]:
            target = target[index]
        before = target[path[-1]]
        target[path[-1]] = replacement
        self.assertEqual(self.differences(baseline, mutation),
                         [(tuple(path), before, replacement)])
        self.assertIs(type(before), bool)
        self.assertIs(type(replacement), int)
        mutated = json.dumps(mutation, separators=(",", ":")).encode()
        self.assertEqual(self.R2.count(old_token), 1)
        self.assertEqual(self.R2.count(new_token), 0)
        expected = self.R2.replace(old_token, new_token)
        self.assertEqual(mutated, expected)
        self.invoke(self.R1 + b"\n" + mutated + b"\n", True,
                    process_calls, thread_calls)

    def test_output_process_bool9_integer_zero(self):
        self.negative(
            [3, 0, 9], 0, 2, 0,
            b',null,0,[1,0,1,1,1,1,1],false,true,true,null',
            b',null,0,[1,0,1,1,1,1,1],0,true,true,null')

    def test_output_process_bool10_integer_one(self):
        self.negative(
            [3, 0, 10], 1, 2, 0,
            b',null,0,[1,0,1,1,1,1,1],false,true,true,null',
            b',null,0,[1,0,1,1,1,1,1],false,1,true,null')

    def test_output_process_bool11_integer_one(self):
        self.negative(
            [3, 0, 11], 1, 2, 0,
            b',null,0,[1,0,1,1,1,1,1],false,true,true,null',
            b',null,0,[1,0,1,1,1,1,1],false,true,1,null')

    def test_output_thread_main_integer_one(self):
        self.negative(
            [4, 0, 4], 1, 2, 1,
            b',[1,0,1,1,1,0,1],100,200,true,"Allocated"',
            b',[1,0,1,1,1,0,1],100,200,1,"Allocated"')

    def test_output_registry_boolean_positive_controls(self):
        baseline = [json.loads(self.R1), json.loads(self.R2)]
        self.invoke(self.R1 + b"\n" + self.R2 + b"\n", False, 2, 1, baseline)
        complement = [json.loads(self.R1), json.loads(self.COMPLEMENT_R2)]
        booleans = complement[1][3][0][9:12] + [complement[1][4][0][4]]
        self.assertEqual(booleans, [True, False, False, False])
        self.assertTrue(all(type(value) is bool for value in booleans))
        self.invoke(self.R1 + b"\n" + self.COMPLEMENT_R2 + b"\n",
                    False, 2, 1, complement)


class NativeLifecycleOutputControlBooleanTests(unittest.TestCase):
    R1 = b'[1,"OK",[[1,1,1,"PROCESS_ALLOC",[1,0,1,1,1,0,1],null,100,null,[0,0,0,0,0],1,1]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,null,false,true,false,null]],[],[1,1,0,false,false,false,0]]'
    COMPLEMENT_R1 = b'[1,"OK",[[1,1,1,"PROCESS_ALLOC",[1,0,1,1,1,0,1],null,100,null,[0,0,0,0,0],1,1]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,null,false,true,false,null]],[],[1,1,0,true,true,true,0]]'
    CONTROL_SUFFIX = b'[1,1,0,false,false,false,0]]'

    @staticmethod
    def harness_module():
        spec = importlib.util.spec_from_file_location(
            "native_lifecycle_output_control_boolean_harness", HERE / "harness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def setUp(self):
        self.fixture_paths = [
            HERE / "harness.py", HERE / "vectors.json", HERE / "expected.json",
            HERE / "raw-invalid/oversized-document.json",
        ]
        self.fixture_hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.fixture_paths
        }
        self.assertEqual((len(self.R1), hashlib.sha256(self.R1).hexdigest()),
                         (192, "4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a"))
        self.assertEqual(len(self.R1 + b"\n"), 193)
        self.assertEqual(len(self.COMPLEMENT_R1), 189)
        self.assertEqual(len(self.COMPLEMENT_R1 + b"\n"), 190)

    def tearDown(self):
        self.assertEqual(
            {path: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in self.fixture_paths},
            self.fixture_hashes)

    @classmethod
    def differences(cls, left, right, path=()):
        if type(left) is not type(right) or not isinstance(left, (list, dict)):
            return [] if type(left) is type(right) and left == right else [(path, left, right)]
        if isinstance(left, list):
            if len(left) != len(right):
                return [(path + ("length",), len(left), len(right))]
            result = []
            for index, (old, new) in enumerate(zip(left, right)):
                result.extend(cls.differences(old, new, path + (index,)))
            return result
        if set(left) != set(right):
            return [(path + ("keys",), set(left), set(right))]
        result = []
        for key in left:
            result.extend(cls.differences(left[key], right[key], path + (key,)))
        return result

    def invoke(self, stdout, rejected, want=None):
        module = self.harness_module()
        command = ["/model-not-executed"]
        data = b"MODEL2 256 NONE\n"
        completed = subprocess.CompletedProcess(command, 0, stdout, b"")
        unexpected = RuntimeError("unexpected control-Boolean action")
        order = []
        strict = module.strict_bytes
        validate = module.validate_output_row
        process = module.process_row

        def ordered_strict(value):
            order.append("strict")
            return strict(value)

        def ordered_validate(row, expected_id):
            order.append("validate")
            return validate(row, expected_id)

        def ordered_process(row):
            order.append("process")
            return process(row)

        actual = None
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"
            with mock.patch.object(module.subprocess, "run", return_value=completed) as run_call, \
                 mock.patch.object(module.subprocess, "Popen", side_effect=unexpected) as popen_call, \
                 mock.patch.object(module, "build", side_effect=unexpected) as build_call, \
                 mock.patch.object(module, "compiler", side_effect=unexpected) as compiler_call, \
                 mock.patch.object(module, "raw_child", side_effect=unexpected) as raw_child_call, \
                 mock.patch.object(module, "strict_bytes", side_effect=ordered_strict) as strict_call, \
                 mock.patch.object(module, "validate_output_row", side_effect=ordered_validate) as validate_call, \
                 mock.patch.object(module, "process_row", side_effect=ordered_process) as process_call, \
                 mock.patch.object(module, "thread_row", wraps=module.thread_row) as thread_call, \
                 mock.patch.object(module, "assert_oracle_match", wraps=module.assert_oracle_match) as oracle_call:
                if rejected:
                    with self.assertRaises(AssertionError) as raised:
                        module.run(command, data)
                    self.assertIs(type(raised.exception), AssertionError)
                    self.assertEqual(raised.exception.args, ())
                    oracle_call.assert_not_called()
                else:
                    actual = module.run(command, data)
                    module.assert_oracle_match(want, actual, want)
                    oracle_call.assert_called_once_with(want, actual, want)
                run_call.assert_called_once_with(
                    command, input=data, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=10, check=False)
                self.assertEqual(strict_call.call_count, 1)
                validate_call.assert_called_once_with(mock.ANY, 1)
                self.assertEqual(process_call.call_count, 1)
                thread_call.assert_not_called()
                self.assertEqual(order, ["strict", "validate", "process"])
                popen_call.assert_not_called()
                build_call.assert_not_called()
                compiler_call.assert_not_called()
                raw_child_call.assert_not_called()
                self.assertFalse(output.exists())
        return actual

    def negative(self, index, replacement_suffix):
        baseline = json.loads(self.R1)
        mutation = json.loads(self.R1)
        before = mutation[5][index]
        mutation[5][index] = 0
        self.assertEqual(self.differences(baseline, mutation),
                         [((5, index), before, 0)])
        self.assertIs(type(before), bool)
        self.assertIs(type(mutation[5][index]), int)
        self.assertEqual(self.R1.count(self.CONTROL_SUFFIX), 1)
        self.assertEqual(self.R1.count(replacement_suffix), 0)
        expected = self.R1.replace(self.CONTROL_SUFFIX, replacement_suffix)
        self.assertEqual(len(expected), 188)
        self.assertEqual(json.dumps(mutation, separators=(",", ":")).encode(),
                         expected)
        self.invoke(expected + b"\n", True)

    def test_output_control_overflow_integer_zero(self):
        self.negative(3, b'[1,1,0,0,false,false,0]]')

    def test_output_control_ended_integer_zero(self):
        self.negative(4, b'[1,1,0,false,0,false,0]]')

    def test_output_control_incomplete_integer_zero(self):
        self.negative(5, b'[1,1,0,false,false,0,0]]')

    def test_output_control_boolean_positive_controls(self):
        baseline = [json.loads(self.R1)]
        self.invoke(self.R1 + b"\n", False, baseline)
        complement = [json.loads(self.COMPLEMENT_R1)]
        booleans = complement[0][5][3:6]
        self.assertEqual(booleans, [True, True, True])
        self.assertTrue(all(type(value) is bool for value in booleans))
        self.invoke(self.COMPLEMENT_R1 + b"\n", False, complement)

class NativeLifecycleOutputRowIdTypeTests(unittest.TestCase):
    R1 = b'[1,"OK",[[1,1,1,"PROCESS_ALLOC",[1,0,1,1,1,0,1],null,100,null,[0,0,0,0,0],1,1]],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,null,false,true,false,null]],[],[1,1,0,false,false,false,0]]'
    CASES = {
        "boolean": (b'[true,"OK",', 195,
                    "a2e87b36e2721a0b6fe65cbe760ceaa36117e8a3387931dce0f175d94c6783a6", bool),
        "float": (b'[1.0,"OK",', 194,
                  "ede0e731f1cd76cda959b6ebc14cec1ef0fbb4ac44e8bd3392196089ba32c1fd", float),
    }

    @staticmethod
    def harness_module():
        spec = importlib.util.spec_from_file_location(
            "native_lifecycle_output_row_id_type_harness", HERE / "harness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def setUp(self):
        self.fixture_paths = (
            HERE / "harness.py", HERE / "vectors.json", HERE / "expected.json",
            HERE / "raw-invalid/oversized-document.json",
        )
        self.fixture_hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.fixture_paths
        }
        self.assertEqual((len(self.R1), len(self.R1 + b"\n"),
                          hashlib.sha256(self.R1).hexdigest()),
                         (192, 193,
                          "4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a"))

    def tearDown(self):
        self.assertEqual(
            {path: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in self.fixture_paths},
            self.fixture_hashes)

    @classmethod
    def differences(cls, left, right, path=()):
        if type(left) is not type(right) or not isinstance(left, (list, dict)):
            return [] if type(left) is type(right) and left == right else [(path, left, right)]
        if isinstance(left, list):
            if len(left) != len(right):
                return [(path + ("length",), len(left), len(right))]
            result = []
            for index, (old, new) in enumerate(zip(left, right)):
                result.extend(cls.differences(old, new, path + (index,)))
            return result
        if set(left) != set(right):
            return [(path + ("keys",), set(left), set(right))]
        result = []
        for key in left:
            result.extend(cls.differences(left[key], right[key], path + (key,)))
        return result

    def invoke(self, row_bytes, rejected):
        module = self.harness_module()
        command = ["/model-not-executed"]
        data = b"MODEL2 256 NONE\n"
        stream = row_bytes + b"\n"
        completed = subprocess.CompletedProcess(command, 0, stream, b"")
        unexpected = RuntimeError("unexpected output-row-ID action")
        order = []
        strict = module.strict_bytes
        validate = module.validate_output_row
        integer = module.integer

        def ordered_strict(value):
            order.append("strict")
            return strict(value)

        def ordered_validate(row, expected_id):
            order.append("validate")
            return validate(row, expected_id)

        def ordered_integer(value, low=0, high=(1 << 64) - 1):
            order.append("integer")
            return integer(value, low, high)

        actual = None
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"
            with mock.patch.object(module.subprocess, "run", return_value=completed) as run_call, \
                 mock.patch.object(module.subprocess, "Popen", side_effect=unexpected) as popen_call, \
                 mock.patch.object(module, "build", side_effect=unexpected) as build_call, \
                 mock.patch.object(module, "compiler", side_effect=unexpected) as compiler_call, \
                 mock.patch.object(module, "raw_child", side_effect=unexpected) as raw_child_call, \
                 mock.patch.object(module, "strict_bytes", side_effect=ordered_strict) as strict_call, \
                 mock.patch.object(module, "validate_output_row", side_effect=ordered_validate) as validate_call, \
                 mock.patch.object(module, "integer", side_effect=ordered_integer) as integer_call, \
                 mock.patch.object(module, "process_row", wraps=module.process_row) as process_call, \
                 mock.patch.object(module, "thread_row", wraps=module.thread_row) as thread_call, \
                 mock.patch.object(module, "nullable_key", wraps=module.nullable_key) as nullable_call, \
                 mock.patch.object(module, "assert_oracle_match", wraps=module.assert_oracle_match) as oracle_call:
                if rejected:
                    with self.assertRaises(module.ValidationError) as raised:
                        module.run(command, data)
                    self.assertIs(type(raised.exception), module.ValidationError)
                    self.assertEqual(str(raised.exception), "integer")
                    self.assertEqual(order, ["strict", "validate", "integer"])
                    strict_call.assert_called_once_with(row_bytes)
                    validate_call.assert_called_once_with(mock.ANY, 1)
                    self.assertEqual(integer_call.call_count, 1)
                    value, low, high = integer_call.call_args.args
                    self.assertIs(type(value), type(json.loads(row_bytes)[0]))
                    self.assertEqual((low, high), (1, 128))
                    process_call.assert_not_called()
                    thread_call.assert_not_called()
                    nullable_call.assert_not_called()
                    oracle_call.assert_not_called()
                else:
                    want = [json.loads(self.R1)]
                    actual = module.run(command, data)
                    module.assert_oracle_match(want, actual, want)
                    strict_call.assert_called_once_with(row_bytes)
                    validate_call.assert_called_once_with(mock.ANY, 1)
                    self.assertEqual(process_call.call_count, 1)
                    thread_call.assert_not_called()
                    oracle_call.assert_called_once_with(want, actual, want)
                run_call.assert_called_once_with(
                    command, input=data, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, timeout=10, check=False)
                popen_call.assert_not_called()
                build_call.assert_not_called()
                compiler_call.assert_not_called()
                raw_child_call.assert_not_called()
                self.assertFalse(output.exists())
        return actual

    def negative(self, name, replacement):
        token = b'[1,"OK",'
        replacement_token, row_size, row_hash, replacement_type = self.CASES[name]
        self.assertIs(replacement_type, type(replacement))
        self.assertEqual(self.R1.count(token), 1)
        self.assertEqual(self.R1.count(replacement_token), 0)
        fixed = self.R1.replace(token, replacement_token)
        baseline = json.loads(self.R1)
        mutation = json.loads(self.R1)
        mutation[0] = replacement
        self.assertEqual(self.differences(baseline, mutation),
                         [((0,), 1, replacement)])
        self.assertIs(type(baseline[0]), int)
        self.assertIs(type(mutation[0]), replacement_type)
        structural = json.dumps(mutation, separators=(",", ":")).encode()
        self.assertEqual(structural, fixed)
        self.assertEqual((len(fixed), len(fixed + b"\n"),
                          hashlib.sha256(fixed).hexdigest()),
                         (row_size, row_size + 1, row_hash))
        self.invoke(fixed, True)

    def test_output_row_id_positive_control(self):
        self.assertIs(type(json.loads(self.R1)[0]), int)
        self.assertEqual(self.invoke(self.R1, False), [json.loads(self.R1)])

    def test_output_row_id_boolean_true(self):
        self.negative("boolean", True)

    def test_output_row_id_integral_float(self):
        self.negative("float", 1.0)


class NativeLifecycleOutputOracleTests(unittest.TestCase):
    CASE_NAMES = {
        "oracle-row-malformed-json", "oracle-row-missing", "oracle-row-extra",
        "oracle-row-duplicate", "oracle-event-malformed", "oracle-event-missing",
        "oracle-event-extra", "oracle-event-duplicate", "oracle-control-malformed",
        "oracle-control-missing", "oracle-control-extra", "oracle-control-duplicate",
        "oracle-control-value-corrupt",
    }

    @staticmethod
    def harness_module():
        spec = importlib.util.spec_from_file_location(
            "native_lifecycle_oracle_harness", HERE / "harness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def literal_row():
        return [
            1, "OK",
            [[1, 1, 1, "PROCESS_ALLOC", [1, 0, 1, 1, 1, 0, 1], None,
              100, None, [0, 0, 0, 0, 0], 1, 1]],
            [[[1, 0, 1, 1, 1, 0, 1], None, 100, "Allocated", 1, "E",
              None, 0, None, False, True, False, None]],
            [], [1, 1, 0, False, False, False, 0],
        ]

    def setUp(self):
        self.fixture_paths = [
            HERE / "harness.py", HERE / "vectors.json", HERE / "expected.json",
            HERE / "raw-invalid/oversized-document.json",
        ]
        self.fixture_hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.fixture_paths
        }

    def tearDown(self):
        self.assertEqual(
            {path: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in self.fixture_paths},
            self.fixture_hashes)

    def invoke_run(self, module, stdout):
        command = ["/model-not-executed"]
        data = b"MODEL2 256 NONE\n"
        completed = subprocess.CompletedProcess(command, 0, stdout, b"")
        unexpected = RuntimeError("unexpected non-oracle action")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "must-not-exist"
            with mock.patch.object(module.subprocess, "run", return_value=completed) as run_call, \
                 mock.patch.object(module.subprocess, "Popen", side_effect=unexpected) as popen_call, \
                 mock.patch.object(module, "build", side_effect=unexpected) as build_call, \
                 mock.patch.object(module, "compiler", side_effect=unexpected) as compiler_call, \
                 mock.patch.object(module, "raw_child", side_effect=unexpected) as raw_child_call:
                try:
                    return module.run(command, data)
                finally:
                    run_call.assert_called_once_with(
                        command, input=data, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, timeout=10, check=False)
                    popen_call.assert_not_called()
                    build_call.assert_not_called()
                    compiler_call.assert_not_called()
                    raw_child_call.assert_not_called()
                    self.assertFalse(output.exists())

    @staticmethod
    def stdout_for_rows(rows):
        return b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n"
                        for row in rows)

    def corruptions(self):
        row = self.literal_row()
        compact = json.dumps(row, separators=(",", ":")).encode()
        cases = {}
        cases["oracle-row-malformed-json"] = (compact[:-1] + b"\n", "validation")
        cases["oracle-row-missing"] = (b"", "comparison")
        extra = json.loads(json.dumps(row)); extra[0] = 2; extra[2] = []
        cases["oracle-row-extra"] = (self.stdout_for_rows([row, extra]), "comparison")
        cases["oracle-row-duplicate"] = (compact + b"\n" + compact + b"\n", "assertion")
        mutation = json.loads(json.dumps(row)); mutation[2][0].pop()
        cases["oracle-event-malformed"] = (self.stdout_for_rows([mutation]), "assertion")
        mutation = json.loads(json.dumps(row)); mutation[2] = []
        cases["oracle-event-missing"] = (self.stdout_for_rows([mutation]), "comparison")
        mutation = json.loads(json.dumps(row)); event = json.loads(json.dumps(mutation[2][0])); event[3] = "EXTRA"; mutation[2].append(event)
        cases["oracle-event-extra"] = (self.stdout_for_rows([mutation]), "comparison")
        mutation = json.loads(json.dumps(row)); mutation[2].append(json.loads(json.dumps(mutation[2][0])))
        cases["oracle-event-duplicate"] = (self.stdout_for_rows([mutation]), "comparison")
        mutation = json.loads(json.dumps(row)); mutation[5] = None
        cases["oracle-control-malformed"] = (self.stdout_for_rows([mutation]), "assertion")
        mutation = json.loads(json.dumps(row)); mutation.pop()
        cases["oracle-control-missing"] = (self.stdout_for_rows([mutation]), "assertion")
        mutation = json.loads(json.dumps(row)); mutation[5].append(0)
        cases["oracle-control-extra"] = (self.stdout_for_rows([mutation]), "assertion")
        mutation = json.loads(json.dumps(row)); mutation.append(json.loads(json.dumps(mutation[5])))
        cases["oracle-control-duplicate"] = (self.stdout_for_rows([mutation]), "assertion")
        mutation = json.loads(json.dumps(row)); mutation[5][0] = 2
        cases["oracle-control-value-corrupt"] = (self.stdout_for_rows([mutation]), "comparison")
        self.assertEqual(set(cases), self.CASE_NAMES)
        return cases

    def test_independent_literal_and_gated_helper_site(self):
        module = self.harness_module()
        row = self.literal_row()
        compact = json.dumps(row, separators=(",", ":")).encode()
        self.assertEqual(len(compact), 192)
        self.assertEqual(hashlib.sha256(compact).hexdigest(),
                         "4a7ebba05f2481c55dfd4565d5e81567b3fdb17691551a82b9b5d7d88b99dc8a")
        expected = {
            "schema_version": 2, "model_only": True, "corpus_complete": False,
            "pools": {}, "vectors": {"oracle": [row]},
        }
        self.assertEqual(module.expected_rows(expected, "oracle"), [row])
        source = (HERE / "harness.py").read_text()
        lines = source.splitlines()
        definition = "def assert_oracle_match(want, rust_rows, c_rows):"
        body = "    assert rust_rows == want and c_rows == want and rust_rows == c_rows"
        call = "        assert_oracle_match(want, rust_rows, c_rows)"
        self.assertEqual(lines.count(definition), 1)
        self.assertEqual(lines.count(body), 1)
        self.assertEqual(lines.count(call), 1)
        helper_index = lines.index(definition)
        self.assertEqual(lines[helper_index + 1], body)
        self.assertEqual(lines.count("def main():"), 1)
        main_start = lines.index("def main():")
        main_end = lines.index('if __name__ == "__main__":', main_start)
        main_lines = lines[main_start:main_end]
        self.assertEqual(main_lines.count(call), 1)
        self.assertNotIn(body.strip(), [line.strip() for line in main_lines])
        call_index = main_lines.index(call)
        self.assertEqual(main_lines[call_index - 3:call_index], [
            "        want = expected_rows(expected, name)",
            '        rust_rows = run([str(rust)], wire(vector, vectors["pools"]))',
            '        c_rows = run([str(cref)], wire(vector, vectors["pools"]))',
        ])

    def test_exact_thirteen_corruptions(self):
        module = self.harness_module()
        want = [self.literal_row()]
        good = self.invoke_run(module, self.stdout_for_rows(want))
        for name, (stdout, rejection) in self.corruptions().items():
            with self.subTest(name=name):
                if rejection == "validation":
                    with self.assertRaises(module.ValidationError) as raised:
                        self.invoke_run(module, stdout)
                    self.assertIs(type(raised.exception), module.ValidationError)
                    self.assertEqual(str(raised.exception), "invalid JSON")
                    continue
                if rejection == "assertion":
                    with self.assertRaises(AssertionError) as raised:
                        self.invoke_run(module, stdout)
                    self.assertIs(type(raised.exception), AssertionError)
                    self.assertEqual(raised.exception.args, ())
                    continue
                bad = self.invoke_run(module, stdout)
                for rust_rows, c_rows in ((bad, good), (good, bad), (bad, bad)):
                    with self.assertRaises(AssertionError) as raised:
                        module.assert_oracle_match(want, rust_rows, c_rows)
                    self.assertIs(type(raised.exception), AssertionError)
                    self.assertEqual(raised.exception.args, ())

    def test_positive_baseline_with_and_without_terminal_lf(self):
        module = self.harness_module()
        want = [self.literal_row()]
        baseline = self.stdout_for_rows(want)
        with_lf = self.invoke_run(module, baseline)
        without_lf = self.invoke_run(module, baseline[:-1])
        self.assertEqual(with_lf, want)
        self.assertEqual(without_lf, want)
        module.assert_oracle_match(want, with_lf, without_lf)

class NativeLifecycleCaptureClosedLiteralTests(unittest.TestCase):
    NAMES = (
        "end-after-complete-end", "end-after-incomplete-end",
        "operation-after-end", "wrong-key-after-end",
        "launcher-loss-after-end", "teardown-fail-after-end",
    )
    COMPLETE_NAMES = (
        "end-after-complete-end", "operation-after-end",
        "wrong-key-after-end", "launcher-loss-after-end",
        "teardown-fail-after-end",
    )
    SUFFIXES = {
        "end-after-complete-end": [17, "CAPTURE_END", None, None, 0, 0, 0, 0],
        "operation-after-end": [17, "REF_ADD", [1, 0, 1, 1, 1, 1, 1], None, 0, 0, 0, 0],
        "wrong-key-after-end": [17, "REF_ADD", [2, 0, 1, 1, 1, 1, 1], None, 0, 0, 0, 0],
        "launcher-loss-after-end": [17, "LAUNCHER_LOSS", None, None, 0, 0, 0, 0],
        "teardown-fail-after-end": [17, "TEARDOWN_FAIL", [1, 0, 1, 1, 1, 1, 1], None, 0, 0, 0, 0],
    }
    SUFFIX_BYTES = {
        "end-after-complete-end": b'[17,"CAPTURE_END",null,null,0,0,0,0]',
        "operation-after-end": b'[17,"REF_ADD",[1,0,1,1,1,1,1],null,0,0,0,0]',
        "wrong-key-after-end": b'[17,"REF_ADD",[2,0,1,1,1,1,1],null,0,0,0,0]',
        "launcher-loss-after-end": b'[17,"LAUNCHER_LOSS",null,null,0,0,0,0]',
        "teardown-fail-after-end": b'[17,"TEARDOWN_FAIL",[1,0,1,1,1,1,1],null,0,0,0,0]',
    }
    COMPLETE_CLOSED_BYTES = (
        b'[17,"CLOSED",[],[[[1,0,1,1,1,0,1],null,100,"Retired",0,"N",'
        b'[9472,37,0,4],0,[1,0,1,1,1,1,1],false,false,false,[[1,0,1,1,1,0,1],'
        b'[9472,37,0,4],0]]],[[[1,0,1,1,1,1,1],[1,0,1,1,1,0,1],100,200,true,'
        b'"Retired",0,"N",[9472,37,0,1],0,[[1,0,1,1,1,1,1],[9472,37,0,1],0]]],'
        b'[16,16,0,false,true,true,0]]'
    )
    INCOMPLETE_END_BYTES = (
        b'[2,"OK",[[1,2,2,"CAPTURE_END",null,null,null,null,[0,0,0,0,0],1,2]],'
        b'[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,null,false,true,'
        b'false,null]],[],[2,2,0,false,true,true,0]]'
    )
    INCOMPLETE_CLOSED_BYTES = (
        b'[3,"CLOSED",[],[[[1,0,1,1,1,0,1],null,100,"Allocated",1,"E",null,0,'
        b'null,false,true,false,null]],[],[2,2,0,false,true,true,0]]'
    )

    @staticmethod
    def harness_module():
        spec = importlib.util.spec_from_file_location(
            "native_lifecycle_capture_closed_harness", HERE / "harness.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def complete_closed_row():
        return [
            17, "CLOSED", [],
            [[[1, 0, 1, 1, 1, 0, 1], None, 100, "Retired", 0, "N",
              [9472, 37, 0, 4], 0, [1, 0, 1, 1, 1, 1, 1], False,
              False, False, [[1, 0, 1, 1, 1, 0, 1], [9472, 37, 0, 4], 0]]],
            [[[1, 0, 1, 1, 1, 1, 1], [1, 0, 1, 1, 1, 0, 1], 100,
              200, True, "Retired", 0, "N", [9472, 37, 0, 1], 0,
              [[1, 0, 1, 1, 1, 1, 1], [9472, 37, 0, 1], 0]]],
            [16, 16, 0, False, True, True, 0],
        ]

    @staticmethod
    def incomplete_rows():
        return [
            [2, "OK",
             [[1, 2, 2, "CAPTURE_END", None, None, None, None,
               [0, 0, 0, 0, 0], 1, 2]],
             [[[1, 0, 1, 1, 1, 0, 1], None, 100, "Allocated", 1, "E",
               None, 0, None, False, True, False, None]],
             [], [2, 2, 0, False, True, True, 0]],
            [3, "CLOSED", [],
             [[[1, 0, 1, 1, 1, 0, 1], None, 100, "Allocated", 1, "E",
               None, 0, None, False, True, False, None]],
             [], [2, 2, 0, False, True, True, 0]],
        ]

    def setUp(self):
        self.fixture_paths = (
            HERE / "harness.py", HERE / "vectors.json", HERE / "expected.json",
            HERE / "raw-invalid/oversized-document.json",
        )
        self.fixture_hashes = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.fixture_paths
        }

    def tearDown(self):
        self.assertEqual(
            {path: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in self.fixture_paths},
            self.fixture_hashes)

    def sources(self):
        return (json.loads((HERE / "vectors.json").read_text()),
                json.loads((HERE / "expected.json").read_text()))

    @staticmethod
    def assert_no_execution_calls(calls):
        for call in calls:
            call.assert_not_called()

    @contextlib.contextmanager
    def no_execution(self, module):
        unexpected = RuntimeError("unexpected execution")
        with mock.patch.object(module.subprocess, "run", side_effect=unexpected) as subprocess_run, \
             mock.patch.object(module.subprocess, "Popen", side_effect=unexpected) as popen_call, \
             mock.patch.object(module, "raw_child", side_effect=unexpected) as raw_child_call, \
             mock.patch.object(module, "build", side_effect=unexpected) as build_call, \
             mock.patch.object(module, "compiler", side_effect=unexpected) as compiler_call, \
             mock.patch.object(module, "run", side_effect=unexpected) as model_call:
            calls = (subprocess_run, popen_call, raw_child_call,
                     build_call, compiler_call, model_call)
            yield calls
            self.assert_no_execution_calls(calls)

    def test_exact_six_mappings_and_eighty_eight_rows(self):
        module = self.harness_module()
        with self.no_execution(module):
            vectors, expected = self.sources()
            record_names = [record["name"] for record in vectors["vectors"]]
            self.assertEqual(len(record_names), len(set(record_names)))
            records = {record["name"]: record for record in vectors["vectors"]}
            self.assertEqual(set(records), set(expected["vectors"]))
            self.assertEqual(set(records), module.ORDINARY_REQUIRED)
            self.assertEqual(set(records), REQUIRED)
            self.assertEqual(set(self.NAMES), {
                name for name, record in records.items()
                if record["coverage"][0] == "capture-closed"
            })
            lrefs = [{"pool": "L%02d" % index} for index in range(1, 17)]
            brefs = [{"pool": "B%02d" % index} for index in range(1, 17)]
            for name in self.NAMES:
                record = records[name]
                self.assertEqual(record["coverage"], ["capture-closed", name])
                self.assertEqual(record["event_capacity"], 256)
                self.assertEqual(record["seed"], "NONE")
                self.assertTrue(module.wire(record, vectors["pools"]).startswith(
                    b"MODEL2 256 NONE\n"))
                if name in self.COMPLETE_NAMES:
                    self.assertEqual(record["operations"][:-1], lrefs)
                    self.assertEqual(record["operations"][-1], self.SUFFIXES[name])
                    self.assertEqual(json.dumps(record["operations"][-1],
                                                separators=(",", ":")).encode(),
                                     self.SUFFIX_BYTES[name])
                    self.assertEqual(expected["vectors"][name][:-1], brefs)
                    self.assertEqual(expected["vectors"][name][-1],
                                     {"pool": "CLOSED_COMPLETE_17"})
            incomplete_input = [
                [1, "P_ALLOC", [1, 0, 1, 1, 1, 0, 1], None, 100, 0, 0, 0],
                [2, "CAPTURE_END", None, None, 0, 0, 0, 0],
                [3, "CAPTURE_END", None, None, 0, 0, 0, 0],
            ]
            self.assertEqual(records["end-after-incomplete-end"]["operations"],
                             incomplete_input)
            self.assertEqual(expected["vectors"]["end-after-incomplete-end"], [
                {"pool": "B01"}, {"pool": "INCOMPLETE_END_2"},
                {"pool": "INCOMPLETE_CLOSED_3"},
            ])
            expanded_inputs = [module.checked_expansion(
                records[name]["operations"], vectors["pools"]) for name in self.NAMES]
            expanded_outputs = [module.expected_rows(expected, name) for name in self.NAMES]
            self.assertEqual(sum(map(len, expanded_inputs)), 88)
            self.assertEqual(sum(map(len, expanded_outputs)), 88)
            self.assertEqual((len(records), len(expected["vectors"]),
                              len(module.ORDINARY_REQUIRED), len(vectors["raw_invalid"])),
                             (44, 44, 44, 137))
            self.assertEqual((HERE / "vectors.json").stat().st_size, 1017373)
            self.assertLess((HERE / "vectors.json").stat().st_size, 1 << 20)

    def test_independent_full_rows_and_closed_deltas(self):
        module = self.harness_module()
        with self.no_execution(module):
            _, expected = self.sources()
            complete = self.complete_closed_row()
            incomplete = self.incomplete_rows()
            self.assertEqual(expected["pools"]["CLOSED_COMPLETE_17"], complete)
            self.assertEqual(expected["pools"]["INCOMPLETE_END_2"], incomplete[0])
            self.assertEqual(expected["pools"]["INCOMPLETE_CLOSED_3"], incomplete[1])
            compact = lambda row: json.dumps(row, separators=(",", ":")).encode()
            self.assertEqual(compact(expected["pools"]["CLOSED_COMPLETE_17"]),
                             self.COMPLETE_CLOSED_BYTES)
            self.assertEqual(compact(expected["pools"]["INCOMPLETE_END_2"]),
                             self.INCOMPLETE_END_BYTES)
            self.assertEqual(compact(expected["pools"]["INCOMPLETE_CLOSED_3"]),
                             self.INCOMPLETE_CLOSED_BYTES)
            self.assertEqual(complete[1:3], ["CLOSED", []])
            self.assertEqual(incomplete[1][1:3], ["CLOSED", []])
            for name in self.COMPLETE_NAMES:
                rows = module.expected_rows(expected, name)
                self.assertEqual(rows[-1], complete)
                self.assertEqual(rows[-2][3:5], rows[-1][3:5])
                self.assertEqual(rows[-2][5][:5] + rows[-2][5][6:],
                                 rows[-1][5][:5] + rows[-1][5][6:])
                self.assertFalse(rows[-2][5][5])
                self.assertTrue(rows[-1][5][5])
                self.assertEqual(rows[-1][5][:3] + rows[-1][5][6:],
                                 [16, 16, 0, 0])
            rows = module.expected_rows(expected, "end-after-incomplete-end")
            self.assertEqual(rows[1:], incomplete)
            self.assertEqual(rows[1][3:], rows[2][3:])
            self.assertTrue(rows[1][5][5] and rows[2][5][5])
            self.assertEqual(rows[2][2], [])

    def schema_rejection(self, suffix, reason):
        module = self.harness_module()
        vectors, _ = self.sources()
        operations = ([{"pool": "L%02d" % index} for index in range(1, 17)] +
                      [suffix])
        document = {
            "schema_version": 2, "model_only": True, "corpus_complete": False,
            "pools": vectors["pools"],
            "vectors": [{
                "name": "schema-first",
                "coverage": ["capture-closed", "schema-first"],
                "event_capacity": 256, "seed": "NONE", "operations": operations,
            }],
            "raw_invalid": [], "mutants": {},
        }
        raw = json.dumps(document, separators=(",", ":")).encode()
        unexpected = RuntimeError("unexpected execution")
        stdin = mock.Mock()
        stdin.buffer = io.BytesIO(raw)
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(module.subprocess, "run", side_effect=unexpected) as subprocess_run, \
             mock.patch.object(module.subprocess, "Popen", side_effect=unexpected) as popen_call, \
             mock.patch.object(module, "raw_child", side_effect=unexpected) as raw_child_call, \
             mock.patch.object(module, "build", side_effect=unexpected) as build_call, \
             mock.patch.object(module, "compiler", side_effect=unexpected) as compiler_call, \
             mock.patch.object(module, "run", side_effect=unexpected) as model_call, \
             mock.patch.object(module.sys, "stdin", stdin), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            with self.assertRaises(module.ValidationError) as raised:
                module.decode_raw_document(raw)
            self.assertIs(type(raised.exception), module.ValidationError)
            self.assertEqual(str(raised.exception), reason)
            self.assertEqual(module.decoder_mode(), 2)
        self.assertEqual((stdout.getvalue(), stderr.getvalue()), ("", ""))
        self.assert_no_execution_calls((subprocess_run, popen_call, raw_child_call,
                                        build_call, compiler_call, model_call))

    def test_unknown_operation_after_end_is_schema_rejected(self):
        self.schema_rejection(
            [17, "UNKNOWN", None, None, 0, 0, 0, 0], "operation identity")

    def test_boolean_capture_after_end_is_schema_rejected(self):
        self.schema_rejection(
            [17, "REF_ADD", [True, 0, 1, 1, 1, 1, 1], None, 0, 0, 0, 0],
            "integer")

if __name__ == "__main__":
    unittest.main()
