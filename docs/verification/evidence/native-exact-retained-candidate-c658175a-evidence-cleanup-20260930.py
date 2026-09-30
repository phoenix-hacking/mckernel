#!/usr/bin/env python3
"""Plan exact Git-blob duplicate cleanup for retained c658175a only.

The default command is read-only and prints a complete restoration map.  It
  never mutates the live scratch build or candidate source outside the pinned
  evidence tree.  Its safety census is read-only.  Applying a plan is a
separate explicit, revalidated operation.
"""
import argparse, hashlib, json, os, stat, subprocess, tempfile
from pathlib import Path

CANDIDATE_COMMIT = "c658175ae1831e2caef6ecf59730a272f1324645"
CANDIDATE_ROOT = Path("/home/holden/mckernel-work/retained-exact-candidates/mckernel-exact-candidate-c658175a-scratch-7")
CANDIDATE_IDENTITY = "66306:47753167"
REPO = Path("/home/holden/mckernel")
LIVE_SCRATCH = Path("/home/holden/mckernel-work/scratch")
LIVE_CANDIDATE = LIVE_SCRATCH/"mckernel-exact-candidate-c658175a-scratch-7"
LIVE_FAILURE = REPO/"docs/verification/evidence/native-exact-build-c658175a-scratch7-runtime-self-digest-failure-20260930.json"
LIVE_EVIDENCE = LIVE_SCRATCH/"native-exact-build-evidence-c658175a-scratch-7-retry1"
LIVE_OUTPUT = LIVE_SCRATCH/"native-exact-build-output-c658175a-scratch-7-retry1"
PROTECTED_LIVE_EXCLUSION = LIVE_SCRATCH/"native-exact-candidate-operational-exclusion-runtimeblob-12.json"

def die(message): raise SystemExit("FAIL_CLOSED: " + message)
def sha(data): return hashlib.sha256(data).hexdigest()
def git(repo,*args): return subprocess.check_output(["git","-C",str(repo),*args],stderr=subprocess.STDOUT).decode().strip()
def live_guard(root):
    root=Path(root).resolve(strict=True)
    for p in (LIVE_CANDIDATE,LIVE_EVIDENCE,LIVE_OUTPUT,LIVE_FAILURE):
        q=Path(p).resolve(strict=False)
        if q == root or root in q.parents or q in root.parents: die("retained root overlaps live failure/build input")
    if LIVE_FAILURE.exists() and not LIVE_FAILURE.is_file(): die("live failure record is not regular")

def root_guard(root, repo, commit):
    root=Path(root)
    if root != CANDIDATE_ROOT or not root.is_absolute() or root.is_symlink() or not root.is_dir(): die("wrong candidate root")
    st=root.stat()
    if f"{st.st_dev}:{st.st_ino}" != CANDIDATE_IDENTITY: die("candidate root identity differs")
    if commit != CANDIDATE_COMMIT: die("wrong candidate commit")
    try:
        if git(repo,"rev-parse",commit+"^{commit}") != commit or git(root,"rev-parse","HEAD") != commit: die("candidate HEAD differs")
    except (OSError,subprocess.CalledProcessError): die("candidate checkout unavailable")
    live_guard(root)

def evidence_base(root):
    base=Path(root)/"docs/verification/evidence"
    for p in (Path(root)/"docs",Path(root)/"docs/verification",base):
        if p.is_symlink() or not p.is_dir(): die("evidence ancestor missing or linked")
    rr=Path(root).resolve(strict=True); rb=base.resolve(strict=True)
    if os.path.commonpath((str(rr),str(rb))) != str(rr): die("evidence path escapes candidate")
    return base,rb

