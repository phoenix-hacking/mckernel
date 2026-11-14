"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-bind existing reviewed adapter; no changed composition/controller algorithm.
Calling this CLI materializes CPIO and requires Root's separate actual grant.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
BINDINGS_SHA='8782f1cf64f62b44d3b9534ee620ce56b2e452051635bbcab2d86b6a4e1cb0b6'

def bound_adapter():
 raw=(HERE/'ADAPTER-DATA-BINDINGS.json').read_bytes()
 assert hashlib.sha256(raw).hexdigest()==BINDINGS_SHA
 data=json.loads(raw);r=data['adapter_source'];p=Path(r['path']);source=p.read_bytes()
 assert len(source)==r['size'] and hashlib.sha256(source).hexdigest()==r['sha256'] and p.stat().st_mode==r['mode']
 frozen=(HERE/'FROZEN-FP-COMPOSITION.json').read_bytes();assert hashlib.sha256(frozen).hexdigest()==data['frozen_data']['sha256']
 spec=importlib.util.spec_from_file_location('byte_exact_reviewed_fp_adapter',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 # Only the adapter's already-supported frozen data location/digest bindings.
 m.HERE=HERE;m.FROZEN_SHA=data['frozen_data']['sha256'];return m

if __name__=='__main__':
 p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--inputs',required=True);p.add_argument('--inputs-sha256',required=True);a=p.parse_args()
 print(json.dumps(bound_adapter().stage(a.inputs,a.inputs_sha256)))
