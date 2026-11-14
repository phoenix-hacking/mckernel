"""Bounded source authoring only. Does not import or run the authored sources."""
import ast, copy, difflib, hashlib, json, os, uuid
from pathlib import Path
D=Path(__file__).resolve().parent
H=D.parent
OLD=H/'phase5-m03-valid-protection-closure-delta-20261020-1/runtime-next-preparation-1/expert-correction-1/runtime-source-1'
STAGE=H/'phase5-m03-protection-grace-stage-20261020-1'
PRIOR=H/'phase5-m03-protection-nonce-binding-correction-20261020-1/ENTIRE-ACTIVE-TUPLE.json'
R=D/'runtime-source-1'
R.mkdir(mode=0o700)
def ref(p):
 p=Path(p);s=p.lstat();raw=p.read_bytes()
 return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),mode=s.st_mode)
def js(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
 os.chmod(p,0o600)
def write(p,raw):
 with p.open('x') as f:f.write(raw)
 os.chmod(p,0o600)
def assign(tree,name):
 return next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets))
def edits(raw,changes):
 lines=raw.splitlines(keepends=True);offset=[0]
 for line in lines:offset.append(offset[-1]+len(line))
 out=raw
 for n,new in sorted(changes,key=lambda v:(v[0].lineno,v[0].col_offset),reverse=True):
  a=offset[n.lineno-1]+n.col_offset;b=offset[n.end_lineno-1]+n.end_col_offset
  out=out[:a]+new+out[b:]
 return out
prior=json.loads(PRIOR.read_bytes())
oldrefs={n:ref(OLD/n) for n in ['native_diagnostic_backend.py','native_diagnostic_container_owner.py','native_diagnostic_runner.py','native_owner_binding.py','qmp_capture.py']}
evaluator=ref(STAGE/'native_diagnostic.py')
assert evaluator['sha256']=='2827a106e9a82ba1590cb4726d98ef25f337c741b63e5d571ae38850bba39fd6'
changes_report={}
for name in ['native_diagnostic_backend.py','qmp_capture.py']:
 raw=(OLD/name).read_text();write(R/name,raw)
 changes_report[name]=dict(kind='BYTE_IDENTICAL',original=oldrefs[name],new=ref(R/name))
name='native_diagnostic_runner.py';raw=(OLD/name).read_text();tree=ast.parse(raw);changed=[]
for n in ast.walk(tree):
 if isinstance(n,ast.BinOp) and isinstance(n.left,ast.Name) and n.left.id=='_HERE' and isinstance(n.op,ast.Div) and isinstance(n.right,ast.Constant) and n.right.value=='native_diagnostic.py':
  changed.append((n,'Path('+repr(evaluator['path'])+')'))
assert len(changed)==2
out=edits(raw,changed);write(R/name,out)
changes_report[name]=dict(kind='TWO_DIAGNOSTIC_IMPORT_PATH_EXPRESSIONS_ONLY',original=oldrefs[name],new=ref(R/name),edits=len(changed))
name='native_owner_binding.py';raw=(OLD/name).read_text();tree=ast.parse(raw);n=assign(tree,'RUNTIME')
out=edits(raw,[(n.value,'Path('+repr(str(R))+')')]);write(R/name,out)
changes_report[name]=dict(kind='RUNTIME_PATH_LITERAL_ONLY',original=oldrefs[name],new=ref(R/name))
name='native_diagnostic_container_owner.py';raw=(OLD/name).read_text();tree=ast.parse(raw)
oldpins=ast.literal_eval(assign(tree,'SOURCE_HASHES').value)
oldroots=ast.literal_eval(assign(tree,'EXTRA_READONLY').value)
assert oldpins==prior['source_hashes'] and len(oldpins)==prior['preserved_source_pin_counts']['current']
pins=copy.deepcopy(oldpins)
for row in [evaluator,*[ref(R/n) for n in ['native_diagnostic_runner.py','native_diagnostic_backend.py','qmp_capture.py','native_owner_binding.py']]]:
 assert row['path'] not in pins;pins[row['path']]=row['sha256']
