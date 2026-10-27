"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-dispatched ordinary manifest-only staging; no overlay, nonce, guest or clock.
"""
from pathlib import Path
import hashlib,json,os
A=Path(__file__).resolve().parent
b=json.loads((A/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json').read_bytes())
r=b['offline_manifest'];raw=Path(r['path']).read_bytes()
assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
# Fixed new scope: no previous stage/parent/attempt is reused or replaced.
scratch=Path('/home/holden/mckernel-work/scratch/fp26eb-native1')
assert not os.path.lexists(scratch) and not (A/'ACTUAL-SCRATCH-MANIFEST-STAGE.json').exists()
scratch.mkdir(mode=0o755);p=scratch/'p';p.mkdir(mode=0o700)
manifest=scratch/'m.json'
with manifest.open('xb') as f:f.write(raw)
manifest.chmod(0o400)
assert manifest.read_bytes()==raw
stage=dict(scope=b['scope'],source_manifest=r,scratch_manifest=dict(path=str(manifest),bytes=len(raw),sha256=r['sha256']),planned_attempt_parent=str(p),runtime_authority=None,nonce=None)
with (A/'ACTUAL-SCRATCH-MANIFEST-STAGE.json').open('x') as f:json.dump(stage,f,indent=2);f.write('\n')
print(json.dumps(stage))
