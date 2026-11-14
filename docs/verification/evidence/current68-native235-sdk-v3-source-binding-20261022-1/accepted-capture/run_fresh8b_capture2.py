from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,sys,time
V=Path(__file__).resolve().parent;run=V/'affected-path-run-2'
def pin(p,sha):
 raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==sha;return raw
index=json.loads(pin(V/'SOURCE-AMENDMENT-INDEX.json','dae579326898fc7c1992a1e48f6882b52a3135560a81918df5598748a1777391'));proposal=json.loads(pin(V/'AFFECTED-FIXTURE-PROPOSAL.json','1405600d11649206f3e28d4d24696b7914e4e55408ad43f09316c1532cf6a903'))
for ref in index['files'].values():
 raw=pin(Path(ref['path']),ref['sha256']);assert len(raw)==ref['bytes']
assert not run.exists() and 6 in os.sched_getaffinity(0)
mem=next(int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'));fs=lambda p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize;host=fs('/home/holden/mckernel');scratch=fs('/home/holden/mckernel-work/scratch');reserve=(640+64)<<20
assert mem>=(16<<30)+reserve and host>=(16<<30)+reserve and scratch>=(12<<30)+reserve
python=Path(shutil.which('python3')).resolve();assert python==Path(sys.executable).resolve();run.mkdir(mode=0o700)
def write(name,value):
 fd=os.open(run/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
write('admission.json',dict(status='PASS_FRESH_CPU6_ADMISSION',mem_available_bytes=mem,host_free_bytes=host,scratch_free_bytes=scratch,reserve_bytes=reserve,profile=proposal['profile'],python_resolved=str(python),python_version=sys.version,argv=proposal['command'],namespace_absent_before_create=True,source_index_sha256='dae579326898fc7c1992a1e48f6882b52a3135560a81918df5598748a1777391',source_refs=len(index['files']),writer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),prior_attempt='affected-path-run-1',root_new_admission='User18:00 numeric child status genuinely absent; one freshcapture2 authorized'))
stdout=(run/'stdout').open('xb');stderr=(run/'stderr').open('xb');start=time.monotonic();child=subprocess.Popen(proposal['command'],stdout=stdout,stderr=stderr,start_new_session=True);pid=child.pid;proc_start=Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
write('child-start.json',dict(pid=pid,proc_start_ticks=proc_start,argv=proposal['command'],process_group=pid))
rc=child.wait();elapsed=time.monotonic()-start
write('direct-join.json',dict(pid=pid,proc_start_ticks=proc_start,direct_joined=True,returncode=rc,elapsed_seconds=elapsed))
stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno());stdout.close();stderr.close()
try:os.killpg(pid,0)
except ProcessLookupError:absent=True
else:absent=False
write('stream-and-group-close.json',dict(streams_closed=True,process_group_absent=absent,pid=pid));assert absent
def descriptor(name):
 path=run/name;fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  a=os.fstat(fd);raw=os.read(fd,a.st_size+1);b=os.fstat(fd);named=path.lstat();fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  assert all(getattr(a,k)==getattr(b,k)==getattr(named,k) for k in fields) and stat.S_ISREG(b.st_mode) and b.st_nlink==1 and len(raw)==b.st_size and len(raw)<=33554432
  return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),device=b.st_dev,inode=b.st_ino,uid=b.st_uid,gid=b.st_gid,mode=oct(stat.S_IMODE(b.st_mode)),nlink=b.st_nlink,mtime_ns=b.st_mtime_ns,ctime_ns=b.st_ctime_ns)
 finally:os.close(fd)
status=dict(status='PASS' if rc==0 else 'FAIL_PRESERVED_STOPPED',pid=pid,proc_start_ticks=proc_start,argv=proposal['command'],direct_joined=True,returncode=rc,elapsed_seconds=elapsed,streams_closed=True,process_group_absent=absent,stdout=descriptor('stdout'),stderr=descriptor('stderr'),cpu6_released=True)
write('status.json',status);print(json.dumps(dict(status=status['status'],returncode=rc,elapsed_seconds=elapsed,stdout_bytes=status['stdout']['bytes'],stderr_bytes=status['stderr']['bytes'],status_path=str(run/'status.json'),status_sha256=hashlib.sha256((run/'status.json').read_bytes()).hexdigest(),cpu6_released=True)))
