"""One root-admitted ordinary CPU7 check; status precedes stream hashes."""
import datetime,hashlib,json,os,resource,subprocess,time
from pathlib import Path
B=Path(__file__).resolve().parent;O=B/'ordinary-callback-check-1'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def store(name,obj):
 with (O/name).open('x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());used=state.get('last_rate_limits',{}).get('primary',{}).get('usedPercent')
 assert state.get('phase')=='running' and not state.get('pause_reason') and type(used) in (int,float) and used<100,'included-only service guard'
 for p,floor in [('/home/holden',16*2**30),('/home/holden/mckernel-work/scratch',12*2**30)]:
  s=os.statvfs(p);assert s.f_bavail*s.f_frsize>=floor+64*2**20
 proposal=json.loads((B/'FAILURE-CHAIN-PROPOSAL.json').read_text())
 for row in proposal['source_pins'].values():assert ref(Path(row['path']))==row
 argv=proposal['ordinary_check']['argv'];O.mkdir(mode=0o700)
 store('started.json',dict(argv=argv,profile='CPU7/1job/AS1GiB/CPU30/wall35+2/FS32MiB/core0/nofile256',started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),proposal=ref(B/'FAILURE-CHAIN-PROPOSAL.json'),driver=ref(Path(__file__))))
 os.sched_setaffinity(0,{7});resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432))
 started=time.monotonic()
 with (O/'stdout').open('xb') as out,(O/'stderr').open('xb') as err:
  child=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True,stdin=subprocess.DEVNULL)
  store('child.json',dict(pid=child.pid,pgid=child.pid,argv=argv))
  rc=child.wait();out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
  store('direct-wait.json',dict(pid=child.pid,returncode=rc,direct_child_joined=True,elapsed_seconds=time.monotonic()-started))
 try:os.killpg(child.pid,0);absent=False
 except ProcessLookupError:absent=True
 store('group.json',dict(pgid=child.pid,process_group_absent=absent))
 whole=dict(status='PASS' if rc==0 and absent else 'FAIL',returncode=rc,direct_child_joined=True,process_group_absent=absent,cpu7_released=absent,stdout=ref(O/'stdout'),stderr=ref(O/'stderr'))
 store('whole.json',whole);print(json.dumps({k:whole[k] for k in ('status','returncode','direct_child_joined','process_group_absent','cpu7_released')}))
 return 0 if whole['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
