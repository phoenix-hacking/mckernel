"""Source authoring only; never import/run the candidate controls."""
import ast,copy,hashlib,json,os
from pathlib import Path
D=Path(__file__).resolve().parent;B=D.parent;H=B.parent
OLD=H/'phase5-exit7-grace-retry-binding-20261020-1';OS=OLD/'non-temporal-source-3';OQ=OLD/'native-control-packet-3'
S=D/'non-temporal-source-4';Q=D/'native-control-packet-4';S.mkdir(mode=0o700);Q.mkdir(mode=0o700)
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def typed(p):
 p=Path(p);r=ref(p);return dict(path=r['path'],sha256=r['sha256'],size=r['bytes'],mode=p.lstat().st_mode)
def load(p):return json.loads(Path(p).read_bytes())
def write(p,s):
 with p.open('x') as f:f.write(s)
 p.chmod(0o600)
def js(p,v):write(p,json.dumps(v,indent=2,sort_keys=True)+'\n')
def relocate(v):
 if isinstance(v,str):
  for old,new in [(OQ,Q),(OS,S)]:
   if v==str(old) or v.startswith(str(old)+'/'):return str(new)+v[len(str(old)):]
  return v
 if isinstance(v,list):return [relocate(x) for x in v]
 if isinstance(v,dict):return {k:relocate(x) for k,x in v.items()}
 return v
def span_edit(raw,changes):
 lines=raw.splitlines(True);offset=[0]
 for line in lines:offset.append(offset[-1]+len(line))
 for n,value in sorted(changes,key=lambda x:(x[0].lineno,x[0].col_offset),reverse=True):
  a=offset[n.lineno-1]+n.col_offset;b=offset[n.end_lineno-1]+n.end_col_offset;raw=raw[:a]+value+raw[b:]
 return raw
def literals(raw,mapping):
 t=ast.parse(raw);changes=[(n,repr(mapping[n.value])) for n in ast.walk(t) if isinstance(n,ast.Constant) and isinstance(n.value,str) and n.value in mapping]
 return span_edit(raw,changes),len(changes)
def predicate(raw,label,expression):
 tree=ast.parse(raw);nodes=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='need' and len(n.args)>=2 and isinstance(n.args[1],ast.Constant) and n.args[1].value==label]
 assert len(nodes)==1,label
 return span_edit(raw,[(nodes[0].args[0],expression)])
