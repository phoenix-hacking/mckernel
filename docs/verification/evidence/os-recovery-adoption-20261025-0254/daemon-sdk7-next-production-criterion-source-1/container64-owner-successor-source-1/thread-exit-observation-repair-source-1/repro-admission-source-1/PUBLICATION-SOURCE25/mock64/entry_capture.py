"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact new owner via unchanged h990; requires existing actual Root/reviewer release.
"""
from pathlib import Path
import hashlib,json,os,resource,time,types
import repro_contract as mc
import repro_owner as owner
A=Path(__file__).resolve().parent

def main():
 mc.need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000,'ordinary UID1000 caller')
 request=A/'REPRO-REQUEST.json';release=A/'ACTUAL-REVIEWED-RELEASE.json';rr=mc.ref(request);er=mc.ref(release)
 req,approval=owner.authenticate(request,rr['sha256'],release,er['sha256'])
 C=A/'OWNER-CAPTURE';mc.need(C.is_dir() and not list(C.iterdir()),'prepared empty owner capture required')
 argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(mc.OWNER),'--request',str(request),'--request-sha256',rr['sha256'],'--release',str(release),'--release-sha256',er['sha256']]
 helper=Path(mc.PREP['capture_helper']['path']);raw=helper.read_bytes();mc.need(mc.sha(raw)==mc.PREP['capture_helper']['sha256'],'exact h990 outer capture')
 module=types.ModuleType('existing_mock64_owner_capture');module.__file__=str(helper);exec(compile(raw,str(helper),'exec'),module.__dict__)
 timeout=req['timeout']+120;mc.need(time.time()+timeout+300<mc.CUTOFFS[0],'fixed end margin before entry')
 def limits():
  os.sched_setaffinity(0,{2,3,4,5});resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(64<<20,64<<20))
 command=dict(argv=argv,scope=__doc__.splitlines()[0]);(A/'OWNER-COMMAND.EXACT.json').write_bytes(mc.canonical(command));started=time.time()
 result=module.owned_capture(command,C,timeout,limits);result.update(started_wall=started,finished_wall=time.time(),capture_helper_sha256=mc.PREP['capture_helper']['sha256'])
 with (A/'OWNER-WHOLE-JOIN.json').open('xb') as f:f.write(mc.canonical(result))
 print(json.dumps({k:result[k] for k in ['pid','returncode','direct_child_joined','group_absent','closed_streams','error','retirement_error','timed_out','seconds']}),flush=True)
 return 0 if mc.capture_ok(result) else 1
if __name__=='__main__':raise SystemExit(main())
