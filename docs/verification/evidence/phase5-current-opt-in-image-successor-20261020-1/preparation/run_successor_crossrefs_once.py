from pathlib import Path
import importlib.util,json,os,resource,time,signal,hashlib,sys
R=Path(__file__).resolve().parent;O=R/'actual-successor-crossref-capture-1';O.mkdir(mode=0o700)
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py');s=importlib.util.spec_from_file_location('accepted_owned_capture',S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for number in m.STOP_SIGNALS:signal.signal(number,m.stop)
assert os.sched_getaffinity(0)=={6} and resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
p=R/'probe_successor_crossrefs.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='fa84953e7f20baf4546cb63dc33a700c453df67e00f57fd8bfb747ec0bda0761' and p.stat().st_size==3045
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());assert state['phase']=='running' and not state.get('pause_reason') and not state.get('stop_reason') and state['last_rate_limits']['primary']['usedPercent']<100
measured=[]
for root,floor in [('/home/holden/mckernel-work',16<<30),('/home/holden/mckernel-work/scratch',12<<30)]:
 v=os.statvfs(root);free=v.f_bavail*v.f_frsize;assert free>=floor+(64<<20);measured.append({'path':root,'free_bytes':free,'floor':floor,'growth':64<<20})
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;assert mem>=1<<30
command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(p)]};m.write(O/'initial-command-and-admission.json',{'command':command,'profile':{'cpu':6,'jobs':1,'as':1<<30,'cpu_seconds':30,'wall_seconds':35,'kill_after':2,'fsize':32<<20,'core':0,'nofile':256},'measured_storage':measured,'measured_mem_available':mem,'phase':state['phase'],'pause_reason':state.get('pause_reason'),'used_percent':state['last_rate_limits']['primary']['usedPercent'],'uid':os.getuid(),'affinity':sorted(os.sched_getaffinity(0)),'interpreter':sys.executable})
def limits():
 for kind,val in [(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_AS,1<<30)]:resource.setrlimit(kind,(val,val))
begin=time.monotonic();rec=m.owned_capture(command,O,35,limits);m.write(O/'whole.json',{'record':rec,'elapsed_seconds':time.monotonic()-begin,'scope':'actual deterministic crossrefs and9copy AST only; noowner.run/livevalidate/Docker/lock/compiler/sourcecopy'});ok=rec['returncode']==0 and rec['direct_child_joined'] and rec['group_absent'] and rec['error'] is None and rec['retirement_error'] is None;print(json.dumps({'returncode':rec['returncode'],'seconds':time.monotonic()-begin,'direct_joined':rec['direct_child_joined'],'group_absent':rec['group_absent'],'closed_streams':rec['closed_streams'],'error':rec['error'],'retirement_error':rec['retirement_error']}));raise SystemExit(0 if ok else 1)
