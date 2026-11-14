"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact pidfd SIGTERM to the selected normal owner. No cleanup or physical-clearance authority.
"""
import hashlib,json,os,signal,stat,sys
from pathlib import Path
EXPECTED = {'pid': 3769329, 'start': 56612906, 'pgid': 3769329, 'sid': 3769329, 'uid': 0, 'gid': 0, 'controller_uid': 0, 'boot_id': '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb', 'source_path': '/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1/current110-variant-1/final-LONG-execution-preparation-1/bounded-correction-1/final-execution-assembly-1/post-M14-fresh-admission-preparation-1/expired-release-successor-1/serialized-release-successor-2/source/native_diagnostic_container_owner.py', 'source_sha256': '401657d55cd24609d81a98f00efdb6141185ccfd2766092aa69f2be30d7ca70c', 'cmdline': ['/home/holden/anaconda3/bin/python3', '-I', '-B', '/home/holden/mckernel-work/host-preparation/p12-sdk5-session-successor-20261023-1/current110-variant-1/final-LONG-execution-preparation-1/bounded-correction-1/final-execution-assembly-1/post-M14-fresh-admission-preparation-1/expired-release-successor-1/serialized-release-successor-2/source/native_diagnostic_container_owner.py', '--owner-sha256', '401657d55cd24609d81a98f00efdb6141185ccfd2766092aa69f2be30d7ca70c', '--attempt-parent', '/home/holden/mckernel-work/native-runs/l12a1/p', '--nonce', '110f473a34f14ca58d88e080e273be2c', '--manifest', '/home/holden/mckernel-work/scratch/p12s5l1/m.json', '--manifest-sha256', '6c3c80bff36af0f96ce05f73294c37f035a3e12d7fdc3aeeef88fc7532c11471', '--long-profile-release', '/home/holden/mckernel-work/scratch/p12s5l1/r-renewal-2.json', '--long-profile-release-sha256', 'e38c4a884c1c03bc931fc3467721520df208967b6bfe3eedb1a18415f1501ccf'], 'nonce': '110f473a34f14ca58d88e080e273be2c'}
PYTHON='/home/holden/anaconda3/bin/python3'
def need(v,m):
 if not v:raise ValueError(m)
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
 need(callable(getattr(os,'pidfd_open',None)) and callable(getattr(signal,'pidfd_send_signal',None)),'pidfd API unavailable; no fallback')
 need(os.getuid()==os.geteuid()==expected['controller_uid'],'exact controller UID')
 need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected['boot_id'],'exact current boot')
 need(hashlib.sha256(stable_regular(expected['source_path'],2**20)).hexdigest()==expected['source_sha256'],'exact selected owner source')
 first=snapshot(expected)
 result=dict(scope=__doc__,pid=expected['pid'],expected_start=expected['start'],nonce=expected['nonce'],source_sha256=expected['source_sha256'],signal='SIGTERM',signal_calls=0,physical_clearance=False,application_acceptance=False,owner_cleanup_observed=False,mutations='Only one targeted pidfd SIGTERM if all exactguards pass; no external ownership/lease/file changes')
 if first is None:result['status']='OBSERVED_ALREADY_ABSENT_NO_SIGNAL';return result
 state=verify(expected,first)
 if state!='MATCHED_LIVE_IDENTITY':result['status']=state+'_NO_SIGNAL';return result
 try:pidfd=os.pidfd_open(expected['pid'],0)
 except ProcessLookupError:result['status']='OBSERVED_EXIT_DURING_PIDFD_OPEN_NO_SIGNAL';return result
 try:
  second=snapshot(expected)
  if second is None:result['status']='OBSERVED_EXIT_AFTER_PIDFD_OPEN_NO_SIGNAL';return result
  state=verify(expected,second)
  if state!='MATCHED_LIVE_IDENTITY':result['status']=state+'_NO_SIGNAL';return result
  need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==expected['boot_id'],'current boot immediately before signal')
  need(hashlib.sha256(stable_regular(expected['source_path'],2**20)).hexdigest()==expected['source_sha256'],'source immediately before signal')
  # pidfd pins this process across numeric PID reuse. Never kill(), killpg() or retry.
  try:signal.pidfd_send_signal(pidfd,signal.SIGTERM,None,0)
  except ProcessLookupError:result['status']='OBSERVED_EXIT_AT_SIGNAL_NO_RETRY';return result
  result.update(status='ONE_SIGTERM_SENT_TO_EXACT_OWNER_ONLY',signal_calls=1,matched_uid=second['uids'],matched_pgid=second['pgid'],matched_sid=second['sid']);return result
 finally:os.close(pidfd)
def main():
 need(len(sys.argv)==2 and sys.executable==PYTHON and sys.version_info[:3]==(3,9,12),'exact selected Anaconda3.9.12 invocation')
 need(hashlib.sha256(stable_regular(str(Path(__file__).resolve()),65536)).hexdigest()==sys.argv[1],'exact cancel source digest')
 try:r=cancel(EXPECTED)
 except (OSError,ValueError,KeyError,IndexError) as e:
  print(json.dumps(dict(scope=__doc__,status='REFUSED_NO_FALLBACK',error=type(e).__name__+': '+str(e),physical_clearance=False,application_acceptance=False),sort_keys=True));raise SystemExit(1)
 print(json.dumps(r,sort_keys=True))
if __name__=='__main__':main()
