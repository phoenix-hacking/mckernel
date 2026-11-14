from pathlib import Path
import json,hashlib,stat
D=Path(__file__).resolve().parent
HP=D.parent
report=HP/'phase5-m03-native-app-binding-independent-review-20261020-1/ACTUAL-EXIT7-NATIVE-FAILURE-PHYSICAL-RETIREMENT-REVIEW.json'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
s=report.lstat();fd=dict(path=str(report),sha256=ref(report)['sha256'],device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)),nlink=s.st_nlink,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
assert fd['sha256']=='62ba148e03291d001de685dc589caf13fe9bad8e5a94ff00d90543fd8e935882'
t=json.loads(report.read_bytes());b=json.loads(Path(t['snapshot_bindings']['path']).read_bytes())
ctx=dict(schema='mckernel.native-positive-physical-binding-context.v1',scope=t['scope'],physical=ref(report),physical_FD=fd,persistent_predecessor=b['physical_predecessor'])
p=D/'NATIVE-CURRENT-PHYSICAL-CONTEXT.json';p.write_text(json.dumps(ctx,indent=2,sort_keys=True)+'\n');p.chmod(0o600)
reader=HP/'phase5-next-native-positive-physical-binding-20261020-1/native_positive_physical_projection.py'
# Reuse the released stable-FD and full archive readers. This current failed
# instance retains the established native-owner kind, without positive7zero.
header='''"""Current62ba native-owner physical-only binding; source-only, unexecuted.
Preserves the genuine failed exit7 report, full FD identity and archive roles.
"""
from pathlib import Path
import hashlib,importlib.util,json,os
READER = READER_VALUE
CONTEXT_REF = CONTEXT_VALUE
SCHEMA = 'mckernel.independent-actual-m03-native-physical-retirement-review.v1'
def need(ok, why):
    if not ok: raise ValueError(why)
p=Path(READER['path']);need(hashlib.sha256(p.read_bytes()).hexdigest()==READER['sha256'],'accepted known-kind physical reader source')
s=importlib.util.spec_from_file_location('accepted_known_native_owner_kind',p)
R=importlib.util.module_from_spec(s);s.loader.exec_module(R)
checked=R.checked;captured_bytes=R.captured_bytes;tar_members=R.tar_members

def kind(t):
    need(t['schema']==SCHEMA and t['status']=='PASS' and t['decision']=='PASS_PHYSICAL_RETIREMENT_M03_NATIVE_OWNER_ONLY','genuine native-owner physical kind')

def project(t,physical_ref):
    kind(t);ctx=checked(CONTEXT_REF)
    need(physical_ref==ctx['physical'] and t==checked(ctx['physical_FD']),'whole current62ba report with complete FD identity')
    for key in ('physical_release','physical_retirement','all_owned_groups_empty','container_absent'):need(t[key] is True,'positive physical fact '+key)
    for key in ('lease_retained','implementation_ownership','cleanup_separately_required','application_acceptance','whole_M03_acceptance','positive_fork_or_final_ACK_acceptance','production_default_activation'):need(t[key] is False,'physical-only boundary '+key)
    f=t['facts'];need(f['new_native_persistent_ownership_record_files']==f['current_proc_matches']==f['current_proc_permission_denials']==0,'actual released ownership and complete host census')
    for key in ('all_clients_positively_reaped','all_inner_stream_hashes_and_full_nine_field_identities_verified','all_outer_inner_direct_joined_and_groups_absent','direct_and_attempt_result_copies_byte_equal','outer_owner_process_covered_by_exact_group_and_SID','retained_case_owner_and_attempt_records','three_final_name_nonce_CID_scans_returncode_zero_and_output_empty'):need(f[key] is True,'actual independent physical fact '+key)
    need(f['all_seven_inner_returncodes_zero'] is False and f['all_seven_outer_returncodes_zero'] is False and f['three_archive_result_copies_byte_equal'] is False,'preserve failed4main plus3manual branch and distinct receipt/result roles')
    need((f['tracked_host_PID_start_tuples'],f['tracked_host_PGIDs'],f['tracked_host_SIDs'])==(37,36,11),'complete current host identity cardinalities')
    inner=[checked(r) for r in t['inner_statuses']];outer=[checked(r) for r in t['outer_statuses']]
    need(len(inner)==7 and len(outer)==4,'genuine four main plus three failure reader branch')
    for row,rc in zip(inner,[0,0,0,1,0,0,0]):R.R.status_join(row,rc)
    for row,rc in zip(outer,[0,0,0,1]):R.R.status_join(row,rc)
    whole=checked(t['actual_whole']);need(whole['status']=='FAIL_STOPPED' and whole['failed_stage']=='native-owner' and [r['returncode'] for r in whole['rows']]==[0,0,0,1] and [r['status_path'] for r in whole['rows']]==[r['path'] for r in t['outer_statuses']],'actual failed whole chain; no successful7zero substitution')
    join=checked(t['actual_root_tool_join']);need(join['direct_executor_join_confirmed'] is True and join['tool_session']==6413 and join['tool_exit_code']==1 and join['whole_result']==whole and join['owner_status']==inner[3],'actual original failed executor and owner joins')
    raw={k:captured_bytes(v) for k,v in t['archived_record_FDs'].items()}
    need([captured_bytes(row['streams']['stdout']) for row in inner[4:]]==[raw['owner'],raw['result'],raw['attempt']],'all three whole failure archive stream identities')
    owner=tar_members(raw['owner'],f['owner_archive_regular_files']);attempt=tar_members(raw['attempt'],f['attempt_archive_regular_files'])
    need(owner['./inner-result.json']==raw['result']==attempt['./result.json'] and owner['./result.json']!=raw['result'],'distinct terminal receipt and byte-equal backend/attempt result roles')
    for key in ('receipt_evidence','owner_identity_evidence','terminal_inspect_evidence'):
        e=t[key];value=owner[e['member']]
        need(e['archive']==dict(path=t['archived_record_FDs']['owner']['path'],sha256=t['archived_record_FDs']['owner']['sha256'],bytes=len(raw['owner'])) and len(value)==e['bytes'] and hashlib.sha256(value).hexdigest()==e['sha256'],'complete archived member authority '+key)
    receipt=json.loads(owner['./result.json'],object_pairs_hook=R.R.no_duplicates)
    need(receipt==t['terminal_receipt'] and receipt==dict(status='FAIL',failure='OwnerError',absence_verified=True,lease_retained=False,container=t['container_id'],secondary=[],secondary_omitted=0,signal_number=None,application_acceptance=False),'whole authentic failed terminal receipt')
    meta=json.loads(owner['./owner.json'],object_pairs_hook=R.R.no_duplicates)
    need(meta['nonce']==t['case_nonce'] and meta['name']==t['actual_owner_name'] and meta['attempt']==t['actual_attempt'] and meta['owner_sha256']==t['actual_owner_source_sha256'] and meta['lock']==dict(dev=27,ino=4,uid=0,gid=0,mode=420,nlink=1),'whole actual owner identity and permanent mutex')
    clients=[(name,json.loads(value,object_pairs_hook=R.R.no_duplicates)) for name,value in sorted(owner.items()) if name[2:5].isdigit() and name.endswith('.json')]
    need(len(clients)==f['client_count']==len(t['docker_clients'])==25,'all current25 transport clients')
    for (name,c),saved in zip(clients,t['docker_clients']):
        cmd=c['command'];need(saved==dict(member=name,command=cmd,failure=c['failure'],returncode=c['returncode']) and cmd['reaped'] is True and cmd['returncode']==c['returncode'] and c['failure'] is None and all(type(cmd[k]) is int and cmd[k]>0 for k in ('pid','pgid','sid','proc_starttime')) and cmd['sid']==meta['outer']['sid'],'whole positively reaped current transport birth identity')
        need(c['returncode']==(1 if name in ('./009-start.json','./018-kill.json') else 0),'truthful current failed attached-start and already-exited kill codes')
    terminal=json.loads(owner['./021-inspect.stdout'],object_pairs_hook=R.R.no_duplicates)[0];state=terminal['State']
    need(terminal['Id']==t['container_id'] and terminal['Name']=='/'+t['actual_owner_name'] and terminal['Config']['Labels']['mckernel.native-diagnostic.owner']==t['case_nonce'] and state['Status']=='exited' and state['Running'] is False and state['Pid']==0 and state['ExitCode']==1 and state['OOMKilled'] is False,'whole exact exited current CID/name/nonce/state')
    rm=json.loads(owner['./022-rm.json']);need(rm['argv'][-3:]==['rm','--force',t['container_id']] and rm['returncode']==0,'actual same CID removal')
    selectors=['name=^/'+t['actual_owner_name']+'$','label=mckernel.native-diagnostic.owner='+t['case_nonce'],'id='+t['container_id']]
    need([c['argv'][-1] for _,c in clients[-3:]]==selectors,'three distinct current post-rm selectors')
    for name,c in clients[-3:]:need(c['argv'][3:7]==['ps','-aq','--no-trunc','--filter'] and c['returncode']==0 and owner[name[:-5]+'.stdout']==owner[name[:-5]+'.stderr']==b'','three empty actual post-rm census streams')
    result=json.loads(raw['result'],object_pairs_hook=R.R.no_duplicates)
    need(result['qemu_evidence']==t['qemu_evidence'] and result['admitted_qemu_argv']==t['qemu_evidence']['argv'] and result['cleanup']==t['cleanup']==dict(reaped=True,errors=[]) and result['capture_errors']==t['capture_errors']==[],'actual full QEMU argv and cleanup/capture roles')
    q=t['qemu_evidence'];need(q['pid']==q['pgid']==q['sid']==11 and q['starttime_ticks']==31436339 and q['returncode']==-9,'QEMU namespace birth preserved separately from host identities')
    b=checked(t['snapshot_bindings']);pre=b['physical_predecessor'];need(pre==ctx['persistent_predecessor'],'whole actual persistent predecessor identity')
    paths=[pre[k] for k in ('lease_path','common_exclusion','shared_heavy')]
    need(paths==f['predecessor_lease_common_shared_currently_absent'] and len(set(paths))==3,'whole actual persistent absence identities')
    for path in paths:need(not os.path.lexists(path),'persistent predecessor path currently absent')
    need(f['permanent_development_mutex']==dict(dev=27,ino=4,uid=0,gid=0,mode=420,nlink=1),'permanent27:4 retained; live root admission separate')
    return dict(boot_id=pre['boot_id'],filesystem_uuid=pre['filesystem_uuid'],container_id=t['container_id'],owner_nonce=t['case_nonce'],lease_path=paths[0],common_exclusion=paths[1],shared_heavy=paths[2])
'''
header=header.replace('READER_VALUE',repr(ref(reader)),1).replace('CONTEXT_VALUE',repr(ref(p)),1)
p=D/'native_current_physical_projection.py';p.write_text(header);p.chmod(0o600)
print(json.dumps(dict(source=ref(p),context=ref(D/'NATIVE-CURRENT-PHYSICAL-CONTEXT.json')),indent=2))
