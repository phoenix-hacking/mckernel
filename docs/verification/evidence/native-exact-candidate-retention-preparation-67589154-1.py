#!/usr/bin/python3
"""One-shot, ordinary-user live inventory/archive packet.

This file is deliberately released only after an independent reviewer replaces
RELEASE_HASH_REQUIRED with the reviewed packet hash.  Until then it is a
non-executed draft and cannot touch either retained root.
"""
from __future__ import print_function
import argparse, errno, hashlib, importlib.util, json, os, signal, stat, subprocess, sys, time

SOURCE = "/home/holden/mckernel"
FETCHED_SOURCE = "6f8a499ec33359ac49a1191a2a8139790e2044ce"
MAIN_COMMIT = "675891545c881b8d625256ade56fe66ac69fe794"
IHK_COMMIT = "3114d9e7101ad52030eb3effa849a5c108972a1f"
CANDIDATE = "/dev/shm/mckernel-exact-candidate-67589154-1"
BACKUP = "/dev/shm/mckernel-exact-metadata-backup-67589154-1"
CANDIDATE_ID = {"dev": 26, "inode": 25166, "uid": 1000, "gid": 1000, "mode": 0o755}
BACKUP_ID = {"dev": 26, "inode": 35798, "uid": 1000, "gid": 1000, "mode": 0o755}
PLANNER = "scripts/native_exact_candidate_retention_capsule.py"
ARCHIVER = "scripts/native_exact_candidate_retention_archive.py"
PLANNER_SHA = "ac3bb0354d1353928fd5f63ddf6743b636642fab79a4f5a3ec9195d5721d0b26"
ARCHIVER_SHA = "6a28184e13e4ddec3a5e2fe6229c618929df29f235901083d55918c8291ac06e"
RELEASE_HASH = "RELEASE_HASH_REQUIRED"
RELEASE_PATH = SOURCE + "/docs/verification/evidence/stability-native-exact-candidate-retention-preparation-67589154-20260929-1.release.json"
TEMPLATE_SOURCE_COMMIT = "6f8a499ec33359ac49a1191a2a8139790e2044ce"
TEMPLATE_PACKET_SHA = "9e0a57c632816e1f2d8708eac05ded4b4afd714b08c3f958ef7e42aa97b7d423"
TEMPLATE_TEST_SHA = "63abe21198811a6e5b44bf837a7c6e5706a3982f00256ed1ac3c56087f27defa"
CAPSULE_TEST_SHA = "ae6f129ac8f86379d98ad2ca1eec1e03034d3754a6786300014c140320743c9a"
ARCHIVE_TEST_SHA = "fa9d727d74e462a9d6fdb2d96f3a3a597ccdab331b4321b92a2d11eaeb48355e"
PYTHON = "/usr/bin/python3"
OUT = SOURCE + "/docs/verification/evidence/stability-native-exact-candidate-retention-67589154-20260929-1.inventory.json"
ARCHIVE = SOURCE + "/docs/verification/evidence/stability-native-exact-candidate-retention-67589154-20260929-1.tar"
SCRATCH = "/home/holden/mckernel-work/scratch/native-exact-retention-preparation-evidence-67589154-1"
CLAIM = SCRATCH + "/claim-67589154-1.json"
LEASE = SCRATCH + "/lease-67589154-1.json"

def fail(message):
    raise RuntimeError(message)

def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""): h.update(b)
    return h.hexdigest()

def _write_all(fd, data):
    off = 0
    while off < len(data):
        n = os.write(fd, data[off:])
        if n <= 0: fail("short write")
        off += n

def _fsync_parent(path):
    fd = os.open(os.path.dirname(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0))
    try: os.fsync(fd)
    finally: os.close(fd)

def _stable(path):
    s = os.lstat(path)
    return {"dev": s.st_dev, "inode": s.st_ino, "uid": s.st_uid,
            "gid": s.st_gid, "mode": stat.S_IMODE(s.st_mode)}

def _absent(path):
    if os.path.lexists(path): fail("fresh path exists: " + path)
    parent = os.path.dirname(path)
    cur = os.path.sep
    for part in parent.split(os.path.sep):
        if not part: continue
        cur = os.path.join(cur, part)
        if os.path.islink(cur): fail("symlink ancestor: " + cur)

def _exclusive(path, payload):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        _write_all(fd, (json.dumps(payload, sort_keys=True) + "\n").encode("utf-8")); os.fsync(fd)
    finally: os.close(fd)
    _fsync_parent(path)

