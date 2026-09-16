#!/usr/bin/env python3
"""Dispatcher-owned bounded runner for the MODEL_ONLY lifecycle packet."""
import argparse
import hashlib
import json
import os
import pathlib
import selectors
import stat
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
MAX_JSON = 1 << 20
MAX_EXPANDED = 2 << 20
MAX_OUTPUT = 1 << 20
MAX_RAW_ARTIFACT = MAX_JSON + 1
MAX_RAW_STREAM = 1 << 16
RAW_EXPECTED = {
    "stage": "harness", "exit_code": 2, "stdout_hex": "", "stderr_hex": "",
    "model_invocations": 0,
}
RAW_MECHANISM_REQUIRED = {
    "raw-duplicate-key", "raw-nonfinite", "raw-trailing-object",
    "raw-embedded-nul", "raw-129-operations", "raw-oversized-document",
    "raw-unknown-pool", "raw-cyclic-pool", "raw-excess-pool-args",
    "raw-authority-retire-a", "raw-authority-retire-b",
    "raw-authority-retire-c", "raw-authority-retire-d",
    "raw-authority-extra-operation-field",
    "raw-authority-extra-vector-field", "raw-authority-unknown-operation",
    "raw-pid-zero", "raw-pid-int32-overflow", "raw-pid-negative",
    "raw-pid-u64-overflow", "raw-pid-integral-float",
    "raw-pid-fractional-float", "raw-pid-boolean", "raw-pid-string",
    "raw-pid-null", "raw-tid-alloc-int32-overflow",
    "raw-tid-assign-zero", "raw-tid-assign-int32-overflow",
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
    "raw-raw-invalid-nonarray", "raw-mutants-nonobject",
    "raw-nested-raw-invalid",
    "raw-operation-id-overflow", "raw-operation-id-fractional",
    "raw-main-flag-overflow", "raw-terminal-raw-overflow",
    "raw-terminal-status-overflow", "raw-terminal-signal-overflow",
    "raw-terminal-branch-zero", "raw-terminal-branch-overflow",
    "raw-unused-p-alloc-b", "raw-unused-p-alloc-c", "raw-unused-p-alloc-d",
    "raw-unused-t-alloc-c", "raw-unused-t-alloc-d",
    "raw-unused-tid-assign-b", "raw-unused-tid-assign-c",
    "raw-unused-tid-assign-d", "raw-unused-abort-b",
    "raw-unused-abort-c", "raw-unused-abort-d",
    "raw-pool-expanded-node-budget-over",
    "raw-pool-expanded-depth-over",
    "raw-pool-preflight-aggregate-byte-over",
    "raw-pool-preflight-aggregate-node-over",
    "raw-key-capture-u64-overflow",
}
RAW_FULL_MATRIX_FROZEN = False
ORDINARY_REQUIRED = {
    "immediate-exit", "preparation-abort", "assigned-tid-abort",
    "late-clone-abort", "birth-after-runnable", "duplicate-terminal",
    "missing-birth", "ref-resurrection", "active-tid-alias",
    "retained-thread-ref", "retained-process-ref", "authority-revoked",
    "zombie-before-after-reap", "main-storage-held", "vm-held",
    "teardown-failure", "launcher-loss", "missing-end", "buffer-full",
    "counter-overflow", "attempt-counter-overflow", "unfinished-reservation",
    "wrong-raw-terminal", "wrong-capture", "wrong-os-generation",
    "wrong-application", "wrong-process", "wrong-exec", "wrong-domain",
    "thread-only-exit", "last-thread-exit", "live-sibling-retirement",
    "competing-group-orders", "inherited-status", "tid-reuse",
    "application-limit", "process-limit", "thread-limit",
    "end-after-complete-end", "end-after-incomplete-end",
    "operation-after-end", "wrong-key-after-end",
    "launcher-loss-after-end", "teardown-fail-after-end",
}
MUTANTS = {
    "birth-after-runnable": "birth-after-runnable",
    "early-retirement": "retained-thread-ref",
    "silent-loss": "buffer-full",
    "tid-aliasing": "active-tid-alias",
}

