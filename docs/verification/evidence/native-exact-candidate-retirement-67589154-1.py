#!/usr/bin/env python3
"""DRAFT only: one future root retirement boundary, never an execution release.

The only authorized future invocation is `/usr/bin/sudo -A /usr/bin/python3
-E -s -B PACKET --release RELEASE`.  This packet itself never calls sudo or an
askpass program.  While any digest sentinel remains, it fails before euid,
Git, subprocess, output, Docker, observer, rename, or deletion activity.
"""
from __future__ import print_function
import argparse, fcntl, hashlib, importlib.util, json, os, re, resource, select, signal, stat, subprocess, sys, time
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
HELPER=SOURCE/'scripts/native_exact_candidate_retire.py'; OBSERVER=SOURCE/'docs/verification/evidence/native-exact-candidate-live-reference-observer-67589154-1.py'
# Corrected owner/observer boundary is concurrently pending independent review.
HELPER_SHA256='2ba700743d01060b0d35114c3b4380cb9b25865d2d973ca05a3d83df3d38964e'; OBSERVER_SHA256='3562b1d3d4e9a1e09cb7fa2be30f8e320923d50cf628b7f42314318702653666'; HELPER_TEST_SHA256='e7630fa2cf7c374fe6f27ebf29c01af7ec3913c811bdbd003e4c8fe565f20981'; OBSERVER_TEST_SHA256='b5f48e7b616f9ac517397455a1aebe0e13ce2a741388cf46046d0761adb922e4'
HELPER_TEST=SOURCE/'scripts/tests/test_native_exact_candidate_retire.py'; OBSERVER_TEST=SOURCE/'scripts/tests/test_native_exact_candidate_live_reference_observer_67589154.py'
FLOORS={'host':16<<30,'scratch':12<<30,'tmpfs':4<<30,'memory':4<<30}
OUT=('claim-67589154-1.json','journal-67589154-1.jsonl','evidence-67589154-1.json','packet.status','operational-exclusion-lease.json','observer.stdout','observer.stderr','observer.status','docker-ps.stdout','docker-ps.stderr','docker-ps.status','docker-inspect.stdout','docker-inspect.stderr','docker-inspect.status','docker-ps-after.stdout','docker-ps-after.stderr','docker-ps-after.status')
H40=re.compile(r'^[0-9a-f]{40}$'); H64=re.compile(r'^[0-9a-f]{64}$')
CONFLICT_BASENAMES=('qemu-system-x86_64','qemu-system-aarch64','native_rust_exact_build_container_owner.py','native_exact_candidate_retire.py')
class Error(RuntimeError): pass
class Interrupted(Error): pass
def bad(s): raise Error(s)
def sha(b): return hashlib.sha256(b).hexdigest()
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
 if any(x.endswith('_REQUIRED') for x in (RELEASE_SHA256,HELPER_SHA256,OBSERVER_SHA256,HELPER_TEST_SHA256,OBSERVER_TEST_SHA256)): bad('DRAFT_NOT_RELEASED')
 if not all(H64.fullmatch(x) for x in (RELEASE_SHA256,HELPER_SHA256,OBSERVER_SHA256,HELPER_TEST_SHA256,OBSERVER_TEST_SHA256)):bad('invalid digest literal')
