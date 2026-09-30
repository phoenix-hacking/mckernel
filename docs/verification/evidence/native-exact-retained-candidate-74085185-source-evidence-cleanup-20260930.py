#!/usr/bin/env python3
"""Audit/apply only exact Git-blob duplicates in candidate-74085185 evidence.

The default is an audit.  ``--apply`` is deliberately separate and rechecks
the pinned checkout, safety census, and every target immediately before unlink.
Build outputs, receipts, requests, manifests, failure archives, containers,
leases, and all non-identical/untracked files are preserved.
"""
import argparse, hashlib, json, os, stat, subprocess, tempfile
from pathlib import Path

CANDIDATE_COMMIT = "740851854b53036d4834dfb86a5fc7fb0f3954e6"
CANDIDATE_ROOT = Path("/home/holden/mckernel-work/scratch/mckernel-exact-candidate-74085185-scratch-3")
CANDIDATE_IDENTITY = "1831:3932163"
REPO = Path("/home/holden/mckernel")
LIVE_SCRATCH = Path("/home/holden/mckernel-work/scratch")
FAILURE = REPO/"docs/verification/evidence/native-exact-build-74085185-scratch-3-failure-20260930.json"
BUILD_EVIDENCE = LIVE_SCRATCH/"native-exact-build-evidence-74085185-scratch-3"
BUILD_OUTPUT = LIVE_SCRATCH/"native-exact-build-output-74085185-scratch-3"
METADATA = LIVE_SCRATCH/"native-exact-metadata-evidence-74085185-scratch-3"
METADATA_BACKUP = LIVE_SCRATCH/"mckernel-exact-metadata-backup-74085185-scratch-3"
FAILURE_ARCHIVE = LIVE_SCRATCH/"native-exact-build-failure-74085185-scratch-3-20260930-1.tar"
REQUEST = LIVE_SCRATCH/"native-exact-build-request-74085185-scratch-3.json"
INPUTS = LIVE_SCRATCH/"native-exact-inputs-74085185-scratch-3.json"
PREP_LOG = LIVE_SCRATCH/"native-exact-candidate-preparation-74085185-scratch-3.log"
PREP_TERM = LIVE_SCRATCH/"native-exact-candidate-preparation-74085185-scratch-3-terminal.json"
EXCLUSION_NAME = "native-exact-candidate-operational-exclusion-runtimeclosure-5.json"
EXCLUSION = LIVE_SCRATCH/EXCLUSION_NAME
LEASE = LIVE_SCRATCH/"native-exact-build-lease-74085185-scratch-3.json"
EXPECTED_FILES = {
    FAILURE:(66306,47475658,2554,0o600,"e867096108b73cd89bc90a7d0741f8b58315795a516d1727ab999d0fdf6ef8a0"), FAILURE_ARCHIVE:(1831,31536,87541760,0o600,"4fb88caac3e95612f52e4f51059e2a2efedd3d43a3753ae86c5e1c594ef9b4ee"), REQUEST:(1831,31533,2914,0o644,"c0fe30d7c04a05d17ca36f61a9cd7ce66c18b43e6306f506d3bb91d6ca166156"), INPUTS:(1831,31532,1183023,0o644,"2e54c946a47cf438d7eb0e2175b4802daf22a55682944b5ef24c5d7f85f1b77f"), PREP_LOG:(1831,31531,44145,0o600,"f7eb4c6060bde7b8fce7b86f4875381a67a48810f6fd356365bfe57f9b11da5b"), PREP_TERM:(1831,31534,361,0o644,"9620f0915aa3b05f0a6ef1d0c33742461dd9c42d7d17734dafebb8dfea329472"), EXCLUSION:(1831,31535,269,0o600,"0b2cf4f2718834f27e054684559ff31d1d4ce8dcff75aa5548ac572a0ee9fccb")}
