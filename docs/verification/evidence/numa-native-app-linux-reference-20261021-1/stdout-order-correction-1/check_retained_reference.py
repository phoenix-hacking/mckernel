#!/usr/bin/env python3
"""Source-bound retained-evidence check; never compiles or launches the payload.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execution requires the dispatcher's ordinary-profile grant. No native credit.
"""
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent
EXPECTED = (b"numa allowed=1 interval=1 queries=9 mode=1 mask=1 "
            b"neighbors=2 process=1 guards=1 bytes=12288 preserved=1 unmapped=1\n")
OLD = (b"numa allowed=1 interval=1 queries=9 mode=1 mask=1 "
       b"guards=1 neighbors=2 process=1 bytes=12288 preserved=1 unmapped=1\n")
INPUTS = {
    "numa_interval_app.rs": "0863c1e9ef2c3777f6ac9baeab33283afeac99b5d5ea374546ee6b24be886936",
    "ORACLE-AND-PROPOSAL.md": "404adb9c987884a6f5ede4eac6ed40d1d9bf3bdb551756c30585dbb24f311927",
    "compile-reference-1/whole.json": "0ce8675b23e20c3f7309d2c26bbd3e3e803be1e4731e58dc313626813d085e4b",
    "compile-reference-1/02-linux-reference/stdout": "ba0adb908f3f118b325873878bcc336107b8953e9b7a7f9e9e5abd8f37931bf2",
    "compile-reference-1/02-linux-reference/stderr": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def streams_match(stdout, stderr, code):
    return stdout == EXPECTED and stderr == b"" and code == 37


def regression():
    require(streams_match(EXPECTED, b"", 37), "positive comparator vector")
    rejected = [
        (OLD, b"", 37),
        (EXPECTED[:-1], b"", 37),
        (EXPECTED + b"\n", b"", 37),
        (EXPECTED.replace(b"neighbors=2 ", b""), b"", 37),
        (EXPECTED.replace(b"queries=9", b"queries=8"), b"", 37),
        (EXPECTED, b"FAIL\n", 37),
        (EXPECTED, b"", 0),
        (EXPECTED, b"", -9),
    ]
    require(all(not streams_match(*v) for v in rejected), "negative comparator vector")
    return len(rejected) + 1


def main():
    vectors = regression()
    for name, digest in INPUTS.items():
        require(hashlib.sha256((PACKET / name).read_bytes()).hexdigest() == digest,
                "changed retained input: " + name)
    source = (PACKET / "numa_interval_app.rs").read_bytes()
    literals = re.findall(rb'^const PASS: &\[u8\] = b"([^"\r\n]*)";$', source, re.MULTILINE)
    require(len(literals) == 1, "ambiguous source PASS literal")
    # This exact literal has one LF escape and no other escapes. Refuse a new
    # escape form rather than decoding arbitrary source or copying actual output.
    require(literals[0].count(b"\\") == 1 and literals[0].endswith(b"\\n"),
            "unexpected source literal escaping")
    derived = literals[0][:-2] + b"\n"
    require(derived == EXPECTED == (HERE / "expected.stdout").read_bytes(),
            "source-derived expected bytes disagree")
    whole = json.loads((PACKET / "compile-reference-1/whole.json").read_bytes())
    require(whole["status"] == "FAIL_LINUX_REFERENCE_PRESERVE_NO_RETRY", "original failure missing")
    records = whole["records"]
    require(bytes.fromhex(records["expected_stdout_hex"]) == OLD, "failure family changed")
    require(sorted(OLD.split()) == sorted(EXPECTED.split()), "more than field order changed")
    stdout = (PACKET / "compile-reference-1/02-linux-reference/stdout").read_bytes()
    stderr = (PACKET / "compile-reference-1/02-linux-reference/stderr").read_bytes()
    require(bytes.fromhex(records["actual_stdout_hex"]) == stdout, "stdout receipt mismatch")
    require(records["actual_stderr_text"] == "" and stderr == b"", "stderr receipt mismatch")
    for label, code in (("compile", 0), ("reference", 37)):
        entry = records[label]
        require(entry["returncode"] == code and entry["timed_out"] is False,
                label + " status/timeout")
        require(entry["error"] is None and entry["retirement_error"] is None,
                label + " observer/retirement error")
        require(all(entry[k] is True for k in ("closed_streams", "direct_child_joined", "group_absent")),
                label + " incomplete closure")
        require(entry["remaining_group_members"] == [] and entry["unexpected_group_members"] == [],
                label + " group members")
    require(records["reference_normal_wait_status"] == 9472, "normal wait encoding")
    require(whole["ordinary_CPU_released_after_positive_closure"] is True, "ordinary grant closure")
    require(streams_match(stdout, stderr, records["reference"]["returncode"]), "retained exact oracle")
    print(json.dumps({"status": "PASS_RETAINED_LINUX_REFERENCE_EXPECTED_ORDER_CORRECTION",
                      "regression_vectors": vectors, "stdout_bytes": len(stdout),
                      "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                      "compile_or_app_rerun": False, "native_or_retirement_credit": False}, sort_keys=True))


if __name__ == "__main__":
    main()
