"""Functional McKernel OS review only; no security testing. Offline exact captures."""
import ast
import hashlib
import json
import re
from pathlib import Path

D = Path(__file__).resolve().parent
M = D.parent
E = next(p for p in D.parents if p.name == "os-recovery-adoption-20261025-0254")


def ref(path):
    path = Path(path)
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def emit(name, obj):
    p = D / name
    with p.open("x") as f:
        json.dump(obj, f, indent=2, sort_keys=True)
        f.write("\n")
    return ref(p)


static = json.loads((M / "STATIC-NATIVE-BINDINGS.NOT-RELEASED.json").read_text())
serial_path = D / "RAW-ATTEMPT/serial.log"
serial = serial_path.read_text()
lines = serial.splitlines()
reports = [json.loads(l[len("ND_PAYLOAD "):]) for l in lines if l.startswith("ND_PAYLOAD ")]
assert len(reports) == 1
report = reports[0]
contract_ref = static["executor_contract"]
assert ref(contract_ref["path"]) == contract_ref
contract = json.loads(Path(contract_ref["path"]).read_text())["cases"]["startup.argv-empty"]
assert report["argv"] == contract["argv"] == static["expected_guest_argv"]
assert report["cwd"] == contract["cwd"]
assert report["env"] == contract["environment"]
assert report["raw_wait_status"] == 0
assert report["procfs_empty"] is True
assert report["started_ns"] < report["reaped_ns"] <= report["finished_ns"]
assert report["reaped_ns"] - report["started_ns"] < 10_000_000_000
assert report["finished_ns"] - report["reaped_ns"] < 5_000_000_000
for stream, expected in (("stdout", contract["oracle"]["stdout_hex"]), ("stderr", "")):
    s = report["streams"][stream]
    n = len(bytes.fromhex(expected))
    assert s["hex"] == expected
    assert s["observed"] == s["retained"] == n
    assert s["discarded"] == 0 and s["limit"] == 1024
    assert s["eof"] is True and s["truncated"] is False
    assert report["started_ns"] <= s["eof_ns"] <= report["finished_ns"]
assert len(bytes.fromhex(report["streams"]["stdout"]["hex"])) == 91
prefix = "os=0 generation=1 pid=258"
terminal = [i for i,l in enumerate(lines) if re.search(r"application_syscall=delivered "+prefix+r" .*number=231$", l)]
assert len(terminal) == 1
selected = [{"line": i+1, "text": l} for i,l in enumerate(lines)
            if prefix in l and any(x in l for x in (
                "application SCHEDULE ", "application procfs published ",
                "application procfs deleted ", "application_process=cleanup_requested ",
                "application cleanup ACK ", "application retirement "))]
assert sum("application SCHEDULE " in x["text"] for x in selected) == 1
assert sum("application procfs published " in x["text"] for x in selected) == 1
assert sum("application procfs deleted " in x["text"] for x in selected) == 1
retirements = [x for x in selected if "application retirement " in x["text"]]
assert len(retirements) == 1 and retirements[0]["text"].endswith("token=513 errno=-11")

# Execute only these three original pure AST nodes, never the evaluator module,
# its imports, observation commands, manifest helper main, or guest entry.
evaluator = Path(static["evaluator_source"]["path"])
assert ref(evaluator) == static["evaluator_source"]
source = evaluator.read_text()
tree = ast.parse(source)
names = {"DiagnosticError", "_need", "_check_begin_cleanup"}
nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
assert {n.name for n in nodes} == names
ns = {"re": re}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(evaluator), "exec"), ns)
try:
    ns["_check_begin_cleanup"](serial, prefix, terminal[0])
except ns["DiagnosticError"] as error:
    replay_error = str(error)
else:
    raise AssertionError("Original strict predicate unexpectedly accepted")
assert replay_error == "BEGIN retirement result"
attempt = json.loads((D / "RAW-ATTEMPT/result.json").read_text())
assert attempt["status"] == "FAIL"
assert attempt["failure"] == {"error": replay_error, "phase": "evaluation", "type": "DiagnosticError"}
assert attempt["cleanup"] == {"errors": [], "reaped": True}
assert attempt["capture_errors"] == []
assert attempt["qemu_evidence"]["pid"] == 10 and attempt["qemu_evidence"]["returncode"] == -9
qmp = json.loads((D / "RAW-ATTEMPT/qmp.transcript.json").read_text())
received = []
for row in qmp:
    if row["direction"] == "received":
        received.extend(json.loads(l) for l in bytes.fromhex(row["raw_hex"]).decode().splitlines())
