"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only exact review-reference binding; does not execute materialization.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
if __name__=='__main__':
 p=argparse.ArgumentParser(allow_abbrev=False);p.add_argument('--review',required=True,type=Path);a=p.parse_args()
 assert a.review.is_absolute() and a.review.resolve(strict=True)==a.review
 raw=a.review.read_bytes();review=dict(path=str(a.review),size=len(raw),sha256=hashlib.sha256(raw).hexdigest(),mode=a.review.stat().st_mode)
 data=json.loads((HERE/'26EB-FP-STAGING-INPUTS.SOURCE-ONLY.json').read_bytes());assert data['stage_review'] is None
 data['stage_review']=review
 spec=importlib.util.spec_from_file_location('bound26eb_fp_static_only',HERE/'stage_bound_26eb_fp.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 adapter=m.bound_adapter();adapter.validate(json.loads((HERE/'FROZEN-FP-COMPOSITION.json').read_bytes()),data,final=True)
 out=HERE/'26EB-FP-STAGING-INPUTS.FINAL-BOUND.json'
 with out.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
 print(json.dumps(dict(status='FINAL_DATA_BOUND_NOT_MATERIALIZED',path=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),runtime_authority=None)))
