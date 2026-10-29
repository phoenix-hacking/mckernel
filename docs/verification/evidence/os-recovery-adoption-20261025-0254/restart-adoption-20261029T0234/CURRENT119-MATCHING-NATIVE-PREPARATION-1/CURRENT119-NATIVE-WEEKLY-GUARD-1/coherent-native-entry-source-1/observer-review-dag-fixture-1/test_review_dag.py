"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure metadata fixture: synthetic reviews are in-memory test values, never authority.
Executes the frozen Resource2 and observer predicates and the formatter predicate.
"""
from pathlib import Path
from graphlib import TopologicalSorter,CycleError
import ast,copy,json
D=Path(__file__).resolve().parent
P=D.parent.parent
consumer=P/'post119-resource-successor-source-1/capture_fresh_startup_resource.py'
observer=P/'post119-resource-successor-source-1/accepted-current-physical-source-1/observe_current119_native_resources.py'
formatter=D.parent/'materialize_entries.py'
review_path=P/'post119-resource-successor-source-1/accepted-current-physical-source-1/independent-source-review-1/SOURCE-REVIEW.ACTUAL.json'
actual=json.loads(review_path.read_bytes());assert actual['decision']=='PASS_SOURCE' and actual['independent'] is True and actual['implementation_ownership'] is False
# Use authentic reviewed subjects; the proposed typed records below are merely test data.
obs=actual['observer'];ledger=actual['Root68_ledger'];free=actual['independent_current_free'];boundary=actual['Root68_boundary']
context=dict(current_ledger=ledger,post119_current_free=free,current_boundary=boundary)
st=dict(root_ledger35=ledger,latest_serial_operation_physical_acceptance=free,current_boundary=boundary,current_observer_source=obs)
sourcereview=dict(decision='PASS_EXACT_CURRENT119_FRESH_RESOURCE_OBSERVER',independent=True,implementation_ownership=False,observer=obs,current_ledger=ledger,current_free=free,current_boundary=boundary,complete_actual_actor_frontier=True,original_resource_lock_holder_cgroup_checks_preserved=True,runtime_authority=None,reviewer='/root/recovery_review',source_review='actual-2ea67-byte-ref')
def functions(path,names,namespace):
 tree=ast.parse(path.read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names];exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),namespace);return namespace
ns=functions(consumer,{'validate_post119_route'},{});ns['validate_post119_route'](st,context,sourcereview)
# Run the formatter's actual typed review check, not a reconstructed approximation.
tree=ast.parse(formatter.read_bytes());main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
found=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='need' and n.args and 'PASS_EXACT_CURRENT119_FRESH_RESOURCE_OBSERVER' in ast.unparse(n.args[0])]
assert len(found)==1
node=ast.Expression(body=found[0].args[0]);fn={'review':sourcereview,'template':dict(current_observer_source=obs,root_ledger35=ledger,latest_serial_operation_physical_acceptance=free,current_boundary=boundary)}
assert eval(compile(node,str(formatter),'eval'),fn)
def need(ok,msg):
 if not ok:raise ValueError(msg)
def fake_ref(path):
 assert path==str(observer);return obs
ons=functions(observer,{'validate_route'},{'need':need,'ref':fake_ref,'__file__':str(observer)})
binding=dict(author='/root',decision='BIND_CURRENT119_NATIVE_RESOURCE_OBSERVER',runtime_authority=None,source=obs,current_ledger=ledger,current_free=free,current_boundary=boundary,physical_history_binding='LATER_ACTUAL_PHYSICAL_BINDING',query_output_directory='/actual/fresh/root-owned-output',independent_review='LATER_ACTUAL_RUNTIME_REVIEW')
runreview=dict(sourcereview,binding_payload={k:v for k,v in binding.items() if k!='independent_review'})
ons['validate_route'](binding,context,runreview)
try:ons['validate_route'](binding,context,sourcereview)
except (KeyError,ValueError,AssertionError):pass
else:raise AssertionError('source review improperly substituted for runtime binding review')
bad=copy.deepcopy(runreview);bad['binding_payload']['physical_history_binding']='DIFFERENT_BINDING'
try:ons['validate_route'](binding,context,bad)
except (KeyError,ValueError,AssertionError):pass
else:raise AssertionError('changed runtime physical binding accepted')
bad=copy.deepcopy(sourcereview);bad['current_free']={}
try:ns['validate_post119_route'](st,context,bad)
except AssertionError:pass
else:raise AssertionError('wrong static current-free accepted')
# Values list prerequisite nodes. The later physical source review is independent
# from the current observer review; actual receipts must be authored independently.
graph={'reviewed_observer_sources':set(),'accepted_root68':set(),'typed_source_review':{'reviewed_observer_sources','accepted_root68'},'five_wrapper_sources':set(),'actual_source_capability_and_stage':{'five_wrapper_sources','typed_source_review','accepted_root68'},'static_bindings':{'five_wrapper_sources','typed_source_review','actual_source_capability_and_stage'},'sixth_bridge':{'static_bindings'},'native_guard_operation_binding':{'sixth_bridge','five_wrapper_sources','static_bindings'},'physical_history_review':{'native_guard_operation_binding','reviewed_observer_sources'},'physical_history_binding':{'physical_history_review','native_guard_operation_binding'},'runtime_observer_payload':{'physical_history_binding','native_guard_operation_binding','accepted_root68'},'typed_runtime_review':{'runtime_observer_payload'},'runtime_observer_binding':{'runtime_observer_payload','typed_runtime_review'},'separately_reviewed_resource_observation':{'runtime_observer_binding','static_bindings','native_guard_operation_binding'}}
order=list(TopologicalSorter(graph).static_order());assert order.index('typed_source_review')<order.index('static_bindings')<order.index('sixth_bridge')<order.index('native_guard_operation_binding')<order.index('physical_history_binding')<order.index('typed_runtime_review')<order.index('runtime_observer_binding')
cycle=copy.deepcopy(graph);cycle['typed_source_review'].add('runtime_observer_payload')
try:list(TopologicalSorter(cycle).static_order())
except CycleError:pass
else:raise AssertionError('single full-payload review should create cycle')
print('PASS actual frozen Resource2/formatter/runtime predicates: split synthetic typed reviews; wrong free and modified runtime payload refused; source receipt alone cannot satisfy runtime. DAG valid; shared full-payload review cyclic. No physical validation, guard or generated authority.')
print('DAG:', ' -> '.join(order))
