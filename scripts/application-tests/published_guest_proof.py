#!/usr/bin/env python3
"""Join retained version2 mode2 observations; no execution or physical reads."""
import hashlib
import importlib.util
from pathlib import Path
import re
import struct


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


owner = module('published_proof_owner', 'owner_observations.py')
physical = module('published_proof_physical', 'published_physical_observations.py')
base_physical = module('published_proof_base_physical', 'physical_observations.py')
require = owner.require
U64 = (1 << 64) - 1


def u64(data, offset):
    return struct.unpack_from('<Q', data, offset)[0]


def validate(out, record, comparison, contract):
    """Validate exact retained bytes against independent native and UART sources.

    Source/image bindings, actual QMP provenance and the final independent
    guest review remain external requirements; this returns comparison only.
    """
    require(record['mode'] == 'postpublish-notify', 'mode2 only')
    out = Path(out)
    files = out / 'guest-artifacts/files/mckernel'
    inputs = []
    def read(path, cap=8 * 1024**2):
        raw, identity = owner.read_artifact(path, cap)
        inputs.append(identity)
        return raw
    def load(path):
        return owner.load_json(read(path, 1024**2))
    parsed = comparison['phase_observations']
    snapshots = [row['owner'] for row in parsed['snapshots']]
    require([row['phase'] for row in snapshots] == ['BlockedRead', 'AcceptedReturn', 'Terminal', 'TerminalPlusFive'], 'four mode2 native phases')
    key = snapshots[0]['selection']
    tid = owner.original_worker(snapshots[0])
    nonce = record['nonce']
    nonce_words = (int(nonce[:16], 16), int(nonce[16:], 16))
    control = record['control']
    require(control['first_failure'] is None and control['normal_phases_complete'] and control['ack_count'] == 4,
            'complete four-ACK host sequence')
    require(control['release_possible'] is True and control['release_ack_sequence'] == 2 and
            control['original_response_reads_allowed'] is False, 'host release ownership latch')
    captures = record['phase_captures']
    phases = ['PRE_INPUT', 'ACCEPTED_RETURN', 'POST_RET', 'QUIET']
    require(len(captures) == 4, 'unexpected phase capture count')
    manifests = []
    roots = []
    for sequence, (capture, phase) in enumerate(zip(captures, phases), 1):
        req = capture['request']
        require(req['kind'] == 'REQ' and req['sequence'] == sequence and req['phase'] == req['ack_phase'] == phase,
                'phase capture order/identity')
        require(req['nonce'] == nonce and req['mode'] == record['mode'] and
                [req['tgid'], req['tid'], req['start_ticks']] == control['identity'], 'capture original task identity')
        require(req['release_possible'] is (sequence >= 3) and req['original_response_reads_allowed'] is (sequence < 3),
                'capture release latch drift')
        target = out / ('capture-uart-%d-%s' % (sequence, phase))
        require(capture['manifest']['path'] == str(target / 'capture-manifest.json'), 'capture manifest path')
        manifest_raw = read(target / 'capture-manifest.json')
        require(hashlib.sha256(manifest_raw).hexdigest() == capture['manifest']['sha256'] and
                len(manifest_raw) == capture['manifest']['size'], 'capture manifest identity changed')
        manifest = owner.load_json(manifest_raw)
        require(manifest['request'] == req and manifest['continued'] and manifest['recovery']['resume_verified'],
                'capture stopped/resumed observation')
        require(manifest['original_response_physically_read'] is (sequence < 3), 'physical response read phase')
        require(manifest['release_possible_before_ack'] is (sequence >= 3), 'manifest ownership epoch')
        listed = [artifact['path'] for artifact in manifest['artifacts']]
        actual_paths = sorted(str(path) for path in target.iterdir() if path.name != 'capture-manifest.json')
        require(len(listed) == len(set(listed)) and sorted(listed) == actual_paths, 'exact unique capture artifact membership')
        required_names = {'control-501-send.bin', 'control-503-receive.bin', 'native-prefix.json'}
        if sequence < 3: required_names |= {'selected-response.bin', 'selected-response.json'}
        if sequence == 2: required_names.add('prepared-response-comparison.json')
        require(required_names <= {Path(path).name for path in listed}, 'critical physical evidence missing from receipt')
        for artifact in manifest['artifacts']:
            path = Path(artifact['path'])
            require(path.parent == target, 'capture artifact outside own root')
            data = read(path)
            require(len(data) == artifact['size'] and hashlib.sha256(data).hexdigest() == artifact['sha256'], 'capture artifact drift')
        manifests.append(manifest); roots.append(target)
    accepted_digest = captures[1]['manifest']['sha256']
    require(control['release_capture_sha256'] == accepted_digest, 'host ACK does not bind accepted stopped capture')
    release = parsed['published_hold']['release']
    ready = parsed['published_hold']['ready']
    require(release['capture_sha256'] == accepted_digest and release['accepted_sequence'] == release['uart_sequence'] == 2,
            'native release does not bind exact accepted ACK')
    timer, held_ns = ready['timer_seconds'], ready['held_ns']
    deadline = (timer + 5) * 1_000_000_000
    require(deadline <= U64, 'original deadline overflow')
    # Decode the complete immutable key independently of the C client's struct.
    expected_key = struct.pack('<7Q4IQ', *(key[name] for name in
        ('application', 'worker', 'delivery', 'ledger_serial', 'ledger_index', 'response', 'response_end',
         'pid', 'cpu', 'requester', 'os', 'generation')))
    result_paths = sorted(files.glob('owner-phase-???-result.json'))
    require(5 <= len(result_paths) <= 24, 'client attempt count')
    consumed_sequence = 0
    successes = []
    release_attempts = 0
    for attempt, path in enumerate(result_paths, 1):
        require(path.name == 'owner-phase-%03d-result.json' % attempt, 'client attempt gap')
        result = load(path)
        integer_fields = ('schema_version', 'phase', 'attempt', 'request_sequence', 'probe_pid', 'probe_raw_wait',
                          'begin_ns', 'observed_ns', 'probe_bytes_received', 'open_result', 'open_errno',
                          'ioctl_result', 'ioctl_errno', 'client_result')
        boolean_fields = ('application_acceptance', 'transport_acceptance', 'probe_reaped', 'timed_out',
                          'response_received', 'ioctl_called', 'request_consumed')
        owner.exact_keys(result, integer_fields + boolean_fields, 'client result schema')
        require(all(type(result[k]) is int for k in integer_fields) and all(type(result[k]) is bool for k in boolean_fields),
                'client result plain integer/boolean types')
        require(not result['application_acceptance'] and not result['transport_acceptance'], 'client cannot grant acceptance')
        stem = 'owner-phase-%03d-' % attempt
        request = read(files / (stem + 'request.bin'), 256)
        response = read(files / (stem + 'response.bin'), 256)
        probe = read(files / (stem + 'probe.bin'), 304)
        require(len(request) == len(response) == 256 and len(probe) == 304, 'complete actual ioctl/probe bytes')
        version, phase, slot, pid, generation, sequence, low, high, delivery, ledger = struct.unpack_from('<4I6Q', request)
        require(version == 2 and phase in (1, 7, 8, 2, 3) and (slot, pid, generation) == (key['os'], key['pid'], key['generation']) and
                (low, high) == nonce_words and sequence == consumed_sequence + 1, 'native ioctl request identity/sequence')
        require((delivery, ledger) == ((0, 0) if phase == 1 else (key['delivery'], key['ledger_serial'])), 'ioctl claim serials')
        require(len(successes) < 5 and phase == (1, 7, 8, 2, 3)[len(successes)], 'attempt must target next permitted operation')
        if phase == 8:
            release_attempts += 1
            require(request[64:80] == struct.pack('<2Q', 2, 2) and request[80:112] == bytes.fromhex(accepted_digest)
                    and not any(request[112:]), 'release request proof/tail')
        else:
            require(not any(request[64:]), 'nonrelease request nonzero tail')
        require(result['schema_version'] == 1 and result['phase'] == phase and result['attempt'] == attempt and
                result['request_sequence'] == sequence, 'client result identity')
        require(result['probe_reaped'] and result['probe_raw_wait'] == 0 and not result['timed_out'] and
                result['probe_bytes_received'] == 304 and result['response_received'] and result['ioctl_called'] and
                result['open_result'] >= 0 and result['open_errno'] == 0 and result['probe_pid'] > 0,
                'client actual child/ioctl collection')
        require(type(result['begin_ns']) is int and 0 < result['begin_ns'] <= result['observed_ns'] < result['begin_ns'] + 5_000_000_000,
                'client collection timestamps/deadline')
        require(response == probe[:256] and struct.unpack_from('<4i', probe, 256) ==
                tuple(result[k] for k in ('open_result', 'open_errno', 'ioctl_result', 'ioctl_errno')) and probe[276] == 1,
                'actual child probe result bytes differ')
        require(not any(probe[272:276]) and not any(probe[277:281]) and not any(probe[288:304]),
                'defined unused child probe fields changed')
        # Retain padding281..287 as opaque ABI bytes. The C language does not
        # guarantee padding remains zero after member stores, even with memset.

        require(response[:64] == request[:64], 'ioctl request echo')
        consumed = response != request
        require(result['request_consumed'] is consumed, 'consumed sequence classification')
        if consumed:
            require(u64(response, 200) == sequence, 'native consumed sequence')
            consumed_sequence = sequence
            require(response[80:160] == expected_key and u64(response, 184) == 0, 'native original key/error')
            require(result['begin_ns'] <= u64(response, 240) <= u64(response, 248) <= result['observed_ns'], 'native ioctl timestamp bracket')
        if result['client_result'] == 1:
            require(phase != 8 and result['ioctl_result'] == -1 and result['ioctl_errno'] == 11, 'only explicit EAGAIN retries')
            if consumed:
                require(u64(response, 64) == 0 and u64(response, 72) == U64 - 10, 'consumed retry snapshot/errno')
                require(phase != 1, 'SELECT cannot consume an EAGAIN retry')
                if phase == 7:
                    require(u64(response, 160) in (1, 2) and all(u64(response, offset) == 0 for offset in (168, 176, 208, 216, 224, 232)),
                            'accepted pending retry fields')
                else:
                    require(u64(response, 160) == 3 and u64(response, 168) == 2 and u64(response, 208) == timer and
                            u64(response, 216) == 1 and u64(response, 224) == held_ns and
                            u64(response, 192) == parsed['snapshots'][1]['counts']['barrier_attempts'] and
                            successes[-1]['hold_calls'] <= u64(response, 232) <= 1_000_000,
                            'released pending retry identity/timer/holds')
                    if phase == 3: require(u64(response, 176) == successes[3]['terminal_ns'], 'quiet retry changed terminal')
            continue
        require(result['client_result'] == 0 and consumed and result['ioctl_result'] == result['ioctl_errno'] == 0 and
                u64(response, 72) == 0, 'successful client/native ioctl required')
        index = len(successes)
        require(index < 5 and phase == (1, 7, 8, 2, 3)[index], 'successful ioctl phase order')
        require(u64(response, 64) == (1, 2, 2, 3, 4)[index] and u64(response, 160) == (1, 5, 3, 3, 3)[index], 'native snapshot/stage')
        if index == 0:
            require(sequence == 1 and all(u64(response, offset) == 0 for offset in (168, 176, 192, 208, 216, 224, 232)), 'selected state starts clean')
            require(read(files / 'owner-selected-response.bin', 256) == response, 'selected reply retained alias')
        else:
            require(u64(response, 168) == 2 and u64(response, 208) == timer and u64(response, 216) == 1 and
                    u64(response, 224) == held_ns and u64(response, 192) == parsed['snapshots'][1]['counts']['barrier_attempts'],
                    'original accepted timer/hold/barrier changed')
            require(u64(response, 232) <= 1_000_000, 'native hold evidence bound')
            if index < 3:
                require(held_ns <= u64(response, 240) <= u64(response, 248) < deadline and u64(response, 176) == 0,
                        'held/release deadline and terminal state')
            if index == 1:
                require(read(files / 'owner-accepted-response.bin', 256) == response, 'accepted reply retained alias')
            if index == 2:
                require(sequence == release['request_sequence'] and result['begin_ns'] <= release['begin_ns'] <= release['end_ns'] <= result['observed_ns'],
                        'native release interval/sequence differs from one ioctl')
                require(read(files / 'owner-release-response.bin', 256) == response, 'release reply retained alias')
        successes.append(dict(phase=phase, attempt=attempt, sequence=sequence, result=result,
                              snapshot=u64(response, 64), terminal_ns=u64(response, 176), hold_calls=u64(response, 232)))
    require(len(successes) == 5 and release_attempts == 1, 'complete one-shot release lifecycle')
    require(successes[3]['terminal_ns'] == successes[4]['terminal_ns'] > 0 and
            successes[4]['result']['begin_ns'] >= successes[3]['terminal_ns'] + 5_000_000_000, 'original terminal/five-second observation')
    require(all(b['hold_calls'] >= a['hold_calls'] for a, b in zip(successes, successes[1:])), 'client hold counter decreased')
    summary = load(files / 'owner-phase-summary.json')
    require(summary['attempts'] == len(result_paths) and summary['last_consumed_sequence'] == consumed_sequence and
            all(summary[name] is True for name in ('selected', 'held', 'released', 'release_possible')),
            'final client state differs from retained attempts')
    # Every response read was performed only in the stopped retained-owner era.
    bound_span = [key['response'], key['response_end']]
    bound = False
    reads = []
    require(type(record['physical_reads']) is list and len(record['physical_reads']) <= 1024, 'bounded physical read journal')
    for row in record['physical_reads']:
        require(type(row['address']) is type(row['bytes']) is int and 0 < row['address'] < row['address'] + row['bytes'] <= 256 << 30
                and 0 < row['bytes'] <= 4 << 20, 'physical read coordinate bounds')
        require(all(type(row[k]) is bool for k in ('completed', 'release_possible', 'original_overlap')), 'physical journal plain booleans')
        require(row['completed'] and 'error' not in row, 'physical read attempt failed')
        span = row['selected_span']
        if span is not None:
            require(type(span) is list and len(span) == 2 and all(type(v) is int for v in span) and span == bound_span,
                    'physical selected span binding')
            bound = True
        else:
            require(not bound and not row['release_possible'] and row['allowed_original_phase'] is None, 'physical span binding lost after selection')
        overlap = span is not None and row['address'] < span[1] and span[0] < row['address'] + row['bytes']
        require(row['original_overlap'] is overlap, 'physical overlap flag contradicts coordinates')
        if overlap:
            reads.append(row)
            require(row['allowed_original_phase'] in ('BlockedRead', 'AcceptedReturn') and not row['release_possible'] and
                    row['bytes'] == 40 and row['address'] == key['response'], 'original response read after possible transfer')
            receipt = manifests[0 if row['allowed_original_phase'] == 'BlockedRead' else 1]
            require(row['artifact'] in receipt['artifacts'], 'physical original-response read not bound into ACK receipt')
        else:
            require(row['allowed_original_phase'] is None, 'original read permission leaked into other dump')
    require(len(reads) == 2 and [r['allowed_original_phase'] for r in reads] == ['BlockedRead', 'AcceptedReturn'], 'original response read phase/count')
    for target in roots[2:]:
        require(not (target / 'selected-response.bin').exists(), 'forbidden terminal original-response artifact')
    physical_captures = []
    for target in roots:
        matches = [r for r in record['captures'] if r['directory'] == str(target)]
        require(len(matches) == 1 and matches[0]['owner'] == {'slot': key['os'], 'generation': key['generation']}, 'physical generation binding')
        physical_captures.append(matches[0])
    geometry = lambda c: [(q['port'], q['direction'], q['physical'], q['bytes']) for q in c['queues']]
    require(all(geometry(c) == geometry(physical_captures[0]) for c in physical_captures), 'physical control queue identity changed')
    delivery = next(r['row'] for r in snapshots[0]['records'] if r['kind'] == 'DELIVERY' and
                    r['application'] == key['application'] and r['row']['serial'] == key['delivery'])
    original_request = {name: delivery[name] for name in ('cpu', 'pid', 'requester', 'target', 'number', 'response', 'arguments')}
    request_binding = base_physical.locate_consumed_request(read(roots[0] / 'control-503-receive.bin', 16384), original_request)
    rings = [read(path / 'control-501-send.bin', 16384) for path in roots]
    prefix = physical.compare_prepared_response(read(roots[0] / 'selected-response.bin', 40),
                read(roots[1] / 'selected-response.bin', 40), worker_tid=tid)
    before_publication = base_physical.no_new_requester_wake(rings[0], rings[1], key['requester'])
    publication = physical.one_new_requester_wake(rings[1], rings[2], key['requester'])
    quiet = base_physical.no_new_requester_wake(rings[2], rings[3], key['requester'])
    require(owner.inventory_projection(snapshots[2]) == owner.inventory_projection(snapshots[3]), 'all retained terminal owners changed')
    require(snapshots[2]['counters'] == snapshots[3]['counters'] == contract['expected_counters']['Terminal'], 'terminal counters changed')
    return dict(status='PUBLISHED_GUEST_BYTES_AND_METADATA_MATCH_ONLY', mode=record['mode'], inputs=inputs,
                ioctl_successes=successes, attempts=len(result_paths), release_attempts=release_attempts,
                accepted_capture_sha256=accepted_digest, original_request=request_binding,
                prepared_response=prefix, before_publication=before_publication, publication=publication, quiet=quiet,
                original_response_reads=reads, application_acceptance=False, transport_acceptance=False,
                production_gate_credit=False, physical_full_ring_verified=False,
                required_external_review=['exact_compiled_sources_and_module_image_bindings', 'actual_guest_and_QMP_origin',
                                          'controller_task_and_RET_sample_provenance', 'independent_complete_fault_review'])
