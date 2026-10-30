"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused changed metadata/route source review and real pure operation binding.
"""
from pathlib import Path
import ast,json,hashlib,importlib.util,time,copy
D=Path(__file__).resolve().parent;P=D.parent;A=P.parent;OLD=A/'M14-CONVERSION-FIRST-CURRENT-FRONTIER-PREPARATION-1/parent-ownership-correction-1'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def nodes(p):return {n.name:n for n in ast.parse(Path(p).read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ready=read(P/'SOURCE-READY.json');assert ref(P/'SOURCE-READY.json')['sha256']=='c1ac4fc6c7ae5e9da30a823e0da0021c8a144fe12bbea7b897017e40db992080'
for row in ready['files'].values():assert ref(row['path'])==row
old=nodes(OLD/'readonly_operation_guard.py');new=nodes(P/'readonly_operation_guard.py')
q_names=['validate_operation','confirmed_weekly_ceiling','_evaluate','guard','current_cutoffs']
for n in q_names:assert ast.dump(old[n],include_attributes=False)==ast.dump(new[n],include_attributes=False),n
assert (P/'root_capture_parent.py').read_text()==(OLD/'root_capture_parent.py').read_text().replace('observe_conversion_frontier.py','observe_conversion_postjoin.py')
x=nodes(OLD/'observe_conversion_frontier.py');y=nodes(P/'observe_conversion_postjoin.py');unchanged=[]
for n in x:
 if n not in ['observe','main']:
  assert ast.dump(x[n],include_attributes=False)==ast.dump(y[n],include_attributes=False),n
  unchanged.append(n)
obs=(P/'observe_conversion_postjoin.py').read_text();body=obs[obs.index('def observe():'):obs.index('\ndef main():')];assert 'history.validate(read(context[\'source_authority\']))'in body and 'checker.validate_metadata()'not in body
assert 'for actor in actors:'in body and 'executor.process_source(normal,packet,live_b,[])'in body
saved=read(P/'PURE-CHECKS.json');assert saved['status']=='PASS_SOURCE_AND_ACTUAL_RETAINED_POSTRETIREMENT_DATA_WITH_SYNTHETIC_CONTEXT_ONLY'and len(saved['negative_custody_cases'])==5 and saved['pre_capture_rows']==230 and saved['pre_capture_distinct']==225 and saved['unchanged_Q_AST']is True
pins=read(P/'HISTORY-INPUTS.json');accept=read(pins['independent_retirement_acceptance']['path']);assert ref(pins['independent_retirement_acceptance']['path'])==pins['independent_retirement_acceptance']and accept['decision']=='PASS_EXACT_CONVERSION_FIRST_NORMAL_RETIREMENT_WITH_TYPED_ROOT_TOOL_CLOSURE'
resource=read(pins['actual_build_resource']['path']);assert ref(pins['actual_build_resource']['path'])==pins['actual_build_resource'];collector=resource['actual_observations']['resource_collector'];assert (collector['pid'],collector['birth'],collector['process_group'])==(2624123,111570045,2624123)
source=dict(schema='mckernel.independent-postretirement-readonly-source-review.v1',scope=__doc__.splitlines()[0],decision='PASS_SOURCE',reviewer='/root/recovery_review',independent=True,implementation_ownership=False,recorded_at=time.time(),source_ready=ref(P/'SOURCE-READY.json'),files=ready['files'],observer=ref(P/'observe_conversion_postjoin.py'),guard=ref(P/'readonly_operation_guard.py'),history=ref(P/'postjoin_history.py'),parent=ref(P/'root_capture_parent.py'),history_inputs=ref(P/'HISTORY-INPUTS.json'),independent_actual_retirement_acceptance=pins['independent_retirement_acceptance'],unchanged_Q_function_AST=q_names,unchanged_observer_function_AST=unchanged,parent_exact_predecessor_except_observer_basename=True,changed_scope='New actual74nonce/Root70 pending route, accepted69216 retirement typed closure, resourcecollector plus230frontier data; inherited physical/history/census/resource algorithms retained.',pure_tests_reused=ref(P/'PURE-CHECKS.json'),new_collector=collector,frontier=dict(prior=212,retirement_scope=229,pre_capture=230,distinct=225,retained_duplicates=5),findings=['Historical5326 remains provenance only; new observer returns candidate/pending, never selfacceptance/currentfree.','History requires exact independently accepted69216/bc2df/0750 and Root typed closure; no invented parent wait4 or unknown birth.','All18 newly measured identities are included before unchanged complete process/PID/FD/group/cgroup/holder predicates; inherited groups remainNone and all UNKNOWN fields retained.','Exact distinct readonly operation and unused readonly ID; no build/native grant alias. Q confirmed usage and actual effective three-clock minima functions remain exact predecessor AST.','Existing7652 parent owns directwait4, streams, child group census and atomic no-overwrite publication; actualAnaconda3.9 required for inherited ast.unparse.','Five meaningful source custody negatives and coherent synthetic context checks are preserved; only actual upcoming operation uses real Root data.'],source_implementation_only=True,current_free=False,native_acceptance=False,C_retirement=False,runtime_authority=None)
sp=D/'SOURCE-REVIEW.ACTUAL.json';tmp=sp.with_suffix('.tmp');tmp.write_text(json.dumps(source,indent=2)+'\n');tmp.replace(sp)
op_path=P/'CONVERSION-FRONTIER-READONLY-OPERATION.PENDING-REVIEW.json';assert ref(op_path)['bytes']==10178 and ref(op_path)['sha256']=='88c00216aac91e7628d6b2c9a4a273dc4da070c893145a03dcbfda88a5b6eb2e';op=read(op_path);g=load(P/'readonly_operation_guard.py','independent_real_postretirement_readonly_operation')
subjects=g.context_subjects(op['context']);guardian=g.load(subjects['guardian'],'pure_current_Q_metadata');arm=g.read(op['context']['armed_controls']);bootstrap=g.read(op['context']['bootstrap_caps']);binder=g.load(g.read(g.FIXED)['accepted_helper'],'pure_weekly_limit_binder');caps=binder.weekly_limits(arm,bootstrap);assert list(caps)==op['operation_cutoffs']
review=dict(schema='mckernel.independent-operation-window-review.v1',decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,implementation_ownership=False,reviewer='/root/recovery_review',operation=g.OPERATION,successor=op,source_review=ref(sp),recorded_at=time.time(),pure_validation='actual context_subjects and validate_operation; no _evaluate/guard/process query')
g.validate_operation(op,review,subjects,op['context'],[0,0,0],caps)
p=D/'OPERATION-REVIEW.ACTUAL.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(review,indent=2)+'\n');tmp.replace(p);print(json.dumps(dict(source=ref(sp),operation=ref(p),subjects=len(subjects),caps=caps)))
