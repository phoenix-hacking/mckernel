"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root59 native lifecycle observer. Import and validate_current are data-only.
observe requires a separately reviewed new-window physical observer and guard.
"""
from pathlib import Path
import base64
import hashlib
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
PINS = {'ledger59': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER59.json', 'bytes': 20246, 'sha256': '8917629dcf0dd686c77e2531e26818c003ec43d6543786c4b4fa6e5a8cb25b53'}, 'ledger57': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER57.json', 'bytes': 18845, 'sha256': '0140dcb85e685cce3c23d7f76b50b05c092f0db4fa8b5f3e651c8467bfdf2f55'}, 'free59': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/independent-actual-native-review-1/CURRENT-FREE.json', 'bytes': 4068, 'sha256': 'f76d267e712f7906821f91576bab5d2847396eee9c19680aec6c5e0e4a7bb7a3'}, 'compose': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/actual-host-bound-source-1/root-ordinary-compose-dispatch-source-1/future-capture-1/ACTUAL-COMPOSE-RESULT.json', 'bytes': 3596, 'sha256': '2afd5f7fb1ffb3501bda6071b135e055262a681a6fa2f09f7c07eff737ba3728'}, 'observation': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/independent-actual-native-review-1/ADDITIVE-ACTUAL-NATIVE-CURRENT-FREE-OBSERVATION.json', 'bytes': 24314, 'sha256': 'f56349a46eca9371ae04d4eb555ea38177a3bac0df0f2d830f3b9aa0f6d76c81'}, 'snapshot': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/independent-actual-native-review-1/ROOT-OWNED-RETIREMENT-EVIDENCE.READONLY-SNAPSHOT.json', 'bytes': 951852, 'sha256': '743e580b3679ec28b5c1e1fe95de5f9ceef79d8443bb9fd839bb9b4b83ad26ad'}, 'entry': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/normal-entry-preclock-source-2/root-adopted-matching115-process235-entry-2/ROOT-ONCE-ENTRY.JOINED.json', 'bytes': 1678, 'sha256': '717b2dbe4a6df2f5ad79b08a8907249449866660be74e71ecab205a37428b6b0'}, 'capture': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/normal-entry-preclock-source-2/root-adopted-matching115-process235-entry-2/CAPTURE/JOINED.json', 'bytes': 233, 'sha256': 'fc73565366eb015c80cfa6c9a13e55db13f78b822a8546335c0da5bdbfd5db8b'}, 'claim': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/normal-entry-preclock-source-2/root-adopted-matching115-process235-entry-2/ROOT-ONCE-ENTRY.CLAIM.json', 'bytes': 3210, 'sha256': 'a7f29a2dc1d5a37e184a75ba016220cbc557d07cf4d91689d2c0186fbc709d1f'}, 'acceptance': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-current115-matching235-native-preparation-source-1/independent-actual-native-review-1/INDEPENDENT-ACTUAL-NATIVE-ACCEPTANCE.json', 'bytes': 5882, 'sha256': 'ef56cfbc44e4aad2639b0b702b630760a050dd9392467f4eb0972ce1b7825feb'}, 'retained_common': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/known-cid-mount-order-correction-source-1/observe_root57_known_cid_mount_order.py', 'bytes': 12952, 'sha256': 'e1b5d1b51af0c2b5d78bf23143dfdd41fadc6382bd2cdbc3fabbda388c67dc7b'}, 'mount_compare': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/known-cid-mount-order-correction-source-1/known_cid_inspect_compare.py', 'bytes': 2056, 'sha256': 'fb2dbf184ee6c4c3bd861963b72918cda3c781e1bbd47c278b993ccecf6a02a1'}}
CURRENT = dict(ledger=PINS['ledger59'], root_inputs=PINS['ledger59'],
               latest_free=PINS['free59'], ledger_key='Root59',
               compose_result=PINS['compose'])
STATUS = 'PASS_Root59_CURRENT_BOUNDARY_OBSERVATION_PENDING_ROOT_ACCEPTANCE'
NONCE = '4d1c28c2d9caa913e4ab1e8a504ac5ea'
CID = '3205b91b74d8bb5ca29f993f6c5851674f04f5446de1b324ae4636a22a07b215'
NAME = 'mckernel-native-diagnostic-' + NONCE


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def auth(row):
    require(type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}, 'typed BYTE reference')
    require(type(row['bytes']) is int and type(row['path']) is str and type(row['sha256']) is str,
            'BYTE reference field types')
    require(ref(row['path']) == row, 'BYTE authentication: ' + row['path'])
    return Path(row['path'])


def checked(row):
    return json.loads(auth(row).read_bytes())


def load(row, name):
    spec = importlib.util.spec_from_file_location(name, auth(row))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def absence_queries():
    prefix = ['/usr/bin/sudo', '-A', '/usr/bin/docker']
    return [
        (prefix + ['ps', '-aq', '--no-trunc', '--filter', 'name=^/' + NAME + '$'], 0, '', ''),
        (prefix + ['ps', '-aq', '--no-trunc', '--filter', 'label=mckernel.native-diagnostic.owner=' + NONCE], 0, '', ''),
        (prefix + ['ps', '-aq', '--no-trunc', '--filter', 'id=' + CID], 0, '', ''),
        (prefix + ['--host=unix:///var/run/docker.sock', 'inspect', CID], 1, '[]\n', 'Error: No such object: ' + CID + '\n'),
        (prefix + ['--host=unix:///var/run/docker.sock', 'ps', '-q', '--no-trunc'], 0, '', ''),
    ]


def validate_queries(rows):
    require(len(rows) == 5, 'all five native absence queries')
    for row, expected in zip(rows, absence_queries()):
        require((row['argv'], row['returncode'], row['stdout'], row['stderr']) == expected,
                'exact native CID/name/label absence query')
        require(row['positive_wait'] is True and row['streams_closed'] is True, 'query join and EOF')


def decode_snapshot(snapshot):
    require(snapshot['read_only'] is True, 'read-only owner custody snapshot')
    require(snapshot['original_owner_directory'].endswith('f02p115n1.owner-' + NONCE), 'owner custody path')
    records = {}
    for row in snapshot['files']:
        path = Path(row['path'])
        require(path.parent == Path(snapshot['original_owner_directory']), 'snapshot path containment')
        require(path.name not in records, 'snapshot file multiplicity')
        raw = base64.b64decode(row['base64'], validate=True)
        require(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'],
                'snapshot embedded BYTE authentication')
        require(row['uid'] == row['gid'] == 0, 'root owner custody')
        records[path.name] = raw
    require(len(records) == 100, 'complete retained owner snapshot')
    return records


def validate_native_bundle(ledger, free, observation, snapshot, entry, capture, claim, acceptance):
    """Pure parser; inputs come from authenticated JSON subjects in validate_current."""
    require(ledger['current_physical_clearance_pending'] is False, 'actual physical clearance adopted')
    require(ledger['consumed_nonces'][-1] == NONCE and len(ledger['consumed_nonces']) == 69,
            'native operation is last consumed nonce')
    require(NONCE not in [op['nonce'] for op in ledger['ordinary_operations_since_prior_heavy_boundary']],
            'native operation cannot be ordinary')
    native = ledger['current_native_operation']
    require(native['nonce'] == NONCE and native['actual_current_free'] == PINS['free59'] and
            native['actual_case_acceptance'] == PINS['acceptance'], 'Root native/free adoption')
    require(ledger['latest_native_once_claim'] == PINS['claim'] and
            ledger['latest_native_once_join'] == PINS['entry'] and
            ledger['latest_native_caller_join'] == PINS['capture'], 'Root native join references')
    require(free['decision'] == 'PASS_MATCHING_CURRENT115_ORIGINAL235_NORMAL_OWNER_RETIREMENT_AND_CURRENT_FREE',
            'post-native current-free decision')
    for key in ('independent', 'current_free', 'normal_owned_retirement', 'all30_owned_clients_reaped',
                'all35_host_controls_absent', 'newCID_absent',
                'permanent27_4_mutex_two_closed_probes_and_no_current_kernel_owner'):
        require(free[key] is True, 'post-native ' + key)
    require(free['implementation_ownership'] is False and free['runtime_authority'] is None,
            'independent ownership evidence only')
    require(free['nonce'] == free['newly_consumed_nonce'] == NONCE and free['actual_CID'] == CID,
            'exact native identity')
    require(free['prior_complete_consumed'] == 68 and free['proposed_successor_consumed'] == 69,
            'native count increment exactly once')
    require(free['Root57'] == PINS['ledger57'] and free['actual_current_case_ownership'] == PINS['observation']
            and free['root_owned_retirement_evidence'] == PINS['snapshot']
            and free['entry_join'] == PINS['entry'] and free['capture_join'] == PINS['capture'],
            'free custody and joins')
    require(free['pids_current'] == 0 and free['signals_cleanup_or_workloads_by_reviewer'] == 0,
            'free without reviewer cleanup')
    require(acceptance['nonce'] == NONCE and acceptance['current_free'] == PINS['free59'] and
            acceptance['entry_join'] == PINS['entry'] and acceptance['capture_join'] == PINS['capture'] and
            acceptance['conditional_once_claim'] == PINS['claim'], 'native acceptance provenance')
    require(acceptance['independent'] is True and acceptance['native_acceptance'] is True,
            'native independent acceptance')
    require(claim['nonce'] == NONCE and claim['maximum_invocations'] == 1 and
            claim['status'] == 'ONE_STARTUP_ENTRY_CLAIMED_NO_RETRY', 'spent once claim')
    require(entry['nonce'] == NONCE and entry['claim'] == PINS['claim'] and
            entry['status'] == 'NORMAL_NATIVE_HELPER_POSITIVELY_JOINED' and
            entry['direct_child_joined'] is True and entry['streams_closed'] is True and
            entry['returncode'] == 0 and entry['evidence_error'] is None, 'positive native entry join')
    require(capture['joined'] is True and capture['returncode'] == 0 and
            capture['caller_pid'] == entry['native_helper_pid'] == 1875152 and
            capture['caller_starttime'] == '96203538', 'positive native caller join')
    auth(entry['stdout']); auth(entry['stderr'])
    require(observation['case_nonce'] == NONCE and observation['container'] == CID and
            observation['name'] == NAME, 'native observation identity')
    validate_queries(observation['queries'])
    records = decode_snapshot(snapshot)
    clients = observation['actual_normal_owned_clients']
    require(len(clients) == 30 and len({r['evidence_file'] for r in clients}) == 30, 'all30 distinct native clients')
    expected_files = sorted(name for name in records if len(name) > 4 and name[:3].isdigit() and name.endswith('.json'))
    require([r['evidence_file'] for r in clients] == expected_files, 'all native commands exactly once')
    for client in clients:
        name = client['evidence_file']
        row = json.loads(records[name])
        command = client['command']
        require(row['command'] == command and row['returncode'] == client['returncode'] == command['returncode'],
                'client reaping binds original owner bytes')
        require(command['reaped'] is True and type(command['pid']) is int and
                type(command['proc_starttime']) is int and command['pgid'] == command['pid'], 'reaped exact PID/birth/group')
        require(row['failure'] is None, 'owner command completed')
        require(records[name[:-5] + '.stderr'].hex() == client['stderr_hex'], 'exact cleanup stderr retained')
    owner = json.loads(records['owner.json'])
    require(owner['nonce'] == NONCE and owner['name'] == NAME and owner['lock']['dev'] == 27 and
            owner['lock']['ino'] == 4, 'native owner permanent mutex identity')
    result = json.loads(records['result.json'])
    require(result['status'] == 'PROTOCOL_PASS' and result['absence_verified'] is True and
            result['container'] == CID and result['lease_retained'] is False and result['failure'] is None,
            'normal owner protocol retirement')
    actors = observation['actual_host_actors']
    require(len(actors) == len({a['pid'] for a in actors}) == 35, 'all35 distinct host actors')
    require(actors[0]['pid'] == owner['outer']['pid'] == 1875156 and
            actors[0]['start'] == owner['outer']['proc_starttime'] == 96203551, 'native container owner identity')
    require(actors[1]['pid'] == capture['caller_pid'] and actors[1]['start'] == int(capture['caller_starttime']), 'native caller actor')
    require([a['pid'] for a in actors[2:5]] == [1874437, 1874436, 1874406], 'operator/session/waiter controls')
    require([a['pid'] for a in actors[5:]] == [r['command']['pid'] for r in clients] and
            [a['start'] for a in actors[5:]] == [r['command']['proc_starttime'] for r in clients] and
            [a['group'] for a in actors[5:]] == [r['command']['pgid'] for r in clients], 'client actor set')
    require(observation['all_host_actor_PID_and_owned_PGRP_controls_absent'] is True and
            observation['pids_current'] == 0 and observation['signals_or_removals_by_reviewer'] == 0,
            'native host retirement without reviewer cleanup')
    require(observation['permanent_mutex'] == dict(device=27, inode=4, regular=True, no_kernel_lock_row=True),
            'permanent mutex unchanged and free')
    qmp = observation['retained_QMP_socket_artifact']
    require(qmp['expected_preserved_capture'] is True and qmp['not_inferred_live_from_path'] is True and
            qmp['host_kernel_UNIX_endpoint_rows'] == [], 'QMP artifact is retained without live endpoint')
    require(observation['container_QEMU_identity']['namespace'] == 'inside exact removed CID; not a hostPID10 absence claim',
            'container PID never reclassified as host PID')
    return actors


def validate_current(current=CURRENT):
    require(current == CURRENT, 'exact Root59/f76 current binding')
    retained = load(PINS['retained_common'], 'root59_retained_data_only')
    l53, _free115, ext, actors = retained.validate_retained53()
    ledger = checked(current['ledger']); free = checked(current['latest_free'])
    require(ledger['author'] == '/root' and ledger['complete_within_declared_current_boundary'] is True and
            ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True,
            'Root complete current boundary attestation')
    require(ledger['latest_accepted_free_boundary'] == current['latest_free'] and
            len(set(ledger['consumed_nonces'])) == 69 and ledger['consumed_nonces'][:64] == l53['consumed_nonces'],
            'complete current nonce ledger')
    operations = ledger['ordinary_operations_since_prior_heavy_boundary']
    require([op['nonce'] for op in operations] == ledger['consumed_nonces'][63:68],
            'five ordinary suffix operations followed by genuine native operation')
    for op in operations:
        checked(op['grant'])
        rows = checked(op['actual_results'])['results'] if 'actual_results' in op else [dict(join=checked(op['actual_whole_join']))]
        require(bool(rows), 'ordinary rows present')
        for row in rows:
            retained.validate_join(row['join'])
            actors.append(dict(pid=row['join']['pid'], start=row['join']['start'], role='postRoot53_ordinary_child'))
    compose = checked(current['compose_result']); retained.validate_join(checked(compose['join']))
    require(compose['status'] == 'ACTUAL_ONE_46D_COMPOSE_ZERO_JOINED_FULL_RECEIPT_NOT_NATIVE' and
            compose['nonce'] in ledger['consumed_nonces'][64:68], 'retained real227 composition')
    native_actors = validate_native_bundle(ledger, free, checked(PINS['observation']), checked(PINS['snapshot']),
                                          checked(PINS['entry']), checked(PINS['capture']), checked(PINS['claim']),
                                          checked(PINS['acceptance']))
    actors.extend(native_actors)
    return ledger, free, ext, actors


def configured_dependencies(bindings):
    require(set(bindings) == {'schema', 'author', 'observer', 'nonce_ledger',
            'account_window_guard', 'account_window_guard_configuration',
            'physical_history_observer', 'physical_history_configuration',
            'independent_dependency_review', 'runtime_authority'}, 'exact configured dependency JSON schema')
    require(bindings['schema'] == 'mckernel.configured-root59-observer-dependencies.v1' and
            bindings['runtime_authority'] is None and bindings['author'] == '/root' and
            bindings['observer'] == ref(__file__) and bindings['nonce_ledger'] == CURRENT['ledger'],
            'Root exact configured runtime dependencies')
    review = checked(bindings['independent_dependency_review'])
    require(review['independent'] is True and review['implementation_ownership'] is False and
            review['decision'] == 'PASS_EXACT_ROOT59_CONFIGURED_NEW_WINDOW_OBSERVER_DEPENDENCIES' and
            review['reviewed_observer'] == ref(__file__), 'independent configured dependency review')
    for key in ['account_window_guard', 'account_window_guard_configuration',
                'physical_history_observer', 'physical_history_configuration']:
        require(review['reviewed_' + key] == bindings[key], 'exact reviewed source/config: ' + key)
        auth(bindings[key])
    guard = load(bindings['account_window_guard'], 'root59_configured_new_window_guard')
    guard.configure(bindings['account_window_guard_configuration'])
    physical = load(bindings['physical_history_observer'], 'root59_configured_physical_history')
    physical.configure(bindings['physical_history_configuration'])
    return guard, physical


def observe():
    """Root-only live observation; does not create a grant or execute an application."""
    require(os.getuid() == os.geteuid() == 1000, 'unprivileged reviewed observer profile')
    ledger, free, ext, actors = validate_current()
    bindings = json.loads((HERE / 'ROOT-ACTUAL-RUNTIME-DEPENDENCIES.json').read_bytes())
    guard, physical = configured_dependencies(bindings)
    first = guard.guard()
    history = physical.observe()
    census = history['group_membership_observation']
    require(not census['errors'], 'complete current process census')
    for actor in actors:
        require(not Path('/proc', str(actor['pid'])).exists(), 'retired host PID remains absent')
        group = actor.get('group') or actor['pid']
        require(not any(r['pid'] == actor['pid'] or r['pgrp'] == group for r in census['rows']), 'retired host process group remains absent')
    require(not Path('/proc/1849845/fd/3').exists(), 'retired CURRENT115 holder FD absent')
    compare = load(PINS['mount_compare'], 'root59_preserved_full_record_mount_compare')
    old_queries = []
    for expected in ext['exact_CID_queries']:
        q = subprocess.run(expected['argv'], capture_output=True, text=True, timeout=15)
        compare.compare(expected, q.returncode, q.stdout, q.stderr)
        old_queries.append(dict(argv=expected['argv'], returncode=q.returncode, stdout=q.stdout, stderr=q.stderr,
                                positive_wait=True, streams_closed=True))
    native_queries = []
    for argv, rc, stdout, stderr in absence_queries():
        q = subprocess.run(argv, capture_output=True, text=True, timeout=15)
        require((q.returncode, q.stdout, q.stderr) == (rc, stdout, stderr), 'current exact native CID absence')
        native_queries.append(dict(argv=argv, returncode=q.returncode, stdout=q.stdout, stderr=q.stderr,
                                   positive_wait=True, streams_closed=True))
    qmp = checked(PINS['observation'])['retained_QMP_socket_artifact']['path']
    unix_rows = Path('/proc/net/unix').read_text().splitlines()[1:]
    require(not any(line.split()[-1] == qmp for line in unix_rows if line.split()), 'retained QMP path has no live UNIX endpoint')
    require(len(history['closed_exclusive_probes']) == 2 and history['pids_current'] == 0 and
            history['no_existing_heavy'] is True, 'current custody remains free')
    last = guard.guard()
    require(all(a < b for a, b in zip(last, guard.current_cutoffs())), 'new-window final cutoffs')
    result = dict(history)
    result.update(status=STATUS, scope=__doc__.splitlines()[0], runtime_authority=None,
                  Root59=CURRENT['ledger'], current_boundary=CURRENT['root_inputs'],
                  actual_latest_operation_postjoin_acceptance=CURRENT['latest_free'],
                  observed_clocks=first, last_observed_clocks=last, fixed_cutoffs=list(guard.current_cutoffs()),
                  boot_id=guard.BOOT, new_exact_actors=actors,
                  known_numeric_controls_absent=sorted(set(history['known_numeric_controls_absent'] + [a['pid'] for a in actors])),
                  current115_exact_CID_queries=old_queries, native_exact_CID_queries=native_queries,
                  native_lifecycle=dict(nonce=NONCE, container=CID, current_free=PINS['free59'],
                                        custody=PINS['snapshot'], retirement=PINS['observation'],
                                        entry_join=PINS['entry'], caller_join=PINS['capture'],
                                        clients_reaped=30, host_controls_absent=35),
                  historical_physical_reobservation=history, native_acceptance=False, artifact_acceptance=False)
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--validate-retained-only', action='store_true')
    args = parser.parse_args()
    if args.validate_retained_only:
        ledger, free, ext, actors = validate_current()
        print(json.dumps(dict(status='PASS_RETAINED_ROOT59_NATIVE_LIFECYCLE_SOURCE_ONLY', runtime_authority=None,
                              consumed_nonces=len(ledger['consumed_nonces']), native_nonce=NONCE,
                              current_free=CURRENT['latest_free'], actor_controls=len(actors)), indent=2))
    else:
        print(json.dumps(observe(), indent=2))