EXPECTED_DIRS = {BUILD_EVIDENCE:(1831,4456450), BUILD_OUTPUT:(1831,5636110), METADATA:(1831,5767170), METADATA_BACKUP:(1831,5111810)}

def fail(msg): raise SystemExit("FAIL_CLOSED: " + msg)
def digest(data): return hashlib.sha256(data).hexdigest()
def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.STDOUT).decode().strip()
def blob(repo, commit, path):
    try: return subprocess.check_output(["git", "-C", str(repo), "show", f"{commit}:{path}"], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError: return None

def root_guard(root, repo=REPO, commit=CANDIDATE_COMMIT):
    root = Path(root)
    if root != CANDIDATE_ROOT or not root.is_absolute() or root.is_symlink() or not root.is_dir(): fail("wrong candidate root")
    st = root.stat()
    if f"{st.st_dev}:{st.st_ino}" != CANDIDATE_IDENTITY: fail("candidate identity differs")
    if commit != CANDIDATE_COMMIT: fail("wrong candidate commit")
    try:
        if git(repo, "rev-parse", commit+"^{commit}") != commit or git(root, "rev-parse", "HEAD") != commit: fail("candidate HEAD differs")
    except (OSError, subprocess.CalledProcessError): fail("candidate checkout unavailable")

def evidence_base(root):
    root = Path(root); base = root/"docs/verification/evidence"
    for p in (root/"docs", root/"docs/verification", base):
        if p.is_symlink() or not p.is_dir(): fail("linked or missing evidence ancestor")
    rr, rb = root.resolve(), base.resolve()
    if os.path.commonpath((str(rr), str(rb))) != str(rr): fail("evidence escapes candidate")
    return base, rb

def validate_bindings():
    for p,(dev,ino,size,mode,expected) in EXPECTED_FILES.items():
        st=p.lstat()
        if p.is_symlink() or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or (st.st_dev,st.st_ino,st.st_size,stat.S_IMODE(st.st_mode)) != (dev,ino,size,mode) or digest(p.read_bytes()) != expected: fail("protected file binding differs: "+str(p))
    for p,(dev,ino) in EXPECTED_DIRS.items():
        st=p.lstat()
        if p.is_symlink() or not stat.S_ISDIR(st.st_mode) or (st.st_dev,st.st_ino) != (dev,ino): fail("protected directory binding differs: "+str(p))
    if LEASE.exists(): fail("unexpected active lease record")
    try: owner=json.loads(EXCLUSION.read_text()); pid=int(owner.get("pid",124733)); start=str(owner.get("starttime",94890435))
    except (OSError,json.JSONDecodeError,ValueError): fail("exclusion record unreadable")
    try:
        text=Path(f"/proc/{pid}/stat").read_text(); active=text.rsplit(")",1)[1].split()[19] == start
    except (OSError,ValueError,IndexError): active=False
    if active: fail("exclusion owner is still active")

def census(root):
    def run(argv):
        try:
            p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20, check=False)
            return {"argv": argv, "returncode": p.returncode, "output": p.stdout, "stderr": p.stderr}
        except (OSError, subprocess.TimeoutExpired) as e: return {"argv": argv, "error": type(e).__name__+":"+str(e)}
    result = {
        "open_processes": run(["sudo", "-A", "lsof", "-nP", "-w", "+D", str(root)]),
        "mount_device": run(["findmnt", "-T", str(root), "-o", "SOURCE,FSTYPE,MAJ:MIN,TARGET"]),
        "docker_all": run(["sudo", "-A", "docker", "ps", "-a", "--format", "{{json .}}"]),
        "docker_inspect": run(["sudo", "-A", "docker", "inspect", "80e172a592939e2c30ca87a5bc3b9356467876f8ca1716b4ccf718320593eb22", "--format", "{{json .}}"]),
        "lease_listing": run(["find", str(LIVE_SCRATCH), "-maxdepth", "1", "-type", "f", "(", "-name", "*lease*", "-o", "-name", "*operational-exclusion*", ")", "-printf", "%p %D:%i %u:%g %m\\n"]),
        "protected_paths": [str(x) for x in (FAILURE, BUILD_EVIDENCE, BUILD_OUTPUT, METADATA, METADATA_BACKUP, FAILURE_ARCHIVE, REQUEST, INPUTS, PREP_LOG, PREP_TERM)],
        "container_removal": False,
    }
    validate_census(result)
    return result

