"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Supervise only the two reviewed synthetic fixtures or evidence normalization.
"""
import ast,datetime,hashlib,json,os,resource,signal,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;PYTHON=Path('/home/holden/anaconda3/bin/python3.9')
BASE=D.parent
MATCH=BASE.parent/'MANUAL-RESUME-M14-20261030-2/perf-counter-runner-successor-1/serial_supervised.py'
CONVERTER=BASE/'sdk21-nonheld13-ledger-converter-source-1/sdk13_data32_ledger_converter.py'
VALIDATOR=BASE/'sdk21-nonheld13-input-validation-source-1/test_sdk13_data32_input_validation.py'
SNAPSHOT=BASE/'sdk21-nonheld13-input-validation-source-1/test_sdk13_data32_input_snapshot.py'
WORKER=D/'normalize_evidence_only.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def proc(pid):
 s=Path('/proc/%s/stat'%pid).read_text().rsplit(')',1)[1].split()
 return {'pid':pid,'state':s[0],'ppid':int(s[1]),'pgid':int(s[2]),'sid':int(s[3]),'start_ticks':int(s[19])}
def save(name,obj):
 with (out/name).open('x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
if len(sys.argv)!=2 or sys.argv[1] not in ('validator','snapshot','converter'):raise ValueError('unknown exact operation')
mode=sys.argv[1]
assert sha(MATCH)=='7d8e744c755b37213abb81e9ce8b2220edc2b982fdfcbd9b61b3b45815e1dbfd'
assert sha(PYTHON)=='8f122d7bdf820e716491d2be6c3b9f2b85f5fa46b34811e29432fa7cd8fd41fb'
assert sha(CONVERTER)=='36280257a6faf3d2ce99b3c018f16bca092d1ed124838ab99dda2edf94cefe3f'
assert sha(VALIDATOR)=='0241619c42dd0858950fe3a1e5dfd6dcc386c7959c57b33fccacad5c37019a3a'
assert sha(SNAPSHOT)=='73643532ec27a5275d8c74aea1eaa48c233fd542382a9e4a98e70946d5530527'
assert os.sched_getaffinity(0)=={0}
for kind,value in ((resource.RLIMIT_AS,536870912),(resource.RLIMIT_CPU,20),(resource.RLIMIT_NOFILE,128),(resource.RLIMIT_FSIZE,16777216),(resource.RLIMIT_CORE,0)):
 assert resource.getrlimit(kind)==(value,value)
nodes=[n for n in ast.parse(MATCH.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('census','leader_state')]
assert {n.name for n in nodes}=={'census','leader_state'}
space={'Path':Path,'os':os};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(MATCH),'exec'),space)
out=D/mode;out.mkdir(mode=0o700);tmp=out/'tmp';tmp.mkdir(mode=0o700)
target={'validator':VALIDATOR,'snapshot':SNAPSHOT,'converter':WORKER}[mode]
child_argv=[str(PYTHON),'-I','-B',str(target)]
owner_argv=['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=536870912:536870912','--cpu=20:20','--nofile=128:128','--fsize=16777216:16777216','--core=0:0','--',str(PYTHON),'-I','-B',str(Path(__file__).resolve()),mode]
env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','PYTHONNOUSERSITE':'1','TMPDIR':str(tmp)}
save('argv.json',{'owner_argv':owner_argv,'child_argv':child_argv,'child_environment':env,'supervisor':{'path':str(Path(__file__).resolve()),'sha256':sha(Path(__file__))},'worker':{'path':str(WORKER),'sha256':sha(WORKER)},'converter':{'path':str(CONVERTER),'sha256':sha(CONVERTER)},'validator_fixture':{'path':str(VALIDATOR),'sha256':sha(VALIDATOR)},'snapshot_fixture':{'path':str(SNAPSHOT),'sha256':sha(SNAPSHOT)},'matcher':{'path':str(MATCH),'sha256':sha(MATCH)},'python':{'path':str(PYTHON),'sha256':sha(PYTHON)},'taskset_sha256':sha(Path('/usr/bin/taskset')),'prlimit_sha256':sha(Path('/usr/bin/prlimit')),'limits':'CPU0; AS512MiB; CPU20; nofile128; fsize16MiB; core0; wall30 TERM+5 KILL'})
grant_path=BASE/'ORDINARY-CPU0-PURE-GRANT-20261030T0724.ACTUAL.json'
grant_raw=grant_path.read_bytes()
if hashlib.sha256(grant_raw).hexdigest()!='381afc9819ea7a453717b644532fa110fe78bc06981fdd140bfe26792b843043':raise RuntimeError('grant hash changed')
grant=json.loads(grant_raw)
quota=Path('/home/holden/mckernel/.git/os-autopilot/runs/20261030T041353Z-1e1aeda1/weekly-quota-observations.jsonl')
with quota.open('rb') as f:
 f.seek(0,2);size=f.tell();f.seek(max(0,size-262144));lines=f.read().splitlines()
observed=None
for line in reversed(lines):
 try:row=json.loads(line)
 except (ValueError,UnicodeDecodeError):continue
 if row.get('thread_id')==grant['thread'] and row.get('source')=='notification' and row.get('limits',{}).get('primary'):
  observed=row;break
if observed is None:raise RuntimeError('fresh primary usage unavailable')
now=time.time();boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic()
observed_at=datetime.datetime.fromisoformat(observed['at']).timestamp();weekly=observed['limits']['primary']
if not (0<=now-observed_at<=30 and weekly['usedPercent']<100 and weekly['resetsAt']==1793774133 and now<grant['expires_at'] and now<1793774133 and boot<1571569.6959267766 and mono<1556231.5688797957):raise RuntimeError('usage or deadline not current')
controls=[]
for item in grant['controls']:
 actual=proc(item['pid'])
 if str(actual['start_ticks'])!=item['birth'] or actual['state'] in ('Z','X'):raise RuntimeError('controller is not live')
 controls.append(actual)
markers={name:Path(name).exists() for name in grant['markers']}
if any(markers.values()):raise RuntimeError('stop or hold marker exists')
save('pre-spawn-check.json',{'grant':{'path':str(grant_path),'sha256':'381afc9819ea7a453717b644532fa110fe78bc06981fdd140bfe26792b843043'},'at':now,'boot':boot,'monotonic':mono,'weekly':weekly,'weekly_observed_at':observed['at'],'weekly_source':'notification','controllers':controls,'markers':markers})
ready_r,ready_w=os.pipe();gate_r,gate_w=os.pipe();stdout=(out/'stdout').open('xb');stderr=(out/'stderr').open('xb');start=time.monotonic();pid=os.fork()
if pid==0:
 try:
  os.close(ready_r);os.close(gate_w);os.setsid();os.write(ready_w,b'R');os.close(ready_w)
  if os.read(gate_r,1)!=b'G':os._exit(121)
  os.close(gate_r);os.dup2(stdout.fileno(),1);os.dup2(stderr.fileno(),2)
  os.chdir(D);os.execve(str(PYTHON),child_argv,env)
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
save('supervisor-result.json',result);print(json.dumps(result));sys.exit(0 if code==0 and closed and not term and not kill else 1)
