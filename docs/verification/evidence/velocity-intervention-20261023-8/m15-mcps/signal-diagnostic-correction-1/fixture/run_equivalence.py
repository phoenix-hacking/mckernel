#!/usr/bin/env python3
"""Prepared mcps original-script/Rust equivalence fixture. --execute requires grant.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse
import base64
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
BASE = Path(__file__).resolve().parent.parent

def cases():
    rows = b" PID  TID CPU STATUS COMMAND\n  17   17   1 RUNNING rust-app\n  23   24   2 SLEEPING worker --part=0\n"
    result = []
    def add(name, args=None, stdout=rows, stderr=b"", status=0, mode="executable", signal=None, stdin=b""):
        result.append(dict(name=name, args=args or [], stdout=stdout, stderr=stderr, status=status, mode=mode, signal=signal, stdin=stdin))
    add("synthetic-two-processes")
    add("empty-output", stdout=b"")
    add("header-only", stdout=b" PID TID CPU STATUS COMMAND\n")
    add("verbatim-bytes", stdout=b"\x00binary\xff\n  7 cmd with spaces\n")
    for args in [["--help"], ["-h"], ["--ps"], ["--kernel=/ignored"], ["--", "extra"], ["a b", "*", ""]]: add("ignored-args-" + str(len(result)), args=args)
    for status in [1, 2, 7, 126, 127, 255]: add("child-exit-" + str(status), stdout=b"", stderr=b"mcinspect: synthetic failure\n", status=status)
    add("mixed-streams", stderr=b"mcinspect: synthetic warning\n")
    add("inherited-stdin", stdin=b"synthetic input\x00\n")
    add("missing-command", stdout=b"", mode="missing")
    add("permission-denied", stdout=b"", mode="nonexecutable")
    add("directory-command", stdout=b"", mode="directory")
    # Full stdout/stderr/status parity is tested here too. Source candidate
    # explicitly has no claimed Bash signal-diagnostic closure yet; retain FAIL.
    add("child-sigterm-parity-open", stdout=b"", signal=15)
    add("child-sigkill-parity-open", stdout=b"", signal=9)
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--cc", default="/usr/bin/cc")
    ap.add_argument("--rustc", default="/home/holden/.rustup/toolchains/1.85.1-x86_64-unknown-linux-gnu/bin/rustc")
    ns = ap.parse_args()
    matrix = cases()
    if not ns.execute:
        print(json.dumps({"state": "PREPARED_ONLY", "cases": len(matrix), "open_signal_parity_cases": 2, "compilers_or_fixtures_run": False})); return 0
    output = BASE / "fixture-output"
    if output.exists(): raise SystemExit("Retain existing fixture-output; use a reviewed successor, no overwrite")
    output.mkdir()
    started = time.monotonic()
    prefix = output / "prefix"; (prefix / "bin").mkdir(parents=True)
    kernel = output / "kernel"  # Stub records argument; no real kernel or image access.
    program = prefix / "bin/mcinspect"
    reference = output / "mcps-original"
    source = (BASE / "reference/mcps.in").read_text()
    reference.write_text(source.replace("@prefix@", str(prefix)).replace("@MCKERNELDIR@", str(kernel)))
    reference.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith("MCPS_FIXTURE_") and k not in ["LD_PRELOAD", "LD_LIBRARY_PATH", "BASH_ENV", "ENV", "SHELLOPTS", "BASHOPTS"]}
    env.update(LC_ALL="C", MCPS_PREFIX=str(prefix), MCPS_MCKERNELDIR=str(kernel))
    cc = shutil.which(ns.cc); rustc = shutil.which(ns.rustc)
    if not cc or not rustc: raise SystemExit("Qualified host compilers not found")
    def remaining(limit):
        r = 120 - (time.monotonic() - started)
        if r <= 0: raise TimeoutError("120-second fixture envelope exhausted")
        return min(limit, r)
    # Own synthetic grandchildren as well as compiler/CLI leaders. This runs
    # only after --execute and its fresh host grant, never during preparation.
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    if libc.prctl(36, 1, 0, 0, 0) != 0: raise OSError(ctypes.get_errno(), "fixture child-subreaper admission failed")
    ownership = []
    def run_owned(command, child_env, timeout, data=None):
        command_timeout = remaining(timeout)
        p = subprocess.Popen(command, cwd=BASE, env=child_env, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        timed_out = False
        try:
            stdout, stderr = p.communicate(input=data, timeout=command_timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            stdout, stderr = p.communicate(timeout=2)
        # A conforming wrapper waits for its own worker. Unexpected adopted
        # descendants are killed/reaped; preserve failure and stop this batch.
        deadline = time.monotonic() + 2
        adopted = []
        while True:
            try: child, status = os.waitpid(-p.pid, os.WNOHANG)
            except ChildProcessError: break
            if child:
                adopted.append({"pid": child, "status": status}); continue
            try: os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            if time.monotonic() >= deadline: raise RuntimeError("fixture process-group retirement UNKNOWN; retain owner, stop")
            time.sleep(0.01)
        group_gone = False
        try: os.killpg(p.pid, 0)
        except ProcessLookupError: group_gone = True
        ownership.append({"leader": p.pid, "group": p.pid, "leader_status": p.returncode, "timed_out": timed_out, "adopted_reaps": adopted, "group_gone": group_gone})
        (output / "ownership.json").write_text(json.dumps(ownership, indent=2) + "\n")
        if timed_out or adopted or not group_gone:
            (output / "retirement-failure.stdout").write_bytes(stdout)
            (output / "retirement-failure.stderr").write_bytes(stderr)
            raise RuntimeError("fixture command failed/needed descendant retirement; originals retained, no retry")
        return subprocess.CompletedProcess(command, p.returncode, stdout, stderr)
    def build(command, label, limit):
        (output / (label + ".command.json")).write_text(json.dumps({"argv": command, "MCPS_PREFIX": str(prefix), "MCPS_MCKERNELDIR": str(kernel)}, indent=2) + "\n")
        p = run_owned(command, env, limit)
        (output / (label + ".stdout")).write_bytes(p.stdout); (output / (label + ".stderr")).write_bytes(p.stderr)
        if p.returncode: raise RuntimeError(label + " failed rc=" + str(p.returncode))
    obj = output / "mcps.o"; binary = output / "mcps-rust"
    build([rustc, "--edition=2021", "--crate-name", "mcps", "--crate-type=lib", "-C", "panic=abort", "-C", "opt-level=2", "-C", "relocation-model=pic", "--emit=obj=" + str(obj), str(BASE / "mcps.rs")], "rust-compile", 60)
    build([cc, "-fPIE", "-pie", str(obj), "-o", str(binary)], "rust-link", 20)
    case_dir = output / "invocation"; case_dir.mkdir()
    invocation = case_dir / "mcps"
    results = []
    for index, case in enumerate(matrix):
        if program.is_file() or program.is_symlink(): program.unlink()
        elif program.is_dir(): program.rmdir()
        if case["mode"] == "directory": program.mkdir()
        elif case["mode"] != "missing":
            program.write_bytes((BASE / "fixture/mcinspect_stub.py").read_bytes())
            program.chmod(0o755 if case["mode"] == "executable" else 0o644)
        observations = []
        for label, target in [("script", reference), ("rust", binary)]:
            if invocation.is_symlink(): invocation.unlink()
            invocation.symlink_to(target)
            trace_path = output / ("case-%02d-%s.trace.json" % (index, label))
            child_env = dict(env, MCPS_FIXTURE_TRACE=str(trace_path), MCPS_FIXTURE_SENTINEL="inherited-value", MCPS_FIXTURE_STDOUT=base64.b64encode(case["stdout"]).decode(), MCPS_FIXTURE_STDERR=base64.b64encode(case["stderr"]).decode(), MCPS_FIXTURE_STATUS=str(case["status"]))
            if case["stdin"]: child_env["MCPS_FIXTURE_STDIN"] = "1"
            if case["signal"]: child_env["MCPS_FIXTURE_SIGNAL"] = str(case["signal"])
            p = run_owned([str(invocation)] + case["args"], child_env, 3, case["stdin"])
            (output / ("case-%02d-%s.stdout" % (index, label))).write_bytes(p.stdout)
            (output / ("case-%02d-%s.stderr" % (index, label))).write_bytes(p.stderr)
            trace = json.loads(trace_path.read_text()) if trace_path.exists() else None
            normalized_stderr = p.stderr
            if trace:
                pid = trace.pop("pid")
                # Normalize only the dynamic worker PID in Bash's own diagnostic
                # prefix; raw stderr remains retained. Payload bytes untouched.
                pattern = rb"(?m)^(" + re.escape(str(invocation).encode()) + rb": line 10: +)" + str(pid).encode() + rb"(?= )"
                normalized_stderr = re.sub(pattern, rb"\1PID", normalized_stderr)
            observations.append((p.returncode, p.stdout, normalized_stderr, trace))
        same = observations[0] == observations[1]
        expected_args = [str(program), "--kernel=" + str(kernel) + "/mckernel.img", "--ps"]
        trace_ok = all(o[3] is None or (o[3]["argv"] == expected_args and o[3]["sentinel"] == "inherited-value" and o[3]["cwd"] == str(BASE) and (not case["stdin"] or o[3].get("stdin_hex") == case["stdin"].hex())) for o in observations)
        expected_ok = True
        if case["mode"] == "executable" and not case["signal"]:
            expected_ok = all(o[:3] == (case["status"], case["stdout"], case["stderr"]) for o in observations)
        results.append({"name": case["name"], "equal": same and trace_ok and expected_ok, "script_status": observations[0][0], "rust_status": observations[1][0], "trace_ok": trace_ok, "expected_ok": expected_ok, "open_signal_boundary": bool(case["signal"])})
    summary = {"scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.", "status": "PASS_HOST_SCRIPT_STUB_ONLY" if all(r["equal"] for r in results) else "FAIL", "cases": len(results), "passed": sum(r["equal"] for r in results), "failed": [r["name"] for r in results if not r["equal"]], "results": results, "compiler_paths": {"cc": cc, "rustc": rustc}, "elapsed_seconds": round(time.monotonic() - started, 3), "native_acceptance": False, "canonical_selected": False}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"})); return 0 if summary["status"].startswith("PASS") else 1

if __name__ == "__main__": sys.exit(main())