def validate_census(c):
    l = c["open_processes"]
    if l.get("returncode") not in (0, 1) or l.get("stderr", "").strip(): fail("lsof census failed")
    rows = [x for x in l.get("output", "").splitlines() if x and not x.startswith("COMMAND")]
    if rows: fail("candidate has open references")
    m = c["mount_device"]; lines = [x.split() for x in m.get("output", "").splitlines() if x.strip() and not x.startswith("SOURCE")]
    if m.get("returncode") != 0 or len(lines) != 1 or lines[0][:4] != ["/dev/loop39", "ext4", "7:39", "/home/holden/mckernel-work/scratch"]: fail("unexpected scratch mount/device")
    d = c["docker_all"]
    if d.get("returncode") != 0: fail("Docker census failed")
    for line in d.get("output", "").splitlines():
        try: obj = json.loads(line)
        except json.JSONDecodeError: fail("Docker census malformed")
        state = str(obj.get("State", "")).lower()
        if state in ("running", "restarting") and ("mckernel-exact" in str(obj.get("Names", "")) or "/home/holden/mckernel-work" in str(obj.get("Mounts", ""))): fail("relevant running container")
    i=c.get("docker_inspect", {}); lines=[x for x in i.get("output","").splitlines() if x.strip()]
    if i.get("returncode") != 0 or len(lines)!=1: fail("container inspect failed")
    try: obj=json.loads(lines[0]); state=obj.get("State",{})
    except json.JSONDecodeError: fail("container inspect malformed")
    if obj.get("Id") != "80e172a592939e2c30ca87a5bc3b9356467876f8ca1716b4ccf718320593eb22" or obj.get("Name") != "/mckernel-exact-d60382667e3d4c1f89a61850e5a1ba59" or state.get("Status") != "exited" or state.get("Running") is not False or state.get("Pid") != 0 or state.get("ExitCode") != 1 or state.get("OOMKilled") is not False: fail("container identity/state differs")

def row(path, base, repo, commit):
    st = path.lstat(); data = path.read_bytes(); rel = str(path.relative_to(base)); restore = "docs/verification/evidence/"+rel
    return {"path": str(path), "restore_git_path": restore, "blob": git(repo, "rev-parse", f"{commit}:{restore}"), "mode": stat.S_IMODE(st.st_mode), "mtime_ns": st.st_mtime_ns, "size": st.st_size, "sha256": digest(data), "allocated_bytes": st.st_blocks*512, "dev": st.st_dev, "ino": st.st_ino, "nlink": st.st_nlink}

