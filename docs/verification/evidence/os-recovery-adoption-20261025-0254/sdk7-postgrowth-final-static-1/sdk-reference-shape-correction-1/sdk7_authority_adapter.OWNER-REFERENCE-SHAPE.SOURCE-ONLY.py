"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Pure admission metadata adapter. No owner imports, observers, grants or execution.
Historical producer retirement and latest host operation are deliberately separate.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

import sys
sys.path.insert(0, '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-sdk7-current-authority-composition-source-1')
from prepare_current_window_bindings import ORIGIN, ORIGIN_SHA
from sdk7_current_window import load_window, validate_window
from retained_sdk21_authority import validate_current
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from growth_chain_validator import current_sources, validate_growth_chain as growth_chain

PROFILE = dict(cpus='2-5', jobs=1, memory_bytes=12 * 2**30,
               memory_swap_bytes=12 * 2**30, network='none', pids=512)
MUTABLE = {'nonce', 'request_path', 'candidate_root', 'candidate_identity',
           'owner_evidence_root', 'output_parent_identity', 'input_identity',
           'basis_identity', 'backing_identity', 'boot_id'}
SCHEMA = 'mckernel.daemon7.live-admission.v1'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)
            + '\n').encode()


def bound(ref, json_value=True):
    need(set(ref) == {'path', 'bytes', 'sha256'}, 'complete evidence reference required')
    raw = Path(ref['path']).read_bytes()
    need(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'],
         'evidence bytes changed: ' + ref['path'])
    return json.loads(raw) if json_value else raw


def historical(origin, load=bound):
    """Use the unchanged validator only for A482's original SDK21 producer."""
    validate_current(load(origin['current_physical']), load(origin['SDK21_artifact_behavior']))
    source, mapping, fetched, review = [load(origin[k]) for k in
                                      ('source27', 'full11_map', 'fetched_source',
                                       'source_approval')]
    need(source['member_count'] == len(source['members']) == 27
         and source['actual11map'] == origin['full11_map']
         and source['actual_request'] == origin['request']
         and source['provider'] == origin['provider'], 'historical SOURCE27 tuple differs')
    need(review['decision'] == 'PASS_SOURCE' and review['implementation_ownership'] is False
         and review['execution_authority'] is False and review['SDK_execution_released'] is False
         and review['request_sha256'] == origin['request']['sha256']
         and review['source_map_sha256'] == origin['full11_map']['sha256']
         and review['fetched_proof_sha256'] == origin['fetched_source']['sha256']
         and review['provider_sha256'] == origin['provider']['sha256']
         and review['source_sha256'] == mapping['source_sha256'], 'source approval differs')
    need(fetched['status'] == 'PASS_ACTUAL_FETCHED_SOURCE'
         and fetched['source_archive_member_count'] == 27
         and fetched['source_manifest'] == origin['source27']
         and fetched['source_members'] == source['members']
         and fetched['fetched_commit'] == review['fetched_commit']
         and fetched['heavy_execution_release'] is False, 'fetched source proof differs')
    for member in source['members'].values():
        load(member, False)
    load(origin['provider'], False)
    for name, digest in mapping['source_sha256'].items():
        raw = Path(mapping['effective_runtime_paths'][name]).read_bytes()
        need(hashlib.sha256(raw).hexdigest() == digest, 'installed runtime source drift: ' + name)
    return mapping, review


def joined(join):
    need(join['returncode'] == 0 and all(join[k] is True for k in
         ('direct_child_joined', 'group_absent', 'closed_streams'))
         and join['error'] is None and join['retirement_error'] is None
         and join['timed_out'] is False
         and join['remaining_group_members'] == join['unexpected_group_members'] == [],
         'owned query retirement incomplete')
    need(join['captures']['stderr']['size'] == 0
         and join['captures']['stderr']['sha256'] == hashlib.sha256(b'').hexdigest(),
         'query stderr must be empty')


def fresh(clock, now, window):
    need(clock['boot_id'] == now['boot_id'] == window['boot_id'], 'mixed boot clocks')
    for field, start, end in (('wall', 'start_epoch', 'deadline_epoch'),
                              ('boot', 'start_boot', 'boot_deadline'),
                              ('monotonic', 'start_monotonic', 'monotonic_deadline')):
        a, b = clock[field], now[field]
        need(type(a) in (int, float) and type(b) in (int, float)
             and math.isfinite(a) and math.isfinite(b)
             and window[start] <= a <= b < window[end] and b - a <= 120,
             'stale/outside-window ' + field + ' observation')


