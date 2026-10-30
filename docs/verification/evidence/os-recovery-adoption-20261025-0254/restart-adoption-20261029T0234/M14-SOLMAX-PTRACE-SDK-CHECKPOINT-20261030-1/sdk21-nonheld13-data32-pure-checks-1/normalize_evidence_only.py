"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Normalize previously observed evidence only; not adoption or SDK/native work.
"""
import hashlib,importlib.util,json,os
from pathlib import Path
D=Path(__file__).resolve().parent;B=D.parent
MODULE=B/'sdk21-nonheld13-ledger-converter-source-1/sdk13_data32_ledger_converter.py'
RECEIPT=B/'sdk21-nonheld13-data32-source-map-1/rust157-joint-observation-1/receipt-run/RUST157-JOINT-RECEIPT.ACTUAL.json'
REVIEW=B/'sdk21-nonheld13-ledger-converter-source-1/INDEPENDENT-DATA32-ASSOCIATION-SNAPSHOT-REVIEW.md'
MODULE_SHA='36280257a6faf3d2ce99b3c018f16bca092d1ed124838ab99dda2edf94cefe3f'
RECEIPT_SHA='4deccc37096638e0bf7d8ef4527cda16a1bfdc0c48d8daa87c510a2521a0285c'
def read_bound(path,expected):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('input digest differs: '+str(path))
 return raw
read_bound(MODULE,MODULE_SHA);raw=read_bound(RECEIPT,RECEIPT_SHA)
read_bound(REVIEW,'760626dbf6d5b645db2da0f1a7e8a535e6e44557af542441d68170042de24441')
spec=importlib.util.spec_from_file_location('data32_converter',MODULE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
out=m.assemble_candidate(raw,RECEIPT_SHA)
# The review file is linked as evidence only; it supplies no live authority.
out['provenance']['independent_source_review']={'path':str(REVIEW),'sha256':hashlib.sha256(REVIEW.read_bytes()).hexdigest(),'scope':'evidence-only, no live adoption'}
blob=(json.dumps(out,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
p=D/'converter'/'NORMALIZED-PROPOSED.json'
with p.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
print(json.dumps({'status':'PROPOSED_EVIDENCE_DATA_NO_LIVE_ADOPTION','path':str(p),'output_sha256':hashlib.sha256(blob).hexdigest(),'prehashed_trees_sha256':out['prehashed_trees_sha256'],'authority':None,'live_review':None},sort_keys=True))
