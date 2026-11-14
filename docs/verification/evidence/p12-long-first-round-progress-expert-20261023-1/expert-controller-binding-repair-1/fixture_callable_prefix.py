"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact extracted callable actualprefix regression, no effects."""
import ast,hashlib,importlib.util,json,os,sys
from pathlib import Path
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('same_tested_prefix',D/'controller_pre_effect_consumer.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert os.getuid()==os.geteuid()==1000 and sys.executable=='/home/holden/anaconda3/bin/python3'
p=D/'TESTONLY-request-01.json'
try:m.consume(D/'capture_root_LONG.NOT-RELEASED.py',p,hashlib.sha256(p.read_bytes()).hexdigest())
except m.ReachedPreEffect:pass
else:raise AssertionError('positive didnotreachboundary')
old=D.parent/'failure-dfbb-docker-start-1/runtime-successor-1';p=old/'CAPTURE-REQUEST.json'
try:m.consume(old/'capture_root_LONG.NOT-RELEASED.py',p,hashlib.sha256(p.read_bytes()).hexdigest())
except RuntimeError as e:assert str(e)=='exact LONG owner/release paths'
else:raise AssertionError('oldactualfailure accepted')
assert not m.factory_calls
report=dict(scope=__doc__,status='PASS_EXACT_EXTRACTED_CALLABLE_PREFIX_TWO_CHECKS',checks=2,process_factory_calls=0,root_profile_proof=False,final_published_request_consumer=None,native_acceptance=False)
(D/'ACTUAL-CALLABLE-PREFIX-RESULT.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report,sort_keys=True))
