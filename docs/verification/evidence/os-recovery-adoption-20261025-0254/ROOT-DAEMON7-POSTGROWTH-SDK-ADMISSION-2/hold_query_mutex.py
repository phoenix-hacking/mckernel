"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Ordinary query custody only; close own FD after Root's exact command and joined query.
"""
from pathlib import Path
import os,fcntl,json,time,signal,hashlib,importlib.util,sys
A=Path(__file__).resolve().parent;S=A.parent/'scratch-growth-final-copy-close-source-1/recover_growth_custody.py'
assert hashlib.sha256(S.read_bytes()).hexdigest()=='04b5c6af885baca472e99e590bf07ae360dacad95487709477cf3d2bf8d6c90a'
spec=importlib.util.spec_from_file_location('accepted_pure_account_guard',S);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m.BOOT
assert all(c<e for c,e in zip([time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)],m.CUTOFFS))
m.check_account_state(json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes()),time.time())
request=json.loads((A/'SDK7-REQUEST.json').read_bytes());lock=Path('/run/lock/mckernel-development.lock')
def metadata(s):return (s.st_dev,s.st_ino,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mode)
assert metadata(lock.lstat())==(27,4,0,0,1,0,0o100644)
fd=os.open(lock,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BaseException:os.close(fd);raise
for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP,signal.SIGQUIT]:signal.signal(sig,signal.SIG_IGN)
try:
 assert metadata(os.fstat(fd))==metadata(lock.lstat())==(27,4,0,0,1,0,0o100644)
 raw=Path('/proc/self/stat').read_text().rsplit(') ',1)[1].split();ready=dict(pid=os.getpid(),starttime=int(raw[19]),fd=fd,device=27,inode=4,uid=1000,nonce=request['nonce'],command_hex=Path('/proc/self/cmdline').read_bytes().hex())
 with (A/'QUERY-HOLDER.READY.json').open('x') as f:json.dump(ready,f,indent=2);f.write('\n')
 print(json.dumps(ready),flush=True)
 while True:
  line=sys.stdin.readline()
  normal=line.strip()=='CLOSE '+request['nonce'];failed=line.strip()=='CLOSE_FAILED_QUERY '+request['nonce']
  if not (normal or failed):time.sleep(1);continue
  joinraw=(A/'QUERY-WHOLE-JOIN.json').read_bytes();joins=json.loads(joinraw)
  assert joins['direct_child_joined'] is True and joins['group_absent'] is True and joins['closed_streams'] is True and joins['retirement_error'] is None
  if normal:assert joins['returncode']==0 and joins['joined'] is True
  else:
   release=json.loads((A/'FAILED-QUERY-CLOSE-REVIEW.json').read_bytes())
   assert release['decision']=='PASS_QUERY_ONLY_HOLDER_CLOSE' and release['independent'] is True and release['implementation_ownership'] is False and release['reviewer'] not in ('','/root',None)
   assert release['holder']==ready and release['query_join_sha256']==hashlib.sha256(joinraw).hexdigest() and release['SDK_workload_entered'] is False
  assert not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().strip()
  assert metadata(os.fstat(fd))==metadata(lock.lstat())==(27,4,0,0,1,0,0o100644)
  os.close(fd);fd=None
  with (A/'QUERY-HOLDER.NORMAL-CLOSE.json').open('x') as f:json.dump(dict(holder=ready,fd_closed=True,lock_un_called=False,closed_wall=time.time()),f,indent=2);f.write('\n')
  print('Query holder own FD closed normally',flush=True);break
except BaseException as error:
 print(('QUERY_POSTCLOSE_FAULT ' if fd is None else 'QUERY_CUSTODY_HOLD ')+repr(error),flush=True)
 if fd is None:raise SystemExit(2)
 while True:time.sleep(30)
