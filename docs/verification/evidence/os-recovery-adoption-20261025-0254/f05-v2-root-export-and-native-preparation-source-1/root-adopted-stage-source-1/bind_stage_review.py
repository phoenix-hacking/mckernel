"""Functional OS/apps and Rust migration only; no security testing.
Root data-only review binding. No stage, compiler, container, guest or nonce.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
STAGER_SHA='9d0dc6c96dd722cf36270c4dde59006e2bd43174b30df17ea50f6560ea36e034'
INPUTS_SHA='23b6140f31c9d1451e3e5ac18e0c04b0a6d20abd6a333d9264da93e85daf58bb'
FROZEN_SHA='d41ea260caf431ceabb211da3281adeabc870d9d99292946efe31133a611b369'
if __name__=='__main__':
 p=argparse.ArgumentParser(allow_abbrev=False)
 p.add_argument('--review',required=True,type=Path)
 p.add_argument('--review-sha256',required=True)
 a=p.parse_args()
 assert a.review.is_absolute() and a.review.resolve(strict=True)==a.review and not a.review.is_symlink()
 raw=a.review.read_bytes();assert hashlib.sha256(raw).hexdigest()==a.review_sha256
 review=dict(path=str(a.review),size=len(raw),sha256=a.review_sha256,mode=a.review.stat().st_mode)
 raw=(HERE/'F05-STAGING-INPUTS.SOURCE-ONLY.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==INPUTS_SHA
 data=json.loads(raw);assert data['stage_review'] is None;data['stage_review']=review
 frozen=(HERE/'FROZEN-F05-COMPOSITION.json').read_bytes();assert hashlib.sha256(frozen).hexdigest()==FROZEN_SHA
 source=HERE/'stage_bound_v2_current110.py';raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==STAGER_SHA
 spec=importlib.util.spec_from_file_location('f05_current110_source_only_review_binding',source)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.bound_adapter().validate(json.loads(frozen),data,final=True)
 out=HERE/'F05-STAGING-INPUTS.FINAL-BOUND.json'
 with out.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
 print(json.dumps(dict(status='FINAL_DATA_BOUND_NOT_MATERIALIZED_NOT_RUNTIME_RELEASE',path=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),runtime_authority=None)))