def context(bundle, origin, window, now, load=bound, check_history=historical):
    """Validate root-supplied evidence and construct a non-authorizing release draft.

    The head is the parent's exact current operation-head receipt, authenticated by
    the separately supplied root admission review; a saved old cleanup is not a head.
    Existing owner admission still rechecks identities, resources and the mutex.
    """
    validate_window(window)
    need(window['deadline_epoch'] == 1793100290,
         'this adapter is fixed to the consumed 2026-10-27T11:24:50Z deadline')
    need(bundle['schema'] == SCHEMA and bundle['parent_window'] == bundle['query_window']
         and load(bundle['parent_window']) == window, 'consumed window binding differs')
    mapping, source_review = check_history(origin, load)
    adapter_raw = Path(__file__).read_bytes()
    adapter_ref = dict(path=str(Path(__file__).resolve()), bytes=len(adapter_raw),
                       sha256=hashlib.sha256(adapter_raw).hexdigest())
    mapping, source_review, _ = current_sources(bundle, origin, mapping, load, adapter_ref)
    original = load(origin['request'])
    request = load(bundle['request'])
    need(set(request) == set(original)
         and {k: v for k, v in request.items() if k not in MUTABLE}
         == {k: v for k, v in original.items() if k not in MUTABLE},
         'immutable request/compiler/input tuple changed')
    nonce = request['nonce']
    need(re.fullmatch('[0-9a-f]{32}', nonce) is not None
         and nonce != original['nonce'] and request['request_path'] == bundle['request']['path']
         and request['boot_id'] == window['boot_id'], 'fresh request nonce/path/boot required')
    parent = Path(request['output_parent_identity']['path'])
    need(parent == Path(original['output_parent_identity']['path'])
         and Path(request['candidate_root']) == parent / ('native-running-modules-candidate-' + nonce)
         and request['candidate_identity']['path'] == request['candidate_root']
         and Path(request['owner_evidence_root']) == parent / ('native-running-modules-owner-' + nonce)
         and request['input_identity']['path'] == request['input_root'],
         'fresh owner-compatible output namespace required')
    head, latest, live = [load(bundle[k]) for k in
                          ('operation_head', 'latest_operation', 'live_observation')]
    growth_chain(bundle, head, latest, request, live, window, load)
    need(latest['schema'] == 'mckernel.owned-operation-closure.v1'
         and latest['status'] == 'PASS_OWNED_OPERATION_CLOSED'
         and latest['nonce'] != nonce and latest['boot_id'] == window['boot_id']
         and all(latest[k] is True for k in
                 ('direct_child_joined', 'group_absent', 'closed_streams', 'holder_retired')),
         'latest operation positive retirement required')
    # Terminal state alone is insufficient: closure binds the actual captured result.
    terminal = load(latest['terminal'])
    need(terminal['container'] == latest['container'], 'latest terminal CID differs')
    state = terminal['state']
    need(state['Running'] is False and state['Paused'] is False
         and state['Restarting'] is False and state['Pid'] == 0,
         'latest container remains active or unknown')
    need(live['schema'] == 'mckernel.daemon7.live-environment-observation.v1'
         and live['latest_operation'] == bundle['latest_operation']
         and live['operation_head'] == bundle['operation_head']
         and live['clock']['wall'] >= latest['closed_wall']
         and live['global_mutex_rows'] == [] and live['active_records_absent'] is True
         and live['root_mutex'] == {'device': 27, 'inode': 4, 'free': True}
         and live['no_unknown_owned_operations'] is True, 'post-latest environment required')
    fresh(live['clock'], now, window)
    need(live['container_dispositions'] == latest['container_dispositions'],
         'latest retained container disposition differs')
    for item in live['container_dispositions']:
        need(item['cid'] == latest['container']
             and item['disposition'] in ('absent', 'retained_created_nonrunning')
             and item['independently_accepted'] is True, 'unreviewed retained CID')
        if item['disposition'] == 'retained_created_nonrunning':
            need(state['Status'] == 'created' and item['state'] == state,
                 'retained CID must match actual terminal created/nonrunning state')
    need(any(i['cid'] == latest['container'] for i in live['container_dispositions']),
         'latest CID disposition missing')
    return mapping, source_review, request, latest, live


