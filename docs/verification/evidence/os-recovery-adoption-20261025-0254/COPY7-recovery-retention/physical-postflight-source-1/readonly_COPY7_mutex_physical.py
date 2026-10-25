"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only COPY7 physical postflight; no configure/recover/transaction mutation.
"""
from pathlib import Path
import fcntl,hashlib,json,os,stat,types
ENGINE={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/cleanup_copy7_normal_failed_image.py', 'bytes': 133140, 'sha256': 'ab794aa8cf6733bbac92b49d2d6df171344f1241d0e70644ccb58af5505bcb96'}
RELEASE_REF={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/ROOT-CLEANUP-RELEASE.json', 'bytes': 598669, 'sha256': '5415341ce63b43adba7951c6c2ad59b3e75e50091b116c1b252d143bb002c247'}
RESULT_REF={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/actual-normal-cleanup-1/stdout', 'bytes': 369056, 'sha256': 'eef16afae29dd5441d393c22c9010ffa49a698e1eb371f81577a52c4df0eba4e'}
def need(v,m):
 if not v:raise RuntimeError(m)
def pinned(ref):
 p=Path(ref['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
 try:
  a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_size==ref['bytes'] and a.st_size<=4<<20,'bounded regular pinned source')
  raw=b''
  while len(raw)<=ref['bytes']:
   b=os.read(fd,min(65536,ref['bytes']+1-len(raw)))
   if not b:break
   raw+=b
  z=os.fstat(fd);n=p.lstat();keys=('st_dev','st_ino','st_mode','st_nlink','st_size','st_uid','st_gid','st_mtime_ns','st_ctime_ns')
  need(all(getattr(a,k)==getattr(z,k)==getattr(n,k) for k in keys),'stable pinned input')
  need(len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256'],'exact pinned bytes')
  return raw
 finally:os.close(fd)
need(os.getuid()==os.geteuid()==0,'authenticated root read-only observation')
m=types.ModuleType('_copy7_normal_readonly');m.__file__=ENGINE['path'];exec(compile(pinned(ENGINE),ENGINE['path'],'exec'),m.__dict__)
release=json.loads(pinned(RELEASE_REF));normal=json.loads(pinned(RESULT_REF));obs=release['observation']
need(normal['status']=='PASS_EXECUTED' and normal['terminal'] is True and normal['container_absent'] is True,'genuine terminal cleanup result')
need(normal['container_id']==m.KNOWN_TARGET['container_id'] and normal['boot_id']==obs['boot_id'] and normal['filesystem_uuid']==m.UUID,'exact COPY7 cleanup identity')
need(normal['release_sha256']==m.digest(m.canonical(release)),'consumed actual release bytes')
m.RELEASE=release;m.BOOT_ID=obs['boot_id'];m.OWNER_PID=413643;m.OWNER_START='68359948';m.WAITER_PIDS=(473751,473748,414842,416203,414785,416194,414777,414759,414767)
m.CONTAINER=m.KNOWN_TARGET['container_id'];m.CONTAINER_NAME=m.KNOWN_TARGET['container_name'];m.OWNER_NONCE=m.KNOWN_TARGET['owner_nonce']
m.CANDIDATE=Path(obs['candidate_root']['path']);m.PROTECTED=obs['selected_files']
need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==m.BOOT_ID,'current exact boot')
def absent(paths):
 for path in paths:need(not os.path.lexists(path),'ownership/quarantine path remains:'+str(path))
lock=m.observe_identity(m.ROOT_LOCK)
need((lock['device'],lock['inode'],lock['uid'],lock['gid'],lock['mode'],lock['nlink'],lock['size'])==(27,4,0,0,'0o644',1,0),'permanent mutex27:4')
key=f"{os.major(lock['device']):02x}:{os.minor(lock['device']):02x}:{lock['inode']}"
need(not [line for line in Path('/proc/locks').read_text().splitlines() if key in line.split()],'root mutex already held')
fd=os.open(m.ROOT_LOCK,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
try:
 need((os.fstat(fd).st_dev,os.fstat(fd).st_ino)==(27,4),'held mutex FD identity')
 fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 m.validate_mount();need(m.namespace_ancestry()==obs['namespace_ancestry'],'original namespace ancestry')
 paths=['/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json', '/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json', '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json']+[str(x) for x in (m.ATTEMPT,m.SHARED,m.LEASE,m.QUARANTINE)]
 absent(paths)
 need(not m.census(),'COPY7 CID/name/nonce still present')
 # Source-hashed inherited read-only inventory/hash oracle, original root-selected paths.
 m.protected_files()
 for ref in [normal['plan'],normal['journal'],normal['capture'],*normal['archives']]:
  need(m.observe_identity(Path(ref['path']))==ref,'retained transaction evidence differs:'+ref['path'])
 need([str(x) for x in m.archive_paths()]==[x['path'] for x in normal['archives']],'exact archive paths')
 plan=json.loads(m.read_bounded(Path(normal['plan']['path'])))
 need(m.digest(m.canonical(plan))==normal['plan_sha256'],'actual canonical plan SHA')
 transaction_mutex=m.observe_identity(m.MUTEX)
 need([transaction_mutex['device'],transaction_mutex['inode']]==plan['mutex'] and transaction_mutex['mode']=='0o600' and transaction_mutex['uid']==transaction_mutex['gid']==1000 and transaction_mutex['nlink']==1 and transaction_mutex['size']==0 and transaction_mutex['sha256']==m.digest(b''),'retained exact empty transaction mutex')
 journal=[json.loads(line) for line in m.read_bounded(Path(normal['journal']['path'])).splitlines()]
 need([(x['event'],x['index']) for x in journal]==[(e,i) for i in (0,1) for e in ('before_exchange','after_exchange','release','after_release')]+[('complete',2)],'nine exact legal journal events')
 previous=normal['plan_sha256']
 for i,row in enumerate(journal):
  need(row['sequence']==i and row['previous']==previous and row['plan_sha256']==normal['plan_sha256'] and row['plan_identity']==[normal['plan']['device'],normal['plan']['inode']],'journal exact chain binding')
  body={k:v for k,v in row.items() if k!='hash'};need(m.digest(m.canonical(body))==row['hash'],'journal row hash');previous=row['hash']
 absent(paths);need(m.observe_identity(m.ROOT_LOCK)==lock,'mutex path identity unchanged')
 print(json.dumps(dict(scope=__doc__,status='PASS_COPY7_MUTEX_HELD_PHYSICAL_POSTFLIGHT',normal_result=RESULT_REF,root_lock=lock,absence_paths=paths,container_absent=dict(container_id=m.CONTAINER,name=m.CONTAINER_NAME,nonce=m.OWNER_NONCE),preserved_inventory_rows=sum(len(v) for v in obs['inventories'].values()),preserved_selected_files=len(m.PROTECTED),transaction_records=[normal['plan'],normal['journal'],normal['capture'],*normal['archives']],journal_events=len(journal),proc=m.PROCESS_REPORTS[-1],cleanup=dict(pid=473751,starttime='69456080',sudo_pid=473748),artifact_native_acceptance=False),sort_keys=True))
finally:
 fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
