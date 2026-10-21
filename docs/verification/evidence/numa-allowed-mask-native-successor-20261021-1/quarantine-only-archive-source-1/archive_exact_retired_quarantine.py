#!/usr/bin/env python3
"""One exact retired quarantine NOREPLACE archival; no engine or cleanup effects.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse,ctypes,fcntl,hashlib,json,os,re,resource,signal,stat,time
from pathlib import Path
D=Path(__file__).resolve().parent
PROFILE=D/'EXACT-QUARANTINE-ARCHIVE-PROFILE.json'
LOCK=Path('/run/lock/mckernel-development.lock')
CAP=1<<20
DEFERRED=(signal.SIGHUP,signal.SIGINT,signal.SIGTERM,signal.SIGQUIT)
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

def directory(path):
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  for part in path.parts[1:]:
   child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
  return fd
 except BaseException:os.close(fd);raise

def snapshot(item,fd=None,renamed=False):
 path=Path(item['path']);owned=fd is None
 if owned:fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=full9(os.fstat(fd));named=full9(os.lstat(path));need(before==named and stat.S_ISREG(before['mode']),'regular FD/named identity')
  keys=[k for k in before if not(renamed and k=='ctime_ns')];need(all(before[k]==item['full9'][k] for k in keys),'exact bound full9 drift')
  os.lseek(fd,0,os.SEEK_SET);h=hashlib.sha256();count=0
  while True:
   raw=os.read(fd,65536)
   if not raw:break
   count+=len(raw);need(count<=CAP,'bound regular exceeds1MiB');h.update(raw)
  need(count==before['size'] and h.hexdigest()==item['sha256'],'bound raw bytes drift')
  need(full9(os.fstat(fd))==before==full9(os.lstat(path)),'FD/named during-read drift')
  return dict(path=str(path),full9=before,sha256=h.hexdigest())
 finally:
  if owned:os.close(fd)
def stable_inputs(p):
 need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==p['boot_id'],'boot drift')
 for key in ['old_holder','old_outer']:need(not os.path.lexists('/proc/'+str(p[key]['pid'])),'original PID present/reused')
 rows=[snapshot(x) for x in p['unchanged_regulars']]
 for name in p['absent_paths']:need(not os.path.lexists(name),'preplan state appeared')
 return rows

def main():
 parser=argparse.ArgumentParser(allow_abbrev=False);parser.add_argument('--release',required=True,type=Path);parser.add_argument('--release-sha256',required=True);parser.add_argument('--execute',action='store_true');a=parser.parse_args()
 need(a.execute and os.getuid()==os.geteuid()==0,'released root archive invocation required');need(resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1),'critical inheritedCPU unlimited required')
 raw=read(a.release);need(digest(raw)==a.release_sha256,'actual releasefileSHA');r=json.loads(raw);p=bound(r['profile'])
 need(r.get('schema')=='mckernel.exact-retired-quarantine-archive-release.v1' and r.get('status')=='PASS_EXECUTION_RELEASE' and type(r.get('execution_count')) is int and r['execution_count']==1 and r.get('effect_count')==1,'one-effect exactrelease')
 need(r['source']['path']==str(Path(__file__).resolve()) and digest(read(r['source']['path']))==r['source']['sha256'] and r['profile']['path']==str(PROFILE),'source/profile binding')
 need(r.get('fetched_source_verified') is True and re.fullmatch('[0-9a-f]{40}',str(r.get('source_checkpoint',''))),'source checkpoint binding')
 review=bound(r['execution_review']);payload={k:v for k,v in r.items() if k!='execution_review'}
 need(review.get('decision')=='PASS_EXECUTION' and review.get('implementation_ownership') is False and review.get('reviewer') and review['reviewer']!=r.get('author') and review.get('reviewed_release_payload_sha256')==digest(canonical(payload)),'independent exactexecutionreview')
 retirement=bound(p['retirement_export']);need(retirement.get('status')=='PASS_READ_ONLY_TWO_RECEIPTS' and retirement['complete']['stable_full9'] and retirement['prepared']['stable_full9'],'positive exacttwofile export')
 need(retirement['complete']['sha256']==p['complete_sha256'] and retirement['prepared']['sha256']==p['prepared_sha256'],'exactretirement receipts')
 c=retirement['complete']['parsed_json'];need(c['status']=='COMPLETE_IDLE_HOLDER_RETIREMENT_ONLY' and c['pidfd_exit_ready'] and c['quarantine_mutex_preserved'] and c['protected_inputs_unchanged'],'positive holderretirement scope')
 outer=bound(p['original_critical_closed_status']);need(outer['pid']==p['old_outer']['pid'] and outer['proc_start_ticks']==p['old_outer']['starttime'] and outer['returncode']==-9 and outer['direct_child_joined'] and outer['process_group_absent'] and outer['streams_closed'],'original outer positiveclosure, failure preserved')
 need(r['retirement_actual_acceptance']==p['retirement_actual_acceptance'],'exact current actualretirement review required')
 accepted=bound(r['retirement_actual_acceptance']);need(accepted.get('implementation_ownership') is False and accepted.get('reviewer') and str(accepted.get('status','')).startswith('PASS'),'genuine actualretirement/state review')
 actor=dict(pid=os.getpid(),starttime=read('/proc/self/stat',65536).rsplit(b') ',1)[1].split()[19].decode(),uid=os.getuid(),gid=os.getgid(),pgrp=os.getpgrp(),boot_id=p['boot_id'])
 base=Path(p['evidence_directory']);need(not os.path.lexists(base),'fresh evidence namespace');base.mkdir(mode=0o700)
 rootfd=mfd=qfd=parent=None;attempted=complete=False;previous=signal.pthread_sigmask(signal.SIG_BLOCK,DEFERRED)
 try:
  rootfd=replacement_lock();first=stable_inputs(p);need(not os.path.lexists(p['destination']),'archive destination exists')
  mfd=os.open(p['mutex']['path'],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK);snapshot(p['mutex'],mfd);need(p['mutex']['full9']['inode']==116297 and p['mutex']['full9']['size']==0,'original emptymutex only');fcntl.flock(mfd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  source=Path(p['quarantine']['path']);destination=Path(p['destination']);need(source.parent==destination.parent and source.parent==Path('/home/holden/mckernel-work/scratch'),'same bound scratchparent')
  parent=directory(source.parent);need(os.fstat(parent).st_dev==p['quarantine']['full9']['device']==p['mutex']['full9']['device'],'same filesystem device')
  qfd=os.open(source.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);snapshot(p['quarantine'],qfd);need(p['quarantine']['full9']['inode']==116298 and p['quarantine']['full9']['size']==990,'exact retiredquarantine only')
  second=stable_inputs(p);need(first==second,'two stable protectedstate snapshots');snapshot(p['mutex'],mfd);snapshot(p['quarantine'],qfd);need(not os.path.lexists(destination),'destination appeared')
  prepared=publish(base,'prepared.json',dict(status='PREPARED_QUARANTINE_ONLY_ARCHIVAL',actor=actor,release_sha256=a.release_sha256,profile=r['profile'],source=p['quarantine'],destination=str(destination),preserved=first,effect_budget=1,cleanup_authorized=False))
  libc=ctypes.CDLL(None,use_errno=True);rename=getattr(libc,'renameat2',None);need(rename is not None,'qualified renameat2 unavailable');rename.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint];rename.restype=ctypes.c_int
  snapshot(p['quarantine'],qfd);snapshot(p['mutex'],mfd);attempted=True
  result=rename(parent,os.fsencode(source.name),parent,os.fsencode(destination.name),1);need(result==0,'soleNOREPLACE rename failed/uncertain, no retry')
  os.fsync(qfd);os.fsync(mfd);os.fsync(parent);need(not os.path.lexists(source),'originalquarantine name remains')
  archived=dict(p['quarantine'],path=str(destination));actual=snapshot(archived,qfd,renamed=True);need(actual['full9']['inode']==116298,'original quarantininode not retained')
  after=stable_inputs(p);need(after==first,'preservedinputs changed after archive');snapshot(p['mutex'],mfd)
  receipt=publish(base,'complete.json',dict(status='COMPLETE_QUARANTINE_ONLY_ARCHIVAL',actor=actor,release_sha256=a.release_sha256,prepared_sha256=prepared,rename_count=1,rename_flags=1,archived=actual,original_name_absent=True,mutex_preserved=p['mutex'],protected_inputs_unchanged=True,root_lock_identity=[27,4],cleanup_authorized=False,retained_mutex_preflight_accepted=False))
  complete=True;print(json.dumps(dict(status='COMPLETE_QUARANTINE_ONLY_ARCHIVAL',receipt=str(base/'complete.json'),receipt_sha256=receipt,cleanup_authorized=False,retained_mutex_preflight_accepted=False),sort_keys=True))
 except BaseException as exc:
  if attempted and not complete:uncertain_hold(base,rootfd,exc)
  raise
 finally:
  if not attempted or complete:
   for fd in [qfd,parent,mfd,rootfd]:
    if fd is not None:os.close(fd)
   signal.pthread_sigmask(signal.SIG_SETMASK,previous)
if __name__=='__main__':main()