class ValidationError(Exception):
    pass

def require(condition, message="invalid input"):
    if not condition:
        raise ValidationError(message)
OPS = {
    "P_ALLOC", "T_ALLOC", "TID_ASSIGN", "BIRTH", "RUNNABLE", "REF_ADD",
    "REF_DROP", "RETIRE_BEGIN", "RETIRE_DONE", "ABORT", "TERMINAL",
    "ZOMBIE_SET", "PARENT_REAP", "VM_RELEASE", "MAIN_STORAGE_RELEASE",
    "LAUNCHER_LOSS", "CAPTURE_END", "TEARDOWN_FAIL",
}

def strict_bytes(raw):
    require(isinstance(raw, bytes) and len(raw) <= MAX_JSON)
    def pairs(items):
        result = {}
        for name, value in items:
            require(name not in result, "duplicate key")
            result[name] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValidationError(value)))
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, ValueError) as error:
        raise ValidationError("invalid JSON") from error

def strict_file(path):
    path = pathlib.Path(path)
    assert path.is_absolute() and path.resolve() == path and path.is_file()
    raw = path.read_bytes()
    assert raw.rstrip().endswith(b"}") and b"\x00" not in raw
    return strict_bytes(raw)

class ExpansionBudget:
    def __init__(self):
        self.nodes = 262144
        self.bytes = MAX_EXPANDED

    def take(self, value):
        self.nodes -= 1
        if value is None:
            cost = 4
        elif type(value) is bool:
            cost = 5
        elif type(value) is int:
            cost = len(str(value))
        elif isinstance(value, str):
            cost = 12 * len(value) + 2
        elif isinstance(value, list):
            cost = max(2, len(value) + 1)
        else:
            cost = 2
        self.bytes -= cost
        require(self.nodes >= 0 and self.bytes >= 0, "expanded literal budget")

def scan_arity(value, budget, depth=0):
    require(depth <= 32, "pool depth")
    budget.take(value)
    if isinstance(value, dict):
        if set(value) == {"arg"}:
            index = value["arg"]
            require(type(index) is int and index >= 0, "placeholder")
            return index + 1
        greatest = 0
        for item in value.values():
            greatest = max(greatest, scan_arity(item, budget, depth + 1))
        return greatest
    if isinstance(value, list):
        greatest = 0
        for item in value:
            greatest = max(greatest, scan_arity(item, budget, depth + 1))
        return greatest
    require(value is None or type(value) in (str, int, bool), "literal type")
    return 0

def analyze_pools(pools):
    require(isinstance(pools, dict))
    require(all(isinstance(name, str) and name for name in pools))
    arity_budget = ExpansionBudget()
    arities = {name: scan_arity(body, arity_budget) for name, body in pools.items()}
    dependencies = {name: set() for name in pools}
    syntax_budget = ExpansionBudget()

    def inspect(value, owner, depth=0):
        require(depth <= 32, "pool depth")
        syntax_budget.take(value)
        if isinstance(value, dict):
            if set(value) == {"arg"}:
                index = value["arg"]
                require(type(index) is int and 0 <= index < arities[owner], "placeholder")
                return
            require(set(value) in ({"pool"}, {"pool", "args"}), "pool reference")
            name = value.get("pool")
            require(isinstance(name, str) and name in pools, "unknown pool")
            supplied = value.get("args", [])
            require(isinstance(supplied, list) and len(supplied) == arities[name], "pool arity")
            dependencies[owner].add(name)
            for item in supplied:
                inspect(item, owner, depth + 1)
            return
        if isinstance(value, list):
            for item in value:
                inspect(item, owner, depth + 1)
            return
        require(value is None or type(value) in (str, int, bool), "literal type")

    for name, body in pools.items():
        inspect(body, name)

    visiting, longest_paths = set(), {}
    def visit(name, depth=0):
        require(depth <= 32 and name not in visiting, "pool cycle or dependency depth")
        if name in longest_paths:
            return longest_paths[name]
        visiting.add(name)
        longest = 1
        for dependency in dependencies[name]:
            longest = max(longest, 1 + visit(dependency, depth + 1))
        visiting.remove(name)
        require(longest <= 32, "pool dependency depth")
        longest_paths[name] = longest
        return longest
    for name in pools:
        visit(name)
    return arities

