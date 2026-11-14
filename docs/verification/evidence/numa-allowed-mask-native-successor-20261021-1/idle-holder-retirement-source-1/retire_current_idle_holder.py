#!/usr/bin/env python3
"""One exact idle cleanup holder only. Separate release; no engine/record cleanup.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse,base64,ctypes,fcntl,hashlib,json,os,re,resource,select,signal,stat,time
from pathlib import Path
D=Path(__file__).resolve().parent
PROFILE=D/'CURRENT-EXACT-PROFILE.json'
LOCK=Path('/run/lock/mckernel-development.lock')
DEFERRED=(signal.SIGHUP,signal.SIGINT,signal.SIGTERM,signal.SIGQUIT)
CAP=1<<20

def need(ok,why):
 if not ok:raise RuntimeError(why)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'
def full9(s):return dict(device=s.st_dev,inode=s.st_ino,mode=s.st_mode,nlink=s.st_nlink,uid=s.st_uid,gid=s.st_gid,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def read(path,cap=CAP):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  parts=[];count=0
  while True:
   b=os.read(fd,min(65536,cap+1-count))
   if not b:break
   parts.append(b);count+=len(b)
   need(count<=cap,'bounded read exceeded')
  return b''.join(parts)
 finally:os.close(fd)
def bound(pointer):
 raw=read(pointer['path']);need(len(raw)==pointer['bytes'] and digest(raw)==pointer['sha256'],'exact bound input drift');return json.loads(raw)
def identity_check(p):
 need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==p['boot_id'],'boot drift')
 t=p['target'];base=Path('/proc')/str(t['pid']);first=read(base/'stat',65536);f=first.rsplit(b') ',1)[1].split()
 need(f[19].decode()==t['starttime'] and int(f[1])==t['parent'] and int(f[2])==t['pgrp'] and f[0] not in (b'Z',b'X',b'x'),'exact target birth/parent/pgrp/state')
 fields=dict(line.split(':',1) for line in read(base/'status',65536).decode().splitlines() if ':' in line)
 need(fields['Uid'].split()==[str(t['uid'])]*4 and fields['Gid'].split()==[str(t['gid'])]*4 and fields['Threads'].strip()==str(t['threads']),'target root credentials/threads')
 need(read(base/'cmdline',65536)==base64.b64decode(t['cmdline_base64']) and os.readlink(base/'exe')==t['exe'],'exact target argv/executable')
 for number,dev,ino,path in [(t['root_lock_fd'],27,4,str(LOCK)),(t['mutex_fd'],p['preserved_regulars'][0]['full9']['device'],116297,p['preserved_regulars'][0]['path'])]:
  name=base/'fd'/str(number);meta=os.stat(name);need((meta.st_dev,meta.st_ino)==(dev,ino) and os.readlink(name)==path,'exact held FD differs')
 need(read(base/'stat',65536).rsplit(b') ',1)[1].split()[19].decode()==t['starttime'],'target birth raced')
 return dict(pid=t['pid'],starttime=t['starttime'],parent=t['parent'],pgrp=t['pgrp'],uid=t['uid'],gid=t['gid'])
def lock_holder(expected):
 selected=[]
 for line in read('/proc/locks').decode().splitlines():
  f=line.split()
  if '->' in f or len(f)!=8:continue
  dev=f[5].split(':')
  if len(dev)==3 and (int(dev[0],16),int(dev[1],16),int(dev[2]))==(0,27,4):selected.append(f[1:])
 need(selected==[['FLOCK','ADVISORY','WRITE',str(expected),'00:1b:4','0','EOF']],'sole27:4 holder differs')
 return selected
def preserved(p):
 rows=[]
 for item in p['preserved_regulars']:
  path=Path(item['path']);before=full9(os.lstat(path));fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   fd_before=full9(os.fstat(fd));need(stat.S_ISREG(fd_before['mode']) and before==fd_before==item['full9'],'preserved full9/regular mismatch')
   h=hashlib.sha256();count=0
   while True:
    b=os.read(fd,65536)
    if not b:break
    count+=len(b);need(count<=CAP,'protected file bound');h.update(b)
   need(h.hexdigest()==item['sha256'] and full9(os.fstat(fd))==fd_before==full9(os.lstat(path)),'preserved FD/hash drift')
   rows.append(item)
  finally:os.close(fd)
 for path in p['absent_paths']:need(not os.path.lexists(path),'preplan absentpath appeared')
 need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==p['boot_id'],'boot drift')
 return rows

def publish(base,name,value):
 raw=canonical(value);fd=os.open(str(base/name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  view=memoryview(raw)
  while view:
   n=os.write(fd,view);need(n>0,'shortwrite');view=view[n:]
  os.fsync(fd)
 finally:os.close(fd)
 fd=os.open(str(base),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
 return digest(raw)
def pidfd_bind(fd,p):
 t=identity_check(p);info=dict(line.split(':',1) for line in read('/proc/self/fdinfo/'+str(fd),65536).decode().splitlines() if ':' in line)
 need(info.get('Pid','').strip()==str(t['pid']),'pidfd target mismatch');return t
def replacement_lock():
 fd=os.open(str(LOCK),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd);need((s.st_dev,s.st_ino,s.st_uid,s.st_gid)==(27,4,0,0),'permanent rootlock mismatch')
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);return fd
 except BaseException:os.close(fd);raise

def uncertain_hold(base,lockfd,error):
 try:publish(base,'uncertain.json',dict(status='UNCERTAIN_RETIREMENT_HOLD',error_type=type(error).__name__,message=str(error)[:1024],no_retry=True))
 except BaseException:pass
 while True:
  if lockfd is None:
   try:lockfd=replacement_lock()
   except BaseException:pass
  try:time.sleep(60)
  except BaseException:pass

def main():
 a=argparse.ArgumentParser(allow_abbrev=False);a.add_argument('--release',required=True,type=Path);a.add_argument('--release-sha256',required=True);a.add_argument('--execute',action='store_true');args=a.parse_args()
 need(args.execute and os.getuid()==os.geteuid()==0 and os.uname().machine=='x86_64','explicit released root x86_64 execution required')
 need(resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1),'critical recovery requires inherited unlimited CPU time')
 raw=read(args.release);need(digest(raw)==args.release_sha256,'exact release hash');r=json.loads(raw);p=bound(r['profile'])
 need(r.get('schema')=='mckernel.current-quarantine-holder-retirement-release.v1' and r.get('status')=='PASS_EXECUTION_RELEASE' and type(r.get('execution_count')) is int and r['execution_count']==1 and r.get('signal_budget')==1,'exact one-shot release')
 need(r.get('fetched_source_verified') is True and re.fullmatch('[0-9a-f]{40}',str(r.get('source_checkpoint',''))),'source checkpoint required')
 need(r['source']['path']==str(Path(__file__).resolve()) and digest(read(r['source']['path']))==r['source']['sha256'],'source binding')
 need(r['profile']['path']==str(PROFILE) and p['target']['pid']==2575750 and p['target']['starttime']=='37684618','current profile only')
 need(bound(p['independent_held_state_acceptance']).get('reviewer'),'actual heldstate review')
 review=bound(r['execution_review']);payload={k:v for k,v in r.items() if k!='execution_review'}
 need(review.get('decision')=='PASS_EXECUTION' and review.get('implementation_ownership') is False and review.get('reviewer') and review['reviewer']!=r.get('author') and review.get('reviewed_release_payload_sha256')==digest(canonical(payload)),'independent exact execution review')
 base=Path(p['evidence_directory']);need(not os.path.lexists(base),'fresh evidence path required');base.mkdir(mode=0o700);pidfd=lockfd=None;attempted=complete=False
 previous=signal.pthread_sigmask(signal.SIG_BLOCK,DEFERRED)
 try:
  first=preserved(p);target=identity_check(p);lock_holder(target['pid'])
  libc=ctypes.CDLL(None,use_errno=True);ret=libc.syscall(434,ctypes.c_int(target['pid']),ctypes.c_uint(0));need(ret>=0,'pidfd_open failed');pidfd=int(ret)
  target=pidfd_bind(pidfd,p);second=preserved(p);lock_holder(target['pid']);need(first==second,'two pre-snapshots differ')
  prepared=publish(base,'prepared.json',dict(status='PREPARED_EXACT_PROCESS_RETIREMENT_ONLY',target=target,profile=r['profile'],release_sha256=args.release_sha256,preserved=first,signal_budget=1,cleanup_authorized=False))
  pidfd_bind(pidfd,p);lock_holder(target['pid']);attempted=True
  ret=libc.syscall(424,ctypes.c_int(pidfd),ctypes.c_int(signal.SIGKILL),ctypes.c_void_p(),ctypes.c_uint(0));need(ret==0,'sole pidfd signal uncertain/failed; no retry')
  poll=select.poll();poll.register(pidfd,select.POLLIN);need(bool(poll.poll(10000)),'pidfd exit not ready')
  deadline=time.monotonic()+10
  while True:
   try:
    state=read('/proc/'+str(target['pid'])+'/stat',65536).rsplit(b') ',1)[1].split()
    need(state[19].decode()==target['starttime'],'target PID reused after pidfd exit')
    need(time.monotonic()<deadline,'target not reaped within bound')
    time.sleep(0.01)
   except FileNotFoundError:break
  lockfd=replacement_lock();lock_holder(os.getpid());after=preserved(p);need(after==first,'post-retirement protected inputs changed')
  receipt=publish(base,'complete.json',dict(status='COMPLETE_IDLE_HOLDER_RETIREMENT_ONLY',target=target,signal_count=1,pidfd_exit_ready=True,replacement_root_lock=[27,4],prepared_sha256=prepared,release_sha256=args.release_sha256,protected_inputs_unchanged=True,quarantine_mutex_preserved=True,cleanup_authorized=False,fresh_preflight_eligible=False,original_critical_direct_join_receipt=None))
  complete=True;print(json.dumps(dict(status='COMPLETE_IDLE_HOLDER_RETIREMENT_ONLY',receipt=str(base/'complete.json'),receipt_sha256=receipt,cleanup_authorized=False,fresh_preflight_eligible=False),sort_keys=True))
 except BaseException as exc:
  if attempted and not complete:uncertain_hold(base,lockfd,exc)
  raise
 finally:
  if lockfd is not None and complete:os.close(lockfd)
  if pidfd is not None:os.close(pidfd)
  if not attempted or complete:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
if __name__=='__main__':main()