roots=[*oldroots,str(R),str(STAGE)]
assert len(set(roots))==len(roots)
changed=[(assign(tree,'RUNNER').value,repr(str(R/'native_diagnostic_runner.py'))),(assign(tree,'SELF').value,repr(str(R/name))), (assign(tree,'SOURCE_HASHES').value,repr(pins)),(assign(tree,'EXTRA_READONLY').value,repr(roots))]
bound=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='bound_manifest')
node=next(n for n in bound.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='source' for t in n.targets))
assert ast.literal_eval(node.value)==prior['evaluator']['path']
changed.append((node.value,repr(evaluator['path'])))
out=edits(raw,changed);write(R/name,out)
changes_report[name]=dict(kind='FIVE_BINDING_ASSIGNMENT_VALUES_ONLY',original=oldrefs[name],new=ref(R/name),old_source_count=len(oldpins),new_source_count=len(pins),old_readonly_extra_count=len(oldroots),new_readonly_extra_count=len(roots))
# Static AST equality after replacing exactly the identified nodes with the new values.
static={}
for name in oldrefs:
 before=ast.parse((OLD/name).read_text());after=ast.parse((R/name).read_text())
 if name=='native_diagnostic_container_owner.py':
  for key in ['RUNNER','SELF','SOURCE_HASHES','EXTRA_READONLY']:assign(before,key).value=copy.deepcopy(assign(after,key).value)
  a=next(n for n in before.body if isinstance(n,ast.FunctionDef) and n.name=='bound_manifest')
  b=next(n for n in after.body if isinstance(n,ast.FunctionDef) and n.name=='bound_manifest')
  aa=next(n for n in a.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='source' for t in n.targets))
  bb=next(n for n in b.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='source' for t in n.targets));aa.value=copy.deepcopy(bb.value)
 elif name=='native_owner_binding.py':assign(before,'RUNTIME').value=copy.deepcopy(assign(after,'RUNTIME').value)
 elif name=='native_diagnostic_runner.py':
  class ReplaceDiagnostic(ast.NodeTransformer):
   def visit_BinOp(self,n):
    if isinstance(n.left,ast.Name) and n.left.id=='_HERE' and isinstance(n.op,ast.Div) and isinstance(n.right,ast.Constant) and n.right.value=='native_diagnostic.py':return ast.parse('Path('+repr(evaluator['path'])+')',mode='eval').body
    return self.generic_visit(n)
  before=ReplaceDiagnostic().visit(before)
 assert ast.dump(before,include_attributes=False)==ast.dump(after,include_attributes=False)
 static[name]=dict(allowed_AST_delta_only=True,source_parsed_only=True)
 patch=''.join(difflib.unified_diff((OLD/name).read_text().splitlines(True),(R/name).read_text().splitlines(True),fromfile=str(OLD/name),tofile=str(R/name)))
 if patch:write(D/(name+'.binding-only.patch'),patch)
nonce=uuid.uuid4().hex
scratch=Path('/home/holden/mckernel-work/scratch')
norm=scratch/'vpg-n261020-1';parent=scratch/'vpg-s261020-1/p';attempt=parent/('attempt-'+nonce)
assert nonce!=prior['prospective_binding']['nonce'] and len(nonce)==32
for path in [norm,parent.parent,D/'normalization-source-1',D/'ordinary-capture-1']:
 assert not os.path.lexists(path)
