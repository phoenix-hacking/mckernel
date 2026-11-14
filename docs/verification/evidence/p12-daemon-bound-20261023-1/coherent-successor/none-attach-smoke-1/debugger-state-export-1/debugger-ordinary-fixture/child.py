# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import ctypes,json,os,time
from pathlib import Path
from types import SimpleNamespace as NS
D=Path(__file__).resolve().parent
libc=ctypes.CDLL(None,use_errno=True)
assert libc.prctl(0x59616d61,os.getppid(),0,0,0)==0,ctypes.get_errno()
lock=os.open(D/'fixture.lock',os.O_RDWR|os.O_CREAT|os.O_EXCL,0o600)
stat=os.fstat(lock)
start=int(Path('/proc/self/stat').read_text().rpartition(') ')[2].split()[19])
ledger=NS(pending=set(),final_reap_records=[],errors=[])
owner=NS(nonce='7247e16d234147afa148cd0ef24206d4',owner_sha='a15680bb1a50d05bc8ee167ca20b0c1d3e34b8dc5fc1d1bdd593f4dc4f31eefe',
 lock=lock,pending_evidence=[(D/'fixture-evidence',b'controlled fixture bytes')],pending_bytes=24,
 failure=ValueError('controlled fixture failure'),backend=NS(children=ledger),create_issued=True,create_completed=False,
 container=None,sequence=7,absent=False,may_exist=True,cleaning=False,command_deadline=None,retirement_sequence=0,
 owner_queued=True,signal_number=None)
# Source-adapter metadata only: no actual owner module/method is imported or invoked.
__file__='/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/source/native_diagnostic_container_owner.py'
def execute_owner(owner):
 delay=1;recoveries=2
 (D/'ready.json').write_text(json.dumps(dict(pid=os.getpid(),parent=os.getppid(),start=start,lock_device=stat.st_dev,lock_inode=stat.st_ino)))
 while True:time.sleep(1)
execute_owner(owner)
