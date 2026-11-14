"""One current NUMA-case derivative of the accepted finite nineteen-output binder.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No snapshot, owner, backend, compiler, socket, root or workload invocation.
"""
from pathlib import Path
import ast,copy,hashlib,json,os,stat,sys,importlib.util
D=Path(__file__).resolve().parent;Q=D/'native-packet-1';N=D;I=D
OLD=Path('/home/holden/mckernel-work/host-preparation/current-v6-composite-native-probe-20261020-1/host66-probe-1/stage-preparation-1');OQ=OLD/'native-packet-1';OR=OQ
H=Path('/home/holden/mckernel-work/host-preparation')
def load(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def need(v,s):
 if not v:raise ValueError(s)

def derive_current_readbacks(binding,pre):
 """Host readback operands follow the actual owner's accepted parent/nonce."""
 parent=Path(binding['attempt_parent']);nonce=binding['nonce']
 argv=pre['root_owner_argv']
 need(argv[argv.index('--attempt-parent')+1]==str(parent) and argv[argv.index('--nonce')+1]==nonce,'actual owner parent/nonce for host readbacks')
 need(argv[argv.index('--manifest')+1]==binding['manifest']['path'] and argv[argv.index('--manifest-sha256')+1]==binding['manifest']['sha256'],'actual owner manifest for host readbacks')
 need(pre['binding']['nonce']==nonce and pre['binding']['attempt_parent']==str(parent),'actual preflight binding parent/nonce')
 attempt=parent/('attempt-'+nonce);evidence=parent.with_name(parent.name+'.owner-'+nonce)
 need(str(attempt)==pre['paths']['attempt'] and str(attempt/'qmp.sock')==pre['paths']['qmp_socket'],'actual owner attempt/QMP path')
 return [['/usr/bin/sudo','-A','/usr/bin/tar','--create','--file=-','--directory='+str(evidence),'.'],
         ['/usr/bin/sudo','-A','/usr/bin/cat',str(attempt/'result.json')],
         ['/usr/bin/sudo','-A','/usr/bin/tar','--create','--file=-','--directory='+str(attempt),'--exclude=./qmp.sock','.']]

def validate_current_path_join(outputs,root,binding,pre):
 """Whole generated owner/meta/config/seven-row/template/output/hash boundary."""
 root=Path(root);packet=root/'native-packet-1'
 def data(path):return json.loads(outputs[Path(path)])
 raw=derive_current_readbacks(binding,pre)
 parent=Path(binding['attempt_parent']);nonce=binding['nonce'];attempt=parent/('attempt-'+nonce);evidence=parent.with_name(parent.name+'.owner-'+nonce)
 prop=data(packet/'proposal.json');meta=data(packet/'conditional-metadata.json');cfg=data(packet/'FINAL-IHK-LOGGING-CHECK-CONFIG.json');seven=data(packet/'FINAL-SEVEN-ROOT-CALL-DATA.json')
 need(prop['parent']['path']==str(parent) and prop['nonce']==nonce and prop['argv']==pre['root_owner_argv'],'whole current proposal/owner join')
 need(meta['postjoin_readback']['argv']==raw,'whole current host readback operands')
 need(cfg['postjoin_readback']==meta['postjoin_readback'] and cfg['launch_argv']==pre['root_owner_argv'],'whole current config/readback/owner join')
 need(cfg['parent']==prop['parent'] and cfg['attempt']==str(attempt) and cfg['owner_evidence']==str(evidence),'whole current config owner output derivation')
 need(seven['native_allowed_argv']==pre['root_owner_argv'],'whole current seven owner command')
 rows=seven['steps'];names=['LAST-snapshot','machine-assembly','final-guard','native-owner','readback-1','readback-2','readback-3']
 need(len(rows)==7 and [r['name'] for r in rows]==names and rows[3]['argv_template']==pre['root_owner_argv'],'whole current seven row order/owner')
 for row,expected in zip(rows[4:],raw):
  argv=row['argv_template'];program='/usr/bin/tar' if '/usr/bin/tar' in expected else '/usr/bin/cat';at=argv.index(program)
  need(argv[:2]==expected[:2] and argv[at:]==expected[2:],'whole current wrapped host readback argv '+row['name'])
 need(seven['snapshot_output']==str(root/'root-live-preflight-1.json') and seven['final_machine_output']==str(packet/'execution-release.json') and seven['final_guard_output']==str(packet/'FINAL-205-MATCHED-SDK-NATIVE-MACHINE-REVIEW.json'),'whole current late output paths')
 need(cfg['snapshot_path']==seven['snapshot_output'] and cfg['machine_path']==seven['final_machine_output'],'whole config late output paths')
 actual=[]
 for index,row in enumerate(rows):
  name=row['name'];base=packet if index==0 else packet/'captures'/('%02d-'%index+name)
  expected_paths=[str(base/('snapshot.'+v if index==0 else v)) for v in ['stdout','stderr','status.json']]
  if index==0:expected_paths[2]=str(packet/'snapshot.status.json')
  need([row[k] for k in ['stdout','stderr','status']]==expected_paths,'whole current capture locator '+name)
  expected_capture=expected_paths+[row['status']+v for v in ['.command.json','.child.json','.direct-join.json']]
  need(row['capture_outputs']==expected_capture,'whole current six capture paths '+name)
  material=str(packet/'actual-command-data'/('%02d-'%index+name+'.json'))
  need(row['materialized_command_data']==material,'whole current command data locator '+name)
  need(row['caller_argv_template'][3]==str(packet/'root-run-exact-readonly-stage.py') and row['caller_argv_template'][row['caller_argv_template'].index('--commands-file')+1]==material and row['caller_argv_template'][row['caller_argv_template'].index('--commands-sha256')+1] is None,'whole current caller command binding '+name)
  template=data(row['template']['path']);op=template['operations'][1]
  need(op['argv_template']==row['argv_template'] and [op[k+'_path'] for k in ['stdout','stderr','status']]==expected_paths,'whole current capture template join '+name)
  actual.extend(expected_capture+[material])
 need(seven['fresh_capture_and_actual_command_paths']==actual and len(actual)==len(set(actual))==49,'whole current49 fresh output paths')
 need(len(outputs)==19 and len(set(outputs))==19 and not (set(map(str,outputs))&set(actual)),'whole current19 control/49 effect path disjointness')
 def walk(value):
  if isinstance(value,dict):
   if {'path','sha256','bytes'}<=set(value) and value['path'] is not None and Path(value['path']) in outputs:
    b=outputs[Path(value['path'])];need(value['sha256']==hashlib.sha256(b).hexdigest() and value['bytes']==len(b),'whole generated descriptor hash/bytes '+value['path'])
   for v in value.values():walk(v)
  elif isinstance(value,list):
   for v in value:walk(v)
 for path,b in outputs.items():
  if path.suffix=='.json':walk(json.loads(b))
 return raw
c=load(D/'STATIC-NONTEMPORAL-INPUTS.json')
need(len(sys.argv) in (1,3),'usage: bind_numa_native_packet.py [GENUINE_STATIC_DECISION SHA256]')
final=len(sys.argv)==3
if final:
 static=ref(sys.argv[1]);need(static['sha256']==sys.argv[2],'actual independent source/data review hash')
else:static=dict(path=None,sha256=None,bytes=None)
A=Path(c['actual_preparation_acceptance']['path']);need(ref(A)==c['actual_preparation_acceptance'],'actual accepted normalization bytes');accept=load(A)
need(c['actual_preparation_acceptance']['sha256']=='d7e94bbc4ceae6e5b04213e3beae0c221b2ee850150246ed9b6199a2b71063bb' and accept['schema']=='mckernel.numa-native-app.actual-normalization-review.v1' and accept['status']=='PASS_ACTUAL_NORMALIZATION_PARENT_AND_NO_EFFECT_ARGV_ONLY' and accept['implementation_ownership'] is False and accept['runtime_release'] is False and accept['reviewer'],'current accepted no-effect NUMA preparation')
pre=load(c['actual_full_preflight']['path']);binding=load(c['actual_binding_result']['path'])
need(ref(c['actual_full_preflight']['path'])==c['actual_full_preflight'] and ref(c['actual_binding_result']['path'])==c['actual_binding_result'],'full actual preflight and binding')
need(set(accept['normalized_manifest'])=={'path','sha256','size','mode'},'actual typed normalized manifest descriptor')
accepted_manifest=dict(accept['normalized_manifest'])
need(binding['manifest']==accepted_manifest==c['normalized_manifest'],'actual normalized manifest typed references')
for key,current in [('preflight',c['actual_full_preflight']),('binding',c['actual_binding_result'])]:
 typed=accept[key];need(set(typed)=={'path','sha256','size','mode'},'actual typed '+key+' descriptor')
 need(current==dict(path=typed['path'],sha256=typed['sha256'],bytes=typed['size']) and ref(typed['path'])==current and Path(typed['path']).stat().st_mode==typed['mode'],'actual complete typed '+key+' reference')
nonce=binding['nonce'];parent=Path(binding['attempt_parent']);attempt=parent/('attempt-'+nonce);evidence=Path(str(parent)+'.owner-'+nonce);stage=Path(c['stage_manifest']['path']).parent
facts=dict(parent_identity=pre['parent_identity'],parent_nine_field_identity=pre['parent_nine_field_identity'])
consumer=dict(normalized_manifest=binding['manifest'])
pre=dict(pre,owner_argv=pre['root_owner_argv'],inside_argv=pre['inside_owner_argv'],AF_UNIX_endpoints=[dict(option='-qmp',path=pre['paths']['qmp_socket'],encoded_bytes=pre['paths']['qmp_socket_bytes'])])
oldsettings=load(OLD/'variant-settings.json');oldprop=load(OQ/'proposal.json')
replacements={str(OQ):str(Q),str(OLD):str(D),'h66rx-261020-1':str(parent.parent.name),'h66rm-261020-1':str(Path(binding['manifest']['path']).parent.name),oldsettings['nonce']:nonce}
def subst(s):
 for a,b in replacements.items():s=s.replace(a,b)
 return s
def transform(v):
 if isinstance(v,str):return subst(v)
 if isinstance(v,list):return [transform(x) for x in v]
 if isinstance(v,dict):return {k:transform(x) for k,x in v.items()}
 return v
outputs={}
def add(path,v):
 b=(json.dumps(v,indent=2,sort_keys=True)+'\n').encode();outputs[Path(path)]=b;return dict(path=str(path),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def add_source(path,s):outputs[Path(path)]=s.encode();return dict(path=str(path),sha256=hashlib.sha256(s.encode()).hexdigest(),bytes=len(s.encode()))
owner=Path(c['runtime_owner']['path']);runtime=c['runtime_source_hashes']
s=parent.stat();five=dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)));full=dict(path=str(parent),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)),nlink=s.st_nlink,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
need(five==facts['parent_identity']==pre['parent_identity'] and not list(parent.iterdir()),'actual exact empty parent')
need(all(facts['parent_nine_field_identity'][k]==getattr(s,k) for k in facts['parent_nine_field_identity']),'actual full nine-field parent unchanged')
need(type(c['latest_physical']) is dict and type(c['physical_consumer_mapping']) is dict and type(c['physical_consumer_mapping_schema']) is str,'PENDING genuine current cleanup report/decoder/mapping; no predecessor alias permitted')
P=Path(c['latest_physical']['path']);need(ref(P)==c['latest_physical'],'genuine current full physical report')
physical=load(P);physical_pending=False
def physical_ref():return ref(P)
decoderref=load(D/'CURRENT-PHYSICAL-DECODER-SOURCE.json');need(type(decoderref) is dict and ref(decoderref['path'])==decoderref,'genuine compatible accepted physical projector source remains unresolved')
whole_ref=load(D/'CURRENT-PHYSICAL-COMPANION-ACCEPTANCE.json');need(type(whole_ref) is dict and ref(whole_ref['path'])==whole_ref==c['physical_consumer_mapping'],'genuine current physical mapping descriptor');need(load(whole_ref['path'])['schema']==c['physical_consumer_mapping_schema'],'explicit current mapping kind; no claimed future actual whole-body acceptance')
spec=importlib.util.spec_from_file_location('exact_current_threads_physical',decoderref['path']);decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
predecessor=decoder.project(physical,ref(P));need(set(predecessor)=={'boot_id','filesystem_uuid','container_id','owner_nonce','lease_path','common_exclusion','shared_heavy'},'existing seven-field snapshot interface')
need(all(not os.path.lexists(predecessor[k]) for k in ['lease_path','common_exclusion','shared_heavy']),'current retired predecessor records absent')
prop=transform(load(OQ/'proposal.json'));prop.update(actual_full_argument_preflight=c['actual_full_preflight'],actual_ordinary_acceptance=ref(A),actual_stage_review=ref(A),actual_owner_sha256=ref(owner)['sha256'],argv=pre['owner_argv'],effective_current_controller_stop_percent=100,latest_exclusive_operation_physical_predecessor=physical_ref(),normalized_manifest=consumer['normalized_manifest'],parent=dict(path=str(parent),identity=five),parent_full_ninefield_identity=full,stage_manifest=ref(stage/'manifest.json'),scope='One unchanged NUMA interval consumer; strict116B stdout/empty stderr/exit37 and complete lifecycle; no native/default/ACK/C-retirement credit',status='PENDING_LAST_SNAPSHOT_AND_FINAL_MACHINE')
prop.pop('pair_rounds',None);prop.pop('native_throughput_measurement',None);prop.pop('strict_startup_CPU_unchanged',None)
prop.update(profile=c['native_profile'],payload_contract=c['payload_contract'],component_ABI=c['tested_tuple_authority'],component_artifact=c['matched_module_artifact_authority'],criterion='current-native-numa-interval',expected_apps_if_native_passes=1,oracles_stdout_bytes=[116],strict_oracle=c['strict_oracle'],scope='Functional OS/apps plus Rust cutover; current selected NUMA interval app with exact116B stdout/empty stderr/exit37 and unchanged full lifecycle; no automatic native/default/ACK/C-retirement credit',new_throughput_or_behavior_credit=False)
prop['stage_manifest']=c['stage_manifest']
pref=add(Q/'proposal.json',prop)
meta=transform(load(OQ/'conditional-metadata.json'));meta.update(accepted_stage_manifest=prop['stage_manifest'],actual_metadata_review=ref(A),effective_current_controller_stop_percent=100,independent_static_execution_decision=static,normalized_manifest=prop['normalized_manifest'],parent_full_ninefield_identity=full,parent_identity=five,proposal=pref)
meta['postjoin_readback']=dict(meta['postjoin_readback'],argv=derive_current_readbacks(binding,pre))
meta['status']='PASS_NONTEMPORAL_DATA_ONLY' if final else 'PENDING_INDEPENDENT_STATIC_DATA_REVIEW'
mref=add(Q/'conditional-metadata.json',meta)
base=transform(load(OQ/'machine-base.json'));base.update(accepted_actual_stage_fixture_parent_review=ref(A),conditional_metadata_release=mref,exclusive_queue_predecessor=physical_ref(),independent_static_execution_decision=static,parent_identity=five,terminal_cleanup_and_common_shared_release=dict(status='PASS',ref=physical_ref()))
baseref=add(Q/'machine-base.json',base)
freeze=transform(load(OQ/'non-temporal-freeze.json'));freeze.update(actual_consumer_result=c['actual_binding_result'],actual_mandatory_consumer_review=ref(A),actual_preflight=c['actual_full_preflight'],actual_stage_review=ref(A),conditional_metadata=mref,current_snapshot_producer=ref(D/'root_manual_snapshot_threads.py'),effective_current_controller_stop_percent=100,independent_static_execution_decision=static,latest_exclusive_operation_physical_predecessor=physical_ref(),latest_predecessor_note='Genuine latest exclusive physical release; historical tested HOST66 tuple remains separate' ,machine_base=baseref,native_manifest=prop['normalized_manifest'],native_target=None,owner_argv=pre['owner_argv'],inside_argv=pre['inside_argv'],qemu_argv=pre['qemu_argv'],AF_UNIX_endpoints=pre['AF_UNIX_endpoints'],parent_full_ninefield_identity=full,parent_legacy_fivefield_identity=five,proposal=pref,readonly_roots=pre['readonly_roots'],runtime_owner=ref(owner),runtime_runner=c['runtime_runner'],runtime_observer=c['runtime_observer'],runtime_source_hashes=runtime,runtime_source_count=len(runtime),entire_consumed_paths=pre['consumed_paths'],consumed_path_count=len(pre['consumed_paths']),stage_native_manifest=prop['stage_manifest'])
freeze['diagnostic_extra_capture_growth_bytes']=8388608
freeze['status']='PASS_ACTUAL_STATIC_DATA_ONLY_PENDING_LAST_SNAPSHOT' if final else 'PENDING_INDEPENDENT_STATIC_DATA_REVIEW'
fref=add(Q/'non-temporal-freeze.json',freeze)
b=transform(load(OLD/'fresh-snapshot-bindings.json'));b.update(conditional_metadata=mref,effective_current_controller_stop_percent=100,entire_consumed_paths=pre['consumed_paths'],machine_pending=baseref,mandatory_consumer_review=ref(A),manifest=prop['normalized_manifest'],non_temporal_freeze=fref,parent_full_identity=full,parent_identity=five,parent_review_identity=facts['parent_nine_field_identity'],physical_predecessor=predecessor,physical_review=physical_ref(),runtime_source_hashes=runtime,crate_request=None,stage_review=ref(A),static_review=static,qemu_argv=pre['qemu_argv'],inside_argv=pre['inside_argv'])
scratch=Path('/home/holden/mckernel-work/scratch').stat();b['scratch_identity']=[scratch.st_dev,scratch.st_ino]
b.pop('crate_request');b.pop('sdk_request',None)
b.update(repaired_image_sha256=c['image_sha256'],payload_contract=c['payload_contract'],runtime_owner=c['runtime_owner'],physical_projection_source=decoderref,strict_oracle=c['strict_oracle'],accepted_owner_argv=c['accepted_owner_argv'],root_owner_argv=c['root_owner_argv'],mandatory_consumer_review=c['actual_preparation_acceptance'],stage_review=c['actual_stage_acceptance'])
b['future_policy_source_preserved']=load(OLD/'fresh-snapshot-bindings.json')['future_policy_source_preserved']
b['source_pins']=c['runtime_source_refs']+[whole_ref,ref(D/'root_manual_snapshot_threads.py'),decoderref]
bref=add(D/'fresh-snapshot-bindings.json',b)
index=dict(status='PASS_STATIC_DATA_ONLY_PENDING_LAST_SNAPSHOT' if final else 'PENDING_INDEPENDENT_STATIC_DATA_DECISION',proposal=pref,conditional_metadata=mref,machine_base=baseref,non_temporal_freeze=fref,snapshot_bindings=bref,snapshot_source=ref(D/'root_manual_snapshot_threads.py'),snapshot_OUTPUT=str(D/'root-live-preflight-1.json'),static_review=static,actual_stage_review=ref(A),actual_mandatory_consumer_review=ref(A),actual_sdk_physical=physical_ref(),effective_current_controller_stop_percent=100,actual_snapshot=None,final_release=None,runtime_release=False)
iref=add(Q/'FINAL-NONTEMPORAL-DATA-INDEX.json',index)
projection=transform(load(OR/'SNAPSHOT-STATIC-EQUALITY-AND-CAPPED-ARGV.json'))
snapshot_argv=projection['root_snapshot_argv'];snapshot_argv=[arg.replace('root_manual_snapshot_twenty_launches_sdk.py','root_manual_snapshot_threads.py') if isinstance(arg,str) else arg for arg in snapshot_argv];snapshot_argv[snapshot_argv.index('--bindings-sha256')+1]=bref['sha256'];snapshot_argv[snapshot_argv.index('--terminal')+1]=(None if physical_pending else str(P));snapshot_argv[snapshot_argv.index('--terminal-sha256')+1]=physical_ref()['sha256']
# Rebind every static equality to the full current authoritative descriptor.
equal=projection['snapshot_equal'];equal.update(accepted_actual_stage_fixture_parent_review=static,independent_static_execution_decision=static,non_temporal_join_result=fref,parent_identity=five,terminal_acceptance=physical_ref(),boot_id=predecessor['boot_id'],released_paths_absent=[predecessor[k] for k in ['common_exclusion','shared_heavy']])
projection.update(snapshot_equal=equal,root_snapshot_argv=snapshot_argv,OUTPUT=str(D/'root-live-preflight-1.json'),actual_static_review=static,bindings=bref,latest_physical=physical_ref(),non_temporal_freeze=fref,producer=ref(D/'root_manual_snapshot_threads.py'),schema='mckernel.selected205.m03-current100-static-snapshot-projection.v1',status='PASS_SOURCE_DERIVED_STATIC_DATA_ONLY_NO_SNAPSHOT' if final else 'PENDING_INDEPENDENT_STATIC_DATA_REVIEW')
# The exact capped snapshot stdout/stderr/status names stay in the new packet.
for k in ['stdout_path','stderr_path','status_path']:
 projection[k]=str(Q/Path(projection[k]).name)
