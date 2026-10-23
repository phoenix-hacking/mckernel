"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Explicitly selected Linux x86_64 LP64 pidfd syscall provider. No Python API or numeric-signal fallback.
"""
import ctypes,errno,hashlib,json,os,signal,stat,sys
from pathlib import Path
EXPECTED = {'pid': 3925729, 'start': 58851263, 'pgid': 3925729, 'sid': 3925729, 'uid': 0, 'gid': 0, 'controller_uid': 0, 'boot_id': '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb', 'source_path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-successor-1/source/native_diagnostic_container_owner.py', 'source_sha256': 'b23c19f45edf56c0b693e6a809727f85d6443d5c6569e02210ba2be97af6e6f3', 'cmdline': ['/home/holden/anaconda3/bin/python3', '-I', '-B', '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-successor-1/source/native_diagnostic_container_owner.py', '--owner-sha256', 'b23c19f45edf56c0b693e6a809727f85d6443d5c6569e02210ba2be97af6e6f3', '--attempt-parent', '/home/holden/mckernel-work/l12s8a1/p', '--nonce', '599bd7a0a4cb4e29b52d6ed0cc9aa0db', '--manifest', '/home/holden/mckernel-work/scratch/p12s8l1/m.json', '--manifest-sha256', '6cfab63af3a9a528865134124dec5fde33ef209a0133153f91e55561341f18cf', '--long-profile-release', '/home/holden/mckernel-work/scratch/p12s8l1/r.json', '--long-profile-release-sha256', '6803fdc29865203ab245c34f47cb08e131abf9cba933150cee98ad09c0f4bba5'], 'nonce': '599bd7a0a4cb4e29b52d6ed0cc9aa0db'}
PYTHON='/home/holden/anaconda3/bin/python3'
SYS_PIDFD_OPEN = 434
SYS_PIDFD_SEND_SIGNAL = 424
HEADER_MACRO_SHA256 = 'd167cc6c5911f84e4a536b10e2f64456d6875f8f16ef2404e41a136816e6a26b'
def need(v,m):
 if not v:raise ValueError(m)
def require_architecture():
 need(os.uname().machine=='x86_64' and ctypes.sizeof(ctypes.c_long)==8 and ctypes.sizeof(ctypes.c_void_p)==8 and ctypes.sizeof(ctypes.c_int)==4 and sys.maxsize==2**63-1,'exact Linux x86_64 LP64 syscall ABI')
 require_linux=sys.platform=='linux';need(require_linux,'Linux pidfd ABI only')
def libc_syscall():
 require_architecture()
 libc=ctypes.CDLL(None,use_errno=True);call=libc.syscall
 call.restype=ctypes.c_long;call.argtypes=[ctypes.c_long]
 return libc,call
def typed_pidfd_open(pid):
 libc,call=libc_syscall();ctypes.set_errno(0)
 result=call(ctypes.c_long(SYS_PIDFD_OPEN),ctypes.c_int(pid),ctypes.c_uint(0))
 if result==-1:raise OSError(ctypes.get_errno(),'pidfd_open syscall')
 need(0<=result<=2**31-1,'pidfd_open result fitsint');return int(result)
def typed_pidfd_send_term(fd):
 libc,call=libc_syscall();ctypes.set_errno(0)
 result=call(ctypes.c_long(SYS_PIDFD_SEND_SIGNAL),ctypes.c_int(fd),ctypes.c_int(signal.SIGTERM),ctypes.c_void_p(None),ctypes.c_uint(0))
 if result==-1:raise OSError(ctypes.get_errno(),'pidfd_send_signal syscall')
 need(result==0,'pidfd_send_signal exactzero');return 0
def fdinfo_pid(fd):
 path=Path('/proc/self/fdinfo')/str(fd);raw=path.read_bytes();need(len(raw)<=4096,'bounded pidfd fdinfo')
 rows=[line.split(':',1)[1].strip() for line in raw.decode('ascii').splitlines() if line.startswith('Pid:')]
 need(len(rows)==1,'exact pidfd Pid field');return int(rows[0])
def stable_regular(path,cap):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_size<=cap,'bounded regular source')
  b=b''
  while len(b)<=cap:
   chunk=os.read(fd,min(65536,cap+1-len(b)))
   if not chunk:break
   b+=chunk
  z=os.fstat(fd);n=os.lstat(path);fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_uid','st_gid','st_nlink')
  need(len(b)==a.st_size and all(getattr(a,k)==getattr(z,k)==getattr(n,k) for k in fields),'stable source identity')
  return b
 finally:os.close(fd)
def snapshot(expected):
 p=Path('/proc')/str(expected['pid'])
 try:fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
 except FileNotFoundError:return None
 try:
  def read(name,cap):
   child=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
   try:
    raw=os.read(child,cap+1);need(len(raw)<=cap,'bounded process identity '+name);return raw
   finally:os.close(child)
  try:
   first=read('stat',16384).decode().rpartition(') ')[2].split();status=read('status',65536).decode();cmdline=read('cmdline',65536);last=read('stat',16384).decode().rpartition(') ')[2].split()
  except (FileNotFoundError,ProcessLookupError):return None
  need(len(first)>19 and len(last)>19 and first[19]==last[19],'stable process start')
  row=dict(line.split(':',1) for line in status.splitlines() if ':' in line)
  return dict(pid=expected['pid'],start=int(last[19]),state=last[0],pgid=int(last[2]),sid=int(last[3]),uids=[int(x) for x in row['Uid'].split()],gids=[int(x) for x in row['Gid'].split()],cmdline=cmdline)
 finally:os.close(fd)
def verify(expected,fact):
 need(fact['start']==expected['start'],'exact owner birth')
 if fact['state']=='Z':return 'ALREADY_TERMINAL_ZOMBIE'
 need(fact['state'] not in ('X','x'),'owner alreadyterminal')
 need(fact['pgid']==expected['pgid'] and fact['sid']==expected['sid'],'exact owner PGID/SID')
 need(fact['uids']==[expected['uid']]*4 and fact['gids']==[expected['gid']]*4,'exact owner UID/GID')
 need(fact['cmdline']==b'\0'.join(x.encode() for x in expected['cmdline'])+b'\0','exact owner cmdline')
 return 'MATCHED_LIVE_IDENTITY'

def cancel(expected):
 require_architecture();need(os.getuid()==os.geteuid()==expected['controller_uid'],'exact controller UID')
 result=dict(scope=__doc__,pid=expected['pid'],expected_start=expected['start'],nonce=expected['nonce'],source_sha256=expected['source_sha256'],signal='SIGTERM',signal_calls=0,physical_clearance=False,application_acceptance=False,owner_cleanup_observed=False,provider='explicit ctypes libc.syscall pidfd only')
 # Open the exact process handle BEFORE fresh target identity/source checks.
 try:pidfd=typed_pidfd_open(expected['pid'])
 except OSError as e:
  if e.errno==errno.ESRCH:result['status']='OBSERVED_ALREADY_ABSENT_NO_SIGNAL';return result
  raise
 try:
  def checked_identity():
   need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected['boot_id'],'exact current boot')
   need(hashlib.sha256(stable_regular(expected['source_path'],2**20)).hexdigest()==expected['source_sha256'],'exact selected owner source')
   fact=snapshot(expected)
   if fact is None:return None
   return fact,verify(expected,fact)
  fd_pid=fdinfo_pid(pidfd)
  if fd_pid==-1:result['status']='OBSERVED_PIDFD_TARGET_EXITED_NO_SIGNAL';return result
  need(fd_pid==expected['pid'],'pidfd exact target PID')
  first=checked_identity()
  if first is None:result['status']='OBSERVED_EXIT_AFTER_PIDFD_OPEN_NO_SIGNAL';return result
  if first[1]!='MATCHED_LIVE_IDENTITY':result['status']=first[1]+'_NO_SIGNAL';return result
  second=checked_identity()
  if second is None:result['status']='OBSERVED_EXIT_BEFORE_SIGNAL_NO_SIGNAL';return result
  if second[1]!='MATCHED_LIVE_IDENTITY':result['status']=second[1]+'_NO_SIGNAL';return result
  fd_pid=fdinfo_pid(pidfd)
  if fd_pid==-1:result['status']='OBSERVED_PIDFD_TARGET_EXITED_BEFORE_SIGNAL_NO_SIGNAL';return result
  need(fd_pid==expected['pid'],'pidfd still exact target PID')
  result['signal_calls']=1
  try:typed_pidfd_send_term(pidfd)
  except OSError as e:
   if e.errno==errno.ESRCH:result['status']='OBSERVED_EXIT_AT_SIGNAL_NO_RETRY';return result
   raise
  fact=second[0];result.update(status='ONE_SIGTERM_SENT_TO_EXACT_OWNER_ONLY',matched_uid=fact['uids'],matched_pgid=fact['pgid'],matched_sid=fact['sid'],fdinfo_pid=fd_pid);return result
 finally:os.close(pidfd)
def main():
 need(len(sys.argv)==2 and sys.executable==PYTHON and sys.version_info[:3]==(3,9,12),'exact selected Anaconda3.9.12 invocation')
 need(hashlib.sha256(stable_regular(str(Path(__file__).resolve()),65536)).hexdigest()==sys.argv[1],'exact cancel source digest')
 try:r=cancel(EXPECTED)
 except (OSError,ValueError,KeyError,IndexError) as e:
  print(json.dumps(dict(scope=__doc__,status='REFUSED_NO_FALLBACK',error=type(e).__name__+': '+str(e),physical_clearance=False,application_acceptance=False),sort_keys=True));raise SystemExit(1)
 print(json.dumps(r,sort_keys=True))
if __name__=='__main__':main()