def _git(args, cwd=SOURCE):
    env = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C",
           "TZ": "UTC", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_TERMINAL_PROMPT": "0", "GIT_NO_REPLACE_OBJECTS": "1"}
    git_dir = os.path.join(cwd, ".git")
    return subprocess.check_output(["/usr/bin/git", "--git-dir=" + git_dir, "--work-tree=" + cwd] + args, cwd=SOURCE, env=env,
                                   stderr=subprocess.PIPE).decode("ascii").strip()

def _release_check(packet_hash):
    if RELEASE_HASH == "RELEASE_HASH_REQUIRED": fail("draft packet")
    if _sha(RELEASE_PATH) != RELEASE_HASH: fail("release hash mismatch")
    with open(RELEASE_PATH, "rb") as f: release = json.load(f)
    required = {"status", "one_shot", "mutation_scope", "cleanup", "retirement", "runtime_acceptance",
                "template_source_commit", "template_packet_sha256", "template_test_sha256", "inputs"}
    if set(release) != required or release["status"] != "PASS_ONE_SHOT_RETENTION_PREPARATION" or not release["one_shot"]: fail("invalid release")
    if release["mutation_scope"] != "manifest_archive_only" or release["cleanup"] or release["retirement"] or release["runtime_acceptance"]: fail("release scope")
    if release["template_source_commit"] != TEMPLATE_SOURCE_COMMIT or release["template_packet_sha256"] != TEMPLATE_PACKET_SHA or release["template_test_sha256"] != TEMPLATE_TEST_SHA: fail("template binding")
    expected = {"planner": PLANNER_SHA, "archiver": ARCHIVER_SHA, "capsule_test": CAPSULE_TEST_SHA, "archive_test": ARCHIVE_TEST_SHA,
                "candidate": CANDIDATE_ID, "backup": BACKUP_ID, "output": OUT, "archive": ARCHIVE}
    if release["inputs"] != expected: fail("release inputs")
    return release

def _capacity():
    values = {}
    for name, path, floor in (("host", "/", 16 << 30), ("scratch", "/home/holden/mckernel-work/scratch", 12 << 30), ("tmpfs", "/dev/shm", 4 << 30)):
        s = os.statvfs(path); values[name] = s.f_bavail * s.f_frsize
        if values[name] < floor: fail(name + " capacity floor")
    mem = None
    for line in open("/proc/meminfo"):
        if line.startswith("MemAvailable:"): mem = int(line.split()[1]) * 1024; break
    if mem is None or mem < (4 << 30): fail("memory capacity floor")
    values["memory"] = mem
    return values

def _census():
    forbidden = ("make", "cmake", "ninja", "cc", "gcc", "clang", "rustc", "cargo", "qemu", "mcexec")
    for name in os.listdir("/proc"):
        if not name.isdigit() or int(name) == os.getpid(): continue
        try: cmd = open("/proc/" + name + "/cmdline", "rb").read().replace(b"\0", b" ").decode("utf-8", "ignore").lower()
        except (IOError, OSError): continue
        if any(x in cmd.split("/")[-1] for x in forbidden): fail("conflicting process: " + cmd)
    known = "/home/holden/mckernel-work/scratch/native-exact-build-lease-67589154-1.json"
    if os.path.lexists(known): fail("known build lease exists")
    return {"pid": os.getpid(), "at": time.time()}

def _run(argv, label, timeout=1800):
    base = os.path.join(SCRATCH, label)
    out, err, status = base + ".stdout", base + ".stderr", base + ".status"
    started = time.time()
    stdout = open(out, "xb"); stderr = open(err, "xb")
    p = subprocess.Popen(argv, stdout=stdout, stderr=stderr, close_fds=True, start_new_session=True)
    stdout.close(); stderr.close()
    try:
        proc_stat = open("/proc/%d/stat" % p.pid).read().split()
        identity = {"pid": p.pid, "starttime": int(proc_stat[21]), "pgid": os.getpgid(p.pid), "sid": os.getsid(p.pid)}
    except (IOError, OSError, ValueError, IndexError):
        fail(label + " identity unavailable")
    try:
        rc = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL); rc = p.wait(); fail(label + " timeout")
    with open(status, "x") as f: f.write(str(rc) + "\n"); f.flush(); os.fsync(f.fileno())
    if rc != 0: fail(label + " failed rc=" + str(rc))
    if os.path.exists("/proc/%d" % p.pid): fail(label + " child not retired")
    return {"label": label, "identity": identity, "returncode": rc, "elapsed": time.time() - started}

