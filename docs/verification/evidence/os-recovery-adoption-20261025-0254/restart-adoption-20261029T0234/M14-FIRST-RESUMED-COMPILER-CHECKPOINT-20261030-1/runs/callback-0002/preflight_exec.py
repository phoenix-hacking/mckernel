"""One granted functional-OS synthetic test; no security testing."""
import datetime,hashlib,json,os,stat,sys,time
from pathlib import Path
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1')
O=D/'source-test-runs/callback-0002';S=D/'child-callback-expert-1'
Q=Path('/home/holden/mckernel/.git/os-autopilot/runs/20261030T175456Z-0e492844/weekly-quota-observations.jsonl')
STATE=Path('/home/holden/mckernel/.git/os-autopilot/state.json')

def need(ok,msg):
 if not ok:raise ValueError(msg)
def h(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def publish(name,obj):
 raw=(json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();fd=os.open(str(O/name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
 try:
  i=0
  while i<len(raw):
   n=os.write(fd,raw[i:]);need(n>0,'short receipt write');i+=n
  os.fsync(fd)
 finally:os.close(fd)
 parent=os.open(str(O),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
 try:os.fsync(parent)
 finally:os.close(parent)
def main():
 manifest=S/'SOURCE-MANIFEST.json';need(h(manifest)=='dc95927633174fcd5e17151da8b67688bbd9908e1a3fcd88331b4b4d64d2e72c','manifest drift')
 doc=json.loads(manifest.read_bytes());need(len(doc['files'])==16 and doc['files']['test_callback_handoff.py']=='c529a06971df496c733ae9c5dc5662f1a71f7e40cd2ffa1bf547823406434859','selection')
 refs={}
 for name,sha in doc['files'].items():
  path=S/name;st=path.lstat();need(stat.S_ISREG(st.st_mode) and st.st_nlink==1 and h(path)==sha,'source '+name);refs[name]=sha
 graph=D/'adapter-readiness-expert-1/graph_observations.py';need(h(graph)=='a0c5c4d0222fac7906a1591449efefab36d9f97a076a9cc47c913de06614ea1b','graph drift')
 a=json.loads((D/'ACTUAL-CONTROLS-ARMED.json').read_bytes());b=json.loads((D/'ACTUAL-CAPACITY-FALLBACK-ARMED.json').read_bytes())
 need(a['binding']==b['binding'] and a['caps']==b['caps'] and a['thread_id']==b['thread_id']=='01a18bc3-e072-7810-9426-75101b0856c0','controls')
 need(b['billing_mode']=='included_only' and b['status']=='PASS_ACTUAL_MANUAL_SAME_ROOT_RESUME' and b['same_thread'] is True and b['generic_c_request_still_held'] is True and a['native_release'] is False and b['native_release'] is False,'billing and holds')
 cap=a['caps'];need(cap['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip() and cap['deadline']==1793774133 and cap['boot_deadline']<=1571567.6959065471 and cap['monotonic_deadline']<=1556229.568859425,'caps')
 need(time.time()<cap['deadline'] and time.clock_gettime(time.CLOCK_BOOTTIME)<cap['boot_deadline'] and time.monotonic()<cap['monotonic_deadline'],'clock expired')
 actors={}
 for role,row in list(a['binding'].items())+[('capacity',b['supervisor'])]:
  fields=Path('/proc/%d/stat'%row['pid']).read_text().rsplit(')',1)[1].split()
  need(fields[19]==row['start'] and int(fields[1])==row['ppid'] and fields[0] not in ('Z','X','x'),'actor '+role)
  actors[role]={'pid':row['pid'],'start':row['start'],'state':fields[0]}
 wall_before=time.time();boot_before=time.clock_gettime(time.CLOCK_BOOTTIME)
 guardian=json.loads((D/'armed-controller/journal.json').read_bytes())
 boot_after=time.clock_gettime(time.CLOCK_BOOTTIME);wall_after=time.time()
 lower=max(wall_before,1793774133+boot_before-cap['boot_deadline']);upper=max(wall_after,1793774133+boot_after-cap['boot_deadline'])
 need(guardian.get('packet_sha256')==a['guardian_packet_sha256'] and guardian.get('last_action','').startswith('WAIT_') and not guardian.get('stop_intent') and not guardian.get('transition_hold'),'guardian state')
 clock=guardian.get('last_clock');need(type(clock) in (int,float) and lower-30<=clock<=upper+2,'guardian effective clock')
 monp=D/'twenty-minute-steering/journal.json';mon=json.loads(monp.read_bytes());now=time.time()
 need(mon.get('thread_id')==a['thread_id'] and mon.get('arm_binding_sha256')==a['monitor_arm_sha256'] and mon.get('status')=='queued' and 0<=now-monp.stat().st_mtime<=45,'monitor')
 for directory in (D,D/'armed-controller',D/'twenty-minute-steering'):
  for name in ('STOP','HOLD','USER-STOP','STOP.json','HOLD.json','USER-STOP.json','stop-request.json'):
   need(not os.path.lexists(directory/name),'stop marker')
 state=json.loads(STATE.read_bytes());need(state.get('phase')=='running' and (state.get('goal') or {}).get('status')=='active' and state.get('thread_id')==a['thread_id'] and state.get('worker_pid')==a['binding']['worker']['pid'] and not state.get('stop_reason') and not state.get('transport_uncertain'),'campaign state')
 with Q.open('rb') as stream:
  stream.seek(0,2);size=stream.tell();stream.seek(max(0,size-65536));lines=stream.read().splitlines()
 need(bool(lines),'weekly guard empty');q=json.loads(lines[-1]);limits=q['limits']
 observed=datetime.datetime.fromisoformat(q['at'].replace('Z','+00:00')).timestamp();now=time.time()
 need(0<=now-observed<=60 and q.get('thread_id')==a['thread_id'] and q.get('worker_pid')==a['binding']['worker']['pid'] and str(q.get('worker_start'))==a['binding']['worker']['start'],'weekly guard freshness/identity')
 spend=limits.get('spendControlReached')
 need(limits.get('limitId')=='codex' and limits.get('rateLimitReachedType') is None and (spend is None or spend is False),'weekly guard hold')
 windows=[v for v in (limits.get('primary'),limits.get('secondary')) if isinstance(v,dict) and v.get('windowDurationMins')==10080]
 need(len(windows)==1 and windows[0].get('resetsAt')==1793774133 and type(windows[0].get('usedPercent')) in (int,float) and 0<=windows[0]['usedPercent']<100,'weekly allowance')
 need(6 in os.sched_getaffinity(0),'CPU6 unavailable')
 memory=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;need(memory>=24*2**30,'memory floor')
 free={}
 for label,path,floor in (('host','/home/holden',16*2**30),('scratch','/home/holden/mckernel-work/scratch',12*2**30)):
  v=os.statvfs(path);free[label]=v.f_bavail*v.f_frsize;need(free[label]>=floor,label+' floor')
 known={'/usr/bin/env':'5f7c7882898e9e280e93579b459e22b339c4f38cfd54a05b46b81dfb60c557cc','/usr/bin/taskset':'28f2dd426247d7d1d794c0fb8a723efc6a1ae3c56393a238b180fe9a0dc32f1c','/usr/bin/prlimit':'06a57e4767f1bdfcc8c5a39b4b58decb9366447b007a8bdd9d6b12d1e6698d8c','/usr/bin/timeout':'91db1e64064f0bf5ee99abda3a054cc6f05748dad2af5a145f890c9172d28d73','/usr/bin/time':'f3c4104d963b00e1b3a3dcf80722fea57f15f67b57a512cc30adc434b60e6e03','/usr/bin/python3.8':'298a9e830ed52f36c299427565485d717d1ce0179c0597cc16560513eb780b06'}
 tools={}
 for path,sha in known.items():
  p=Path(path);st=p.lstat();need(stat.S_ISREG(st.st_mode) and st.st_uid==0 and h(p)==sha,'tool '+path);tools[path]={'sha256':sha,'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid,'mode':st.st_mode}
 need(os.path.realpath('/usr/bin/python3')=='/usr/bin/python3.8','python alias')
 # Recheck consumed bytes, controls, clocks and the actual weekly observation age just before exec.
 for name,sha in refs.items():need(h(S/name)==sha,'source changed '+name)
 need(h(graph)=='a0c5c4d0222fac7906a1591449efefab36d9f97a076a9cc47c913de06614ea1b','graph changed')
 need(json.loads((D/'ACTUAL-CONTROLS-ARMED.json').read_bytes())==a and json.loads((D/'ACTUAL-CAPACITY-FALLBACK-ARMED.json').read_bytes())==b,'controls changed')
 need(0<=time.time()-observed<=60 and time.time()<cap['deadline'] and time.clock_gettime(time.CLOCK_BOOTTIME)<cap['boot_deadline'] and time.monotonic()<cap['monotonic_deadline'],'pre-exec freshness')
 if os.getpgrp()!=os.getpid():os.setpgid(0,0)
 need(os.getpgrp()==os.getpid(),'owner group')
 fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split();owner={'pid':os.getpid(),'ppid':os.getppid(),'start':fields[19],'state':fields[0],'pgid':os.getpgrp(),'uid':os.getuid(),'at':time.time(),'role':'tool-owned same-PID exec'}
 nonce=os.urandom(32).hex();tmp=O/'tmp';os.mkdir(tmp,0o700)
 argv=['/usr/bin/env','-i','PATH=/usr/bin:/bin','LC_ALL=C','TMPDIR='+str(tmp),'/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=536870912','--cpu=30','--core=0','--nofile=128','--','/usr/bin/timeout','--signal=TERM','--kill-after=5s','45s','/usr/bin/time','-v','-o',str(O/'time.txt'),'/usr/bin/python3','-s','-E','-S','-B','-m','unittest','-v','test_callback_handoff']
 admission={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','grant_id':'ROOT_LIGHT_TEST_CALLBACK6_2_20261030','status':'ONE_SYNTHETIC_FIXTURE_PRE_EXEC','at':time.time(),'nonce':nonce,'grant':{'cpu':[6],'jobs':1,'max_address_space_bytes':536870912,'cpu_seconds':30,'wall_seconds':45,'native_access':False,'heavy_lease':False},'tools':tools,'argv':argv,'cwd':str(S),'source_manifest_sha256':h(manifest),'sources':refs,'graph_sha256':h(graph),'weekly':{'at':q['at'],'usedPercent':windows[0]['usedPercent'],'resetsAt':windows[0]['resetsAt'],'windowDurationMins':10080},'actors':actors,'caps':cap,'guardian_effective_clock':{'lower':lower,'upper':upper,'journal':clock},'mem_available_bytes':memory,'free_bytes':free,'source_exclusion':'Root-confirmed private source ownership for this fixture'}
 publish('PROCESS-OWNER.json',owner);publish('ADMISSION.json',admission)
 out=os.open(str(O/'stdout.txt'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,0o600);err=os.open(str(O/'stderr.txt'),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,0o600)
 os.dup2(out,1);os.dup2(err,2);os.close(out);os.close(err);os.chdir(str(S))
 os.execv(argv[0],argv)

if __name__=='__main__':
 try:main()
 except BaseException as exc:
  try:publish('PREFLIGHT-FAIL.json',{'status':'ABORT_BEFORE_EXEC_OR_EXEC_UNKNOWN','error':type(exc).__name__+': '+str(exc),'at':time.time(),'grant_id':'ROOT_LIGHT_TEST_CALLBACK6_2_20261030'})
  except BaseException:pass
  raise