review=H/'phase5-m03-valid-protection-closure-independent-review-20261020-1/ACTUAL-PROTECTION-GRACE-NORMALIZATION-ACCEPTANCE.json';accept=load(review)
assert typed(review)['sha256']=='ebd6ddf1083953d7e601d7c39acbbcc1a3248be603517c41773302f2e41052a2'
pre=load(B/'ACTUAL-NATIVE-PREFLIGHT.json');binding=load(B/'ACTUAL-BINDING.json');settings=load(B/'SETTINGS.json');tuple_=load(B/'ENTIRE-ACTIVE-TUPLE.PROPOSAL.json')
manifest=load(binding['manifest']['path']);nonce=binding['nonce'];parent=binding['attempt_parent'];attempt=pre['paths']['attempt'];evidence=parent+'.owner-'+nonce
scope='Functional supported-profile OS/apps plus compute-C retirement into Rust/reviewed assembly; retained61B precise ROwritefault/unchangedbyte/RWrestore slice only.'
contract='''"""Exact known-kind M03 grace normalization contract; no effects or aliases.
Every consumer keeps the original report and complete authoritative descriptors.
This is an ordinary-preparation proof, never runtime or application authority.
"""
from pathlib import Path
import hashlib,json,os,stat
STABLE=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def read(row):
    assert type(row) is dict and set(row)=={'path','sha256','size','mode'}
    p=Path(row['path']);assert p.is_absolute() and p.resolve()==p
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    with os.fdopen(fd,'rb') as f:
        a=os.fstat(f.fileno());assert stat.S_ISREG(a.st_mode) and a.st_mode==row['mode'] and a.st_size==row['size'] and a.st_size<=4<<20
        raw=f.read((4<<20)+1);b=os.fstat(f.fileno());c=p.lstat()
        assert all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in STABLE)
    assert len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    return raw

def validate(row,stage_row=None):
    report=json.loads(read(row))
    assert report['schema']=='mckernel.independent-actual-m03-protection-grace-normalization-acceptance.v1'
    assert report['status']=='PASS' and report['decision']=='PASS_ACTUAL_M03_PROTECTION_GRACE_BYTE_EXACT_NORMALIZATION_AND_CLOSED_RETIREMENT'
    assert report['blocking_findings']==[] and report['normalization_acceptance'] is True
    assert report['native_acceptance'] is False and report['application_acceptance'] is False and report['runtime_release'] is None
    assert report['root_operations']==report['guest_runs']==0
    facts=report['facts']
    for k in ['normalized_manifest_byte_exact','parent_empty','attempt_absent','full_argv_exact','observer_and_retirement_errors_null','inner_direct_joined','inner_group_absent','outer_direct_joined','outer_group_absent','closed_streams','CPU6_released']:assert facts[k] is True,k
    assert facts['clocks_or_host_effects']==facts['inner_rc']==facts['outer_rc']==facts['stderr_bytes']==0
    assert facts['normalization_runs']==1
    pre=json.loads(read(report['actual_full_preflight']));binding=json.loads(read(report['actual_binding_result']))
    assert pre['binding']==binding==report['binding']
    assert binding['manifest']==report['actual_normalized_manifest']
    assert pre['parent_identity']==facts['parent_identity']==report['parent_identity']
    assert pre['parent_nine_field_identity']==facts['parent_nine_field_identity']==report['parent_nine_field_identity']
    assert pre['clocks_or_host_effects']==pre['guest_runs']==pre['root_operations']==0
    assert pre['latest_exclusive_predecessor'] is None and pre['snapshot'] is None and pre['runtime_release'] is None
    assert pre['accepted_stage']==report['actual_stage_acceptance']
    assert len(pre['consumed_paths'])==facts['consumed_paths'] and len(pre['readonly_roots'])==facts['readonly_roots']
    for k,v in facts['actual_full_argv_counts'].items():assert len(pre[k])==v
    stage_row=report['actual_stage_acceptance'] if stage_row is None else stage_row
    assert stage_row==report['actual_stage_acceptance']
    stage=json.loads(read(stage_row))
    assert stage['schema']=='mckernel.independent-actual-m03-protection-grace-init-only-stage-acceptance.v1'
    assert stage['status']=='PASS' and stage['decision']=='PASS_ACTUAL_M03_PROTECTION_GRACE_INIT_ONLY_OFFLINE_STAGE'
    assert stage['stage_kind']=='M03_GRACE_INIT_ONLY_OFFLINE_STAGE' and stage['blocking_findings']==[]
    assert stage['native_acceptance'] is False and stage['normalization_acceptance'] is False and stage['runtime_release'] is None and stage['guest_runs']==stage['root_operations']==0
    assert read(stage['stage_manifest'])==read(report['actual_normalized_manifest'])
    result=json.loads(read(stage['stage_result']))
    assert result['status']=='M03_GRACE_INIT_ONLY_OFFLINE_STAGE' and result['manifest']==stage['stage_manifest']
    assert result['permitted_final_changes']==['init'] and result['accepted_original_archive_prefix_unchanged'] is True and result['app_unchanged'] is True
    assert result['native_acceptance'] is False and result['runtime_release'] is None and result['guest_runs']==0
    return dict(report=report,preflight=pre,binding=binding,facts=facts,stage=stage,report_ref=row,stage_ref=stage_row)
'''
write(S/'m03_protection_normalization_contract.py',contract)
# Explicit source-local known-kind import, independent of Python sys.path/-I.
bootstrap="\ndef m03_contract():\n import importlib.util\n p=Path(__file__).resolve().parent/'m03_protection_normalization_contract.py'\n spec=importlib.util.spec_from_file_location('exact_m03_protection_contract',p)\n m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m\n"
normal_schema='mckernel.independent-actual-m03-protection-grace-normalization-acceptance.v1';normal_decision='PASS_ACTUAL_M03_PROTECTION_GRACE_BYTE_EXACT_NORMALIZATION_AND_CLOSED_RETIREMENT';stage_schema='mckernel.independent-actual-m03-protection-grace-init-only-stage-acceptance.v1';stage_decision='PASS_ACTUAL_M03_PROTECTION_GRACE_INIT_ONLY_OFFLINE_STAGE'
changes=[]
for name in ['machine_assembly_caller.py','run_final19_once.py','root_manual_snapshot_m03.py','review_final_205_release.py','bind_m03_handshake_native_packet.py']:
 raw=(OS/name).read_text();mapping={str(OQ):str(Q),'startup.nonzero-dualstream.rust.exit7':manifest['case_id'],'mckernel.independent-actual-exit7-native-preparation-acceptance.v1':normal_schema,'PASS_ACTUAL_EXIT7_BYTE_EXACT_NORMALIZATION_FRESH_PARENT_AND_FULL_OWNER_CREATE_INSIDE_QEMU_ARGV_ONLY':normal_decision,'mckernel.independent-actual-exit7-app-only-offline-stage-acceptance.v1':stage_schema,'PASS_ACTUAL_EXIT7_LITERAL_BINDING_AND_APP_ONLY_OFFLINE_STAGE':stage_decision,'actual exit7 app-only stage ancestry':'actual M03 grace init-only stage ancestry','whole73B oracle/exit/stderr unchanged':'whole retained61B oracle/exit/stderr unchanged','P-M02-02':'P-M03-01','Functional OS/apps plus Rust cutover; selected P-M02-02 Rust app with exact24B stdout/24B stderr/raw1792/exit7 and normal retirement; no automatic whole criterion/default/fork/ACK credit':scope,'Reuse accepted finite19/seven-row49 mapping/caller/executor and live-resource/mutex checks; one Rust exit7 app only':'Reuse accepted finite19/seven-row49 mapping/caller/executor and live-resource/mutex checks; one retained61B valid-protection app only','Exact24B stdout/24B stderr/raw1792/exit7; full genuine current stage/normalization/source tuples required':'Exact61B stdout/empty stderr/exit0; precise ROwritefault/unchangedbyte/RWrestore and full genuine current stage/normalization/source tuples required','Selected P-M02-02 Rust nonzero dualstream observation on exact tested205/HOST66 tuple: exact24B stdout/24B stderr/raw1792/exit7 and normal retirement; no automatic whole criterion/default/ACK/compute-C retirement credit.':scope,'PASS_ONE_EXACT_EXIT7_OWNER_AND_THREE_SUCCESS_ONLY_READBACKS':'PASS_ONE_EXACT_M03_PROTECTION_OWNER_AND_THREE_SUCCESS_ONLY_READBACKS'}
 raw,count=literals(raw,mapping)
 if name in ['root_manual_snapshot_m03.py','review_final_205_release.py','bind_m03_handshake_native_packet.py']:
  # Insert helper before the first function definition; all relative source
  # locators resolve to this fresh S4 directory.
  at=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)).lineno-1
  lines=raw.splitlines(True);lines[at:at]=[bootstrap];raw=''.join(lines)
 if name=='root_manual_snapshot_m03.py':
  anchor="    c=checked(b['mandatory_consumer_review']);s=checked(b['stage_review'])\n"
  assert raw.count(anchor)==1;raw=raw.replace(anchor,anchor+"    m03_contract().validate(b['mandatory_consumer_review'],b['stage_review'])\n")
  raw=predicate(raw,'preparation only, no native substitution',"c['status']=='PASS' and c['normalization_acceptance'] is True and c['native_acceptance'] is False and c['application_acceptance'] is False and c['runtime_release'] is None and c['root_operations']==c['guest_runs']==0")
  raw=predicate(raw,'closed ordinary preparation only',"c['guest_runs']==0 and c['root_operations']==0 and facts['clocks_or_host_effects']==0 and facts['inner_direct_joined'] is True and facts['inner_group_absent'] is True")
 if name=='bind_m03_handshake_native_packet.py':
  # Preserve exact authoritative four-field actual report references everywhere.
  tree=ast.parse(raw);nodes=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='ref' and len(n.args)==1 and isinstance(n.args[0],ast.Name) and n.args[0].id=='A']
  raw=span_edit(raw,[(n,'typed_ref(A)') for n in nodes])
  anchor="def load(p):return json.loads(Path(p).read_bytes())\n";assert raw.count(anchor)==1
  raw=raw.replace(anchor,anchor+"def typed_ref(p):\n p=Path(p);r=ref(p);return dict(path=r['path'],sha256=r['sha256'],size=r['bytes'],mode=p.lstat().st_mode)\n")
  anchor="c=load(I/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.json');accept=load(A)\n";assert raw.count(anchor)==1;raw=raw.replace(anchor,anchor+"m03_contract().validate(typed_ref(A),c['actual_stage_acceptance'])\n")
  # c6 stage acceptance is the stage role; ebd6 is actual typed composition.
  tree=ast.parse(raw);nodes=[]
  for n in ast.walk(tree):
   if isinstance(n,ast.keyword) and n.arg=='stage_acceptance' and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='typed_ref':nodes.append(n.value)
  assert len(nodes)==1;raw=span_edit(raw,[(nodes[0],"c['actual_stage_acceptance']")])
  # Inherited fixed24 stdout summary becomes exact current oracle byte count.
  raw=predicate(raw,'actual stage decision bytes',"ref(A)['sha256']==sys.argv[2]")
  tree=ast.parse(raw);nodes=[n.value for n in ast.walk(tree) if isinstance(n,ast.keyword) and n.arg=='oracles_stdout_bytes']
  assert len(nodes)==1;raw=span_edit(raw,[(nodes[0],"[len(bytes.fromhex(c['strict_oracle']['stdout_hex']))]")])
 if name=='review_final_205_release.py':
  anchor=" need(cfg['schema']==SCHEMA and cfg['status']==STATUS,'approved fixed case config')\n";assert raw.count(anchor)==1;raw=raw.replace(anchor,anchor+" m03_contract().validate(cfg['actual_typed_composition'],cfg['stage_acceptance'])\n")
 write(S/name,raw);ast.parse(raw);changes.append(dict(source=ref(OS/name),candidate=ref(S/name),literal_edits=count,kind='Precise AST case/path literals and exact known-kind contract/facts roles; inherited control algorithm retained'))
