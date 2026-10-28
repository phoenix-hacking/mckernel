#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only nine-path CURRENT114 preflight; no canonical/runtime/compiler operation.
"""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent
m=json.loads((D/'SELECTIVE-SOURCE-RECIPE.json').read_bytes())
for row in m['files']:
 pre=row['canonical_preimage']
 if pre is None:assert not (Path('/home/holden/mckernel')/row['relative']).exists()
 for r in [pre,row['candidate'],row['patch']]:
  if r is None:continue
  p=Path(r['path']);assert p.is_file() and not p.is_symlink()
  assert p.stat().st_size==r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],str(p)
r=json.loads((D/'NEXT115-COMMAND-RECIPE.NOT-GRANTED.json').read_bytes())
for row in r['retained_inputs']:
 a=row['actual_current114'];p=Path(a['path']);assert p.stat().st_size==a['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256']
assert len(m['files'])==9 and len(r['commands'])==4 and len(r['retained_inputs'])==8
print(json.dumps(dict(decision='PASS_NINE_PATH_SOURCE_AND_EIGHT_RETAINED_INPUTS_ONLY',source_paths=9,new_objects=3,compiler_link_commands=4,actual_authority=None),sort_keys=True))
