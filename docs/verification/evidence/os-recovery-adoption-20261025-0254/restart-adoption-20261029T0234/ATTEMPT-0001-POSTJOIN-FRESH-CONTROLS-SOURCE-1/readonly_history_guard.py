"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Adapter for the retained physical-history successor; delegates only readonly Q guard.
"""
from pathlib import Path
import hashlib,importlib.util,json
GUARD=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/ATTEMPT-0001-POSTJOIN-FRESH-CONTROLS-SOURCE-1/readonly_operation_guard.py')
SHA='801b552c7002208f87df3da97a2058c205c00c62f1ffb03c918e0e9ae79b64d8'
M=None
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def configure(binding_ref):
 global M
 assert M is None and ref(GUARD)['sha256']==SHA
 spec=importlib.util.spec_from_file_location('readonly_Q_physical_history_guard',GUARD);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 assert binding_ref==ref(m.BINDING),'exact distinct readonly operation binding'
 m.binding_metadata(m.read(binding_ref));M=m
 return None
def guard():
 assert M is not None;return M.guard()
def current_cutoffs():
 assert M is not None;return M.current_cutoffs()
