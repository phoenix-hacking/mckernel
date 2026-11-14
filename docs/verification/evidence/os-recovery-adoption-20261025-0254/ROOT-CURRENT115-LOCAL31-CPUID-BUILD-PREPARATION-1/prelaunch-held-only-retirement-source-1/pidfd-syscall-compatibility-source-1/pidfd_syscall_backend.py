"""Functional OS/apps and Rust migration only; no security testing.
Exact Linux x86_64 LP64 pidfd syscall compatibility; no PID/group signal fallback.
load_backend() validates/loads/types only and NEVER invokes either syscall.
"""
import ctypes,hashlib,os,re,signal,sys
from pathlib import Path
PINS={'header': {'path': '/usr/include/x86_64-linux-gnu/asm/unistd_64.h', 'bytes': 9286, 'sha256': '698d4666c969b0b4d0bed328b4a4f3cab765ec1a9948e0f14751f0ce56d91535'}, 'header_alias': '/usr/include/asm/unistd_64.h', 'libc': {'path': '/usr/lib/x86_64-linux-gnu/libc-2.31.so', 'bytes': 2029592, 'sha256': '53b909551f8e581120ddc2d24cfb5df76c52e3c2e2a5dac0d202b25638b3e902'}}
NR_PIDFD_OPEN=434
NR_PIDFD_SEND_SIGNAL=424
EXPECTED_PID=1815979
MAX_INT=(1<<31)-1

def authenticate():
 assert sys.platform=='linux' and os.uname().machine=='x86_64' and sys.byteorder=='little'
 assert ctypes.sizeof(ctypes.c_long)==ctypes.sizeof(ctypes.c_void_p)==8
 assert ctypes.sizeof(ctypes.c_int)==ctypes.sizeof(ctypes.c_uint)==4
 assert ctypes.c_int(-1).value==-1 and ctypes.c_uint(-1).value==MAX_INT*2+1
 assert Path(PINS['header_alias']).resolve()==Path(PINS['header']['path'])
 for key in ('header','libc'):
  row=PINS[key];p=Path(row['path']);raw=p.read_bytes()
  assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 header=Path(PINS['header']['path']).read_text()
 for name,value in [('pidfd_open',NR_PIDFD_OPEN),('pidfd_send_signal',NR_PIDFD_SEND_SIGNAL)]:
  assert re.findall(r'^#define\s+__NR_'+name+r'\s+(\d+)\s*$',header,re.M)==[str(value)]
 return dict(Linux_x86_64_LP64=True,long_bytes=8,pointer_bytes=8,int_bytes=4,unsigned_int_bytes=4,header=PINS['header'],libc=PINS['libc'],pidfd_open=434,pidfd_send_signal=424)

class Backend:
 def __init__(self):
  self.proof=authenticate();self.library=ctypes.CDLL(PINS['libc']['path'],use_errno=True)
  # Linux x86_64 syscall(long,...): these fixed integer/pointer prototypes match
  # each public syscall ABI. No floats/vector args; libc supplies errno/-1.
  self._open=ctypes.CFUNCTYPE(ctypes.c_long,ctypes.c_long,ctypes.c_int,ctypes.c_uint,use_errno=True)(('syscall',self.library))
  self._send=ctypes.CFUNCTYPE(ctypes.c_long,ctypes.c_long,ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_uint,use_errno=True)(('syscall',self.library))
 def open_pidfd(self,pid):
  assert type(pid) is int and pid==EXPECTED_PID
  ctypes.set_errno(0);value=self._open(ctypes.c_long(NR_PIDFD_OPEN),ctypes.c_int(pid),ctypes.c_uint(0))
  if value==-1:raise OSError(ctypes.get_errno(),'pidfd_open syscall failed; no fallback/retry')
  assert type(value) is int and 0<=value<=MAX_INT
  return value
 def send_sigint(self,fd):
  assert type(fd) is int and 0<=fd<=MAX_INT
  ctypes.set_errno(0);value=self._send(ctypes.c_long(NR_PIDFD_SEND_SIGNAL),ctypes.c_int(fd),ctypes.c_int(signal.SIGINT),ctypes.c_void_p(None),ctypes.c_uint(0))
  if value==-1:raise OSError(ctypes.get_errno(),'pidfd_send_signal failed; no fallback/retry')
  assert value==0

def load_backend():return Backend()
