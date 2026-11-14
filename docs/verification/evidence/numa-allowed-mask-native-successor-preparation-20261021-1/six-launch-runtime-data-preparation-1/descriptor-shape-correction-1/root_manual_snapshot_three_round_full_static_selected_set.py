"""Case-specific read-only root admission recipe; no owner or guest invocation."""
from pathlib import Path
import argparse,fcntl,hashlib,importlib.util,json,os,re,stat,subprocess,time
N=Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/six-launch-runtime-data-preparation-1/source-correction-1')
PACKET=Path(__file__).resolve().parent
OUTPUT=PACKET/'root-live-preflight-1.json'
class Refusal(RuntimeError):pass
def need(ok,message):
    if not ok:raise Refusal(message)
def ref(path):return {'path':str(path),'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
def checked(record):
    p=Path(record['path']);need(p.is_absolute() and p.resolve(strict=True)==p and not p.is_symlink(),'canonical input')
    raw=p.read_bytes();need(len(raw)<=4*1024**2 and hashlib.sha256(raw).hexdigest()==record['sha256'],'input hash')
    return json.loads(raw)
def identity(p):
    s=Path(p).lstat();return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)))
def command(argv):
    p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,check=False)
    need(p.returncode==0 and p.stderr==b'' and len(p.stdout)<=4*1024**2,'bounded read-only command')
    return p.stdout.decode()
