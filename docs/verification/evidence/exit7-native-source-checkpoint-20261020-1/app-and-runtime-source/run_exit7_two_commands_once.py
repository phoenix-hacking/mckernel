"""Fixed adaptation of accepted owned_capture, no new capture framework.

Dispatcher CPU6 grant is required externally. Source/body checks then stage;
first failure stops. No compiler, root, module, Docker or guest command.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,stat,time
D=Path(__file__).resolve().parent

def checked(row):
 p=Path(row['path']);a=p.lstat();raw=p.read_bytes();b=p.lstat()
 assert stat.S_ISREG(a.st_mode) and a.st_mode==row['mode']
 fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')
 assert all(getattr(a,k)==getattr(b,k)for k in fields)
 assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 return raw

def main():
 begin=time.monotonic()
 cfg=json.loads((D/'SERIAL-CAPTURE-ENVELOPE.json').read_bytes())
 checked(cfg['wrapper'])
 source=checked(cfg['capture_engine'])
 spec=importlib.util.spec_from_file_location('accepted_exit7_owned_capture',cfg['capture_engine']['path'])
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.STOP_SIGNALS.add(signal.SIGXCPU)
 for number in m.STOP_SIGNALS:signal.signal(number,m.stop)
 # Parent only:10 CPU seconds, hard80 retained so children can lower to8/55.
 # The two child limits total63, so whole planned CPU bound is73<80.
 assert resource.getrlimit(resource.RLIMIT_CPU)==(80,80)
 resource.setrlimit(resource.RLIMIT_CPU,(10,80))
 signal.setitimer(signal.ITIMER_REAL,max(0.1,84-(time.monotonic()-begin)))
 assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
 assert os.sched_getaffinity(0)=={6}
 for kind,value in [(resource.RLIMIT_AS,1<<30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256)]:
  assert resource.getrlimit(kind)==(value,value)
 assert hashlib.sha256(m.CENSUS_SOURCE.read_bytes()).hexdigest()==m.CENSUS_SHA
 checked(cfg['census_engine'])
 commands=json.loads(checked(cfg['commands']))
 freeze=json.loads(checked(cfg['source_freeze']))
 for row in freeze['files']:checked(row)
 data=json.loads((D/'INPUT-AND-DECLARED-DATA.json').read_bytes())
 for key in ('retained_case','accepted_linux','rust_source','oracle','accepted_app','expected_stdout','expected_stderr','tested_parent','current_collector','current_overlay','base','stage_engine','overlay_engine','tested_runtime_evaluator','private_evaluator'):checked(data[key])
 state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
 assert state['phase']=='running' and not state.get('pause_reason') and not state.get('stop_reason') and state['last_rate_limits']['primary']['usedPercent']<100
 assert not os.path.lexists('/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock')
 for path in cfg['required_absent_paths']:assert not os.path.lexists(path),path
 mem=int(next(x.split()[1]for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')))*1024
 assert mem>=5<<30
 scratch=Path('/home/holden/mckernel-work/scratch')
 assert D.stat().st_dev!=scratch.stat().st_dev
 for path,floor,growth in [(D,16<<30,256<<20),(scratch,12<<30,0)]:
  v=os.statvfs(path);assert v.f_bavail*v.f_frsize>=floor+growth
 O=D/'ordinary-capture-1';O.mkdir(mode=0o700)
 m.write(O/'admission.json',dict(affinity=[6],included_used_percent=state['last_rate_limits']['primary']['usedPercent'],mem_available=mem,external_CPU6_grant_required=True,commands=commands,profile=cfg['profile']))
 records=[];failed=None
 try:
  for index,command in enumerate(commands):
   assert not m.stopping
   remaining=84-(time.monotonic()-begin)
   assert remaining>=command['wall_seconds']+6,'full next child plus retirement headroom'
   folder=O/('%02d-command'%index);folder.mkdir(mode=0o700)
   m.write(folder/'command.json',command)
   def limits():
    os.sched_setaffinity(0,{6})
    for kind,value in [(resource.RLIMIT_CPU,command['cpu_seconds']),(resource.RLIMIT_AS,1<<30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256)]:resource.setrlimit(kind,(value,value))
   record=m.owned_capture(command,folder,command['wall_seconds'],limits)
   m.write(folder/'status.json',record);records.append(record)
   if record['returncode']!=0 or not record['direct_child_joined'] or not record['group_absent'] or record['timed_out'] or record['error'] or record['retirement_error'] or record['captures']['stderr']['size']:
    failed='first command failure';break
  assert m.cpu_used()<=80,'whole aggregate CPU bound'
 except BaseException as exc:failed=type(exc).__name__+': '+str(exc)
 finally:
  signal.setitimer(signal.ITIMER_REAL,0)
  m.write(O/'whole.json',dict(records=records,failure=failed,elapsed_seconds=time.monotonic()-begin,aggregate_CPU_seconds=m.cpu_used(),guest_runs=0,root_operations=0,compiler_runs=0))
 print(json.dumps(dict(status='PASS_TWO_ORDINARY_COMMANDS'if failed is None and len(records)==2 else 'FAIL',commands=len(records),failure=failed,guest_runs=0)))
 return 0 if failed is None and len(records)==2 else 1

if __name__=='__main__':raise SystemExit(main())
