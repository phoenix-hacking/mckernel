#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Own one fixed source pass and use retained census; no native/SDK/compiler work.
"""
import ast,hashlib,json,os,resource,signal,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent; OUT=D/'results'; WORKER=D/'validate_fixed_source.py'
MATCH=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/MANUAL-RESUME-M14-20261030-2/perf-counter-runner-successor-1/serial_supervised.py')
PYTHON=Path('/home/holden/anaconda3/bin/python3.9')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,value):
 with (OUT/name).open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def proc(pid):
 s=Path('/proc/%s/stat'%pid).read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'state':s[0],'ppid':int(s[1]),'pgid':int(s[2]),'sid':int(s[3]),'start_ticks':int(s[19])}
assert sha(MATCH)=='7d8e744c755b37213abb81e9ce8b2220edc2b982fdfcbd9b61b3b45815e1dbfd'
assert sha(PYTHON)=='8f122d7bdf820e716491d2be6c3b9f2b85f5fa46b34811e29432fa7cd8fd41fb'
assert os.sched_getaffinity(0)=={0}
assert resource.getrlimit(resource.RLIMIT_AS)==(536870912,536870912)
assert resource.getrlimit(resource.RLIMIT_CPU)==(45,45)
assert resource.getrlimit(resource.RLIMIT_NOFILE)==(128,128)
assert resource.getrlimit(resource.RLIMIT_FSIZE)==(16777216,16777216)
assert resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
raw=MATCH.read_text(); tree=ast.parse(raw); nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('census','leader_state')]
assert {n.name for n in nodes}=={'census','leader_state'}
space={'Path':Path,'os':os};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(MATCH),'exec'),space)
OUT.mkdir(mode=0o700)
argv=[str(PYTHON),'-I','-B',str(WORKER)]
owner_argv=['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=536870912:536870912','--cpu=45:45','--nofile=128:128','--fsize=16777216:16777216','--core=0:0','--',str(PYTHON),'-I','-B',str(Path(__file__).resolve())]
save('argv.json',{'scope':__doc__.splitlines()[0],'owner_argv':owner_argv,'worker_argv':argv,'cwd':os.getcwd(),
 'supervisor':{'path':str(Path(__file__).resolve()),'sha256':sha(Path(__file__))},'worker':{'path':str(WORKER),'sha256':sha(WORKER)},
 'matcher':{'path':str(MATCH),'sha256':sha(MATCH)},'python':{'path':str(PYTHON),'sha256':sha(PYTHON)},
 'taskset_sha256':sha('/usr/bin/taskset'),'prlimit_sha256':sha('/usr/bin/prlimit'),
 'limits':'CPU0; AS512MiB; CPU45s; nofile128; fsize16MiB; core0; monotonic wall60s TERM then 5s KILL','nightly_rehashed':False})
ready_r,ready_w=os.pipe();gate_r,gate_w=os.pipe();stdout=(OUT/'worker.stdout').open('xb');stderr=(OUT/'worker.stderr').open('xb');started=time.monotonic();pid=os.fork()
if pid==0:
 try:
  os.close(ready_r);os.close(gate_w);os.setsid();os.write(ready_w,b'R');os.close(ready_w)
  if os.read(gate_r,1)!=b'G':os._exit(121)
  os.close(gate_r);os.dup2(stdout.fileno(),1);os.dup2(stderr.fileno(),2)
  os.chdir(D);os.execve(str(PYTHON),argv,{'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
 except BaseException:os._exit(122)
os.close(ready_w);os.close(gate_r);stdout.close();stderr.close()
if os.read(ready_r,1)!=b'R':raise RuntimeError('worker did not establish group')
os.close(ready_r);leader=proc(pid)
if leader['ppid']!=os.getpid() or leader['pgid']!=pid or leader['sid']!=pid:raise RuntimeError('worker identity mismatch')
save('started.json',{'supervisor':proc(os.getpid()),'worker':leader,'affinity':sorted(os.sched_getaffinity(0))})
os.write(gate_w,b'G');os.close(gate_w)
term=False;hard=False
while space['leader_state'](pid) is None:
 elapsed=time.monotonic()-started
 if elapsed>=60 and not term:
  x=proc(pid)
  if (x['start_ticks'],x['pgid'],x['sid'])!=(leader['start_ticks'],pid,pid):raise RuntimeError('worker group anchor changed')
  os.killpg(pid,signal.SIGTERM);term=True
 if elapsed>=65 and not hard:
  x=proc(pid)
  if (x['start_ticks'],x['pgid'],x['sid'])!=(leader['start_ticks'],pid,pid):raise RuntimeError('worker group anchor changed')
  os.killpg(pid,signal.SIGKILL);hard=True
 time.sleep(0.02)
try:
 members=space['census'](pid);anchors=[s for s in members if s['pid']==pid];extra=[s for s in members if s['pid']!=pid]
 closed=len(anchors)==1 and anchors[0]['state']=='Z' and anchors[0]['start_ticks']==leader['start_ticks'] and not extra
 census={'members':members,'closed_before_reap':closed,'error':None}
except BaseException as error:census={'members':None,'closed_before_reap':False,'error':repr(error)}
save('postterminal-census.json',census)
waited,status,usage=os.wait4(pid,0);code=os.waitstatus_to_exitcode(status);self_usage=resource.getrusage(resource.RUSAGE_SELF)
result={'scope':__doc__.splitlines()[0],'pid':waited,'start_ticks':leader['start_ticks'],'pgid':pid,'sid':pid,'exit_code':code,
 'wall_seconds':time.monotonic()-started,'user_seconds':usage.ru_utime,'system_seconds':usage.ru_stime,'max_rss_kib':usage.ru_maxrss,
 'supervisor_user_seconds':self_usage.ru_utime,'supervisor_system_seconds':self_usage.ru_stime,'supervisor_max_rss_kib':self_usage.ru_maxrss,
 'timeout_term':term,'timeout_kill':hard,'postterminal_group_closed_before_reap':census['closed_before_reap'],'native_ownership_clearance':False}
try:
 worker_result=json.loads((OUT/'SOURCE-CURRENT-RESULT.json').read_text());result['worker_status']=worker_result['status'];result['files']=worker_result['files'];result['symlinks']=worker_result['symlinks'];result['file_bytes']=worker_result['file_bytes'];result['first_failure']=worker_result['first_failure']
except Exception as exc:result['worker_result_error']=repr(exc)
save('supervisor-result.json',result)
if code==0 and census['closed_before_reap'] and not term and not hard and result.get('worker_status')=='PASS_FIXED_RETAINED_ENTRIES_ONLY':
 snapshot={'scope':__doc__.splitlines()[0],'status':'POINT_IN_TIME_FIXED_SOURCE_OBSERVATION_NOT_REVIEW_OR_RELEASE',
  'prior_map':{'path':str(D.parent/'SDK13-SOURCE-MAP.PROPOSED.json'),'sha256':sha(D.parent/'SDK13-SOURCE-MAP.PROPOSED.json')},
  'prior_nightly_identity_ledger':{'path':str(D.parent/'POINT-IN-TIME-IDENTITIES.json'),'sha256':sha(D.parent/'POINT-IN-TIME-IDENTITIES.json'),'resource_metrics':'UNKNOWN_FROM_EARLIER_PASS_NOT_REHASHED'},
  'source_identities':{'path':str(OUT/'SOURCE6153-IDENTITIES.jsonl'),'sha256':sha(OUT/'SOURCE6153-IDENTITIES.jsonl'),'files':result['files'],'symlinks':result['symlinks'],'file_bytes':result['file_bytes']},
  'worker_result':{'path':str(OUT/'SOURCE-CURRENT-RESULT.json'),'sha256':sha(OUT/'SOURCE-CURRENT-RESULT.json')},
  'group_closure':{'path':str(OUT/'postterminal-census.json'),'sha256':sha(OUT/'postterminal-census.json')},
  'supervisor_result':{'path':str(OUT/'supervisor-result.json'),'sha256':sha(OUT/'supervisor-result.json')},
  'extra_file_inventory_performed':False,'nightly_rehashed':False,'authority':None,'independent_review':None}
 save('COMPLETED-SOURCE-SNAPSHOT.PROPOSED.json',snapshot)
 print(json.dumps(result));sys.exit(0)
print(json.dumps(result));sys.exit(1)
