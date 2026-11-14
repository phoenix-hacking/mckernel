"""Case-specific read-only root admission recipe; no owner or guest invocation."""
from pathlib import Path
import argparse,fcntl,hashlib,importlib.util,json,os,re,stat,subprocess,time
N=Path(__file__).resolve().parent
OUTPUT=N/'root-live-preflight-1.json'
class Refusal(RuntimeError):pass
def need(ok,message):
    if not ok:raise Refusal(message)
def ref(path):return {'path':str(path),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'bytes':Path(path).stat().st_size}
def checked(record):
    p=Path(record['path']);need(p.is_absolute() and p.resolve(strict=True)==p and not p.is_symlink(),'canonical input')
    raw=p.read_bytes();need(len(raw)<=4*1024**2 and hashlib.sha256(raw).hexdigest()==record['sha256'],'input hash');need('bytes' not in record or len(raw)==record['bytes'],'whole descriptor bytes');need('size' not in record or (len(raw)==record['size'] and p.stat().st_mode==record['mode']),'whole typed descriptor size/mode')
    return json.loads(raw)
def identity(p):
    s=Path(p).lstat();return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)))
def command(argv):
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,check=False)
    need(p.returncode==0 and p.stderr==b'' and len(p.stdout)<=4*1024**2,'bounded read-only command')
    return p.stdout.decode()
