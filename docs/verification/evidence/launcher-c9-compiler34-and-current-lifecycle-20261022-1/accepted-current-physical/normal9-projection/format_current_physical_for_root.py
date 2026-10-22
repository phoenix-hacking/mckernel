"""Finite ROOT mechanical current normal-nine report/mapping projection.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Genuine independent acceptance required. No runtime/locks/census/cleanup actions.
"""
from pathlib import Path
import argparse,ast,hashlib,io,json,tarfile
M=Path(__file__).resolve().parent
S=M.parent
B=S.parent
L=B.parent
D=L.parent
LG=D/'generated-source-1'
G=Path('/home/holden/mckernel-work/host-preparation/current-focused-progress-recording-20261021-1/current-normalization-review-recording-1')
H=Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1')
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=sha(raw))
def read(p):return json.loads(Path(p).read_bytes())
def write(name,value):
 p=M/name
 with p.open('xb')as f:f.write(canonical(value)+b'\n')
 return ref(p)
def main():
 a=argparse.ArgumentParser();a.add_argument('--physical-review',required=True);a.add_argument('--physical-review-sha256',required=True);opts=a.parse_args()
 independent=read(opts.physical_review);physical_decision=ref(opts.physical_review)
 assert physical_decision['sha256']==opts.physical_review_sha256
 assert independent['implementation_ownership']is False and independent['reviewer']and independent['reviewer']!='/root'
 assert independent['status']=='PASS'and independent['decision']=='PASS_ACTUAL_CURRENT_LAUNCHER_PHYSICAL_CLEANUP_ONLY'and independent['physical_clearance']is True,'genuine final physical acceptance required'
 reviewer=independent['reviewer']
 release=read(S/'cleanup-execution-release.json');obs=release['observation'];target=obs['target']
 assert independent['final_release_file_sha256']==ref(S/'cleanup-execution-release.json')['sha256']and independent['container_id']==target['container_id']
 original=read(B/'actual-exported-original-five-1/observation.json');assert obs==original
 raw_execution_path=G/'LAUNCHER-C9-FRESH-NAMESPACE-EXACT-THREE-OPERATION-EXECUTION-REVIEW.json'
 raw_execution=read(raw_execution_path);assert raw_execution==release['execution_review']
 payload={k:v for k,v in release.items()if k!='execution_review'};payload_ref=write('ACTUAL-REVIEWED-CLEANUP-PAYLOAD.json',payload)
 assert payload_ref['sha256']==raw_execution['reviewed_release_payload_sha256']
 execution=dict(schema='mckernel.numa-current-launcher.cleanup-exact-execution-review.v1',status='PASS',
  reviewer=raw_execution['reviewer'],implementation_ownership=False,recorder='/root',
  original_independent_decision=ref(raw_execution_path),reviewed_payload_sha256=raw_execution['reviewed_release_payload_sha256'],
  reviewed_release_payload_sha256=raw_execution['reviewed_release_payload_sha256'],same_release_preflight_cleanup_postjoin=True,
  no_outer_timeout_or_kill=True,target=target,whole_inline_execution_review=raw_execution)
 execution_ref=write('ROOT-MECHANICAL-EXECUTION-REVIEW-CONSUMER.json',execution)
 raw5path=G/'LAUNCHER-C9-CURRENT-ACTUAL-RAW5-AND-5FD-ACCEPTANCE.json';raw5=read(raw5path)
 raw5archive=ref(L/'actual-raw-five-export-capture-1/stdout')
 assert raw5archive['bytes']==raw5['archive_bytes']and raw5archive['sha256']==raw5['archive_sha256']
 raw5ref=write('ROOT-MECHANICAL-RAW5-ACCEPTANCE-CONSUMER.json',dict(status='PASS_ACTUAL_EXACT_FIVE_MEMBER_RAW_EXPORT_AND_OBSERVATION_ONLY',
  reviewer=raw5['reviewer'],implementation_ownership=False,recorder='/root',original_independent_decision=ref(raw5path),
  members=len(raw5['members']),archive=raw5archive,scope=raw5['scope'],native_acceptance=False))
 capture_pairs=[];tool_terminals={};captures=[];births=[]
 for role in ('cleanup','postjoin'):
  source=S/('ACTUAL-'+role.upper()+'-TOOL-OWNED-TERMINAL-PAIR.json');pair=read(source);saved={}
  assert pair['os_outer_pid']is None and pair['os_outer_birth']is None and pair['os_outer_process_group']is None
  for state in ('started','completed'):
   protocol=pair[state+'_protocol_record'];assert protocol['event']==pair[state+'_event']
   assert json.loads(pair['raw_'+state+'_event_utf8'])==protocol
   saved[state]=write(role+'-'+state+'-ACTUAL-PROTOCOL.json',protocol)
  last=pair['completed_event']['params']['item'];tool_terminals[role]=[last['id'],last['processId'],last['durationMs']]
  pairref=dict(role=role,**saved);capture_pairs.append(pairref)
  cap=S/('actual-'+role+'-capture-1');status=read(cap/'status.json');birth=read(cap/'child-start.json')
  assert status['returncode']==0 and status['direct_child_joined']and status['process_group_absent']and status['streams_closed']
  captures.append(dict(role=role,inner_birth=birth,inner_birth_ref=ref(cap/'child-start.json'),inner_join=ref(cap/'direct-join.json'),
   inner_status=ref(cap/'status.json'),controller_terminal_receipt=pairref,outer_os_identity=None,outer_group_observation=None,
   identity_scope='Captured sudo child PID/birth only; tool session never an OS PID; actor and outer OS births/groups unobserved.'))
  births.append(dict(role=role+'-rootchild',pid=birth['pid'],start=birth['proc_start_ticks'],direct_joined=True,group_absent=True))
 engine=read(S/'actual-cleanup-result-1.json');internal=sha(canonical(release));assert internal==engine['release_sha256']
 post=read(S/'actual-postjoin-capture-1/stderr');assert post['status']=='PASS_CLEANUP_POSTJOIN_READBACK_ONLY'and post['members']==5
 sidepath=B/'actual-exported-original-five-1/new-object-metadata.json';metadata=read(sidepath);assert post['actual_object_rows']==metadata['objects']
 names=[];saved={};expected=[engine[k]for k in ('plan','journal','capture')]+engine['archives']
 archive=(S/'actual-postjoin-capture-1/stdout').read_bytes()
 with tarfile.open(fileobj=io.BytesIO(archive),mode='r:')as tar:
  members=tar.getmembers();assert len(members)==5
  for member,row in zip(members,expected):
   assert member.isfile()and member.name==Path(row['path']).name and member.size==row['size']
   raw=tar.extractfile(member).read((4<<20)+1);assert len(raw)==row['size']and sha(raw)==row['sha256']
   saved[row['path']]=raw;names.append(dict(name=member.name,bytes=len(raw),sha256=sha(raw)))
 plan=json.loads(saved[engine['plan']['path']]);plan_sha=sha(canonical(plan));lines=saved[engine['journal']['path']].splitlines(keepends=True)
 assert len(lines)==9 and saved[engine['plan']['path']]==canonical(plan)+b'\n'
 previous=plan_sha
 for seq,(line,(event,index))in enumerate(zip(lines,[(e,i)for i in range(2)for e in ('before_exchange','after_exchange','release','after_release')]+[('complete',2)])):
  body=dict(event=event,index=index,sequence=seq,plan_sha256=plan_sha,previous=previous,plan_identity=[engine['plan']['device'],engine['plan']['inode']]);want=dict(body,hash=sha(canonical(body)))
  assert line==canonical(want)+b'\n';previous=want['hash']
 case=read(LG/'LAUNCHER-CASE-STATIC.json');counts=dict(finite_roles=case['finite_role_count'],selected_files=len(obs['selected_files']),
  postreader_actual_objects=len(metadata['objects']),inventories={k:len(v)for k,v in obs['inventories'].items()})
 projection=dict(boot_id=obs['boot_id'],filesystem_uuid=engine['filesystem_uuid'],container_id=target['container_id'],owner_nonce=target['owner_nonce'])
 # Request is large; use the already authenticated full request descriptor and parse only once, without serialization.
 request=read(obs['request']['path']);projection.update(lease_path=request['lease_path'],common_exclusion=request['common_exclusion_path'],shared_heavy='/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock')
 controller=dict(kind='tool-owned-unified-exec-terminal',decision='PASS_TOOL_TERMINAL_AND_SINGLE_CHILD_CONTROL_FLOW',implementation_ownership=False,
  reviewer=reviewer,capture_source=ref(LG/'capture_critical_two.py'),outer_os_identity=None,actor_os_identity=None,tool_processId_is_session_not_OS_PID=True)
 report=dict(schema='mckernel.independent-current-numa-launcher-cleanup-physical-release-review.v1',
  status='PASS_ACTUAL_CURRENT_NUMA_LAUNCHER_CLEANUP_POSTJOIN_AND_POSITIVE_PHYSICAL_RETIREMENT',decision='PASS_POSITIVE_CURRENT_NUMA_LAUNCHER_OWNER_AND_RECORD_RETIREMENT',
  scope=raw5['scope'],reviewer=reviewer,implementation_ownership=False,recorder='/root',independent_actual_physical_acceptance=physical_decision,
  operation_scope='launcher-only',launcher_only=True,target=target,container_id=target['container_id'],owner_nonce=target['owner_nonce'],boot_id=obs['boot_id'],filesystem_uuid=engine['filesystem_uuid'],
  physical_release=True,retired=True,record_release_complete=True,terminal=True,container_absent=True,common_shared_records_absent=True,owned_inner_groups_empty=True,controller_terminal=True,root_mutex_available=True,lease_retained=False,
  native_acceptance=False,runtime_acceptance=False,application_acceptance=False,execution_review=execution_ref,cleanup_release=ref(S/'cleanup-execution-release.json'),
  actual_cleanup_result=ref(S/'actual-cleanup-result-1.json'),actual_cleanup_status=ref(S/'actual-cleanup-capture-1/status.json'),actual_postjoin_archive=ref(S/'actual-postjoin-capture-1/stdout'),
  actual_postjoin_status=ref(S/'actual-postjoin-capture-1/status.json'),actual_postjoin_stderr=ref(S/'actual-postjoin-capture-1/stderr'),
  actual_preflight=read(S/'actual-readonly-preflight-capture-1/stdout'),actual_preflight_status=ref(S/'actual-readonly-preflight-capture-1/status.json'),actual_preflight_stdout=ref(S/'actual-readonly-preflight-capture-1/stdout'),
  controller_terminal_contract=controller,controller_terminal_receipts=capture_pairs,captures=captures,positive_closed_births=births,
  ownership_archives=[dict(archive=a,original=o)for a,o in zip(engine['archives'],obs['retained_exclusions'])],postjoin_members=names,
  full_journal=dict(rows=9,plan_canonical_sha256=plan_sha,plan_identity=[engine['plan']['device'],engine['plan']['inode']],final_chain_hash=previous,final_event='complete',all_canonical_lines_and_hash_links_verified=True),
  root_lock=plan['root_lock'],retained_mutex=dict(path=release['transaction_paths'][0],device=plan['mutex'][0],inode=plan['mutex'][1],root_mutex_reacquired_during_postjoin=True,identity_basis='Captured plan and executed postjoin semantics; no fresh FD observation by formatter.'),
  preservation=dict(all_actual_object_rows_equal_originalsidecar=True,all_actual_object_rows_equal_released_observation=True,finite_objects=counts['postreader_actual_objects'],finite_roles=counts['finite_roles'],inventories=counts['inventories'],selected_files=counts['selected_files'],full_transaction_FD_metadata_and_original_archive_inodes_preserved=True,protected_inputs_and_inventory_unchanged=True),
  release_internal_canonical_without_LF_sha256=internal,reviewed_cleanup_payload=payload_ref,whole_inline_execution_review=raw_execution,independently_data_bound_expected_projection=projection)
 report_ref=write('ROOT-MECHANICAL-CURRENT-PHYSICAL-REPORT.json',report)
 authorities={k:report[k]for k in ('execution_review','cleanup_release','actual_cleanup_result','actual_cleanup_status','actual_postjoin_archive','actual_postjoin_status','actual_postjoin_stderr','controller_terminal_receipts')}
 authorities.update(original_physical=report_ref,reviewed_cleanup_payload=payload_ref,source_capture=ref(LG/'capture_critical_two.py'),source_cleanup_engine=ref(S/'cleanup_launcher.py'),source_postreader=ref(S/'postjoin_launcher.py'),
  source_request=dict(path=obs['request']['path'],sha256=obs['request']['sha256'],bytes=obs['request']['size']),actual_raw_five_acceptance=raw5ref,actual_raw_five_archive=raw5archive,
  actual_original_five_fd_metadata=ref(L/'actual-original-five-FD-metadata-capture-1/stdout'),actual_sidecar_review_copy=ref(sidepath))
 mapping=dict(schema='mckernel.current-numa-launcher.known-kind-physical-consumer-mapping.v1',status='PASS_INDEPENDENT_CURRENT_NUMA_LAUNCHER_PHYSICAL_REPORT_MAPPING',
  reviewer=reviewer,implementation_ownership=False,recorder='/root',independent_review=physical_decision,physical_report_acceptance=physical_decision,
  controller_terminal_contract=controller,current_actual_counts=counts,genuine_current_authorities=authorities,source_refs={p.name:ref(p)for p in (S/'cleanup_launcher.py',S/'postjoin_launcher.py')},
  independently_data_bound_expected_projection=projection,runtime_release=False)
 mapref=write('ROOT-MECHANICAL-CURRENT-PHYSICAL-MAPPING.json',mapping)
 instance=dict(cleanup_engine_sha256=release['script_sha256'],execution_review_sha256=execution_ref['sha256'],mapping=mapref,physical_report=report_ref,
  objects=counts['postreader_actual_objects'],roles=counts['finite_roles'],selected_files=counts['selected_files'],tool_terminals=tool_terminals)
 write('CURRENT-PHYSICAL-EXPECTED-INSTANCE.json',instance)
 template=H/'launcher-sentinel-terminal-data-preparation-1/current_numa_launcher_physical.UNBOUND.py'
 helper=H/'terminal-consumer-preparation-1/prepare_successor_sources_correction1.py';ns={'ast':ast,'need':lambda x,y:None if x else (_ for _ in ()).throw(AssertionError(y))}
 node=next(n for n in ast.parse(helper.read_bytes()).body if isinstance(n,ast.FunctionDef)and n.name=='global_value');exec(compile(ast.Module(body=[node],type_ignores=[]),'<qualified DATA binding>','exec'),ns)
 out=M/'bound-physical-source-1';out.mkdir(mode=0o700);text=template.read_text();instance['tool_terminals']={k:tuple(v)for k,v in tool_terminals.items()}
 text=ns['global_value'](text,'EXPECTED_INSTANCE',repr(instance))
 (out/'current_numa_launcher_physical.py').write_text(text)
 (out/'CURRENT-PHYSICAL-MAPPING-BINDING.json').write_bytes(canonical(mapref)+b'\n')
 body=lambda s:{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
 assert body(text)==body(template.read_text())
 result=dict(status='ROOT_MECHANICAL_CURRENT_NORMAL_NINE_REPORT_MAPPING_BOUND_NO_RUNTIME_AUTHORITY',report=report_ref,mapping=mapref,
  decoder=ref(out/'current_numa_launcher_physical.py'),binding=ref(out/'CURRENT-PHYSICAL-MAPPING-BINDING.json'),independent_physical_decision=physical_decision,
  decoder_function_class_AST_unchanged=True,current_counts=counts,live_FD_observation_by_formatter=False,native_acceptance=False)
 write('ROOT-CURRENT-PHYSICAL-REPORT-MAPPING-COMPLETION.json',result);print(json.dumps(result,sort_keys=True))
if __name__=='__main__':main()
