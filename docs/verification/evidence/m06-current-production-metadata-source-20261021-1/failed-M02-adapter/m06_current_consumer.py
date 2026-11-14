"""Finite M06 source/normalization and M02 failed-predecessor consumer.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No runtime release, process, clock, census, root operation or cleanup is performed.
"""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def need(value, message):
    if not value:
        raise ValueError(message)


def tools(context):
    row = context['accepted_FD_helpers']
    need(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256'],
         'accepted FD helper source')
    return load('m06_accepted_failure_FD_helpers', row['path'])


def compact(row):
    return dict(path=row['path'], sha256=row['sha256'],
                bytes=row.get('bytes', row.get('size')))


def checked(R, row):
    value = R.checked(compact(row))
    if 'mode' in row:
        need(Path(row['path']).lstat().st_mode == row['mode'], 'typed descriptor mode')
    return value


def physical_project(t, physical_ref, context):
    """Consume the exact independently reviewed failed M02 report, never CHILD/PASS."""
    R = tools(context)
    need(compact(physical_ref) == compact(context['physical']), 'current physical reference')
    need(t == checked(R, context['physical']), 'whole genuine M02 physical report')
    need((t['schema'], t['status'], t['decision']) == (
        'mckernel.independent-actual-M02-native-failure-physical-retirement-review.v1',
        'PASS_PHYSICAL_RETIREMENT_ONLY',
        'PASS_EXACT_CURRENT_M02_FAILED_NATIVE_OWNER_CLIENT_CONTAINER_QEMU_AND_ALL_READERS_PHYSICALLY_RETIRED_ONLY'),
        'known M02 failed-native physical kind')
    need(t['physical_acceptance'] is True and t['application_acceptance'] is False and
         t['implementation_ownership'] is False and t['native_protocol_status'] == 'FAIL' and
         t['no_runtime_retry_or_cleanup_authority'] is True and t['runtime_release'] is None,
         'physical-only failed predecessor authority')
    receipt, owner = t['actual_atomic_receipt'], t['actual_owner']
    need(receipt['status'] == 'FAIL' and receipt['absence_verified'] is True and
         receipt['lease_retained'] is False and receipt['application_acceptance'] is False and
         receipt['secondary'] == [] and receipt['secondary_omitted'] == 0 and
         receipt['signal_number'] is None, 'positive failed owner atomic release')
    need(t['permanent_mutex'] == dict(path='/run/lock/mckernel-development.lock',
         device=27, inode=4, uid=0, gid=0, mode='0o644', nlink=1) and
         owner['lock'] == dict(dev=27, ino=4, uid=0, gid=0, mode=420, nlink=1),
         'permanent mutex identity')
    status = checked(R, t['owner_status'])
    R.status_join(status, 1)
    argv = status['argv']
    need(argv[argv.index('--nonce') + 1] == owner['nonce'] and
         argv[argv.index('--owner-sha256') + 1] == owner['owner_sha256'] and
         argv[argv.index('--attempt-parent') + 1] + '/attempt-' + owner['nonce'] == owner['attempt'],
         'genuine failed predecessor source/nonce/parent')
    stop = checked(R, t['root_stopped_result'])
    need(stop['schema'] == 'mckernel.root.exact-seven-stopped.v1' and
         [(r['index'], r['returncode']) for r in stop['results']] == [(0, 0), (1, 0), (2, 0), (3, 1)] and
         stop['later_rows'] == 'UNRUN_NO_AUTOMATIC_REPLAY' and
         all(r['closed_streams'] is True and r['direct_child_joined'] is True and
             r['group_absent'] is True and r['remaining'] == [] for r in stop['results']),
         'genuine stopped failed caller')
    need(t['root_original_tool_join_fact']['closed'] is True and
         t['root_original_tool_join_fact']['returncode'] == 1, 'closed original root tool')
    checked(R, t['native_release'])
    checked(R, t['preliminary_readonly_release'])
    checked(R, t['readback_grant'])
    checked(R, t['readback_whole'])
    # Every independently retained actual evidence descriptor remains authoritative.
    for row in t['evidence'].values():
        R.read_bytes(compact(row))
    need(len(t['readers']) == 3, 'three actual archive readers')
    streams = []
    for row in t['readers']:
        need(row['returncode'] == 0 and row['direct_child_joined'] is True and
             row['process_group_absent'] is True and row['observer_error'] is None,
             'closed actual archive reader')
        streams.append(R.captured_bytes(row['streams']['stdout']))
        need(R.captured_bytes(row['streams']['stderr']) == b'', 'empty archive reader stderr')
    archived_owner = R.tar_members(streams[0], 77)
    archived_attempt = R.tar_members(streams[2], 7)
    need(json.loads(archived_owner['./result.json']) == receipt and
         json.loads(archived_owner['./owner.json']) == owner,
         'whole archived atomic receipt and owner')
    need(streams[1] == archived_attempt['./result.json'], 'whole CAT/archive result equality')
    result = json.loads(streams[1])
    qemu = t['inner_QEMU_retirement']
    need(result['qemu_evidence'] == qemu['actual'] and
         result['admitted_qemu_argv'] == qemu['admitted_argv'] == qemu['actual']['argv'] and
         result['cleanup'] == qemu['cleanup'] == dict(reaped=True, errors=[]) and
         result['capture_errors'] == qemu['capture_errors'] == [], 'whole genuine QEMU retirement')
    need(qemu['actual']['pid'] == qemu['actual']['pgid'] == qemu['actual']['sid'] and
         qemu['actual']['returncode'] == -9 and qemu['namespace_PID10_is_not_hostPID10'] is True,
         'namespace QEMU birth/reap')
    transcript = archived_attempt[qemu['QMP_transcript']['member']]
    need(len(transcript) == qemu['QMP_transcript']['bytes'] and
         hashlib.sha256(transcript).hexdigest() == qemu['QMP_transcript']['sha256'],
         'whole QMP transcript')
    clients = t['client_retirement']
    need(clients['recorded_commands'] == len(clients['source_bound_records']) == 25 and
         clients['all25_reaped'] is True and clients['failedstart_and_alreadyexitedkill_preserved'] is True,
         'all25 genuine failed and successful clients preserved')
    for item in clients['source_bound_records']:
        actual = json.loads(archived_owner[item['member']])
        need(actual == item['record'], 'whole archived source-bound client record')
        command = actual['command']
        need(command['reaped'] is True and command['returncode'] == actual['returncode'] and
             command['sid'] == owner['outer']['sid'] and
             all(type(command[k]) is int and command[k] > 0
                 for k in ('pid', 'pgid', 'sid', 'proc_starttime')), 'positive client birth/reap')
    container = t['container_retirement']
    need(container['id'] == receipt['container'] and container['remove_returncode'] == 0 and
         container['final_state']['Status'] == 'exited' and
         container['final_state']['Running'] is False and container['final_state']['Pid'] == 0 and
         container['final_state']['OOMKilled'] is False, 'positive container retirement')
    for item in container['final_three_empty_exact_lookup_records']:
        need(item in [x['record'] for x in clients['source_bound_records']], 'actual final lookup client')
        member = next(x['member'] for x in clients['source_bound_records'] if x['record'] == item)
        need(item['returncode'] == 0 and archived_owner[member[:-5] + '.stdout'] ==
             archived_owner[member[:-5] + '.stderr'] == b'', 'exact empty terminal selectors')
    scan = t['fresh_current_scoped_host_scan']
    need(scan['complete_scan'] is True and scan['matches'] == scan['permission_denials'] == [] and
         scan['time_qualification'] == 'FRESH_CURRENT_ONLY_NOT_HISTORICAL' and
         scan['namespaceQEMU10_excluded'] is True and scan['unknown_outerPGIDs_not_invented'] is True,
         'retained time-qualified complete host census')
    predecessor = checked(R, context['predecessor_bindings'])['physical_predecessor']
    need(t['persistent_paths'] == [dict(path=predecessor[k], exists=False)
         for k in ('lease_path', 'common_exclusion', 'shared_heavy')], 'whole persistent path report')
    # Root's later live admission remains responsible for current absence/census.
    projected = dict(boot_id=predecessor['boot_id'], filesystem_uuid=predecessor['filesystem_uuid'],
                container_id=receipt['container'], owner_nonce=owner['nonce'],
                lease_path=predecessor['lease_path'], common_exclusion=predecessor['common_exclusion'],
                shared_heavy=predecessor['shared_heavy'])
    need(projected == context['expected_predecessor'], 'independent expected predecessor tuple')
    return projected


