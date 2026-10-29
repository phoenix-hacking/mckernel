"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure in-memory contract regression; fixture values are not actual authority.
"""
import ast, copy
from pathlib import Path
src=Path(__file__).with_name('capture_fresh_startup_resource.py').read_text()
tree=ast.parse(src)
selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('validate_post119_route','validate_post119_physical')]
ns={};exec(compile(ast.Module(body=selected,type_ignores=[]),'<pure-contract>','exec'),ns)
context=dict(current_ledger='actual-ledger-ref',post119_current_free='actual-free-ref',current_boundary='actual-boundary-ref')
st=dict(root_ledger35='actual-ledger-ref',latest_serial_operation_physical_acceptance='actual-free-ref',current_boundary='actual-boundary-ref',current_observer_source='reviewed-fresh-observer-ref')
review=dict(decision='PASS_EXACT_CURRENT119_FRESH_RESOURCE_OBSERVER',independent=True,implementation_ownership=False,observer=st['current_observer_source'],current_ledger=context['current_ledger'],current_free=context['post119_current_free'],current_boundary=context['current_boundary'],complete_actual_actor_frontier=True,original_resource_lock_holder_cgroup_checks_preserved=True,runtime_authority=None)
physical=dict(current_ledger=context['current_ledger'],current_boundary=context['current_boundary'],actual_latest_operation_postjoin_acceptance=context['post119_current_free'],complete_actual_actor_frontier=True,native_acceptance=False,runtime_authority=None)
route=ns['validate_post119_route'];verify=ns['validate_post119_physical']
route(st,context,review);verify(context,physical)
checks=[('st','root_ledger35','historical-Root54'),('st','latest_serial_operation_physical_acceptance','pending-Root67'),('st','current_boundary','old-boundary'),('review','decision','PENDING'),('review','independent',False),('review','implementation_ownership',True),('review','observer','unreviewed-source'),('review','current_ledger','old-ledger'),('review','current_free','pending-free'),('review','current_boundary','old-boundary'),('review','complete_actual_actor_frontier',False),('review','original_resource_lock_holder_cgroup_checks_preserved',False),('review','runtime_authority','claimed'),('physical','current_ledger','old-ledger'),('physical','current_boundary','old-boundary'),('physical','actual_latest_operation_postjoin_acceptance','pending-free'),('physical','complete_actual_actor_frontier',False),('physical','native_acceptance',True),('physical','runtime_authority','claimed')]
for target,key,value in checks:
 a,b,c,d=map(copy.deepcopy,(st,context,review,physical));{'st':a,'review':c,'physical':d}[target][key]=value
 try:route(a,b,c);verify(b,d)
 except AssertionError:continue
 raise SystemExit('failed to refuse '+target+'.'+key)
# Route validation runs before loading/invoking any physical observer.
main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
code=ast.unparse(main)
assert code.index('validate_post119_route') < code.index("load(OBSERVER_REF") < code.index('observer.observe()') < code.index('validate_post119_physical')
assert 'validate_candidate' not in src
for invariant in ("memory['MemAvailable'] >= 24 * 2 ** 30",'pids == 0',"physical['no_existing_heavy'] is True", "len(physical['closed_exclusive_probes']) == 2"):
 assert invariant in code,invariant
print('PASS: matching in-memory route, 19 negative bindings, observer ordering and original resource floor checks; no physical observation')