# The seven static rows are the accepted algorithm, rebound only as DATA.
x=relocate(load(OQ/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json'));oldx=load(OQ/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json');oldnonce=oldx['nonce'];oldparent=oldx['prospective_attempt_parent'];oldattempt=oldparent+'/attempt-'+oldnonce;oldevidence=oldparent+'.owner-'+oldnonce
rootowner=['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3',*pre['owner_argv'][1:]]
for row in x['steps']:
 for i,arg in enumerate(row['argv_template']):
  if arg=='--directory='+oldevidence:row['argv_template'][i]='--directory='+evidence
  elif arg==oldattempt+'/result.json':row['argv_template'][i]=attempt+'/result.json'
  elif arg=='--directory='+oldattempt:row['argv_template'][i]='--directory='+attempt
x['steps'][3]['argv_template']=rootowner
captures=S/'capture-template-source';captures.mkdir(mode=0o700)
for row,oldrow in zip(x['steps'],oldx['steps']):
 template=relocate(load(oldrow['template']['path']));template['operations'][1]['argv_template']=row['argv_template']
 for k in ['stdout','stderr','status']:template['operations'][1][k+'_path']=row[k]
 template['release']=None;template['root_installed_release_path']=None
 p=captures/Path(oldrow['template']['path']).name;js(p,template);row['template']=ref(p)
x.update(actual_binding=typed(B/'ACTUAL-BINDING.json'),actual_normalization=typed(B/'ACTUAL-NATIVE-PREFLIGHT.json'),actual_normalization_acceptance=typed(review),adapter_freeze=typed(B/'SOURCE-FREEZE.json'),prospective_attempt_parent=parent,prospective_manifest_path=binding['manifest']['path'],nonce=nonce,native_allowed_argv=rootowner,genuine_individual_source_components={n:ref(S/n) for n in ['machine_assembly_caller.py','review_final_205_release.py','root_manual_snapshot_m03.py']},runtime_release=None,status='SOURCE_ONLY_M03_ACTUAL_PREPARATION_BOUND_FETCHED_PROOF_STATIC_DECISION_NULL',future_bindings=dict(LAST_snapshot=None,actual_machine=None,actual_guard=None))
x['fresh_capture_and_actual_command_paths']=[p for r in x['steps'] for p in r['capture_outputs']+[r['materialized_command_data']]]
js(Q/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json',x)
manual=load(OQ/'MANUAL-READBACK-CONTRACT.json');manual.update(attempt=attempt,owner_evidence=evidence,strict_oracle=manifest['payload']['oracle']);js(Q/'MANUAL-READBACK-CONTRACT.json',manual)
c=relocate(load(OQ/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.PENDING.json'))
runtime=[ref(B/'runtime-source-1'/n) for n in ['native_diagnostic_runner.py','native_diagnostic_backend.py','qmp_capture.py','native_owner_binding.py','native_diagnostic_container_owner.py']]+[ref(settings['evaluator']['path'])]
c.update(actual_binding_result=typed(B/'ACTUAL-BINDING.json'),actual_full_preflight=typed(B/'ACTUAL-NATIVE-PREFLIGHT.json'),actual_preparation_acceptance=typed(review),binding=binding,normalized_manifest=binding['manifest'],whole_manifest=manifest,stage_manifest=accept['actual_stage_acceptance'] and settings['late_fields']['source_manifest'],actual_stage_acceptance=accept['actual_stage_acceptance'],runtime_owner=ref(B/'runtime-source-1/native_diagnostic_container_owner.py'),runtime_runner=ref(B/'runtime-source-1/native_diagnostic_runner.py'),runtime_observer=ref(settings['evaluator']['path']),runtime_source_refs=runtime+[c['physical_projection_source'],c['physical_consumer_context']]+[ref(S/n) for n in ['machine_assembly_caller.py','root_manual_snapshot_m03.py','review_final_205_release.py','m03_protection_normalization_contract.py']],runtime_source_hashes=tuple_['source_hashes'],whole_boundary_freeze=typed(B/'SOURCE-FREEZE.json'),fetched_runtime_proof=None,parent_identity=pre['parent_identity'],parent_nine_field_identity=pre['parent_nine_field_identity'],consumed_paths=pre['consumed_paths'],readonly_roots=pre['readonly_roots'],strict_oracle=manifest['payload']['oracle'],accepted_owner_argv=pre['owner_argv'],root_owner_argv=rootowner,qemu_argv=pre['qemu_argv'],inside_argv=pre['inside_owner_argv'],container_create_argv=pre['container_create_argv'],AF_UNIX=pre['paths'],source_only_adapter=ref(S/'root_manual_snapshot_m03.py'),final_guard=ref(S/'review_final_205_release.py'),static_execution_review=None,snapshot=None,runtime_release=None,status='SOURCE_ONLY_CURRENT_M03_ACTUAL_REVIEWS_BOUND_FETCHED_PROOF_STATIC_DECISION_NULL',scope=scope)
js(Q/'STATIC-M03-NONTEMPORAL-INPUTS.SCHEMA-CORRECTED.PENDING.json',c)
command=dict(argv=['/home/holden/anaconda3/bin/python3.9','-I','-B',str(S/'bind_m03_handshake_native_packet.py'),str(review),typed(review)['sha256'],x['final_physical']['path'],x['final_physical']['sha256'],None,None]);js(S/'FINAL19-CHILD-COMMAND.PENDING.json',command)
fixed=['proposal.json','conditional-metadata.json','machine-base.json','non-temporal-freeze.json','ROOT-SNAPSHOT-BINDINGS.json','FINAL-NONTEMPORAL-DATA-INDEX.json','SNAPSHOT-STATIC-EQUALITY-AND-CAPPED-ARGV.json','FINAL-IHK-LOGGING-CHECK-CONFIG.json','FINAL-SEVEN-ROOT-CALL-DATA.json','root-execute-seven-1.py','ROOT-SEVEN-REVIEW-REF-1.json','NATIVE-COHERENT-REVIEW-PACKET.json'];outputs=[str(Q/n) for n in fixed]+[str(Q/'capture-templates'/Path(r['template']['path']).name) for r in x['steps']]
source_paths={str(p) for p in S.rglob('*') if p.is_file()}|{str(p) for p in Q.rglob('*') if p.is_file()}|{r['path'] for r in c['runtime_source_refs']}|set(pre['consumed_paths'])|{str(review)}
prioroutputs=set(load(OLD/'S3-Q3-SOURCE-SCAFFOLD-PROPOSAL.json')['final19_outputs'])|set(oldx['fresh_capture_and_actual_command_paths'])
assert len(outputs)==len(set(outputs))==len(fixed)+len(x['steps']) and set(outputs).isdisjoint(source_paths|prioroutputs)
assert len(x['fresh_capture_and_actual_command_paths'])==len(set(x['fresh_capture_and_actual_command_paths']))
for p in outputs+x['fresh_capture_and_actual_command_paths']:assert not os.path.lexists(p) and p not in source_paths and p not in prioroutputs
assert len(nonce)==32 and all(v in '0123456789abcdef' for v in nonce) and pre['paths']['qmp_socket_bytes']<=107
js(D/'S4-Q4-SOURCE-SCAFFOLD.PARTIAL.json',dict(status='SOURCE_AUTHORING_IN_PROGRESS_NOT_RELEASED',scope=scope,source_changes=changes,actual_normalization_acceptance=typed(review),source_tuple=typed(B/'ENTIRE-ACTIVE-TUPLE.PROPOSAL.json'),final19_outputs=outputs,source_input_paths=sorted(source_paths),prior_output_paths=sorted(prioroutputs),all_output_source_disjoint=True,all_prior_outputs_disjoint=True,all_outputs_absent=True,nonce=nonce,QMP=pre['paths'],fetched_source_proof=None,static_decision=None,root_grant=None,runtime_release=None,tests=0,ordinary_runs=0,guest_runs=0))
print(json.dumps(dict(status='SOURCE_CONTROLS_AND_DATA_AUTHORED_NOT_FROZEN',sources=len(list(S.glob('*.py'))),output_count=len(outputs),capture_paths=len(x['fresh_capture_and_actual_command_paths']),guest_runs=0)))
