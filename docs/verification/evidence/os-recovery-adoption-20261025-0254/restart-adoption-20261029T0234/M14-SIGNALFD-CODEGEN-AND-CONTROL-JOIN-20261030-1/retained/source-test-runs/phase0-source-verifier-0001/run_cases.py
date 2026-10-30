"Functional McKernel OS/apps and Rust/assembly migration only; no security testing."
import importlib.util,sys,json,hashlib,os
from pathlib import Path
b=Path("/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1")
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
phase=module("readonly_phase0",b/"root-install-direct-child-successor-4/phase0.py")
install=module("readonly_install",b/"root-install-direct-child-successor-4/install_source_closure.py")
raw=(b/"root-install-source-10/SOURCE-CLOSURE.json").read_bytes()
fd,ancestry=phase.open_dir(install.SOURCE_DIR)
phase.verify_source(install,fd,raw)
print(json.dumps({"status":"PASS_ACTUAL_READONLY_PHASE0_SOURCE_VERIFIER","files":23,"fd_count":len(os.listdir("/proc/self/fd")),"scope":"DATA consistency only; no root authority/current-free/install proof","mutating_run_not_called":True}))
