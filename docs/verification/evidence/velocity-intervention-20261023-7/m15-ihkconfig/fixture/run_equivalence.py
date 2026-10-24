#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepared isolated host fixture. Explicit --execute is required; compilers execute
only when the parent grants an ordinary host compiler/fixture resource profile.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent.parent
WRAPS = ["open", "close", "ioctl", "pread", "pwrite", "mmap", "munmap", "calloc", "malloc", "realloc", "strdup"]

def case_list():
    cases = []
    def add(args, env=None, expected=None):
        cases.append({"args": args, "env": env or {}, "expected_status": expected})
    for a in [[], ["--help"], ["0"]]: add(a, expected=1)
    add(["0", "--help"], expected=0)  # Existing CLI has no special help option.
    for index in ["0", "abc", "-1", "17junk"]: add([index, "create"])
    for a in [["destroy"], ["destroy", "7"], ["destroy", "-1"], ["destroy", "junk"], ["scratch"], ["sbox"], ["sbox", "10"], ["sbox", "junk"], ["ioctl"], ["ioctl", "feed"], ["ioctl", "feed", "ffffffffffffffff"], ["ioctl", "garbage", "garbage"], ["unknown"], ["create", "ignored"]]: add(["0"] + a)
    for action in ["read", "mmap", "clear_kmsg", "clear_kmsg_write"]:
        for tail in [[], ["1000"], ["junk"], ["-1"]]: add(["0", action] + tail)
    for action in ["reserve", "release"]:
        for tail in [[], ["cpu"], ["mem"], ["other", "1"], ["cpu", "1,3-5"], ["cpu", "0,2"], ["cpu", "1,1"], ["cpu", "2-1"], ["cpu", "-1"], ["cpu", "1-"], ["cpu", "bad"], ["cpu", "1x"], ["cpu", ""], ["cpu", ",1"], ["cpu", "1,"], ["cpu", "1,,2"], ["mem", "4096"], ["mem", "1K@0,2M@1"], ["mem", "1KB@2"], ["mem", "all"], ["mem", "ALL@1"], ["mem", "0"], ["mem", "bad"], ["mem", "@0"], ["mem", "1K@"], ["mem", "1K@bad"], ["mem", "1K@1@2"], ["mem", "1K,"], ["mem", ""]]: add(["0", action] + tail)
    for tail in [[], ["cpu"], ["mem"], ["other"]]: add(["0", "query"] + tail)
    for tail in [[], ["os_instances"], ["buildid"], ["other"]]: add(["0", "get"] + tail)
    for tail in [[], ["50"], ["junk"]]: add(["0", "reserve_mem_max_ratio"] + tail)
    for action in ["create", "destroy", "query", "release", "unknown"]: add(["0", action], {"IHK_FIXTURE_FAIL_OPEN": "1"}, 1)
    add(["0", "get", "buildid"], {"IHK_FIXTURE_FAIL_OPEN": "1"}, 255)
    for a in [["create"], ["destroy", "7"], ["scratch"], ["sbox"], ["ioctl", "feed", "1"], ["release", "cpu", "1-3"], ["release", "mem", "4096@0"], ["release", "mem", "all"], ["query", "cpu"], ["query", "mem"], ["get", "buildid"]]: add(["0"] + a, {"IHK_FIXTURE_IOCTL_RET": "-1"})
    for key, action in [("IHK_FIXTURE_FAIL_PREAD", "read"), ("IHK_FIXTURE_FAIL_PWRITE", "clear_kmsg_write"), ("IHK_FIXTURE_FAIL_MMAP", "mmap"), ("IHK_FIXTURE_FAIL_MMAP", "clear_kmsg")]: add(["0", action, "1000"], {key: "1"}, 1)
    add(["0", "clear_kmsg_write", "1000"], {"IHK_FIXTURE_PWRITE_COUNT": "0"}, 0)
    for ret in ["-22", "-12", "7"]:
        for a in [["reserve", "cpu", "1-3"], ["reserve", "mem", "1K@1"], ["get", "os_instances"]]: add(["0"] + a, {"IHK_FIXTURE_LIB_RET": ret})
    for count in ["0", "-1"]: add(["0", "get", "os_instances"], {"IHK_FIXTURE_OS_COUNT": count})
    for count in ["0", "-1", "80"]: add(["0", "query", "cpu"], {"IHK_FIXTURE_CPU_COUNT": count})
    add(["0", "query", "cpu"], {"IHK_FIXTURE_CPU_GAPPED": "1"})
    for count in ["0", "20"]: add(["0", "query", "mem"], {"IHK_FIXTURE_MEM_COUNT": count})
    for request in ["0x11290c", "0x112906", "0x112907"]:
        action = ["query", "mem"] if request == "0x112907" else ["query", "cpu"]
        add(["0"] + action, {"IHK_FIXTURE_FAIL_REQUEST": request})
    add(["0", "release", "mem", "all"], {"IHK_FIXTURE_FAIL_REQUEST": "0x112907"})
    alloc_actions = [["reserve", "cpu", "1-3"], ["reserve", "mem", "1K@1"], ["release", "cpu", "1-3"], ["release", "mem", "1K@1"], ["release", "mem", "all"], ["query", "cpu"], ["query", "mem"], ["get", "os_instances"]]
    for a in alloc_actions:
        for nth in ["1", "2", "3"]: add(["0"] + a, {"IHK_FIXTURE_FAIL_CALLOC": nth})
    for a in alloc_actions[:4]:
        for nth in ["1", "2", "3"]: add(["0"] + a, {"IHK_FIXTURE_FAIL_STRDUP": nth})
    for a in [["query", "cpu"], ["query", "mem"]]: add(["0"] + a, {"IHK_FIXTURE_FAIL_MALLOC": "1"})
    return cases

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--profile", choices=["default", "krm", "both"], default="default")
    ap.add_argument("--max-cases", type=int, default=256)
    ap.add_argument("--cc", default="cc")
    ap.add_argument("--rustc", default="rustc")
    ns = ap.parse_args()
    cases = case_list()
    if not ns.execute:
        print(json.dumps({"state": "PREPARED_ONLY", "cases_per_profile": len(cases), "profiles": ns.profile, "compilers_or_fixtures_run": False})); return 0
    if ns.max_cases < len(cases) or ns.max_cases > 256: raise SystemExit("case bound must cover the fixed matrix and be <=256")
    start = time.monotonic()
    output = BASE / "fixture-output"
    if output.exists(): raise SystemExit("fixture-output already exists; retain evidence and choose a reviewed successor, no overwrite")
    output.mkdir()
    cc = shutil.which(ns.cc); rustc = shutil.which(ns.rustc)
    if not cc or not rustc: raise SystemExit("explicit host cc/rustc not found")
    env = {k: v for k, v in os.environ.items() if not k.startswith("IHK_FIXTURE_") and k not in ["LD_PRELOAD", "LD_LIBRARY_PATH"]}
    env["LC_ALL"] = "C"
    env["IHKCONFIG_BUILDID"] = "fixture-build"
    def run(command, limit, log):
        remain = 180 - (time.monotonic() - start)
        if remain <= 0: raise TimeoutError("180-second fixture envelope exhausted")
        (output / (log + ".command.json")).write_text(json.dumps({"argv": command, "IHKCONFIG_BUILDID": env["IHKCONFIG_BUILDID"], "LC_ALL": env["LC_ALL"]}, indent=2) + "\n")
        p = subprocess.run(command, cwd=BASE, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=min(limit, remain))
        (output / (log + ".stdout")).write_bytes(p.stdout); (output / (log + ".stderr")).write_bytes(p.stderr)
        if p.returncode: raise RuntimeError("command failed: " + log + " rc=" + str(p.returncode))
    includes = ["-I", str(BASE / "fixture/include")]
    wrap_flags = ["-Wl,--wrap=" + w for w in WRAPS]
    profiles = ["default", "krm"] if ns.profile == "both" else [ns.profile]
    summary = {"scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.", "profiles": [], "compiler_paths": {"cc": cc, "rustc": rustc}, "native_acceptance": False, "full_c_free_acceptance": False}
    for profile in profiles:
        d = output / profile; d.mkdir()
        c_flags = ["-DENABLE_KRM_WORKAROUND=1"] if profile == "krm" else []
        rust_flags = ["--cfg", "ihkconfig_krm_workaround"] if profile == "krm" else []
        obj = d / "ihkconfig-rust.o"
        run([rustc, "--edition=2021", "--crate-name", "ihkconfig", "--crate-type=lib", "-C", "panic=abort", "-C", "opt-level=2", "-C", "relocation-model=pic", "--emit=obj=" + str(obj)] + rust_flags + [str(BASE / "ihkconfig.rs")], 60, profile + "-rust-compile")
        c_exe = d / "reference" / "ihkconfig"; r_exe = d / "rust" / "ihkconfig"
        c_exe.parent.mkdir(); r_exe.parent.mkdir()
        common = [cc, "-std=gnu11", "-O2", "-fPIE", "-pie"] + includes + c_flags
        run(common + [str(BASE / "reference/ihkconfig.c"), str(BASE / "reference/ihklib_helpers.c"), str(BASE / "fixture/abi_stub.c")] + wrap_flags + ["-o", str(c_exe)], 30, profile + "-c-reference-build")
        run(common + [str(obj), str(BASE / "fixture/abi_stub.c")] + wrap_flags + ["-o", str(r_exe)], 30, profile + "-rust-link")
        results = []
        for number, case in enumerate(cases):
            observations = []
            for label, exe in [("c", c_exe), ("rust", r_exe)]:
                trace = d / ("case-%03d-%s.trace" % (number, label))
                child_env = dict(env, **case["env"], IHK_FIXTURE_TRACE=str(trace))
                remain = 180 - (time.monotonic() - start)
                if remain <= 0: raise TimeoutError("180-second fixture envelope exhausted")
                # Equal argv[0] is necessary: usage/destroy diagnostics include it.
                p = subprocess.run(["ihkconfig"] + case["args"], executable=str(exe), cwd=BASE, env=child_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=min(2, remain))
                (d / ("case-%03d-%s.stdout" % (number, label))).write_bytes(p.stdout)
                (d / ("case-%03d-%s.stderr" % (number, label))).write_bytes(p.stderr)
                observations.append((p.returncode, p.stdout, p.stderr, trace.read_bytes() if trace.exists() else b""))
            expected = case["expected_status"]
            ok = observations[0] == observations[1] and observations[0][0] >= 0 and (expected is None or observations[0][0] == expected)
            results.append(dict(case, number=number, equal=ok, reference_status=observations[0][0], rust_status=observations[1][0]))
        # These are reviewed-correctness proposals for originally undefined C
        # paths. Never execute the C reference on these synthetic inputs.
        contracts = [
            {"name": "short-pread-zero-tail", "args": ["0", "read", "1000"], "env": {"IHK_FIXTURE_PREAD_COUNT": "8"}, "status": 0, "stdout": b"00 01 02 03 04 05 06 07 00 00 00 00 00 00 00 00 \n", "stderr": b""},
            {"name": "unterminated-buildid-bounded", "args": ["0", "get", "buildid"], "env": {"IHK_FIXTURE_BUILDID_NO_NUL": "1"}, "status": 0, "stdout": b"xxxxxxxxxxxxx\n", "stderr": b""},
            {"name": "format-realloc-failure", "args": ["0", "query", "mem"], "env": {"IHK_FIXTURE_MEM_COUNT": "20", "IHK_FIXTURE_FAIL_REALLOC": "1"}, "status": 255, "stdout": b"do_query,build result string failed\n", "stderr": b""},
        ]
        contract_results = []
        for contract in contracts:
            trace = d / (contract["name"] + ".trace")
            child_env = dict(env, **contract["env"], IHK_FIXTURE_TRACE=str(trace))
            remain = 180 - (time.monotonic() - start)
            if remain <= 0: raise TimeoutError("180-second fixture envelope exhausted")
            p = subprocess.run(["ihkconfig"] + contract["args"], executable=str(r_exe), cwd=BASE, env=child_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=min(2, remain))
            (d / (contract["name"] + ".stdout")).write_bytes(p.stdout)
            (d / (contract["name"] + ".stderr")).write_bytes(p.stderr)
            ok = (p.returncode, p.stdout, p.stderr) == (contract["status"], contract["stdout"], contract["stderr"])
            contract_results.append({"name": contract["name"], "passed": ok, "status": p.returncode})
        (d / "defined-contracts.json").write_text(json.dumps(contract_results, indent=2) + "\n")
        (d / "cases.json").write_text(json.dumps(results, indent=2) + "\n")
        failed = [x["number"] for x in results if not x["equal"]]
        summary["profiles"].append({"profile": profile, "cases": len(results), "failed": failed, "passed": len(results) - len(failed), "defined_contracts": contract_results})
        # Preserve all original failures; no automatic candidate correction/retry.
        if failed or any(not c["passed"] for c in contract_results): break
    summary["elapsed_seconds"] = round(time.monotonic() - start, 3)
    summary["status"] = "PASS_HOST_ABI_STUB_ONLY" if all(not p["failed"] and all(c["passed"] for c in p["defined_contracts"]) for p in summary["profiles"]) else "FAIL"
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary)); return 0 if summary["status"].startswith("PASS") else 1

if __name__ == "__main__":
    sys.exit(main())
