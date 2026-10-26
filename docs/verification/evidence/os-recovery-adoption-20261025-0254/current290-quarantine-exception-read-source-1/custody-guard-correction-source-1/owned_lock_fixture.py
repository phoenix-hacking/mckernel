"""Functional own-harness lock fixture only; no security testing."""
import ctypes,fcntl,json,os,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
libc=ctypes.CDLL(None,use_errno=True)
if libc.prctl(0x59616d61,ctypes.c_ulong(-1).value,0,0,0)!=0:raise OSError(ctypes.get_errno(),'fixture PR_SET_PTRACER_ANY')
lock_fd=os.open(sys.argv[2],os.O_RDONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
fcntl.flock(lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:
 code='''def recover():
 try:
  raise RuntimeError("MCKERNEL_OWNED_FIXTURE_LOCKED_ERROR_20261026")
 except RuntimeError as error:
  print(json.dumps(dict(pid=os.getpid(),ready=True,lock_fd=lock_fd,lock_path=sys.argv[2])),flush=True)
  until=time.monotonic()+30
  while not Path(sys.argv[1]).exists() and time.monotonic()<until:
   time.sleep(0.05)
recover()
'''
 exec(compile(code,str(root/'FIXTURE-ONLY-EXACT-CO-FILENAME.py'),'exec'))
finally:os.close(lock_fd)
