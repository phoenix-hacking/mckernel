# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,ast
C=Path(__file__).resolve().parent;P=C.parent

def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
b=json.loads((P/'SOURCE-BINDINGS.json').read_text());old=json.loads((P/'EXACT-ORDINARY-FIXTURE-RECIPE.CORRECTION-1.GRANTED.json').read_text());r=next(iter(old['tools']))
f=C/'fixture/diagnostic.rs';s=f.read_text().replace('origins=11 observer_before_quarantine=1','origins=11 first_pairs=20 observer_before_quarantine=1');f.write_text(s)
fm=dict(scope=scope,status='PREPARED_CORRECTED_11_ORIGIN_AND20_FIRST_BODY_PAIRS_NOT_COMPILED',sources={q.name:pin(q) for q in (C/'fixture').iterdir()},prior_actual_fixture=pin(P/'ACTUAL-FIXTURE-RECEIPT.CORRECTION-1.json'),models='Sameexplicitkernelprimitive models as accepted fixture; new Service.first original/corrected body uses explicit dispatch/fail receiver model, no native/module claim.')
(C/'FIXTURE-SOURCE-BINDINGS.json').write_text(json.dumps(fm,indent=2)+'\n')
O=C/'fixture-output-1';commands=[dict(name='00-finite68-source-fail-caller-check',argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(C/'check_actual_fail_callers.py')]),dict(name='01-pure-actual-body-Rust-compile',argv=[r,'--edition=2021','-C','opt-level=2','-C','panic=abort','-C','codegen-units=1',str(f),'-o',str(O/'diagnostic-fixture')]),dict(name='02-functional-pure-error-context-fixture',argv=[str(O/'diagnostic-fixture')])]
recipe=dict(scope=scope,status='ROOT_GRANTED_ACTUAL_SDK7_OMITTED_CALLER_BOUNDED_CORRECTION_FOCUSED_FIXTURE',authority='Root explicitCPU0onejob AS2GiBCPU60wall90+6 FSIZE32MFD256core0Rust1.92CGU1stack2MiB/h990. No root/container/heavy/module/native/canonical.',profile=old['profile'],tools=old['tools'],source_bindings=pin(C/'SOURCE-BINDINGS.json'),fixture_bindings=pin(C/'FIXTURE-SOURCE-BINDINGS.json'),source_files={str(q):pin(q) for q in [*list((C/'fixture').iterdir()),C/'source/smp_service.rs',C/'check_actual_fail_callers.py',C/'PRIVATE-OMITTED-CALLER-CORRECTION.patch',*[Path(v['private_postimage']['path']) for k,v in b['changes'].items() if k!='smp_service.rs']]},commands=commands,expected_output='PASS memory_pairs=8195 conflict_bucket_masks=256 origins=11 first_pairs=20 observer_before_quarantine=1 errors_claims_callcounts_unchanged=1 budgets=16 metadata_pairs=90 rpc_pairs=12 remote_pairs=24 line_prefix_budget=96; HOST_PRIMITIVES_MODELED_NO_NATIVE',models=fm['models'],failure_history=dict(actual_SDK7_first_compile_failure=json.loads((C/'SOURCE-BINDINGS.json').read_text())['actual_SDK7_failure'],actual_SDK7_bounded_correction=1,prior_pure_fixture_missing_constant_family=old['failure_history'],further_unexpected_failure='STOP_EXPERT_NO_RESET'))
R=C/'EXACT-ORDINARY-FIXTURE-RECIPE.GRANTED.json';R.write_text(json.dumps(recipe,indent=2)+'\n')
d=(P/'run_fixture_owned.py').read_text().replace('fb8fc50b2caf43a68d5fb94a6c7febd36bb420f9cf0b43f9b6008a3b322389e1',pin(R)['sha256'])
d=d.replace("bindings=json.loads((P/'SOURCE-BINDINGS.json').read_text())", "bindings=json.loads((P.parent/'SOURCE-BINDINGS.json').read_text())")
d=d.replace("command['name']=='00-pure-actual-body-Rust-compile'", "command['name']=='01-pure-actual-body-Rust-compile'")
d=d.replace("recipe['commands'][1]['name']", "recipe['commands'][2]['name']")
d=d.replace('typed_origins=10','typed_origins=11,first_original_corrected_pairs=20,finite_actual_source_callers=11,metadata_completion_pairs=90,RPC_pairs=12,remote_reply_pairs=24')
d=d.replace('failures=0,corrections=0','actual_SDK7_failure_count=1,actual_SDK7_correction_count=1')
d=d.replace("SDK7_module_compile_or_native=None", "SDK7_module_compile_or_native=None,failure_history=recipe['failure_history']")
ast.parse(d);D=C/'run_fixture_owned.py';D.write_text(d);print(json.dumps(dict(recipe=pin(R),driver=pin(D),fixture=pin(f))))
