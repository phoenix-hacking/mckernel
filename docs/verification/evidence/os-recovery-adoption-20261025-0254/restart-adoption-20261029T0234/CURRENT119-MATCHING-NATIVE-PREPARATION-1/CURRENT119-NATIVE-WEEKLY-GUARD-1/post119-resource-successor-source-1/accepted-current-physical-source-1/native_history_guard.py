"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Adapter for the retained physical-history successor; delegates only native Q guard.
"""
from pathlib import Path
import hashlib,importlib.util,json
GUARD=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-MATCHING-NATIVE-PREPARATION-1/CURRENT119-NATIVE-WEEKLY-GUARD-1/native_operation_guard.py')
SHA='1f89fba32c016346cec9f11ae96fe1e4b0c5e781c307c34bda646ab7c05f92e4'
M=None
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def configure(binding_ref):
 global M
 assert M is None and ref(GUARD)['sha256']==SHA
 spec=importlib.util.spec_from_file_location('native_Q_physical_history_guard',GUARD);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 assert binding_ref==ref(m.BINDING),'exact native operation binding; no readonly alias'
 m.binding_metadata(m.read(binding_ref));M=m
 return None
def guard():
 assert M is not None;return M.guard()
def current_cutoffs():
 assert M is not None;return M.current_cutoffs()
