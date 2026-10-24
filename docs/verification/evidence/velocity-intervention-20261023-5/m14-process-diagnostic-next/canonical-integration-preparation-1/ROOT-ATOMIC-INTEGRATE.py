"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-owned exact two-file integration proposal. Per-file atomic replacement;
coordinated checks, conditional rollback never overwrites an intervening edit.
"""
from pathlib import Path
import hashlib,json,os,tempfile
P=Path(__file__).resolve().parent
ROWS=[{'target': '/home/holden/mckernel/kernel/process.c', 'preimage': {'path': '/home/holden/mckernel/kernel/process.c', 'sha256': '64af918855ea361bd850d6ad7480d304634c28814e04127fe3dec8c013f21044', 'bytes': 161959}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/canonical-integration-preparation-1/staged/kernel/process.c', 'sha256': '08c238a08066a6eda5f346bbd6e6f87333bd505d8d598276dc9c52cd43568a45', 'bytes': 162457}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/candidate/process.c', 'sha256': '08c238a08066a6eda5f346bbd6e6f87333bd505d8d598276dc9c52cd43568a45', 'bytes': 162457}, 'rollback_preimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/canonical-integration-preparation-1/preimages/kernel/process.c', 'sha256': '64af918855ea361bd850d6ad7480d304634c28814e04127fe3dec8c013f21044', 'bytes': 161959}, 'mode': 420, 'uid': 1000, 'gid': 1000, 'observed_old_mode': '0o600', 'observed_old_inode': {'device': 66306, 'inode': 47459989, 'nlink': 1}}, {'target': '/home/holden/mckernel/kernel/rust/process_helpers.rs', 'preimage': {'path': '/home/holden/mckernel/kernel/rust/process_helpers.rs', 'sha256': '3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e', 'bytes': 352627}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/canonical-integration-preparation-1/staged/kernel/rust/process_helpers.rs', 'sha256': 'd04b48c887c834edd6380e3ae06fccdef7dfafaf67196fd28af7f9571993bd6d', 'bytes': 353812}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/bounded-correction-1/candidate/process_helpers.rs', 'sha256': 'd04b48c887c834edd6380e3ae06fccdef7dfafaf67196fd28af7f9571993bd6d', 'bytes': 353812}, 'rollback_preimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/canonical-integration-preparation-1/preimages/kernel/rust/process_helpers.rs', 'sha256': '3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e', 'bytes': 352627}, 'mode': 420, 'uid': 1000, 'gid': 1000, 'observed_old_mode': '0o600', 'observed_old_inode': {'device': 66306, 'inode': 47484935, 'nlink': 1}}]
AUTHORITIES=[{'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/SNAPSHOT-EQUALITY-RUNTIME-SOURCE-AND-ACTUAL-FIXTURE-READY.json', 'sha256': '214d772c14dfc54bd5066a8d7b5c1c501ebc5bec46605dbfc94b867905127bc5', 'bytes': 5535}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/source/native_diagnostic_container_owner.py', 'sha256': '57600f1c92d2075ee85d6a52949f11ae69c99dbd122087c227bab28178caedb6', 'bytes': 147559}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/COHORT-BINDINGS.json', 'sha256': 'b5aa82c50bdd34f15d88275d1d12540a5ee194291bedba4e670b06169f284ea8', 'bytes': 3219}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/ACTUAL-SNAPSHOT-EQUALITY-COHORT-FIXTURE-RECEIPT.json', 'sha256': 'ff2ea7cf60e21c431336f07dbe728ce0d3d173ab40b8bb78e1bec14579ece840', 'bytes': 2876}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/ACTUAL-MOUNT-AND-OPEN-FOOTPRINT-RESULT.json', 'sha256': '16cf0d2f59ef6633e669d533d5a8c673c9389fa42e99eb0b535a588cc09ab802', 'bytes': 217938}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/canonical-integration-preparation-1/ACTIVE-CURRENT287-PIN-EXCLUSION.json', 'sha256': '4e378e5f5f42b565d690efe503aa35c1d4d93dc2d698568ba5c2cb2599ddace4', 'bytes': 188146}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/bounded-correction-1/ACTUAL-PRODUCTION-WHOLE-JOIN.json', 'sha256': '7a0191a235c29356ab48f25fd28e6e33b698ae1bd9a539ab84c795c52fc9993f', 'bytes': 28854}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/bounded-correction-1/ACTUAL-DEBUG-METADATA-ABI.json', 'sha256': '8c0abe8fa626c954d6f10209265895b0c234dea73b7b8dcc5922926065396706', 'bytes': 1263}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json', 'sha256': 'bebe72021c410cddfd8c67dfc086c365d51641e074aca04f87f5450405509316', 'bytes': 24274}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/PRODUCTION-FIRST-FAILURE-1.json', 'sha256': '2fb3a2294e4347bc7eced2aee91ef259778c079779bcbfa5e8f61eda3fb17698', 'bytes': 3145}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/actual-production-capture-1/00-current78-production-Rust-compile/stderr', 'sha256': 'e9a1a83c79078bfecf6bfd2e63cca2705fa1dbfbe16ad7afff3e830d093e0425', 'bytes': 1574}, {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/bounded-correction-1/SOLE-DECLARATION-CORRECTION-AND-LEAF-SCOPE.json', 'sha256': 'bc98b02360a2582bd00d766fa902f2a691079ba117520fa9dafbdbac76dcda3f', 'bytes': 3701}]

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
 for r,data in zip(ROWS,posts):staged.append(stage(r,data,'.m14-process-log-root-stage-'))
 for r in ROWS:checked(r['target'],r['preimage'])
 for r,name in zip(ROWS,staged):
  # Recheck this exact original immediately before replacing its directory entry.
  checked(r['target'],r['preimage'])
  os.replace(name,r['target']);s=Path(r['target']).lstat()
  published.append((r,s.st_dev,s.st_ino));fsyncdir(Path(r['target']).parent)
 for r in ROWS:checked(r['target'],r['staged_postimage'])
 status='ROOT_EXACT2_PROCESS_LOG_SOURCE_INTEGRATION_PASS'
except BaseException as exc:
 status='ROOT_INTEGRATION_FAILED_CONDITIONAL_ROLLBACK'
 for r,dev,ino in reversed(published):
  target=Path(r['target']);s=target.lstat()
  try:
   assert (s.st_dev,s.st_ino)==(dev,ino),'intervening replacement: retain current bytes'
   checked(target,r['staged_postimage'])
   original=checked(r['rollback_preimage']['path'],r['rollback_preimage'])
   tmp=stage(r,original,'.m14-process-log-root-rollback-')
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
result={'scope':__doc__,'status':status,'copies':ROWS,'conditional_rollback':rollback,'remaining_C_callbacks':'vm_range_insert_dump_bridge/dump_tree/optional dtree and other process.c compute remain debt','defaultGCC14_kernel_link_native':False,'no_candidate15_mutation':True}
with (P/'ROOT-INTEGRATION-RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(result))
