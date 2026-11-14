"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
ROOT-only exact two-file atomic source integration, not a compiler/runtime action.
"""
from pathlib import Path
import hashlib,json,os,tempfile
P=Path(__file__).resolve().parent
ROWS=[{'target': '/home/holden/mckernel/arch/x86_64/kernel/cpu.c', 'preimage': {'path': '/home/holden/mckernel/arch/x86_64/kernel/cpu.c', 'sha256': '67dd7ea590ad9c1470ce34434770efa5e8cd7449b5f28d3b4ee5d3e0c96eb348', 'bytes': 95486}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-x86-cpu/canonical-integration-preparation-1/staged/arch/x86_64/kernel/cpu.c', 'sha256': '8c71fe79e003f7aa7ef0f7faf2b31ebf11e65e747abdb0969dc77dbafbd839e9', 'bytes': 95267}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-x86-cpu/candidate/arch/x86_64/kernel/cpu.c', 'sha256': '8c71fe79e003f7aa7ef0f7faf2b31ebf11e65e747abdb0969dc77dbafbd839e9', 'bytes': 95267}, 'mode': 384, 'old_inode': {'device': 66306, 'inode': 47485981, 'nlink': 1, 'uid': 1000, 'gid': 1000}}, {'target': '/home/holden/mckernel/kernel/rust/x86_cpu_helpers.rs', 'preimage': {'path': '/home/holden/mckernel/kernel/rust/x86_cpu_helpers.rs', 'sha256': '59d0723c5d4d35ba63120b59c0422d6bc357246e1146d6cbbd010fe2d727a651', 'bytes': 89419}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-x86-cpu/canonical-integration-preparation-1/staged/kernel/rust/x86_cpu_helpers.rs', 'sha256': 'a6e7465d7924755c97e5d72919a97c2985aacd35cf9db417c4ee981b4d5d071a', 'bytes': 90445}, 'accepted_private_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-x86-cpu/candidate/kernel/rust/x86_cpu_helpers.rs', 'sha256': 'a6e7465d7924755c97e5d72919a97c2985aacd35cf9db417c4ee981b4d5d071a', 'bytes': 90445}, 'mode': 384, 'old_inode': {'device': 66306, 'inode': 47486686, 'nlink': 1, 'uid': 1000, 'gid': 1000}}]
AUTHORITIES=[{'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-diagnostic-collector-successor-1/source/native_diagnostic_container_owner.py', 'sha256': '626bef088a1c8d60c5c41afb88d59faeb55c025c3f11c9d47c649c571e05e2eb', 'bytes': 139652}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-diagnostic-collector-successor-1/COHORT-BINDINGS.json', 'sha256': 'e746c77878591125fc7ad87a90cab5e3ada208f539cccbb06af0b43b8be66b85', 'bytes': 3249}, {'path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-diagnostic-collector-successor-1/ACTUAL-MOUNT-AND-OPEN-FOOTPRINT-RESULT.json', 'sha256': '93d2ff8e8c183a6deb5550a3a736ab318bea0f45e598eb9231fb7529189496ca', 'bytes': 197652}]
def sha(data):return hashlib.sha256(data).hexdigest()
def checked(path,row):
 data=Path(path).read_bytes()
 assert sha(data)==row['sha256'] and len(data)==row['bytes'],path
 return data
# The dispatcher must first confirm these are still its selected active source
# authorities or separately reconcile positive physical retirement. No lease API.
for row in AUTHORITIES:checked(row['path'],row)
for row in ROWS:checked(row['target'],row['preimage'])
inputs=[checked(row['staged_postimage']['path'],row['staged_postimage']) for row in ROWS]
staged=[]
for row,data in zip(ROWS,inputs):
 target=Path(row['target']);fd,name=tempfile.mkstemp(prefix='.m14-cpu-root-stage-',dir=target.parent)
 with os.fdopen(fd,'wb') as stream:
  os.fchmod(stream.fileno(),row['mode'])
  assert stream.write(data)==len(data)
  stream.flush();os.fsync(stream.fileno())
 staged.append((row,name))
# Validate both originals together immediately before the first replacement.
for row in ROWS:checked(row['target'],row['preimage'])
for row,name in staged:
 os.replace(name,row['target'])
 fd=os.open(str(Path(row['target']).parent),os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
for row in ROWS:checked(row['target'],row['staged_postimage'])
result=dict(scope=__doc__,status='ROOT_EXACT2_SOURCE_ATOMIC_INTEGRATION_PASS',copies=ROWS,
 full_GCC14_defaultlink_native=False,remaining_C_callbacks=4)
with (P/'ROOT-INTEGRATION-RESULT.json').open('x') as stream:
 json.dump(result,stream,indent=2);stream.write(chr(10));stream.flush();os.fsync(stream.fileno())
print(json.dumps(result))
