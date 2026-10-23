"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,time
E=Path(__file__).resolve().parent
D=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-5/default-image-successor-1/release-assembly-1/final-build-facts-preparation-1')
R=Path('/home/holden/mckernel')
def write(p,v):
 with p.open('x') as f:json.dump(v,f,sort_keys=True,indent=2);f.write('\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 start=time.monotonic();os.sched_setaffinity(0,{6})
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 helper=R/'docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py';assert sha(helper)=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8';nodes=[]
 for node in ast.parse(helper.read_bytes()).body:
  if isinstance(node,(ast.Import,ast.ImportFrom)):nodes.append(node)
  elif isinstance(node,ast.FunctionDef) and node.name in {'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}:nodes.append(node)
  elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'} for t in node.targets):nodes.append(node)
 ns={'__file__':str(helper)};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),ns)
 for signum in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(signum,ns['stop'])
 signal.setitimer(signal.ITIMER_REAL,60)
 prepared=json.loads((E/'PREPARED-THREE-READONLY.json').read_text());results=[];error=None
 try:
  for i,cmd in enumerate(prepared['commands'],1):
   assert not any(x in cmd['argv'] for x in ('/usr/bin/sudo','/usr/sbin/losetup'))
   cap=D/str(i);cap.mkdir(mode=0o700);write(cap/'command.json',cmd)
   j=ns['owned_capture'](cmd,cap,max(1,54-(time.monotonic()-start)),lambda:None);write(cap/'whole-join.json',j);results.append(j)
   assert j['returncode']==0 and j['direct_child_joined'] and j['group_absent'] and j['closed_streams'] and not j['error'] and not j['retirement_error'],'first readonly failure '+str(i)
 except BaseException as exc:error=repr(exc)
 result=dict(scope=__doc__,status='PASS_THREE_AUTHORIZED_UNPRIVILEGED_READONLY_FACTS' if error is None else 'FAIL_FIRST_READONLY_RETAINED',error=error,results=results,seconds=time.monotonic()-start,combined_cpu_seconds=ns['cpu_used'](),root_Docker_compiler_guest=0)
 write(D/'ACTUAL-THREE-READONLY-RESULT.json',result)
 for p in [D/'ACTUAL-THREE-READONLY-RESULT.json']+[q for i in range(1,len(results)+1) for q in (D/str(i)).iterdir()]:
  target=E/p.relative_to(D);target.parent.mkdir(exist_ok=True)
  with target.open('xb') as f:f.write(p.read_bytes())
 signal.setitimer(signal.ITIMER_REAL,0);print(json.dumps(dict(status=result['status'],error=error,commands=len(results),seconds=result['seconds'])))
if __name__=='__main__':main()
