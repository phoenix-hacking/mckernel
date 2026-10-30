"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Supervise the one fixed observation or the separately admitted pure fixture.
"""
import ast,hashlib,json,os,resource,signal,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;PYTHON=Path('/home/holden/anaconda3/bin/python3.9')
BASE=D.parent.parent
MATCH=BASE.parent/'MANUAL-RESUME-M14-20261030-2/perf-counter-runner-successor-1/serial_supervised.py'
CONVERTER=BASE/'sdk21-nonheld13-ledger-converter-source-1/sdk13_ledger_converter.py'
FIXTURE=CONVERTER.parent/'test_sdk13_ledger_converter.py'
WORKER=D/'observe_rust157.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def proc(pid):
 s=Path('/proc/%s/stat'%pid).read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'state':s[0],'ppid':int(s[1]),'pgid':int(s[2]),'sid':int(s[3]),'start_ticks':int(s[19])}
def save(name,obj):
 with (out/name).open('x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
if len(sys.argv)!=2 or sys.argv[1] not in ('receipt','fixture'):raise ValueError('receipt or fixture required')
mode=sys.argv[1]
assert sha(MATCH)=='7d8e744c755b37213abb81e9ce8b2220edc2b982fdfcbd9b61b3b45815e1dbfd'
assert sha(PYTHON)=='8f122d7bdf820e716491d2be6c3b9f2b85f5fa46b34811e29432fa7cd8fd41fb'
assert sha(CONVERTER)=='0493933dc0e8f1f24e28db5bdba52d20e5595cc7c0055a3f3534b0ff54852b16'
assert sha(FIXTURE)=='078f4ec1398080128a05001df2a859cb3d8cd6d78241404434f7ca020a28bae6'
assert os.sched_getaffinity(0)=={0}
for kind,value in ((resource.RLIMIT_AS,536870912),(resource.RLIMIT_CPU,20),(resource.RLIMIT_NOFILE,128),(resource.RLIMIT_FSIZE,16777216),(resource.RLIMIT_CORE,0)):
 assert resource.getrlimit(kind)==(value,value)
nodes=[n for n in ast.parse(MATCH.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('census','leader_state')]
assert {n.name for n in nodes}=={'census','leader_state'}
space={'Path':Path,'os':os};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(MATCH),'exec'),space)
out=D/('receipt-run' if mode=='receipt' else 'fixture-run');out.mkdir(mode=0o700)
child_argv=[str(PYTHON),'-I','-B',str(WORKER)] if mode=='receipt' else [str(PYTHON),'-B',str(FIXTURE)]
owner_argv=['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=536870912:536870912','--cpu=20:20','--nofile=128:128','--fsize=16777216:16777216','--core=0:0','--',str(PYTHON),'-I','-B',str(Path(__file__).resolve()),mode]
env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','PYTHONNOUSERSITE':'1'}
save('argv.json',{'owner_argv':owner_argv,'child_argv':child_argv,'child_environment':env,'supervisor':{'path':str(Path(__file__).resolve()),'sha256':sha(Path(__file__))},'worker':{'path':str(WORKER),'sha256':sha(WORKER)},'converter':{'path':str(CONVERTER),'sha256':sha(CONVERTER)},'fixture':{'path':str(FIXTURE),'sha256':sha(FIXTURE)},'matcher':{'path':str(MATCH),'sha256':sha(MATCH)},'python':{'path':str(PYTHON),'sha256':sha(PYTHON)},'taskset_sha256':sha(Path('/usr/bin/taskset')),'prlimit_sha256':sha(Path('/usr/bin/prlimit')),'limits':'CPU0; AS512MiB; CPU20; nofile128; fsize16MiB; core0; wall30 TERM+5 KILL'})
ready_r,ready_w=os.pipe();gate_r,gate_w=os.pipe();stdout=(out/'stdout').open('xb');stderr=(out/'stderr').open('xb');start=time.monotonic();pid=os.fork()
if pid==0:
 try:
  os.close(ready_r);os.close(gate_w);os.setsid();os.write(ready_w,b'R');os.close(ready_w)
  if os.read(gate_r,1)!=b'G':os._exit(121)
  os.close(gate_r);os.dup2(stdout.fileno(),1);os.dup2(stderr.fileno(),2)
  os.chdir(D if mode=='receipt' else FIXTURE.parent);os.execve(str(PYTHON),child_argv,env)
 except BaseException:os._exit(122)
os.close(ready_w);os.close(gate_r);stdout.close();stderr.close()
if os.read(ready_r,1)!=b'R':raise RuntimeError('child did not establish group')
os.close(ready_r);leader=proc(pid)
if leader['ppid']!=os.getpid() or leader['pgid']!=pid or leader['sid']!=pid:raise RuntimeError('group identity mismatch')
save('started.json',{'supervisor':proc(os.getpid()),'child':leader,'affinity':sorted(os.sched_getaffinity(0))})
os.write(gate_w,b'G');os.close(gate_w);term=False;kill=False
while space['leader_state'](pid) is None:
 elapsed=time.monotonic()-start
 if (elapsed>=30 and not term) or (elapsed>=35 and not kill):
  x=proc(pid)
  if (x['start_ticks'],x['pgid'],x['sid'])!=(leader['start_ticks'],pid,pid):raise RuntimeError('group anchor changed')
  if elapsed>=35:os.killpg(pid,signal.SIGKILL);kill=True
  else:os.killpg(pid,signal.SIGTERM);term=True
 time.sleep(.02)
try:
 members=space['census'](pid);anchors=[x for x in members if x['pid']==pid];other=[x for x in members if x['pid']!=pid]
 closed=len(anchors)==1 and anchors[0]['state']=='Z' and anchors[0]['start_ticks']==leader['start_ticks'] and not other
 census={'members':members,'closed_before_reap':closed,'error':None}
except BaseException as exc:census={'members':None,'closed_before_reap':False,'error':repr(exc)}
save('postterminal-census.json',census)
waited,status,usage=os.wait4(pid,0);selfuse=resource.getrusage(resource.RUSAGE_SELF);code=os.waitstatus_to_exitcode(status)
result={'mode':mode,'pid':waited,'birth':leader['start_ticks'],'pgid':pid,'sid':pid,'exit_code':code,'wall_seconds':time.monotonic()-start,'user_seconds':usage.ru_utime,'system_seconds':usage.ru_stime,'max_rss_kib':usage.ru_maxrss,'supervisor_user_seconds':selfuse.ru_utime,'supervisor_system_seconds':selfuse.ru_stime,'supervisor_max_rss_kib':selfuse.ru_maxrss,'timeout_term':term,'timeout_kill':kill,'closed_before_reap':census['closed_before_reap']}
if mode=='receipt':
 try:result['worker_result']=json.loads((out/'worker-result.json').read_text())
 except Exception as exc:result['worker_result_error']=repr(exc)
save('supervisor-result.json',result);print(json.dumps(result));sys.exit(0 if code==0 and closed and not term and not kill else 1)