projection['current100percent_included_only']=True
projectionref=add(Q/'SNAPSHOT-STATIC-EQUALITY-AND-CAPPED-ARGV.json',projection)
cfg=transform(load(OR/'FINAL-IHK-LOGGING-CHECK-CONFIG.json'));cfg.update(actual_scope=prop['scope'],actual_typed_composition=ref(A),attempt=str(attempt),effective_current_controller_stop_percent=100,future100policy_parked=False,latest_physical=physical_ref(),launch_argv=pre['owner_argv'],machine_base=baseref,machine_base_object=base,machine_index=fref,manifest=prop['normalized_manifest'],owner=ref(owner),owner_evidence=str(evidence),parent=prop['parent'],postjoin_readback=meta['postjoin_readback'],released_paths_absent=[predecessor[k] for k in ['common_exclusion','shared_heavy']],snapshot_adapter=ref(D/'root_manual_snapshot_threads.py'),snapshot_argv=snapshot_argv,snapshot_bindings=bref,snapshot_config=bref,snapshot_equal=equal,snapshot_packet=projectionref,snapshot_projection=projectionref,stage_acceptance=ref(A),static_review=static,throughput_target=None)
cfg['container_image_id']=c['container_image_id'];cfg['module_authority']=prop['component_ABI']
cfg['component_artifact']=prop['component_artifact']
cfg['runtime_source_refs']=b['source_pins']+[ref(D/'root_manual_snapshot_threads.py'),bref];cfg['diagnostic_extra_capture_growth_bytes']=8388608;cfg['capacity_reserve_bytes']=679477248
cfg['runtime_source_fd_identity_map']=ref(D/'RUNTIME-SOURCE-FD-IDENTITIES.json')
source_fd_map=load(cfg['runtime_source_fd_identity_map']['path'])
need(source_fd_map['schema']=='mckernel.current-native.selected-runtime-source-full-fd-identities.v1' and set(source_fd_map['identities'])=={row['path'] for row in cfg['runtime_source_refs'] if not row['path'].endswith('.json')},'mandatory exact selected runtime source FD map set')
cfg['status']='PASS_NON_TEMPORAL_CURRENT_IHK_LOGGING_NATIVE_CHECK_CONFIG' if final else 'PENDING_INDEPENDENT_STATIC_DATA_REVIEW'
cfgref=add(Q/'FINAL-IHK-LOGGING-CHECK-CONFIG.json',cfg)
oldx=load(OQ/'FINAL-SEVEN-ROOT-CALL-DATA.json');x=transform(oldx);x['historical_template_ancestry']=oldx['historical_template_ancestry'];x.update(machine_base=baseref,non_temporal_index=iref,snapshot_projection=projectionref,final_config=cfgref,native_allowed_argv=pre['owner_argv'],snapshot_output=str(D/'root-live-preflight-1.json'),required_caller=ref(Q/'root-run-exact-readonly-stage.py'))
rows=x['steps'];rows[0]['argv_template']=snapshot_argv;rows[1]['argv_template'][-2]=baseref['sha256'];rows[1]['argv_template'][rows[1]['argv_template'].index('-c')+1]=rows[1]['argv_template'][rows[1]['argv_template'].index('-c')+1].replace("{k:base['exclusive_queue_predecessor'][k] for k in ['path','sha256']}","base['exclusive_queue_predecessor']")
rows[2]['argv_template']=[arg.replace('review_final_205_release.py','review_final_threads_release.py') if isinstance(arg,str) else arg for arg in rows[2]['argv_template']];rows[2]['argv_template'][rows[2]['argv_template'].index('--config-sha256')+1]=cfgref['sha256'];rows[3]['argv_template']=pre['owner_argv']
for row,actual in zip(rows[4:],meta['postjoin_readback']['argv']):
 argv=row['argv_template'];at=argv.index('/usr/bin/tar') if '/usr/bin/tar' in argv else argv.index('/usr/bin/cat');row['argv_template']=argv[:at]+actual[2:]
