"""Finite source/data binding only. Pending outputs cannot authorize execution.
One final invocation binds the independent full static decision; no snapshot,
root, compiler, owner, backend, socket or workload is invoked by this program.
"""
from pathlib import Path
import ast,copy,hashlib,json,os,stat,sys
SOURCE=Path(__file__).resolve().parent;D=Path('/home/holden/mckernel-work/host-preparation/phase5-m03-helper-retry-seven-step-preparation-20261020-1');Q=D;N=D;I=D;OLD=Path('/home/holden/mckernel-work/host-preparation/current-v6-composite-native-probe-20261020-1/host66-probe-1/stage-preparation-1');OQ=OLD/'native-packet-1';OR=OQ;H=Path('/home/holden/mckernel-work/host-preparation')

def load(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def need(v,s):
 if not v:raise ValueError(s)
need(len(sys.argv) in (5,7),'usage: bind_native_packet.py ACTUAL_STAGE_REVIEW SHA256 LATEST_CRATE_PHYSICAL_OR_PENDING SHA256_OR_PENDING [STATIC_DECISION SHA256]')
A=Path(sys.argv[1]);need(ref(A)['sha256']==sys.argv[2],'actual stage decision bytes')
physical_pending=False
need(sys.argv[3:5]!=['PENDING','PENDING'],'genuine latest physical required; unresolved current cleanup never authorizes output')
P=Path('/home/holden/mckernel-work/host-preparation/phase4-host-sdk-independent-review-20261020-1/HOST66-ACTUAL-PHYSICAL-RETIREMENT-REVIEW.json') if physical_pending else Path(sys.argv[3])
if not physical_pending:need(ref(P)['sha256']==sys.argv[4],'genuine latest full physical descriptor')
def physical_ref():return dict(path=None,sha256=None,bytes=None) if physical_pending else ref(P)
final=len(sys.argv)==7
need(not(final and physical_pending),'cannot publish final data without latest genuine physical predecessor')
if final:
 static=ref(sys.argv[5]);need(static['sha256']==sys.argv[6],'actual static hash');review=load(sys.argv[5]);need(review['status']=='PASS' and review['implementation_ownership'] is False,'independent exact static source/data decision')
else:static=dict(path=str(H/'phase5-m03-native-app-binding-independent-review-20261020-1/M03-HELPER-EXPORT-NATIVE-SOURCE-AND-NONTEMPORAL-RELEASE.json'),sha256=None,bytes=None)
c=load(I/'STATIC-M03-NONTEMPORAL-INPUTS.json');accept=load(A)
need(ref(A)==c['actual_preparation_acceptance'] and accept['schema']=='mckernel.independent-actual-m03-native-preparation-acceptance.v1' and accept['status']=='PASS','genuine complete M03 actual preparation decision')
pre=load(accept['actual_full_preflight']['path']);binding=load(accept['actual_binding_result']['path']);nonce=binding['nonce'];parent=Path(binding['attempt_parent']);attempt=parent/('attempt-'+nonce);evidence=Path(str(parent)+'.owner-'+nonce);stage=Path(c['stage_manifest']['path']).parent
facts=accept['facts'];consumer=dict(normalized_manifest=binding['manifest'])
pre=dict(pre,owner_argv=c['root_owner_argv'],inside_argv=pre['inside_owner_argv'],AF_UNIX_endpoints=[dict(option='-qmp',path=pre['paths']['qmp_socket'],encoded_bytes=pre['paths']['qmp_socket_bytes'])])
oldsettings=load(OLD/'variant-settings.json')
replacements={str(Path('/home/holden/mckernel-work/host-preparation/phase5-m03-native-app-binding-20261020-1/native-preparation-1/native-packet-1/posteffects-quarantine-variant-1/native-packet-1')):str(Q),str(OQ):str(Q),str(OLD):str(D),oldsettings['parent']:str(parent),str(Path(oldsettings['manifest']).parent):str(Path(binding['manifest']['path']).parent),oldsettings['nonce']:nonce}

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
owner=Path(c['runtime_owner']['path']);tree=ast.parse(owner.read_text());runtime=ast.literal_eval(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SOURCE_HASHES' for t in n.targets)))
s=parent.stat();five=dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)));full=dict(path=str(parent),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)),nlink=s.st_nlink,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
need(five==facts['parent_identity']==pre['parent_identity'] and not list(parent.iterdir()),'accepted exact empty parent')
need(all(facts['parent_nine_field_identity'][k]==getattr(s,k) for k in facts['parent_nine_field_identity']),'full accepted actual parent metadata')
physical=load(P)
import importlib.util
decoderref=c['physical_projection_source'];need(decoderref is not None,'latest genuine known-kind decoder is still unresolved')
need(ref(decoderref['path'])==decoderref,'reviewed known-kind decoder full source descriptor')
spec=importlib.util.spec_from_file_location('exact_m03_latest_physical',decoderref['path']);decoder=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoder)
whole_ref=c['physical_consumer_actual_acceptance'];need(type(whole_ref) is dict,'genuine current native-failure whole-consumer acceptance remains unresolved');need(ref(whole_ref['path'])==whole_ref,'complete genuine whole-consumer acceptance descriptor')
whole=load(whole_ref['path']);need(whole['status']=='PASS_SOURCE_AND_ACTUAL_WHOLE_CONSUMER_CHECKS_ONLY' and whole['decision']=='PASS_EXACT_M03_NATIVE_FAILURE_COMPLETE_CONSUMER_ASSEMBLY_AND_ACTUAL_LATE_SLOT_CLI_CHECKS' and whole['source']==decoderref and whole['genuine_current_physical']==ref(P),'exact accepted actual whole decoder/physical source tuple')
predecessor=decoder.project(physical,ref(P));need(predecessor==whole['actual_projection'],'complete genuine actual projection unchanged')
if physical_pending:predecessor={key:(value if key=='filesystem_uuid' else None) for key,value in predecessor.items()}
need(physical_pending or all(not os.path.lexists(predecessor[k]) for k in ['lease_path','common_exclusion','shared_heavy']),'released predecessor records absent')
prop=transform(load(OQ/'proposal.json'));prop.update(actual_full_argument_preflight=c['actual_full_preflight'],actual_ordinary_acceptance=ref(A),actual_stage_review=ref(A),actual_owner_sha256=ref(owner)['sha256'],argv=pre['owner_argv'],effective_current_controller_stop_percent=100,latest_exclusive_operation_physical_predecessor=physical_ref(),normalized_manifest=consumer['normalized_manifest'],parent=dict(path=str(parent),identity=five),parent_full_ninefield_identity=full,stage_manifest=ref(stage/'manifest.json'),scope='Fixed ten sequential strict387/254 Rust pairs in one accepted205 OS; changed Linux userland failure diagnostics only;20actual strict successes required; no partial acceptance',status='PENDING_LAST_SNAPSHOT_AND_FINAL_MACHINE')
prop.pop('pair_rounds',None);prop.pop('native_throughput_measurement',None);prop.pop('strict_startup_CPU_unchanged',None)
prop.update(component_ABI=c['tested_tuple_authority'],component_artifact=c['matched_module_artifact_authority'],criterion='P-M03-01',expected_apps_if_native_passes=1,oracles_stdout_bytes=[73],strict_oracle=c['strict_oracle'],scope='Functional OS/apps plus Rust cutover; selected P-M03-01 unaligned mprotect Rust app with exact73B stdout/EINVAL22/data/write/unmap oracle; no automatic whole M03/default/fork/ACK credit',new_throughput_or_behavior_credit=False)
prop['stage_manifest']=c['stage_manifest']
pref=add(Q/'proposal.json',prop)
meta=transform(load(OQ/'conditional-metadata.json'));meta.update(accepted_stage_manifest=prop['stage_manifest'],actual_metadata_review=ref(A),effective_current_controller_stop_percent=100,independent_static_execution_decision=static,normalized_manifest=prop['normalized_manifest'],parent_full_ninefield_identity=full,parent_identity=five,proposal=pref)
meta['status']='PASS_NONTEMPORAL_DATA_ONLY' if final else 'PENDING_INDEPENDENT_STATIC_DATA_REVIEW'
mref=add(Q/'conditional-metadata.json',meta)
base=transform(load(OQ/'machine-base.json'));base.update(accepted_actual_stage_fixture_parent_review=ref(A),conditional_metadata_release=mref,exclusive_queue_predecessor=physical_ref(),independent_static_execution_decision=static,parent_identity=five,terminal_cleanup_and_common_shared_release=dict(status='PASS_PHYSICAL_RETIREMENT_ONLY',scope='M03_NATIVE_FAILURE_PHYSICAL_RETIREMENT_ONLY',new_native_persistent_ownership_record_files=0,ref=physical_ref()))
baseref=add(Q/'machine-base.json',base)
freeze=transform(load(OQ/'non-temporal-freeze.json'));freeze.update(actual_consumer_result=c['actual_binding_result'],actual_mandatory_consumer_review=ref(A),actual_preflight=c['actual_full_preflight'],actual_stage_review=ref(A),conditional_metadata=mref,current_snapshot_producer=ref(SOURCE/'root_manual_snapshot_m03.py'),effective_current_controller_stop_percent=100,independent_static_execution_decision=static,latest_exclusive_operation_physical_predecessor=physical_ref(),latest_predecessor_note='Genuine latest exclusive physical release; historical tested HOST66 tuple remains separate' ,machine_base=baseref,native_manifest=prop['normalized_manifest'],native_target=None,owner_argv=pre['owner_argv'],inside_argv=pre['inside_argv'],qemu_argv=pre['qemu_argv'],AF_UNIX_endpoints=pre['AF_UNIX_endpoints'],parent_full_ninefield_identity=full,parent_legacy_fivefield_identity=five,proposal=pref,readonly_roots=pre['readonly_roots'],runtime_owner=ref(owner),runtime_runner=c['runtime_runner'],runtime_observer=c['runtime_observer'],runtime_source_hashes=runtime,runtime_source_count=len(runtime),entire_consumed_paths=pre['consumed_paths'],consumed_path_count=len(pre['consumed_paths']),stage_native_manifest=prop['stage_manifest'])
freeze['diagnostic_extra_capture_growth_bytes']=8388608
freeze['status']='PASS_ACTUAL_STATIC_DATA_ONLY_PENDING_LAST_SNAPSHOT' if final else 'PENDING_INDEPENDENT_STATIC_DATA_REVIEW'
fref=add(Q/'non-temporal-freeze.json',freeze)
b=transform(load(OLD/'ROOT-SNAPSHOT-BINDINGS.json'));b.update(conditional_metadata=mref,effective_current_controller_stop_percent=100,entire_consumed_paths=pre['consumed_paths'],machine_pending=baseref,mandatory_consumer_review=ref(A),manifest=prop['normalized_manifest'],non_temporal_freeze=fref,parent_full_identity=full,parent_identity=five,parent_review_identity=facts['parent_nine_field_identity'],physical_predecessor=predecessor,physical_review=physical_ref(),runtime_source_hashes=runtime,crate_request=None,stage_review=ref(A),static_review=static,qemu_argv=pre['qemu_argv'],inside_argv=pre['inside_argv'])
scratch=Path('/home/holden/mckernel-work/scratch').stat();b['scratch_identity']=[scratch.st_dev,scratch.st_ino]
b.pop('crate_request');b.pop('sdk_request',None)
b.update(runtime_owner=c['runtime_owner'],physical_projection_source=decoderref,strict_oracle=c['strict_oracle'],accepted_owner_argv=c['accepted_owner_argv'],root_owner_argv=c['root_owner_argv'],mandatory_consumer_review=c['actual_preparation_acceptance'],stage_review=c['actual_stage_acceptance'])
b['future_policy_source_preserved']=load(OLD/'ROOT-SNAPSHOT-BINDINGS.json')['future_policy_source_preserved']
b['source_pins']=c['runtime_source_refs']+[ref(SOURCE/'root_manual_snapshot_m03.py'),decoderref]
bref=add(D/'ROOT-SNAPSHOT-BINDINGS.json',b)
index=dict(status='PASS_STATIC_DATA_ONLY_PENDING_LAST_SNAPSHOT' if final else 'PENDING_INDEPENDENT_STATIC_DATA_DECISION',proposal=pref,conditional_metadata=mref,machine_base=baseref,non_temporal_freeze=fref,snapshot_bindings=bref,snapshot_source=ref(SOURCE/'root_manual_snapshot_m03.py'),snapshot_OUTPUT=str(D/'root-live-preflight-1.json'),static_review=static,actual_stage_review=ref(A),actual_mandatory_consumer_review=ref(A),actual_sdk_physical=physical_ref(),effective_current_controller_stop_percent=100,actual_snapshot=None,final_release=None,runtime_release=False)
iref=add(Q/'FINAL-NONTEMPORAL-DATA-INDEX.json',index)
projection=transform(load(OR/'SNAPSHOT-STATIC-EQUALITY-AND-CAPPED-ARGV.json'))
snapshot_argv=projection['root_snapshot_argv'];snapshot_argv=[arg.replace('root_manual_snapshot_twenty_launches_sdk.py','root_manual_snapshot_m03.py') if isinstance(arg,str) else arg for arg in snapshot_argv];snapshot_argv[snapshot_argv.index('--bindings-sha256')-1]=str(SOURCE/'root_manual_snapshot_m03.py');snapshot_argv[snapshot_argv.index('--bindings-sha256')+1]=bref['sha256'];snapshot_argv[snapshot_argv.index('--terminal')+1]=(None if physical_pending else str(P));snapshot_argv[snapshot_argv.index('--terminal-sha256')+1]=physical_ref()['sha256']
# Rebind every static equality to the full current authoritative descriptor.
equal=projection['snapshot_equal'];equal.update(accepted_actual_stage_fixture_parent_review=static,independent_static_execution_decision=static,non_temporal_join_result=fref,parent_identity=five,terminal_acceptance=physical_ref(),boot_id=predecessor['boot_id'],released_paths_absent=[predecessor[k] for k in ['common_exclusion','shared_heavy']])
projection.update(snapshot_equal=equal,root_snapshot_argv=snapshot_argv,OUTPUT=str(D/'root-live-preflight-1.json'),actual_static_review=static,bindings=bref,latest_physical=physical_ref(),non_temporal_freeze=fref,producer=ref(SOURCE/'root_manual_snapshot_m03.py'),schema='mckernel.selected205.m03-current100-static-snapshot-projection.v1',status='PASS_SOURCE_DERIVED_STATIC_DATA_ONLY_NO_SNAPSHOT' if final else 'PENDING_INDEPENDENT_STATIC_DATA_REVIEW')
# The exact capped snapshot stdout/stderr/status names stay in the new packet.
for k in ['stdout_path','stderr_path','status_path']:
 projection[k]=load(D/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json')['steps'][0][k.removesuffix('_path')]
projection['current100percent_included_only']=True
projectionref=add(Q/'SNAPSHOT-STATIC-EQUALITY-AND-CAPPED-ARGV.json',projection)
cfg=transform(load(OR/'FINAL-IHK-LOGGING-CHECK-CONFIG.json'));cfg.update(actual_scope=prop['scope'],actual_typed_composition=ref(A),attempt=str(attempt),effective_current_controller_stop_percent=100,future100policy_parked=False,latest_physical=physical_ref(),launch_argv=pre['owner_argv'],machine_base=baseref,machine_base_object=base,machine_index=fref,manifest=prop['normalized_manifest'],owner=ref(owner),owner_evidence=str(evidence),parent=prop['parent'],postjoin_readback=meta['postjoin_readback'],released_paths_absent=[predecessor[k] for k in ['common_exclusion','shared_heavy']],snapshot_adapter=ref(SOURCE/'root_manual_snapshot_m03.py'),snapshot_argv=snapshot_argv,snapshot_bindings=bref,snapshot_config=bref,snapshot_equal=equal,snapshot_packet=projectionref,snapshot_projection=projectionref,stage_acceptance=ref(A),static_review=static,throughput_target=None)
cfg['module_authority']=prop['component_ABI']
cfg['component_artifact']=prop['component_artifact']
cfg['runtime_source_refs']=b['source_pins']+[ref(SOURCE/'root_manual_snapshot_m03.py'),bref];cfg['diagnostic_extra_capture_growth_bytes']=8388608;cfg['capacity_reserve_bytes']=679477248
cfg['status']='PASS_NON_TEMPORAL_CURRENT_IHK_LOGGING_NATIVE_CHECK_CONFIG' if final else 'PENDING_INDEPENDENT_STATIC_DATA_REVIEW'
cfgref=add(Q/'FINAL-IHK-LOGGING-CHECK-CONFIG.json',cfg)
oldx=load(D/'FINAL-SEVEN-ROOT-CALL-DATA.PENDING.json');x=copy.deepcopy(oldx);x.update(machine_base=baseref,non_temporal_index=iref,snapshot_projection=projectionref,final_config=cfgref,native_allowed_argv=pre['owner_argv'],snapshot_output=str(D/'root-live-preflight-1.json'),required_caller=c['root_caller'])
rows=x['steps'];rows[0]['argv_template']=snapshot_argv
# Existing accepted caller late-binds argv[-1], which remains snapshot SHA.
rows[1]['argv_template'][-5:]=[str(D/'machine-base.json'),baseref['sha256'],str(D/'root-live-preflight-1.json'),str(D/'execution-release.json'),None]
need(str(SOURCE/'machine_assembly_caller.py') in rows[1]['argv_template'],'actual reviewed assembly CLI source')
rows[2]['argv_template'][rows[2]['argv_template'].index('--config-sha256')-1]=str(SOURCE/'review_final_205_release.py');rows[2]['argv_template'][rows[2]['argv_template'].index('--config-sha256')+1]=cfgref['sha256'];rows[3]['argv_template']=pre['owner_argv']
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
 row['caller_argv_template'][3]=str(Path(c['root_caller']['path']))
 template=transform(load(oldrow['template']['path']));template['operations'][1]['argv_template']=row['argv_template']
 for k in ['stdout','stderr','status']:template['operations'][1][k+'_path']=row[k]
 template['release']=static;template['root_installed_release_path']=static['path'];row['template']=add(Q/'capture-templates'/Path(oldrow['template']['path']).name,template)
x['fresh_capture_and_actual_command_paths']=[v for row in rows for v in row['capture_outputs']+[row['materialized_command_data']]];need(len(x['fresh_capture_and_actual_command_paths'])==49,'exact seven rows49 outputs')
for p in x['fresh_capture_and_actual_command_paths']:need(not os.path.lexists(p),'fresh capture absent '+p)
need(not Path(x['snapshot_output']).exists() and not Path(x['final_machine_output']).exists() and not Path(x['final_guard_output']).exists(),'no snapshot/release/guard minted')
xref=add(Q/'FINAL-SEVEN-ROOT-CALL-DATA.json',x)
executor=(Path('/home/holden/mckernel-work/host-preparation/phase5-m03-native-app-binding-20261020-1/native-preparation-1/native-packet-1/posteffects-quarantine-variant-1/native-packet-1/root-execute-seven-1.py').read_text()).replace('/home/holden/mckernel-work/host-preparation/phase5-m03-native-app-binding-20261020-1/native-preparation-1/native-packet-1/posteffects-quarantine-variant-1/native-packet-1',str(Q)).replace('6501f0699d788a5f5f7939f4833e14b51d16f6bb4dcdcd897a68b40b6a4ce07f',xref['sha256']).replace('current owned-caller78 physical predecessor','current M03 native-failure physical predecessor')
eref=add_source(Q/'root-execute-seven-1.py',executor);ast.parse(executor)
# All non-temporal authority before LAST-snapshot is bound here; only the declared
# temporal machine/snapshot hash slots are null. Pending static nulls fail closed.
packet=dict(status='BOUND_NON_TEMPORAL_PENDING_ROOT_ADMISSION' if final else 'PENDING_ONE_INDEPENDENT_SOURCE_DATA_MAPPING_REVIEW',scope=prop['scope'],actual_stage_acceptance=c['actual_stage_acceptance'],actual_preparation_acceptance=ref(A),latest_exclusive_physical=physical_ref(),module_authority=prop['component_ABI'],strict_oracles=c['strict_oracle'],diagnostic_source_acceptance=c['observer_source_acceptance'],proposal=pref,conditional_metadata=mref,machine_base=baseref,freeze=fref,bindings=bref,index=iref,projection=projectionref,final_config=cfgref,seven_rows=xref,root_executor=eref,root_caller=ref(Path(c['root_caller']['path'])),snapshot_source=ref(SOURCE/'root_manual_snapshot_m03.py'),final_guard_source=ref(SOURCE/'review_final_205_release.py'),static_decision=static,full_authoritative_descriptors=True,caller_guard100included_only=True,native_runtime_authority=False,actual_guest_runs=0,diagnostic_extra_capture_growth_bytes=8388608,capacity_reserve_bytes=679477248,source_change_summary=['Exact selected M03 source and full actual argv; genuine latest physical schema and genuine stage/consumer contract; full authoritative descriptors; current100 included guard; same rootlock/currentUUID and648MiB diagnostic reserve','Accepted seven-row mapping/capture/executor semantics retained; current full terminal descriptor assembly equality, exact new owner/nonce/manifest/parent; only declared temporal slots late-bound','No workload/source recompilation/stage replay/new image; genuine complete HOST66 module artifact authority and separate physical retirement; accepted205 image/apps unchanged; collector bounded readiness/evidence correction independently accepted'])
packet['latest_physical_unresolved']=physical_pending
packet['actual_stage_expected_namespace']=c['stage_manifest']['path'];packet['criterion']='P-M03-01'
packet['source_change_summary']=['Reuse accepted HOST66 seven-row mapping/caller/executor and stable final guard; one selected M03 Rust app only','M03 snapshot static joins use genuine b330 preparation/5940 init-only stage/full accepted current owner argv and exact73B oracle, unchanged live-resource/mutex checks','Genuine39cd native-owner physical retirement and accepted7f12 full decoder are current; no image cleanup or record transaction is asserted','No guest, compiler, archive regeneration, passed-fixture replay, activation or default/ACK credit']
packet['actual_whole_consumer_acceptance']=whole_ref
packet['binding_source']=ref(Path(__file__))
add(Q/'ROOT-SEVEN-REVIEW-REF-1.json',static)
packetref=add(Q/'NATIVE-COHERENT-REVIEW-PACKET.json',packet)
for path,raw in outputs.items():
 out=path if final else path.with_name(path.name+('.PENDING-PHYSICAL' if physical_pending else '.PENDING-STATIC-CORRECTED'));need(not os.path.lexists(out),'fresh one-time data binding '+str(out))
 with out.open('xb') as f:os.fchmod(f.fileno(),0o600);f.write(raw);f.flush();os.fsync(f.fileno())
print(json.dumps({'packet':packetref,'pending':not final,'outputs':len(outputs),'rows':7,'fresh_capture_paths':49,'snapshots':0,'guest_runs':0}))
