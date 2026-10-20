"""Current CHILD failed-owner kind; source-only until its affected review/check.

The authoritative report is retained whole. Reuse the accepted bounded stable-FD,
status and flat-TAR primitives; do not translate this report into an older kind.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, stat

HELPERS = {'path': '/home/holden/mckernel-work/host-preparation/phase5-m03-prepayload-helper-export-correction-20261020-1/runtime-source-1/native_failure_physical_projection.py', 'sha256': 'ba5d3ea283eefb8f5e8249a8e703a10f4ffaeae15b8bfe4e51f379e8e6b45656'}
p = Path(HELPERS['path'])
if hashlib.sha256(p.read_bytes()).hexdigest() != HELPERS['sha256']:
    raise ValueError('accepted full FD helper source')
s = importlib.util.spec_from_file_location('accepted_child_failure_fd_helpers', p)
R = importlib.util.module_from_spec(s)
s.loader.exec_module(R)
need = R.need
CONTEXT_REF = {'path': '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/CURRENT-CHILD-FAILURE-CONTEXT.json', 'sha256': 'efded3e8c1d34026b81227c90cb6ac7f2f3eecae39c4175b6bc67f9872631253', 'size': 23702, 'device': 66306, 'inode': 48391380, 'uid': 1000, 'gid': 1000, 'mode': '0o600', 'nlink': 1, 'mtime_ns': 1792530777874282153, 'ctime_ns': 1792530777874282153}

def typed_role(source, full):
    need(set(source) == {'path', 'sha256', 'bytes', 'mode'} and set(full) == R.IDENTITY_FIELDS, 'original typed4 and actual full11 role shapes')
    need(source['path'] == full['path'] and source['sha256'] == full['sha256'] and source['bytes'] == full['size'] and stat.S_ISREG(source['mode']) and stat.S_IMODE(source['mode']) == int(full['mode'], 8), 'original typed4 identity/mode retained against genuine full11')
    return full

def census_join(c):
    need(c['host_census_supplement'] is not None, 'genuine complete current host census supplement remains unbound')
    scan = R.checked(c['host_census_supplement'])
    scope = R.checked(c['host_census_scope'])
    accepted = R.checked(c['host_census_acceptance'])
    need(accepted['schema'] == 'mckernel.independent-current-child-host-census-supplement-acceptance.v1' and accepted['status'] == 'PASS_FRESH_CURRENT_SCOPED_HOST_CENSUS_ONLY' and accepted['current_scoped_host_scan_pass'] is True, 'genuine independent actual census acceptance kind')
    need(accepted['historical_zero_claim'] is False and accepted['original4d34_modified'] is False and accepted['no_future_execution_authority'] is True, 'fresh supplement never rewrites historical authority or grants execution')
    typed_role(accepted['actual_scan'], c['host_census_supplement'])
    typed_role(accepted['immutable_saved_physical_review'], c['physical_FD'])
    typed_role(accepted['frozen_scope'], c['host_census_scope'])
    need(scan['schema'] == 'mckernel.current-child-host-census-supplement.v1' and scan['time_qualification'] == 'FRESH_CURRENT_RE_ADMISSION_ONLY_NOT_HISTORICAL', 'genuine time-qualified current census kind')
    need(scan['scope_ref'] == c['host_census_scope_compact'] and scope['schema'] == 'mckernel.child-current-physical-host-scan-scope.v1', 'complete exact mechanically derived host scope')
    typed_role(scan['physical_report'], c['physical_FD'])
    need(scan['physical_report'] == scope['physical_report'] and scan['boot_id'] == c['persistent_predecessor']['boot_id'], 'current report and observed boot join')
    actual = scan['scan']
    need(actual['method'] == 'accepted-Q6-proc-stat-host-birth-PGID-SID' and actual['complete_scan'] is True and actual['matches'] == actual['permission_denials'] == [], 'whole completed host census has no live matches or denials')
    need(actual['pid_start_tuples'] == scope['tracked_host_pid_start_tuples'] and actual['groups'] == scope['tracked_host_PGIDs'] and actual['sessions'] == scope['tracked_host_SIDs'], 'all actual tracked host birth/group/session identities')
    need(scan['counts'] == dict(tracked_host_PID_start_tuples=len(actual['pid_start_tuples']), tracked_host_PGIDs=len(actual['groups']), tracked_host_SIDs=len(actual['sessions']), live_matches=0, proc_permission_denials=0), 'complete truthful current host census counts')
    need(scan['namespace_PID_is_not_a_host_identity'] is True and scan['container_id_context_only'] == scope['current_container_id'] and scan['case_nonce_context_only'] == scope['current_nonce'], 'namespace QEMU remains distinct from host birth identities')
    need(scan['scan_started_monotonic_ns'] <= scan['scan_finished_monotonic_ns'] and scan['scan_started_utc'] <= scan['scan_finished_utc'], 'genuine observed scan interval retained')
    need(scan['permanent_mutex'] == scope['permanent_mutex'] == dict(path='/run/lock/mckernel-development.lock', device=27, inode=4, uid=0, gid=0, mode='0o644', nlink=1), 'permanent mutex exact retained identity')
    paths = [c['persistent_predecessor'][k] for k in ('lease_path', 'common_exclusion', 'shared_heavy')]
    need(set(scope['persistent_paths_to_inspect']) == set(paths) and scan['persistent_paths'] == [dict(path=path, exists=False) for path in scope['persistent_paths_to_inspect']], 'all three actual persistent paths observed absent')
    need(scan['root_operations'] == scan['workloads'] == scan['cleanup_operations'] == 0, 'census observation only')

def project(t, physical_ref):
    need(CONTEXT_REF is not None, 'genuine current CHILD context remains unbound')
    c = R.checked(CONTEXT_REF)
    need(c['schema'] == 'mckernel.current-child-failed-native-context.v1', 'exact current context kind')
    census_join(c)
    need(physical_ref == c['physical'] and t == R.checked(c['physical_FD']), 'whole genuine current report/FD')
    need(t['schema'] == 'mckernel.child-native-owner-failure-physical-retirement-review.v1' and t['status'] == 'PASS_PHYSICAL_RETIREMENT_ONLY', 'exact current failed-native kind')
    need(t['physical_acceptance'] is True and t['application_acceptance'] is False and t['implementation_ownership'] is False and t['native_protocol_status'] == 'FAIL', 'physical-only failed owner authority')
    need(t['no_runtime_retry_or_cleanup_authority'] is True, 'no retry or cleanup authority')
    release = t['ownership_release']
    need(release['absence_verified'] is True and release['lease_retained'] is False and release['new_native_persistent_owned_record_files'] == 0 and release['source_known_owner_flush_only_after_absence_and_lockrelease'] is True, 'positive ownership release')
    need(release['permanent_root_mutex'] == dict(dev=27, ino=4, uid=0, gid=0, mode=420, nlink=1), 'permanent mutex identity')
    statuses = [R.checked(r) for r in c['pipeline_statuses']]
    typed_role(t['owner_status'], c['owner_status'])
    typed_role(t['root_stop'], c['root_stop'])
    typed_role(t['original_tool_wholejoin'], c['original_tool_join'])
    typed_role(t['readback_whole'], c['readback_whole'])
    need(len(statuses) == 4 and c['pipeline_statuses'][3] == c['owner_status'] and t['owner_status'] == c['owner_status_report_descriptor'], 'complete actual pipeline roles')
    for row, rc in zip(statuses, [0, 0, 0, 1]):
        R.status_join(row, rc)
    stop = R.checked(c['root_stop'])
    need(t['root_stop'] == c['root_stop_report_descriptor'] and stop['status'] == 'STOPPED_ON_FAILED_EXACT_CALLER' and stop['owner_invoked'] is True and stop['prior_closed_zero_steps'] == [0, 1] and [(r['index'], r['returncode']) for r in stop['steps']] == [(2, 0), (3, 1)], 'truthful split current controller join')
    tool = R.checked(c['original_tool_join'])
    need(t['original_tool_wholejoin'] == c['original_tool_report_descriptor'] and tool == c['original_tool_value'], 'entire exact original tool evidence')
    need(tool['schema'] == 'mckernel.root.actual-original-tool-wholejoin.v1' and tool['whole_command_joined'] is True and tool['tool_exit_code'] == 1 and tool['whole'] == stop and tool['physical_or_semantic_acceptance'] is False, 'positive failed original tool join')
    prior = R.checked(c['prior_preparation_receipt'])
    need(tool['prior_tool']['correction_receipt'] == c['prior_preparation_receipt']['path'] and tool['prior_tool']['exit_code'] == 1 and prior == c['prior_preparation_value'], 'actual prior LAST/machine join receipt')
    atomic_status = R.checked(c['atomic_status'])
    R.status_join(atomic_status, 0)
    atomic_raw = R.captured_bytes(atomic_status['streams']['stdout'])
    need(atomic_raw == R.read_bytes(c['atomic_stdout']) and R.captured_bytes(atomic_status['streams']['stderr']) == b'', 'whole closed atomic receipt capture')
    atomic_lines = atomic_raw.splitlines(keepends=True)
    need(len(atomic_lines) == 2 and all(line.endswith(b'\n') for line in atomic_lines), 'exact two-line atomic receipt and owner identity')
    receipt = t['actual_atomic_receipt']
    need(json.loads(atomic_lines[0], object_pairs_hook=R.no_duplicates) == receipt and json.loads(atomic_lines[1], object_pairs_hook=R.no_duplicates) == t['actual_owner'], 'exact atomic owner receipt authority')
    need(receipt['status'] == 'FAIL' and receipt['absence_verified'] is True and receipt['lease_retained'] is False and receipt['secondary'] == [] and receipt['secondary_omitted'] == 0 and receipt['signal_number'] is None and receipt['application_acceptance'] is False, 'truthful failed-owner terminal receipt')
    readers = t['readers']
    need(len(readers) == len(c['reader_statuses']) == 3, 'exact three closed exports')
    raw = []
    for reported, status_ref in zip(readers, c['reader_statuses']):
        row = R.checked(status_ref)
        typed_role(reported['status'], status_ref)
        typed_role(reported['stdout'], c['reader_streams'][len(raw)])
        typed_role(reported['stderr'], c['reader_stderr'][len(raw)])
        R.status_join(row, 0)
        need(reported['closed'] is True and reported['status']['path'] == status_ref['path'] and reported['status']['sha256'] == status_ref['sha256'], 'whole current reader role')
        out = R.captured_bytes(row['streams']['stdout'])
        need(out == R.read_bytes(c['reader_streams'][len(raw)]) and R.captured_bytes(row['streams']['stderr']) == b'', 'full stable exported streams')
        raw.append(out)
    readback = R.checked(c['readback_whole'])
    need(readback['status'] == 'THREE_EXACT_READERS_RETURNED_ZERO' and [r['index'] for r in readback['records']] == [1, 2, 3] and all(r['caller_returncode'] == 0 for r in readback['records']), 'actual complete exports whole join')
    owner = R.tar_members(raw[0], c['owner_archive_regular_files'])
    attempt = R.tar_members(raw[2], c['attempt_archive_regular_files'])
    need(owner['./result.json'] == atomic_lines[0] and owner['./owner.json'] == atomic_lines[1], 'atomic whole bytes and archived receipt/owner equality')
    need(raw[1] == attempt['./result.json'], 'actual result cat/TAR byte equality')
    result = json.loads(raw[1], object_pairs_hook=R.no_duplicates)
    q = t['inner_qemu_retirement']
    need(result['qemu_evidence'] == q['actual'] and result['admitted_qemu_argv'] == q['admitted_argv'] == q['actual']['argv'] and result['cleanup'] == q['cleanup'] == dict(reaped=True, errors=[]) and result['capture_errors'] == q['capture_errors'] == [], 'actual whole QEMU birth/argv/reap/cleanup')
    need(q['actual'] == c['actual_QEMU'] and q['actual']['pid'] == q['actual']['pgid'] == q['actual']['sid'] and q['actual']['returncode'] == -9, 'genuine current namespace QEMU identity')
    transcript = attempt[q['QMP_transcript']['member']]
    need(len(transcript) == q['QMP_transcript']['bytes'] and hashlib.sha256(transcript).hexdigest() == q['QMP_transcript']['sha256'], 'whole QMP transcript authority')
    meta = json.loads(owner['./owner.json'], object_pairs_hook=R.no_duplicates)
    need(meta == t['actual_owner'] and meta['lock'] == release['permanent_root_mutex'] and meta['nonce'] == statuses[3]['argv'][statuses[3]['argv'].index('--nonce') + 1] and meta['owner_sha256'] == statuses[3]['argv'][statuses[3]['argv'].index('--owner-sha256') + 1], 'whole owner identity/source/nonce')
    clients = [(name, json.loads(value, object_pairs_hook=R.no_duplicates)) for name, value in sorted(owner.items()) if name[2:5].isdigit() and name.endswith('.json')]
    need(len(clients) == t['client_retirement']['recorded_commands'] == 25 and t['client_retirement']['all25_reaped'] is True and t['client_retirement']['failed_start_and_already_exited_kill_preserved'] is True, 'all twenty-five actual clients including truthful failures')
    source_rows = []
    for name, client in clients:
        cmd = client['command']
        need(cmd['reaped'] is True and type(cmd['returncode']) is int and cmd['returncode'] == client['returncode'] and cmd['sid'] == meta['outer']['sid'] and all(type(cmd[k]) is int and cmd[k] > 0 for k in ('pid', 'pgid', 'sid', 'proc_starttime')), 'positive full client birth/wait identity')
        source_rows.append(dict(argv=client['argv'], identity=cmd, returncode=client['returncode']))
    key = lambda row: json.dumps(row, sort_keys=True, separators=(',', ':'))
    need(sorted(source_rows, key=key) == sorted(t['client_retirement']['source_bound_records'], key=key), 'all complete reported client identity/argv/returncode rows')
    need([client for _, client in clients[-3:]] == t['container_retirement']['final_lookup_records'], 'exact final name/nonce/CID clients')
    selectors = ['name=^/' + meta['name'] + '$', 'label=mckernel.native-diagnostic.owner=' + meta['nonce'], 'id=' + receipt['container']]
    for (name, client), selector in zip(clients[-3:], selectors):
        need(client['argv'][-1] == selector and client['command']['returncode'] == 0 and owner[name[:-5] + '.stdout'] == owner[name[:-5] + '.stderr'] == b'', 'positive three exact empty final selectors')
    terminal = json.loads(owner['./021-inspect.stdout'], object_pairs_hook=R.no_duplicates)[0]
    need(terminal['Id'] == receipt['container'] == t['container_retirement']['id'] and terminal['Name'] == '/' + meta['name'] and terminal['Config']['Labels']['mckernel.native-diagnostic.owner'] == meta['nonce'] and terminal['State'] == t['container_retirement']['final_state'], 'whole exact exited container')
    need(terminal['State']['Status'] == 'exited' and terminal['State']['Running'] is False and terminal['State']['Pid'] == 0 and terminal['State']['OOMKilled'] is False, 'positive terminal container state')
    rm = json.loads(owner['./022-rm.json'], object_pairs_hook=R.no_duplicates)
    need(rm['argv'][-3:] == ['rm', '--force', receipt['container']] and rm['returncode'] == t['container_retirement']['remove_returncode'] == 0, 'exact successful container removal')
    last_data = R.checked(c['LAST_command_data'])
    native = R.checked(c['native_release'])
    metadata = R.checked(c['metadata_release'])
    bindings = R.checked(c['snapshot_bindings'])
    need(last_data['release'] == c['native_release_compact'] and bindings['static_review'] == c['metadata_release_compact'] and c['native_release_compact'] != c['metadata_release_compact'], 'distinct genuine native and metadata authority roles')
    need(native['schema'] == 'mckernel.independent-child-exact-seven-conditional-native-protocol-review.v1' and native['status'] == 'PASS_CONDITIONAL_ONE_EXACT_CHILD_NATIVE_PROTOCOL_PENDING_FETCHED_CONTROLS_FRESH_ADMISSION_AND_ROOT_GRANT' and metadata['schema'] == 'mckernel.independent-child-corrected19-conditional-source-data-profile-review.v1' and metadata['status'] == 'PASS', 'actual distinct independent release kinds remain whole')
    argv = last_data['operations'][1]['argv_template']
    need(statuses[0]['argv'] == argv and argv[argv.index('--bindings-sha256') + 1] == c['snapshot_bindings']['sha256'] and c['snapshot_source']['path'] in argv, 'complete current actual LAST argv/bindings/source')
    R.read_bytes(c['snapshot_source'])
    R.read_bytes(c['caller_source'])
    need(c['snapshot_bindings']['path'] == c['actual_control_root'] + '/ROOT-SNAPSHOT-BINDINGS.json' and bindings['root_owner_argv'] == statuses[3]['argv'], 'actual current control basename and owner argv')
    pre = bindings['physical_predecessor']
    need(pre == c['persistent_predecessor'], 'whole prior persistent predecessor identity')
    for key in ('lease_path', 'common_exclusion', 'shared_heavy'):
        need(not os.path.lexists(pre[key]), 'prior persistent path remains absent')
    return dict(boot_id=pre['boot_id'], filesystem_uuid=pre['filesystem_uuid'], container_id=receipt['container'], owner_nonce=meta['nonce'], lease_path=pre['lease_path'], common_exclusion=pre['common_exclusion'], shared_heavy=pre['shared_heavy'])