def literal_expand(value, pools, args=(), stack=(), budget=None, depth=0, arities=None):
    """Acyclic literal substitution only; no transition or arithmetic evaluation."""
    if budget is None:
        budget = ExpansionBudget()
    if arities is None:
        arities = analyze_pools(pools)
    require(depth <= 32 and len(stack) <= 32, "expansion depth")
    budget.take(value)
    if isinstance(value, dict):
        if set(value) == {"arg"}:
            index = value["arg"]
            require(type(index) is int and 0 <= index < len(args), "placeholder")
            return literal_expand(args[index], {}, (), (), budget, depth + 1, {})
        require(set(value) in ({"pool"}, {"pool", "args"}), "pool reference")
        name = value["pool"]
        require(isinstance(name, str) and name in pools and name not in stack, "pool reference")
        supplied = value.get("args", [])
        require(isinstance(supplied, list) and len(supplied) == arities[name], "pool arity")
        expanded_args = [literal_expand(item, pools, args, stack, budget, depth + 1, arities) for item in supplied]
        return literal_expand(pools[name], pools, expanded_args, stack + (name,), budget, depth + 1, arities)
    if isinstance(value, list):
        result = []
        for item in value:
            result.append(literal_expand(item, pools, args, stack, budget, depth + 1, arities))
        return result
    require(value is None or type(value) in (str, int, bool), "literal type")
    return value

def checked_expansion(value, pools):
    result = literal_expand(value, pools, budget=ExpansionBudget())
    require(len(json.dumps(result, separators=(",", ":")).encode()) <= MAX_EXPANDED,
            "expanded literal budget")
    return result

def integer(value, low=0, high=(1 << 64) - 1):
    require(type(value) is int and low <= value <= high, "integer")
    return value

def key(value, process=False):
    require(isinstance(value, list) and len(value) == 7, "key")
    result = [integer(item) for item in value]
    require(result[0] and result[2] and result[3] and result[4] and result[6], "key")
    require((result[5] == 0) if process else (result[5] != 0), "key domain")
    return result

def operation(raw, expected_id):
    require(isinstance(raw, list) and len(raw) == 8, "operation")
    op_id, name, subject, parent, a, b, c, d = raw
    require(integer(op_id, 1, 128) == expected_id and type(name) is str and name in OPS,
            "operation identity")
    if name in ("LAUNCHER_LOSS", "CAPTURE_END"):
        require(subject is None and parent is None, "capture-wide subject")
        subject_wire = parent_wire = [0] * 7
    else:
        require(isinstance(subject, list) and len(subject) == 7, "subject")
        process_subject = subject[5] == 0
        subject_wire = key(subject, process=process_subject)
        if name == "P_ALLOC":
            require(process_subject and parent is None, "process allocation")
            parent_wire = [0] * 7
        elif name == "T_ALLOC":
            require(not process_subject, "thread allocation")
            parent_wire = key(parent, process=True)
        else:
            require(parent is None, "unexpected parent")
            parent_wire = [0] * 7
    args = [integer(item) for item in (a, b, c, d)]
    if name == "P_ALLOC":
        integer(a, 1, (1 << 31) - 1); require(b == c == d == 0, "unused argument")
    elif name == "T_ALLOC":
        integer(a, 0, (1 << 31) - 1); require(b in (0, 1) and c == d == 0, "thread arguments")
    elif name == "TID_ASSIGN":
        integer(a, 1, (1 << 31) - 1); require(b == c == d == 0, "unused argument")
    elif name == "ABORT":
        integer(a, 1, 255); require(b == c == d == 0, "abort arguments")
    elif name == "TERMINAL":
        integer(a, 0, (1 << 32) - 1); integer(b, 0, 255)
        integer(c, 0, 255); integer(d, 1, 4)
    else:
        require(a == b == c == d == 0, "unused argument")
    return [op_id, name, *subject_wire, *parent_wire, *args]

