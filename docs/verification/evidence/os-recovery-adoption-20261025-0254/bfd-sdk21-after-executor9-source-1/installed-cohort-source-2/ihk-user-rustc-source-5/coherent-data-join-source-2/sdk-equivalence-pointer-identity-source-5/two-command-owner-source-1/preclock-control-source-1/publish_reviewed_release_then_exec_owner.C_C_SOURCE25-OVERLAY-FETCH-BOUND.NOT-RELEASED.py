"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One separately root-granted reviewed metadata publish -> ordinary samePID owner exec.
No outer timeout/CPU watchdog, retry, kill controller or implicit execution authority.
"""
from pathlib import Path
import os,sys,json,hashlib,stat,subprocess,time,resource
D=Path(__file__).parent
FILL_REF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/preclock-control-source-1/fill_BFD_C_C_current_review_payload.OVERLAY-FETCH-BOUND.NOT-RELEASED.py', 'bytes': 67476, 'sha256': '978a208bd953b738ccef477ed8805447f50396b35fea61d3f4fda694287c9e00'}
ENTRY_REF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/preclock-control-source-1/ROOT-OWNER-ENTRY.PENDING.json', 'bytes': 2585, 'sha256': '1ebfa4f436ee22c758781a4a911fa308e53e578e3ce532261e73fa290f533247'}
REQUEST_REF = {'bytes': 4602, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/REQUEST.BFD-CC-CONTROL.PENDING-RELEASE.json', 'sha256': '1d9b4e5501a31b7a38307afbc442b7cc891f613c12b8880e9afca6756e26462c'}
OWNER_REF = {'bytes': 76813, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/bfd_original_c_twice_owner.PREFIX-SOURCE-CORRECTED.py', 'sha256': 'cca85a8205ee8875da705676c9c104d4801e095cb683acd1f008545b3b77fada'}
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def read(ref):
 p=Path(ref['path']);assert p.is_absolute() and all(not x.is_symlink() for x in (p,*p.parents))
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
 try:
  a=os.fstat(fd);assert stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_size<=32<<20
  parts=[];size=0
  while True:
   b=os.read(fd,65536)
   if not b:break
   size+=len(b);assert size<=32<<20;parts.append(b)
  raw=b''.join(parts);b=os.fstat(fd);c=p.lstat()
  assert all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in FIELDS) and size==b.st_size
 finally:os.close(fd)
 assert hashlib.sha256(raw).hexdigest()==ref['sha256']
 if 'bytes' in ref:assert len(raw)==ref['bytes']
 return raw
def emit(path,value):
 raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def ref(path):
 raw=Path(path).read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
assert os.getuid()==os.geteuid()==os.getgid()==1000
assert len(sys.argv)==5 and sys.argv[1]=='--actual-review' and sys.argv[4]==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
assert resource.getrlimit(resource.RLIMIT_CPU)==(resource.RLIM_INFINITY,resource.RLIM_INFINITY)
for r in (FILL_REF,ENTRY_REF,REQUEST_REF,OWNER_REF):assert r is not None;read(r)
review_ref=dict(path=sys.argv[2],sha256=sys.argv[3]);review=json.loads(read(review_ref))
assert review['decision']=='PASS_EXECUTION' and review['implementation_ownership'] is False and review['reviewer'] and review['reviewer']!='/root'
payload_path=D/'RELEASE.ROOT.REVIEW-PAYLOAD.NOT-RELEASED.json';payload=json.loads(payload_path.read_bytes())
canonical=(json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
assert review['reviewed_release_payload_sha256']==hashlib.sha256(canonical).hexdigest()
request=json.loads(read(REQUEST_REF));entry=json.loads(read(ENTRY_REF));query=json.loads(read(payload['actual_query']))
assert request['nonce']==payload['nonce'] and payload['request']=={k:REQUEST_REF[k] for k in ('path','sha256')}
assert 0<=time.time()-query['at']<=120
assert not os.path.lexists(D/'RELEASE.ROOT.FINAL.json') and not os.path.lexists(D/'ROOT-OWNER-ENTRY.FINAL.LIBDWARF1.json')
C=D/'actual-root-final-publish-and-owner-1';assert not os.path.lexists(C);C.mkdir(mode=0o700)
argv=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',FILL_REF['path'],'--publish-reviewed-release',review_ref['path'],review_ref['sha256']]
emit(C/'EXACT-ROOT-FINAL-PUBLISH-COMMAND.json',dict(scope=__doc__,argv=argv,actual_review=review_ref,fill=FILL_REF,query_age_seconds=time.time()-query['at'],outer_timeout=None,outer_CPU_rlimit=None))
with (C/'root-publish.stdout').open('xb') as out,(C/'root-publish.stderr').open('xb') as err:
 result=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
 out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
emit(C/'ACTUAL-ROOT-FINAL-PUBLISH-EXIT.json',dict(returncode=result.returncode,stdout=ref(C/'root-publish.stdout'),stderr=ref(C/'root-publish.stderr')))
assert result.returncode==0 and (C/'root-publish.stderr').stat().st_size==0
published=json.loads((C/'root-publish.stdout').read_bytes());assert published['status']=='REVIEWED_RELEASE_PUBLISHED_OWNER_NOT_EXECUTED'
release_ref=published['release'];release=json.loads(read(release_ref));final_entry=json.loads(read(published['ordinary_entry']))
assert release_ref['path']==str(D/'RELEASE.ROOT.FINAL.json') and release['execution_review']==review_ref
assert release['request']==payload['request'] and release['nonce']==request['nonce']
expected=list(entry['argv']);index=expected.index('--release-sha256')+1;assert expected[index]=='ROOT_FINAL_REVIEWED_RELEASE_SHA256';expected[index]=release_ref['sha256']
assert final_entry['argv']==expected and final_entry['release_sha256']==release_ref['sha256']
assert expected[:3]==['/usr/bin/taskset','-c','7'] and not any(a.startswith('--cpu=') for a in expected) and '/usr/bin/sudo' not in expected
assert final_entry['outer_timeout'] is None and final_entry['outer_CPU_rlimit'] is None
# Fresh resource checks immediately before the ordinary owner (which independently repeats exact identity/capacity checks).
back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512)
assert dict(device=back.st_dev,inode=back.st_ino,mode=stat.S_IMODE(back.st_mode),uid=back.st_uid,gid=back.st_gid,path='/home/holden/mckernel-work/scratch.ext4',size=back.st_size,nlink=back.st_nlink)==request['backing_identity']
mem={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')};hv=os.statvfs('/');sv=os.statvfs('/home/holden/mckernel-work/scratch')
resources=dict(memory_available=mem['MemAvailable'],host_free=hv.f_bavail*hv.f_frsize,scratch_free=sv.f_bavail*sv.f_frsize,full_sparse_growth_bytes=gap,host_minimum_bytes=26449281024+gap,scratch_minimum_bytes=14091616256)
assert resources['memory_available']>=25501368320 and resources['host_free']>=resources['host_minimum_bytes'] and resources['scratch_free']>=resources['scratch_minimum_bytes']
age=time.time()-query['at'];assert 0<=age<=120
pid=os.getpid()
if os.getpgid(pid)!=pid:os.setsid()
birth=Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[19];boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==request['boot_id']
emit(C/'DIRECT-OWNER-PROCESS-BEFORE-EXEC.json',dict(scope=__doc__,pid=pid,starttime=birth,pgid=os.getpgid(pid),boot_id=boot,nonce=request['nonce'],argv=expected,request=REQUEST_REF,release=release_ref,actual_review=review_ref,query_age_seconds=age,resources=resources,outer_timeout=None,outer_CPU_rlimit=None,owner_not_yet_executed_at_record=True))
for target,name in ((1,'owner.stdout'),(2,'owner.stderr')):
 fd=os.open(C/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.dup2(fd,target);os.close(fd)
os.execv(expected[0],expected)