def census(root):
    """Capture safety state without opening or mutating any build input."""
    root=Path(root)
    def run(argv,timeout=15):
        try:
            p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=timeout,check=False)
            return {"argv":argv,"returncode":p.returncode,"output":p.stdout,"stderr":p.stderr}
        except (OSError,subprocess.TimeoutExpired) as exc:
            return {"argv":argv,"error":type(exc).__name__+":"+str(exc)}
    leases=[]
    for p in sorted(LIVE_SCRATCH.iterdir()):
        if p.is_file() and ("lease" in p.name or "operational-exclusion" in p.name):
            st=p.stat(); leases.append({"path":str(p),"dev":st.st_dev,"ino":st.st_ino,"uid":st.st_uid,"gid":st.st_gid,"mode":stat.S_IMODE(st.st_mode)})
    records=[]
    for item in leases:
        rec=run(["sudo","-A","cat",item["path"]])
        try: owner=json.loads(rec.get("output","")) if rec.get("returncode")==0 else None
        except json.JSONDecodeError: owner=None
        item["owner_record"]={k:owner.get(k) for k in ("pid","starttime","state","immutable") if owner} if owner else None
        records.append(item)
    result={"open_processes":run(["sudo","-A","lsof","-nP","+D",str(root)]),
            "mount_device":run(["findmnt","-T",str(root),"-o","SOURCE,FSTYPE,MAJ:MIN,TARGET"]),
            "docker_all":run(["sudo","-A","docker","ps","-a","--no-trunc","--format","{{json .}}"]),
            "lease_exclusion_paths":records,
            "lease_exclusion_listing":run(["find",str(LIVE_SCRATCH),"-maxdepth","1","-type","f","(","-name","*lease*","-o","-name","*operational-exclusion*",")","-printf","%p %D:%i %u:%g %m\\n"]),
            "lease_policy":"historical tombstones require immutable-owner policy or absent owner PID/starttime; live f021 exclusion remains untouched",
            "live_exclusion_untouched":True}
    validate_census(result)
    return result

def validate_census(c):
    l=c["open_processes"]
    if l.get("returncode") not in (0,1): die("lsof census failed")
    payload=[x for x in (l.get("output","")+"\n"+l.get("stderr","")).splitlines() if x and not x.startswith("lsof:") and not x.startswith("COMMAND")]
    if l.get("returncode")==1 and payload: die("lsof reported open reference")
    if l.get("returncode")==0 and payload: die("lsof reported open reference")
    m=c["mount_device"]
    if m.get("returncode") != 0: die("mount census failed")
    mount_lines=[x.split() for x in m.get("output","").splitlines() if x.strip() and not x.startswith("SOURCE")]
    if len(mount_lines)!=1 or mount_lines[0][:4] != ["/dev/nvme0n1p2","ext4","259:2","/"]: die("unexpected nested mount/device")
    d=c["docker_all"]
    if d.get("returncode") != 0: die("Docker census failed")
    for line in d.get("output","").splitlines():
        try: obj=json.loads(line)
        except json.JSONDecodeError: die("Docker census malformed")
        if str(obj.get("State","")).lower() in ("running","restarting") and (str(obj.get("Names","")).startswith("mckernel-exact") or "/home/holden/mckernel-work" in str(obj.get("Mounts","") )): die("relevant running container")
    for item in c.get("lease_exclusion_paths",[]):
        owner=item.get("owner_record") or {}; pid=owner.get("pid"); active=False
        if pid:
            try:
                text=Path(f"/proc/{int(pid)}/stat").read_text(); active=text.rsplit(")",1)[1].split()[19] == str(owner.get("starttime"))
            except (OSError,ValueError,IndexError): active=False
        if active and Path(item["path"]).resolve() != PROTECTED_LIVE_EXCLUSION.resolve(): die("active owner exclusion")
        if active and Path(item["path"]).resolve() == PROTECTED_LIVE_EXCLUSION.resolve(): item["protected_active_owner"]=True