for k in ['stdout','stderr','status']:rows[0][k]=projection[k+'_path']
rows[0]['capture_outputs']=[rows[0]['stdout'],rows[0]['stderr'],rows[0]['status']]+[rows[0]['status']+v for v in ['.command.json','.child.json','.direct-join.json']]
parents=list(dict.fromkeys([Q/'actual-command-data']+[Path(row['status']).parent for row in rows[1:]]+[Q]))
for p in parents+[Q/'capture-templates']:
 if not p.exists():p.mkdir(parents=True,mode=0o700)
 need(p.is_dir() and stat.S_IMODE(p.stat().st_mode)==0o700,'private fresh capture parent')
x['capture_parents']=[]
for p in parents:
 st=p.stat();x['capture_parents'].append(dict(path=str(p),identity=dict(device=st.st_dev,inode=st.st_ino,uid=st.st_uid,gid=st.st_gid,mode=oct(stat.S_IMODE(st.st_mode)))))
for row,oldrow in zip(rows,oldx['steps']):
 row['caller_argv_template'][3]=str(Q/'root-run-exact-readonly-stage.py')
 template=transform(load(oldrow['template']['path']));template['operations'][1]['argv_template']=row['argv_template']
 for k in ['stdout','stderr','status']:template['operations'][1][k+'_path']=row[k]
 template['release']=static;template['root_installed_release_path']=static['path'];row['template']=add(Q/'capture-templates'/Path(oldrow['template']['path']).name,template)
