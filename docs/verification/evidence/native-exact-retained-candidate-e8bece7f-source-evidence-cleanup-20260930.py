#!/usr/bin/env python3
"""Audit/apply exact Git-blob duplicates in scratch10 candidate evidence only."""
import argparse, hashlib, json, os, stat, subprocess, tempfile
from pathlib import Path
CANDIDATE_COMMIT="e8bece7fd55a862599facb6c5e81e7597a4a5c0d"
CANDIDATE_ROOT=Path("/home/holden/mckernel-work/scratch/mckernel-exact-candidate-e8bece7f-scratch-10")
CANDIDATE_IDENTITY="1831:5111900"; REPO=Path("/home/holden/mckernel"); SCRATCH=Path("/home/holden/mckernel-work/scratch")
EVIDENCE=SCRATCH/"native-exact-build-evidence-e8bece7f-scratch-10"; OUTPUT=SCRATCH/"native-exact-build-output-e8bece7f-scratch-10"
EXCLUSION=SCRATCH/"native-exact-candidate-operational-exclusion-exportset-14.json"; FAILURE=REPO/"docs/verification/evidence/native-exact-build-scratch10-temp-environment-failure-20260930.json"
EXPECTED_CONTAINER="8c56b1377fc66808ed85b348d2c09df82222d1a8c246a056f154c620b5cb401a"
PROTECTED_NAMES=("e8bece7f","scratch-10","native-exact-build","native-exact-inputs","native-exact-candidate-preparation","operational-exclusion","exportset-14")
def fail(x): raise SystemExit("FAIL_CLOSED: "+x)
def sha(b): return hashlib.sha256(b).hexdigest()
def git(repo,*a): return subprocess.check_output(["git","-C",str(repo),*a],stderr=subprocess.STDOUT).decode().strip()
def blob(repo,commit,path):
    try:return subprocess.check_output(["git","-C",str(repo),"show",f"{commit}:{path}"],stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:return None
def guard(root,repo=REPO,commit=CANDIDATE_COMMIT):
    root=Path(root); st=root.lstat()
    if root!=CANDIDATE_ROOT or root.is_symlink() or not stat.S_ISDIR(st.st_mode) or f"{st.st_dev}:{st.st_ino}"!=CANDIDATE_IDENTITY:fail("candidate root identity")
    if commit!=CANDIDATE_COMMIT or git(repo,"rev-parse",commit+"^{commit}")!=commit or git(root,"rev-parse","HEAD")!=commit:fail("candidate HEAD")
def base(root):
    b=Path(root)/"docs/verification/evidence"
    for p in (Path(root)/"docs",Path(root)/"docs/verification",b):
        if p.is_symlink() or not p.is_dir():fail("evidence ancestor")
    return b,b.resolve()
def census(root):
    def run(a):
        try:
            p=subprocess.run(a,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20);return {"argv":a,"returncode":p.returncode,"output":p.stdout,"stderr":p.stderr}
        except Exception as e:return {"argv":a,"error":type(e).__name__+":"+str(e)}
    c={"lsof":run(["sudo","-A","lsof","-nP","-w","+D",str(root)]),"mount":run(["findmnt","-T",str(root),"-o","SOURCE,FSTYPE,MAJ:MIN,TARGET"]),"docker":run(["sudo","-A","docker","ps","-a","--format","{{json .}}"]),"protected":[str(x) for x in (EVIDENCE,OUTPUT,EXCLUSION,FAILURE)],"container_removal":False}; validate_census(c);return c
def validate_census(c):
    l=c["lsof"]
    if l.get("returncode") not in (0,1) or l.get("stderr","").strip() or [x for x in l.get("output","").splitlines() if x and not x.startswith("COMMAND")]:fail("open reference census")
    m=c["mount"]; rows=[x.split() for x in m.get("output","").splitlines() if x.strip() and not x.startswith("SOURCE")]
    if m.get("returncode")!=0 or len(rows)!=1 or rows[0][:4]!=["/dev/loop39","ext4","7:39","/home/holden/mckernel-work/scratch"]:fail("mount census")
    if c["docker"].get("returncode")!=0:fail("docker census")
    retained=False
    for line in c["docker"].get("output","").splitlines():
        try:o=json.loads(line)
        except json.JSONDecodeError:fail("docker syntax")
        if o.get("ID")==EXPECTED_CONTAINER:
            retained=True
            if str(o.get("State","")).lower()!="exited":fail("retained container state")
        if str(o.get("State","")).lower() in ("running","restarting") and ("mckernel-exact" in str(o.get("Names","")) or "/home/holden/mckernel-work" in str(o.get("Mounts",""))):fail("running relevant container")
    if not retained:fail("retained container absent")
def audit(root=CANDIDATE_ROOT,repo=REPO,commit=CANDIDATE_COMMIT):
    guard(root,repo,commit); b,rb=base(root); safety=census(root); targets=[]; preserved=[]
    for p in sorted(b.rglob("*")):
        st=p.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:continue
        if os.path.commonpath((str(rb),str(p.resolve(strict=False))))!=str(rb):fail("escape")
        rel=str(p.relative_to(b)); gp="docs/verification/evidence/"+rel; data=p.read_bytes(); expected=blob(repo,commit,gp); r={"path":str(p),"restore_git_path":gp,"blob":git(repo,"rev-parse",f"{commit}:{gp}") if expected is not None else None,"mode":stat.S_IMODE(st.st_mode),"mtime_ns":st.st_mtime_ns,"size":st.st_size,"sha256":sha(data),"allocated_bytes":st.st_blocks*512,"dev":st.st_dev,"ino":st.st_ino,"nlink":st.st_nlink}
        if expected is not None and data==expected:targets.append(r)
        else:r["reason"]="untracked-or-delta";preserved.append(r)
    if not targets:fail("no exact Git duplicates")
    return {"schema":"mckernel.exact-git-source-cleanup.v1","status":"AUDIT_PASS","candidate_commit":commit,"candidate_root":str(root),"candidate_identity":CANDIDATE_IDENTITY,"targets":targets,"preserved":preserved,"safety_census":safety,"protected_paths":[str(x) for x in (EVIDENCE,OUTPUT,EXCLUSION,FAILURE)],"nested_ihk_deltas_preserved":True,"container_removal":False}
def stable(x):return {k:v for k,v in x.items() if k not in ("safety_census","fresh_safety_census")}
def write(path,obj):
    path=Path(path);fd,tmp=tempfile.mkstemp(prefix=".e8be-",dir=path.parent);payload=(json.dumps(obj,sort_keys=True,indent=2)+"\n").encode();off=0
    try:
        while off<len(payload):off+=os.write(fd,payload[off:])
        os.fsync(fd);st=os.fstat(fd)
        if st.st_nlink!=1 or os.path.lexists(path):fail("result collision")
        os.link(tmp,path);d=os.open(path.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
    finally:
        os.close(fd)
        if os.path.lexists(tmp):os.unlink(tmp)
def apply(plan):
    if plan.get("schema")!="mckernel.exact-git-source-cleanup.v1" or plan.get("status")!="AUDIT_PASS":fail("plan")
    root=Path(plan["candidate_root"]);guard(root,REPO,plan["candidate_commit"]);fresh=audit(root,REPO,plan["candidate_commit"])
    if stable(fresh)!=stable(plan):fail("plan differs")
    _,rb=base(root)
    for r in plan["targets"]:
        p=Path(r["path"]);st=p.lstat()
        if os.path.commonpath((str(rb),str(p.resolve(strict=False))))!=str(rb) or not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or (st.st_dev,st.st_ino)!=(r["dev"],r["ino"]) or st.st_size!=r["size"] or sha(p.read_bytes())!=r["sha256"]:fail("target changed")
        p.unlink();d=os.open(p.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
    plan["status"]="APPLY_PASS";plan["removed_allocated_bytes"]=sum(x["allocated_bytes"] for x in plan["targets"]);return plan
def main():
    a=argparse.ArgumentParser();a.add_argument("--plan",required=True);a.add_argument("--apply",action="store_true");a.add_argument("--write-plan",action="store_true");x=a.parse_args();r=apply(json.loads(Path(x.plan).read_text())) if x.apply else audit();write(x.plan,r) if x.write_plan else None;print(json.dumps(r,sort_keys=True))
if __name__=="__main__":raise SystemExit(main())
