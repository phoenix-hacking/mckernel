"""Functional OS source/hash checks only; no security testing, execution or writes."""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent
m=json.loads((D/'SELECTIVE-EIGHT-SOURCE-MAP.json').read_text())
def check(r):
 b=Path(r['path']).read_bytes();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
for row in m['writes']:
 if row['preimage']:check(row['preimage'])
 else:assert not (Path('/home/holden/mckernel')/row['relative']).exists()
 check(row['postimage']);check(row['frozen_input'])
for row in m['Rust_files']:check(row['source'])
p=json.loads((D/'MINIMAL-PRODUCTION-CONTINUATION.NOT-GRANTED.json').read_text())
for row in p['retained_inputs']:check(row['source'])
print('PASS exact8preimages/8postimages/121Rust/8retainedobjects; no execution')
