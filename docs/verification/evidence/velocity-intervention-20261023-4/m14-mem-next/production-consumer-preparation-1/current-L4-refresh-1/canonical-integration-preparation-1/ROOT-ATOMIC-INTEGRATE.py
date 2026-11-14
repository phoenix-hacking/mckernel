"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-owned exact two-file integration proposal. Per-file atomic replacement;
coordinated checks, conditional rollback never overwrites an intervening edit.
"""
from pathlib import Path
import hashlib,json,os,tempfile
P=Path(__file__).resolve().parent
ROWS=[{'target': '/home/holden/mckernel/kernel/mem.c', 'preimage': {'path': '/home/holden/mckernel/kernel/mem.c', 'sha256': '7498e7c930a55bdcde5ecd12f4498c47c5573d690355c8f09a7b9f957ffe00a2', 'bytes': 226712}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-mem-next/production-consumer-preparation-1/current-L4-refresh-1/canonical-integration-preparation-1/staged/kernel/mem.c', 'sha256': '638788c79fb96c1edb229d016fa678a02c0fcde6e1b56c7fa45d33b5490354d4', 'bytes': 226806}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-mem-next/candidate/kernel/mem.c', 'sha256': '638788c79fb96c1edb229d016fa678a02c0fcde6e1b56c7fa45d33b5490354d4', 'bytes': 226806}, 'rollback_preimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-mem-next/production-consumer-preparation-1/current-L4-refresh-1/canonical-integration-preparation-1/preimages/kernel/mem.c', 'sha256': '7498e7c930a55bdcde5ecd12f4498c47c5573d690355c8f09a7b9f957ffe00a2', 'bytes': 226712}, 'mode': 420, 'uid': 1000, 'gid': 1000, 'observed_old_inode': {'device': 66306, 'inode': 47475811, 'nlink': 1}}, {'target': '/home/holden/mckernel/kernel/rust/mem_helpers.rs', 'preimage': {'path': '/home/holden/mckernel/kernel/rust/mem_helpers.rs', 'sha256': 'c0e7f8bd0b117c9b4e0a4e3690ef5ed5cb01bdc6b16f7225de973eba039d72d5', 'bytes': 202708}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-mem-next/production-consumer-preparation-1/current-L4-refresh-1/canonical-integration-preparation-1/staged/kernel/rust/mem_helpers.rs', 'sha256': '4635a252332cd369e36384f04a414e2b4c2d79726a4f95caafcf1d3ed1a56b4d', 'bytes': 203495}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-mem-next/candidate/kernel/rust/mem_helpers.rs', 'sha256': '4635a252332cd369e36384f04a414e2b4c2d79726a4f95caafcf1d3ed1a56b4d', 'bytes': 203495}, 'rollback_preimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-mem-next/production-consumer-preparation-1/current-L4-refresh-1/canonical-integration-preparation-1/preimages/kernel/rust/mem_helpers.rs', 'sha256': 'c0e7f8bd0b117c9b4e0a4e3690ef5ed5cb01bdc6b16f7225de973eba039d72d5', 'bytes': 202708}, 'mode': 420, 'uid': 1000, 'gid': 1000, 'observed_old_inode': {'device': 66306, 'inode': 47484784, 'nlink': 1}}]
AUTHORITIES=[{'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-diagnostic-collector-successor-1/source/native_diagnostic_container_owner.py', 'sha256': '626bef088a1c8d60c5c41afb88d59faeb55c025c3f11c9d47c649c571e05e2eb', 'bytes': 139652}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-diagnostic-collector-successor-1/COHORT-BINDINGS.json', 'sha256': 'e746c77878591125fc7ad87a90cab5e3ada208f539cccbb06af0b43b8be66b85', 'bytes': 3249}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-diagnostic-collector-successor-1/ACTUAL-MOUNT-AND-OPEN-FOOTPRINT-RESULT.json', 'sha256': '93d2ff8e8c183a6deb5550a3a736ab318bea0f45e598eb9231fb7529189496ca', 'bytes': 197652}]

def checked(path,row):
 data=Path(path).read_bytes()
 assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],path
 return data
def fsyncdir(path):
 fd=os.open(str(path),os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def stage(row,data,tag):
 target=Path(row['target']);fd,name=tempfile.mkstemp(prefix=tag,dir=target.parent)
 with os.fdopen(fd,'wb') as f:
  os.fchmod(f.fileno(),row['mode']);os.fchown(f.fileno(),row['uid'],row['gid'])
  assert f.write(data)==len(data);f.flush();os.fsync(f.fileno())
 return name
# Root confirms the finite authority selection in the accompanying proposal.
# No root/runtime/lease/Docker API is called by this source operation.
for a in AUTHORITIES:checked(a['path'],a)
for r in ROWS:checked(r['target'],r['preimage'])
posts=[checked(r['staged_postimage']['path'],r['staged_postimage']) for r in ROWS]
backs=[checked(r['rollback_preimage']['path'],r['rollback_preimage']) for r in ROWS]
staged=[];published=[];rollback=[]
try:
 for r,data in zip(ROWS,posts):staged.append(stage(r,data,'.m14-scalar-root-stage-'))
 for r in ROWS:checked(r['target'],r['preimage'])
 for r,name in zip(ROWS,staged):
  # Recheck this exact original immediately before replacing its directory entry.
  checked(r['target'],r['preimage'])
  os.replace(name,r['target']);s=Path(r['target']).lstat()
  published.append((r,s.st_dev,s.st_ino));fsyncdir(Path(r['target']).parent)
 for r in ROWS:checked(r['target'],r['staged_postimage'])
 status='ROOT_EXACT2_SCALAR_SOURCE_INTEGRATION_PASS'
except BaseException as exc:
 status='ROOT_INTEGRATION_FAILED_CONDITIONAL_ROLLBACK'
 for r,dev,ino in reversed(published):
  target=Path(r['target']);s=target.lstat()
  try:
   assert (s.st_dev,s.st_ino)==(dev,ino),'intervening replacement: retain current bytes'
   checked(target,r['staged_postimage'])
   original=checked(r['rollback_preimage']['path'],r['rollback_preimage'])
   tmp=stage(r,original,'.m14-scalar-root-rollback-')
   # Recheck identity and exact postimage before reverting only our own change.
   s=target.lstat();assert (s.st_dev,s.st_ino)==(dev,ino)
   checked(target,r['staged_postimage'])
   os.replace(tmp,target);fsyncdir(target.parent)
   rollback.append({'target':str(target),'status':'RESTORED_EXACT_PREIMAGE_OWN_INODE_ONLY'})
  except BaseException as re:
   rollback.append({'target':str(target),'status':'HOLD_INTERVENING_EDIT_OR_UNCERTAINTY','error':repr(re)})
 result={'scope':__doc__,'status':status,'error':repr(exc),'copies':ROWS,'conditional_rollback':rollback,'no_other_work_undone':True,'canonical_two_file_transaction_is_not_single_filesystem_atomic_operation':True}
 with (P/'ROOT-INTEGRATION-RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 raise
result={'scope':__doc__,'status':status,'copies':ROWS,'conditional_rollback':rollback,'remaining_C_callbacks':13,'defaultGCC14_kernel_link_native':False,'no_candidate15_mutation':True}
with (P/'ROOT-INTEGRATION-RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(result))
