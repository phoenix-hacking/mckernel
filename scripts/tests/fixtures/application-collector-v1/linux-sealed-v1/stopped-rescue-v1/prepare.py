#!/usr/bin/env python3
"""Prepare hash-bound, separately named stopped-rescue collector sources; never build/run."""
import argparse, difflib, hashlib, importlib.util, json, os, stat, subprocess, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path('/workspace') if HERE == Path('/inputs') else HERE.parents[5]
SOURCE = REPO / "scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/collector.c"
EXPECTED_SOURCE = "09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f"
CASES = {"control": 0, "stopped-rescue": 1}
EXPECTED_PACKET = 'c7891c88c42e68a2051af04e63e2103867c531c4e273887aaa88905a7d6e51bd'
PINS = {
    'root_orchestrator.py': 'b794fc74a668f9f41caceb99e299381652fe02caa002c06d8b43c287b75599a3',
    'root_profile.py': 'a65d104d76ec7ce3918d667ac02b1cea92c1a80cae321360b01c12190f2f6dd6',
    'run_collector_tests.py': '691aee973f9ea5e79cdf7766b87c69e0d5d5a01ff334b8674cd099c776125bb5',
    'supervisor_host38.py': 'cba4b4d50d68f9afd5aa8a4c2d830ec0b800f7fd7dfd07774911d5fd1b99c7e7',
}

def require(value, message):
    if not value: raise ValueError(message)

def read(path, maximum=16 * 1024**2):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path, 'canonical artifact path')
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'bounded regular artifact')
        with os.fdopen(fd, 'rb', closefd=False) as stream: raw = stream.read(maximum + 1)
        after = os.fstat(fd)
        stable = ('st_dev','st_ino','st_mode','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')
        require(all(getattr(before,k)==getattr(after,k) for k in stable) and len(raw) == before.st_size, 'artifact changed while reading')
        return raw
    finally: os.close(fd)

def module(path, expected=None):
    path = Path(path); raw = read(path)
    if expected is not None: require(digest(raw) == expected, 'reviewed helper hash: ' + str(path))
    spec = importlib.util.spec_from_file_location('stopped-rescue_' + path.stem, path)
    obj = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), obj.__dict__)
    return obj

def reviewed(name):
    return module(SOURCE.parent / name, PINS[name])

def packet(path):
    raw = read(path)
    require(digest(raw) == EXPECTED_PACKET, 'fixed reviewed packet hash')
    result = json.loads(raw)
    for leaf, key in [('collector.patch', 'patch_sha256'), ('inject.h', 'header_sha256')]:
        require(digest(read(HERE / leaf)) == result['source'][key], 'fixed reviewed ' + leaf)
    require(digest(read(SOURCE)) == result['source']['sha256'] == EXPECTED_SOURCE, 'released source hash')
    return result

def digest(raw): return hashlib.sha256(raw).hexdigest()
def load(path):
    return json.loads(path.read_text(encoding="utf-8"))
def atomic_new(path, raw, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, mode)
    try:
        view = memoryview(raw)
        while view:
            n = os.write(fd, view)
            if n <= 0: raise OSError("short write")
            view = view[n:]
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally: os.close(fd)

def generate(source):
    if digest(source) != EXPECTED_SOURCE: raise ValueError("released collector source SHA mismatch")
    text = source.decode("utf-8")
    if source.count(b"    setup_packet(setup_fd, words);\n") != 1: raise ValueError("setup anchor is not unique")
    if source.count(b"        pump(); observe_exec(); check_leader();\n") != 1: raise ValueError("leader anchor is not unique")
    if source.count(b"#define SETUP_PACKET (SETUP_WORDS * 8U)\n") != 1: raise ValueError("constant anchor is not unique")
    if source.count(b"#include <unistd.h>\n") != 1: raise ValueError("include anchor is not unique")
    if source.count(b"m02_stopped_rescue_child_boundary") or source.count(b"m02_stopped_rescue_completed_wait_hook"): raise ValueError("injection already present")
    text = text.replace("#define SETUP_PACKET (SETUP_WORDS * 8U)\n", "#define SETUP_PACKET (SETUP_WORDS * 8U)\n#include \"inject.h\"\n", 1)
    text = text.replace("    setup_packet(setup_fd, words);\n", "    m02_stopped_rescue_child_boundary(setup_fd, words);\n    setup_packet(setup_fd, words);\n", 1)
    text = text.replace("        pump(); observe_exec(); check_leader();\n", "        pump(); observe_exec(); check_leader();\n        if (m02_stopped_rescue_completed_wait_hook(leader_waitable, !leader.reaped, completion_observed, process_deadline, failure, &interrupted) < 0)\n            fail(\"COLLECTOR_ERROR\", \"stopped-rescue-hook\", errno ? errno : EIO);\n", 1)
    return text.encode()