def blob(repo,commit,path):
    try: return subprocess.check_output(["git","-C",str(repo),"show",f"{commit}:{path}"],stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError: return None

def audit(root=CANDIDATE_ROOT,repo=REPO,commit=CANDIDATE_COMMIT):
    root_guard(root,repo,commit); base,resolved=evidence_base(root); targets=[]; preserved=[]; safety=census(root)
    for path in sorted(base.rglob("*")):
        st=path.lstat()
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1: continue
        if os.path.commonpath((str(resolved),str(path.resolve(strict=False)))) != str(resolved): die("target escapes evidence")
        rel=str(path.relative_to(base)); restore="docs/verification/evidence/"+rel; expected=blob(repo,commit,restore)
        if expected is None: preserved.append({"path":str(path),"reason":"not-present-in-pinned-Git-commit"}); continue
        data=path.read_bytes(); digest=sha(data)
        row={"path":str(path),"restore_git_path":restore,"blob":git(repo,"rev-parse",f"{commit}:{restore}"),"mode":stat.S_IMODE(st.st_mode),"mtime_ns":st.st_mtime_ns,"size":st.st_size,"sha256":digest,"allocated_bytes":st.st_blocks*512,"dev":st.st_dev,"ino":st.st_ino}
        if data == expected and digest == sha(expected): targets.append(row)
        else: row["reason"]="content-or-size-differs-from-pinned-Git-blob"; preserved.append(row)
    if not targets: die("no exact duplicate evidence targets")
    return {"schema":"mckernel.exact-evidence-cleanup.v1","status":"AUDIT_PASS","candidate_commit":commit,"candidate_root":str(root),"candidate_identity":CANDIDATE_IDENTITY,"targets":targets,"preserved":preserved,"safety_census":safety,"recovery":"restore each restore_git_path from the exact blob at candidate_commit","live_failure_untouched":str(LIVE_FAILURE),"live_build_inputs_untouched":[str(LIVE_EVIDENCE),str(LIVE_OUTPUT)]}

def atomic_write(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=".c658-cleanup-",dir=path.parent); temp_identity=os.fstat(fd); os.close(fd)
    try:
        Path(tmp).write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")
        f=os.open(tmp,os.O_RDONLY); os.fsync(f); os.close(f)
        if os.path.lexists(path): die("plan destination exists; no replacement")
        st=os.lstat(tmp)
        if (st.st_dev,st.st_ino)!=(temp_identity.st_dev,temp_identity.st_ino): die("plan temp replaced")
        os.link(tmp,path); d=os.open(path.parent,os.O_DIRECTORY); os.fsync(d); os.close(d)
    finally:
        if os.path.lexists(tmp):
            st=os.lstat(tmp)
            if (st.st_dev,st.st_ino)==(temp_identity.st_dev,temp_identity.st_ino): os.unlink(tmp)

def apply(plan):
    if plan.get("schema") != "mckernel.exact-evidence-cleanup.v1" or plan.get("status") != "AUDIT_PASS": die("invalid plan")
    root=Path(plan.get("candidate_root","")); commit=plan.get("candidate_commit",""); root_guard(root,REPO,commit)
    fresh=audit(root,REPO,commit)
    if fresh != plan: die("audit plan differs from fresh audit")
    _,resolved=evidence_base(root)
    for row in plan["targets"]:
        p=Path(row["path"]); st=p.lstat()
        if os.path.commonpath((str(resolved),str(p.resolve(strict=False)))) != str(resolved) or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or (st.st_dev,st.st_ino)!=(row["dev"],row["ino"]) or st.st_size!=row["size"] or stat.S_IMODE(st.st_mode)!=row["mode"] or sha(p.read_bytes())!=row["sha256"]: die("final target revalidation failed: "+str(p))
        p.unlink()
        d=os.open(p.parent,os.O_DIRECTORY); os.fsync(d); os.close(d)
    plan["status"]="APPLY_PASS"; plan["removed_allocated_bytes"]=sum(x["allocated_bytes"] for x in plan["targets"]); plan["removed"]=[x["path"] for x in plan["targets"]]; return plan

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--plan",required=True); ap.add_argument("--apply",action="store_true"); ap.add_argument("--write-plan",action="store_true"); a=ap.parse_args()
    result=apply(json.loads(Path(a.plan).read_text())) if a.apply else audit()
    if a.write_plan: atomic_write(a.plan,result)
    print(json.dumps(result,sort_keys=True)); return 0
if __name__ == "__main__": main()
