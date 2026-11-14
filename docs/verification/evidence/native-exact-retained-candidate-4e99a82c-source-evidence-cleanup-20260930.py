#!/usr/bin/env python3
"""Read-only audit inventory for exact Git duplicates under scratch12."""
import argparse, hashlib, json, os, stat, subprocess, tempfile
from pathlib import Path
COMMIT="4e99a82c9b87a7cf3d6002b75ec380fef37af7a1"; ROOT=Path("/home/holden/mckernel-work/scratch/mckernel-exact-candidate-4e99a82c-scratch-12"); ID="1831:3693246"; REPO=Path("/home/holden/mckernel"); SCRATCH=Path("/home/holden/mckernel-work/scratch")
EVID=SCRATCH/"native-exact-build-evidence-4e99a82c-scratch-12"; OUT=SCRATCH/"native-exact-build-output-4e99a82c-scratch-12"; META=SCRATCH/"native-exact-metadata-evidence-4e99a82c-scratch-12"; BACK=SCRATCH/"native-exact-metadata-backup-4e99a82c-scratch-12"; REQ=SCRATCH/"native-exact-build-request-4e99a82c-scratch-12.json"; INPUT=SCRATCH/"native-exact-inputs-4e99a82c-scratch-12.json"; PREP=SCRATCH/"native-exact-candidate-preparation-4e99a82c-scratch-12.log"; TERM=SCRATCH/"native-exact-candidate-preparation-4e99a82c-scratch-12-terminal.json"; EXCLUSION=SCRATCH/"native-exact-candidate-operational-exclusion-exportset-24.json"; FAILURE=REPO/"docs/verification/evidence/native-exact-mckernel-image-exportset24-failure-20260930.json"
IMAGE=(SCRATCH/"native-exact-mckernel-image-prepare-inputs-4e99a82c-exportset-24.json",SCRATCH/"native-exact-mckernel-image-request-4e99a82c-exportset-24.json",SCRATCH/"native-exact-mckernel-image-toolchain-4e99a82c-exportset-24.json",SCRATCH/"native-exact-mckernel-image-owner-evidence-4e99a82c-exportset-24",SCRATCH/"native-exact-mckernel-image-work-4e99a82c-exportset-24"); LIBDWARF=SCRATCH/"native-exact-mckernel-gitlink-libdwarf-4e99a82c-exportset-23"; NIGHTLY=SCRATCH/"native-exact-rust-nightly-1.95.0-20260218-1"; PROTECTED=(EVID,OUT,META,BACK,REQ,INPUT,PREP,TERM,EXCLUSION,FAILURE,*IMAGE,LIBDWARF,NIGHTLY)
CONTAINER_ID="053b5528de7605a712b7842b0145c7e777843c2fd14225174ac8959918a7d24f"; CONTAINER_NAME="mckernel-image-69d5302ef1b74816aec831cf959404ee"
def die(x): raise SystemExit("FAIL_CLOSED: "+x)
def sha(b): return hashlib.sha256(b).hexdigest()
def env():
 e=os.environ.copy(); e.update(GIT_NO_REPLACE_OBJECTS="1",GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=os.devnull); return e
def git(*a): return subprocess.check_output(["git","-c",f"safe.directory={REPO}","-C",str(REPO),*a],stderr=subprocess.STDOUT,env=env()).decode().strip()
def blob(p):
 try:return subprocess.check_output(["git","-c",f"safe.directory={REPO}","-C",str(REPO),"cat-file","blob",git("rev-parse",f"{COMMIT}:{p}")],stderr=subprocess.STDOUT,env=env())
 except subprocess.CalledProcessError:return None
def guard():
 s=ROOT.lstat()
 if ROOT.is_symlink() or not stat.S_ISDIR(s.st_mode) or f"{s.st_dev}:{s.st_ino}"!=ID: die("candidate binding")
 if git("rev-parse",COMMIT+"^{commit}")!=COMMIT: die("commit unavailable")
 try:h=subprocess.check_output(["git","-c",f"safe.directory={ROOT}","-C",str(ROOT),"rev-parse","HEAD"],text=True,env=env()).strip()
 except (OSError,subprocess.CalledProcessError):die("candidate checkout")
 if h!=COMMIT:die("candidate HEAD")
def base():
 b=ROOT/"docs/verification/evidence"
 for p in (ROOT/"docs",ROOT/"docs/verification",b):
  if p.is_symlink() or not p.is_dir():die("evidence ancestor")
 r=b.resolve(strict=True)
 if os.path.commonpath((str(ROOT.resolve()),str(r)))!=str(ROOT.resolve()):die("evidence escape")
 return b,r
def run(a):
 try:
  p=subprocess.run(a,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20);return {"returncode":p.returncode,"output":p.stdout,"stderr":p.stderr,"argv":a}
 except Exception as e:return {"error":type(e).__name__+":"+str(e),"argv":a}
def mounts():
 out=[]
 for line in Path("/proc/self/mountinfo").read_text().splitlines():
  x=line.split(" - ",1)[0].split()
  if len(x)>=5:out.append(x[4].replace("\\040"," ").replace("\\011","\t"))
 return out