def adapt(bundle, origin, window, now, load=bound, check_history=historical):
    mapping, source_review, request, latest, live = context(
        bundle, origin, window, now, load, check_history)
    nonce = request['nonce']
    review, query, join, reservation = [load(bundle[k]) for k in
        ('root_admission_review', 'query', 'query_join', 'reservation')]
    need(review['decision'] == 'PASS_DAEMON7_CURRENT_ADMISSION'
         and review['implementation_ownership'] is False and review['reviewer']
         and review['execution_release'] is False
         and review['bindings'] == {k: bundle[k] for k in
             ('request', 'parent_window', 'operation_head', 'latest_operation',
              'live_observation', 'query', 'query_join', 'reservation', 'accepted_growth_stage')}
         and review['historical_source_approval'] == origin['source_approval']
         and review['current_source_map'] == bundle['current_source_map']
         and review['current_source_review'] == bundle['current_source_review']
         and review['current_source_publication'] == bundle['current_source_publication']
         and review['growth_closure'] == bundle['growth_closure']
         and review['seven_commands'] == origin['seven_commands']
         and review['profile'] == origin['profile'] == PROFILE,
         'independent exact metadata/environment admission review required')
    need(query['schema'] == 'mckernel.daemon7.current-window-readonly-query.v1'
         and query['request'] == bundle['request']
         and query['live_observation'] == bundle['live_observation']
         and query['operation_head'] == bundle['operation_head']
         and query['accepted_growth_stage'] == bundle['accepted_growth_stage']
         and query['window'] == bundle['parent_window']
         and query['profile'] == PROFILE and query['image_id'] == request['image_id']
         and query['current_owner'] == source_review['bindings']['current_owner']
         and query['current_source_map'] == bundle['current_source_map']
         and query['current_source_review'] == bundle['current_source_review']
         and query['current_source_publication'] == bundle['current_source_publication']
         and query['target_calls'] == query['container_create_calls'] == 0
         and query['live_identity_and_resource_gates'] is True
         and query['conflict_paths_absent'] is True,
         'actual read-only query relation differs')
    fresh(query['clock'], now, window)
    need(query['clock']['wall'] >= live['clock']['wall'], 'query precedes live observation')
    joined(join)
    need(join['stdout'] == bundle['query'], 'query wholejoin stdout binding differs')
    need(join['captures']['stdout']['size'] == bundle['query']['bytes']
         and join['captures']['stdout']['sha256'] == bundle['query']['sha256'],
         'actual captured query bytes differ')
    resources = query['resources']
    need(resources['memory_available'] >= 25501368320
         and resources['host_free'] >= 16 * 2**30
         and resources['scratch_free'] >= 12 * 2**30, 'preserved capacity floor failed')
    need(reservation['status'] == 'ROOT_RESERVED_DAEMON7_SOLE_HEAVY'
         and reservation['nonce'] == nonce and reservation['request'] == bundle['request']
         and reservation['window'] == bundle['parent_window']
         and reservation['operation_head'] == bundle['operation_head']
         and reservation['profile'] == PROFILE and reservation['one_heavy'] is True
         and reservation['jobs_total'] <= 7 and reservation['host_reserve_bytes'] >= 4 * 2**30
         and reservation['expires_wall'] <= window['deadline_epoch']
         and now['wall'] < reservation['expires_wall']
         and reservation['query_capture'] == bundle['query_join']
         and reservation['capture_helper'] == origin['capture_helper']
         and reservation['actual_aggregate_memory_bytes'] <= resources['memory_available']
         - reservation['host_reserve_bytes'], 'actual root reservation/capture binding required')
    holder = reservation['owned_holder']
    need(holder['device'] == 27 and holder['inode'] == 4 and holder['pid'] > 0
         and holder['starttime'] > 0 and holder['fd'] >= 0
         and query['owned_holder'] == holder, 'actual owned holder/capture identity required')
    fresh(reservation['clock'], now, window)
    base = load(origin['pending_release_base'])
    need(base['execution_release'] is False and base['execution_review'] is None
         and base['source_sha256'] == load(origin['full11_map'])['source_sha256'],
         'historical pending base source differs')
    payload = copy.deepcopy(base)
    payload.update(nonce=nonce, request={k: bundle['request'][k] for k in ('path', 'sha256')},
                   boot_id=window['boot_id'], source_review={k: bundle['current_source_review'][k] for k in ('path', 'sha256')},
                   source_sha256=mapping['source_sha256'],
                   current_consumer_source_map=bundle['current_source_map'],
                   current_consumer_source_publication=bundle['current_source_publication'],
                   historical_source_review=origin['source_approval'],
                   physical_prerequisites=[bundle['growth_closure']],
                   fetched_source_verified=True, fetched_source_proof=origin['fetched_source'],
                   historical_sdk21_artifact=origin['SDK21_artifact_behavior'],
                   historical_sdk21_physical=origin['current_physical'],
                   current_physical=bundle['live_observation'],
                   current_live_postjoin=bundle['latest_operation'],
                   current_authority_source_proof=bundle['root_admission_review'],
                   actual_query=bundle['query'], actual_query_whole_join=bundle['query_join'],
                   parent_window=bundle['parent_window'], current_operation_head=bundle['operation_head'],
                   resource_reservation=bundle['reservation'],
                   accepted_growth_stage=bundle['accepted_growth_stage'],
                   status='PENDING_INDEPENDENT_EXECUTION_REVIEW', execution_release=False)
    return payload


