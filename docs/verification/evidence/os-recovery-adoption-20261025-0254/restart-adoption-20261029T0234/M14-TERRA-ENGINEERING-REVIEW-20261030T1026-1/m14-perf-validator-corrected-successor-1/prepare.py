#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,pathlib
O=pathlib.Path(__file__).resolve().parent;A=O.parent
base=A/'m14-configure-quiescence-correction-1/validator.corrected.py';old=A/'m14-perf-mount-validator-successor-1/validator.py'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(base)=='3ec89ea9c8d4d320700a4b5cbf425954807fd8f732dc7c850a63fe301d0a54c2'
assert sha(old)=='70b37a914df8cc94155af052808ef374e1afef18b0c26300399b5242c5dccdc9'
b=base.read_bytes();a=old.read_bytes();marker=b'\n# Source-only exact-one-perf-file model. _collect remains hard-disabled.\n';assert a.count(marker)==1;tail=a[a.index(marker):];out=O/'validator.py';out.write_bytes(b+tail)
assert out.read_bytes()==b+tail
print('PASS exact corrected validator prefix and exact perf-model suffix; previous guards retained')
