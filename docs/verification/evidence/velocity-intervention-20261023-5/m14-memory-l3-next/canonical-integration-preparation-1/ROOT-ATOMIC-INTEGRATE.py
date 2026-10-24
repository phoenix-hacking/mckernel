"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-owned exact two-file integration proposal. Per-file atomic replacement;
coordinated checks, conditional rollback never overwrites an intervening edit.
"""
from pathlib import Path
import hashlib,json,os,tempfile
P=Path(__file__).resolve().parent
ROWS=[{'target': '/home/holden/mckernel/arch/x86_64/kernel/memory.c', 'preimage': {'path': '/home/holden/mckernel/arch/x86_64/kernel/memory.c', 'sha256': '2b285359ee00dac9e6281d112743e4f39247b9d661d0b5d00993e74d17a0739e', 'bytes': 87143}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next/canonical-integration-preparation-1/staged/arch/x86_64/kernel/memory.c', 'sha256': '28a435d862d1a52263c3bf7b08bd401b4a28be914c2f7f9bdd6fedc68283ec46', 'bytes': 87978}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next/bounded-product-correction-1/candidate/arch/x86_64/kernel/memory.c', 'sha256': '28a435d862d1a52263c3bf7b08bd401b4a28be914c2f7f9bdd6fedc68283ec46', 'bytes': 87978}, 'rollback_preimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next/canonical-integration-preparation-1/preimages/arch/x86_64/kernel/memory.c', 'sha256': '2b285359ee00dac9e6281d112743e4f39247b9d661d0b5d00993e74d17a0739e', 'bytes': 87143}, 'mode': 420, 'uid': 1000, 'gid': 1000, 'observed_old_mode': '0o600', 'observed_old_inode': {'device': 66306, 'inode': 47459936, 'nlink': 1}}, {'target': '/home/holden/mckernel/kernel/rust/x86_memory_helpers.rs', 'preimage': {'path': '/home/holden/mckernel/kernel/rust/x86_memory_helpers.rs', 'sha256': '2994b6fe46feb6d0f6dd1390cd4a4efc550f8dfee66c067e506eba16b00029d7', 'bytes': 197568}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next/canonical-integration-preparation-1/staged/kernel/rust/x86_memory_helpers.rs', 'sha256': '245faf1198d9b7715714d236238172330257f4291776aced4e7cee6c3c518ce2', 'bytes': 199322}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next/bounded-product-correction-1/candidate/kernel/rust/x86_memory_helpers.rs', 'sha256': '245faf1198d9b7715714d236238172330257f4291776aced4e7cee6c3c518ce2', 'bytes': 199322}, 'rollback_preimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next/canonical-integration-preparation-1/preimages/kernel/rust/x86_memory_helpers.rs', 'sha256': '2994b6fe46feb6d0f6dd1390cd4a4efc550f8dfee66c067e506eba16b00029d7', 'bytes': 197568}, 'mode': 420, 'uid': 1000, 'gid': 1000, 'observed_old_mode': '0o600', 'observed_old_inode': {'device': 66306, 'inode': 47485029, 'nlink': 1}}]
AUTHORITIES=[{'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/SNAPSHOT-EQUALITY-RUNTIME-SOURCE-AND-ACTUAL-FIXTURE-READY.json', 'sha256': '214d772c14dfc54bd5066a8d7b5c1c501ebc5bec46605dbfc94b867905127bc5', 'bytes': 5535}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/source/native_diagnostic_container_owner.py', 'sha256': '57600f1c92d2075ee85d6a52949f11ae69c99dbd122087c227bab28178caedb6', 'bytes': 147559}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/COHORT-BINDINGS.json', 'sha256': 'b5aa82c50bdd34f15d88275d1d12540a5ee194291bedba4e670b06169f284ea8', 'bytes': 3219}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/ACTUAL-SNAPSHOT-EQUALITY-COHORT-FIXTURE-RECEIPT.json', 'sha256': 'ff2ea7cf60e21c431336f07dbe728ce0d3d173ab40b8bb78e1bec14579ece840', 'bytes': 2876}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/ACTUAL-MOUNT-AND-OPEN-FOOTPRINT-RESULT.json', 'sha256': '16cf0d2f59ef6633e669d533d5a8c673c9389fa42e99eb0b535a588cc09ab802', 'bytes': 217938}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next/canonical-integration-preparation-1/ACTIVE-CURRENT287-PIN-EXCLUSION.json', 'sha256': 'ec139fbbf094da5c201dd65ce3fc95b45172068574d4e855c1efce185848f8da', 'bytes': 188202}]

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
 for r,data in zip(ROWS,posts):staged.append(stage(r,data,'.m14-l3-root-stage-'))
 for r in ROWS:checked(r['target'],r['preimage'])
 for r,name in zip(ROWS,staged):
  # Recheck this exact original immediately before replacing its directory entry.
  checked(r['target'],r['preimage'])
  os.replace(name,r['target']);s=Path(r['target']).lstat()
  published.append((r,s.st_dev,s.st_ino));fsyncdir(Path(r['target']).parent)
 for r in ROWS:checked(r['target'],r['staged_postimage'])
 status='ROOT_EXACT2_L3_SOURCE_INTEGRATION_PASS'
except BaseException as exc:
 status='ROOT_INTEGRATION_FAILED_CONDITIONAL_ROLLBACK'
 for r,dev,ino in reversed(published):
  target=Path(r['target']);s=target.lstat()
  try:
   assert (s.st_dev,s.st_ino)==(dev,ino),'intervening replacement: retain current bytes'
   checked(target,r['staged_postimage'])
   original=checked(r['rollback_preimage']['path'],r['rollback_preimage'])
   tmp=stage(r,original,'.m14-l3-root-rollback-')
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
result={'scope':__doc__,'status':status,'copies':ROWS,'conditional_rollback':rollback,'remaining_C_callbacks':'L2/L1/effect/log and CwalkL3 dispatcher remain debt','defaultGCC14_kernel_link_native':False,'no_candidate15_mutation':True}
with (P/'ROOT-INTEGRATION-RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(result))
