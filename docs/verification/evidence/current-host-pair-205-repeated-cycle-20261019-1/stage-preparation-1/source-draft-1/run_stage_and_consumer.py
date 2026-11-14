"""Two fixed ordinary commands using the existing direct-join capture primitive."""
import argparse,hashlib,importlib.util,json,os,resource,signal,stat,time
from pathlib import Path
D=Path(__file__).resolve().parent
CAPTURE=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-two-rounds-20261019-1/stage-preparation-1/run_two_commands_source_bound.py')
CAPTURE_SHA='3f588c9306ad83308d2984914ad1d9d3ead794581f7db2a2db85473d4bf05cac'
def need(ok,label):
 if not ok:raise ValueError(label)
def main(profile,digest):
 start=time.monotonic();raw=Path(profile).read_bytes();need(hashlib.sha256(raw).hexdigest()==digest,'whole execution profile');p=json.loads(raw)
 need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7},'UID1000/CPU7')
 for kind,limit in [(resource.RLIMIT_AS,1<<30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20)]:need(resource.getrlimit(kind)==(limit,limit),'exact inherited ordinary cap')
 need(hashlib.sha256(CAPTURE.read_bytes()).hexdigest()==CAPTURE_SHA,'existing direct-join capture source')
 s=importlib.util.spec_from_file_location('existing_fixed_ordinary_capture',CAPTURE);capture=importlib.util.module_from_spec(s);s.loader.exec_module(capture)
 for row in p['tool_paths']:need(str(Path(row['path']).resolve(strict=True))==row['resolved'],'exact existing tool path resolution')
 authorities_raw=Path(p['source_authorities']['path']).read_bytes();need(hashlib.sha256(authorities_raw).hexdigest()==p['source_authorities']['sha256'] and len(authorities_raw)==p['source_authorities']['bytes'],'whole source authorities')
 for row in json.loads(authorities_raw):
  fd=os.open(row['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_size<=64<<20,'bounded source file');h=hashlib.sha256();n=0
   while True:
    block=os.read(fd,65536)
    if not block:break
    h.update(block);n+=len(block)
   z=os.fstat(fd);q=Path(row['path']).lstat();fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns');need(all(getattr(a,k)==getattr(z,k)==getattr(q,k) for k in fields),'stable source FD')
   actual=dict(path=row['path'],device=a.st_dev,inode=a.st_ino,uid=a.st_uid,gid=a.st_gid,mode=oct(stat.S_IMODE(a.st_mode)),size=n,nlink=a.st_nlink,mtime_ns=a.st_mtime_ns,ctime_ns=a.st_ctime_ns,sha256=h.hexdigest());need(actual==row,'whole pinned source identity')
  finally:os.close(fd)
 for value in p['fresh_outputs']:need(not os.path.lexists(value),'all fresh output roots')
 state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());usage=state['last_rate_limits']['primary']['usedPercent'];need(usage<97,'included usage')
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;need(mem>=5<<30,'RAMreserve+1GiB')
 for path,floor,growth in [('/home/holden/mckernel',16<<30,8<<20),('/home/holden/mckernel-work/scratch',12<<30,64<<20)]:
  v=os.statvfs(path);need(v.f_bavail*v.f_frsize>=floor+growth+(640<<20),'floor+growth+640reserve')
 out=Path(p['capture_root']);out.mkdir(mode=0o700);capture.write(out/'admission.json',dict(profile_sha256=digest,usage_percent=usage,mem_available_bytes=mem,whole_source_count=len(json.loads(authorities_raw)),root_cpu7_allocation_required=True))
 for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,capture.stop)
 records=[];error=None
 try:
  for i,command in enumerate(p['commands']):
   left=28-(time.monotonic()-start);need(left>0 and capture.cpu_used()<30,'shared28wall30CPU budget')
   target=out/('%02d-'%i+command['role']);target.mkdir(mode=0o700);capture.write(target/'command.json',command)
   cpu_left=max(1,int(30-capture.cpu_used()))
   def limits():
    resource.setrlimit(resource.RLIMIT_CPU,(cpu_left,cpu_left))
   record=capture.owned_capture(command,target,left,limits);record['role']=command['role'];capture.write(target/'status.json',record);records.append(record)
   need(record['returncode']==0 and record['direct_child_joined'] and record['group_absent'] and not record['timed_out'] and not record['error'] and not record['retirement_error'],'first command failure preserved')
   need(capture.cpu_used()<=30,'aggregate30CPU cap')
 except BaseException as exc:error=type(exc).__name__+': '+str(exc)
 result=dict(status='PASS_TWO_FIXED_ORDINARY_CYCLE_PREPARATION_STEPS_ONLY' if error is None and len(records)==2 else 'FAIL_STOP_FIRST_PRESERVE_ALL',profile_sha256=digest,records=records,error=error,seconds=time.monotonic()-start,CPU_seconds=capture.cpu_used(),stage_or_native_acceptance=False)
 capture.write(out/'whole-result.json',result);print(json.dumps({k:result[k] for k in ('status','seconds','CPU_seconds')}));return 0 if error is None and len(records)==2 else 1
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--profile',required=True);p.add_argument('--profile-sha256',required=True);a=p.parse_args();raise SystemExit(main(a.profile,a.profile_sha256))
