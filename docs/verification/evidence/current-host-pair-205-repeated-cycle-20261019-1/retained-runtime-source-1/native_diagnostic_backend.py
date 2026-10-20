import hashlib,importlib.util
from pathlib import Path
p=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-compatibility-20261019-1/n3-variant/native_diagnostic_backend.py')
if hashlib.sha256(p.read_bytes()).hexdigest()!='cd0759c926876483665065cb320b9daf7d7c6b32f56e561805b4b0343f60d614':raise ValueError("pinned imported engine")
s=importlib.util.spec_from_file_location('original_cycle_backend',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
globals().update({k:v for k,v in vars(m).items() if not k.startswith("__")})