def protected():
 rows=[]
 for q in PROTECTED:
  p=Path(q); x=p
  while x!=x.parent:
   if x.is_symlink():die("protected symlink ancestor")
   x=x.parent
  try:s=p.lstat()
  except OSError:die("protected missing: "+str(p))
  if p.is_symlink():die("protected symlink")
  r={"path":str(p),"type":"directory" if stat.S_ISDIR(s.st_mode) else "file" if stat.S_ISREG(s.st_mode) else "other","dev":s.st_dev,"ino":s.st_ino,"mode":stat.S_IMODE(s.st_mode)}
  if stat.S_ISREG(s.st_mode):r.update(size=s.st_size,sha256=sha(p.read_bytes()))
  rows.append(r)
 return rows
def validate(c):
 l=c["lsof"]
 if l.get("returncode") not in (0,1) or l.get("stderr","").strip() or any(x for x in l.get("output","").splitlines() if x and not x.startswith("COMMAND")):die("lsof")
 m=c["mount"]; rows=[x.split() for x in m.get("output","").splitlines() if x.strip() and not x.startswith("SOURCE")]
 if m.get("returncode")!=0 or len(rows)!=1 or rows[0][:4]!=["/dev/loop39","ext4","7:39","/home/holden/mckernel-work/scratch"]:die("mount")
 if c.get("nested_mounts"):die("nested mount")
 d=c["docker"]
 if d.get("returncode")!=0:die("docker")
 found=False
 for line in d.get("output","").splitlines():
  try:o=json.loads(line)
  except json.JSONDecodeError:die("docker json")
  if CONTAINER_ID.startswith(str(o.get("ID",""))) and o.get("Names")==CONTAINER_NAME:
   found=True
   if str(o.get("State","")).lower()!="exited":die("retained state")
  if str(o.get("State","")).lower() in ("running","restarting") and ("mckernel" in str(o.get("Names","")) or "/home/holden/mckernel-work" in str(o.get("Mounts",""))):die("live related container")
 if not found:die("retained container absent")
 i=c["inspect"]
 if i.get("returncode")!=0 or i.get("stderr","").strip():die("inspect")
 try:s=json.loads(i.get("output",""))
 except json.JSONDecodeError:die("inspect json")
 if s.get("Status")!="exited" or s.get("Pid")!=0 or s.get("ExitCode")!=1 or s.get("OOMKilled") is not False:die("terminal identity")
def census():
 c={"lsof":run(["sudo","-A","lsof","-nP","-w","+D",str(ROOT)]),"mount":run(["findmnt","-T",str(ROOT),"-o","SOURCE,FSTYPE,MAJ:MIN,TARGET"]),"nested_mounts":[x for x in mounts() if x.startswith(str(ROOT)+"/")],"docker":run(["sudo","-A","docker","ps","-a","--format","{{json .}}"]),"inspect":run(["sudo","-A","docker","inspect","--format","{{json .State}}",CONTAINER_ID]),"protected":protected()}; validate(c); return c
def audit():
 guard(); b,r=base(); targets=[]; preserved=[]; safe=census()
 for p in sorted(b.rglob("*")):
  s=p.lstat()
  if p.is_symlink() or not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:continue
  if os.path.commonpath((str(r),str(p.resolve(strict=False))))!=str(r):die("target escape")
  rel="docs/verification/evidence/"+str(p.relative_to(b)); data=p.read_bytes(); exp=blob(rel); row={"path":str(p),"restore_git_path":rel,"blob":git("rev-parse",f"{COMMIT}:{rel}") if exp is not None else None,"mode":stat.S_IMODE(s.st_mode),"mtime_ns":s.st_mtime_ns,"size":s.st_size,"sha256":sha(data),"allocated_bytes":s.st_blocks*512,"dev":s.st_dev,"ino":s.st_ino,"nlink":s.st_nlink}
  (targets if exp is not None and data==exp else preserved).append(row)
 if not targets:die("no exact duplicates")
 return {"schema":"mckernel.exact-git-source-audit.v1","status":"AUDIT_PASS","candidate_commit":COMMIT,"candidate_root":str(ROOT),"candidate_identity":ID,"targets":targets,"preserved":preserved,"safety_census":safe,"protected_paths":[str(p) for p in PROTECTED],"nested_delta_preserved":True}
def publish(path,obj):
 path=Path(path); data=(json.dumps(obj,sort_keys=True,indent=2)+"\n").encode()
 with tempfile.NamedTemporaryFile(mode="wb",dir=path.parent,prefix=".4e99-audit-",delete=True) as f:
  n=0
  while n<len(data):n+=os.write(f.fileno(),data[n:])
  os.fsync(f.fileno())
  if os.path.lexists(path):die("plan collision")
  os.link(f.name,path); d=os.open(path.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
def main():
 p=argparse.ArgumentParser();p.add_argument("--plan",required=True);a=p.parse_args(); publish(a.plan,audit()); print("AUDIT_PASS")
if __name__=="__main__":raise SystemExit(main())
