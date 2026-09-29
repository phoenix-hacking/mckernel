#!/usr/bin/env python3
"""DRAFT only: one future root retirement boundary, never an execution release.

The only authorized future invocation is `/usr/bin/sudo -A /usr/bin/python3
-E -s -B PACKET --release RELEASE`.  This packet itself never calls sudo or an
askpass program.  While any digest sentinel remains, it fails before euid,
Git, subprocess, output, Docker, observer, rename, or deletion activity.
"""
from __future__ import print_function
import argparse, ctypes, fcntl, hashlib, json, os, re, resource, select, signal, stat, struct, subprocess, sys, time, types
from pathlib import Path

SOURCE=Path('/home/holden/mckernel'); GIT=SOURCE/'.git'; IHK_GIT=GIT/'modules/ihk'
PACKET_REL='docs/verification/evidence/native-exact-candidate-retirement-67589154-1.py'
TEST_REL='scripts/tests/test_native_exact_candidate_retirement_67589154.py'
RELEASE_PATH='docs/verification/evidence/stability-native-exact-candidate-retirement-67589154-1.release.json'
RELEASE_SHA256='RELEASE_HASH_REQUIRED'
MAIN='675891545c881b8d625256ade56fe66ac69fe794'; IHK='3114d9e7101ad52030eb3effa849a5c108972a1f'
CANDIDATE='/dev/shm/mckernel-exact-candidate-67589154-1'; BACKUP='/dev/shm/mckernel-exact-metadata-backup-67589154-1'
QUARANTINES=('/dev/shm/.mckernel-retirement-candidate-67589154-1','/dev/shm/.mckernel-retirement-metadata-backup-67589154-1')
INVENTORY=SOURCE/'docs/verification/evidence/stability-native-exact-candidate-retention-67589154-20260929-2.inventory.json'
CAPSULE=SOURCE/'docs/verification/evidence/stability-native-exact-candidate-retention-67589154-20260929-2.tar'
SUCCESS=SOURCE/'docs/verification/evidence/stability-native-exact-retention-preparation-success-20260929-2.json'
INV_SHA='ce0c47f5a20e16216513c3ea6ef1dc7a72a9893e95bf1ae999a27217e90e1d10'; CAP_SHA='94fe0c364e6aaae5b280cc5d21b8e156cf3bb6d28804f1e529bcc378c4e712c8'; SUCCESS_SHA='e7fc78077ac612cfdd5eab53d8196260ec566fee72f1babbe1216ae1537bf8f2'
HELPER=SOURCE/'scripts/native_exact_candidate_retire.py'; OBSERVER=SOURCE/'docs/verification/evidence/native-exact-candidate-live-reference-observer-67589154-1.py'; ARCHIVE=SOURCE/'scripts/native_exact_candidate_retention_archive.py'
# Corrected owner/observer boundary is concurrently pending independent review.
HELPER_SHA256='7860b315247585f64df2adac7709b1d1405e553d884c08923501b1926a57226b'; OBSERVER_SHA256='3562b1d3d4e9a1e09cb7fa2be30f8e320923d50cf628b7f42314318702653666'; ARCHIVE_SHA256='6a28184e13e4ddec3a5e2fe6229c618929df29f235901083d55918c8291ac06e'; HELPER_TEST_SHA256='846ef1adb3bd1d39dd7dabe3a110a57c9470504ef82fc9170ff0c219aaa7f225'; OBSERVER_TEST_SHA256='b5f48e7b616f9ac517397455a1aebe0e13ce2a741388cf46046d0761adb922e4'
HELPER_TEST=SOURCE/'scripts/tests/test_native_exact_candidate_retire.py'; OBSERVER_TEST=SOURCE/'scripts/tests/test_native_exact_candidate_live_reference_observer_67589154.py'
FLOORS={'host':16<<30,'scratch':12<<30,'tmpfs':4<<30,'memory':4<<30}
OUT=('claim-67589154-1.json','journal-67589154-1.jsonl','evidence-67589154-1.json','packet.status','packet.status.pending','packet.failure','packet.failure.pending','helper.sealed.py','archive.sealed.py','observer.sealed.py','observer.stdout','observer.stderr','observer.status','docker-ps.stdout','docker-ps.stderr','docker-ps.status','docker-inspect.stdout','docker-inspect.stderr','docker-inspect.status','docker-ps-after.stdout','docker-ps-after.stderr','docker-ps-after.status')
RENAME_NOREPLACE=1
H40=re.compile(r'^[0-9a-f]{40}$'); H64=re.compile(r'^[0-9a-f]{64}$')
BUILD_LEASE=Path('/home/holden/mckernel-work/scratch/native-exact-build-lease-67589154-1.json')
EVIDENCE_PARENT=Path('/dev/shm')
EVIDENCE_DIR=EVIDENCE_PARENT/'.mckernel-retirement-evidence-67589154-1'
FS_IOC_GETFLAGS=0x80086601; FS_IOC_SETFLAGS=0x40086602; FS_IMMUTABLE_FL=0x00000010
CONFLICT_BASENAMES=('qemu-system-x86_64','qemu-kvm','qemu-system-aarch64','native_rust_exact_build_container_owner.py','native_exact_candidate_retire.py')
MAX_FILE=64<<20; MAX_CALLBACK=8<<20; COMMAND_TIMEOUT=180; TERM_TIMEOUT=5; KILL_TIMEOUT=5
class Error(RuntimeError): pass
class Interrupted(Error): pass
def bad(s): raise Error(s)
def sha(b): return hashlib.sha256(b).hexdigest()
def full_write(fd,data):
 at=0
 while at<len(data):
  try:n=os.write(fd,data[at:])
  except InterruptedError:continue
  if not isinstance(n,int) or n<=0 or n>len(data)-at:bad('short output write')
  at+=n
def exact_json(b):
 def pairs(rows):
  d={}
  for k,v in rows:
   if k in d: bad('duplicate JSON key: '+k)
   d[k]=v
  return d
 try:return json.loads(b.decode('utf8') if isinstance(b,bytes) else b,object_pairs_hook=pairs)
 except (ValueError,UnicodeError,TypeError) as e:bad('invalid JSON: '+str(e))
def draft_guard():
 if any(x.endswith('_REQUIRED') for x in (RELEASE_SHA256,HELPER_SHA256,OBSERVER_SHA256,ARCHIVE_SHA256,HELPER_TEST_SHA256,OBSERVER_TEST_SHA256)): bad('DRAFT_NOT_RELEASED')
 if not all(H64.fullmatch(x) for x in (RELEASE_SHA256,HELPER_SHA256,OBSERVER_SHA256,ARCHIVE_SHA256,HELPER_TEST_SHA256,OBSERVER_TEST_SHA256)):bad('invalid digest literal')
