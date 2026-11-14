"""Functional owned Python harness fixture only; no security testing."""
import ctypes,json,os,sys,time
from pathlib import Path
root=Path(__file__).resolve().parent
# Process-local permission for the sibling owned debugger. No host sysctl.
libc=ctypes.CDLL(None,use_errno=True)
if libc.prctl(0x59616d61,ctypes.c_ulong(-1).value,0,0,0)!=0:
 raise OSError(ctypes.get_errno(),'fixture-only PR_SET_PTRACER_ANY failed')
code='''def recover():
 try:
  raise RuntimeError("MCKERNEL_OWNED_FIXTURE_EXACT_ERROR_20261026")
 except RuntimeError as error:
  print(json.dumps(dict(pid=os.getpid(),ready=True)),flush=True)
  until=time.monotonic()+30
  while not Path(sys.argv[1]).exists() and time.monotonic()<until:
   time.sleep(0.05)
recover()
'''
exec(compile(code,str(root/'FIXTURE-ONLY-EXACT-CO-FILENAME.py'),'exec'))
