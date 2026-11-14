"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused pure reproduction. Real predicate; explicit fake configure effect leaves.
No guard/observe/proc/query/Docker/capture execution or review-authority claim.
"""
from pathlib import Path
import ast,copy,importlib.util,json
D=Path(__file__).resolve().parent;P=D.parent;H=D/'recursive-current62/history'
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def j(p):return json.loads(p.read_bytes())
used=j(P/'recursive-current62/history/ACTUAL-PINS.json');deps=j(P/'recursive-current62/history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json')
old=load(Path(used['common']['path']),'pure_actual_misrouted_root59')
try:old.configured_dependencies(deps)
except ValueError as error:assert str(error)=='Root exact configured runtime dependencies'
else:raise AssertionError('original failing route no longer reproduced')
print('PASS exact actual old common versus new dependency observer failure reproduced before effect leaves')
# Execute unchanged current60.validate_current with only its DATA input substituted.
# This reaches the actual consumed common key and full frozen historical predicates.
p=H/'observe_bfd_current60_history.py';tree=ast.parse(p.read_text());tree.body=[n for n in tree.body if not(isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='PINS'for t in n.targets))]
pins=j(H/'ACTUAL-PINS.TEMPLATE.NOT-AUTHORITY.json');assert 'common_source'not in pins
pins['common_dependencies']=old.ref(P/'recursive-current62/history/ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json')
ns=dict(PINS=pins,__file__=str(p),__name__='pure_corrected_current60')
exec(compile(tree,str(p),'exec'),ns)
rows,common,actors=ns['validate_current']();assert len(actors)==53
assert common.__file__==str(H/'observe_bfd_root59_history.py') and common.ref(common.__file__)==pins['common']
print('PASS unchanged actual current60 consumer selects corrected common BYTE ref and validates original53 history actors')
# The complete configured_dependencies function runs with genuine source/config
# refs and explicit synthetic future-review/configure leaves. This is a predicate
# fixture only; actual new independent review and materialization remain Root's.
future=copy.deepcopy(deps);future['observer']=common.ref(common.__file__)
review=common.checked(deps['independent_dependency_review']);review['reviewed_observer']=future['observer']
configured=[]
class Leaf:
 def __init__(self,row):self.row=row
 def configure(self,row):configured.append((self.row,row))
def checked(row):
 if row==future['independent_dependency_review']:return review
 return common.checked(row)
fn=next(n for n in ast.parse(Path(common.__file__).read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='configured_dependencies')
env=dict(__file__=common.__file__,CURRENT=common.CURRENT,require=common.require,ref=common.ref,checked=checked,auth=common.auth,load=lambda row,name:Leaf(row))
exec(compile(ast.Module(body=[fn],type_ignores=[]),common.__file__,'exec'),env)
env['configured_dependencies'](future)
assert configured==[(future['account_window_guard'],future['account_window_guard_configuration']),(future['physical_history_observer'],future['physical_history_configuration'])]
print('PASS complete unmodified configured_dependencies accepts corrected source/ref with synthetic reviewed-data and configure leaves')
for rel in ['recursive-current62/observe_current62_bfd_postjoin.py','recursive-current62/bind_history.py','recursive-current62/history/observe_bfd_current60_history.py','recursive-current62/history/observe_bfd_root59_history.py']:
 assert (P/rel).read_bytes()==(D/rel).read_bytes(),rel
oldtree=ast.parse((P/'recursive-current62/history/observe_bfd_current61.py').read_text());newtree=ast.parse((H/'observe_bfd_current61.py').read_text())
for a,b in zip(oldtree.body,newtree.body):
 if not(isinstance(a,ast.Assign)and isinstance(a.targets[0],ast.Name)and a.targets[0].id=='PINS'):assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
assert j(D/'INPUTS.json')['runtime_base_source']==common.ref(D/'recursive-current62/observe_current62_bfd_postjoin.py')
assert j(D/'recursive-current62/INPUTS.json')['history_runtime_source']==common.ref(H/'observe_bfd_current61.py')
print('PASS only consumed DATA/source pins changed; all observer/physical/ledger/retirement algorithms byte or AST unchanged')
outer=load(D/'observe_current64_current118_postjoin.py','pure_corrected_outer')
assert len(outer.failed_weekly_capture1_actors())==2
retained=outer.validate_retained();outer.attach_custody(dict(custody_supplement=outer.ref(D.parents[2]/'ROOT-CUSTODY-SUPPLEMENT.ACTUAL.json')),retained)
assert len(retained['actors'])==134
pending=outer.checked(outer.PINS['post_weekly_capture1_pending']);outer.validate_pending_ledger(pending,retained)
note=json.loads(outer.checked(outer.PINS['post_root4_pending'])['note']);_,receipts,retired=outer.validate_retirement(retained,note['closed_current118_root4_retirement']['result'],outer.PINS['root4_parent_normalized'])
assert len(receipts)==14 and len(retired)==15 and len(retained['actors'])+len(retired)==149 and len(pending['consumed_nonces'])==72
assert any(r['role']=='CURRENT118_failed_retirement_readonly_client_UNKNOWN'for r in retained['actors'])
print('PASS actual rawparent/tool/failure refs append exact2 closed actors:134+15=149;72nonces and UNKNOWN retained')
actual_checked=outer.checked;failed=actual_checked(outer.PINS['failed_weekly_capture1'])
def reject(f):
 try:f()
 except(ValueError,AssertionError,KeyError):return
 raise AssertionError('bad custody accepted')
for row,key,value in [(failed['parent_join'],'positive_direct_parent_wait',False),(failed['tool_join'],'joined',False),(failed['tool_join'],'parent_receipt',dict(failed['parent_join'],sha256='0'*64))]:
 def substituted(r,row=row,key=key,value=value):
  v=actual_checked(r)
  if r==row:v[key]=value
  return v
 outer.checked=substituted;reject(outer.failed_weekly_capture1_actors)
outer.checked=actual_checked
before={n.name:n for n in ast.parse((P/'observe_current64_current118_postjoin.py').read_text()).body if isinstance(n,ast.FunctionDef)}
after={n.name:n for n in ast.parse((D/'observe_current64_current118_postjoin.py').read_text()).body if isinstance(n,ast.FunctionDef)}
for name in before:
 if name not in ['attach_custody','source_subjects']:assert ast.dump(before[name],include_attributes=False)==ast.dump(after[name],include_attributes=False),name
print('PASS unjoined/mismatched rawtool refs refused; original physical/ledger/retirement algorithms unchanged')
print(json.dumps(dict(status='PASS_PURE_SINGLE_COMMON_ROUTING_CORRECTION_PLUS_NEW_ACTUAL_CUSTODY',groups=6,actual_guard_calls=0,external_queries=0,proc_reads=0,native_effects=0,actors=149,nonces=72,original_client='UNKNOWN',independent_review_claim=False)))