def stable_regular(path):
 try:
  before=os.lstat(str(path))
  if not stat.S_ISREG(before.st_mode):bad('not durable regular: '+str(path))
  fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0)|getattr(os,'O_NONBLOCK',0))
 except OSError as e:bad('cannot open durable file: '+str(e))
 try:
  opened=os.fstat(fd)
  if (opened.st_dev,opened.st_ino,opened.st_mode)!=(before.st_dev,before.st_ino,before.st_mode) or opened.st_size<0 or opened.st_size>MAX_FILE:bad('substituted before read')
  chunks=[]
  while True:
   try:b=os.read(fd,min(1<<20,MAX_FILE-sum(len(x) for x in chunks)+1))
   except BlockingIOError:bad('durable file would block')
   if not b:break
   chunks.append(b)
   if sum(len(x) for x in chunks)>MAX_FILE:bad('durable file oversize')
  after,named=os.fstat(fd),os.lstat(str(path))
  if (after.st_dev,after.st_ino,after.st_size,after.st_mode)!=(opened.st_dev,opened.st_ino,opened.st_size,opened.st_mode) or (named.st_dev,named.st_ino,named.st_size,named.st_mode)!=(after.st_dev,after.st_ino,after.st_size,after.st_mode):bad('substituted while read')
  return b''.join(chunks)
 finally:os.close(fd)
def checked(path,wanted):
 b=stable_regular(path)
 if sha(b)!=wanted:bad('hash mismatch: '+str(path))
 return b
def genv():return {'PATH':'/usr/bin:/bin','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0','GIT_ASKPASS':'/bin/false','GIT_OPTIONAL_LOCKS':'0','LC_ALL':'C'}
def gargv(directory,*a):return ['/usr/bin/git','--no-optional-locks','--git-dir='+str(directory),'--work-tree='+str(SOURCE),*a]
SYS_pidfd_open=434;SYS_pidfd_send_signal=424
def proc_row(pid):
 try:fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:raise
 except (OSError,IndexError,ValueError) as e:bad('process census unreadable: '+str(e))
 try:return {'pid':int(pid),'pgrp':int(fields[2]),'session':int(fields[3]),'starttime':int(fields[19])}
 except (IndexError,ValueError):bad('process census malformed')
def session_members(session):
 """Census the original session; each returned PID gets a pidfd before signal."""
 answer=[]
 try:names=os.listdir('/proc')
 except OSError as e:bad('process-group census unavailable: '+str(e))
 for name in names:
  if not name.isdigit():continue
  try:row=proc_row(int(name))
  except FileNotFoundError:continue
  if row['session']==session:answer.append(row)
 return answer
def group_members(pgid):return [x['pid'] for x in session_members(pgid)] # retained pure-test compatibility
def _syscall(number,*args):
 try:result=ctypes.CDLL(None,use_errno=True).syscall(number,*args)
 except AttributeError:bad('pidfd syscall unavailable')
 if result<0:
  e=ctypes.get_errno()
  if e==3:raise FileNotFoundError(e,os.strerror(e))
  bad('pidfd syscall failed: '+os.strerror(e))
 return result
def pidfd_open(pid):return _syscall(SYS_pidfd_open,pid,0)
def pidfd_send(fd,sig):_syscall(SYS_pidfd_send_signal,fd,sig,0,0)
def bind_process(p):
 """Record a born start-new-session leader before any wait can lose identity."""
 if not isinstance(getattr(p,'pid',None),int):return p # in-memory pure test double
 p._mckernel_session=p.pid;p._mckernel_leader_starttime=None
 try:row=proc_row(p.pid)
 except FileNotFoundError:
  # start_new_session guarantees the numeric session while alive.  A confirmed
  # immediate exit has no leader to inspect; later session census proves that
  # it did not leave a descendant behind.
  if p.poll() is not None:return p
  bad('new session leader disappeared without confirmed exit')
 if row['pgrp']!=p.pid or row['session']!=p.pid:bad('new session identity unavailable')
 p._mckernel_leader_starttime=row['starttime'];return p
def _drain(p,streams,limit,deadline):
 """Drain both callback pipes without an unbounded communicate buffer."""
 fds={}
 for k in ('stdout','stderr'):
  s=streams.get(k)
  if s is None:continue
  try:fds[s.fileno()]=k
  except (AttributeError,OSError):
   bad('callback pipe has no descriptor')
 while fds:
  left=deadline-time.monotonic()
  if left<=0:break
  try:ready=select.select(list(fds),[],[],min(left,.25))[0]
  except (OSError,ValueError) as e:bad('callback pipe select: '+str(e))
  if not ready:continue
  for fd in ready:
   try:block=os.read(fd,1<<16)
   except BlockingIOError:continue
   except OSError as e:bad('callback pipe read: '+str(e))
   if not block:del fds[fd];continue
   bucket=streams[fds[fd]+'_data']
   if len(bucket)+len(block)>limit:bad('callback output cap exceeded')
   bucket.extend(block)
 return bytes(streams['stdout_data']),bytes(streams['stderr_data'])
def retire_process(p,streams=None):
 """Retire every identity-proved original-session member via pidfd only."""
 streams=streams or {}
 if getattr(p,'_mckernel_retired',False) is True:return bytes(streams.get('stdout_data',b'')),bytes(streams.get('stderr_data',b''))
 if getattr(p,'_mckernel_retiring',False) is True:bad('concurrent process retirement')
 try:p._mckernel_retiring=True
 except BaseException:pass
 def shield(fn):
  while True:
   try:return fn()
   except (KeyboardInterrupt,Interrupted):continue # a second signal never skips retirement
 def collect(seconds):
  try:return shield(lambda:_drain(p,streams,MAX_CALLBACK,time.monotonic()+seconds))
  except Error:return bytes(streams.get('stdout_data',b'')),bytes(streams.get('stderr_data',b''))
 try:
  session=getattr(p,'_mckernel_session',None)
  if not isinstance(session,int) or session<=0:bad('process session was not recorded')
  def signal_session(sig):
   rows=session_members(session);errors=[]
   for row in rows:
    fd=None
    try:
     try:fd=pidfd_open(row['pid'])
     except FileNotFoundError:continue # ESRCH: this specific member exited
     try:again=proc_row(row['pid'])
     except FileNotFoundError:continue
     if again!=row or again['session']!=session:errors.append(Error('process identity changed during pidfd admission'));continue
     try:pidfd_send(fd,sig)
     except FileNotFoundError:continue
     except Error as e:errors.append(e)
    finally:
     if fd is not None:os.close(fd)
   if errors:raise errors[0]
   return bool(rows)
  errors=[]
  try:signal_session(signal.SIGTERM)
  except Error as e:errors.append(e)
  collect(TERM_TIMEOUT)
  if session_members(session):
   try:signal_session(signal.SIGKILL)
   except Error as e:errors.append(e)
   collect(KILL_TIMEOUT)
  if errors:raise errors[0]
  deadline=time.monotonic()+KILL_TIMEOUT
  while session_members(session):
   if time.monotonic()>=deadline:bad('uncertain child retirement')
   try:shield(lambda:p.wait(timeout=min(.1,deadline-time.monotonic())))
   except subprocess.TimeoutExpired:pass
   except TypeError:break # pure test double
  p._mckernel_retired=True
  return bytes(streams.get('stdout_data',b'')),bytes(streams.get('stderr_data',b''))
 finally:
  try:p._mckernel_retiring=False
  except BaseException:pass
