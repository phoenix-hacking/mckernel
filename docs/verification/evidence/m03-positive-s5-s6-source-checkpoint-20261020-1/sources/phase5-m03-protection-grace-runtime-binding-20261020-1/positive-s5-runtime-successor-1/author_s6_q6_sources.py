"""Pure finite source/DATA authoring; generated controls remain unexecuted."""
from pathlib import Path
import ast,copy,difflib,hashlib,json,os
D=Path(__file__).resolve().parent;B=D.parent;H=B.parent
OLD=B/'s4-q4-source-preparation-1';OS=OLD/'non-temporal-source-4';OQ=OLD/'native-control-packet-4'
S=D/'non-temporal-source-6';Q=D/'native-control-packet-6';S.mkdir(mode=0o700);Q.mkdir(mode=0o700)
POS=B/'positive-s5-predecessor-binding-1';R=H/'phase5-m03-native-app-binding-independent-review-20261020-1';PHYSICAL=R/'ACTUAL-EXIT7-GRACE-CORRECTED-LAST-NATIVE-PHYSICAL-RETIREMENT-REVIEW.json';ACCEPTANCE=R/'ACTUAL-M03-POSITIVE-S5-PHYSICAL-CONSUMER-AND-TWO-WITNESS-ACCEPTANCE.json'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def typed(p):
 p=Path(p);r=ref(p);return dict(path=r['path'],sha256=r['sha256'],size=r['bytes'],mode=p.lstat().st_mode)
def load(p):return json.loads(Path(p).read_bytes())
def write(p,raw):
 with p.open('x') as f:f.write(raw)
 p.chmod(0o600)
def js(p,v):write(p,json.dumps(v,indent=2,sort_keys=True)+'\n')
def relocate(v):
 if isinstance(v,str):
  if v==str(OS/'materialize_s4_q4_static_inputs_once.py'):return str(S/'materialize_s6_q6_static_inputs_once.py')
  for old,new in [(OQ,Q),(OS,S)]:
   if v==str(old) or v.startswith(str(old)+'/'):return str(new)+v[len(str(old)):]
  return v
 if isinstance(v,list):return [relocate(x) for x in v]
 if isinstance(v,dict):return {k:relocate(x) for k,x in v.items()}
 return v
def edit(raw,changes):
 offsets=[0]
 for line in raw.splitlines(True):offsets.append(offsets[-1]+len(line))
 for n,s in sorted(changes,key=lambda x:(x[0].lineno,x[0].col_offset),reverse=True):
  a=offsets[n.lineno-1]+n.col_offset;b=offsets[n.end_lineno-1]+n.end_col_offset;raw=raw[:a]+s+raw[b:]
 return raw
def literal_map(raw,mapping):
 tree=ast.parse(raw);changes=[(n,repr(mapping[n.value])) for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value in mapping]
 return edit(raw,changes),len(changes)
def predicate(raw,label,value):
 tree=ast.parse(raw);nodes=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='need' and len(n.args)>1 and isinstance(n.args[1],ast.Constant) and n.args[1].value==label];assert len(nodes)==1,label
 return edit(raw,[(nodes[0].args[0],value)])
assert ref(ACCEPTANCE)['sha256']=='33f023f26c65982e27b25ebf38b27377c8618a156aa50e0ded2344a8f59d88b3'
actual=load(ACCEPTANCE);assert actual['source']==ref(POS/'native_positive_s5_physical_projection.py') and actual['genuine_current_physical']==ref(PHYSICAL)
changes=[]
for oldname in ['machine_assembly_caller.py','run_final19_once.py','root_manual_snapshot_m03.py','review_final_205_release.py','bind_m03_handshake_native_packet.py','materialize_s4_q4_static_inputs_once.py','m03_protection_normalization_contract.py']:
 newname='materialize_s6_q6_static_inputs_once.py' if oldname.startswith('materialize_') else oldname
 raw=(OS/oldname).read_text();mapping={str(OQ):str(Q),str(OS):str(S),'S4-Q4-SOURCE-SCAFFOLD-PROPOSAL.json':'S6-Q6-SOURCE-SCAFFOLD-PROPOSAL.json','S4-Q4-FINAL19-MATERIALIZED-PROPOSAL.json':'S6-Q6-FINAL19-MATERIALIZED-PROPOSAL.json'}
 out,n=literal_map(raw,mapping)
 if oldname=='bind_m03_handshake_native_packet.py':
  out=predicate(out,'exact accepted SDK whole decoder/physical tuple',"whole['schema']=='mckernel.independent-native-positive-physical-actual-two-witness-review.v1' and whole['status']=='PASS_SOURCE_AND_ACTUAL_WHOLE_CONSUMER_CHECKS_ONLY' and whole['decision']=='PASS_EXACT_CURRENT_POSITIVE_NATIVE_OWNER_PHYSICAL_CONSUMER_AND_TWO_WITNESS_CHECKS' and whole['genuine_current_physical']==ref(P) and whole['source']==decoderref")
  out=predicate(out,'complete exact reviewed current physical projection typed role',"load(proposal_ref['path'])['candidate_projection']==dict(path=decoderref['path'],sha256=decoderref['sha256'],size=decoderref['bytes'],mode=Path(decoderref['path']).stat().st_mode)")
 write(S/newname,out);ast.parse(out)
 if raw!=out:write(D/(newname+'.locator-kind.patch'),''.join(difflib.unified_diff(raw.splitlines(True),out.splitlines(True),fromfile=str(OS/oldname),tofile=str(S/newname))))
 changes.append(dict(source=typed(OS/oldname),candidate=typed(S/newname),exact_literal_changes=n,knownkind_predicate_changes=2 if oldname=='bind_m03_handshake_native_packet.py' else 0))