def audit(root=CANDIDATE_ROOT, repo=REPO, commit=CANDIDATE_COMMIT):
    root_guard(root, repo, commit); validate_bindings(); base, resolved = evidence_base(root); targets=[]; preserved=[]
    safety = census(root)
    for path in sorted(base.rglob("*")):
        st = path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1: continue
        if os.path.commonpath((str(resolved), str(path.resolve(strict=False)))) != str(resolved): fail("target escapes evidence")
        r = row(path, base, repo, commit); expected = blob(repo, commit, r["restore_git_path"])
        if expected is not None and r["sha256"] == digest(expected) and r["size"] == len(expected): targets.append(r)
        else:
            r["reason"] = "not-present-or-content-differs-from-pinned-Git-blob"; preserved.append(r)
    if not targets: fail("no exact Git-blob duplicate evidence targets")
    protected = [FAILURE, BUILD_EVIDENCE, BUILD_OUTPUT, METADATA, METADATA_BACKUP, FAILURE_ARCHIVE, REQUEST, INPUTS, PREP_LOG, PREP_TERM, EXCLUSION, LEASE]
    bindings = {"failure_record": {"path":str(FAILURE), "sha256":digest(FAILURE.read_bytes()) if FAILURE.is_file() else None}, "failure_archive": {"path":str(FAILURE_ARCHIVE), "sha256":"4fb88caac3e95612f52e4f51059e2a2efedd3d43a3753ae86c5e1c594ef9b4ee", "size":87541760}, "container": {"id":"80e172a592939e2c30ca87a5bc3b9356467876f8ca1716b4ccf718320593eb22", "name":"mckernel-exact-d60382667e3d4c1f89a61850e5a1ba59", "state":"exited", "pid":0, "exit_code":1}, "operational_exclusion":str(EXCLUSION), "lease":str(LEASE)}
    return {"schema":"mckernel.exact-git-source-cleanup.v1", "status":"AUDIT_PASS", "candidate_commit":commit, "candidate_root":str(root), "candidate_identity":CANDIDATE_IDENTITY, "targets":targets, "preserved":preserved, "safety_census":safety, "protected_records":[str(x) for x in protected], "protected_bindings":bindings, "container_removal":False, "recovery":"restore each target from its recorded Git blob/path/mode/mtime"}

def stable(plan): return {k:v for k,v in plan.items() if k not in ("safety_census", "fresh_safety_census", "fresh_safety_census_sha256")}
def durable_write(path, obj):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=".74085185-cleanup-", dir=path.parent)
    ident=os.fstat(fd); payload=(json.dumps(obj, sort_keys=True, indent=2)+"\n").encode()
    try:
        off=0
        while off<len(payload): off += os.write(fd, payload[off:])
        os.fsync(fd); st=os.fstat(fd)
        if (st.st_dev,st.st_ino,st.st_nlink)!=(ident.st_dev,ident.st_ino,1) or os.path.lexists(path): fail("plan collision or replacement")
        os.link(tmp,path); d=os.open(path.parent,os.O_DIRECTORY); os.fsync(d); os.close(d)
    finally:
        os.close(fd)
        if os.path.lexists(tmp):
            try: os.unlink(tmp)
            except FileNotFoundError: pass

def apply(plan):
    if plan.get("schema")!="mckernel.exact-git-source-cleanup.v1" or plan.get("status")!="AUDIT_PASS": fail("invalid plan")
    root=Path(plan["candidate_root"]); root_guard(root,REPO,plan["candidate_commit"]); fresh=audit(root,REPO,plan["candidate_commit"])
    if stable(fresh)!=stable(plan): fail("audit plan differs from fresh audit")
    base,resolved=evidence_base(root)
    for expected in plan["targets"]:
        p=Path(expected["path"]); st=p.lstat()
        if os.path.commonpath((str(resolved),str(p.resolve(strict=False))))!=str(resolved) or not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or (st.st_dev,st.st_ino)!=(expected["dev"],expected["ino"]) or st.st_size!=expected["size"] or stat.S_IMODE(st.st_mode)!=expected["mode"] or digest(p.read_bytes())!=expected["sha256"]: fail("target revalidation failed: "+str(p))
        p.unlink(); d=os.open(p.parent,os.O_DIRECTORY); os.fsync(d); os.close(d)
    plan["status"]="APPLY_PASS"; plan["removed_allocated_bytes"]=sum(x["allocated_bytes"] for x in plan["targets"]); return plan

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--plan",required=True); ap.add_argument("--apply",action="store_true"); ap.add_argument("--write-plan",action="store_true"); a=ap.parse_args()
    result=apply(json.loads(Path(a.plan).read_text())) if a.apply else audit()
    if a.write_plan: durable_write(a.plan,result)
    print(json.dumps(result,sort_keys=True)); return 0
if __name__ == "__main__": raise SystemExit(main())
