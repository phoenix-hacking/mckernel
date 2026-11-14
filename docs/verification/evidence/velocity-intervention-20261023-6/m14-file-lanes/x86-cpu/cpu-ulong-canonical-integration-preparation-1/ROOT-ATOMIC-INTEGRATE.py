"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root exactCPUlogger2file per-file atomicintegration; conditional owninode rollback only.
"""
from pathlib import Path
import hashlib,json,os,tempfile
P=Path(__file__).resolve().parent
ROWS=[{'target': '/home/holden/mckernel/arch/x86_64/kernel/cpu.c', 'preimage': {'path': '/home/holden/mckernel/arch/x86_64/kernel/cpu.c', 'sha256': '8c71fe79e003f7aa7ef0f7faf2b31ebf11e65e747abdb0969dc77dbafbd839e9', 'bytes': 95267}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/cpu-ulong-canonical-integration-preparation-1/staged/arch/x86_64/kernel/cpu.c', 'sha256': '2d29bca555936a213f0a7296a302ec57b55c575536c33a58285b07b203390eca', 'bytes': 95484}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-cpu-log-next/candidate/arch/x86_64/kernel/cpu.c', 'sha256': '2d29bca555936a213f0a7296a302ec57b55c575536c33a58285b07b203390eca', 'bytes': 95484}, 'rollback_preimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/cpu-ulong-canonical-integration-preparation-1/preimages/arch/x86_64/kernel/cpu.c', 'sha256': '8c71fe79e003f7aa7ef0f7faf2b31ebf11e65e747abdb0969dc77dbafbd839e9', 'bytes': 95267}, 'mode': 384, 'uid': 1000, 'gid': 1000, 'observed_old_inode': {'device': 66306, 'inode': 47459703, 'nlink': 1}}, {'target': '/home/holden/mckernel/kernel/rust/x86_cpu_helpers.rs', 'preimage': {'path': '/home/holden/mckernel/kernel/rust/x86_cpu_helpers.rs', 'sha256': 'a6e7465d7924755c97e5d72919a97c2985aacd35cf9db417c4ee981b4d5d071a', 'bytes': 90445}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/cpu-ulong-canonical-integration-preparation-1/staged/kernel/rust/x86_cpu_helpers.rs', 'sha256': '26180e00c1d6673aa600f0ec9afed5d100ca6e0c39af803c3328e58f8cc88fb9', 'bytes': 91270}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-cpu-log-next/candidate/kernel/rust/x86_cpu_helpers.rs', 'sha256': '26180e00c1d6673aa600f0ec9afed5d100ca6e0c39af803c3328e58f8cc88fb9', 'bytes': 91270}, 'rollback_preimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/cpu-ulong-canonical-integration-preparation-1/preimages/kernel/rust/x86_cpu_helpers.rs', 'sha256': 'a6e7465d7924755c97e5d72919a97c2985aacd35cf9db417c4ee981b4d5d071a', 'bytes': 90445}, 'mode': 384, 'uid': 1000, 'gid': 1000, 'observed_old_inode': {'device': 66306, 'inode': 47484786, 'nlink': 1}}]
AUTHORITIES=[{'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/source/native_diagnostic_container_owner.py', 'sha256': '57600f1c92d2075ee85d6a52949f11ae69c99dbd122087c227bab28178caedb6', 'bytes': 147559}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/COHORT-BINDINGS.json', 'sha256': 'b5aa82c50bdd34f15d88275d1d12540a5ee194291bedba4e670b06169f284ea8', 'bytes': 3219}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/ACTUAL-MOUNT-AND-OPEN-FOOTPRINT-RESULT.json', 'sha256': '16cf0d2f59ef6633e669d533d5a8c673c9389fa42e99eb0b535a588cc09ab802', 'bytes': 217938}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/controller_pre_effect_consumer.py', 'sha256': 'd069b0d6d8562dda0f70fd52478ed63703a01a8b92d6a869f32e9c2f43a4d0fa', 'bytes': 4139}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1/SOURCE-PREPARATION-READINESS.PENDING.json', 'sha256': '3fe8bcfdc28fc2dea1f3668f0e00e4d72413555a0c69d5355934ea746babce8e', 'bytes': 2582}]
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
 for r,data in zip(ROWS,posts):staged.append(stage(r,data,'.m14-cpu-ulong-root-stage-'))
 for r in ROWS:checked(r['target'],r['preimage'])
 for r,name in zip(ROWS,staged):
  # Recheck this exact original immediately before replacing its directory entry.
  checked(r['target'],r['preimage'])
  os.replace(name,r['target']);s=Path(r['target']).lstat()
  published.append((r,s.st_dev,s.st_ino));fsyncdir(Path(r['target']).parent)
 for r in ROWS:checked(r['target'],r['staged_postimage'])
 status='ROOT_EXACT2_CPU_ULONG_SOURCE_INTEGRATION_PASS'
except BaseException as exc:
 status='ROOT_INTEGRATION_FAILED_CONDITIONAL_ROLLBACK'
 for r,dev,ino in reversed(published):
  target=Path(r['target']);s=target.lstat()
  try:
   assert (s.st_dev,s.st_ino)==(dev,ino),'intervening replacement: retain current bytes'
   checked(target,r['staged_postimage'])
   original=checked(r['rollback_preimage']['path'],r['rollback_preimage'])
   tmp=stage(r,original,'.m14-cpu-ulong-root-rollback-')
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
result={'scope':__doc__,'status':status,'copies':ROWS,'conditional_rollback':rollback,'all_other_C_debt_preserved':True,'defaultGCC14_kernel_link_native':False,'no_candidate15_mutation':True}
with (P/'ROOT-INTEGRATION-RESULT.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(result))
