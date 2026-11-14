"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Configured readonly facade to the unchanged emitted BFD operation consumer.
"""
from pathlib import Path
import hashlib,importlib.util,json
D=Path(__file__).resolve().parent
OPERATION='bfd-current-default-two-tools'
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
_BINDING=None

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def configure(r):
 global _BINDING
 assert _BINDING is None and ref(r['path'])==r,'one exact immutable BFD facade configuration'
 b=json.loads(Path(r['path']).read_bytes());pins=json.loads((D/'FROZEN-COHORT-PINS.json').read_bytes())
 assert b['author']=='/root' and b['operation']==OPERATION and b['runtime_guard']==ref(Path(pins['admission'])/'runtime_guard.py')
 assert b['operation_bindings']==ref(Path(pins['admission'])/'ROOT-OPERATION-BINDINGS.json')
 assert b['authorized_clamps']==pins['clamps']
 _BINDING=(r,b)
def binding():
 assert _BINDING is not None
 r,b=_BINDING;assert ref(r['path'])==r and json.loads(Path(r['path']).read_bytes())==b
 return b
def guard():
 b=binding();r=b['runtime_guard'];assert ref(r['path'])==r
 s=importlib.util.spec_from_file_location('unchanged_BFD_runtime_guard',r['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 now=m.guard();assert all(a<c for a,c in zip(now,current_cutoffs()));return now
def current_cutoffs():
 b=binding();op=json.loads(Path(b['operation_bindings']['path']).read_bytes());r=op['successor'];assert ref(r['path'])==r
 limits=json.loads(Path(r['path']).read_bytes())['operation_cutoffs']
 return [min(v) for v in zip(limits,b['authorized_clamps'])]
