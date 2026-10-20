import hashlib,importlib.util
from pathlib import Path
p=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-compatibility-20261019-1/n3-variant/qmp_capture.py')
if hashlib.sha256(p.read_bytes()).hexdigest()!='5bccd46cdcf8ee6201e28835f5bcbebda6217f9f902f964c5430e70e4b70d741':raise ValueError("pinned imported engine")
s=importlib.util.spec_from_file_location('original_cycle_qmp',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
globals().update({k:v for k,v in vars(m).items() if not k.startswith("__")})