def wire(vector, input_pools):
    capacity = integer(vector["event_capacity"], 0, 256)
    seed = vector["seed"]
    require(type(seed) is str and seed in ("NONE", "ATTEMPTS_MAX", "LOST_MAX", "RESERVATION_ONE"), "seed")
    operations = checked_expansion(vector["operations"], input_pools)
    require(isinstance(operations, list) and 0 < len(operations) <= 128, "operation count")
    rows = [f"MODEL2 {capacity} {seed}"]
    for index, raw in enumerate(operations, 1):
        rows.append(" ".join(map(str, operation(raw, index))))
    return ("\n".join(rows) + "\n").encode("ascii")

def expected_rows(document, name):
    rows = checked_expansion(document["vectors"][name], document["pools"])
    assert isinstance(rows, list) and rows
    for index, row in enumerate(rows, 1):
        validate_output_row(row, index)
    return rows

def nullable_key(value, process=None):
    if value is None:
        return
    assert isinstance(value, list) and len(value) == 7
    for item in value:
        integer(item)
    if process is True:
        assert value[5] == 0
    elif process is False:
        assert value[5] != 0

def terminal(value):
    if value is None:
        return
    assert isinstance(value, list) and len(value) == 4
    integer(value[0], 0, (1 << 32) - 1)
    integer(value[1], 0, 255); integer(value[2], 0, 255); integer(value[3], 1, 4)

def process_row(row):
    assert isinstance(row, list) and len(row) == 13
    nullable_key(row[0], True); nullable_key(row[1], True)
    integer(row[2], 1, (1 << 31) - 1)
    assert row[3] in ("Allocated", "Born", "Aborted", "Terminal", "Retiring", "Retired")
    integer(row[4], 0, (1 << 32) - 1); assert row[5] in ("E", "N")
    terminal(row[6]); integer(row[7], 0, 255); nullable_key(row[8], False)
    assert type(row[9]) is type(row[10]) is type(row[11]) is bool
    if row[12] is not None:
        assert isinstance(row[12], list) and len(row[12]) == 3
        nullable_key(row[12][0], True); terminal(row[12][1]); integer(row[12][2], 0, 255)

def thread_row(row):
    assert isinstance(row, list) and len(row) == 11
    nullable_key(row[0], False); nullable_key(row[1], True)
    integer(row[2], 1, (1 << 31) - 1); integer(row[3], 0, (1 << 31) - 1)
    assert type(row[4]) is bool
    assert row[5] in ("Allocated", "Born", "Runnable", "Aborted", "Terminal", "Retiring", "Retired")
    integer(row[6], 0, (1 << 32) - 1); assert row[7] in ("E", "N")
    terminal(row[8]); integer(row[9], 0, 255)
    if row[10] is not None:
        assert isinstance(row[10], list) and len(row[10]) == 3
        nullable_key(row[10][0], False); terminal(row[10][1]); integer(row[10][2], 0, 255)