def stable_regular(path):
 try:
  before=os.lstat(str(path))
  if not stat.S_ISREG(before.st_mode):bad('not durable regular: '+str(path))
  fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|getattr(os,'O_CLOEXEC',0))
 except OSError as e:bad('cannot open durable file: '+str(e))
 try:
  opened=os.fstat(fd)
  if (opened.st_dev,opened.st_ino,opened.st_mode)!=(before.st_dev,before.st_ino,before.st_mode):bad('substituted before read')
  chunks=[]
  while True:
   b=os.read(fd,1<<20)
   if not b:break
   chunks.append(b)
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
def gout(directory,*a):
 try:return subprocess.check_output(gargv(directory,*a),env=genv(),stderr=subprocess.PIPE)
 except (OSError,subprocess.CalledProcessError) as e:bad('Git admission: '+str(e))
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
 p=subprocess.Popen(gargv(directory,'cat-file','--batch'),env=genv(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0,preexec_fn=limit)
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
  try:return p.wait(timeout=5)
  except TypeError:return p.wait() # pure in-memory test double
 except subprocess.TimeoutExpired:pass
 p.terminate()
 try:return p.wait(timeout=5)
 except subprocess.TimeoutExpired:pass
 p.kill()
 try:return p.wait(timeout=5)
 except subprocess.TimeoutExpired:bad('uncertain canonical reader retirement')
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
 if subprocess.call(gargv(GIT,'merge-base','--is-ancestor',t['commit'],fetched),env=genv(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)!=0:bad('template not ancestor')
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
def live_gate(r):
 """All mutable names stay absent until these exact live prerequisites hold."""
 floors={'host':free_bytes('/home'),'scratch':free_bytes('/home/holden/mckernel-work/scratch'),'tmpfs':free_bytes('/dev/shm'),'memory':os.sysconf('SC_PAGE_SIZE')*os.sysconf('SC_AVPHYS_PAGES')}
 if any(floors[k]<FLOORS[k] for k in FLOORS):bad('resource floor')
 try:boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
 except OSError:bad('boot id unavailable')
 if boot!=r['boot_id']:bad('current boot mismatch')
 for row in r['launcher_identities']:
  if not isinstance(row,dict) or not isinstance(row.get('pid'),int) or not isinstance(row.get('starttime'),int) or proc_starttime(row['pid'])!=row['starttime']:bad('launcher identity mismatch')
 if r.get('conflict_basenames')!=list(CONFLICT_BASENAMES) or not isinstance(r.get('heavy_lease_paths'),list):bad('process/lease release binding')
 for lease in r['heavy_lease_paths']:
  if not isinstance(lease,str) or os.path.lexists(lease):bad('active heavy lease')
 for q in QUARANTINES:
  if os.path.lexists(q):bad('quarantine already exists')
 if Path(r['output_dir']).exists():bad('output already exists')
 protected={x['pid'] for x in r['launcher_identities']}
 for name in os.listdir('/proc'):
  if not name.isdigit() or int(name) in protected:continue
  cmd=proc_cmdline_stable(int(name))
  if cmd is None:continue
  argv=cmd.split(b'\0');names={os.path.basename(x.decode('utf8','surrogateescape')) for x in argv if x}
  if names.intersection(CONFLICT_BASENAMES):bad('operational exclusion conflict')
def validate_release(r,fetched,inv):
 keys={'schema','status','one_shot','retry','rollback','main_commit','ihk_commit','candidate','metadata_backup','inventory_sha256','capsule_sha256','success_sha256','source_hashes','roots','sealed','observer','docker','boot_id','launcher_identities','operational_exclusion','conflict_basenames','heavy_lease_paths','resource_floors','output_dir','template','finalization'}
 if not isinstance(r,dict) or set(r)!=keys:bad('release keys')
 if (r['schema'],r['status'],r['one_shot'],r['retry'],r['rollback'])!=('mckernel.ordinary-retirement-release.v1','PASS_ONE_SHOT_RETIRE',True,False,False):bad('one-shot/retry/rollback')
 if (r['main_commit'],r['ihk_commit'],r['candidate'],r['metadata_backup'])!=(MAIN,IHK,CANDIDATE,BACKUP) or (r['inventory_sha256'],r['capsule_sha256'],r['success_sha256'])!=(INV_SHA,CAP_SHA,SUCCESS_SHA):bad('identity/evidence')
 if r['source_hashes']!={'helper':HELPER_SHA256,'observer':OBSERVER_SHA256,'helper_test':HELPER_TEST_SHA256,'observer_test':OBSERVER_TEST_SHA256}:bad('support hashes')
 if not isinstance(r['roots'],list) or len(r['roots'])!=2:bad('roots')
 for x,path,ino,q in zip(r['roots'],(CANDIDATE,BACKUP),(25166,35798),QUARANTINES):
  live=x.get('root') if isinstance(x,dict) else None
  if not isinstance(x,dict) or x.get('path')!=path or not isinstance(live,dict) or any(live.get(k)!=v for k,v in (('device',26),('inode',ino),('uid',1000),('gid',1000),('mode',0o755),('kind','directory'))) or not isinstance(live.get('size'),int) or live['size']<0 or not isinstance(x.get('parent'),dict) or not isinstance(x.get('members'),list):bad('root/parent/member map')
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
   m=got[e['path']];typ={'regular':'file','directory':'directory','symlink':'symlink'}.get(e.get('type'))
   if m.get('kind')!=typ or any(m.get(k)!=e.get(k) for k in ('path','uid','gid','mode','size')) or (typ=='file' and m.get('sha256')!=e.get('sha256')) or (typ=='symlink' and m.get('target')!=e.get('target')):bad('inventory member binding')
 if not all(isinstance(r[k],dict) for k in ('sealed','observer','docker')) or not isinstance(r['boot_id'],str) or not r['boot_id'] or not isinstance(r['launcher_identities'],list) or not r['launcher_identities'] or not isinstance(r['operational_exclusion'],str) or not r['operational_exclusion'] or r['resource_floors']!=FLOORS or not isinstance(r['output_dir'],str):bad('runtime release binding')
 seal=r['sealed'];needed=('retention_manifest_sha256','retention_manifest_pushed_sha256','retention_manifest_fetched_sha256','capsule_sha256','capsule_pushed_sha256','capsule_fetched_sha256','retention_manifest_path','capsule_path')
 if any(k not in seal for k in needed) or any(not H64.fullmatch(seal[k]) for k in needed[:6]) or not all(isinstance(seal[k],str) and seal[k].startswith('/') for k in needed[6:]):bad('helper sealed preflight')
 if r['observer'].get('observer_sha256')!=OBSERVER_SHA256 or r['observer'].get('boot_id')!=r['boot_id']:bad('helper observer preflight')
 terminal='decd7cf92467e1214cc955d15a00b847587ada37016f206e9a82019cbb72c6b9'
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
 r=exact_json(raw);validate_release(r,fetch,inv);live_gate(r)
 for p,h in ((HELPER,HELPER_SHA256),(OBSERVER,OBSERVER_SHA256),(HELPER_TEST,HELPER_TEST_SHA256),(OBSERVER_TEST,OBSERVER_TEST_SHA256)):checked(p,h)
 return r
def fresh_output(r):
 p=Path(r['output_dir'])
 if not p.is_absolute() or not str(p).startswith('/home/holden/mckernel-work/scratch/') or p.exists():bad('fresh scratch output')
 p.mkdir(mode=0o700,parents=False)
 if not p.is_dir() or os.lstat(str(p)).st_mode&0o777!=0o700:bad('scratch output mode')
 return p
class ExclusionLease(object):
 """Cooperating actors honor this flock; non-cooperating root actors are a retained threat assumption."""
 def __init__(self,base,release):self.base=base;self.release=release;self.fd=None;self.identity=None
 def __enter__(self):
  path=self.base/'operational-exclusion-lease.json'
  self.fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  try:fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except OSError as e:os.close(self.fd);self.fd=None;bad('operational exclusion lease busy: '+str(e))
  record={'schema':'mckernel.retirement-operational-exclusion.v1','release_sha256':RELEASE_SHA256,'boot_id':self.release['boot_id'],'pid':os.getpid(),'starttime':proc_starttime(os.getpid()),'threat_assumption':'noncooperating actors do not honor flock'}
  data=(json.dumps(record,sort_keys=True,separators=(',',':'))+'\n').encode('utf8');os.write(self.fd,data);os.fsync(self.fd);self.identity=os.fstat(self.fd);return self
 def assert_held(self):
  if self.fd is None:bad('operational exclusion lease absent')
  named=os.lstat(str(self.base/'operational-exclusion-lease.json'));opened=os.fstat(self.fd)
  if (named.st_dev,named.st_ino)!=(opened.st_dev,opened.st_ino) or (opened.st_dev,opened.st_ino)!=(self.identity.st_dev,self.identity.st_ino):bad('operational exclusion lease replaced')
  try:fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except OSError as e:bad('operational exclusion lease lost: '+str(e))
 def __exit__(self,*unused):
  if self.fd is not None:os.fsync(self.fd);os.close(self.fd);self.fd=None
def status(base,value):
 try:capture(base,'packet.status',(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('utf8'))
 except BaseException:pass
def capture(base,name,data):
 if name not in OUT:bad('unreleased capture')
 with open(str(base/name),'xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
def retire_process(p):
 """TERM, then KILL, then a bounded reap; uncertainty is fail-closed."""
 try:os.killpg(p.pid,signal.SIGTERM)
 except OSError:pass
 try:return p.communicate(timeout=5)
 except subprocess.TimeoutExpired:pass
 try:os.killpg(p.pid,signal.SIGKILL)
 except OSError:pass
 try:return p.communicate(timeout=5)
 except subprocess.TimeoutExpired:bad('uncertain child retirement')
def call(argv,base,stem):
 """One callback attempt.  Timeout retires its whole new process group."""
 p=None
 try:
  p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  out,err=p.communicate(timeout=180);rc=p.returncode
 except subprocess.TimeoutExpired as e:
  out,err=retire_process(p)
  rc=124
 except (OSError,KeyboardInterrupt,Interrupted) as e:
  if p is not None:
   out,err=retire_process(p)
  else:out,err=b'',str(e).encode('utf8','replace')
  rc=125
 capture(base,stem+'.stdout',out);capture(base,stem+'.stderr',err);capture(base,stem+'.status',(str(rc)+'\n').encode('ascii'))
 if rc:bad(stem+' callback failed')
 return out
def observer_callback(base,lease):
 argv=['/usr/bin/python3','-E','-s','-B',str(OBSERVER),'--target',QUARANTINES[0],'--target',QUARANTINES[1]]
 def run(targets,members):
  lease.assert_held()
  if list(targets)!=list(QUARANTINES):bad('helper supplied observer targets')
  x=exact_json(call(argv,base,'observer'))
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
  return {'ps_all':ids,'inspect':rows}
 return run
def helper():
 s=importlib.util.spec_from_file_location('retire',str(HELPER));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.OBSERVER_SOURCE=OBSERVER;return m
def execute(release_arg):
 r=admit(release_arg);b=fresh_output(r);h=helper();old={sig:signal.getsignal(sig) for sig in (signal.SIGTERM,signal.SIGINT)}
 def interrupted(signum,frame):raise Interrupted('signal '+str(signum))
 try:
  for sig in old:signal.signal(sig,interrupted)
  with ExclusionLease(b,r) as lease:
   lease.assert_held()
   result=h.retire([CANDIDATE,BACKUP],r,str(b/OUT[0]),str(b/OUT[1]),str(b/OUT[2]),observer_callback(b,lease),docker_callback(b,r['docker'],lease))
   lease.assert_held();status(b,{'status':'PASS','release_sha256':RELEASE_SHA256});return result
 except BaseException as e:
  status(b,{'status':'FAIL','release_sha256':RELEASE_SHA256,'error':repr(e)});raise
 finally:
  for sig,previous in old.items():signal.signal(sig,previous)
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--release',required=True);execute(p.parse_args(argv).release)
if __name__=='__main__':
 try:main()
 except Error as e:print('FAIL CLOSED: '+str(e),file=sys.stderr);sys.exit(2)
