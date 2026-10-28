#!/usr/bin/env python3
"""Functional OS only; no security testing. Loads/types libc; ZERO pidfd/signal/holder calls."""
from pathlib import Path
import importlib.util,json,sys,hashlib
D=Path(__file__).resolve().parent;p=D/'pidfd_syscall_backend.py'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='da4427225d0660fef7139f7af33e4175c464caff4dd265175eed9dda5d909994'
spec=importlib.util.spec_from_file_location('pure_compatibility_precheck',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
b=m.load_backend()
assert b._open.restype is m.ctypes.c_long and b._send.restype is m.ctypes.c_long
assert b._open.argtypes==(m.ctypes.c_long,m.ctypes.c_int,m.ctypes.c_uint)
assert b._send.argtypes==(m.ctypes.c_long,m.ctypes.c_int,m.ctypes.c_int,m.ctypes.c_void_p,m.ctypes.c_uint)
print(json.dumps(dict(decision='PASS_INTERPRETER_HEADER_LIBC_TYPED_API_PRECHECK_ONLY',interpreter=sys.executable,version=sys.version,backend_sha256='da4427225d0660fef7139f7af33e4175c464caff4dd265175eed9dda5d909994',proof=b.proof,syscall_symbol_loaded=True,pidfd_syscalls=0,signals=0,holder_queries=0),sort_keys=True))