qmp=str(attempt/'qmp.sock');assert len(os.fsencode(qmp))<=107
stage_proposal=json.loads((STAGE/'STAGE-PROPOSAL.BOUNDED-CAPTURE.json').read_bytes())
future_archive=str(Path(stage_proposal['output'])/'protection.cpio.gz')
manifest_row=dict(path=str(norm/'manifest.json'),sha256=None,size=None,mode=None)
# Full argv proposals are an explicit static expansion of retained exact argv.
# Only exact argv elements and structurally identified mount fields are changed.
replacements={str(OLD/'native_diagnostic_container_owner.py'):str(R/'native_diagnostic_container_owner.py'),str(OLD/'native_diagnostic_runner.py'):str(R/'native_diagnostic_runner.py'),prior['owner']['sha256']:ref(R/'native_diagnostic_container_owner.py')['sha256'],prior['prospective_binding']['nonce']:nonce,prior['prospective_binding']['attempt_parent']:str(parent),prior['prospective_binding']['manifest']['path']:manifest_row['path'],prior['prospective_binding']['manifest']['sha256']:None}
def arg(v):
 if v in replacements:return replacements[v]
 oldattempt=Path(prior['prospective_AF_UNIX_paths']['qmp_socket']).parent if 'qmp_socket' in prior['prospective_AF_UNIX_paths'] else Path(prior['prospective_binding']['attempt_parent'])/('attempt-'+prior['prospective_binding']['nonce'])
 pathmap={'unix:'+str(oldattempt/'qmp.sock')+',server=on,wait=off':'unix:'+qmp+',server=on,wait=off','file:'+str(oldattempt/'serial.log'):'file:'+str(attempt/'serial.log'),'file:'+str(oldattempt/'debugcon.log'):'file:'+str(attempt/'debugcon.log'),prior['full_manifest']['staging']['derived_initramfs']['path']:future_archive,'type=bind,src='+prior['prospective_binding']['attempt_parent']+',dst='+prior['prospective_binding']['attempt_parent']:'type=bind,src='+str(parent)+',dst='+str(parent)}
 # Docker parent mount includes an optional suffix; handle only its exact current field.
 oldmount='type=bind,src='+prior['prospective_binding']['attempt_parent']+',dst='+prior['prospective_binding']['attempt_parent']
 for suffix in ['',',rw']:pathmap[oldmount+suffix]='type=bind,src='+str(parent)+',dst='+str(parent)+suffix
 # Container/ownership namespace names encode the explicit nonce.
 for prefix in ['native-diagnostic-','nd-','mckernel-native-diagnostic-']:
  pathmap[prefix+prior['prospective_binding']['nonce']]=prefix+nonce
 return pathmap.get(v,v)