def release_payload(draft):
    """Candidate bytes for independent review; not executable without that review."""
    need(draft['status'] == 'PENDING_INDEPENDENT_EXECUTION_REVIEW'
         and draft['execution_release'] is False and draft['execution_review'] is None,
         'only a freshly validated pending draft can be reviewed')
    payload = copy.deepcopy(draft)
    payload.pop('execution_review')
    payload.update(status='PASS_EXECUTION_RELEASE', execution_release=True)
    return payload


def reviewed_release(draft, review_ref, load=bound):
    payload = release_payload(draft)
    review = load(review_ref)
    need(review['decision'] == 'PASS_EXECUTION' and review['implementation_ownership'] is False
         and review['reviewer'] and review['reviewer'] != payload['author']
         and review['reviewed_release_payload_sha256'] == hashlib.sha256(canonical(payload)).hexdigest(),
         'independent exact external execution review required')
    return dict(payload, execution_review={k: review_ref[k] for k in ('path', 'sha256')})


def validate_query_release(release, bundle_ref, origin, window, adapter_sha):
    need(release['schema'] == 'mckernel.daemon7.current-window-query-release.v1'
         and release['decision'] == 'PASS_READONLY_QUERY_ONLY'
         and release['implementation_ownership'] is False and release['reviewer']
         and release['SDK_execution_released'] is False and release['execution_count'] == 1
         and release['bundle'] == bundle_ref and release['adapter_sha256'] == adapter_sha
         and release['origin_sha256'] == ORIGIN_SHA
         and release['window_id'] == window['window_id']
         and release['profile'] == origin['profile'] == PROFILE
         and release['capture_helper'] == origin['capture_helper']
         and release['current_source_map'] == bound(bundle_ref)['current_source_map']
         and release['current_source_review'] == bound(bundle_ref)['current_source_review']
         and release['current_source_publication'] == bound(bundle_ref)['current_source_publication']
         and release['growth_closure'] == bound(bundle_ref)['growth_closure']
         and release['accepted_growth_stage'] == bound(bundle_ref)['accepted_growth_stage']
         and release['aggregate_memory_GiB'] == os.environ.get('MCKERNEL_OS_MEMORY_GIB'),
         'external exact read-only query release required')


