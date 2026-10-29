"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No-argument118 interface to separately accepted post-BFD current63; no old-free fallback.
"""
from pathlib import Path
import importlib.util,json
CORE={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/typed_current_boundary.py', 'bytes': 23327, 'sha256': 'f893832e6f3b5a547bf357aa9c6b79525dbe17c64096c50c81f0462eb5b29b90'}
SELECTION={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/next-attempt-after-expired-capture-preparation-1/A3-source-successor-1/UPSTREAM-SELECTION.SOURCE-ONLY.json', 'bytes': 2114, 'sha256': '596600fab7c3e8551c564187cce52e8207ecf088fe4ac618cf74028eeaee5312'}
BINDING=Path(__file__).resolve().parent/'ROOT-CURRENT118-TYPED-BOUNDARY.json'
def _core():
 raw=Path(CORE['path']).read_bytes()
 import hashlib
 assert len(raw)==CORE['bytes'] and hashlib.sha256(raw).hexdigest()==CORE['sha256']
 spec=importlib.util.spec_from_file_location('current118_typed_accepted_boundary',CORE['path'])
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def validate_current():
 module=_core();return module.validate_typed(module.ref(BINDING),SELECTION,module.ref(__file__),CORE)
def observe():
 module=_core();return module.observe(module.ref(BINDING),SELECTION,module.ref(__file__),CORE)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
