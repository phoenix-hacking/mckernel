"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual retained producer→full original manifest consumer; no future authority substitutes.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json

D=Path(__file__).resolve().parent
E=D.parent.parent
BASE=E/'m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1'
R=D
checks=[]
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(r):
 assert ref(r['path'])==r;return json.loads(Path(r['path']).read_bytes())
def load(p,n):
 spec=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
q=json.loads((R/'ROOT61-227-INPUT.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
ledger=checked(q['current_ledger']);free=checked(q['latest_free'])
assert ledger['latest_accepted_free_boundary']==q['latest_free'] and len(ledger['consumed_nonces'])==70
assert free['current_free'] is True and free['normal_owned_retirement'] is True
checks.append('actual Root61/newfree6c83 and69consumed boundary')
st=json.loads((BASE.parent/'actual-host-bound-source-1/STATIC-NATIVE-BINDINGS.HOST-BOUND.NOT-RELEASED.json').read_bytes())
manifest=checked(q['offline_manifest']);stage=checked(q['scratch_manifest_stage']);checked(stage['scratch_manifest'])
assert stage['source_manifest']==q['offline_manifest'] and stage['scratch_manifest']==q['manifest']
assert stage['nonce'] is None and stage['runtime_authority'] is None
checks.append('retained real manifest/stage6cec and scratch bytes')
owner=Path(st['owner_source']['path']);assert ref(owner)==st['owner_source']
validator=owner.with_name('native_diagnostic.py');assert ref(validator)['sha256']=='529830adcd6fafa13979bf6036b2812c88630c5e0112ce4d80f9fc28cc30d4da'
v=load(validator,'actual_original227_full_manifest_validator')
validated=v.load_manifest(q['offline_manifest']['path']);v.load_manifest(q['manifest']['path'])
checks.append('unchanged5298 full original validator on actual source and scratch manifests')
assert validated['case_id']=='P-M01-02-child-SIGTERM-and-exec-recovery-227B'
assert validated['artifacts']['mcexec']['sha256']=='e5d18169ee50581274b374bba17fcefebe39e828885f367bfee182beaa3df756'
assert validated['artifacts']['mckernel_image']['sha256']=='60e62f97ef48ecaf14174af1c5b75d7181969f439c1b45c618d6c16d4bc40d57'
assert validated['staging']['collector']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
assert [r['sha256'] for r in validated['modules'][1:]]==['887dc3567e6035c921588e61b45b41a8ef32a972d142fe2ba82ec48442353b12','57546af5110c0674b307e5ac5a328228abbe784f890f69521db5f594f21f6ae8']
checks.append('actual original227 image/executor/collector/RustMM module tuple')
facts=checked(st['compiled_collector_facts']);profile=checked(st['compiled_collector_caseprofile']);adopt=checked(st['compiled_collector_adoption']);checked(st['compiled_collector_HOST_acceptance'])
assert facts['actual_test_count']==26 and facts['filtered']==facts['ignored']==0
for a,b in [('payload_argv','argv'),('payload_env','env'),('payload_cwd','cwd')]:assert facts[a]==profile[b]==validated['payload'][b]
assert facts['oracle']==profile['oracle']==validated['payload']['oracle']
assert facts['actual_collector_artifact']['sha256']==adopt['actual_artifact']['sha256']==validated['staging']['collector']['sha256']
assert facts['source_caseprofile']['sha256']==st['compiled_collector_caseprofile']['sha256']
assert len(bytes.fromhex(facts['oracle']['stdout_hex']))==227 and facts['oracle']['stderr_hex']=='' and facts['oracle']['exit_code']==0
checks.append('compiled26-controls producer/profile/oracle227 bytes join unchanged consumer')
contract=json.loads((BASE/'original227-contract-case-correction-source-1/SOURCE-BOUND-NATIVE-CONTRACT.ORIGINAL227-ADDITIVE.json').read_bytes())
assert ref(BASE/'original227-contract-case-correction-source-1/SOURCE-BOUND-NATIVE-CONTRACT.ORIGINAL227-ADDITIVE.json')['sha256']=='7f06ce9bce0d58a6baeb9df1e1c1fd24d26c7b6d825db384dbf12c2693c629a6'
supplement=load(st['executor_supplement']['path'],'actual227_executor_contract_consumer')
supplement.check(validated,json.loads(Path(validated['staging']['overlay_manifest']['path']).read_bytes()),contract)
checks.append('actual unchanged executor supplement and additive7f06 contract')
common=load(R/'observe_current61_original227.py','actual227_configured_common_pure')
l,f,ext,actors=common.validate_current(common.CURRENT)
assert l==ledger and f==free and common.CURRENT['compose_result']==q['compose_result']
checks.append('genuine common typed native lifecycle validates Root61/newfree6c83 data-only')
for p in (R/'cohort').glob('*.py'):ast.parse(p.read_bytes())
load(R/'cohort/runtime_guard.py','unconfigured227_facade_only')
assert "guard.configure" not in (R/'cohort/runtime_guard.py').read_text() # delegated adapter.configure named m.configure
assert "m.configure(config)" in (R/'cohort/runtime_guard.py').read_text()
assert 'operation_guard_binding=guard.binding_reference()' in (R/'cohort/capture_fresh_startup_resource.py').read_text()
assert "age < 120" in (R/'cohort/run_native_startup_capture.py').read_text()
checks.append('all configured consumer sources parse; facade config is external data; resource captures exactbinding;120s unchanged')
result=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_RETAINED227_PRODUCER_TO_CONSUMER_STATIC_DATA_ONLY',checks=checks,count=len(checks),runtime_authority=None,guard_calls=0,observations=0,nonce_calls=0,compiler_calls=0)
with (D/'ACTUAL-ROOT61-227-PIPELINE.json').open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
