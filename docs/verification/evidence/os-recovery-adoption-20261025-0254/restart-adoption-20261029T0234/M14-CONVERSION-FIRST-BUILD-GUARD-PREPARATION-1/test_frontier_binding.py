"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic fixtures only. No actual guard, process, capture, or build invocation.
"""
import copy,importlib.util,json,tempfile
from pathlib import Path
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('conversion_pure_guard',D/'runtime_guard.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
f=g.read(g.FIXED);historic=g.read(f['root68_ledger']);subjects=g.fixed_subjects()
for v in subjects.values():g.auth(v)
with tempfile.TemporaryDirectory(prefix='synthetic-fixtures-',dir=D) as tmp:
 p=Path(tmp)
 def put(name,value):
  path=p/(name+'.json');path.write_text(json.dumps(value,sort_keys=True)+'\n');return g.ref(path)
 def build(mutation=None):
  fresh_nonce='d'*32
  free=dict(independent=True,implementation_ownership=False,current_free=True,runtime_authority=None)
  if mutation=='unknown-free':free['current_free']=None
  free_ref=put('synthetic-free',free)
  if mutation=='stale-free':free_ref=f['root68_free']
  ledger=copy.deepcopy(historic);ledger.update(author='/root',complete_within_declared_current_boundary=True,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=True,current_physical_clearance_pending=False,latest_accepted_free_boundary=free_ref)
  if mutation=='pending':ledger['current_physical_clearance_pending']=True
  if mutation=='nonce-consumed':fresh_nonce=ledger['consumed_nonces'][0]
  if mutation=='nonce-abandoned':fresh_nonce=ledger['reserved_abandoned_unconsumed_nonces'][0]
  if mutation=='nonce-reserved':ledger['reserved_unused_nonces'].append(fresh_nonce)
  ledger_ref=put('synthetic-ledger',ledger);observe=put('synthetic-observation',{'fixture':True});caller=put('synthetic-caller-closure',{'fixture':True})
  boundary=dict(schema='mckernel.root-current-frontier-boundary.v1',author='/root',decision='ADOPT_EXACT_CURRENT_FRONTIER',nonce_ledger=ledger_ref,native_custody_clearance=free_ref,predecessor_boundary=f['root68_boundary'],actual_frontier_observation=observe,actual_caller_closure=caller,retained_actor_rows=207,distinct_actor_identities=202,root_attests_exact_current_boundary=True,root_attests_no_unlisted_post_boundary_execution_or_custody_operation=True,runtime_authority=None)
  br=put('synthetic-boundary',boundary)
  check_names=('full_73_nonce_history_preserved','all_unknown_outcomes_preserved','all_later_custody_accounted','current_frontier_and_caller_closure_exact','independent_free_and_no_pending_custody','root_boundary_current_and_acyclic');checks={k:True for k in check_names}
  if mutation=='unknown-custody':checks['all_unknown_outcomes_preserved']=False
  rv=dict(schema='mckernel.independent-current-frontier-review.v1',decision='PASS_EXACT_CURRENT_FRONTIER_ADOPTION',independent=True,implementation_ownership=False,reviewer='/root/synthetic-reviewer',runtime_authority=None,nonce_ledger=ledger_ref,current_boundary=br,independent_current_free=free_ref,predecessor_boundary=f['root68_boundary'],actual_frontier_observation=observe,actual_caller_closure=caller,checks=checks)
  if mutation=='owner-reviewer':rv['reviewer']='/root/m14_integration_terra'
  rr=put('synthetic-review',rv);bundle=dict(schema='mckernel.root-current-frontier-bundle.v1',author='/root',decision='BIND_REVIEWED_CURRENT_FRONTIER',ledger=ledger_ref,boundary=br,independent_adoption_review=rr,runtime_authority=None);bundle_ref=put('synthetic-bundle',bundle)
  boot=f['bootstrap_caps']
  context=dict(request=f['request'],nonce=fresh_nonce,current_free=free_ref,current_ledger=ledger_ref,current_bindings=bundle_ref,armed_controls=g.ARM,bootstrap_caps=boot,candidate_snapshot_manifest=f['snapshot_manifest'],reuse_descriptor=f['reuse_descriptor'])
  actual_subjects=dict(subjects);actual_subjects.update({'root:'+k:context[k] for k in ('request','current_free','current_ledger','current_bindings','armed_controls','bootstrap_caps','candidate_snapshot_manifest','reuse_descriptor')})
  op=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',operation='conversion-first-three-command-build',window_sha256=g.WINDOW_SHA,first_prepared_window_sha256=g.WINDOW_SHA,weekly_limit_identity=g.WEEKLY,billing_mode='included_only',allow_prepaid_fallback=False,predecessor_cutoffs=None,operation_cutoffs=list(g.MAXIMUM),subjects=actual_subjects,context=context,guardian=dict(source=subjects['guardian'],entrypoint='guard'),source_owners=['/root','/root/m14_integration_terra'])
  review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,implementation_ownership=False,reviewer='/root/synthetic-reviewer',operation=op['operation'],successor=op)
  binding=dict(author='/root',decision='BIND_REVIEWED_CONVERSION_FIRST_PRODUCER_GUARD',runtime_authority=None,source=g.ref(D/'runtime_guard.py'),successor=put('synthetic-operation',op),independent_review=put('synthetic-operation-review',review))
  return binding,op,review,actual_subjects,context
 binding,op,review,sub,ctx=build();a,b,c,d=g.binding_metadata(binding);assert (a,b,c,d)==(op,review,ctx,sub)
 clocks=[x-5 for x in g.MAXIMUM];ceil=[x-3 for x in g.MAXIMUM];assert g.validate_operation(a,b,d,c,clocks,ceil)==g.MAXIMUM
 for axis in range(3):
  test=clocks[:];test[axis]=ceil[axis]
  try:g.validate_operation(a,b,d,c,test,ceil)
  except ValueError:pass
  else:raise AssertionError('clock equality accepted')
 for case in ('stale-free','unknown-free','pending','nonce-consumed','nonce-abandoned','nonce-reserved','unknown-custody','owner-reviewer'):
  binding,*_=build(case)
  try:g.binding_metadata(binding)
  except (AssertionError,ValueError,KeyError,TypeError):pass
  else:raise AssertionError('accepted '+case)
print('PASS synthetic complete byte-bound binding -> frontier -> operation; 8 negative frontier/nonce/reviewer cases and 3 effective-clock equality refusals; no actual guard/runtime')
