"""Exact known native-positive retirement kind; no source/SDK/semantic join.
Reuse accepted full stable-FD reader, captured identity and flat archive helpers.
"""
from pathlib import Path
import hashlib,importlib.util,json,os
READER={'path':'/home/holden/mckernel-work/host-preparation/phase5-m03-prepayload-helper-export-correction-20261020-1/runtime-source-1/native_failure_physical_projection.py','sha256':'ba5d3ea283eefb8f5e8249a8e703a10f4ffaeae15b8bfe4e51f379e8e6b45656'}
def need(ok,why):
 if not ok:raise ValueError(why)
p=Path(READER['path']);need(hashlib.sha256(p.read_bytes()).hexdigest()==READER['sha256'],'accepted full FD reader source')
s=importlib.util.spec_from_file_location('accepted_full_fd_reader',p);R=importlib.util.module_from_spec(s);s.loader.exec_module(R)
read_bytes=R.read_bytes;checked=R.checked;captured_bytes=R.captured_bytes;tar_members=R.tar_members
SCHEMA='mckernel.independent-actual-m03-native-physical-retirement-review.v1'
CONTEXT_REF={'path': '/home/holden/mckernel-work/host-preparation/phase5-m03-q6-positive-predecessor-binding-20261020-1/NATIVE-POSITIVE-Q6-PHYSICAL-CONTEXT.json', 'sha256': '6627cdb3c1b932b777373585af9a2523d8833bfc779d7aef4e481996acc0433e', 'bytes': 2603}

def kind(t):
 need(t['schema']==SCHEMA and t['status']=='PASS' and t['decision']=='PASS_PHYSICAL_RETIREMENT_M03_NATIVE_OWNER_ONLY','exact native-positive physical kind')

def ownership_join(t,owner,attempt,result):
 facts=t['facts'];receipt=json.loads(owner['./result.json'],object_pairs_hook=R.no_duplicates)
 need(receipt==t['terminal_receipt'] and receipt['status']=='PROTOCOL_PASS' and receipt['container']==t['container_id'] and receipt['absence_verified'] is True and receipt['lease_retained'] is False and receipt['failure'] is None and receipt['secondary']==[] and receipt['secondary_omitted']==0 and receipt['signal_number'] is None and receipt['application_acceptance'] is False,'whole genuine native-positive receipt')
 for key,raw in (('receipt_evidence',owner['./result.json']),('owner_identity_evidence',owner['./owner.json']),('terminal_inspect_evidence',owner['./026-inspect.stdout'])):
  e=t[key];need(e['archive']==dict(path=t['archived_record_FDs']['owner']['path'],sha256=t['archived_record_FDs']['owner']['sha256'],bytes=t['archived_record_FDs']['owner']['metadata']['size']) and len(raw)==e['bytes'] and hashlib.sha256(raw).hexdigest()==e['sha256'],'whole archived native member authority')
 meta=json.loads(owner['./owner.json'],object_pairs_hook=R.no_duplicates)
 need(meta['nonce']==t['case_nonce'] and meta['name']==t['actual_owner_name'] and meta['attempt']==t['actual_attempt'] and meta['owner_sha256']==t['actual_owner_source_sha256'],'whole actual native owner identity')
 need(meta['lock']==dict(dev=27,ino=4,uid=0,gid=0,mode=420,nlink=1),'archived permanent mutex identity')
 outer=meta['outer'];need(all(type(outer[k]) is int and outer[k]>0 for k in ('pid','pgid','sid','proc_starttime')),'actual owner host birth/group/session identity')
 clients=[(name,json.loads(raw,object_pairs_hook=R.no_duplicates)) for name,raw in sorted(owner.items()) if name[2:5].isdigit() and name.endswith('.json')]
 need(len(clients)==facts['client_count']==len(t['docker_clients'])==30,'all thirty native transport clients')
 for (name,c),saved in zip(clients,t['docker_clients']):
  cmd=c['command'];need(saved==dict(member=name,command=cmd,failure=c['failure'],returncode=c['returncode']),'complete client and birth identity preserved')
  need(cmd['reaped'] is True and cmd['returncode']==c['returncode'] and c['failure'] is None and all(type(cmd[k]) is int and cmd[k]>0 for k in ('pid','pgid','sid','proc_starttime')) and cmd['sid']==outer['sid'],'positive client reap/host process birth')
  need(c['returncode']==(1 if name=='./023-kill.json' else 0),'retain truthful already-exited kill result')
 need(owner['./result.json']!=attempt['./result.json'] and json.loads(attempt['./result.json'],object_pairs_hook=R.no_duplicates)==result,'distinct whole owner and guest result roles')
 need(result['qemu_evidence']==t['qemu_evidence'] and result['admitted_qemu_argv']==t['qemu_evidence']['argv'] and result['cleanup']==t['cleanup']==dict(reaped=True,errors=[]) and result['capture_errors']==t['capture_errors']==[],'actual namespace QEMU argv/reap/cleanup')
 q=t['qemu_evidence'];need(q['pid']==q['pgid']==q['sid']==9 and q['starttime_ticks']==32133813 and q['returncode']==-9,'namespace QEMU birth kept separate from host identities')
 terminal=json.loads(owner['./026-inspect.stdout'],object_pairs_hook=R.no_duplicates)[0];state=terminal['State']
 need(terminal['Id']==t['container_id'] and terminal['Name']=='/'+t['actual_owner_name'] and terminal['Config']['Labels']['mckernel.native-diagnostic.owner']==t['case_nonce'] and state['Status']=='exited' and state['Running'] is False and state['Pid']==state['ExitCode']==0 and state['OOMKilled'] is False,'actual exact terminal CID/name/owner/state')
 rm=json.loads(owner['./027-rm.json']);need(rm['argv'][-3:]==['rm','--force',t['container_id']] and rm['returncode']==0,'same exact CID removal')
 selectors=['name=^/'+t['actual_owner_name']+'$','label=mckernel.native-diagnostic.owner='+t['case_nonce'],'id='+t['container_id']]
 need([c['argv'][-1] for _,c in clients[-3:]]==selectors,'distinct final current name/nonce/CID selectors')
 for name,c in clients[-3:]:need(c['argv'][3:7]==['ps','-aq','--no-trunc','--filter'] and owner[name[:-5]+'.stdout']==owner[name[:-5]+'.stderr']==b'','actual post-rm census streams empty')
 return meta

