#!/usr/bin/env python3
"""Functional OS only; no security testing. Read-only source preimage/postimage checks."""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
m=json.loads((D/'SELECTIVE-CANDIDATE-MANIFEST.json').read_bytes())
for group in ('preimages','postimages'):
 for row in m[group].values():
  p=Path(row['path']);assert p.is_file() and not p.is_symlink()
  assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],str(p)
assert not Path('/home/holden/mckernel/kernel/rust/f06_obtain_clone_cpuid.rs').exists()
print(json.dumps(dict(decision='PASS_EXACT_SOURCE_PREIMAGES_PRIVATE_POSTIMAGES_ONLY',changed_source_paths=6,new_Rust_algorithm_bodies=0,runtime_authority=None),sort_keys=True))