def _strict_verify(path):
    spec = importlib.util.spec_from_file_location("_exact_archive", os.path.join(SOURCE, ARCHIVER))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return bool(module.verify_archive(path))

def execute(release_hash=None):
    if release_hash != RELEASE_HASH or RELEASE_HASH == "RELEASE_HASH_REQUIRED":
        print("DRAFT_NOT_RELEASED", file=sys.stderr); return 3
    if os.geteuid() == 0: fail("ordinary user required")
    packet_hash = _sha(__file__)
    if release_hash != packet_hash: fail("release hash does not bind packet bytes")
    for path in (OUT, ARCHIVE, SCRATCH, CLAIM, LEASE): _absent(path)
    os.makedirs(SCRATCH, mode=0o700)
    if _stable(CANDIDATE) != CANDIDATE_ID or _stable(BACKUP) != BACKUP_ID: fail("root identity mismatch")
    if _git(["rev-parse", "HEAD"]) != FETCHED_SOURCE: fail("source HEAD mismatch")
    if _git(["rev-parse", "FETCH_HEAD"]) != FETCHED_SOURCE: fail("FETCH_HEAD mismatch")
    if _git(["rev-parse", "upstream/HEAD"]) != FETCHED_SOURCE: fail("upstream mismatch")
    if _git(["-C", CANDIDATE, "rev-parse", "HEAD"]) != MAIN_COMMIT: fail("candidate commit mismatch")
    if _git(["-C", os.path.join(CANDIDATE, "ihk"), "rev-parse", "HEAD"]) != IHK_COMMIT: fail("IHK commit mismatch")
    if _sha(os.path.join(SOURCE, PLANNER)) != PLANNER_SHA or _sha(os.path.join(SOURCE, ARCHIVER)) != ARCHIVER_SHA:
        fail("tool hash mismatch")
    _exclusive(CLAIM, {"schema": "native-exact-retention-claim-v1", "packet": packet_hash, "pid": os.getpid()})
    _exclusive(LEASE, {"schema": "native-exact-retention-lease-v1", "claim": CLAIM, "pid": os.getpid()})
    before = {"candidate": _stable(CANDIDATE), "backup": _stable(BACKUP), "capacity": os.statvfs(SCRATCH).f_bavail}
    planner = _run([PYTHON, "-E", "-s", "-B", os.path.join(SOURCE, PLANNER),
                    "--candidate-root", CANDIDATE, "--metadata-backup-root", BACKUP,
                    "--main-revision", MAIN_COMMIT, "--ihk-revision", IHK_COMMIT, "--output", OUT], "planner")
    archive = _run([PYTHON, "-E", "-s", "-B", os.path.join(SOURCE, ARCHIVER),
                    "--manifest", OUT, "--candidate-root", CANDIDATE,
                    "--metadata-backup-root", BACKUP, "--output", ARCHIVE], "archive")
    if not _strict_verify(ARCHIVE): fail("strict archive verifier failed")
    if _stable(CANDIDATE) != before["candidate"] or _stable(BACKUP) != before["backup"]: fail("root changed")
    with open(OUT, "rb") as f: manifest = json.load(f)
    if len([e for e in manifest.get("entries", []) if e.get("type") == "symlink" and e.get("classification") == "reconstructible"]) != 49: fail("expected 49 links")
    if _sha(os.path.join(SOURCE, PLANNER)) != PLANNER_SHA or _sha(os.path.join(SOURCE, ARCHIVER)) != ARCHIVER_SHA: fail("source tool changed")
    receipt = {"schema": "native-exact-candidate-retention-preparation-v1", "status": "PASS",
               "packet_sha256": packet_hash, "planner": planner, "archive": archive,
               "manifest_sha256": _sha(OUT), "archive_sha256": _sha(ARCHIVE), "before": before,
               "post": {"candidate": _stable(CANDIDATE), "backup": _stable(BACKUP)}}
    receipt_path = os.path.join(SCRATCH, "receipt.json")
    _exclusive(receipt_path, receipt)
    os.unlink(LEASE); os.unlink(CLAIM)
    return 0

def main(argv=None):
    p = argparse.ArgumentParser(); p.add_argument("--release-hash"); a = p.parse_args(argv)
    return execute(a.release_hash)

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception as exc:
        print("retention preparation failed: %s" % exc, file=sys.stderr); sys.exit(2)