x['fresh_capture_and_actual_command_paths']=[v for row in rows for v in row['capture_outputs']+[row['materialized_command_data']]];need(len(x['fresh_capture_and_actual_command_paths'])==49,'exact seven rows49 outputs')
for p in x['fresh_capture_and_actual_command_paths']:need(not os.path.lexists(p),'fresh capture absent '+p)
need(not Path(x['snapshot_output']).exists() and not Path(x['final_machine_output']).exists() and not Path(x['final_guard_output']).exists(),'no snapshot/release/guard minted')
xref=add(Q/'FINAL-SEVEN-ROOT-CALL-DATA.json',x)
executor=subst((OQ/'root-execute-seven-1.py').read_text()).replace(ref(OQ/'FINAL-SEVEN-ROOT-CALL-DATA.json')['sha256'],xref['sha256']).replace("usedPercent']<97","usedPercent']<100").replace('floor+671088640','floor+679477248').replace('current SDK66 physical c253 predecessor, buildFAIL not artifact acceptance','current c7 positive physical predecessor; current threads diagnostic only')
eref=add_source(Q/'root-execute-seven-1.py',executor);ast.parse(executor)
# All non-temporal authority before LAST-snapshot is bound here; only the declared
# temporal machine/snapshot hash slots are null. Pending static nulls fail closed.
packet=dict(status='BOUND_NON_TEMPORAL_PENDING_ROOT_ADMISSION' if final else 'PENDING_ONE_INDEPENDENT_SOURCE_DATA_MAPPING_REVIEW',scope=prop['scope'],actual_stage_acceptance=c['actual_stage_acceptance'],actual_preparation_acceptance=ref(A),latest_exclusive_physical=physical_ref(),module_authority=prop['component_ABI'],strict_oracles=c['strict_oracle'],diagnostic_source_acceptance=c['observer_source_acceptance'],proposal=pref,conditional_metadata=mref,machine_base=baseref,freeze=fref,bindings=bref,index=iref,projection=projectionref,final_config=cfgref,seven_rows=xref,root_executor=eref,root_caller=ref(Q/'root-run-exact-readonly-stage.py'),snapshot_source=ref(D/'root_manual_snapshot_threads.py'),final_guard_source=ref(Q/'review_final_threads_release.py'),static_decision=static,full_authoritative_descriptors=True,caller_guard100included_only=True,native_runtime_authority=False,actual_guest_runs=0,diagnostic_extra_capture_growth_bytes=8388608,capacity_reserve_bytes=679477248,source_change_summary=['Exact selected M03 source and full actual argv; genuine latest physical schema and genuine stage/consumer contract; full authoritative descriptors; current100 included guard; same rootlock/currentUUID and648MiB diagnostic reserve','Accepted seven-row mapping/capture/executor semantics retained; current full terminal descriptor assembly equality, exact new owner/nonce/manifest/parent; only declared temporal slots late-bound','No workload/source recompilation/stage replay/new image; genuine complete HOST66 module artifact authority and separate physical retirement; accepted205 image/apps unchanged; collector bounded readiness/evidence correction independently accepted'])
packet['latest_physical_unresolved']=physical_pending
packet['actual_stage_expected_namespace']=c['stage_manifest']['path'];packet['criterion']='current-native-numa-interval'
packet['source_change_summary']=['Existing seven-row/nineteen-output engine retained for one accepted current NUMA staged case','Actual809e normalization/eccae stage and pinned3.9 root owner/inside/QEMU argv bind imagea4b7/equal launcher689d/matched module tuple and strict116B/empty/exit37 oracle','Genuine current cleanup report/decoder/mapping remain mandatory future inputs; no old c7/37e physical authority aliases; fullFD/capture/journal/TAR/record identities preserved','No guest, compiler, stage/archive replay, snapshot, activation or default/ACK/C-retirement credit; fetchedproof and finalruntime decision remainfuture']
packet['physical_consumer_mapping']=whole_ref;packet['actual_whole_consumer_acceptance']=None
packet['binding_source']=ref(Path(__file__))
add(Q/'ROOT-SEVEN-REVIEW-REF-1.json',static)
packetref=add(Q/'NATIVE-COHERENT-REVIEW-PACKET.json',packet)
validate_current_path_join(outputs,D,binding,pre)
for path,raw in outputs.items():
 out=path if final else path.with_name(path.name+('.PENDING-PHYSICAL' if physical_pending else '.PENDING-STATIC-CORRECTED'));need(not os.path.lexists(out),'fresh one-time data binding '+str(out))
 with out.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(raw);f.flush();os.fsync(f.fileno())
print(json.dumps({'packet':packetref,'pending':not final,'outputs':len(outputs),'rows':7,'fresh_capture_paths':49,'snapshots':0,'guest_runs':0}))
