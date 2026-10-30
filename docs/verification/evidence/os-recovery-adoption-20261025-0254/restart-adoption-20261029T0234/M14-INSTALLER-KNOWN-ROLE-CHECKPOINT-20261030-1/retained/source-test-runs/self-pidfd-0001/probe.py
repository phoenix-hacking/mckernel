"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Check only this disposable process's pidfd APIs; signal zero delivers no signal.
"""
from pathlib import Path
import os,sys,types,hashlib,json,fcntl
source=Path("/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-source-10/package/pidfd_compat.py");expected='068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'
raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected
module=types.ModuleType('reviewed_pidfd_compat');module.__file__=str(source)
exec(compile(raw,str(source),'exec'),module.__dict__)
assert module.fallback_supported()
pid=os.getpid();fd=None;closed=False
try:
 fd=module.open_pidfd(pid,0)
 info=Path('/proc/self/fdinfo',str(fd)).read_text()
 actual_pid=int(next(line.split(':',1)[1].strip() for line in info.splitlines() if line.startswith('Pid:')))
 assert actual_pid==pid
 assert os.readlink('/proc/self/fd/'+str(fd))=='anon_inode:[pidfd]'
 module.send_signal(fd,0)
 os.close(fd);closed=True
 print(json.dumps({'scope':__doc__,'status':'PASS_REAL_SELF_PIDFD_ZERO_SIGNAL','pid':pid,'pidfd_target':actual_pid,'used_native_open':callable(module._native_open()),'used_native_signal':callable(module._native_signal()),'descriptor_closed':closed,'other_pid_targeted':False,'signal_delivered':False}))
finally:
 if fd is not None and not closed:
  # One attempt only; process termination is the external descriptor boundary.
  try:os.close(fd)
  except OSError:pass
