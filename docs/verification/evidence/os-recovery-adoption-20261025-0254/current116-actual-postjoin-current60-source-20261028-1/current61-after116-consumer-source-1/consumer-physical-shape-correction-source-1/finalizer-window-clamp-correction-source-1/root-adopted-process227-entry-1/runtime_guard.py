"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No-argument guard facade; exact configuration comes from sealed static input.
"""
from pathlib import Path
import hashlib,importlib.util,json
A=Path(__file__).resolve().parent
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
ADAPTER_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-operation-guards-source-20261028-1/original227_guard_adapter.py', 'bytes': 3004, 'sha256': '307993c2dfdc44982386e5c3f8c411b3546e16ba0ecc87447ef12551101cba9f'}
_bound=None
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def binding_reference():return ref(A/'ROOT-ACTUAL-OPERATION-GUARD-BINDING.json')
def configured():
 global _bound
 binding=json.loads((A/'ROOT-ACTUAL-OPERATION-GUARD-BINDING.json').read_bytes())
 assert binding['author']=='/root' and binding['schema']=='mckernel.original227.configured-guard-binding.v1'
 assert binding['runtime_facade']==ref(__file__) and binding['adapter']==ADAPTER_REF
 assert ref(ADAPTER_REF['path'])==ADAPTER_REF
 config=binding['configuration'];assert ref(config['path'])==config
 reviewref=binding['independent_review'];assert ref(reviewref['path'])==reviewref
 review=json.loads(Path(reviewref['path']).read_bytes())
 assert review['independent'] is True and review['implementation_ownership'] is False
 assert review['decision']=='PASS_EXACT_ORIGINAL227_GUARD_CONFIGURATION_BINDING'
 for key in ['runtime_facade','adapter','configuration']:assert review[key]==binding[key]
 if _bound is None:
  spec=importlib.util.spec_from_file_location('sealed_original227_operation_guard',ADAPTER_REF['path']);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.configure(config);_bound=(binding_reference(),m)
 assert _bound[0]==binding_reference()
 return _bound[1]
def guard():return configured().guard()
def current_cutoffs():return configured().current_cutoffs()