def readonly_query(bundle, bundle_ref, origin, window, now, release):
    """Same existing query operations, entered only after external source release.

    This is not a compiler runner. Imports and image inspection occur only when
    explicitly invoked later by root under its existing owned-capture authority.
    """
    validate_query_release(release, bundle_ref, origin, window,
                           hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    need(release['parent_window'] == bundle['parent_window'], 'query release window differs')
    _, _, request, _, _ = context(bundle, origin, window, now)
    holder = release['owned_holder']
    stat = Path('/proc/' + str(holder['pid']) + '/stat').read_text().rsplit(')', 1)[1].split()
    identity = os.stat('/proc/' + str(holder['pid']) + '/fd/' + str(holder['fd']))
    need(int(stat[19]) == holder['starttime']
         and (identity.st_dev, identity.st_ino) == (holder['device'], holder['inode']) == (27, 4),
         'actual owned query holder changed')
    # The exact prior query's owner APIs and image-only operation are retained.
    import importlib.util
    historical_mapping, _ = historical(origin)
    adapter_raw = Path(__file__).read_bytes()
    adapter_ref = dict(path=str(Path(__file__).resolve()), bytes=len(adapter_raw),
                       sha256=hashlib.sha256(adapter_raw).hexdigest())
    mapping, _, current_owner = current_sources(bundle, origin, historical_mapping, bound, adapter_ref)
    need(release['current_owner'] == current_owner, 'query release current owner differs')
    bound(current_owner, False)
    spec = importlib.util.spec_from_file_location('daemon7_current_142g_owner', current_owner['path'])
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    owner.validate_runtime_source_bindings(mapping['source_sha256'])
    owner.output_namespace(request)
    mount = owner.live_admission(request)
    capacity = owner.measure(request)
    conflicts = {owner.LEASE, owner.COMMON, Path(owner.shared.SHARED_HEAVY_LOCK_PATH),
                 Path(owner.image.COMMON_EXCLUSION), Path(owner.host.OPERATIONAL_EXCLUSION_PATH)}
    conflicts.update(owner.ROOT.glob('native-exact-mckernel-image-lease-*.json'))
    need(not any(os.path.lexists(p) for p in conflicts), 'active resource owner blocks query')
    evidence = Path(release['evidence_root'])
    need(evidence.name == 'daemon7-query-' + request['nonce'], 'fresh query nonce namespace')
    evidence.mkdir(mode=0o700)
    with owner.DeferredSignals() as latch:
        client = owner.ExternalDocker(evidence / 'image-inspect.log', latch, sudo=True)
        result = client.call(['image', 'inspect', request['image_id']], timeout=15)
        need(result.returncode == 0 and not client.client_retirement_unproven,
             'image inspection/client retirement failed')
        rows = json.loads(result.stdout)
        need(len(rows) == 1 and rows[0]['Id'] == request['image_id']
             and rows[0]['Architecture'] == 'amd64', 'pinned image differs')
        client.check_all_client_groups()
        need(not client.client_retirement_unproven, 'image client retirement unproven')
    clock = actual_clock()
    fresh(clock, clock, window)
    return dict(schema='mckernel.daemon7.current-window-readonly-query.v1',
                request=bundle['request'], live_observation=bundle['live_observation'],
                operation_head=bundle['operation_head'], window=bundle['parent_window'],
                accepted_growth_stage=bundle['accepted_growth_stage'],
                profile=PROFILE, image_id=rows[0]['Id'], target_calls=0, container_create_calls=0,
                current_owner=current_owner, current_source_map=bundle['current_source_map'],
                current_source_review=bundle['current_source_review'],
                current_source_publication=bundle['current_source_publication'],
                live_identity_and_resource_gates=True, conflict_paths_absent=True,
                resources=capacity, mount=mount, clock=clock, owned_holder=holder,
                group_checks=client.group_checks, SDK_execution_released=False)


def actual_clock():
    return dict(wall=time.time(), boot=time.clock_gettime(time.CLOCK_BOOTTIME),
                monotonic=time.monotonic(),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--draft-output', type=Path)
    mode.add_argument('--review-payload-output', type=Path)
    mode.add_argument('--reviewed-release-output', type=Path)
    mode.add_argument('--readonly-query-output', type=Path)
    parser.add_argument('--execution-review-ref', type=Path)
    parser.add_argument('--query-release-ref', type=Path)
    args = parser.parse_args()
    need(os.geteuid() == 0, 'root-authenticated metadata writer required')
    raw = ORIGIN.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == ORIGIN_SHA, 'fixed retained consumer changed')
    window = load_window()
    now = actual_clock()
    bundle_raw = args.bundle.read_bytes()
    bundle = json.loads(bundle_raw)
    if args.readonly_query_output:
        need(args.query_release_ref is not None and args.execution_review_ref is None,
             'external query release reference required')
        bundle_ref = dict(path=str(args.bundle), bytes=len(bundle_raw),
                          sha256=hashlib.sha256(bundle_raw).hexdigest())
        payload = readonly_query(bundle, bundle_ref, json.loads(raw), window, now,
                                 bound(json.loads(args.query_release_ref.read_bytes())))
    else:
        need(args.query_release_ref is None, 'query release applies only to read-only query')
        payload = adapt(bundle, json.loads(raw), window, now)
    output = (args.draft_output or args.review_payload_output or args.reviewed_release_output
              or args.readonly_query_output)
    if args.review_payload_output:
        payload = release_payload(payload)
    if args.reviewed_release_output:
        need(args.execution_review_ref is not None, 'external execution review reference required')
        payload = reviewed_release(payload, json.loads(args.execution_review_ref.read_bytes()))
    else:
        need(args.execution_review_ref is None, 'execution review applies only to publication')
    with output.open('xb') as stream:
        stream.write(canonical(payload))
        stream.flush()
        os.fsync(stream.fileno())
    if args.readonly_query_output:
        import sys
        sys.stdout.buffer.write(canonical(payload))


if __name__ == '__main__':
    main()
