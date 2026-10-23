"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
ROOT-only exact two-file atomic source integration, not a compiler/runtime action.
"""
from pathlib import Path
import hashlib,json,os,tempfile
P=Path(__file__).resolve().parent
ROWS=[{'target': '/home/holden/mckernel/arch/x86_64/kernel/memory.c', 'preimage': {'path': '/home/holden/mckernel/arch/x86_64/kernel/memory.c', 'sha256': 'e52b056f783641ab8b48a5a0d6cec793b89c764f8a5ba3b0f16550eac2fd615f', 'bytes': 86355}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-3/m14-walk-l4/canonical-integration-preparation-1/staged/arch/x86_64/kernel/memory.c', 'sha256': '0da70d7cbc80dc96fe4a6643374c8b0e00c0b3dc02796551115d3d97cf0e3889', 'bytes': 86744}, 'mode': 384, 'old_inode': {'device': 66306, 'inode': 47459703, 'nlink': 1, 'uid': 1000, 'gid': 1000}}, {'target': '/home/holden/mckernel/kernel/rust/x86_memory_helpers.rs', 'preimage': {'path': '/home/holden/mckernel/kernel/rust/x86_memory_helpers.rs', 'sha256': '8d9cf2a72a5fcca67edf25e99f20c84fb2aaac4d6c7f95ec73a8e7de9d46b1cc', 'bytes': 196605}, 'staged_postimage': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-3/m14-walk-l4/canonical-integration-preparation-1/staged/kernel/rust/x86_memory_helpers.rs', 'sha256': 'ec83294bfbdb9b649b6cc313c017d0eef934dbfc638a0a84b257b50b30539c0d', 'bytes': 196974}, 'mode': 384, 'old_inode': {'device': 66306, 'inode': 47459989, 'nlink': 1, 'uid': 1000, 'gid': 1000}}]
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
 target=Path(row['target']);fd,name=tempfile.mkstemp(prefix='.m14-walk-l4-root-stage-',dir=target.parent)
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
 full_GCC14_defaultlink_native=False,remaining_private_C_callback_chain_debt=True)
with (P/'ROOT-INTEGRATION-RESULT.json').open('x') as stream:
 json.dump(result,stream,indent=2);stream.write(chr(10));stream.flush();os.fsync(stream.fileno())
print(json.dumps(result))
