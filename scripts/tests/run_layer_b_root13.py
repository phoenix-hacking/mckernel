"""Fail-closed packet-28 root13 executor (production and injectable backends)."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, time, uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

ROOT="/home/holden/mckernel-work/scratch/stability-layer-b-native-owner-bootstrap-root13-20260928-28"
SOURCE="/home/holden/mckernel/scripts/tests/layer_b_native_owner_v1.c"
SOURCE_SHA256="2c157335e88b2088c56fc40fd6c0d966dc653ea68b4726e51feb1d4b4e62eafc"
TOKEN_SHA256="559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd"
OBSERVER_SHA256="2f18755073ef3c33b4df9178f708187d344a50b03240b0fb7ce51a1d2c87e5bc"
TEST_SHA256="ce6ebd78da99c45e5caccc5c87cf6423ee1738ae884c5dd9c5bf3745a8c371c9"
PACKET24_SHA256="ebc8778cda8d667c40b26362e4540e68a7217b0e7110526d31b7d2bf1c7a13a5"
PACKET28_SHA256="570d174a2a9fad68b21c445cd5a08df62725647456ede144c4f35f5eaa12311d"
TOOL_PATHS=("/usr/bin/gcc","/usr/lib/gcc/x86_64-linux-gnu/9/cc1","/usr/bin/as","/usr/bin/env","/usr/bin/prlimit","/usr/bin/timeout","/usr/bin/systemd-run","/usr/bin/systemctl","/usr/bin/journalctl","/usr/bin/readelf","/usr/bin/objdump","/usr/bin/cat","/usr/bin/dd","/usr/bin/mkfifo","/usr/bin/sync")
INCLUDES=("/usr/lib/gcc/x86_64-linux-gnu/9/include","/usr/include/x86_64-linux-gnu","/usr/include")
PACKET="/home/holden/mckernel/docs/verification/stability-layer-b-native-owner-bootstrap-root13-execution-packet-20260928-28.md"
class State(str,Enum):
 PRECHECK="PRECHECK"; SUBMIT_ONCE="SUBMIT_ONCE"; PRE_ACK="PRE_ACK"; WRITER="WRITER_INITIATED_POSSIBLE_COMPILER"; POST_ACK="POST_ACK"; CLEANUP="CLEANUP"; EVIDENCE="EVIDENCE"; TERMINAL="TERMINAL"
@dataclass
class Result:
 terminal:str=""; state:State=State.PRECHECK; first_failure:str|None=None; cleanup_errors:list[str]=field(default_factory=list); commands:list[dict[str,Any]]=field(default_factory=list); evidence:dict[str,Any]=field(default_factory=dict); writer_started:bool=False; killed:bool=False
 def fail(self,x):
  if self.first_failure is None:self.first_failure=x
def unit_name(nonce):
 try: uuid.UUID(nonce)
 except (ValueError,TypeError,AttributeError) as e: raise ValueError("invalid UUID") from e
 return f"layer-b-native-owner-bootstrap-root13-20260928-28-{nonce}.service"
def submission_argv(root,unit):
 b=os.path.join(root,"layer_b_native_owner_v1")
 return ["/usr/bin/timeout","--signal=TERM","--kill-after=1s","10s","/usr/bin/systemd-run","--user","--unit="+unit,"--service-type=exec","--working-directory="+root,"--property=RemainAfterExit=yes","--property=Restart=no","--property=KillMode=control-group","--property=RuntimeMaxSec=60s","--property=TimeoutStartSec=120s","--property=TimeoutStopSec=5s","--property=SendSIGKILL=yes","--property=UMask=0077","--property=StandardInput=null","--property=StandardOutput=file:"+root+"/logs/unit.stdout","--property=StandardError=file:"+root+"/logs/unit.stderr","--no-block","--property=ExecStartPre=/usr/bin/cat "+root+"/logs/identity.fifo","--","/usr/bin/env","-i","LC_ALL=C","LANG=C","HOME="+root+"/home","TMPDIR="+root+"/tmp","PATH=/usr/bin:/bin","/usr/bin/prlimit","--core=0:0","--cpu=55:55","--nofile=256:256","--fsize=67108864:67108864","--as=536870912:536870912","--","/usr/bin/gcc","-v","-std=c11","-O2","-Wall","-Wextra","-Werror","-fno-pie","-pthread","-nostdinc","-isystem",*INCLUDES,"-save-temps=obj","-MD","-MF",b+".d","-MT",b+".o","-c",SOURCE,"-o",b+".o"]
def _ok(r): return not r.get("timed_out",False) and int(r.get("status",125))==0
class LocalBackend:
 def __init__(self,packet=PACKET): self.packet=packet; self._evidence_root=None
 def uuid(self): return str(uuid.uuid4())
 def exists(self,p): return os.path.lexists(p)
 def unit_exists(self,u): return False
 def authenticate(self,tools,includes,source,source_sha,observer_sha,test_sha,packet24_sha):
  if tuple(tools)!=tuple(TOOL_PATHS) or tuple(includes)!=tuple(INCLUDES) or not os.path.isfile(source): return False
  if hashlib.sha256(open(source,'rb').read()).hexdigest()!=source_sha:return False
  observer=os.path.join(os.path.dirname(source),"layer_b_systemd_cgroup_observer.py")
  tests=os.path.join(os.path.dirname(source),"test_layer_b_systemd_cgroup_observer.py")
  if hashlib.sha256(open(observer,'rb').read()).hexdigest()!=observer_sha or hashlib.sha256(open(tests,'rb').read()).hexdigest()!=test_sha:return False
  if packet24_sha!=PACKET24_SHA256 or not os.path.isfile(self.packet):return False
  if hashlib.sha256(open(self.packet,'rb').read()).hexdigest()!=PACKET28_SHA256:return False
  return all(os.path.exists(x) for x in tools+includes)
 def mkdir_tree(self,r,names,mode): os.mkdir(r,mode); [os.mkdir(os.path.join(r,n),mode) for n in names]; self._evidence_root=os.path.join(r,"logs")
 def mkfifo(self,p,mode): os.mkfifo(p,mode)
 def write_token(self,p,data,mode):
  fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,mode)
  try: os.write(fd,data); os.fsync(fd)
  finally: os.close(fd)
  if hashlib.sha256(data).hexdigest()!=TOKEN_SHA256: raise ValueError("token hash")
 def fsync_record(self,x):
  if not self._evidence_root:return
  fd=os.open(os.path.join(self._evidence_root,"events.jsonl"),os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
  try: os.write(fd,(json.dumps(x,sort_keys=True)+"\n").encode()); os.fsync(fd)
  finally: os.close(fd)
 def run(self,argv,timeout):
  argv=tuple(argv)
  if any("/bin/sh" in x or ("kill" in x.lower() and x.isdigit()) for x in argv): raise ValueError("forbidden argv")
  try:
   p=subprocess.run(argv,capture_output=True,timeout=timeout,check=False); return {"status":p.returncode,"stdout":p.stdout.decode(errors="replace"),"stderr":p.stderr.decode(errors="replace")}
  except subprocess.TimeoutExpired as e:return {"status":124,"timed_out":True,"stdout":""}
 def show_argv(self,u): return ("/usr/bin/timeout","--signal=TERM","--kill-after=1s","2s","/usr/bin/systemctl","--user","show",u,"--property=Id,InvocationID,ActiveState,SubState,Result,ControlGroup,ControlPID,MainPID,ExecMainCode,ExecMainStatus,ExecMainExitTimestampMonotonic,ExecStartPre")
 def sync_argv(self,p): return ("/usr/bin/timeout","--signal=TERM","--kill-after=1s","2s","/usr/bin/sync","-f",p)
 def writer_argv(self,t,f): return ("/usr/bin/timeout","--signal=TERM","--kill-after=1s","2s","/usr/bin/dd","if="+t,"of="+f,"bs=1","count=1","status=none")
 def stop_argv(self,u): return ("/usr/bin/timeout","--signal=TERM","--kill-after=1s","5s","/usr/bin/systemctl","--user","stop",u)
 def kill_argv(self,u): return ("/usr/bin/timeout","--signal=TERM","--kill-after=1s","3s","/usr/bin/systemctl","--user","--signal=SIGKILL","--kill-who=all","kill",u)
 def reset_argv(self,u): return ("/usr/bin/systemctl","--user","reset-failed",u)
 def journal_argv(self,u): return ("/usr/bin/timeout","--signal=TERM","--kill-after=1s","6s","/usr/bin/journalctl","--user","-u",u)
 def _p(self,r):
  p={};
  for line in r.get("stdout","").splitlines():
   if "=" in line:k,v=line.split("=",1);p[k]=v
  return p or r.get("properties",{})
 def valid_pre_ack(self,r,u):
  p=self._p(r);return p.get("Id")==u and p.get("InvocationID") and p.get("ControlGroup") and p.get("MainPID")=="0" and p.get("ControlPID","").isdigit() and p.get("ActiveState") in ("active","activating")
 def valid_success(self,r,u):
  p=self._p(r);return p.get("Id")==u and p.get("Result")=="success" and p.get("ExecMainCode")=="CLD_EXITED" and p.get("ExecMainStatus")=="0" and p.get("ExecMainExitTimestampMonotonic")
 def resolved(self,r,u):
  p=self._p(r);return p.get("MainPID","0")=="0" and p.get("ControlPID","0")=="0" and p.get("ActiveState") in ("inactive","failed")
 def reset_eligible(self,r,u):return self._p(r).get("ActiveState")=="failed"
 def inventory(self,r):return {"root":r,"entries":sorted(os.path.relpath(os.path.join(d,f),r) for d,_,fs in os.walk(r) for f in fs)}
 def post_compile_checks(self,r):
  obj=os.path.join(r,"layer_b_native_owner_v1.o")
  if not os.path.isfile(obj): return False
  for tool,args in (("/usr/bin/readelf",("-h","-S",obj)),("/usr/bin/objdump",("-h",obj))):
   if not _ok(self.run((tool,)+args,3)): return False
  return b"ET_REL" in subprocess.run(("/usr/bin/readelf","-h",obj),capture_output=True,check=False).stdout

class Root13Runner:
 def __init__(self,backend,*,root=ROOT,nonce=None,observer=None):
  self.b=backend;self.root=root;self.nonce=nonce or str(backend.uuid());self.unit=unit_name(self.nonce);self.observer=observer;self.r=Result();self.fifo=root+"/logs/identity.fifo";self.token=root+"/logs/identity.token";self.t0=time.monotonic();self.ack_deadline=self.t0+90
 def _record(self,a,x):self.r.commands.append({"argv":list(a),"response":dict(x)});self.b.fsync_record(self.r.commands[-1]);return x
 def _cmd(self,a,t=3):
  if time.monotonic()+t>self.ack_deadline and self.r.state in (State.PRE_ACK,State.WRITER,State.POST_ACK):raise TimeoutError("ack deadline")
  return self._record(a,self.b.run(tuple(a),t))
 def _fail(self,x):self.r.fail(x);self.r.state=State.CLEANUP;self.b.fsync_record({"first_failure":self.r.first_failure})
 def run(self):
  try:
   paths=[self.root+"/layer_b_native_owner_v1."+x for x in ("i","s","o","d")]+[self.fifo,self.token]
   if self.b.exists(self.root) or self.b.unit_exists(self.unit):return self._early("stale root or unit")
   if any(self.b.exists(p) for p in paths):return self._early("pre-existing output")
   if not self.b.authenticate(TOOL_PATHS,INCLUDES,SOURCE,SOURCE_SHA256,OBSERVER_SHA256,TEST_SHA256,PACKET24_SHA256):return self._early("pin authentication failed")
   self.b.mkdir_tree(self.root,("home","tmp","logs"),0o700);self.b.mkfifo(self.fifo,0o600);self.b.write_token(self.token,b"A",0o600)
   self.r.state=State.SUBMIT_ONCE;s=self._cmd(submission_argv(self.root,self.unit),11)
   if not _ok(s):self._fail("submission failure or timeout")
   else:
    self.r.state=State.PRE_ACK;p=self._cmd(self.b.show_argv(self.unit),2)
    if not _ok(p) or not self.b.valid_pre_ack(p,self.unit) or (self.observer and not self.observer(p)):self._fail("pre-ack observation rejected")
    else:
     self._cmd(self.b.sync_argv(self.root+"/logs"),2);q=self._cmd(self.b.show_argv(self.unit),2)
     if not _ok(q) or not self.b.valid_pre_ack(q,self.unit):self._fail("pre-ack tuple changed")
     else:
      self.r.state=State.WRITER;self.r.writer_started=True;w=self._cmd(self.b.writer_argv(self.token,self.fifo),2)
      if not _ok(w):self._fail("writer failure or timeout")
      else:
       self.r.state=State.POST_ACK;z=self._cmd(self.b.show_argv(self.unit),2)
       if not _ok(z) or not self.b.valid_success(z,self.unit):self._fail("compile or terminal predicate failed")
  except Exception as e:self._fail(type(e).__name__+": "+str(e))
  self.r.state=State.CLEANUP;self._cleanup()
  if not self.r.first_failure and hasattr(self.b,"post_compile_checks"):
   try:
    if not self.b.post_compile_checks(self.root): self.r.fail("artifact/compiler/ET_REL checks failed")
   except Exception as e:self.r.fail("artifact checks: "+str(e))
  self.r.state=State.EVIDENCE
  try:self.r.evidence["journal"]=self._record(self.b.journal_argv(self.unit),self.b.run(self.b.journal_argv(self.unit),6));self.r.evidence["inventory"]=self.b.inventory(self.root)
  except Exception as e:self.r.cleanup_errors.append("journal: "+str(e))
  self.r.state=State.TERMINAL;self.r.terminal="FAIL_UNRESOLVED" if self.r.first_failure=="FAIL_UNRESOLVED" else ("FAIL" if self.r.first_failure else "PASS_COMPILE_ONLY");return self.r
 def _early(self,x):self.r.fail(x);self.r.state=State.TERMINAL;self.r.terminal="FAIL";return self.r
 def _cleanup(self):
  try:
   if self.r.first_failure:self._cmd(self.b.show_argv(self.unit),2)
   stop=self._cmd(self.b.stop_argv(self.unit),5)
   if not _ok(stop):
    self.r.cleanup_errors.append("stop failed");self.r.killed=True;kill=self._cmd(self.b.kill_argv(self.unit),3)
    if not _ok(kill):self.r.cleanup_errors.append("KILL failed")
   final=self._cmd(self.b.show_argv(self.unit),2)
   if not _ok(final) or not self.b.resolved(final,self.unit):self.r.fail("FAIL_UNRESOLVED")
   elif self.b.reset_eligible(final,self.unit):self._cmd(self.b.reset_argv(self.unit),3)
  except Exception as e:self.r.cleanup_errors.append(type(e).__name__+": "+str(e));self.r.fail("FAIL_UNRESOLVED")

def main(argv:Sequence[str]|None=None):
 p=argparse.ArgumentParser();p.add_argument("--execute",action="store_true");p.add_argument("--packet-sha256",required=True);a=p.parse_args(argv)
 if not a.execute: raise SystemExit("--execute is required")
 actual=hashlib.sha256(open(PACKET,"rb").read()).hexdigest()
 if a.packet_sha256!=actual: raise SystemExit("packet hash mismatch")
 return 0 if Root13Runner(LocalBackend()).run().terminal=="PASS_COMPILE_ONLY" else 1
if __name__=="__main__":raise SystemExit(main())
