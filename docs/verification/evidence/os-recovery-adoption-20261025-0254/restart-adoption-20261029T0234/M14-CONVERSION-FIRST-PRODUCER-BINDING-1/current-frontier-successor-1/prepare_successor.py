#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only current frontier predicate successor; no guard or operation calls.
"""
import ast,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent
old=(P/'seal_root_conversion_inputs.py').read_text()
assert hashlib.sha256(old.encode()).hexdigest()=='6fc9eabc35364dee8d49e0985df96ac2feef1a308909b66462818a497ce2644b'
predicate='''def validate_latest_frontier(q, historical_ledger):
    """Authenticate a Root-owned acyclic latest frontier and independent review.

    Actual chronology, full unknown outcomes, caller closure and free custody are
    independently reviewed; this data predicate is not a live operation guard.
    """
    bundle=read(auth(q['current_bindings']))
    assert bundle['schema']=='mckernel.root-current-frontier-bundle.v1' and bundle['author']=='/root' and bundle['decision']=='BIND_REVIEWED_CURRENT_FRONTIER' and bundle['runtime_authority'] is None
    assert set(bundle)=={'schema','author','decision','ledger','boundary','independent_adoption_review','runtime_authority'}
    assert bundle['ledger']==q['current_ledger']
    current_ledger=read(auth(bundle['ledger']));boundary=read(auth(bundle['boundary']));review=read(auth(bundle['independent_adoption_review']));free=read(auth(q['current_free']))
    assert bundle['ledger']!=ROOT68_LEDGER and bundle['boundary']!=ROOT68_BOUNDARY and q['current_free']!=ROOT68_FREE, 'old Root68 is history, not current'
    assert boundary['schema']=='mckernel.root-current-frontier-boundary.v1' and boundary['author']=='/root' and boundary['decision']=='ADOPT_EXACT_CURRENT_FRONTIER' and boundary['runtime_authority'] is None
    assert set(boundary)=={'schema','author','decision','nonce_ledger','native_custody_clearance','predecessor_boundary','actual_frontier_observation','actual_caller_closure','retained_actor_rows','distinct_actor_identities','root_attests_exact_current_boundary','root_attests_no_unlisted_post_boundary_execution_or_custody_operation','runtime_authority'}
    assert boundary['nonce_ledger']==bundle['ledger'] and boundary['native_custody_clearance']==q['current_free'] and boundary['predecessor_boundary']==ROOT68_BOUNDARY
    assert boundary['root_attests_exact_current_boundary'] is True and boundary['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
    assert type(boundary['retained_actor_rows']) is int and boundary['retained_actor_rows']>=199 and type(boundary['distinct_actor_identities']) is int and 194<=boundary['distinct_actor_identities']<=boundary['retained_actor_rows']
    assert boundary['actual_frontier_observation'] not in (q['current_bindings'],bundle['boundary'],bundle['independent_adoption_review']) and boundary['actual_caller_closure'] not in (q['current_bindings'],bundle['boundary'],bundle['independent_adoption_review'])
    auth(boundary['actual_frontier_observation']);auth(boundary['actual_caller_closure'])
    assert free['independent'] is True and free['implementation_ownership'] is False and free['current_free'] is True and free['runtime_authority'] is None
    assert current_ledger['author']=='/root' and current_ledger['complete_within_declared_current_boundary'] is True and current_ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
    assert current_ledger['current_physical_clearance_pending'] is False and current_ledger['latest_accepted_free_boundary']==q['current_free']
    assert type(current_ledger['consumed_nonces']) is list and len(current_ledger['consumed_nonces'])>=73
    assert current_ledger['consumed_nonces'][:73]==historical_ledger['consumed_nonces'] and len(set(current_ledger['consumed_nonces']))==len(current_ledger['consumed_nonces'])
    assert all(isinstance(n,str) and re.fullmatch('[0-9a-f]{32}',n) for n in current_ledger['consumed_nonces'])
    assert set(historical_ledger['reserved_abandoned_unconsumed_nonces'])<=set(current_ledger['reserved_abandoned_unconsumed_nonces'])
    assert not set(current_ledger['consumed_nonces']) & set(current_ledger['reserved_abandoned_unconsumed_nonces'])
    assert re.fullmatch('[0-9a-f]{32}',q['nonce']) and q['nonce'] not in current_ledger['consumed_nonces']+current_ledger['reserved_abandoned_unconsumed_nonces']+current_ledger['reserved_unused_nonces']
    assert review['schema']=='mckernel.independent-current-frontier-review.v1' and review['decision']=='PASS_EXACT_CURRENT_FRONTIER_ADOPTION' and review['independent'] is True and review['implementation_ownership'] is False and review['runtime_authority'] is None
    assert isinstance(review['reviewer'],str) and review['reviewer'].startswith('/root/') and review['reviewer'] not in ('/root','/root/f03_munmap_terra')
    assert review['nonce_ledger']==bundle['ledger'] and review['current_boundary']==bundle['boundary'] and review['independent_current_free']==q['current_free'] and review['predecessor_boundary']==ROOT68_BOUNDARY
    assert review['actual_frontier_observation']==boundary['actual_frontier_observation'] and review['actual_caller_closure']==boundary['actual_caller_closure']
    checks=review['checks'];required={'full_73_nonce_history_preserved','all_unknown_outcomes_preserved','all_later_custody_accounted','current_frontier_and_caller_closure_exact','independent_free_and_no_pending_custody','root_boundary_current_and_acyclic'}
    assert isinstance(checks,dict) and required<=set(checks) and all(checks[k] is True for k in required) and all(value is True for value in checks.values())
    return current_ledger

'''
start=old.index('def validate_root(q):');new=old[:start]+predicate+old[start:]
start=new.index(' # Preserve the previously accepted full Root65 chain');end=new.index(" assert re.fullmatch('[0-9a-f]{32}'",start)
replacement=''' # Root65 and Root68 remain authenticated historical proofs, not current.
 oldq=read(auth(OLD_ROOT_INPUT)); oldfree=read(auth(oldq['current_free'])); oldledger=read(auth(oldq['current_ledger']))
 accepted.accepted_metadata(oldq,oldfree,oldledger); accepted.accepted_chain(oldq)
 historical=read(auth(ROOT68_LEDGER));oldboundary=read(auth(ROOT68_BOUNDARY));oldreview=read(auth(ROOT68_REVIEW));auth(ROOT68_FREE)
 assert oldboundary['nonce_ledger']==ROOT68_LEDGER and oldboundary['native_custody_clearance']==ROOT68_FREE and oldboundary['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert oldreview['decision']=='PASS_EXACT_ROOT68_CURRENT119_CURRENT_BOUNDARY_ADOPTION' and oldreview['independent'] is True and oldreview['implementation_ownership'] is False
 assert oldreview['nonce_ledger']==ROOT68_LEDGER and oldreview['current_boundary']==ROOT68_BOUNDARY and oldreview['independent_current_free']==ROOT68_FREE
 assert all(oldreview['checks'].values()) and len(historical['consumed_nonces'])==73 and historical['latest_accepted_free_boundary']==ROOT68_FREE and historical['current_physical_clearance_pending'] is False
 ledger=validate_latest_frontier(q,historical)
'''
new=new[:start]+replacement+new[end:]
new=new.replace("q['nonce']not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']", "q['nonce']not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']+ledger['reserved_unused_nonces']")
ast.parse(new)
(D/'seal_root_conversion_inputs.py').write_text(new)
(D/'CURRENT-FRONTIER-SUCCESSOR.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/seal_root_conversion_inputs.py',tofile='b/seal_root_conversion_inputs.py')))
for f in ['accepted_bindings.py','run_build_only.template.py','build_only_worker.template.py','hold_and_run_build_only.py','ROOT-INPUT.TEMPLATE.NOT-AUTHORITY.json']:
 (D/f).write_bytes((P/f).read_bytes())
print('PASS_PRIVATE_CURRENT_FRONTIER_SUCCESSOR_SOURCE')
