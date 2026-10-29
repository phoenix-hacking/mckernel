"""Functional OS SOURCE/pure metadata checks only; no security testing/effects."""
from pathlib import Path
import ast,json,copy
D=Path(__file__).resolve().parent
ns={'__file__':str(D/'observe_current67_current119_postjoin.py'),'__name__':'pure119source'};exec(compile((D/'observe_current67_current119_postjoin.py').read_text(),'pure119source','exec'),ns)
e,b,actors,receipts=ns['validate_metadata']();assert len(actors)==186 and len(receipts)==14;assert actors[-1]['pid']==2562993 and actors[-1]['start']==110549500 and actors[-1]['group']is None;assert actors[:168]==b['prior_actors']and actors[168:170]==b['new_known_actors'];assert any('UNKNOWN'in r['role']for r in actors)
BASE=ns['BASE'];oldbind=ns['checked'](ns['PINS']['base_bindings']);g=BASE.runtime_dependencies(oldbind);assert list(g.current_cutoffs())==ns['PINS']['limits']
runtime=BASE.load(BASE.PINS['runtime_base_source'],'pure_actual_final_recursive_metadata');rb=BASE.checked(oldbind['recursive_current63_bindings']);rg=runtime.runtime_dependencies(rb);assert list(rg.current_cutoffs())==ns['PINS']['limits']
# Follow actual consumed final Root61→Root60→common configurations, not templates.
common=runtime.checked(runtime.ref(runtime.HERE/'history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json'));root61=runtime.checked(runtime.ref(runtime.HERE/'history/ROOT61-RUNTIME-DEPENDENCIES.json'));assert common['account_window_guard_configuration']==root61['guard_configuration']==rb['guard_configuration']
for configref in [oldbind['guard_configuration'],rb['guard_configuration'],common['account_window_guard_configuration'],root61['guard_configuration']]:
 cfg=BASE.checked(configref);op=BASE.checked(cfg['successor']);assert op['operation_cutoffs']==ns['PINS']['limits'];assert op['guardian']['source']==ns['PINS']['guardian'];assert cfg['shared_guard']==BASE.PINS['shared_guard']
shared={};shared['__file__']=str(D/'operation_window_guard.py');shared['__name__']='pure_new_readonly_shared';exec(compile((D/'operation_window_guard.py').read_text(),'pure_new_readonly_shared','exec'),shared)
subjects={'TEST_ONLY_SOURCE':dict(path='/TEST_ONLY_SOURCE',bytes=1,sha256='0'*64)};binding=shared['bound']();maximum=binding['operation_cutoffs'];op=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',operation='current119-postjoin-current67',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',window_sha256=shared['WINDOW_SHA256'],first_prepared_window_sha256=shared['WINDOW_SHA256'],predecessor_cutoffs=None,weekly_limit_identity=shared['WEEKLY_IDENTITY'],billing_mode='included_only',allow_prepaid_fallback=False,operation_cutoffs=list(maximum),subjects=subjects,source_owners=['/root','/root/cleanup_bindings'],guardian=dict(source=binding['guardian'],entrypoint='guard'))
def review(o):return dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,implementation_ownership=False,reviewer='/root/TEST_ONLY',operation=o['operation'],successor=o)
clocks=[x-1 for x in maximum];assert list(shared['validate_operation'](op,review(op),op['operation'],subjects,clocks))==maximum
for key,value in [('operation_cutoffs',[maximum[0],maximum[1]+1,maximum[2]]),('billing_mode','prepaid'),('weekly_limit_identity',dict(limit_id='codex',window_duration_mins=10080,resets_at=1793774134))]:
 bad=copy.deepcopy(op);bad[key]=value
 try:shared['validate_operation'](bad,review(bad),bad['operation'],subjects,clocks)
 except ValueError:pass
 else:raise AssertionError(key)
try:shared['validate_operation'](op,review(op),op['operation'],subjects,[1793253601,1035704,1051042])
except ValueError:raise AssertionError('old timestamp itself is not authority; should remain before real caps')
# A stale operation cap06UTC cannot grant now: direct clocks exceed it.
bad=copy.deepcopy(op);bad['operation_cutoffs']=[1793253600,1035703.5689321246,1051041.695980609]
try:shared['validate_operation'](bad,review(bad),bad['operation'],subjects,clocks)
except ValueError:pass
else:raise AssertionError('expired06 operation accepted')
oldsource=Path(BASE.PINS['shared_guard']['path']).read_text();newsource=(D/'operation_window_guard.py').read_text();assert newsource.replace("'bfd-postjoin-current62','current119-postjoin-current67'","'bfd-postjoin-current62'")==oldsource
oldadapter=Path(BASE.PINS['guard']['path']).read_text();newadapter=(D/'current119_guard_adapter.py').read_text();assert newadapter.replace("OPERATION = 'current119-postjoin-current67'","OPERATION = 'current118-postjoin-current64'")==oldadapter
result=ns['checked'](ns['PINS']['retirement_result']);stale=ns['checked'](result['proofs'][-1])['process']
try:BASE.validate_absence_reports([stale],actors)
except ValueError:pass
else:raise AssertionError('retirement-owner-present old proof cannot be current-free')
checks=['retirement postproof with still-livecleanupowner refused as fresh current-free','actual independent119retirement/artifact/73ledger pure metadata contracts and186known actors, parent groupNone','prebuild Root65 metadata retained as historical, not own post119free','actual final inherited64/62 guard configure/caps APIs pure-pass; Root61→Root60→common live refs exact same final62config','only new shared operation tuple literal and adapter OPERATION literal, other source bytes exact','newreadonly operation pure cap/weekly/no-paid regression; increased/expired06 caps/reset identity rejected','no guard(), proc, process, Docker, native, cleanup or live quota query invoked']
(D/'PURE-SOURCE-CHECKS.json').write_text(json.dumps(dict(status='PASS_SOURCE_ONLY_CURRENT119_POSTJOIN_PREPARATION',checks=checks,known_actor_count=186,retirement_clients=14,actual_capture=False),indent=2)+'\n');print('PASS',len(checks),'focused source/metadata groups')