def project(t,physical_ref):
 kind(t);ctx=checked(CONTEXT_REF)
 need(physical_ref==ctx['physical'] and t==checked(ctx['physical_FD']),'complete exact native-positive report and full FD identity')
 for key in ('physical_release','physical_retirement','all_owned_groups_empty','container_absent'):need(t[key] is True,'positive native physical '+key)
 for key in ('lease_retained','implementation_ownership','cleanup_separately_required','application_acceptance','whole_M03_acceptance','positive_fork_or_final_ACK_acceptance','production_default_activation'):need(t[key] is False,'physical-only boundary '+key)
 f=t['facts']
 for key in ('all_clients_positively_reaped','all_inner_stream_hashes_and_full_nine_field_identities_verified','all_outer_inner_direct_joined_and_groups_absent','all_seven_inner_returncodes_zero','all_seven_outer_returncodes_zero','outer_owner_process_covered_by_exact_group_and_SID','predecessor_lease_common_shared_currently_absent','retained_case_owner_and_attempt_records','three_archive_result_copies_byte_equal','three_final_name_nonce_CID_scans_returncode_zero_and_output_empty'):need(f[key] is True,'independent native physical fact '+key)
 need(f['current_proc_matches']==f['current_proc_permission_denials']==f['new_native_persistent_ownership_record_files']==0 and f['tracked_host_PID_start_tuples']==45 and f['tracked_host_PGIDs']==44 and f['tracked_host_SIDs']==14,'exact complete independent host census and no new persistent records')
 inner=[checked(r) for r in t['inner_statuses']];outer=[checked(r) for r in t['outer_statuses']]
 need(len(inner)==len(outer)==7,'whole seven-stage inner and outer status sets')
 for row in inner+outer:R.status_join(row,0)
 need(all(captured_bytes(row['streams']['stderr'])==b'' for row in inner),'all actual inner stderr empty')
 whole=checked(t['actual_whole']);need(whole['status']=='PASS_WHOLE_JOINED_RELEASED_CHAIN' and whole['failed_stage'] is None and len(whole['rows'])==7 and [r['status_path'] for r in whole['rows']]==[r['path'] for r in t['outer_statuses']] and all(r['returncode']==0 for r in whole['rows']),'actual complete seven-stage pipeline')
 join=checked(t['actual_root_tool_join']);need(join['schema']=='mckernel.root.actual-original-tool-wholejoin.v1' and join['status']=='PASS_ORIGINAL_WHOLE_COMMAND_JOIN' and join['session_id']==51811 and join['initial_tool_chunk']=='8a6bec' and join['final_tool_chunk']=='a3a778' and join['tool_exit_code']==0 and join['tool_session_completed'] is True and join['whole']==t['actual_whole'] and join['native_or_application_acceptance'] is False,'positive original tool wholejoin evidence')
 raw={k:captured_bytes(v) for k,v in t['archived_record_FDs'].items()}
 need([captured_bytes(row['streams']['stdout']) for row in inner[4:]]==[raw['owner'],raw['result'],raw['attempt']],'all three full archived stream FD identities')
 owner=tar_members(raw['owner'],f['owner_archive_regular_files']);attempt=tar_members(raw['attempt'],f['attempt_archive_regular_files'])
 need(owner['./inner-result.json']==raw['result']==attempt['./result.json'],'three copies of actual guest result byte equal')
 result=json.loads(raw['result'],object_pairs_hook=R.no_duplicates);meta=ownership_join(t,owner,attempt,result)
 argv=inner[3]['argv'];need(argv[argv.index('--owner-sha256')+1]==meta['owner_sha256'] and argv[argv.index('--nonce')+1]==meta['nonce'] and inner[3]['pid']==meta['outer']['sid'],'actual native owner argv and host SID join')
 b=checked(t['snapshot_bindings']);pre=b['physical_predecessor'];need(pre==ctx['persistent_predecessor'],'whole persistent predecessor identity; no SDK artifact join')
 for key in ('lease_path','common_exclusion','shared_heavy'):need(not os.path.lexists(pre[key]),'persistent predecessor path still absent')
 need(f['permanent_development_mutex']==dict(path='/run/lock/mckernel-development.lock',device=27,inode=4,uid=0,gid=0,mode='0o644',nlink=1),'exact retained permanent mutex fact; live root admission separate')
 return dict(boot_id=pre['boot_id'],filesystem_uuid=pre['filesystem_uuid'],container_id=t['container_id'],owner_nonce=t['case_nonce'],lease_path=pre['lease_path'],common_exclusion=pre['common_exclusion'],shared_heavy=pre['shared_heavy'])
