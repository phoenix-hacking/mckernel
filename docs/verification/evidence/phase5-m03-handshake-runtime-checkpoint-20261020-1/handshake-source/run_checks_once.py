"""One granted CPU6 host-only five-command envelope; no root/stage/guest."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
REF=D/'EXECUTOR-PINS.json'

def main():
 begin=time.monotonic();refs=json.loads(REF.read_text())
 def pin(row):
  p=Path(row['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
  try:
   a=os.fstat(fd);raw=b''
   while True:
    b=os.read(fd,65536)
    if not b:break
    raw+=b;assert len(raw)<=2<<20
   z=os.fstat(fd);q=p.lstat()
   fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
   assert stat.S_ISREG(a.st_mode) and all(getattr(a,k)==getattr(z,k)==getattr(q,k) for k in fields)
   assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
   return raw
  finally:os.close(fd)
 for row in refs['pins']:pin(row)
 capture=Path(refs['capture']['path']);pin(refs['capture'])
 spec=importlib.util.spec_from_file_location('accepted_owned_capture',capture);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
 assert resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
 assert resource.getrlimit(resource.RLIMIT_CPU)==(30,30)
 assert resource.getrlimit(resource.RLIMIT_FSIZE)==(32<<20,32<<20)
 assert resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
 s=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
 assert s['phase']=='running' and s['stop_reason'] is None and s['last_rate_limits']['primary']['usedPercent']<100
 scratch=Path('/home/holden/mckernel-work/scratch')
 assert subprocess.run(['/usr/bin/findmnt','-n','-o','UUID','--target',str(scratch)],capture_output=True,text=True,check=True).stdout.strip()=='2a5768c8-718d-4914-bdc0-6b32c5a92a52'
 boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 assert not os.path.lexists(scratch/'mckernel-heavy-operation.lock')
 assert D.stat().st_dev!=scratch.stat().st_dev
 cpu6=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit() or int(proc.name)==os.getpid():continue
  try:
   if os.sched_getaffinity(int(proc.name))!={6}:continue
   raw=(proc/'stat').read_text().rsplit(')',1)[1].split();flags=int(raw[6]);assert flags&0x200000,'nonkernel CPU6 owner '+proc.name
   cpu6.append(int(proc.name))
  except ProcessLookupError:raise RuntimeError('CPU6 census unstable')
 def capacity():
  hv=os.statvfs(D);sv=os.statvfs(scratch)
  assert hv.f_bavail*hv.f_frsize>=(16<<30)+(128<<20)+(640<<20)
  assert sv.f_bavail*sv.f_frsize>=(12<<30)+(640<<20)
  mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
  assert mem>=5<<30
  return dict(host_free=hv.f_bavail*hv.f_frsize,scratch_free=sv.f_bavail*sv.f_frsize,mem_available=mem)
 admission=capacity();O=D/'check-1';assert not O.exists();O.mkdir(mode=0o700);(O/'vectors').mkdir(mode=0o700)
 m.write(O/'admission.json',dict(boot_id=boot,cpu6_other_owners_kernel_only=cpu6,capacity=admission,source_ref=refs,guest_runs=0,scratch_growth_bytes=0))
 proposal=json.loads((D/'ORDINARY-CHECK-PROPOSAL-v2.json').read_text());commands=proposal['commands'];records=[];error=None
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,m.stop)
 signal.setitimer(signal.ITIMER_REAL,max(.1,30-(time.monotonic()-begin)))
 try:
  for i,argv in enumerate(commands):
   capacity();left=30-(time.monotonic()-begin);assert left>0 and m.cpu_used()<30
   p=O/('%02d-command'%i);p.mkdir(mode=0o700);m.write(p/'command.json',dict(argv=argv))
   def limits():
    os.sched_setaffinity(0,{6});resource.setrlimit(resource.RLIMIT_CPU,(30,30))
   r=m.owned_capture(dict(argv=argv),p,min(10,left),limits);m.write(p/'status.json',r);records.append(r)
   if r['returncode']!=0 or not r['direct_child_joined'] or not r['group_absent'] or r['timed_out'] or r['error'] or r['retirement_error'] or r['captures']['stderr']['size']!=0:
    error='first unexpected command failure';break
  assert m.cpu_used()<=30;capacity()
 except BaseException as exc:error=type(exc).__name__+': '+str(exc)
 finally:signal.setitimer(signal.ITIMER_REAL,0)
 ok=error is None and len(records)==5
 result=dict(status='PASS_HOST_FIXTURES_AND_STATIC_COLLECTOR' if ok else 'FAIL_STOP_PRESERVE',records=records,error=error,elapsed_seconds=time.monotonic()-begin,CPU_seconds=m.cpu_used(),guest_runs=0,stage_or_runtime_acceptance=False)
 m.write(O/'whole.json',result);print(json.dumps({k:result[k] for k in ('status','error','elapsed_seconds','CPU_seconds')}));return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
