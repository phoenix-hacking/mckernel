"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact CID-only permitted read method; preserve every original identity predicate.
"""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;P=D.parent.parent
def ref(p):
 p=Path(p).resolve();raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(n,v):
 p=D/n;assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n');return ref(p)
b=json.loads((P/'BINDINGS.json').read_text());old=ref(P/'retire_exact_failed_guard.py');assert old['sha256']=='4ed5a02f1d64dbd1ed9280fbe039e3700e0e0ead321af2def0c4cf3e16b4c300'
cid=next(r for r in b['protected'] if r['path'].endswith('/ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3/OUTPUT/container.cid'))
failed=json.loads((D.parent/'FAILED-REBIND-ATTEMPT-1.json').read_text());failure=put('FAILED-REBIND-ATTEMPT-1.json',failed)
b.update(controlled_cid_subject=cid,pre_identity_correction_executor=old,failed_rebind_attempt=failure,atime_contract='Original3fdb stable metadata explicitly excludes atime; current caller/profile/release add no atime predicate. Root explicitly permits ordinary read for this exact CID only.')
b['prior_actors'].extend([dict(pid=2247306,start=103642908,role='failed_guard_rebind_executor_joined1'),dict(pid=2247305,start=103642905,role='failed_guard_rebind_parent_joined1')])
binding=put('BINDINGS.json',b)
code=Path(old['path']).read_text().replace("BINDINGS_SHA='b58dd562cef34d08cae2d9028f80024ae723b11e3d37320bd82b4c8e68868c6b'","BINDINGS_SHA='"+binding['sha256']+"'")
anchor='def protected_inputs(release,profile):';assert code.count(anchor)==1
addition='''def controlled_cid_identity(path):
 # Only this exact retained CID receives the same permitted ordinary-read method
 # as the original fixed Python executable. No shared module/global is changed.
 need(Path(path)==Path(B['controlled_cid_subject']['path']),'exact controlled CID read exception only')
 tree=ast.parse(T.authenticated(B['primitive']))
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='file_identity')
 assignment=next(n for n in ast.walk(node) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='noatime' for t in n.targets))
 need(isinstance(assignment.value,ast.IfExp),'unchanged original read flag anchor')
 assignment.value.test=ast.BoolOp(op=ast.Or(),values=[assignment.value.test,ast.Compare(left=ast.Name(id='path',ctx=ast.Load()),ops=[ast.Eq()],comparators=[ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(B['controlled_cid_subject']['path'])],keywords=[])])])
 ast.fix_missing_locations(node);context=dict(vars(M))
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(SELF),'exec'),context)
 return context['file_identity'](Path(path))

'''
code=code.replace(anchor,addition+anchor)
anchor="T.authenticated(r);row,_=M.file_identity(Path(r['path']))";assert code.count(anchor)==1
code=code.replace(anchor,"T.authenticated(r);row,_=(controlled_cid_identity(Path(r['path'])) if r==B['controlled_cid_subject'] else M.file_identity(Path(r['path'])))")
anchor="for key in ['primitive','historical_profile','transport_executor','transport_bindings','portable_converter','guardian','controls','earliest_caps','reconciliation_facts','reconciliation_review']:T.authenticated(B[key])"
assert code.count(anchor)==1;code=code.replace(anchor,anchor+"\n for key in ['controlled_cid_subject','pre_identity_correction_executor','failed_rebind_attempt']:T.authenticated(B[key])")
anchor="rows.update({k:B[k] for k in ('profile','primitive','historical_profile','transport_executor','transport_bindings','portable_converter','guardian','reconciliation_facts','reconciliation_review')})";assert code.count(anchor)==1
code=code.replace(anchor,anchor+"\n rows.update({k:B[k] for k in ('pre_identity_correction_executor','failed_rebind_attempt')})")
(D/'retire_exact_failed_guard.py').write_text(code)
(D/'test_guard_rebind.py').write_text((P/'test_guard_rebind.py').read_text().replace("len(m.B['prior_actors']),109","len(m.B['prior_actors']),111"))
put('UNSELECTED-PRIVILEGED-DRAFT.json',dict(scope=b['scope'],runtime_authority=None,status='UNSELECTED_BEFORE_ANY_PRIVILEGED_EXECUTION',reason='Root steering confirmed no atime predicate; exact CID read exception selected. Prior privileged entry/draft source retained unchanged in parent directory.',actual_privileged_identity_calls=0,actual_queries_or_effects=0))
print(json.dumps(dict(executor=ref(D/'retire_exact_failed_guard.py'),bindings=binding,controlled_cid=cid)))
