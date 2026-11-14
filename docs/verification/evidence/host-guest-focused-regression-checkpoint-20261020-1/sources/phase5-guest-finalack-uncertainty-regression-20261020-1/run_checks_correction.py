from pathlib import Path
import os,resource,subprocess,json,time,signal,hashlib
P=Path(__file__).resolve().parent
COMP=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
assert (P/'ROOT-CORRECTION-ADMISSION.json').exists(),'dispatcher admission required'
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());usage=state.get('last_rate_limits',{}).get('primary',{}).get('usedPercent')
assert state.get('phase')=='running' and not state.get('pause_reason') and isinstance(usage,(int,float)) and usage<100
for path,floor in [('/home/holden',16*2**30),('/home/holden/mckernel-work/scratch',12*2**30)]:
 v=os.statvfs(path);assert v.f_bavail*v.f_frsize>=floor+64*2**20
assert not (P/'check-2').exists();C=P/'check-2';C.mkdir()
def limits():
 os.sched_setaffinity(0,{6});resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256));resource.setrlimit(resource.RLIMIT_AS,(1073741824,1073741824));resource.setrlimit(resource.RLIMIT_CPU,(30,30));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432))
def run(name,args):
 D=C/name;D.mkdir();(D/'command.json').write_text(json.dumps(args)+'\n');start=time.monotonic()
 with (D/'stdout').open('wb')as out,(D/'stderr').open('wb')as err:
  p=subprocess.Popen(args,cwd=P,stdout=out,stderr=err,preexec_fn=limits,start_new_session=True)
  (D/'started.json').write_text(json.dumps({'pid':p.pid,'start':start})+'\n')
  try:rc=p.wait(timeout=35)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGTERM)
   try:rc=p.wait(timeout=2)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);rc=p.wait()
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 (D/'status.json').write_text(json.dumps({'pid':p.pid,'exit_code':rc,'positive_wait':True,'owned_group_absent':absent,'elapsed':time.monotonic()-start})+'\n')
 assert absent
 return rc
argv=[str(COMP),'--edition=2021','--test','-C','codegen-units=1','-C','debuginfo=0','-C','linker=/usr/bin/cc',str(P/'fixture/actual-finalack.rs'),'-o',str(C/'actual')]
rc=run('compile',argv)
if rc==0:rc=run('test',[str(C/'actual'),'finalack_uncertainty_','--test-threads=1','--nocapture'])
print(json.dumps({'exit_code':rc,'evidence':str(C)}))