def validate_output_row(row, expected_id):
    assert isinstance(row, list) and len(row) == 6
    assert integer(row[0], 1, 128) == expected_id
    assert row[1] in ("OK", "SCHEMA", "KEY", "STATE", "IDENTITY", "REF", "BUSY", "STATUS", "LIMIT", "CLOSED")
    assert isinstance(row[2], list)
    for event in row[2]:
        assert isinstance(event, list) and len(event) == 11
        assert integer(event[0]) == 1; integer(event[1], 1); integer(event[2], 1, 128)
        assert isinstance(event[3], str) and event[3]
        nullable_key(event[4]); nullable_key(event[5], True)
        if event[6] is not None: integer(event[6], 1, (1 << 31) - 1)
        if event[7] is not None: integer(event[7], 0, (1 << 31) - 1)
        assert isinstance(event[8], list) and len(event[8]) == 5
        integer(event[8][0], 0, (1 << 32) - 1)
        for item in event[8][1:]: integer(item, 0, 255)
        assert integer(event[9]) == 1 and integer(event[10]) == event[2]
    assert isinstance(row[3], list) and isinstance(row[4], list)
    for item in row[3]: process_row(item)
    for item in row[4]: thread_row(item)
    control = row[5]
    assert isinstance(control, list) and len(control) == 7
    integer(control[0]); integer(control[1]); integer(control[2])
    assert type(control[3]) is type(control[4]) is type(control[5]) is bool
    integer(control[6])

def run(command, data):
    result = subprocess.run(command, input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=10, check=False)
    assert result.returncode == 0 and not result.stderr
    assert len(result.stdout) <= MAX_OUTPUT
    rows = [strict_bytes(line) for line in result.stdout.splitlines()]
    for index, row in enumerate(rows, 1):
        validate_output_row(row, index)
    return rows

def assert_oracle_match(want, rust_rows, c_rows):
    assert rust_rows == want and c_rows == want and rust_rows == c_rows

def compiler(path):
    path = pathlib.Path(path)
    assert path.is_absolute() and path.resolve() == path and path.is_file()
    return str(path)

def build(args, output):
    rust, cref = output / "model-rust", output / "model-c"
    subprocess.run([compiler(args.rustc), "--edition=2021", "-Dwarnings", "-o",
                    str(rust), str(HERE / "model.rs")], check=True, timeout=60)
    subprocess.run([compiler(args.cc), "-std=c11", "-Wall", "-Wextra", "-Werror",
                    "-O2", "-o", str(cref), str(HERE / "reference.c")],
                   check=True, timeout=60)
    return rust, cref

def validate_input_document(document, require_nested_empty=False):
    require(isinstance(document, dict), "document")
    require(set(document) == {"schema_version", "model_only", "corpus_complete", "pools", "vectors", "raw_invalid", "mutants"}, "document fields")
    require(type(document["schema_version"]) is int and document["schema_version"] == 2, "schema version")
    require(document["model_only"] is True, "model-only flag")
    require(type(document["corpus_complete"]) is bool, "corpus flag")
    require(isinstance(document["pools"], dict), "pools")
    analyze_pools(document["pools"])
    require(isinstance(document["vectors"], list), "vectors")
    require(isinstance(document["raw_invalid"], list), "raw cases")
    if require_nested_empty:
        require(document["raw_invalid"] == [], "nested raw cases")
    require(isinstance(document["mutants"], dict), "mutants")
    seen = set()
    for vector in document["vectors"]:
        require(isinstance(vector, dict), "vector")
        require(set(vector) == {"name", "coverage", "event_capacity", "seed", "operations"}, "vector fields")
        name = vector["name"]
        coverage = vector["coverage"]
        require(isinstance(name, str) and name and name not in seen, "vector name")
        require(isinstance(coverage, list) and coverage, "coverage")
        require(all(isinstance(item, str) and item for item in coverage), "coverage")
        require(len(set(coverage)) == len(coverage), "coverage")
        seen.add(name)
        wire(vector, document["pools"])
    return seen

def validate_expected_document(document, names):
    assert isinstance(document, dict)
    assert set(document) == {"schema_version", "model_only", "corpus_complete", "pools", "vectors"}
    assert type(document["schema_version"]) is int and document["schema_version"] == 2
    assert document["model_only"] is True and type(document["corpus_complete"]) is bool
    assert isinstance(document["pools"], dict) and isinstance(document["vectors"], dict)
    analyze_pools(document["pools"])
    assert names == set(document["vectors"])
    for name in names:
        expected_rows(document, name)

