#!/usr/bin/env python3
"""Audit/apply exact Git duplicates under scratch11 evidence only."""
import argparse,hashlib,json,os,stat,subprocess,tempfile
from pathlib import Path
COMMIT="acd4197b6e1f53715f75cad6e2e7677d8ab24bc0"; ROOT=Path("/home/holden/mckernel-work/scratch/mckernel-exact-candidate-acd4197b-scratch-11"); ID="1831:4063240"; REPO=Path("/home/holden/mckernel"); SCRATCH=Path("/home/holden/mckernel-work/scratch")
EVID=SCRATCH/"native-exact-build-evidence-acd4197b-scratch-11"; OUT=SCRATCH/"native-exact-build-output-acd4197b-scratch-11"; META=SCRATCH/"native-exact-metadata-evidence-acd4197b-scratch-11"; BACK=SCRATCH/"native-exact-metadata-backup-acd4197b-scratch-11"; REQ=SCRATCH/"native-exact-build-request-acd4197b-scratch-11.json"; INPUT=SCRATCH/"native-exact-inputs-acd4197b-scratch-11.json"; PREP=SCRATCH/"native-exact-candidate-preparation-acd4197b-scratch-11.log"; TERM=SCRATCH/"native-exact-candidate-preparation-acd4197b-scratch-11-terminal.json"; EXCLUSION=SCRATCH/"native-exact-candidate-operational-exclusion-exportset-15.json"; FAILURE=REPO/"docs/verification/evidence/native-exact-build-scratch11-additive-parameter-failure-20260930.json"
PROTECTED=(EVID,OUT,META,BACK,REQ,INPUT,PREP,TERM,EXCLUSION,FAILURE)
CONTAINER_ID="d19725703c7fbfd35a76a0d36a7d3dac4eb0d09c095ce91e7a83a36f4746d954"; CONTAINER_NAME="mckernel-exact-91c18291f5dd49308177d6c9d41a5089"
def die(x):raise SystemExit("FAIL_CLOSED: "+x)
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(["git","-C",str(REPO),*a],stderr=subprocess.STDOUT).decode().strip()
def blob(p):
 try:return subprocess.check_output(["git","-C",str(REPO),"show",f"{COMMIT}:{p}"],stderr=subprocess.STDOUT)
 except subprocess.CalledProcessError:return None
def guard():
 st=ROOT.lstat()
 if ROOT.is_symlink() or not stat.S_ISDIR(st.st_mode) or f"{st.st_dev}:{st.st_ino}"!=ID or git("rev-parse",COMMIT+"^{commit}")!=COMMIT or subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()!=COMMIT:die("candidate binding")
def evidence_base():
 base=ROOT/"docs/verification/evidence"
 for p in (ROOT/"docs",ROOT/"docs/verification",base):
  if p.is_symlink() or not p.is_dir():die("evidence ancestor")
 return base,base.resolve()
def census():
 def run(a):
  try:p=subprocess.run(a,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20);return {"returncode":p.returncode,"output":p.stdout,"stderr":p.stderr,"argv":a}
  except Exception as e:return {"error":type(e).__name__+":"+str(e),"argv":a}
 c={"lsof":run(["sudo","-A","lsof","-nP","-w","+D",str(ROOT)]),"mount":run(["findmnt","-T",str(ROOT),"-o","SOURCE,FSTYPE,MAJ:MIN,TARGET"]),"docker":run(["sudo","-A","docker","ps","-a","--format","{{json .}}"]),"retained_inspect":run(["sudo","-A","docker","inspect","--format","{{json .State}}",CONTAINER_ID]),"protected":[str(x) for x in PROTECTED],"container_removal":False};validate(c);return c