argv={k:[arg(v) for v in prior[k]] for k in ['owner_argv','inside_owner_argv','container_create_argv','qemu_argv']}
# Docker name is derived literally by current owner, regardless of prefix spelling.
oldcreate=prior['container_create_argv']; idx=oldcreate.index('--name')+1
assert oldcreate[idx].endswith(prior['prospective_binding']['nonce'])
argv['container_create_argv'][idx]=oldcreate[idx][:-len(prior['prospective_binding']['nonce'])]+nonce
inside_len=len(argv['inside_owner_argv']); assert argv['container_create_argv'][-inside_len:]==argv['inside_owner_argv']
# Append exact additional readonly mount pairs immediately before the source-local inside command.
newmounts=[a for p in roots[len(oldroots):] for a in ['--mount','type=bind,src='+p+',dst='+p+',readonly']]
argv['container_create_argv'][-inside_len:-inside_len]=newmounts
assert argv['qemu_argv'][argv['qemu_argv'].index('-qmp')+1]=='unix:'+qmp+',server=on,wait=off'
assert argv['qemu_argv'][argv['qemu_argv'].index('-initrd')+1]==future_archive
# Authoritative complete descriptors: actual rows where bytes exist; null for genuine late values.
future=dict(source_manifest=None,stage_result=None,stage_acceptance=None,stage_acceptance_schema=None,stage_acceptance_decision=None,normalization=None,parent_identity=None,latest_physical=None,LAST_snapshot=None,runtime_release=None,native_result=None)
settings=dict(schema='mckernel.m03-protection-grace-normalization-settings.v1',scope=prior['scope'],case_id=prior['case_id'],runtime_source_directory=str(R),evaluator=evaluator,prior_tuple=ref(PRIOR),stage_proposal=ref(STAGE/'STAGE-PROPOSAL.BOUNDED-CAPTURE.json'),stage_manifest_path=str(Path(stage_proposal['output'])/'manifest.json'),stage_result_path=str(Path(stage_proposal['output'])/'stage-result.json'),stage_base=stage_proposal['base'],accepted_collector=stage_proposal['declared_collector_copy'],accepted_collector_original=stage_proposal['collector'],manifest_directory=str(norm),attempt_parent=str(parent),nonce=nonce,late_fields=future)
js(D/'SETTINGS.json',settings)
physical=H/'phase5-exit7-grace-retry-binding-20261020-1/native_current_physical_projection.py'
shared_reader=dict(source=ref(physical),interface='kind(t); project(t, physical_ref) returns full seven predecessor fields',applicability='Exact current62ba failed Exit7 physical/context only. NOT arbitrary future predecessor. No source/SDK semantics.',future_predecessor=None,execution_here=False)
js(D/'SHARED-PHYSICAL-READER-REF.json',shared_reader)
tuple_=dict(schema='mckernel.m03-protection-grace-entire-runtime-source-tuple.v1',scope=prior['scope'],status='SOURCE_ONLY_UNRUN_NOT_RUNTIME_RELEASE',case_id=prior['case_id'],prior_tuple=ref(PRIOR),evaluator=evaluator,owner=ref(R/'native_diagnostic_container_owner.py'),runner=ref(R/'native_diagnostic_runner.py'),binding=ref(R/'native_owner_binding.py'),bound_manifest_import_literal=evaluator['path'],runner_diagnostic_import_literal=evaluator['path'],binding_RUNTIME=str(R),source_hashes=pins,preserved_source_pin_counts=dict(baseline=prior['preserved_source_pin_counts']['baseline'],prior=prior['preserved_source_pin_counts']['prior'],accepted_current=len(oldpins),current=len(pins)),readonly_ast_counts=dict(prior=len(oldroots),current=len(roots)),readonly_roots=[prior['readonly_roots'][0],prior['readonly_roots'][1],*roots],prospective_binding=dict(manifest=manifest_row,attempt_parent=str(parent),nonce=nonce),prospective_AF_UNIX_paths=dict(qmp_socket=qmp,qmp_socket_bytes=len(os.fsencode(qmp)),limit_bytes=107),future_stage_output_manifest=None,late_fields=future,argv_derivation='Static exact-argument and structurally identified mount expansion from accepted prior full tuple; full owner/inside/container/QEMU argv below. Null manifest SHA is genuine late stage data and makes proposal unexecutable. Actual complete argv equality required after actual byte-exact normalization.',future_archive_path=future_archive,full_manifest=None,source_manifest=None,stage_acceptance=None,**argv,tests=0,imports=0,normalization_runs=0,root_operations=0,guest_runs=0)
js(D/'ENTIRE-ACTIVE-TUPLE.PROPOSAL.json',tuple_)
js(D/'STATIC-SOURCE-ASSERTIONS.json',dict(schema='mckernel.m03-protection-grace-runtime-static-source-assertions.v1',files=static,changes=changes_report,old_source_pins_preserved=all(pins.get(k)==v for k,v in oldpins.items()),current_source_count=len(pins),current_extra_readonly_count=len(roots),all_source_lists_AST_derived=True,sole_external_evaluator=evaluator,mechanical_nonce_32hex=len(nonce)==32 and all(c in '0123456789abcdef' for c in nonce),future_paths_absent_when_prepared=True,full_AF_UNIX_qmp_bytes=len(os.fsencode(qmp)),all_five_sibling_paths_resolve=True,generated_sources_imported=False,tests=0))
print(json.dumps(dict(status='SOURCE_AUTHORING_ONLY',runtime_files=len(oldrefs),source_pins=len(pins),extra_readonly_roots=len(roots),QMP_bytes=len(os.fsencode(qmp)),guest_runs=0)))
