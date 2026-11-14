"""Functional OS/apps and Rust migration only; no security testing.
Root data-only review binding. No stage, compiler, container, guest or nonce.
"""
from pathlib import Path
import argparse,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
STAGER_SHA='53d9bca0a07775c97a55719e19a57b2eb5eec3f3cffc0f5a2acc24c1f6f30d93'
INPUTS_SHA='13cd7dc185883ddea05abae6855271c09f1c336fcd4b002f8bdedb117524cd7b'
FROZEN_SHA='713354bb732c1be3424912cc55dbc08c6df3ad8889abc3e8090922718c3ede48'
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
 source=HERE/'stage_current109_f05_specific.py';raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==STAGER_SHA
 spec=importlib.util.spec_from_file_location('f05_current109_source_only_review_binding',source)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 module.validate(json.loads(frozen),data,final=True)
 out=HERE/'F05-STAGING-INPUTS.FINAL-BOUND.json'
 with out.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
 print(json.dumps(dict(status='FINAL_DATA_BOUND_NOT_MATERIALIZED_NOT_RUNTIME_RELEASE',path=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),runtime_authority=None)))