def project(t, physical_ref):
    context = json.loads((HERE/'CURRENT-M06-CONSUMER-CONTEXT.json').read_bytes())
    return physical_project(t, physical_ref, context)


def current_case(manifest, data):
    need(manifest['case_id'] == data['case_id'] == 'practical.process.clone3-io-unsupported',
         'current M06 case identity')
    need(manifest['payload']['oracle'] == dict(exit_code=0, stderr_hex='',
         stdout_hex='72633d2d31206572726e6f3d393520656f706e6f74737570703d31206368696c645f637265617465643d300a'),
         'unchanged current M06 oracle')


def owner_deadlines(raw):
    tree = ast.parse(raw)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'DiagnosticOwner')
    run = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'run')
    need(ast.literal_eval(run.args.kw_defaults[0]) == 360, 'normal outer360 deadline')
    inside = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_inside')
    calls = [n for n in ast.walk(inside) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and isinstance(n.func.value, ast.Name) and n.func.value.id == 'os' and n.func.attr == 'execve']
    need(len(calls) == 1 and any(isinstance(n, ast.Constant) and n.value == '300'
         for n in ast.walk(calls[0])), 'normal inner300 deadline')


def read_source(data, context):
    """Actual current M06 objects plus full actual loader/owner argv contract."""
    R = tools(context)
    need(data == checked(R, context['current_data']), 'exact genuine current M06 DATA')
    stage = checked(R, context['stage_acceptance'])
    need(stage['schema'] == 'mckernel.m06-closed-stage-output-acceptance.v1' and
         stage['decision'] == 'PASS_EXISTING_OFFLINE_STAGE_OUTPUT_AND_RECORDED_INNER_RETIREMENT_ONLY' and
         stage['blocking_stage_output_findings'] == [], 'known current M06 stage acceptance')
    accepted = checked(R, context['normalization_acceptance'])
    need(accepted['schema'] == 'mckernel.m06-actual-successor-normalization-output-acceptance.v1' and
         accepted['decision'] == 'PASS_ACTUAL_SUCCESSOR_NORMALIZATION_OUTPUT_AND_ORDINARY_RETIREMENT_ONLY' and
         accepted['native_acceptance'] is False,
         'known current M06 normalization acceptance')
    binding = checked(R, data['actual_normalization']['binding'])
    pre = checked(R, data['actual_normalization']['preflight'])
    need(accepted['actual_binding'] == binding == data['binding'] == pre['binding'],
         'whole accepted current normalization binding')
    need(pre['clocks_or_host_effects'] == pre['root_operations'] == pre['guest_runs'] == 0 and
         pre['runtime_release'] is None and pre['native_execution_release'] is None,
         'source-only no-effect preflight')
    runtime = Path(data['source_runtime_directory'])
    for row in context['runtime_sources']:
        R.read_bytes(compact(row))
    verifier = load('m06_actual_binding_verifier', runtime/'native_owner_binding.py')
    actual = verifier.verify(binding)
    for key in ('owner_argv', 'inside_owner_argv', 'container_create_argv', 'qemu_argv'):
        need(actual[key] == pre[key] == data['actual_full_argv'][key], 'current full argv: ' + key)
    owner = load('m06_actual_owner', runtime/'native_diagnostic_container_owner.py')
    _, manifest = owner.bound_manifest(binding['manifest']['path'], binding['manifest']['sha256'])
    outputs = {r['path']: r for r in stage['actual_outputs']}
    for row in (manifest['staging']['derived_initramfs'], manifest['staging']['overlay_manifest'],
                binding['manifest']):
        staged = outputs.get(row['path'])
        # The normalized manifest has a fresh pathname and unchanged complete bytes.
        if staged is None:
            need(row == binding['manifest'], 'only normalized manifest may relocate')
            staged = outputs[context['accepted_stage_manifest']['path']]
        need(staged['sha256'] == row['sha256'] and staged['identity']['st_size'] == row['size'] and
             staged['identity']['st_mode'] == row['mode'], 'actual current stage output join')
    binary, payload = stage['actual_binary'], manifest['artifacts']['payload']
    need(binary['path'] == payload['path'] and binary['sha256'] == payload['sha256'] and
         binary['identity']['st_size'] == payload['size'] and binary['identity']['st_mode'] == payload['mode'],
         'actual current accepted application join')
    st = Path(binding['attempt_parent']).lstat()
    identity = {k: getattr(st, k) for k in pre['parent_nine_field_identity']}
    need(identity == pre['parent_nine_field_identity'] == accepted['actual_parent_identity'],
         'actual current private parent full9')
    current_case(manifest, data)
    owner_deadlines((runtime/'native_diagnostic_container_owner.py').read_bytes())
    physical = checked(R, context['physical'])
    predecessor = physical_project(physical, context['physical'], context)
    return dict(binding=binding, preflight=actual, manifest=manifest,
                physical=physical, predecessor=predecessor, stage=stage,
                normalization_acceptance=accepted, native_release=None)