def run_bounded(argv,timeout=60,cap=MAX_FILE):
 """Admission command with bounded wall time, output and process-group retirement."""
 p=None;streams={}
 try:
  p=bind_process(subprocess.Popen(argv,env=genv(),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True))
  streams={'stdout':p.stdout,'stderr':p.stderr,'stdout_data':bytearray(),'stderr_data':bytearray()}
  out,err=_drain(p,streams,cap,time.monotonic()+timeout)
  if p.poll() is None:out,err=retire_process(p,streams);bad('admission command timeout')
  if session_members(p._mckernel_session):retire_process(p,streams);bad('admission process group survived')
  if p.returncode:return out,err,p.returncode
  return out,err,0
 except (KeyboardInterrupt,Interrupted):
  if p is not None:retire_process(p,streams)
  raise
 except OSError as e:bad('admission command: '+str(e))
 except BaseException:
  if p is not None:retire_process(p,streams)
  raise
 finally:
  for stream in (streams.get('stdout'),streams.get('stderr')):
   if stream is not None:
    try:stream.close()
    except OSError:pass
def gout(directory,*a):
 out,err,rc=run_bounded(gargv(directory,*a))
 if rc:bad('Git admission: '+err.decode('utf8','replace'))
 return out
def gscalar(directory,*a):
 x=gout(directory,*a).decode('ascii','strict').strip()
 if not H40.fullmatch(x):bad('invalid Git scalar')
 return x
def blob(directory,commit,path):return gout(directory,'show',commit+':'+path)
def final_bytes(template,release_hash):
 old=b"RELEASE_SHA256='RELEASE_HASH_REQUIRED'"; new=b"RELEASE_SHA256='"+release_hash.encode('ascii')+b"'"
 if template.count(old)!=1:bad('release sentinel not unique')
 return template.replace(old,new)
def canonical_stores():
 if gscalar(GIT,'rev-parse',MAIN+'^{commit}')!=MAIN or gscalar(IHK_GIT,'rev-parse',IHK+'^{commit}')!=IHK:bad('canonical commit')
 if gout(GIT,'ls-tree',MAIN,'ihk').decode('ascii','strict').strip()!='160000 commit '+IHK+'\tihk':bad('IHK gitlink')
