"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure authenticated metadata and generated-callsite checks. No observer or capture.
"""
import ast, copy, importlib.util, json
from pathlib import Path
D=Path(__file__).resolve().parent
P=D.parent
E=P.parent.parent
S=E/'CURRENT118-postbuild-current-successor-preparation-1/source-2'
spec=importlib.util.spec_from_file_location('constructor_pure',D/'prepare_observer_current_controls.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
pins=json.loads((S/'INPUTS.json').read_bytes())
manifest=dict(schema='mckernel.current118.postjoin-control-source-inputs.v1',scope=c.SCOPE,thread_id='01a18582-1fc6-77b1-bfb6-15c86483f579',guardian=c.EXACT_CLEANUP and json.loads(Path(c.EXACT_CLEANUP['cleanup_bindings']['path']).read_bytes())['guardian'])
manifest.update({k:v for k,v in c.EXACT_CLEANUP.items() if k!='expert_design'})
c.validate_cleanup(pins,manifest)
newpins=copy.deepcopy(pins)
newpins.update(retirement_source=manifest['cleanup_executor'],retirement_bindings=manifest['cleanup_bindings'],compatibility_runtime_files=manifest['cleanup_runtime_files'],compatibility_source_ready=manifest['cleanup_source_ready'])
newpins.update(c.EXTRA_CUSTODY)
tree=ast.parse((D/'observe_current64_current118_postjoin.template.py').read_text())
tree.body=[n for n in tree.body if not(isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='PINS'for t in n.targets))]
ns=dict(__file__=str(S/'observe_current64_current118_postjoin.py'),__name__='pure_observer_only',PINS=newpins)
exec(compile(tree,str(D/'observe_current64_current118_postjoin.template.py'),'exec'),ns)
checks=[]
def passed(s):checks.append(s);print('PASS',s)
def reject(call):
 try:call()
 except (ValueError,KeyError,AssertionError):return
 raise AssertionError('invalid metadata accepted')
root3=ns['checked'](newpins['post_root3_pending'])
assert len(ns['root3_failed_actors'](root3))==3
assert ns['root4_outer_parent_actors']()==[dict(pid=2311392,start=104859779,role='CURRENT118_Root4_closed_cleanup_outer_parent',group=None,fd=None)]
passed('actual Root3 three plus Root4 outer parent, no inherited group')
# Mutate leaf data only in the pure reader; original evidence remains immutable.
actual_checked=ns['checked']
for key,field,value in [('parent_join','positive_direct_parent_wait',False),('client_join','group_absent',False),('client_join','positive_wait4',False)]:
 row=json.loads(root3['note'])['closed_failed_current118_cleanup'][key]
 def replaced(r,row=row,field=field,value=value):
  v=actual_checked(r)
  if r==row:v[field]=value
  return v
 ns['checked']=replaced
 reject(lambda:ns['root3_failed_actors'](root3))
ns['checked']=actual_checked
bad=copy.deepcopy(root3);note=json.loads(bad['note']);note['closed_failed_current118_cleanup']['parent_join']['sha256']='0'*64;bad['note']=json.dumps(note)
reject(lambda:ns['root3_failed_actors'](bad))
rawref=newpins['root4_parent_raw']
def wrongraw(r):
 v=actual_checked(r)
 if r==rawref:v['positive_wait4_join']=False
 return v
ns['checked']=wrongraw;reject(ns['root4_outer_parent_actors']);ns['checked']=actual_checked
passed('negative joins, group absence and exact-reference mismatch refused')
retained=ns['validate_retained']()
assert len(retained['actors'])==114
bindings=dict(custody_supplement=c.ref(P.parent/'ROOT-CUSTODY-SUPPLEMENT.ACTUAL.json'))
ns['attach_custody'](bindings,retained)
assert len(retained['actors'])==132
ns['validate_pending_ledger'](actual_checked(newpins['post_root4_pending']),retained)
note=json.loads(actual_checked(newpins['post_root4_pending'])['note'])
result,receipts,retired=ns['validate_retirement'](retained,note['closed_current118_root4_retirement']['result'],newpins['root4_parent_normalized'])
assert len(receipts)==14 and len(retired)==15 and len(retained['actors'])+len(retired)==147
assert sum(a['role']=='CURRENT118_failed_retirement_readonly_client_UNKNOWN'for a in retained['actors'])==1
passed('actual retained132 + unchanged cleanup15 =147;72nonces and UNKNOWN retained')
# Exact additional four-argument API and identical prior-prefix variable at both callsites.
for name in ['validate_new_commands','observe']:
 fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
 calls=[n for n in ast.walk(fn)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='process_source']
 assert len(calls)==1 and len(calls[0].args)==4 and isinstance(calls[0].args[3],ast.Name)and calls[0].args[3].id=='prior_pids'
 validates=[n for n in ast.walk(fn)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='validate_process']
 assert len(validates)==1 and ast.dump(validates[0].args[-1])==ast.dump(calls[0].args[3])
 # Includes receipt prefix and actor prefix; current census command is created later.
 assign=next(n for n in ast.walk(fn)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='prior_pids'for t in n.targets))
 assert (assign.lineno,assign.col_offset)<(calls[0].lineno,calls[0].col_offset)
passed('both exact four-argument callsites share prior-command PID prefix with validator')
old=ast.parse((S/'observe_current64_current118_postjoin.py').read_text())
changed={'attach_custody','source_subjects','validate_new_commands','observe'}
for fn in old.body:
 if isinstance(fn,ast.FunctionDef)and fn.name not in changed:
  after=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==fn.name)
  assert ast.dump(fn,include_attributes=False)==ast.dump(after,include_attributes=False),fn.name
passed('all original pure physical/retained/retirement predicates unchanged')
shared=(c.SOURCE1/'operation_window_guard64.py').read_text()
rewritten=c.rewrite_guard(shared,manifest['guardian'],manifest['thread_id'])
assert "E = Path(" in rewritten
for key in ['cleanup_executor','cleanup_runtime_files','cleanup_source_review']:
 bad=copy.deepcopy(manifest);bad[key]['sha256']='0'*64
 reject(lambda:c.validate_cleanup(pins,bad))
passed('exact reviewed12-source acceptance only and namespace guard constant binding')
print(json.dumps(dict(status='PASS_PURE_SOURCE_METADATA_ONLY',groups=len(checks),checks=checks,retained=132,cleanup=15,total_before_observer=147,runtime_calls=0)))
