"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One-pass additive output/preparation successor constructor; no candidate module import or test execution.
"""
import ast,copy,hashlib,json,re,stat
from pathlib import Path
N=Path(__file__).parent;Z=N.parent;PUB=N/'publication-preparation'
def ref(p):p=Path(p);return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
def put(p,o):p.write_text(json.dumps(o,sort_keys=True,indent=2)+'\n');return ref(p)
names=['run_frozen_current290_image_entry.ATTEMPT4.READONLY-SEED.py','fill_existing_current290_image_payload.ATTEMPT4.READONLY-SEED.py','capture_existing_c252_for_current290_entry.ATTEMPT4.READONLY-SEED.py','capture_readonly_admission.CURRENT290-IMAGE-ONLY.NOT-EXECUTED.py','native_rust_cutover_image_terminal_cleanup.CURRENT290.ATTEMPT4.READONLY-SEED.py','current290_cleanup_typed_protocol.ATTEMPT4.READONLY-SEED.py','FROZEN-CURRENT290-IMAGE-ENTRY-INPUTS.ATTEMPT4.READONLY-SEED.json','ROOT-PREPARATION-CONTEXT.ATTEMPT4.READONLY-SEED.PENDING-HOLDER-CLOCK-GRANTS.json','FROZEN-CURRENT290-CLEANUP-TYPED-PROTOCOL-CONTRACT.ATTEMPT4.READONLY-SEED.json','ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json','COMPACT-C252-CENSUS-REQUEST.FRESH-DIAGNOSTIC.TEMPLATE.NOT-GRANTED.json','READONLY-ADMISSION-ARGV.CURRENT290-IMAGE-ONLY.NOT-EXECUTED.json','READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json']
files=[Z/n for n in names]
# Exact stable source and retained evidence paths outrank the generic old output prefix.
paths={str(p):str(N/p.name) for p in files}
for name in ['attempt4_exact_source_origin_binding.READONLY-SEED.py','CURRENT-ATTEMPT4-REQUEST-ORIGINAL69-EXACT-ORIGIN-DELTA.json','ATTEMPT4-468813-11B6-RECOVERED-CURRENT-PHYSICAL-NAMESPACE.BINDING.json','validate_exact_failed_owner15_recovery_current_physical.SOURCE-ONLY.py','EXACT-INITIALIZER15-TO-RUNTIME213-ACCEPTED-VALIDATOR-ROLE-JOIN.SOURCE-ONLY.json','attempt4_readonly_seed_cleanup_mode.py','EXACT-ROLEJOIN-PRODUCER-FIXTURES.SOURCE-ONLY.json']:
 p=Z/name;paths[str(p)]=str(p)
paths[str(Z)]=str(N)
pattern=re.compile('|'.join(re.escape(k) for k in sorted(paths,key=len,reverse=True)))
def pathtext(s):return pattern.sub(lambda m:paths[m.group()],s)
hashes={};done=set();active=set()
def jsonupdate(o):
 if isinstance(o,list):return [jsonupdate(v) for v in o]
 if isinstance(o,str):return pathtext(o)
 if not isinstance(o,dict):return o
 if set(o)=={'path','sha256','bytes'}:
  target=pathtext(o['path'])
  if target!=o['path'] and Path(target).is_file():return ref(target)
 return {k:jsonupdate(v) for k,v in o.items()}
def build(p):
 if p.name in done:return
 if p.name in active:raise RuntimeError('dependency cycle '+p.name)
 active.add(p.name);s=p.read_text()
 for q in files:
  if q!=p and (str(q) in s or ref(q)['sha256'] in s):build(q)
 target=N/p.name
 if p.suffix=='.json':
  o=jsonupdate(json.loads(s))
  if p.name.startswith('READY-'):
   o.update(predecessor_READY=ref(p),bootstrap_correction='Only fresh preparation/output paths and exact authentication propagation; all function/class logic retained',status='FRESH_OUTPUT_PREPARATION_SOURCE_ONLY_PENDING_NEW_CLOCK_CENSUS_REVIEW_AND_GRANTS',predecessor_expired_captures_preserved=str(Z/'actual-entry-1'),future_ROOT_grant=None,future_census=None,future_clock=None,future_five=None,future_holder=None,future_retirement_acceptance=None)
  put(target,o)
 else:
  edits=[];lines=s.splitlines(keepends=True);offset=[0]
  for line in lines:offset.append(offset[-1]+len(line))
  for node in ast.walk(ast.parse(s)):
   if isinstance(node,ast.Dict):
    try:o=ast.literal_eval(node)
    except (ValueError,TypeError,SyntaxError):continue
    if isinstance(o,dict) and set(o)=={'path','sha256','bytes'}:
     updated=jsonupdate(o)
     if updated!=o:edits.append((offset[node.lineno-1]+node.col_offset,offset[node.end_lineno-1]+node.end_col_offset,repr(updated)))
  combined=dict(paths);combined.update(hashes);patt=re.compile('|'.join(re.escape(k) for k in sorted(combined,key=len,reverse=True)))
  transform=lambda value:patt.sub(lambda m:combined[m.group()],value)
  chunks=[];last=0
  for start,end,value in sorted(edits):chunks.extend([transform(s[last:start]),value]);last=end
  chunks.append(transform(s[last:]));target.write_text(''.join(chunks));ast.parse(target.read_text())
 hashes[ref(p)['sha256']]=ref(target)['sha256'];active.remove(p.name);done.add(p.name)
for p in files:build(p)
R=json.loads((N/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json').read_bytes())
combined=dict(paths);combined.update(hashes);patt=re.compile('|'.join(re.escape(k) for k in sorted(combined,key=len,reverse=True)))
def alltext(s):return patt.sub(lambda m:combined[m.group()],s)
def template(o):
 if isinstance(o,list):return [template(v) for v in o]
 if isinstance(o,str):return alltext(o)
 if not isinstance(o,dict):return o
 if set(o)=={'path','sha256','bytes'}:
  v=jsonupdate(o)
  if v!=o:return v
 return {k:template(v) for k,v in o.items()}
for name in ['ROOT-OWNER213-ROLEJOIN-PRECLOCK-CONTEXT.TEMPLATE.PENDING-ROOT.json','ROOT-OWNER213-ROLEJOIN-STATIC-PREPARATION-GRANT.TEMPLATE.PENDING-ROOT.json','EXACT-OWNER213-ROLEJOIN-CALLER-CENSUS-GRANT-CLEANUP-COMMANDS.NOT-GRANTED.json']:
 doc=template(json.loads((Z/'publication-preparation'/name).read_bytes()))
 if 'PRECLOCK' in name:doc.update(latest_expired_preowner_retirement_proof=None,latest_expired_preowner_retirement_acceptance=None,root_recording_pending=True,all_actual_root_holder_clock_grants_pending=True)
 put(PUB/name,doc)
# Prepare a single TEMP producer/prequery control from the previously passing exact function logic.
original=Z/'test_exact_recovered_physical_and_producer.PURE.NOT-RUN.py';test=original.read_text();tree=ast.parse(test);lines=test.splitlines(keepends=True)
for node in sorted([n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name.startswith('test_') and n.name!='test_REAL_prepare_finish_emits_runtime213_and_retains_initializer15'],key=lambda n:n.lineno,reverse=True):del lines[node.lineno-1:node.end_lineno]
test=''.join(lines);tree=ast.parse(test);lines=test.splitlines(keepends=True)
# bootstrap helper belongs to the separately accepted old control; it is not rerun here.
for node in sorted([n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='bootstrap_to_transport_boundary'],key=lambda n:n.lineno,reverse=True):del lines[node.lineno-1:node.end_lineno]
test=''.join(lines).replace("F=json.loads((HERE/'EXACT-ROLEJOIN-PRODUCER-FIXTURES.SOURCE-ONLY.json').read_bytes())", "F=json.loads(Path("+repr(str(Z/'EXACT-ROLEJOIN-PRODUCER-FIXTURES.SOURCE-ONLY.json'))+").read_bytes())")
(N/'test_fresh_output_paths_and_actual_prepare_finish.PURE.NOT-RUN.py').write_text(test)
# Function/class code must be identical after only inverse authenticated constants/path propagation.
inverse_paths={v:k for k,v in paths.items() if v!=k};inverse_hashes={v:k for k,v in hashes.items() if v!=k}
checks=[]
for p in files:
 if p.suffix!='.py':continue
 old=ast.parse(p.read_text());new=ast.parse((N/p.name).read_text());inverse=dict(inverse_paths);inverse.update(inverse_hashes)
 inverse_bytes={}
 for q in files:
  qr=ref(q);nr=ref(N/q.name)
  if qr['bytes']!=nr['bytes']:inverse_bytes[(nr['path'],nr['sha256'],nr['bytes'])]=qr
 class Restore(ast.NodeTransformer):
  def visit_Dict(self,node):
   try:v=ast.literal_eval(node)
   except (ValueError,TypeError,SyntaxError):return self.generic_visit(node)
   if isinstance(v,dict) and set(v)=={'path','sha256','bytes'}:
    key=(v['path'],v['sha256'],v['bytes'])
    if key in inverse_bytes:return ast.parse(repr(inverse_bytes[key]),mode='eval').body
   return self.generic_visit(node)
  def visit_Constant(self,node):
   if isinstance(node.value,str):
    if node.value in inverse:node.value=inverse[node.value]
    else:
     pat=re.compile('|'.join(re.escape(k) for k in sorted(inverse_paths,key=len,reverse=True)))
     node.value=pat.sub(lambda m:inverse_paths[m.group()],node.value)
   return node
 restored=Restore().visit(new)
 oldnodes=[n for n in old.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))];newnodes=[n for n in restored.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
 same=ast.dump(ast.Module(body=oldnodes,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=newnodes,type_ignores=[]),include_attributes=False)
 checks.append(dict(source=ref(p),successor=ref(N/p.name),all_function_class_AST_same_after_authentication_unbinding=same,function_class_count=len(oldnodes)))
 if not same:raise RuntimeError('function AST changed beyond authenticated constants '+p.name)
# Audit every local successor reference without executing any candidate code.
local=[];errors=[];strings=[]
def walk(o,label):
 if isinstance(o,dict):
  if set(o)=={'path','sha256','bytes'}:
   if str(o['path']).startswith(str(N)+'/'):
    valid=Path(o['path']).is_file() and ref(o['path'])==o;local.append(dict(label=label,reference=o,exact=valid))
    if not valid:errors.append(label)
  for k,v in o.items():walk(v,label+'.'+k)
 elif isinstance(o,list):
  for i,v in enumerate(o):walk(v,label+'['+str(i)+']')
 elif isinstance(o,str) and o.startswith(str(N)+'/'):strings.append(dict(label=label,path=o,exists=Path(o).exists()))
for p in [N/q.name for q in files if q.suffix=='.json']+[PUB/name for name in ['ROOT-OWNER213-ROLEJOIN-PRECLOCK-CONTEXT.TEMPLATE.PENDING-ROOT.json','ROOT-OWNER213-ROLEJOIN-STATIC-PREPARATION-GRANT.TEMPLATE.PENDING-ROOT.json','EXACT-OWNER213-ROLEJOIN-CALLER-CENSUS-GRANT-CLEANUP-COMMANDS.NOT-GRANTED.json']]:walk(json.loads(p.read_bytes()),p.name)
for p in N.glob('*.py'):
 if p.name.startswith('construct_'):continue
 for node in ast.walk(ast.parse(p.read_text())):
  if isinstance(node,ast.Dict):
   try:o=ast.literal_eval(node)
   except (ValueError,TypeError,SyntaxError):continue
   if isinstance(o,dict) and set(o)=={'path','sha256','bytes'}:walk(o,p.name+':dict:'+str(node.lineno))
  elif isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.startswith(str(N)+'/'):strings.append(dict(label=p.name+':str:'+str(node.lineno),path=node.value,exists=Path(node.value).exists()))
for p in N.glob('*'):
 if p.is_dir() and p.name!='publication-preparation':errors.append('unexpected output directory '+p.name)
 if p.is_file() and p.name not in ['construct_fresh_output_preparation_successor.STATIC-ONLY.py'] and '/fresh-clock-successor1-source-1/fresh-clock-successor1-source-1/' in p.read_text():errors.append('duplicate segment '+p.name)
audit=put(PUB/'EXACT-FRESH-OUTPUT-PATHS-AND-REFERENCE-PINS.STATIC-ONLY.json',dict(scope=R['scope'],status='PASS_STATIC_REFERENCE_PATH_AND_FUNCTION_AST_BINDINGS' if not errors else 'FAIL',local_ref_checks=local,local_ref_count=len(local),function_class_AST_checks=checks,errors=errors,observed_local_paths=strings,actual_tests=0,candidate_module_imports=0,queries=0,actual_grants_copied=0,actual_captures_copied=0,namespace_reinitialization=False,ttl_seconds=120))
argv=['/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--stack=2097152:2097152','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(N/'test_fresh_output_paths_and_actual_prepare_finish.PURE.NOT-RUN.py'),'Controls.test_REAL_prepare_finish_emits_runtime213_and_retains_initializer15']
prior=Z/'capture-write-fixture-correction1-source-1'
coverage=put(N/'EXISTING-LOGIC-COVERAGE-AND-ONE-FRESH-PATH-CONTROL.NOT-GRANTED.json',dict(scope=R['scope'],status='SOURCE_ONLY_PENDING_ONE_NEW_PATH_PRODUCER_CONTROL_AND_INDEPENDENT_REVIEW',ready=ref(N/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json'),static_audit=audit,unchanged_logic_actual_original_controls=dict(test=ref(original),join=ref(Z/'actual-pure-controls-1/JOIN.json'),stderr=ref(Z/'actual-pure-controls-1/stderr')),unchanged_logic_actual_fullpositive=dict(test=ref(prior/'test_exact_recovered_physical_fullpositive.CAPTURE-WRITES-ONLY.NOT-RUN.py'),join=ref(prior/'actual-positive-only-1/JOIN.json'),stderr=ref(prior/'actual-positive-only-1/stderr')),new_control=ref(N/'test_fresh_output_paths_and_actual_prepare_finish.PURE.NOT-RUN.py'),new_control_count=1,ordinary_test_argv=argv,all_actual_grants_pending=True,existing_logic_replay=False,output_path_only=True,ttl_seconds=120))
expected=put(PUB/'EXPECTED-FRESH-COHORT-BEFORE-LIVE-CLOCK.SOURCE-ONLY.json',dict(scope=R['scope'],status='STATIC_EXPECTED_REFS_NOT_ACTUAL_PAYLOAD_ACCEPTANCE',ready=ref(N/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json'),caller=R['caller'],config=R['config'],fill=R['fill'],cleanup=R['cleanup'],protocol=R['protocol'],contract=R['contract'],owner=R['owner'],request=R['request'],namespace_initialization=R['namespace_initialization'],physical=R['physical'],physical_postjoin=json.loads((N/'FROZEN-CURRENT290-IMAGE-ENTRY-INPUTS.ATTEMPT4.READONLY-SEED.json').read_bytes())['postjoin'],static_expected_P=str(N),static_expected_capture_root=str(N/'actual-entry-1'),source_origin_helper=R['origin_helper'],source_origin_data=R['origin_data'],mode_adapter=R['mode_adapter'],readonly_seed=R['seed'],all_actual_grants_census_clock_and_holder_pending=True))
manifestpath=PUB/'FRESH-OUTPUT-PREPARATION-SOURCE-PUBLICATION-MANIFEST.PENDING-CONTROL.json';members=[p for p in N.rglob('*') if p.is_file() and p!=manifestpath];repo=Path('/home/holden/mckernel');rows=[dict(source=str(p),repository=str(p.relative_to(repo)),sha256=ref(p)['sha256'],bytes=p.stat().st_size,git_mode='100644',mode=oct(stat.S_IMODE(p.stat().st_mode))) for p in sorted(members)]
manifest=put(manifestpath,dict(scope=R['scope'],status='SOURCE_READY_NEW_PATH_CONTROL_NOT_GRANTED',ready=ref(N/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json'),coverage=coverage,static_expected=expected,files=rows,stage_paths=[r['repository'] for r in rows],actual_controls=None,independent_review=None,future_root_grant=None))
print(json.dumps(dict(scope=R['scope'],ready=ref(N/'READY-OWNER213-FRONTEND.SOURCE-ONLY.NOT-GRANTED.json'),coverage=coverage,expected=expected,manifest=manifest,local_refs=len(local),function_AST_checks=len(checks),errors=errors),indent=2))
