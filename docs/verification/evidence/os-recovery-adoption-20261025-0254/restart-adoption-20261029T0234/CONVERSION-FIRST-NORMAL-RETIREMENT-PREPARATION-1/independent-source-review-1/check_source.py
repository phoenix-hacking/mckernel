"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused source and actual retained metadata only, no live operations.
"""
from pathlib import Path
import ast,hashlib,json,copy,time,contextlib,io
D=Path(__file__).resolve().parent;P=D.parent;A=P.parent;OLD=A/'CURRENT119-NORMAL-RETIREMENT-PREPARATION-1/parent-custody-data-correction-1'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
ready=read(P/'SOURCE-READY.json');before={k:ref(v['path'])for k,v in ready['files'].items()};assert before==ready['files']
files=read(P/'RUNTIME-FILES.json')
for r in files.values():assert ref(r['path'])==r
raw=(P/'retire_exact_conversion_stopped_container.py').read_text();prior=(OLD/'retire_exact_current119_stopped_container.py').read_text()
def nodes(s):return {n.name:n for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a,c=nodes(prior),nodes(raw);assert a.keys()==c.keys()
# Exact published schema renames only, retaining all other string predicates.
prior=prior.replace('mckernel.current119-build.','mckernel.conversion-first-build.').replace('PASS_EXACT_CURRENT119_STOPPED_CONTAINER_RETIRED_PENDING_POSTJOIN_CURRENT','PASS_EXACT_CONVERSION_FIRST_STOPPED_CONTAINER_RETIRED_PENDING_POSTJOIN_CURRENT').replace('GRANT_ONE_EXACT_STOPPED_CURRENT119_CONTAINER_RETIREMENT','GRANT_ONE_EXACT_STOPPED_CONVERSION_CONTAINER_RETIREMENT')
an=nodes(prior);unchanged=[]
for n in a:
 if n not in ['validate_retained','validate_release']:
  assert ast.dump(an[n],include_attributes=False)==ast.dump(c[n],include_attributes=False),n
  unchanged.append(n)
tree=ast.parse((P/'test_source.py').read_text());kept=[]
for n in tree.body:
 if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call):
  fn=n.value.func
  if isinstance(fn,ast.Attribute)and fn.attr=='write_text':continue
  if isinstance(fn,ast.Name)and fn.id=='print':continue
 kept.append(n)
env={'__file__':str(P/'test_source.py'),'__name__':'independent_pure_source_test'};start=time.monotonic();stdout=io.StringIO()
with contextlib.redirect_stdout(stdout):exec(compile(ast.Module(body=kept,type_ignores=[]),str(P/'test_source.py')+':REPORT-WRITE-OMITTED','exec'),env)
assert env['out']['status']=='PASS_SOURCE_AND_ACTUAL_RETAINED_DATA_ONLY'and len(env['negative'])==7
assert {k:ref(v['path'])for k,v in ready['files'].items()}==before
b=env['b'];packet=env['packet'];protected=env['protected'];oldprotected=read(OLD/'PROTECTED-ORIGINALS.json');rmap={r['path']:r for r in protected['records']}
for r in oldprotected['records']:assert rmap[r['path']]==r
free=read(packet['source_refs']['accepted_capture_current_free']['path']);assert b['prior_actors']==free['next_full_postjoin_actor_frontier']
assert len(b['prior_actors'])==212 and len({(x['pid'],x['start'])for x in b['prior_actors']})==207
assert b['new_known_actors']==[dict(pid=2623592,start=111558755,role='conversion_build_holder',group=None,fd=3),dict(pid=2624628,start=111575974,role='conversion_build_runner',group=None,fd=None)]
assert all(rmap[r['path']]['sha256']==r['sha256']for r in packet['retained_actual_outputs'])
assert len(packet['retained_actual_outputs'])==3
result=dict(scope=__doc__.splitlines()[0],status='PASS_CHANGED_CONSUMER_AND_EXACT_ACTUAL_RETAINED_DATA_ONLY',elapsed_seconds=time.monotonic()-start,source_ready=ref(P/'SOURCE-READY.json'),runtime_files=files,unchanged_function_class_AST_except_three_exact_schema_renames=unchanged,changed_functions=['validate_retained','validate_release'],test_source=ref(P/'test_source.py'),test_only_final_author_report_write_and_print_omitted=True,actual_pure_test=env['out'],original_protected_records_preserved=len(oldprotected['records']),actual_protected_records=len(protected['records']),retained_prior_rows=212,distinct_prior_identities=207,new_known_actors=b['new_known_actors'],unknowns=b['actor_gaps'],author_files_unchanged=True,guard_proc_Docker_compiler_native_cleanup_calls=0)
p=D/'CHECKS.ACTUAL.json';p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(ref(p)))