def static_joins(b):
    for row in b['source_pins']:
        need(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],'frozen source')
    meta=checked(b['conditional_metadata']);proposal=checked(meta['proposal']);pending=checked(b['machine_pending'])
    need(meta['parent_identity']==proposal['parent']['identity']==b['parent_identity']==pending['parent_identity'],'parent static join')
    need(pending['independent_static_execution_decision']==b['static_review'],'static review join');checked(b['static_review'])
    c=checked(b['mandatory_consumer_review']);need(b['mandatory_consumer_review']['sha256']=='392198a2fa47fc851c55ddd9640952600901158af6d680322e53372c534d2e3d' and c['decision']=='PASS_ACTUAL_PAIRED_ALIAS_PUBLICATION_AND_PURE_NORMALIZATION_ONLY' and c['implementation_ownership'] is False and c['findings']==[] and c['reviewer'],'actual remaining normalization review')
    stage=checked(b['stage_review']);need(stage['decision']=='PASS_ACTUAL_REMAINING_APP_ONLY_OFFLINE_STAGE_AND_MANIFEST_ONLY' and stage['implementation_ownership'] is False and stage['reviewer'] and stage['observed_stage']['final_members']==60 and stage['observed_stage']['unchanged_members']==59 and stage['observed_stage']['sole_changed_member']=='apps/app','actual app-only stage')
    pre=checked(b['actual_original_preflight']);projection=checked(b['actual_full_preflight']);binding=checked(b['actual_binding_result'])
    for key,name in [('actual_original_preflight','ACTUAL-NATIVE-PREFLIGHT.json'),('actual_binding_result','ACTUAL-BINDING.json')]:
        need(b[key]['sha256']==c['evidence'][name]['sha256'] and b[key]['bytes']==c['evidence'][name]['bytes'],'actual accepted descriptor')
    need(projection['original_preflight']==b['actual_original_preflight'] and all(projection[k]==v for k,v in pre.items()),'finite actual preflight projection')
    need(binding['manifest']==b['manifest']==pre['binding']['manifest'] and binding['nonce']==proposal['nonce'] and binding['attempt_parent']==proposal['parent']['path'],'manifest nonce parent joins')
    need(pre['parent_nine_field_identity']==b['parent_review_identity'] and projection['parent_identity']==b['parent_identity'],'full nine-field parent')
    need(pre['consumed_paths']==b['entire_consumed_paths'] and pre['readonly_roots']==projection['readonly_roots'],'consumed roots')
    need(projection['root_owner_argv']==b['root_owner_argv']==proposal['argv'] and pre['owner_argv']==b['accepted_owner_argv'] and pre['inside_owner_argv']==b['inside_argv'] and pre['qemu_argv']==b['qemu_argv'],'all actual owner argv')
    need(pre['guest_runs']==pre['root_operations']==0 and pre['snapshot'] is None and pre['runtime_release'] is None,'bounded no-effect source preparation')
    result=checked(b['actual_normalization_result'])['result'];need(result['returncode']==0 and result['direct_child_joined'] is True and result['group_absent'] is True and result['closed_streams'] is True and result['error'] is None and result['retirement_error'] is None,'actual closed normalization')
    for role,row in result['captures'].items():
        raw=Path(row['path']).read_bytes();need(len(raw)==row['size'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'actual captured bytes')
        if role=='stderr':need(raw==b'','actual empty stderr')
    spec=importlib.util.spec_from_file_location('exact_remaining_owner',b['runtime_owner']['path']);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
    _,manifest=owner.bound_manifest(b['manifest']['path'],b['manifest']['sha256'])
    need(manifest['payload']==b['payload_contract'] and manifest['artifacts']['mckernel_image']['sha256']==b['repaired_image_sha256'],'unchanged actual payload and kernel')
    need(owner.SOURCE_HASHES==b['runtime_source_hashes'] and b['strict_oracle']['kind']=='M07_REMAINING_NATIVE_CONDITIONAL_TYPED','actual typed source binding')
    need(proposal['profile']['mckernel_cpus']==2 and proposal['profile']['memory']==proposal['profile']['memory_swap']==12884901888,'reviewed exact profile')
    return proposal,owner
def same_ref(a, b, label):
    need(a == b, label)

def successful_native_terminal_joins(t, b):
    # Current native owner retirement and earlier released build records have
    # distinct genuine schemas. No native lease file is invented here.
    need(t == checked(b['physical_review']), 'exact independent latest native physical report')
    need(t['schema'] == 'mckernel.current-numa-launcher.native-owner-physical-lifecycle-review.v1'
         and t['status'] == 'PASS_ACTUAL_CURRENT_NATIVE_OWNER_PHYSICAL_RETIREMENT_AND_JOIN_ONLY'
         and t['decision'] == 'PASS_CURRENT_NATIVE_CONTAINER_LEASE_PROCESS_AND_CONTROLLER_TERMINAL_SCOPE_ONLY', 'current native physical schema/status/decision')
    need(t['implementation_ownership'] is False and isinstance(t['reviewer'], str) and t['reviewer'], 'independent current native physical review')
    for key in ('current_native_owner_physical_release', 'current_native_request_lease_release', 'current_owner_terminal', 'retired', 'container_absent', 'all_14_owned_caller_and_rootchild_groups_observed_absent', 'all_30_saved_docker_client_commands_reaped', 'all_three_readbacks_exact_join', 'readback_stderr_empty', 'qemu_teardown_observed', 'guest_procfs_empty'):
        need(t[key] is True, 'positive native physical fact: ' + key)
    need(t['lease_retained'] is False and t['primary_failure'] is None and t['secondary_failures'] == []
         and t['secondary_failures_omitted'] == 0 and t['capture_errors'] == [], 'native owner failure and retirement ledger')
    value = t['atomic_owner_receipt']['value']
    need(value['status'] == 'PROTOCOL_PASS' and value['absence_verified'] is True
         and value['lease_retained'] is False and value['failure'] is None
         and value['secondary'] == [] and value['secondary_omitted'] == 0, 'actual atomic native owner retirement')
    need(t['qemu_cleanup'] == {'errors': [], 'reaped': True}, 'native child capture retirement')
    state = t['container_terminal_state']
    need(state['Status'] == 'exited' and state['Pid'] == 0 and state['ExitCode'] == 0
         and state['OOMKilled'] is False and state['Running'] is False
         and state['Dead'] is False and state['Error'] == '', 'retired current native container')
    c = b['physical_predecessor']; owner = t['owner_record']
    need(t['container_id'] == value['container'] == c['container_id']
         and owner['nonce'] == c['owner_nonce'], 'latest native container and owner nonce')
    births = t['actual_closed_births']
    names = ['LAST-snapshot', 'machine-assembly', 'final-guard', 'native-owner', 'readback-1', 'readback-2', 'readback-3']
    need(len(births) == 7 and [row['role'] for row in births] == names
         and all(row['direct_joined'] is True and row['group_absent'] is True
                 and row['returncode'] == 0 for row in births), 'all seven actual native caller/rootchild joins')
    mutex = owner['lock']
    need((mutex['dev'], mutex['ino'], mutex['uid'], mutex['gid'], mutex['mode'], mutex['nlink'])
         == (27, 4, 0, 0, 420, 1) and b['root_lock_identity']
         == dict(device=27, inode=4, uid=0, gid=0, mode='0o644'), 'permanent mutex identity retained; fresh live lock check remains separate')
    controller = t['controller_terminal_contract']
    need(controller['kind'] == 'tool-owned-unified-exec-terminal'
         and controller['decision'] == 'PASS_TOOL_TERMINAL_AND_SINGLE_CHILD_CONTROL_FLOW'
         and controller['implementation_ownership'] is False and controller['reviewer']
         and controller['capture_source'] == b['native_controller_source']
         and t['controller_terminal_pair'] == b['native_controller_pair']
         and t['outer_os_identity'] is None and t['outer_process_group_observation'] is None,
         'genuine tool-owned native controller; no invented OS birth or group')
    # Reuse the already qualified exact build-record decoder on its genuine
    # earlier build report. Native retirement does not relabel that report.
    previous = checked(b['released_record_review'])
    source = b['released_record_projection_source']; path = Path(source['path'])
    need(hashlib.sha256(path.read_bytes()).hexdigest() == source['sha256'], 'exact released-record decoder source')
    spec = importlib.util.spec_from_file_location('current_released_launcher_records', path)
    decoder = importlib.util.module_from_spec(spec); spec.loader.exec_module(decoder)
    released = decoder.project(previous, b['released_record_review'])
    need(released == b['released_record_predecessor'], 'complete genuine earlier released record provenance')
    need(set(c) == set(released) == {'boot_id', 'filesystem_uuid', 'container_id', 'owner_nonce', 'lease_path', 'common_exclusion', 'shared_heavy'}, 'exact seven-field native predecessor interface')
    need(all(c[key] == released[key] for key in ('boot_id', 'filesystem_uuid', 'lease_path', 'common_exclusion', 'shared_heavy')), 'same boot/UUID and earlier released build record paths')
    need(all(not os.path.lexists(c[key]) for key in ('lease_path', 'common_exclusion', 'shared_heavy')), 'earlier released build records remain absent')

def failed_owner_join(t, historical, expected):
    need(t['schema']=='mckernel.current-native.failed-owner-physical-retirement-review.v1' and t['status']=='PASS_CURRENT_FAILED_OWNER_RETIREMENT_ONLY' and t['decision']=='ACCEPT_CURRENT_FAILED_OWNER_RETIREMENT_ONLY','actual current failed-owner physical kind')
    need(t['implementation_ownership'] is False and t['reviewer'] and t['recorder']=='/root' and t['missing_retirement_observations']==[],'genuine qualified failed-owner retirement authority')
    v=t['atomic_owner_receipt']['value'];owner=t['owner_record'];current=t['current_identity']
    need(v['status']=='FAIL' and v['failure']=='OwnerError' and v['absence_verified'] is True and v['lease_retained'] is False and v['secondary']==[] and v['secondary_omitted']==0 and v['signal_number'] is None,'actual FAIL receipt with complete qualified retirement')
    need(v['container']==current['container'] and owner['nonce']==current['nonce'] and owner['outer']['pid']==current['owner_pid'] and int(owner['outer']['proc_starttime'])==current['owner_start'],'exact failed owner identity')
    lock=owner['lock'];need((lock['dev'],lock['ino'],lock['uid'],lock['gid'],lock['mode'],lock['nlink'])==(27,4,0,0,420,1) and current['lock_device_inode']==[27,4],'retained permanent root mutex identity')
    rows=t['actual_closed_births'];need(len(rows)==4 and [row['role'] for row in rows]==['LAST-snapshot','machine-assembly','final-guard','native-owner'],'actual four-stage failed sequence, no success readbacks')
    for index,row in enumerate(rows):
        for key in ('outer','rootchild'):
            status=row[key];need(status['returncode']==(1 if index==3 else 0) and status['direct_child_joined'] is True and status['process_group_absent'] is True and status['observer_error'] is None,'all eight actual failed-sequence child groups closed')
    child=rows[3]['rootchild'];need(child['pid']==current['native_owner_caller_pid'] and int(child['start'])==current['native_owner_caller_start'],'exact failed native-owner caller birth')
    need(t['success_readbacks_executed'] is False and t['application_acceptance'] is False and t['native_accepted'] is False and t['runtime_retry_authority'] is False,'no failed-attempt application or retry authority')
    need(t['new_global_census_observed'] is False and t['new_common_shared_record_absence_observed'] is False and t['root_mutex_reacquisition_observed'] is False,'preserve unobserved post-failure census and reacquisition facts')
    control=t['controller_terminal'];need(control['kind']=='tool-owned-unified-exec-terminal' and control['exit_code']==1 and control['process_handle_is_OS_PID'] is False and control['actual_whole_failure_matches_terminal_output'] is True and control['outer_os_identity'] is None and control['outer_process_group_observation'] is None,'actual failed tool-owned terminal without invented outer OS birth')
    value={k:historical[k] for k in ('boot_id','filesystem_uuid','lease_path','common_exclusion','shared_heavy')};value.update(container_id=current['container'],owner_nonce=current['nonce'])
    need(set(expected)==set(value) and value==expected,'complete current failed-owner seven-field predecessor')
    return value

def terminal_joins(t,b):
    if t.get('schema')!='mckernel.current-native.failed-owner-physical-retirement-review.v1':
        return successful_native_terminal_joins(t,b)
    need(t==checked(b['physical_review']),'exact genuine current failed-owner report')
    checked(t['original_independent_decision'])
    need(checked(t['owner_record_ref'])==t['owner_record'] and checked(t['atomic_owner_receipt']['descriptor'])==t['atomic_owner_receipt']['value'],'actual authenticated failed owner/FAIL receipt copies')
    historical_bindings=checked(b['failed_owner_previous_bindings']);last=checked(b['failed_owner_last_snapshot'])
    need(last['status']=='PASS_LIVE_PREEXECUTION_SNAPSHOT' and last['boot_id']==historical_bindings['physical_predecessor']['boot_id'],'actual failed-attempt LAST snapshot boot lineage')
    prior=historical_bindings['physical_predecessor']
    need(set(last['released_paths_absent'])=={prior['common_exclusion'],prior['shared_heavy']},'actual pre-failure released-path observations only')
    value=failed_owner_join(t,prior,b['physical_predecessor'])
    for row in t['actual_closed_births']:
        need(checked(row['outer_status'])==row['outer'] and checked(row['rootchild_status'])==row['rootchild'],'exact retained failed four-stage caller/rootchild producer records')
    command=t['failure_start_command'];need(checked(command['descriptor'])==command['value'] and command['value']['returncode']==1 and command['value']['command']['reaped'] is True and command['value']['failure']=='OwnerError','actual failed Dockerstart and reaped client')
    need(command['value']['argv'][-3:]==['start','--attach',value['container_id']],'actual failure target CID')
    pair=checked(t['controller_terminal_pair']);control=t['controller_terminal'];need(pair['started_event']==control['started_event'] and pair['completed_event']==control['completed_event'],'actual typed failed controller pair refs')
    first=checked(pair['started_event']);last_event=checked(pair['completed_event']);x=first['event']['params']['item'];y=last_event['event']['params']['item']
    need(first['event']['method']=='item/started' and last_event['event']['method']=='item/completed' and x['type']==y['type']=='commandExecution' and x['id']==y['id']==control['item_id'] and x['command']==y['command'] and y['processId']==control['tool_process_handle'] and y['status']=='failed' and y['exitCode']==1,'genuine actual failed tool completion, handle is not OS PID')
    source=b['failed_owner_released_record_decoder'];need(hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()==source['sha256'],'separate genuine released-record decoder source')
    # This report establishes native mutex-FD retirement, never a compiler archive.
    # Carry paths are historical locators; absence is checked afresh on EACH call,
    # including the future exclusive LAST snapshot, without changing report facts.
    need(all(not os.path.lexists(value[k]) for k in ('lease_path','common_exclusion','shared_heavy')),'current carried ownership paths absent; fresh LAST repeats observation')
    need(b['root_lock_identity']==dict(device=27,inode=4,uid=0,gid=0,mode='0o644'),'permanent mutex identity; live reacquisition remains separate')




def collect_live(b,proposal,owner):
    parent=Path(proposal['parent']['path']);scratch=Path(owner.SCRATCH);lock=Path(owner.LOCK)
    free=False
    with lock.open('r') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);free=True
        except BlockingIOError:pass
        finally:
            if free:fcntl.flock(stream,fcntl.LOCK_UN)
    names=['owner.stdout','owner.stderr','owner-join.json']+[f'readback-{i}.{suffix}' for i in range(1,4) for suffix in ('stdout','stderr','command.json')]
    paths=[b['physical_predecessor']['common_exclusion'],b['physical_predecessor']['shared_heavy']]
    capacity={}
    for path,floor in [(Path(owner.REPO),16*1024**3),(scratch,12*1024**3)]:
        s=os.statvfs(path);capacity[str(path)]={'available_bytes':s.f_bavail*s.f_frsize,'floor_bytes':floor,'reserve_bytes':679477248}
    state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
    s=scratch.stat()
    return {'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'parent_identity':identity(parent),
      'parent_canonical':parent.resolve(strict=True)==parent,'parent_empty':not list(parent.iterdir()),
      'attempt_absent':not os.path.lexists(parent/('attempt-'+proposal['nonce'])),
      'owner_evidence_absent':not os.path.lexists(str(parent)+'.owner-'+proposal['nonce']),
      'fresh_outputs_absent':all(not os.path.lexists(N/name) for name in names) and not os.path.lexists(OUTPUT),
      'scratch_identity':[s.st_dev,s.st_ino],
      'mount':json.loads(command(['/usr/bin/findmnt','-J','-o','TARGET,UUID','-T',str(scratch)]))['filesystems'],
      'root_lock_identity':identity(lock),'root_mutex_snapshot_free':free,
      'released_paths_absent':{p:not os.path.lexists(p) for p in paths},
      'predecessor_container_absent':command(['/usr/bin/docker','ps','-aq','--no-trunc','--filter','id='+b['physical_predecessor']['container_id']])=='',
      'image_id':command(['/usr/bin/docker','image','inspect','--format','{{.Id}}',owner.IMAGE]).strip(),
      'image_record_sha256':hashlib.sha256(Path(owner.IMAGE_RECORD).read_bytes()).hexdigest(),
      'cgroup':{p:Path(p).read_text().strip() for p in owner.CGROUP},'capacity':capacity,
      'mem_available_bytes':int(next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')).split()[1])*1024,
      'launcher_phase':state['phase'],'launcher_stop_reason':state['stop_reason'],'included_usage_percent':state['last_rate_limits']['primary']['usedPercent']}
def validate_live(o,b,owner):
    need(o['boot_id']==b['physical_predecessor']['boot_id'],'current boot')
    need(o['parent_identity']==b['parent_identity'] and all(o[k] is True for k in ('parent_canonical','parent_empty','attempt_absent','owner_evidence_absent','fresh_outputs_absent')),'actual parent/fresh outputs')
    need(o['scratch_identity']==b['scratch_identity'] and o['mount']==[{'target':owner.SCRATCH,'uuid':b['physical_predecessor']['filesystem_uuid']}],'current scratch mount')
    need(o['root_lock_identity']==b['root_lock_identity'] and o['root_mutex_snapshot_free'] is True,'root mutex')
    need(o['released_paths_absent']=={b['physical_predecessor'][key]:True for key in ('common_exclusion','shared_heavy')} and o['predecessor_container_absent'] is True,'current physical/common/shared release')
    need(o['image_id']==owner.IMAGE and o['image_record_sha256']==owner.IMAGE_RECORD_SHA256 and o['cgroup']==owner.CGROUP,'actual image/cgroup')
    for path,floor in ((owner.REPO,16*1024**3),(owner.SCRATCH,12*1024**3)):
        row=o['capacity'][path];need(row['floor_bytes']==floor and row['reserve_bytes']==679477248 and row['available_bytes']>=floor+679477248,'capacity floors/reserve')
    need(o['mem_available_bytes']>=16*1024**3,'memory headroom')
    need(o['launcher_phase']=='running' and o['launcher_stop_reason'] is None and type(o['included_usage_percent']) in (int,float) and 0<=o['included_usage_percent']<100,'launcher/included usage')
def publish(result):
    with OUTPUT.open('x') as f:
        os.fchmod(f.fileno(),0o644)
        json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    return ref(OUTPUT)
def main(argv=None):
    p=argparse.ArgumentParser(allow_abbrev=False)
    for flag in ('bindings-sha256','terminal','terminal-sha256'):p.add_argument('--'+flag,required=True)
    a=p.parse_args(argv);need(os.getuid()==os.geteuid()==0,'root read-only observer required')
    b=checked({'path':str(N/'fresh-snapshot-bindings.json'),'sha256':a.bindings_sha256})
    proposal,owner=static_joins(b);terminal_ref=b['physical_review'];need(terminal_ref['path']==a.terminal and terminal_ref['sha256']==a.terminal_sha256,'exact selected full terminal descriptor')
    terminal_joins(checked(terminal_ref),b)
    o=collect_live(b,proposal,owner);validate_live(o,b,owner)
    result=dict(status='PASS_LIVE_PREEXECUTION_SNAPSHOT',time_epoch=time.time(),parent_identity=b['parent_identity'],
      exclusive_heavy_accepted=True,root_mutex_snapshot_free=True,terminal_acceptance=terminal_ref,
      independent_static_execution_decision=b['static_review'],accepted_actual_stage_fixture_parent_review=b['static_review'],
      non_temporal_join_result=b['non_temporal_freeze'],boot_id=o['boot_id'],capacity=o['capacity'],
      mem_available_bytes=o['mem_available_bytes'],included_usage_percent=o['included_usage_percent'],
      heavy_profile={k:proposal['profile'][k] for k in ('cpuset','cpus','memory','memory_swap','pids','network')},
      guest_profile={'memory_mib':8192,'vcpus':4,'numa_nodes':2},released_paths_absent=list(o['released_paths_absent']),
      current_predecessor_container_absent=True,image_id=o['image_id'],cgroup=o['cgroup'])
    record=publish(result);print(json.dumps({'status':result['status'],**record}),flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