def generated_diff(source, generated):
    return ''.join(difflib.unified_diff(source.decode().splitlines(True), generated.decode().splitlines(True),
                                       fromfile='collector.c', tofile='collector.c')).encode()

def patch_is_applicable(source, generated, patch_bytes):
    with tempfile.TemporaryDirectory() as d:
        root = Path(d); (root / "collector.c").write_bytes(source)
        proc = subprocess.run(["patch", "--batch", "--forward", "-p0"], input=patch_bytes,
                              cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.returncode == 0 and (root / "collector.c").read_bytes() == generated

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet", type=Path, required=True)
    ap.add_argument("--attempt-root", type=Path, required=True)
    args = ap.parse_args()
    record_packet = packet(args.packet)
    if record_packet.get("schema_version") != 1 or record_packet.get("kind") != "linux-sealed-collector-stopped-rescue-v1": raise ValueError("packet kind")
    if record_packet.get("application_acceptance") or record_packet.get("backend_enabled"): raise ValueError("acceptance flags")
    if not args.attempt_root.is_absolute() or args.attempt_root.exists(): raise ValueError("fresh absolute attempt root required")
    source = SOURCE.read_bytes(); generated = generate(source)
    patch_bytes = (HERE / "collector.patch").read_bytes()
    diff = generated_diff(source, generated)
    if generated.count(b'#include "inject.h"') != 1 or generated.count(b"m02_stopped_rescue_child_boundary(setup_fd, words);") != 1: raise ValueError("generated hook count")
    if generated.count(b"m02_stopped_rescue_completed_wait_hook") != 1: raise ValueError("generated wait hook count")
    if not patch_is_applicable(source, generated, patch_bytes): raise ValueError("reviewed patch is not applicable/equivalent")
    out = args.attempt_root; out.mkdir(mode=0o700, parents=False)
    atomic_new(out / "source.collector.c", source)
    atomic_new(out / "inject.h", (HERE / "inject.h").read_bytes())
    atomic_new(out / "collector.patch", patch_bytes)
    atomic_new(out / "generated.diff", diff)
    record = {"schema_version": 2, "kind": "linux-sealed-collector-stopped-rescue-preparation", "status": "PREPARED_NOT_EXECUTED", "application_acceptance": False, "backend_enabled": False, "source": {"path": str(SOURCE), "sha256": digest(source)}, "generated": {"path": str(out / "stopped-rescue-collector.c"), "sha256": digest(generated), "diff_sha256": digest(diff), "include_count": generated.count(b'#include "inject.h"'), "guard_count": generated.count(b"M02_STOPPED_RESCUE_TEST_ONLY"), "hook_call_count": generated.count(b"m02_stopped_rescue_completed_wait_hook")}, "compiler_supplied": {"M02_STOPPED_RESCUE_TEST_ONLY": 1, "M02_STOPPED_RESCUE_CASE": "per-case: 0,1"}, "patch_sha256": digest(patch_bytes), "header_sha256": digest((HERE / "inject.h").read_bytes()), "cases": CASES, "runtime_root": str(out), "generated_diff_membership": ["inject.h", "m02_stopped_rescue_child_boundary", "m02_stopped_rescue_completed_wait_hook"]}
    atomic_new(out / "stopped-rescue-collector.c", generated, 0o644)
    atomic_new(out / "prepare.json", (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
    print(json.dumps(record, sort_keys=True))

if __name__ == "__main__": main()