# Source hashes after locator correction; shared report contract body stays exact.
assert ref(S/'m03_protection_normalization_contract.py')['sha256']=='2a90a35fff7480997996547cd16ddef61ccab1928a806aa7c68f7557d0fb1953'
c=relocate(load(OQ/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.PENDING.json'))
binding=load(B/'ACTUAL-BINDING.json');pre=load(B/'ACTUAL-NATIVE-PREFLIGHT.json');norm=load(c['actual_preparation_acceptance']['path'])
rootowner=['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3',*pre['owner_argv'][1:]]
# All case/source/normalization roles retain their genuine current M03 tuple.
assert c['binding']==binding and c['runtime_source_hashes']==load(B/'ENTIRE-ACTIVE-TUPLE.PROPOSAL.json')['source_hashes']
c.update(physical_consumer_actual_acceptance=ref(ACCEPTANCE),physical_consumer_context=ref(POS/'NATIVE-POSITIVE-S5-PHYSICAL-CONTEXT.json'),physical_projection_source=ref(POS/'native_positive_s5_physical_projection.py'),latest_physical=ref(PHYSICAL),latest_exclusive_physical=ref(PHYSICAL),current_native_predecessor_contract=dict(status='PASS_PHYSICAL_RETIREMENT_ONLY',scope='M03_NATIVE_OWNER_PHYSICAL_RETIREMENT_ONLY',new_native_persistent_owned_record_files=0,ref=ref(PHYSICAL)),fetched_runtime_proof=None,source_only_adapter=ref(S/'root_manual_snapshot_m03.py'),final_guard=ref(S/'review_final_205_release.py'),root_owner_argv=rootowner,static_execution_review=None,snapshot=None,runtime_release=None,status='SOURCE_ONLY_S6_Q6_GENUINE_POSITIVE_S5_KIND_BOUND_FETCHED_SOURCE_PROOF_AND_FINAL_STATIC_NULL')
# Keep original runtime component refs, replace only the host-control physical
# and locator references. No runtime SOURCE_HASHES/container-mount expansion.
runtime_names=['native_diagnostic_runner.py','native_diagnostic_backend.py','qmp_capture.py','native_owner_binding.py','native_diagnostic_container_owner.py']
runtime=[ref(B/'runtime-source-1'/n) for n in runtime_names]+[ref(load(B/'SETTINGS.json')['evaluator']['path'])]
reader=Path(load(POS/'CHECK-INPUTS.json')['accepted_FD_reader']['path'])
c['runtime_source_refs']=runtime+[ref(POS/'native_positive_s5_physical_projection.py'),ref(POS/'NATIVE-POSITIVE-S5-PHYSICAL-CONTEXT.json'),ref(reader)]+[ref(p) for p in sorted(S.glob('*.py'))]
c['host_control_source_readonly_roots']=[str(S),str(POS),str(reader.parent)]
c['host_control_readonly_scope']='Canonical host-control source/read-only inventory only; actualruntime203pins/56containerreadonlyroots remain exact acceptedpreflight.'
js(Q/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.PENDING.json',c)
oldx=load(OQ/'FINAL-SEVEN-ROOT-CALL-DATA.json');x=relocate(oldx)
for key in ['execution_release','fixture_acceptance','final_execution_review','machine_base','non_temporal_index','non_temporal_inputs','final_config','snapshot_projection','fetched_proof']:x[key]=None
x.update(actual_binding=typed(B/'ACTUAL-BINDING.json'),actual_normalization=typed(B/'ACTUAL-NATIVE-PREFLIGHT.json'),actual_normalization_acceptance=c['actual_preparation_acceptance'],adapter_freeze=typed(B/'SOURCE-FREEZE.json'),final_physical=ref(PHYSICAL),exclusive_queue_predecessor=ref(PHYSICAL),current_native_predecessor_contract=c['current_native_predecessor_contract'],physical_consumer_context=c['physical_consumer_context'],prospective_attempt_parent=binding['attempt_parent'],prospective_manifest_path=binding['manifest']['path'],nonce=binding['nonce'],native_allowed_argv=rootowner,genuine_individual_source_components={n:ref(S/n) for n in ['machine_assembly_caller.py','review_final_205_release.py','root_manual_snapshot_m03.py']},status='SOURCE_ONLY_S6_Q6_LATEST_POSITIVE_S5_KIND_BOUND_NOT_EXECUTION',runtime_release=None,future_bindings=dict(LAST_snapshot=None,actual_machine=None,actual_guard=None),final_snapshot_minted=False,capture_parents=[])
r=x['steps'][0]['argv_template']
for flag in ['--bindings-sha256']:r[r.index(flag)+1]=None
r[r.index('--terminal')+1]=str(PHYSICAL);r[r.index('--terminal-sha256')+1]=ref(PHYSICAL)['sha256']
x['steps'][1]['argv_template'][-5:]=[str(Q/'machine-base.json'),None,str(Q/'root-live-preflight-1.json'),str(Q/'execution-release.json'),None]
r=x['steps'][2]['argv_template']
for flag in ['--config-sha256','--machine-sha256','--snapshot-sha256']:r[r.index(flag)+1]=None
x['steps'][3]['argv_template']=rootowner
captures=S/'capture-template-source';captures.mkdir(mode=0o700)
for r,oldr in zip(x['steps'],oldx['steps']):
 t=relocate(load(oldr['template']['path']));t['operations'][1]['argv_template']=r['argv_template']
 for key in ['stdout','stderr','status']:t['operations'][1][key+'_path']=r[key]
 t['release']=None;t['root_installed_release_path']=None
 target=captures/Path(oldr['template']['path']).name;js(target,t);r['template']=ref(target);r['preparation_status']='SOURCE_TEMPLATE_S6_CURRENT_POSITIVE_KIND_STATIC_DECISION_FETCHED_PROOF_NULL'
x['fresh_capture_and_actual_command_paths']=[p for r in x['steps'] for p in r['capture_outputs']+[r['materialized_command_data']]]
js(Q/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json',x)
manual=load(OQ/'MANUAL-READBACK-CONTRACT.json');js(Q/'MANUAL-READBACK-CONTRACT.json',manual)
command=dict(argv=['/home/holden/anaconda3/bin/python3.9','-I','-B',str(S/'bind_m03_handshake_native_packet.py'),c['actual_preparation_acceptance']['path'],c['actual_preparation_acceptance']['sha256'],str(PHYSICAL),ref(PHYSICAL)['sha256'],None,None]);js(S/'FINAL19-CHILD-COMMAND.PENDING.json',command)
fixed=['proposal.json','conditional-metadata.json','machine-base.json','non-temporal-freeze.json','ROOT-SNAPSHOT-BINDINGS.json','FINAL-NONTEMPORAL-DATA-INDEX.json','SNAPSHOT-STATIC-EQUALITY-AND-CAPPED-ARGV.json','FINAL-IHK-LOGGING-CHECK-CONFIG.json','FINAL-SEVEN-ROOT-CALL-DATA.json','root-execute-seven-1.py','ROOT-SEVEN-REVIEW-REF-1.json','NATIVE-COHERENT-REVIEW-PACKET.json']
outputs=[str(Q/n) for n in fixed]+[str(Q/'capture-templates'/Path(r['template']['path']).name) for r in x['steps']]
inputs={str(p) for p in S.rglob('*') if p.is_file()}|{str(p) for p in Q.rglob('*') if p.is_file()}|{r['path'] for r in c['runtime_source_refs']}|set(pre['consumed_paths'])|{str(PHYSICAL),str(ACCEPTANCE)}
prior=load(OLD/'FINAL19-WHOLE-CURRENT-DATA-PROPOSAL.json');prioroutputs=set(prior['final19_outputs'])|set(prior['fresh_capture_and_actual_command_paths'])
assert len(outputs)==len(set(outputs))==len(fixed)+len(x['steps']) and set(outputs).isdisjoint(inputs|prioroutputs)
assert len(x['fresh_capture_and_actual_command_paths'])==len(set(x['fresh_capture_and_actual_command_paths']))
for output in outputs+x['fresh_capture_and_actual_command_paths']:assert not os.path.lexists(output) and output not in inputs and output not in prioroutputs
assert len(binding['nonce'])==32 and pre['paths']['qmp_socket_bytes']<=107
# Validate active locators/typed roles as one whole DATA tuple; no source imports.
for row in c['runtime_source_refs']:assert ref(row['path'])==row
assert load(c['physical_consumer_actual_acceptance']['path'])['source']==c['physical_projection_source']
assert load(c['physical_consumer_actual_acceptance']['path'])['genuine_current_physical']==c['latest_physical']
assert load(load(c['physical_consumer_actual_acceptance']['path'])['reviewed_proposal']['path'])['candidate_projection']==typed(POS/'native_positive_s5_physical_projection.py')
js(D/'S6-Q6-SOURCE-SCAFFOLD-PROPOSAL.json',dict(schema='mckernel.M03-positive-S5-fresh-S6-Q6-source-DATA-proposal.v1',scope='Functional supported-profile OS/apps plus compute-C retirement into Rust/reviewed assembly; retained61B M03protectionapp with genuinepositiveS5 physicalpredecessor.',status='SOURCE_ONLY_S6_Q6_UNEXECUTED_REQUIRES_FINITE_SOURCE_REVIEW_PUBLICATION_FETCHED_PROOF',source_changes=changes,source_pins=[typed(p) for p in sorted({Path(x) for x in inputs}) if p.is_file()],actual_normalization_acceptance=c['actual_preparation_acceptance'],actual_positive_S5_physical=typed(PHYSICAL),actual_positive_S5_whole_consumer_acceptance=typed(ACCEPTANCE),positive_reader=typed(POS/'native_positive_s5_physical_projection.py'),positive_context=typed(POS/'NATIVE-POSITIVE-S5-PHYSICAL-CONTEXT.json'),source_input_paths=sorted(inputs),final19_outputs=outputs,fresh_capture_and_actual_command_paths=x['fresh_capture_and_actual_command_paths'],prior_output_paths=sorted(prioroutputs),all19_output_source_disjoint=True,all19_prior_outputs_disjoint=True,all19_absent=True,expected_output_count=len(outputs),capture_paths=len(x['fresh_capture_and_actual_command_paths']),seven_steps=len(x['steps']),nonce=binding['nonce'],all_AF_UNIX=pre['paths'],runtime_source_count=len(c['runtime_source_hashes']),runtime_readonly_root_count=len(c['readonly_roots']),host_control_source_readonly_roots=c['host_control_source_readonly_roots'],fetched_source_proof=None,materializer_source=typed(S/'materialize_s6_q6_static_inputs_once.py'),materializer_argv_template=['/home/holden/anaconda3/bin/python3.9','-I','-B',str(S/'materialize_s6_q6_static_inputs_once.py'),c['actual_preparation_acceptance']['path'],c['actual_preparation_acceptance']['sha256'],None,None],child_command_template=typed(S/'FINAL19-CHILD-COMMAND.PENDING.json'),seven_template=typed(Q/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json'),static_inputs_template=typed(Q/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.PENDING.json'),ordinary_source_wrapper=typed(S/'run_final19_once.py'),ordinary_profile='ExistingCPU6/AS1GiB/55CPU/52childwall/60+2outer/32MiBfiles/core0/nofile256 onlyafterfinitereview/rootgrant',saved_Q4_actual_whole_static_acceptance=typed(R/'ACTUAL-Q4-WHOLE-STATIC-CONTRACT-ACCEPTANCE.json'),original_Q4_source_and_outputs_untouched=True,source_oracle_or_runtime203_56_changes=False,root7_executor_generated_by_binder_only=True,future=dict(complete_source_publication_and_fetchedproof=None,independent_final19_decision=None,root_ordinary_grant=None,actual_final19_result=None,LAST_snapshot=None,actual_machine=None,actual_guard=None,runtime_release=None,native_acceptance=None),tests=0,ordinary_runs=0,root_operations=0,guest_runs=0))
js(D/'SOURCE-FREEZE.json',dict(schema='mckernel.M03-positive-S5-fresh-S6-Q6-source-freeze.v1',scope='FunctionalOS/apps plusRust/reviewedassembly compute cutover',status='SOURCE_ONLY_UNRUN_BYTESTABLE',files=[typed(p) for p in sorted(D.rglob('*')) if p.is_file() and p.name!='SOURCE-FREEZE.json'],proposal=typed(D/'S6-Q6-SOURCE-SCAFFOLD-PROPOSAL.json'),actual_positive_S5_physical=typed(PHYSICAL),actual_positive_whole_consumer_acceptance=typed(ACCEPTANCE),source_assertion='Only precise locator literals plus 2exactpositive2witnessconsumerrole predicates; unchanged runtime203/56/kernel/modules/app/ebd6/c6/61Boracle',fetched_source_proof=None,root_grant=None,tests=0,ordinary_runs=0,root_operations=0,guest_runs=0))
print(json.dumps(dict(freeze=typed(D/'SOURCE-FREEZE.json'),proposal=typed(D/'S6-Q6-SOURCE-SCAFFOLD-PROPOSAL.json'),source_files=len(list(S.glob('*.py'))),outputs=len(outputs),capture_paths=len(x['fresh_capture_and_actual_command_paths']),tests=0)))
