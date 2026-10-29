"""Functional OS pure TEST_ONLY release-shape regression, no security testing.
Synthetic review/publication objects are memory-only; never execution evidence.
"""
from pathlib import Path
import ast,json,hashlib,copy
D=Path(__file__).resolve().parent;src=(D/'retire_exact_current119_stopped_container.py').read_text();tree=ast.parse(src);function=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate_release')
b=json.loads((D/'BINDINGS.json').read_text());files=json.loads((D/'RUNTIME-FILES.json').read_text())
def canonical(v):return(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def ref(p):
 raw=Path(p).read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def need(ok,msg):
 if not ok:raise ValueError(msg)
checkpoint='1'*40
r=dict(schema='mckernel.current119-build.stopped-container-retirement.release.v1',author='/root',decision='GRANT_ONE_EXACT_STOPPED_CURRENT119_CONTAINER_RETIREMENT',maximum_invocations=1,bindings=ref(D/'BINDINGS.json'),files=files,parent_tool_join=b['parent_tool_join'],cid=b['cid'],nonce=b['nonce'],signals_allowed=0,records_released=[],cutoffs=b['cutoffs'],credit_run_id='7f4af94a83b14cc08f97401f5891d965',credit_ceiling='57774.852125',minimum_cumulative_spent='22812.3311',billing_mode='included_only',allow_prepaid_fallback=False,credit_metadata_only=True,Root_attests_no_unlisted_intervening_operation=True,actual_account_identity_operation_admission_accepted=True,current_ledger=b['current_ledger'],source_review='TEST_ONLY_SOURCE',source_checkpoint=checkpoint,fetched_source_verified=True,source_publication='TEST_ONLY_PUBLICATION',execution_review='TEST_ONLY_EXECUTION',output=str(D/'actual-retirement-current119-root1'))
source=dict(decision='PASS_SOURCE',independent=True,implementation_ownership=False,files=files,bindings=r['bindings'],reviewer='/root/TEST_ONLY',source_checkpoint=checkpoint)
publication=dict(status='PASS_FETCHED_TEST_ONLY_MEMORY',commit=checkpoint,runtime_authority=None,rows=[dict(actual=x)for x in files.values()])
def authenticated(x,declared_json=False):
 if x=='TEST_ONLY_SOURCE':return source
 if x=='TEST_ONLY_PUBLICATION':return publication
 if x=='TEST_ONLY_EXECUTION':return dict(decision='PASS_EXECUTION',independent=True,implementation_ownership=False,reviewer='/root/TEST_ONLY',release_payload_sha256=hashlib.sha256(canonical({k:v for k,v in r.items()if k!='execution_review'})).hexdigest())
 assert type(x)is dict and ref(x['path'])==x
 raw=Path(x['path']).read_bytes();return json.loads(raw)if declared_json else raw
import re,os
ns=dict(D=D,Path=Path,reference=ref,need=need,authenticated=authenticated,canonical=canonical,hashlib=hashlib,re=re,os=os);exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),'TEST_ONLY_RELEASE_SHAPE','exec'),ns)
assert ns['validate_release'](r,b,files)==D/'actual-retirement-current119-root1'
for key,value in [('signals_allowed',1),('records_released',['unrelated']),('allow_prepaid_fallback',True),('cid','0'*64),('maximum_invocations',2)]:
 bad=copy.deepcopy(r);bad[key]=value
 try:ns['validate_release'](bad,b,files)
 except ValueError:pass
 else:raise AssertionError(key)
bad=copy.deepcopy(b);bad['current_build_ledger_entry']['artifact_acceptance']=True
try:ns['validate_release'](r,bad,files)
except ValueError:pass
else:raise AssertionError('entire actual typed119 entry drift')
(D/'PURE-RELEASE-SHAPE.json').write_text(json.dumps(dict(status='PASS_TEST_ONLY_PURE_RELEASE_SHAPE',positive=1,negative=6,synthetic_reviews_not_execution_evidence=True,no_effects=True),indent=2)+'\n');print('PASS release-shape 1positive6negative')