def validate_raw_records(records):
    seen = set()
    for record in records:
        assert isinstance(record, dict) and set(record) == {"name", "coverage", "source", "expected"}
        name, coverage = record["name"], record["coverage"]
        assert isinstance(name, str) and name and name not in seen
        assert isinstance(coverage, list) and coverage
        assert all(isinstance(item, str) and item for item in coverage)
        assert len(set(coverage)) == len(coverage)
        assert isinstance(record["expected"], dict)
        assert set(record["expected"]) == set(RAW_EXPECTED)
        assert record["expected"]["stage"] == "harness"
        assert type(record["expected"]["exit_code"]) is int and record["expected"]["exit_code"] == 2
        assert record["expected"]["stdout_hex"] == record["expected"]["stderr_hex"] == ""
        assert type(record["expected"]["model_invocations"]) is int and record["expected"]["model_invocations"] == 0
        source = record["source"]
        assert isinstance(source, dict)
        assert set(source) in ({"inline_utf8"}, {"artifact"})
        if "inline_utf8" in source:
            assert isinstance(source["inline_utf8"], str)
            assert len(source["inline_utf8"].encode("utf-8")) <= MAX_JSON
        else:
            assert name == "raw-oversized-document"
            artifact = source["artifact"]
            assert set(artifact) == {"path", "sha256", "size"}
            assert isinstance(artifact["path"], str)
            assert isinstance(artifact["sha256"], str) and len(artifact["sha256"]) == 64
            assert artifact["sha256"] == artifact["sha256"].lower()
            assert all(char in "0123456789abcdef" for char in artifact["sha256"])
            assert artifact["path"] == "scripts/tests/fixtures/native-lifecycle-model-v1/raw-invalid/oversized-document.json"
            assert type(artifact["size"]) is int and artifact["size"] == MAX_RAW_ARTIFACT
        seen.add(name)
    return seen