def validate(c):
 l=c["lsof"]
 if l.get("returncode") not in(0,1) or l.get("stderr","").strip() or [x for x in l.get("output","").splitlines() if x and not x.startswith("COMMAND")]:die("lsof")
 m=c["mount"];rows=[x.split() for x in m.get("output","").splitlines() if x.strip() and not x.startswith("SOURCE")]
 if m.get("returncode")!=0 or len(rows)!=1 or rows[0][:4]!=["/dev/loop39","ext4","7:39","/home/holden/mckernel-work/scratch"]:die("mount")
 if c["docker"].get("returncode")!=0:die("docker")
 retained=False
 for x in c["docker"].get("output","").splitlines():
  try:o=json.loads(x)
  except json.JSONDecodeError:die("docker json")
  if CONTAINER_ID.startswith(str(o.get("ID",""))) and o.get("Names")==CONTAINER_NAME:
   retained=True
   if str(o.get("State","")).lower()!="exited":die("retained container state")
  if str(o.get("State","")).lower() in("running","restarting") and("mckernel-exact" in str(o.get("Names","")) or "/home/holden/mckernel-work" in str(o.get("Mounts",""))):die("running container")
 if not retained:die("retained container absent")
 i=c.get("retained_inspect",{})
 if i.get("returncode")!=0 or i.get("stderr","").strip():die("retained inspect")
 try:state=json.loads(i.get("output",""))
 except json.JSONDecodeError:die("retained inspect json")
 if state.get("Status")!="exited" or state.get("Pid")!=0 or state.get("ExitCode")!=1 or state.get("OOMKilled") is not False:die("retained terminal identity")
def audit():
 guard();base,rb=evidence_base();targets=[];preserved=[];safe=census()
 for p in sorted(base.rglob("*")):
  st=p.lstat()
  if p.is_symlink() or not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:continue
  if os.path.commonpath((str(rb),str(p.resolve(strict=False))))!=str(rb):die("escape")
  rel="docs/verification/evidence/"+str(p.relative_to(base));data=p.read_bytes();exp=blob(rel);r={"path":str(p),"restore_git_path":rel,"blob":git("rev-parse",f"{COMMIT}:{rel}") if exp is not None else None,"mode":stat.S_IMODE(st.st_mode),"mtime_ns":st.st_mtime_ns,"size":st.st_size,"sha256":sha(data),"allocated_bytes":st.st_blocks*512,"dev":st.st_dev,"ino":st.st_ino,"nlink":st.st_nlink}
  (targets if exp is not None and data==exp else preserved).append(r)
 if not targets:die("no exact duplicates")
 return {"schema":"mckernel.exact-git-source-cleanup.v1","status":"AUDIT_PASS","candidate_commit":COMMIT,"candidate_root":str(ROOT),"candidate_identity":ID,"targets":targets,"preserved":preserved,"safety_census":safe,"protected_paths":[str(x) for x in PROTECTED],"nested_delta_preserved":True,"container_removal":False}
def apply(plan):
 if plan.get("schema")!="mckernel.exact-git-source-cleanup.v1" or plan.get("status")!="AUDIT_PASS":die("plan")
 fresh=audit();stable=lambda x:{k:v for k,v in x.items() if k!="safety_census"}
 if stable(fresh)!=stable(plan):die("plan differs")
 _,rb=evidence_base()
 for r in plan["targets"]:
  p=Path(r["path"]);st=p.lstat()
  if os.path.commonpath((str(rb),str(p.resolve(strict=False))))!=str(rb) or not stat.S_ISREG(st.st_mode) or(st.st_dev,st.st_ino)!=(r["dev"],r["ino"]) or st.st_nlink!=1 or st.st_size!=r["size"] or sha(p.read_bytes())!=r["sha256"]:die("target changed")
  p.unlink();d=os.open(p.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
 plan["status"]="APPLY_PASS";plan["removed_allocated_bytes"]=sum(x["allocated_bytes"] for x in plan["targets"]);return plan
def write(path,obj):
 path=Path(path);fd,tmp=tempfile.mkstemp(prefix=".acd4-",dir=path.parent);payload=(json.dumps(obj,sort_keys=True,indent=2)+"\n").encode();off=0
 try:
  while off<len(payload):off+=os.write(fd,payload[off:])
  os.fsync(fd)
  if os.fstat(fd).st_nlink!=1 or os.path.lexists(path):die("result collision")
  os.link(tmp,path);d=os.open(path.parent,os.O_DIRECTORY);os.fsync(d);os.close(d)
 finally:
  os.close(fd)
  if os.path.lexists(tmp):os.unlink(tmp)
def main():
 a=argparse.ArgumentParser();a.add_argument("--plan",required=True);a.add_argument("--apply",action="store_true");a.add_argument("--write-plan",action="store_true");x=a.parse_args();r=apply(json.loads(Path(x.plan).read_text())) if x.apply else audit();write(x.plan,r) if x.write_plan else None;print(json.dumps(r,sort_keys=True))
if __name__=="__main__":raise SystemExit(main())