def _reader(directory):
 def limit():
  resource.setrlimit(resource.RLIMIT_AS,(512<<20,512<<20));resource.setrlimit(resource.RLIMIT_CPU,(900,900))
 p=bind_process(subprocess.Popen(gargv(directory,'cat-file','--batch'),env=genv(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0,preexec_fn=limit,start_new_session=True))
 try:os.set_blocking(p.stdin.fileno(),False);os.set_blocking(p.stdout.fileno(),False)
 except (AttributeError,OSError):pass # pure test doubles have no descriptor
 return p
def pipe_read(pipe,count,deadline):
 """No batch reader I/O is allowed to overrun the wall-clock deadline."""
 try:fd=pipe.fileno()
 except (AttributeError,OSError):return pipe.read(count) # pure in-memory test double
 while True:
  left=deadline-time.monotonic()
  if left<=0:bad('canonical reader wall timeout')
  if select.select([fd],[],[],min(left,1.0))[0]:
   try:return os.read(fd,count)
   except BlockingIOError:continue
def pipe_line(pipe,deadline):
 data=[]
 while True:
  b=pipe_read(pipe,1,deadline)
  if not b or b==b'\n':return b''.join(data)
  data.append(b)
  if len(data)>1024:bad('oversize canonical header')
def pipe_write(pipe,data,deadline):
 try:fd=pipe.fileno()
 except (AttributeError,OSError):pipe.write(data);pipe.flush();return
 at=0
 while at<len(data):
  left=deadline-time.monotonic()
  if left<=0:bad('canonical writer wall timeout')
  if not select.select([], [fd], [], min(left,1.0))[1]:continue
  try:n=os.write(fd,data[at:])
  except BlockingIOError:continue
  if n<=0:bad('canonical writer short write')
  at+=n
def finish_reader(p):
 try:
  try:rc=p.wait(timeout=5)
  except TypeError:return p.wait() # pure in-memory test double
 except subprocess.TimeoutExpired:rc=None
 if rc is not None:
  if session_members(getattr(p,'_mckernel_session',-1)):retire_process(p,{'stdout':getattr(p,'stdout',None),'stderr':getattr(p,'stderr',None),'stdout_data':bytearray(),'stderr_data':bytearray()});bad('canonical reader descendants survived')
  return rc
 streams={'stdout':getattr(p,'stdout',None),'stderr':getattr(p,'stderr',None),'stdout_data':bytearray(),'stderr_data':bytearray()}
 try:retire_process(p,streams)
 except Error:bad('uncertain canonical reader retirement')
 try:return p.wait(timeout=5)
 except (subprocess.TimeoutExpired,TypeError):bad('uncertain canonical reader retirement')
def stream_blob_process(p,oid,wanted,size,alternate,deadline):
 """One record from a long-lived batch reader, never buffering a blob."""
 if not H40.fullmatch(oid) or not H64.fullmatch(wanted) or not H64.fullmatch(alternate) or not isinstance(size,int) or size<0:bad('malformed blob record')
 if time.monotonic()>deadline:bad('canonical reader deadline')
 try:
  pipe_write(p.stdin,(oid+'\n').encode('ascii'),deadline); h=pipe_line(p.stdout,deadline).decode('ascii','strict').strip().split()
  if len(h)!=3 or h[0]!=oid or h[1]!='blob' or not h[2].isdigit() or int(h[2])!=size:bad('blob header/type/size')
  left=size; d=hashlib.sha256(); obj=hashlib.sha256(('blob '+str(size)+'\0').encode('ascii'))
  while left:
   if time.monotonic()>deadline:bad('canonical reader deadline')
   b=pipe_read(p.stdout,min(1<<20,left),deadline)
   if not b:bad('short blob')
   d.update(b);obj.update(b);left-=len(b)
  if pipe_read(p.stdout,1,deadline)!=b'\n':bad('blob terminator')
 except (OSError,UnicodeError) as e:bad('blob stream: '+str(e))
 if d.hexdigest()!=wanted or obj.hexdigest()!=alternate:bad('blob digest/object id')
def stream_blob(directory,oid,wanted,size,alternate=None):
 """Testable one-record wrapper; production uses stream_store below."""
 if alternate is None:alternate=hashlib.sha256(('blob '+str(size)+'\0').encode('ascii')+b'abc').hexdigest()
 p=None
 try:
  p=_reader(directory);stream_blob_process(p,oid,wanted,size,alternate,time.monotonic()+900)
  p.stdin.close();p.stdout.close()
  if finish_reader(p)!=0:bad('blob reader exit')
 except (OSError,UnicodeError) as e:bad('blob stream: '+str(e))
 finally:
  if p is not None and p.poll() is None:finish_reader(p)
def stream_store(directory,records):
 p=None
 try:
  p=_reader(directory);deadline=time.monotonic()+900
  for oid,wanted,size,alternate in records:stream_blob_process(p,oid,wanted,size,alternate,deadline)
  p.stdin.close();p.stdout.close()
  if finish_reader(p)!=0:bad('canonical reader exit')
 finally:
  if p is not None and p.poll() is None:finish_reader(p)
def verify_inventory(inv):
 if not isinstance(inv,dict) or inv.get('revisions')!={'main':MAIN,'ihk':IHK} or not isinstance(inv.get('entries'),list):bad('inventory revision/entries')
 main=[];ihk=[]
 for r in inv['entries']:
  if not isinstance(r,dict) or r.get('classification')!='reconstructible' or r.get('type') not in ('regular','symlink'):continue
  ids=r.get('git_oids')
  if not isinstance(ids,dict):bad('reconstructible oid')
  (ihk if r.get('path','').startswith('ihk/') else main).append((ids.get('sha1',''),r.get('sha256',''),r.get('size'),ids.get('sha256','')))
 stream_store(GIT,main);stream_store(IHK_GIT,ihk)
def mechanical(release,fetched):
 t=release.get('template');f=release.get('finalization')
 if not isinstance(t,dict) or not isinstance(f,dict) or not H40.fullmatch(t.get('commit','')) or f.get('prior_ancestor')!=t['commit']:bad('template ancestor')
 if f.get('allowed_changed_paths')!=[PACKET_REL,RELEASE_PATH]:bad('allowed changed paths')
 if run_bounded(gargv(GIT,'merge-base','--is-ancestor',t['commit'],fetched))[2]!=0:bad('template not ancestor')
 if gout(GIT,'diff','--name-only',t['commit'],fetched).decode('utf8','strict').splitlines()!=[PACKET_REL,RELEASE_PATH]:bad('nonmechanical changed path')
 template=blob(GIT,t['commit'],PACKET_REL)
 if sha(template)!=t.get('packet_sha256') or sha(blob(GIT,t['commit'],TEST_REL))!=t.get('test_sha256'):bad('template hash')
 if blob(GIT,t['commit'],TEST_REL)!=blob(GIT,fetched,TEST_REL) or blob(GIT,fetched,PACKET_REL)!=final_bytes(template,RELEASE_SHA256) or stable_regular(SOURCE/PACKET_REL)!=final_bytes(template,RELEASE_SHA256):bad('nonmechanical finalization')
def root(ino,size):return {'device':26,'inode':ino,'uid':1000,'gid':1000,'mode':0o755,'kind':'directory','size':size}
def free_bytes(path):
 s=os.statvfs(path);return s.f_bavail*s.f_frsize
def raw_starttime(pid):return int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
def proc_starttime(pid):
 try:return raw_starttime(pid)
 except (OSError,IndexError,ValueError):bad('launcher identity unavailable')
def proc_cmdline_stable(pid):
 """Only a confirmed disappearance is ignorable; every other /proc fault blocks."""
 try:before=raw_starttime(pid)
 except FileNotFoundError:return None
 except (OSError,IndexError,ValueError) as e:bad('proc identity unreadable: '+str(e))
 try:cmd=(Path('/proc')/str(pid)/'cmdline').read_bytes()
 except FileNotFoundError:
  try:raw_starttime(pid)
  except FileNotFoundError:return None
  except (OSError,IndexError,ValueError) as e:bad('proc disappearance unresolved: '+str(e))
  bad('proc identity replaced')
 except OSError as e:bad('proc cmdline unreadable: '+str(e))
 try:after=raw_starttime(pid)
 except FileNotFoundError:bad('proc disappeared during census')
 except (OSError,IndexError,ValueError) as e:bad('proc identity unreadable: '+str(e))
 if before!=after:bad('proc identity replaced')
 return cmd
def live_gate(r,held_lease,output):
 """All mutable names stay absent until these exact live prerequisites hold."""
 floors={'host':free_bytes('/home'),'scratch':free_bytes('/home/holden/mckernel-work/scratch'),'tmpfs':free_bytes('/dev/shm'),'memory':os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_AVPHYS_PAGES')}
 if any(floors[k]<FLOORS[k] for k in FLOORS):bad('resource floor')
 try:boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 except OSError:bad('boot id unavailable')
 if boot!=r['boot_id']:bad('current boot mismatch')
 for row in r['launcher_identities']:
  if not isinstance(row,dict) or not isinstance(row.get('pid'),int) or not isinstance(row.get('starttime'),int) or proc_starttime(row['pid'])!=row['starttime']:bad('launcher identity mismatch')
 if r.get('conflict_basenames')!=list(CONFLICT_BASENAMES) or r.get('operational_exclusion')!=str(BUILD_LEASE) or not isinstance(r.get('heavy_lease_paths'),list) or r['operational_exclusion'] not in r['heavy_lease_paths'] or len(set(r['heavy_lease_paths']))!=len(r['heavy_lease_paths']):bad('process/lease release binding')
 held_lease.assert_held()
 for lease in r['heavy_lease_paths']:
  if not isinstance(lease,str):bad('active heavy lease')
  if lease==r['operational_exclusion']:continue
  if os.path.lexists(lease):bad('active heavy lease')
 for q in QUARANTINES:
  if os.path.lexists(q):bad('quarantine already exists')
 if not isinstance(output,OutputDir) or output.path!=Path(r['output_dir']):bad('output descriptor binding')
 output.assert_fresh()
 protected={x['pid'] for x in r['launcher_identities']}
 for name in os.listdir('/proc'):
  if not name.isdigit() or int(name) in protected:continue
  cmd=proc_cmdline_stable(int(name))
  if cmd is None:continue
  argv=cmd.split(b'\0');names={os.path.basename(x.decode('utf8','surrogateescape')) for x in argv if x}
  if names.intersection(CONFLICT_BASENAMES):bad('operational exclusion conflict')
 output.assert_fresh();held_lease.assert_held()
def validate_release(r,fetched,inv):
 keys={'schema','status','one_shot','retry','rollback','main_commit','ihk_commit','candidate','metadata_backup','inventory_sha256','capsule_sha256','success_sha256','source_hashes','roots','sealed','observer','docker','boot_id','launcher_identities','operational_exclusion','exclusion_tombstone','conflict_basenames','heavy_lease_paths','resource_floors','output_dir','evidence_namespace','template','finalization'}
 if not isinstance(r,dict) or set(r)!=keys:bad('release keys')
 if (r['schema'],r['status'],r['one_shot'],r['retry'],r['rollback'])!=('mckernel.ordinary-retirement-release.v1','PASS_ONE_SHOT_RETIRE',True,False,False):bad('one-shot/retry/rollback')
 if (r['main_commit'],r['ihk_commit'],r['candidate'],r['metadata_backup'])!=(MAIN,IHK,CANDIDATE,BACKUP) or (r['inventory_sha256'],r['capsule_sha256'],r['success_sha256'])!=(INV_SHA,CAP_SHA,SUCCESS_SHA):bad('identity/evidence')
 if r['source_hashes']!={'helper':HELPER_SHA256,'observer':OBSERVER_SHA256,'archive':ARCHIVE_SHA256,'helper_test':HELPER_TEST_SHA256,'observer_test':OBSERVER_TEST_SHA256}:bad('support hashes')
 if not isinstance(r['roots'],list) or len(r['roots'])!=2:bad('roots')
 for x,path,q in zip(r['roots'],(CANDIDATE,BACKUP),QUARANTINES):
  live=x.get('root') if isinstance(x,dict) else None
  rowkeys={'path','root','parent','members','quarantine_name','quarantine_uid','quarantine_gid','quarantine_mode'}
  rootkeys={'device','inode','uid','gid','mode','kind','size'}
  if not isinstance(x,dict) or set(x)!=rowkeys or x.get('path')!=path or not isinstance(live,dict) or set(live)!=rootkeys or not isinstance(live.get('device'),int) or live['device']<0 or not isinstance(live.get('inode'),int) or live['inode']<=0 or any(live.get(k)!=v for k,v in (('uid',1000),('gid',1000),('mode',0o755),('kind','directory'))) or not isinstance(live.get('size'),int) or live['size']<0 or not isinstance(x.get('parent'),dict) or set(x['parent'])!=rootkeys or not isinstance(x.get('members'),list):bad('root/parent/member map')
  if (x.get('quarantine_name'),x.get('quarantine_uid'),x.get('quarantine_gid'),x.get('quarantine_mode'))!=(q.rsplit('/',1)[1],0,0,0o700):bad('quarantine owner distinction')
 # The preparation inventory is the independent coverage authority; helper
 # records additionally carry live device/inode identities for every member.
 inv_roots={x.get('name'):x for x in inv.get('roots',[]) if isinstance(x,dict)}
 for released,label in zip(r['roots'],('candidate','metadata-backup')):
  ir=inv_roots.get(label);expected=[x for x in inv['entries'] if x.get('root')==label]
  if not isinstance(ir,dict) or ir.get('path')!=released['path'] or ir.get('identity')!={'dev':released['root']['device'],'inode':released['root']['inode'],'uid':1000,'gid':1000,'mode':0o755}:bad('inventory root identity')
  got={x.get('path'):x for x in released['members'] if isinstance(x,dict)}
  if len(got)!=len(released['members']) or set(got)!={x.get('path') for x in expected}:bad('inventory full member map')
  for e in expected:
   m=got[e['path']];typ={'regular':'file','directory':'directory','symlink':'symlink'}.get(e.get('type'));memberkeys={'device','inode','uid','gid','mode','kind','size','path'}|({'sha256'} if typ=='file' else {'sha256','target'} if typ=='symlink' else set())
   if not isinstance(m,dict) or set(m)!=memberkeys or m.get('kind')!=typ or any(m.get(k)!=e.get(k) for k in ('path','uid','gid','mode','size')) or (typ=='file' and m.get('sha256')!=e.get('sha256')) or (typ=='symlink' and (m.get('target')!=e.get('target') or m.get('sha256')!=sha(os.fsencode(e.get('target',''))))):bad('inventory member binding')
 if not all(isinstance(r[k],dict) for k in ('sealed','observer','docker','exclusion_tombstone','evidence_namespace')) or not isinstance(r['boot_id'],str) or not r['boot_id'] or not isinstance(r['launcher_identities'],list) or not r['launcher_identities'] or not isinstance(r['operational_exclusion'],str) or not r['operational_exclusion'] or r['resource_floors']!=FLOORS or r['output_dir']!=str(EVIDENCE_DIR):bad('runtime release binding')
 seal=r['sealed'];needed=('retention_manifest_sha256','retention_manifest_pushed_sha256','retention_manifest_fetched_sha256','capsule_sha256','capsule_pushed_sha256','capsule_fetched_sha256','retention_manifest_path','capsule_path')
 if set(seal)!=set(needed) or any(not H64.fullmatch(seal[k]) for k in needed[:6]) or seal['retention_manifest_path']!=str(INVENTORY) or seal['capsule_path']!=str(CAPSULE) or any(seal[k]!=INV_SHA for k in needed[:3]) or any(seal[k]!=CAP_SHA for k in needed[3:6]):bad('helper sealed preflight')
 if r['observer'].get('observer_sha256')!=OBSERVER_SHA256 or r['observer'].get('boot_id')!=r['boot_id']:bad('helper observer preflight')
 terminal='decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9'
 if r['operational_exclusion']!=str(BUILD_LEASE) or r['heavy_lease_paths']!=[str(BUILD_LEASE)]:bad('shared build lease binding')
 tomb=r['exclusion_tombstone']
 if set(tomb)!={'path','immutable','schema','parent_uid','parent_gid','parent_mode','filesystem_device'} or tomb.get('path')!=str(BUILD_LEASE) or tomb.get('immutable') is not True or tomb.get('schema')!='mckernel.retirement-build-owner-exclusion.v2' or (tomb.get('parent_uid'),tomb.get('parent_gid'),tomb.get('parent_mode'))!=(1000,1000,0o700) or not isinstance(tomb.get('filesystem_device'),int) or tomb['filesystem_device']<0:bad('shared immutable tombstone binding')
 namespace=r['evidence_namespace']
 if set(namespace)!={'parent','name','device','uid','gid','mode','sticky'} or namespace.get('parent')!=str(EVIDENCE_PARENT) or namespace.get('name')!=EVIDENCE_DIR.name or not isinstance(namespace.get('device'),int) or namespace['device']<0 or (namespace.get('uid'),namespace.get('gid'),namespace.get('mode'),namespace.get('sticky'))!=(0,0,0o1777,True):bad('sticky evidence namespace binding')
 if not isinstance(r['docker'].get('terminal'),dict) or r['docker']['terminal'].get('id')!=terminal or not isinstance(r['docker'].get('terminal_containers'),dict):bad('helper Docker preflight')
 mechanical(r,fetched);canonical_stores();verify_inventory(inv)
def admit(release_arg):
 draft_guard()
 if os.geteuid()!=0:bad('root euid required')
 canonical=SOURCE/RELEASE_PATH
 if Path(release_arg)!=canonical:bad('release argument must be canonical')
 head,up,fetch=(gscalar(GIT,'rev-parse',x) for x in ('HEAD','@{upstream}','FETCH_HEAD'))
 if head!=fetch or up!=fetch:bad('HEAD/upstream/FETCH_HEAD mismatch')
 raw=blob(GIT,fetch,RELEASE_PATH)
 if sha(raw)!=RELEASE_SHA256 or stable_regular(canonical)!=raw:bad('release fetched blob')
 inv=exact_json(checked(INVENTORY,INV_SHA));checked(CAPSULE,CAP_SHA);success=exact_json(checked(SUCCESS,SUCCESS_SHA))
 if success.get('status')!='PASS_PREPARATION_EVIDENCE_ONLY':bad('preparation success')
 r=exact_json(raw);validate_release(r,fetch,inv)
 sources={'helper':checked(HELPER,HELPER_SHA256),'observer':checked(OBSERVER,OBSERVER_SHA256),'archive':checked(ARCHIVE,ARCHIVE_SHA256)}
 for p,h in ((HELPER_TEST,HELPER_TEST_SHA256),(OBSERVER_TEST,OBSERVER_TEST_SHA256)):checked(p,h)
 return r,sources
class OutputDir(object):
 """A root-owned sticky-/dev/shm child, used only through its retained fd."""
 def __init__(self,path):
  self.path=Path(path);self.parent=self.path.parent;self.parent_fd=os.open(str(self.parent),os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_DIRECTORY',0)|getattr(os,'O_CLOEXEC',0));self.parent_identity=os.fstat(self.parent_fd)
  self.fd=os.open(self.path.name,os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_DIRECTORY',0)|getattr(os,'O_CLOEXEC',0),dir_fd=self.parent_fd);self.identity=os.fstat(self.fd)
 def __truediv__(self,name):
  if not isinstance(name,str) or not name or '/' in name or name in ('.','..'):bad('unsafe output member')
  return self.path/name
 def assert_fresh(self):
  try:named=os.lstat(str(self.path));opened=os.fstat(self.fd)
  except OSError as e:bad('fresh output unavailable: '+str(e))
  parent_named=os.stat(str(self.parent),follow_symlinks=False);parent_open=os.fstat(self.parent_fd)
  if (parent_named.st_dev,parent_named.st_ino,parent_named.st_mode,parent_named.st_uid,parent_named.st_gid)!=(parent_open.st_dev,parent_open.st_ino,parent_open.st_mode,parent_open.st_uid,parent_open.st_gid) or (parent_open.st_dev,parent_open.st_ino)!=(self.parent_identity.st_dev,self.parent_identity.st_ino):bad('evidence parent substituted')
  if not stat.S_ISDIR(opened.st_mode) or stat.S_IMODE(opened.st_mode)!=0o700 or opened.st_uid!=os.geteuid() or opened.st_gid!=os.getegid() or (named.st_dev,named.st_ino,named.st_mode,named.st_uid,named.st_gid)!=(opened.st_dev,opened.st_ino,opened.st_mode,opened.st_uid,opened.st_gid) or (opened.st_dev,opened.st_ino)!=(self.identity.st_dev,self.identity.st_ino):bad('fresh output substituted')
  try:entries=os.listdir(self.fd)
  except OSError as e:bad('fresh output unreadable: '+str(e))
  if entries:bad('fresh output nonempty')
 def write(self,name,data):
  self.assert_bound()
  if name not in OUT:bad('unreleased capture')
  try:fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0),0o600,dir_fd=self.fd)
  except OSError as e:bad('exclusive output capture: '+str(e))
  try:full_write(fd,data);os.fsync(fd);actual=os.fstat(fd)
  finally:os.close(fd)
  named=os.stat(name,dir_fd=self.fd,follow_symlinks=False)
  if not stat.S_ISREG(actual.st_mode) or actual.st_nlink!=1 or (named.st_dev,named.st_ino,named.st_size,named.st_mode,named.st_uid)!=(actual.st_dev,actual.st_ino,actual.st_size,actual.st_mode,actual.st_uid) or actual.st_size!=len(data):bad('output capture substituted')
  os.fsync(self.fd);self.assert_bound()
 def exists(self,name):
  if not isinstance(name,str) or '/' in name or name in ('','.','..'):bad('unsafe output member')
  try:os.stat(name,dir_fd=self.fd,follow_symlinks=False);return True
  except FileNotFoundError:return False
 def assert_bound(self):
  """Revalidate the namespace after mutation without requiring emptiness."""
  try:named=os.lstat(str(self.path));opened=os.fstat(self.fd)
  except OSError as e:bad('output unavailable: '+str(e))
  if (named.st_dev,named.st_ino,named.st_mode,named.st_uid,named.st_gid)!=(opened.st_dev,opened.st_ino,opened.st_mode,opened.st_uid,opened.st_gid) or (opened.st_dev,opened.st_ino)!=(self.identity.st_dev,self.identity.st_ino):bad('output substituted')
 def close(self):
  if self.fd is not None:os.close(self.fd);self.fd=None
  if self.parent_fd is not None:os.close(self.parent_fd);self.parent_fd=None
def fresh_output(r):
 p=Path(r['output_dir'])
 if p!=EVIDENCE_DIR or p.exists():bad('fresh root-owned evidence output')
 try:parent=os.lstat(str(EVIDENCE_PARENT))
 except OSError as e:bad('sticky evidence parent unavailable: '+str(e))
 namespace=r.get('evidence_namespace',{})
 if not stat.S_ISDIR(parent.st_mode) or parent.st_uid!=0 or parent.st_gid!=0 or stat.S_IMODE(parent.st_mode)!=0o1777 or not (parent.st_mode&stat.S_ISVTX) or namespace.get('device')!=parent.st_dev:bad('sticky evidence parent identity')
 fd=os.open(str(EVIDENCE_PARENT),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0))
 try:
  opened=os.fstat(fd)
  if (opened.st_dev,opened.st_ino,opened.st_mode,opened.st_uid,opened.st_gid)!=(parent.st_dev,parent.st_ino,parent.st_mode,parent.st_uid,parent.st_gid):bad('sticky evidence parent substituted')
  os.mkdir(p.name,0o700,dir_fd=fd);os.chown(p.name,0,0,dir_fd=fd,follow_symlinks=False);os.fsync(fd)
 finally:os.close(fd)
 out=OutputDir(p)
 try:out.assert_fresh();return out
 except BaseException:out.close();raise
class ExclusionLease(object):
 """The exact build-owner O_EXCL lease; its durable tombstone is never removed."""
 def __init__(self,release):self.release=release;self.fd=None;self.identity=None
 def __enter__(self):
  path=BUILD_LEASE
  if self.release.get('operational_exclusion')!=str(path):bad('shared build lease binding')
  self.fd=os.open(str(path),os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  try:
   parent=os.stat(str(path.parent),follow_symlinks=False)
   tomb=self.release.get('exclusion_tombstone',{})
   if not stat.S_ISDIR(parent.st_mode) or (parent.st_uid,parent.st_gid,stat.S_IMODE(parent.st_mode))!=(tomb.get('parent_uid'),tomb.get('parent_gid'),tomb.get('parent_mode')) or tomb.get('filesystem_device')!=parent.st_dev:bad('legacy owner lease parent identity')
   record={'schema':'mckernel.retirement-build-owner-exclusion.v2','release_sha256':RELEASE_SHA256,'boot_id':self.release['boot_id'],'pid':os.getpid(),'starttime':proc_starttime(os.getpid()),'operational_exclusion':str(path),'state':'retirement-owned-immutable-one-shot-tombstone','immutable':True,'filesystem_device':parent.st_dev}
   self.data=(json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode('utf8');full_write(self.fd,self.data);os.fsync(self.fd);self.identity=os.fstat(self.fd)
   # execute() admits only euid 0; using euid here keeps this descriptor check
   # testable in an unprivileged model without changing production ownership.
   if self.identity.st_uid!=os.geteuid() or self.identity.st_gid!=os.getegid() or stat.S_IMODE(self.identity.st_mode)!=0o600 or self.identity.st_nlink!=1 or self.identity.st_dev!=parent.st_dev:bad('shared lease identity')
   self._make_immutable();self.assert_held();fsync_parent(path);return self
  except BaseException:
   os.close(self.fd);self.fd=None;raise
 def assert_held(self):
  if self.fd is None:bad('operational exclusion lease absent')
  named=os.lstat(str(BUILD_LEASE));opened=os.fstat(self.fd)
  if (named.st_dev,named.st_ino,named.st_size,named.st_uid,named.st_gid,stat.S_IMODE(named.st_mode))!=(opened.st_dev,opened.st_ino,opened.st_size,opened.st_uid,opened.st_gid,stat.S_IMODE(opened.st_mode)) or (opened.st_dev,opened.st_ino,opened.st_size)!=(self.identity.st_dev,self.identity.st_ino,self.identity.st_size) or opened.st_uid!=os.geteuid() or opened.st_gid!=os.getegid() or stat.S_IMODE(opened.st_mode)!=0o600 or opened.st_nlink!=1 or self._flags()&FS_IMMUTABLE_FL==0:bad('operational exclusion lease replaced or mutable')
  os.lseek(self.fd,0,os.SEEK_SET)
  if stable_fd(self.fd,opened.st_size)!=self.data:bad('operational exclusion lease content changed')
 def _flags(self):
  buf=bytearray(4)
  try:fcntl.ioctl(self.fd,FS_IOC_GETFLAGS,buf,True)
  except OSError as e:bad('immutable lease flags unavailable: '+str(e))
  return struct.unpack('I',bytes(buf))[0]
 def _make_immutable(self):
  flags=self._flags()
  try:fcntl.ioctl(self.fd,FS_IOC_SETFLAGS,struct.pack('I',flags|FS_IMMUTABLE_FL))
  except OSError as e:bad('immutable lease set failed: '+str(e))
  if self._flags()&FS_IMMUTABLE_FL==0:bad('immutable lease flag not latched')
 def finalize(self):
  """A PASS may follow only a closed and freshly reopened immutable inode."""
  self.assert_held();os.fsync(self.fd);os.close(self.fd);self.fd=None
  fd=os.open(str(BUILD_LEASE),os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0))
  try:
   self.fd=fd;self.assert_held();os.fsync(fd)
  finally:
   if self.fd is not None:os.close(self.fd);self.fd=None
 def __exit__(self,*unused):
  if self.fd is not None:os.fsync(self.fd);os.close(self.fd);self.fd=None
def stable_fd(fd,size):
 if not isinstance(size,int) or size<0 or size>MAX_FILE:bad('lease size')
 a=[];left=size
 while left:
  b=os.read(fd,min(1<<20,left))
  if not b:bad('lease short read')
  a.append(b);left-=len(b)
 if os.read(fd,1):bad('lease grew')
 return b''.join(a)
def fsync_parent(path):
 fd=os.open(str(Path(path).parent),os.O_RDONLY|getattr(os,'O_DIRECTORY',0)|getattr(os,'O_CLOEXEC',0))
 try:os.fsync(fd)
 finally:os.close(fd)
def capture(base,name,data):
 if not isinstance(base,OutputDir):bad('descriptor-bound output required')
 base.write(name,data)
def rename_noreplace_at(dirfd,old,new):
 fn=getattr(ctypes.CDLL(None,use_errno=True),'renameat2',None)
 if fn is None:bad('renameat2 unavailable')
 fn.argtypes=(ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint);fn.restype=ctypes.c_int
 if fn(dirfd,os.fsencode(old),dirfd,os.fsencode(new),RENAME_NOREPLACE):
  e=ctypes.get_errno();bad('terminal status rename: '+os.strerror(e))
def status(base,value,success=False):
 """Publish exactly once; a pending file is never a canonical terminal state."""
 final,pending=('packet.status','packet.status.pending') if success else ('packet.failure','packet.failure.pending')
 if success and (base.exists('packet.status') or base.exists('packet.failure')):bad('canonical terminal status exists')
 if base.exists(pending):bad('terminal pending status exists')
 capture(base,pending,(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('utf8'))
 renamed=False
 try:
  rename_noreplace_at(base.fd,pending,final);renamed=True;os.fsync(base.fd);base.assert_bound()
 except BaseException:
  # A renamed but non-durable PASS is never authoritative: remove only the
  # name we just created, never a pre-existing terminal record.
  if renamed:
   try:os.unlink(final,dir_fd=base.fd);os.fsync(base.fd)
   except OSError:pass
  raise
def call(argv,base,stem,pass_fds=()):
 """One callback attempt.  Timeout retires its whole new process group."""
 p=None;streams={};out=err=b'';rc=125;interrupted=None;cleanup_error=None
 def safe_retire():
  try:return retire_process(p,streams),None
  except BaseException as e:return (bytes(streams.get('stdout_data',b'')),bytes(streams.get('stderr_data',b''))),e
 try:
  p=bind_process(subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,pass_fds=tuple(pass_fds)))
  streams={'stdout':p.stdout,'stderr':p.stderr,'stdout_data':bytearray(),'stderr_data':bytearray()}
  out,err=_drain(p,streams,MAX_CALLBACK,time.monotonic()+COMMAND_TIMEOUT)
  if p.poll() is None:
   (out,err),cleanup_error=safe_retire();rc=124
  elif session_members(p._mckernel_session):
   (out,err),cleanup_error=safe_retire();rc=125
  else:rc=p.returncode
 except (KeyboardInterrupt,Interrupted) as e:
  interrupted=e
  if p is not None:(out,err),cleanup_error=safe_retire()
  else:err=str(e).encode('utf8','replace')
 except BaseException as e:
  if p is not None:(out,err),cleanup_error=safe_retire()
  else:err=str(e).encode('utf8','replace')
 for stream in (streams.get('stdout'),streams.get('stderr')):
  if stream is not None:
   try:stream.close()
   except OSError:pass
 capture(base,stem+'.stdout',out);capture(base,stem+'.stderr',err);capture(base,stem+'.status',(str(rc)+'\n').encode('ascii'))
 if interrupted is not None:raise interrupted
 if cleanup_error is not None:raise Error(stem+' cleanup failed: '+repr(cleanup_error))
 if rc:bad(stem+' callback failed')
 return out
def observer_callback(base,lease,observer_path):
 fd=observer_path
 if not isinstance(fd,int) or fd<0:bad('sealed observer descriptor')
 argv=['/usr/bin/python3','-E','-s','-B','/proc/self/fd/'+str(fd),'--target',QUARANTINES[0],'--target',QUARANTINES[1]]
 def run(targets,members):
  lease.assert_held()
  if list(targets)!=list(QUARANTINES):bad('helper supplied observer targets')
  x=exact_json(call(argv,base,'observer',(fd,)))
  if not isinstance(x,dict):bad('observer JSON object')
  return x
 return run
def docker_callback(base,docker,lease):
 def run():
  lease.assert_held()
  ids=call(['/usr/bin/docker','ps','--all','--quiet','--no-trunc'],base,'docker-ps').decode('ascii','strict').splitlines()
  if len(ids)!=len(set(ids)) or any(not H64.fullmatch(x) for x in ids):bad('Docker identifiers')
  if ids:rows=exact_json(call(['/usr/bin/docker','inspect',*ids],base,'docker-inspect'))
  else: rows=[];capture(base,'docker-inspect.stdout',b'[]');capture(base,'docker-inspect.stderr',b'');capture(base,'docker-inspect.status',b'0\n')
  if not isinstance(rows,list) or len(rows)!=len(ids) or {x.get('Id') for x in rows if isinstance(x,dict)}!=set(ids):bad('Docker omission/churn')
  after=call(['/usr/bin/docker','ps','--all','--quiet','--no-trunc'],base,'docker-ps-after').decode('ascii','strict').splitlines()
  if after!=ids:bad('Docker churn after inspect')
  terminals=docker.get('terminal_containers') if isinstance(docker,dict) else None
  want={'decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9','8943e49772f840ba5da6571c2e2c6fde60b61157f21f873d832669157ef9bc10'}
  if not isinstance(terminals,dict) or set(terminals)!=want or any({x['Id']:x for x in rows}.get(i)!=v for i,v in terminals.items()):bad('terminal config')
  lease.assert_held()
  return {'ps_all':ids,'inspect':rows}
 return run
def sealed_module(path,name,source):
 """Execute only the immutable bytes just persisted in this private output."""
 m=types.ModuleType(name);m.__file__=str(path);m.__package__='';exec(compile(source,str(path),'exec'),m.__dict__);return m
def helper(base,sources):
 hp=base/'helper.sealed.py';ap=base/'archive.sealed.py';op=base/'observer.sealed.py'
 capture(base,hp.name,sources['helper']);capture(base,ap.name,sources['archive']);capture(base,op.name,sources['observer'])
 archive=sealed_module(ap,'_retention_archive_sealed',sources['archive']);m=sealed_module(hp,'_retire_sealed',sources['helper'])
 m._archive_module=lambda:archive
 # The observer is spawned from the exact fd, never from a pathname which a
 # non-root writer could replace between source sealing and callback launch.
 fd=os.open('observer.sealed.py',os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0),dir_fd=base.fd)
 opened=os.fstat(fd);named=os.stat('observer.sealed.py',dir_fd=base.fd,follow_symlinks=False)
 if not stat.S_ISREG(opened.st_mode) or opened.st_nlink!=1 or (opened.st_dev,opened.st_ino,opened.st_size)!=(named.st_dev,named.st_ino,named.st_size):os.close(fd);bad('sealed observer substituted')
 m.OBSERVER_SOURCE=base.path/'observer.sealed.py'
 return m,fd
def bind_delete_boundary(h,lease):
 """The sealed helper cannot cross any root-delete boundary after lease loss."""
 original=h.remove_root
 def guarded(item,journal):
  lease.assert_held()
  try:return original(item,journal)
  finally:lease.assert_held()
 h.remove_root=guarded
def fail_status(base,error):
 try:status(base,{'status':'FAIL','release_sha256':RELEASE_SHA256,'error':repr(error)})
 except BaseException as status_error:raise Error('primary failure '+repr(error)+'; status durability failure '+repr(status_error)) from error
def execute(release_arg):
 b=None;observer_fd=None;published=False;restored=False;old={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
 def interrupted(signum,frame):raise Interrupted('signal '+str(signum))
 try:
  # Latch before Git/cat-file admission: an interrupt can never strand one of
  # those session leaders without passing through the common retire path.
  for sig in old:signal.signal(sig,interrupted)
  r,sources=admit(release_arg)
  b=fresh_output(r)
  # This is deliberately before all live census/root validation and remains a tombstone.
  with ExclusionLease(r) as lease:
   lease.assert_held()
   live_gate(r,lease,b);lease.assert_held()
   h,observer_fd=helper(b,sources);lease.assert_held();bind_delete_boundary(h,lease)
   result=h.retire([CANDIDATE,BACKUP],r,OUT[0],OUT[1],OUT[2],observer_callback(b,lease,observer_fd),docker_callback(b,r['docker'],lease),output_dir_fd=b.fd)
   lease.assert_held();b.assert_bound()
   if observer_fd is not None:os.close(observer_fd);observer_fd=None
   lease.finalize();b.assert_bound()
  # Signal restoration is deliberately a pre-publication operation: any
  # error here leaves only non-authoritative evidence and failure status.
  for sig,previous in old.items():signal.signal(sig,previous)
  restored=True;b.assert_bound();os.fsync(b.fd)
  # The atomic rename + directory fsync below is the sole authoritative PASS.
  status(b,{'status':'PASS','release_sha256':RELEASE_SHA256},success=True);published=True
  try:b.close()
  except OSError:pass
  b=None
  return result
 except BaseException as e:
  if b is not None and not published:fail_status(b,e)
  raise
 finally:
  if observer_fd is not None:
   try:os.close(observer_fd)
   except OSError:pass
  if not restored:
   for sig,previous in old.items():signal.signal(sig,previous)
  if b is not None:
   try:b.close()
   except OSError:
    if not published:raise
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--release',required=True);execute(p.parse_args(argv).release)
if __name__=='__main__':
 try:main()
 except Error as e:print('FAIL CLOSED: '+str(e),file=sys.stderr);sys.exit(2)