def artifact_bytes(description):
    spelling = description["path"]
    assert isinstance(spelling, str) and spelling and not spelling.startswith("/")
    assert "//" not in spelling
    components = spelling.split("/")
    assert all(component not in ("", ".", "..") for component in components)
    relative = pathlib.PurePosixPath(spelling)
    prefix = pathlib.PurePosixPath("scripts/tests/fixtures/native-lifecycle-model-v1")
    assert not relative.is_absolute() and relative.parts[:len(prefix.parts)] == prefix.parts
    root = HERE.parents[3]
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in relative.parts[:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=directory)
    finally:
        os.close(directory)
    try:
        before = os.fstat(descriptor)
        assert stat.S_ISREG(before.st_mode)
        assert before.st_size == description["size"] <= MAX_RAW_ARTIFACT
        chunks, total = [], 0
        while True:
            chunk = os.read(descriptor, min(65536, MAX_RAW_ARTIFACT + 1 - total))
            if not chunk:
                break
            chunks.append(chunk); total += len(chunk)
            assert total <= MAX_RAW_ARTIFACT
        raw = b"".join(chunks)
        after = os.fstat(descriptor)
        assert (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        assert len(raw) == description["size"]
        assert hashlib.sha256(raw).hexdigest() == description["sha256"]
        return raw
    finally:
        os.close(descriptor)

def raw_source_bytes(record):
    source = record["source"]
    if "inline_utf8" in source:
        return source["inline_utf8"].encode("utf-8")
    return artifact_bytes(source["artifact"])

def decode_raw_document(raw):
    document = strict_bytes(raw)
    validate_input_document(document, require_nested_empty=True)

def decoder_mode():
    raw = sys.stdin.buffer.read(MAX_RAW_ARTIFACT + 1)
    try:
        decode_raw_document(raw)
    except ValidationError:
        return 2
    return 0

def bounded_child(command, raw):
    with tempfile.TemporaryFile() as stdin:
        stdin.write(raw); stdin.seek(0)
        process = subprocess.Popen(command, stdin=stdin, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        streams = {process.stdout: bytearray(), process.stderr: bytearray()}
        selector = None
        try:
            selector = selectors.DefaultSelector()
            for stream in streams:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ)
            deadline = time.monotonic() + 5
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError("raw decoder timeout")
                ready = selector.select(remaining)
                if not ready:
                    raise AssertionError("raw decoder timeout")
                for key, _ in ready:
                    stream = key.fileobj
                    chunk = os.read(stream.fileno(), MAX_RAW_STREAM + 1 - len(streams[stream]))
                    if not chunk:
                        selector.unregister(stream); stream.close()
                        continue
                    streams[stream].extend(chunk)
                    if len(streams[stream]) > MAX_RAW_STREAM:
                        raise AssertionError("raw decoder output bound")
            try:
                process.wait(timeout=max(0.0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as error:
                raise AssertionError("raw decoder timeout") from error
        finally:
            try:
                if selector is not None:
                    selector.close()
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait()
                for stream in streams:
                    if not stream.closed:
                        stream.close()
        return process.returncode, bytes(streams[process.stdout]), bytes(streams[process.stderr])

def raw_child(raw):
    return bounded_child(
        [sys.executable, str(HERE / "harness.py"), "--decode-raw-document"], raw)

def check_raw_invalid(vectors, expected):
    names = validate_input_document(vectors)
    validate_expected_document(expected, names)
    raw_names = validate_raw_records(vectors["raw_invalid"])
    assert raw_names == RAW_MECHANISM_REQUIRED
    for record in vectors["raw_invalid"]:
        code, out, err = raw_child(raw_source_bytes(record))
        assert code == 2 and out == b"" and err == b""
    return names, raw_names

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--decode-raw-document", action="store_true")
    parser.add_argument("--check-raw-invalid", action="store_true")
    parser.add_argument("--rustc")
    parser.add_argument("--cc")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    assert not (args.decode_raw_document and args.check_raw_invalid)
    if args.decode_raw_document:
        assert args.rustc is args.cc is args.output is None
        return decoder_mode()
    vectors = strict_file(HERE / "vectors.json")
    expected = strict_file(HERE / "expected.json")
    names = validate_input_document(vectors)
    validate_expected_document(expected, names)
    validate_raw_records(vectors["raw_invalid"])
    if args.check_raw_invalid:
        assert args.rustc is args.cc is args.output is None
        check_raw_invalid(vectors, expected)
        return 0
    assert args.rustc is not None and args.cc is not None and args.output is not None
    assert args.output.is_absolute() and not args.output.exists()
    checked_names, _ = check_raw_invalid(vectors, expected)
    assert checked_names == names == ORDINARY_REQUIRED
    assert vectors["corpus_complete"] is expected["corpus_complete"] is True
    assert RAW_FULL_MATRIX_FROZEN
    assert vectors["mutants"] == MUTANTS
    args.output.mkdir(mode=0o700)
    rust, cref = build(args, args.output)
    seen = set()
    for vector in vectors["vectors"]:
        assert set(vector) == {"name", "coverage", "event_capacity", "seed", "operations"}
        name = vector["name"]
        assert isinstance(name, str) and name not in seen
        assert isinstance(vector["coverage"], list) and vector["coverage"]
        seen.add(name)
        want = expected_rows(expected, name)
        rust_rows = run([str(rust)], wire(vector, vectors["pools"]))
        c_rows = run([str(cref)], wire(vector, vectors["pools"]))
        assert_oracle_match(want, rust_rows, c_rows)
    assert seen == set(expected["vectors"])
    assert vectors["mutants"] == MUTANTS
    directory = os.open(args.output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)

if __name__ == "__main__":
    sys.exit(main())