statuses = [x["return"]["status"] for x in received if isinstance(x.get("return"),dict) and "status" in x["return"]]
assert "running" in statuses and "shutdown" in statuses
free = json.loads((D / "CURRENT-FREE.json").read_text())
assert free["current_free"] is True and free["normal_owned_retirement"] is True
source_dir = E / "m15-rust-startup-supervisor-source-1"
main = (source_dir / "main.rs").read_text()
supervisor = (source_dir / "supervisor.rs").read_text()
assert "if startup_retirement_ready(current, end, procfs_empty())?" in main
assert "pub fn startup_retirement_ready(current: u64, end: u64, namespace: Check<bool>) -> Check<bool>" in supervisor
assert "    namespace\n}" in supervisor
assert main.index("startup_retirement_ready(current, end, procfs_empty())?") < main.index("let count = unsafe { klogctl(3,")
sources = [ref(source_dir / n) for n in ("main.rs", "supervisor.rs", "profile.rs", "report.rs")]
proof = {
    "scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.",
    "independent": True,
    "reviewer": "/root/custody_release_review",
    "decision": "FAIL_ORIGINAL_BEGIN_RETIREMENT_PREDICATE_REPRODUCED_WITH_EXACT_STARTUP_MAIN_BYTES",
    "nonce": static["nonce"],
    "actual_serial": ref(serial_path),
    "full_capture_manifest": ref(D / "RAW-CAPTURE-MANIFEST.json"),
    "actual_attempt_result": ref(D / "RAW-ATTEMPT/result.json"),
    "actual_qmp_transcript": ref(D / "RAW-ATTEMPT/qmp.transcript.json"),
    "qmp_statuses_observed": sorted(set(statuses)),
    "original_contract": contract_ref,
    "exact_report": report,
    "stdout_utf8": bytes.fromhex(report["streams"]["stdout"]["hex"]).decode(),
    "stdout_bytes": 91,
    "stderr_bytes": 0,
    "raw_wait_status": 0,
    "syscall_terminal": {"line": terminal[0]+1, "text": lines[terminal[0]]},
    "selected_actual_lifecycle_rows": selected,
    "predicate": {
        "source": ref(evaluator),
        "function": "_check_begin_cleanup",
        "line": 1338,
        "exact_expression": "all(a[2]==-11 for a in attempts[:-1]) and attempts[-1][2]==0",
        "offline_original_pure_AST_replay": {"result": "DiagnosticError", "message": replay_error},
        "actual_query_tokens_and_errno": [{"token": 513, "errno": -11}],
        "final_errno_zero_observed": False,
        "ACK_abandoned_one_is_permitted_by_original_contract": True,
        "full_evaluator_replay": False,
        "full_evaluator_replay_limit": "The original FAIL path does not retain all host observation timestamps. None were invented. Only the exact original pure failing predicate was replayed. No subsequent gate is claimed passed."
    },
    "collector_source": sources,
    "source_cause": {
        "main_lines": [319,335,350,359],
        "supervisor_lines": [83,90],
        "observed": "The sole retirement query returns -11 before procfs deletion. The exact final serial snapshot contains deletion and ND_PAYLOAD but no final query returning0.",
        "source_fact": "After payload reap the Rust collector finishes on readable empty numeric procfs, then emits one raw klogctl(3) snapshot; the readiness helper does not require definitive application retirement.",
        "inference": "This completion condition permits publication before the pinned BEGIN retirement contract is satisfied. The evidence demonstrates an observation/completion mismatch; it does not establish eventual retirement, a kernel leak, or a Rust executor fault.",
        "smallest_next_source_correction": "In the existing Rust startup collector, bind the sole actual scheduled application's os/generation/PID and require its genuine terminal, successful real cleanup ACK, deletion and final retirement query errno0 before final publication, within the existing absolute5s postreap/outer deadlines. Preserve raw bytes, all unknown/duplicate/malformed-row checks, exact argv/two environment values,10s payload/1024B streams and the unchanged original evaluator. Reuse qualified Rust lifecycle parsing where applicable; introduce no F05 G gate/child protocol, fixed grace sleep, normalized errno, C helper or new runtime quota.",
        "correction_implemented_by_reviewer": False
    },
    "ownership": {"current_free": ref(D / "CURRENT-FREE.json"), "actual_QEMU_positive_reap": attempt["qemu_evidence"], "cleanup": attempt["cleanup"], "QEMU_pid_namespace_note": "PID10 is the namespaced QEMU identity. No comparison with hostPID10 or reviewer signal was performed."},
    "preserved": ["Earlier wrong-argv startup FAIL", "Original strict235/227 and F05 v2 FAILs", "F05 v3 native success remains its separate exact tuple", "WholeFP4096/1024FAIL", "No349/51/354/allocation/file/native-closure inference"],
    "native_acceptance": False,
    "runtime_execution_by_this_offline_review": 0
}
proof_ref = emit("TRACE-AND-FAILURE-PROOF.json", proof)
binding_keys = ["collector", "compiled_collector_HOST_acceptance", "compiled_collector_adoption", "compiled_collector_caseprofile", "compiled_collector_facts", "composed_case_binding", "stage_map_acceptance", "overlay", "offline_manifest", "owner_source", "evaluator_source", "payload", "executor_contract", "loader_acceptance"]
review = {
    "scope": proof["scope"],
    "decision": "FAIL_NATIVE_STARTUP_RETIREMENT_WITH_EXACT91B_MAIN_RESULT_AND_PASS_CURRENT_FREE",
    "independent": True,
    "implementation_ownership": False,
    "reviewer": "/root/custody_release_review",
    "nonce": static["nonce"],
    "nonce_consumed": True,
    "actual_guest_started": True,
    "actual_main_behavior": {"case": "startup.argv-empty", "argv": report["argv"], "stdout_bytes": 91, "stderr_bytes": 0, "raw_wait_status": 0, "exact_oracle_bytes": True, "stream_EOF_no_discard_no_truncation": True},
    "native_acceptance": False,
    "application_acceptance": False,
    "blocker": "Original BEGIN retirement result: the sole actual query token513 returned -11; definitive query errno0 is absent from the full captured serial. Procfs_empty alone does not prove it.",
    "failure_stage": "Postguest evaluation; QEMU ran and reached shutdown. Outer docker start OwnerError is downstream propagation of native evaluation failure, not a preguest failure.",
    "exact_original_predicate_reproduced": True,
    "executor_or_kernel_bug_established": False,
    "current_free": ref(D / "CURRENT-FREE.json"),
    "current_free_acceptance": True,
    "main_execution_diagnosis": proof_ref,
    "static_bindings": ref(M / "STATIC-NATIVE-BINDINGS.NOT-RELEASED.json"),
    "execution_review": ref(M / "ACTUAL-INDEPENDENT-NATIVE-EXECUTION-REVIEW.json"),
    "actual_tool_join": ref(M / "CAPTURE/JOINED.json"),
    "original_bridge_join": ref(M / "ROOT-ONCE-ENTRY.JOINED.json"),
    "retained_accepted_artifact_bindings_reused": {k: static[k] for k in binding_keys},
    "selected_executor_sha256": static["expected_executor_sha256"],
    "selected_image_sha256": static["expected_new_image_sha256"],
    "retained_source_and_stage_reuse_scope": "Exact prior stage/HOST/loader and execution reviews are reused, without recompiling or broadly rehashing unchanged archive/toolchain/source inputs. Native result is independently read from complete actual captures.",
    "preserved_failures_and_limits": proof["preserved"],
    "case_or_file_credit_delta": 0,
    "new_execution_authority": None,
    "reviewer_workloads_compilers_cleanup_signals_retries": 0,
    "next_step": proof["source_cause"]["smallest_next_source_correction"]
}
review_ref = emit("REVIEW.json", review)
for item in (proof_ref, review_ref):
    print(json.dumps(item, sort_keys=True))
