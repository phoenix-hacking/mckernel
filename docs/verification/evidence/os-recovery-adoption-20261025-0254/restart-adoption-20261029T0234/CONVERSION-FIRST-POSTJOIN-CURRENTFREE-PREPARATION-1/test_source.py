"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual retained receipt validation plus explicitly synthetic Root context in RAM.
No guard, proc, Docker, capture, retirement or compiler call.
"""
from pathlib import Path
import importlib.util,json,hashlib,ast,copy
D=Path(__file__).resolve().parent;OLD=D.parent/'M14-CONVERSION-FIRST-CURRENT-FRONTIER-PREPARATION-1/parent-ownership-correction-1'
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
h=load(D/'postjoin_history.py','pure_postjoinhistory');pins=json.loads((D/'HISTORY-INPUTS.json').read_bytes());c=json.loads((D/'ROOT-CUSTODY.TEMPLATE.NOT-AUTHORITY.json').read_bytes());c.update(author='/root',decision='BIND_EXACT_CONVERSION_POSTRETIREMENT_READONLY_CUSTODY',no_unlisted_physical_or_custody_operations_since_retirement=True)
a,receipts,p=h.validate(c);assert len(a)==230 and len({(x['pid'],x['start'])for x in a})==225 and len(receipts)==14
assert len(a[:212])==212 and a[:212]==h.read(pins['previous_free'])['next_full_postjoin_actor_frontier'];assert a[-15]['pid']==2647013 and a[-16]['pid']==2624123
assert len(a[:-1])==229 # countonly; the acceptedretirementfrontier excludes collector specifically.
without_collector=[x for x in a if x['role']!='conversion_build_resource_collector'];assert len(without_collector)==229 and len({(x['pid'],x['start'])for x in without_collector})==224
fail=[]
for key,value in [('current_free',True),('old_readonly_client_status','REAPED'),('uninstrumented_source_tool_identities','KNOWN'),('no_unlisted_physical_or_custody_operations_since_retirement',False),('independent_retirement_acceptance',pins['previous_free'])]:
 bad=copy.deepcopy(c);bad[key]=value
 try:h.validate(bad)
 except (ValueError,KeyError,AssertionError):fail.append(key)
 else:raise AssertionError('accepted bad custody '+key)
assert len(fail)==5
# Existing Q/effective minima algorithm functions remain exact AST; never invoke.
def funcs(path):return {n.name:n for n in ast.parse(path.read_bytes()).body if isinstance(n,ast.FunctionDef)}
x=funcs(OLD/'readonly_operation_guard.py');y=funcs(D/'readonly_operation_guard.py')
for name in ['validate_operation','confirmed_weekly_ceiling','_evaluate','guard','current_cutoffs']:assert ast.dump(x[name],include_attributes=False)==ast.dump(y[name],include_attributes=False),name
# Parent correction is exact predecessor except new observer basename.
assert (D/'root_capture_parent.py').read_text()==(OLD/'root_capture_parent.py').read_text().replace('observe_conversion_frontier.py','observe_conversion_postjoin.py')
obs=(D/'observe_conversion_postjoin.py').read_text();assert 'executor=history.load' in obs and 'checker.validate_metadata()'not in obs[obs.index('def observe():'):];assert "b['cid']"in obs and 'history.validate' in obs
# Source/template closure coherency; no real Root intent is generated.
g=load(D/'readonly_operation_guard.py','pure_new_guard');intent=json.loads((D/'ROOT-OPERATION-INTENT.TEMPLATE.NOT-AUTHORITY.json').read_bytes());assert set(intent)=={'author','decision','runtime_authority','context','cutoffs'}and intent['author']is None
closure=intent['context']['readonly_source_closure'];assert closure==dict(observer=h.ref(D/'observe_conversion_postjoin.py'),physical_adapter=h.ref(D/'readonly_history_guard.py'),capture_parent=h.ref(D/'root_capture_parent.py'),history=h.ref(D/'postjoin_history.py'))
context=copy.deepcopy(intent['context']);context['armed_controls']=g.ARM;context['bootstrap_caps']=h.ref(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1/EARLIEST-CONTROL-CAPS.json'));context['nonce']='ab'*16;fake={'path':'/SYNTHETIC_ROOT_CUSTODY_NO_AUTHORITY','bytes':1,'sha256':'a'*64};context['source_authority']=fake;oldread,oldauth=g.read,g.auth
g.read=lambda r:c if r==fake else oldread(r);g.auth=lambda r:Path(r['path'])if r==fake else oldauth(r);subjects=g.context_subjects(context);assert subjects['root:current_ledger']==pins['root70_pending_ledger']and subjects['history_inputs']==h.ref(D/'HISTORY-INPUTS.json')
for name in ['root_capture_parent.py','readonly_operation_guard.py','readonly_history_guard.py','observe_conversion_postjoin.py','prepare_readonly_operation.py','postjoin_history.py']:ast.parse((D/name).read_bytes())
r=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_SOURCE_AND_ACTUAL_RETAINED_POSTRETIREMENT_DATA_WITH_SYNTHETIC_CONTEXT_ONLY',retirement_accepted_frontier_rows=229,retirement_accepted_distinct=224,extra_resource_collector=dict(pid=2624123,birth=111570045,group=2624123),pre_capture_rows=230,pre_capture_distinct=225,duplicates_preserved=5,retirement_clients=14,actual_retirement_acceptance=pins['independent_retirement_acceptance'],negative_custody_cases=fail,unchanged_Q_AST=True,unchanged_parent_except_observer_basename=True,template_closure=True,real_Root_context=False,guard=0,proc=0,Docker=0,capture=0,retirement=0,compiler=0,native=0)
(D/'PURE-CHECKS.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