def static_joins(b):
    for record in b['source_pins']:
        need(hashlib.sha256(Path(record['path']).read_bytes()).hexdigest() == record['sha256'], 'frozen source')
    meta = checked(b['conditional_metadata']); proposal = checked(meta['proposal']); pending = checked(b['machine_pending'])
    need(meta['parent_identity'] == proposal['parent']['identity'] == b['parent_identity'] == pending['parent_identity'], 'parent static join')
    need(pending['independent_static_execution_decision'] == b['static_review'], 'static review join')
    checked(b['static_review'])
    need(proposal['profile']['mckernel_cpus'] == 2 and proposal['profile']['memory'] == proposal['profile']['memory_swap'] == 12884901888, 'fixed current two CPU batch profile')
    runtime_owner = b['runtime_owner']; path = Path(runtime_owner['path'])
    need(path == N/'native_diagnostic_container_owner.py' and hashlib.sha256(path.read_bytes()).hexdigest() == runtime_owner['sha256'], 'exact current batch owner')
    spec = importlib.util.spec_from_file_location('current_six_batch_snapshot_owner', path)
    owner = importlib.util.module_from_spec(spec); spec.loader.exec_module(owner)
    _, manifest = owner.bound_manifest(b['manifest']['path'], b['manifest']['sha256'])
    need(manifest['artifacts']['mckernel_image']['sha256'] == b['repaired_image_sha256'] and manifest['pair']['host_cpus'] == [1, 2] and manifest['pair']['cpus'] == [0, 1], 'fixed current image and two CPU authority')
    need(type(manifest.get('pair_rounds')) is int and manifest['pair_rounds'] == 3, 'fixed three sequential pair rounds; no duration knob')
    need(manifest['pair'] == b['pair_contract'], 'complete unchanged pair apps and strict oracles')
    c = checked(b['mandatory_consumer_review']); stage = checked(b['stage_review'])
    need(c['schema'] == 'mckernel.current-six-launch.actual-normalization-review.v1'
         and c['status'] == 'PASS_ACTUAL_CURRENT_SIX_LAUNCH_NORMALIZATION_ONLY'
         and c['decision'] == 'ACCEPT_EXACT_CURRENT_SIX_LAUNCH_NORMALIZATION_FOR_RUNTIME_PREPARATION'
         and c['implementation_ownership'] is False and c['runtime_release'] is False
         and isinstance(c['reviewer'], str) and c['reviewer'], 'genuine current batch normalization authority')
    need(stage['schema'] == 'mckernel.current-six-launch.actual-offline-stage-review.v1'
         and stage['status'] == 'PASS_ACTUAL_CURRENT_FOUR_MEMBER_STAGE_ONLY'
         and stage['decision'] == 'ACCEPT_MANIFEST_FOR_DOWNSTREAM_CONSUMER_PREPARATION'
         and stage['implementation_ownership'] is False and stage['runtime_release'] is False
         and isinstance(stage['reviewer'], str) and stage['reviewer'], 'genuine current four member stage authority')
    need(c['stage_acceptance'] == b['stage_review'], 'exact current stage ancestry')
    pre = checked(c['preflight']); binding = checked(c['binding'])
    need(pre['status'] == 'PASS_ACTUAL_CURRENT_SIX_LAUNCH_FULL_ARGUMENT_PREFLIGHT_ONLY', 'actual current batch full preflight')
    need(set(c['normalized_manifest']) == {'path', 'sha256', 'size', 'mode'}
         and binding['manifest'] == c['normalized_manifest'] == b['manifest'], 'complete current normalized manifest')
    source_manifest = pre['source_manifest']
    need(source_manifest['path'] == str(Path(stage['output_root'])/'manifest.json')
         and source_manifest['sha256'] == stage['files']['manifest.json']['sha256']
         and source_manifest['size'] == stage['files']['manifest.json']['bytes'], 'direct genuine stage recorder manifest shape')
    need(pre['normalized_manifest_byte_exact'] is True and pre['validated_manifest_view'] == manifest, 'whole strict loader manifest view')
    nine = {'st_dev', 'st_ino', 'st_uid', 'st_gid', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns'}
    for identity in (c['parent_nine_field_identity'], b['parent_review_identity'], pre['parent_nine_field_identity']):
        need(type(identity) is dict and set(identity) == nine and all(type(value) is int for value in identity.values()), 'complete nine exact integer parent fields')
    need(c['parent_nine_field_identity'] == b['parent_review_identity'] == pre['parent_nine_field_identity']
         and c['parent_identity'] == pre['parent_identity'] == b['parent_identity'], 'distinct complete parent identity roles')
    need(binding['nonce'] == proposal['nonce'] == pre['binding']['nonce']
         and binding['attempt_parent'] == proposal['parent']['path'] == pre['binding']['attempt_parent']
         and pre['binding']['manifest'] == b['manifest'], 'fresh parent nonce and manifest bindings')
    need(c['runtime_owner'] == runtime_owner and c['runtime_source_hashes'] == owner.SOURCE_HASHES == b['runtime_source_hashes'], 'complete actual current runtime source map')
    need(c['runtime_source_pins'] == pre['runtime_source_pins'] == b['runtime_source_pins']
         and c['runtime_source_fd_identities'] == pre['runtime_source_fd_identities'], 'normalizer source reference and full FD identities')
    owner_paths = set(owner.SOURCE_HASHES) | {owner.SELF}
    identities = c['runtime_source_fd_identities']
    need(type(identities) is dict and set(identities) == owner_paths
         and all(type(identity) is dict and set(identity) == nine
                 and all(type(value) is int for value in identity.values()) for identity in identities.values()), 'whole exact integer normalizer source FD closure')
    need(c['consumed_paths'] == pre['consumed_paths'] == b['entire_consumed_paths']
         and c['readonly_roots'] == pre['readonly_roots'] == b['readonly_roots'], 'complete actual consumed paths and readonly roots')
    need(c['root_owner_argv'] == pre['root_owner_argv'] == b['root_owner_argv'] == proposal['argv']
         and c['inside_owner_argv'] == pre['inside_owner_argv'] == b['inside_argv']
         and pre['owner_argv'] == b['accepted_owner_argv']
         and c['qemu_argv'] == pre['qemu_argv'] == b['qemu_argv'], 'whole actual owner inside and QEMU argv')
    whole = checked(c['whole'])
    need(pre['guest_runs'] == pre['root_operations'] == pre['clocks_or_host_effects'] == 0
         and whole['returncode'] == 0 and whole['direct_joined'] is True
         and whole['group_absent'] is True and whole['streams_closed'] is True
         and whole['stderr_bytes'] == 0, 'closed genuine no effect normalization capture')
    verifier_ref = b['runtime_source_fd_verifier']; verifier_path = Path(verifier_ref['path'])
    need(hashlib.sha256(verifier_path.read_bytes()).hexdigest() == verifier_ref['sha256'], 'exact qualified selected source FD verifier')
    spec = importlib.util.spec_from_file_location('qualified_current_source_fd_verifier', verifier_path)
    verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
    verifier.check_runtime_sources(dict(runtime_source_refs=b['runtime_source_refs'],
         runtime_source_fd_identity_map=b['runtime_source_fd_identity_map']))
    selected = checked(b['runtime_source_fd_identity_map'])['identities']
    selected_owner_paths = {owner.SELF, owner.RUNNER, str(N/'native_diagnostic.py'),
         str(N/'native_diagnostic_backend.py'), str(N/'qmp_capture.py'), str(N/'current_image_authority.py')}
    expected_selected = selected_owner_paths | {str(Path(__file__).resolve()), b['released_record_projection_source']['path']}
    need(set(selected) == expected_selected and len(selected) == 8
         and selected_owner_paths <= owner_paths
         and all(selected[path] == identities[path] for path in selected_owner_paths),
         'exact selected eight source FD set joins actual normalization closure')
    return proposal, owner
def same_ref(a, b, label):
    need(a['path'] == b['path'] and a['sha256'] == b['sha256'], label)

def terminal_joins(t, b):
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
      'fresh_outputs_absent':all(not os.path.lexists(PACKET/name) for name in names) and not os.path.lexists(OUTPUT),
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
    b=checked({'path':str(PACKET/'fresh-snapshot-bindings.json'),'sha256':a.bindings_sha256})
    proposal,owner=static_joins(b);terminal_ref={'path':a.terminal,'sha256':a.terminal_sha256}
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
