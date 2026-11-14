#!/usr/bin/env python3
"""Fail-closed, two-phase cleanup of committed duplicate evidence only.

This packet is deliberately inert unless --apply is supplied.  It never removes
directories, links, non-regular files, or files which differ from the pinned Git
tree.  The candidate and commit are fixed to prevent accidental reuse.
"""
import argparse, hashlib, json, os, stat, subprocess, sys, tempfile
from pathlib import Path

CANDIDATE_COMMIT = "6323598141241dc7f734f42bac78c939bf5ae292"
CANDIDATE_ROOT = Path("/home/holden/mckernel-work/retained-exact-candidates/mckernel-exact-candidate-63235981-scratch-2")

def die(msg):
    raise SystemExit("FAIL_CLOSED: " + msg)

def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], stderr=subprocess.STDOUT).decode().strip()

def root_guard(root, repo, commit):
    root = Path(root)
    if root != CANDIDATE_ROOT or not root.is_absolute(): die("wrong candidate root")
    if root.is_symlink() or not root.is_dir(): die("candidate root is not a directory")
    if git(repo, "cat-file", "-e", commit + "^{commit}") is None: die("commit unavailable")
    # A Git checkout must not have moved since the packet was issued.
    try: head = git(root, "rev-parse", "HEAD")
    except Exception: head = None
    if head is not None and head != commit: die("candidate HEAD differs")

def blob(repo, commit, rel):
    try: return git(repo, "rev-parse", f"{commit}:docs/verification/evidence/{rel}")
    except subprocess.CalledProcessError: return None

def audit(root=CANDIDATE_ROOT, repo=Path(__file__).parents[3], commit=CANDIDATE_COMMIT):
    root_guard(root, repo, commit)
    base = Path(root) / "docs/verification/evidence"
    if base.is_symlink() or not base.is_dir(): die("evidence directory missing or linked")
    rows=[]
    for p in sorted(base.rglob("*")):
        st=p.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1: continue
        rel=str(p.relative_to(base))
        b=blob(repo, commit, rel)
        if not b: continue
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        # Git blob identity is authoritative; compare content through cat-file.
        expected=subprocess.check_output(["git","-C",str(repo),"cat-file","blob",b])
        if len(expected)!=st.st_size or hashlib.sha256(expected).hexdigest()!=h or expected!=p.read_bytes(): die("file changed or blob mismatch: "+rel)
        rows.append({"path":str(p),"restore_git_path":"docs/verification/evidence/"+rel,"blob":b,"mode":stat.S_IMODE(st.st_mode),"mtime_ns":st.st_mtime_ns,"size":st.st_size,"sha256":h,"allocated_bytes":st.st_blocks*512,"dev":st.st_dev,"ino":st.st_ino})
    if not rows: die("no exact duplicate evidence targets")
    return {"schema":"mckernel.exact-evidence-cleanup.v1","status":"AUDIT_PASS","candidate_commit":commit,"candidate_root":str(root),"targets":rows,"recovery":"restore each restore_git_path from blob at candidate_commit"}

def atomic_write(path, obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".cleanup-",dir=path.parent); os.close(fd)
    try:
        Path(tmp).write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n");
        with open(tmp,"rb") as f: os.fsync(f.fileno())
        os.replace(tmp,path)
        d=os.open(path.parent,os.O_DIRECTORY); os.fsync(d); os.close(d)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def apply(plan):
    if plan.get("schema") != "mckernel.exact-evidence-cleanup.v1" or plan.get("status") != "AUDIT_PASS": die("invalid audit plan")
    root=Path(plan.get("candidate_root", "")); commit=plan.get("candidate_commit", "")
    root_guard(root,Path(__file__).parents[3],commit)
    # Recreate the complete authoritative target set.  Exact equality rejects
    # omitted, injected, reordered, renamed, relinked, or modified targets.
    fresh=audit(root,Path(__file__).parents[3],commit)
    if plan != fresh: die("audit plan differs from current exact audit")
    for r in plan["targets"]:
        p=Path(r["path"]); st=p.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or
                st.st_dev != r["dev"] or st.st_ino != r["ino"] or
                st.st_size != r["size"] or stat.S_IMODE(st.st_mode) != r["mode"] or
                hashlib.sha256(p.read_bytes()).hexdigest() != r["sha256"]):
            die("final target revalidation failed: "+str(p))
        os.unlink(p)
    plan["status"]="APPLY_PASS"; plan["removed"]=[r["path"] for r in plan["targets"]]; plan["removed_allocated_bytes"]=sum(r["allocated_bytes"] for r in plan["targets"]); return plan

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--plan",required=True); ap.add_argument("--apply",action="store_true"); a=ap.parse_args()
    p=a.plan
    if a.apply: obj=apply(json.loads(Path(p).read_text()))
    else: obj=audit(); obj["status"]="AUDIT_PASS"
    atomic_write(p,obj); print(json.dumps(obj,sort_keys=True))
if __name__=="__main__": main()
