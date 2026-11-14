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
m.process_absent()
print(json.dumps(dict(scope=__doc__,status='PASS_COPY7_COMPLETE_PROC_OBSERVATION',normal_result=RESULT_REF,known_cleanup=dict(pid=473751,starttime='69456080',sudo_pid=473748),known_owner=dict(pid=413643,starttime='68359948'),waiter_pids=list(m.WAITER_PIDS),proc=m.PROCESS_REPORTS[-1]),sort_keys=True))
