#!/usr/bin/env python3
"""Strict private published-hold metadata joined to unchanged native phase parser.

No physical reads, guest execution, QMP or acceptance occur in this module.
The original mode1/4 parser and all source-bound original records remain intact.
"""
import hashlib
import importlib.util
from pathlib import Path
import re

_PATH = Path(__file__).with_name('phase_observations.py')
_SPEC = importlib.util.spec_from_file_location('published_base_phases', _PATH)
base = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(base)
owner, require, ObservationError = base.owner, base.require, base.ObservationError
MODES = {'postpublish-notify': 2, 'recoverable-backpressure': 3}
SCHEMAS = {
    'HOLD_COUNTS': 'version:u32 mode:u32 phase_sequence:u64 stage:u64 timer_present:bool timer_seconds:u64 host_hold_calls:u64 release_commits:u64 release_attempted:bool verification_errno:i32 mono_ns:u64',
    'HOLD_READY': 'version:u32 mode:u32 accepted_sequence:u64 nonce_low:hex16 nonce_high:hex16 timer_seconds:u64 held_ns:u64 host_hold_calls:u64 mono_ns:u64',
    'HOLD_RELEASE': 'version:u32 mode:u32 request_sequence:u64 accepted_sequence:u64 uart_sequence:u64 nonce_low:hex16 nonce_high:hex16 ack_le0:hex16 ack_le1:hex16 ack_le2:hex16 ack_le3:hex16 errno:i32 release_commits:u64 timer_seconds:u64 begin_ns:u64 end_ns:u64',
}
HOLD_LIMIT = 1_000_000


def parse_line(text):
    require(type(text) is str and len(text) <= owner.MAX_LINE, 'hold line size/type')
    prefix = base.PREFIX.match(text)
    match = re.fullmatch(r'ihk_smp_x86_64: STABILITY_(HOLD_[A-Z_]+) (.*)', text[prefix.end():])
    require(match is not None and match[1] in SCHEMAS, 'unknown hold marker/native producer')
    row = base.Literal(match[2]).record(owner.fields(SCHEMAS[match[1]]))
    require(row['version'] == 1, 'unsupported hold record version')
    for name in ('mono_ns', 'held_ns', 'begin_ns', 'end_ns'):
        if name in row:
            require(0 < row[name] < 1 << 63, 'invalid hold native timestamp')
    if 'host_hold_calls' in row:
        require(row['host_hold_calls'] <= HOLD_LIMIT, 'hold evidence counter exceeded')
    return dict(kind=match[1], **row)


def parse_envelopes(raw, *, mode, nonce_low, nonce_high, expect_held=False):
    """Require complete native snapshots and their exact additional hold records.

    expect_held requires the two-snapshot, healthy, unattempted-release prefix
    needed for the host accepted-response capture. It is metadata only; a later
    successful original-deadline release and full physical join remain required.
    """
    require(type(mode) is str and mode in MODES and type(expect_held) is bool,
            'explicit published mode and boolean held expectation required')
    parsed = base.parse_envelopes(raw, mode=mode, nonce_low=nonce_low, nonce_high=nonce_high)
    snapshots = parsed['snapshots']
    rows = []
    for number, line in enumerate(raw.splitlines(keepends=True), 1):
        if b'STABILITY_HOLD' not in line:
            continue
        require(len(rows) < 6 and line.endswith(b'\n') and b'\x00' not in line, 'extra/truncated/NUL hold marker')
        try:
            row = parse_line(line[:-1].removesuffix(b'\r').decode('ascii'))
        except UnicodeError as error:
            raise ObservationError('non-ASCII hold record') from error
        row.update(line=number, raw_sha256=hashlib.sha256(line).hexdigest())
        require(row['mode'] == MODES[mode], 'mixed hold mode')
        rows.append(row)
    counts = [r for r in rows if r['kind'] == 'HOLD_COUNTS']
    ready = [r for r in rows if r['kind'] == 'HOLD_READY']
    releases = [r for r in rows if r['kind'] == 'HOLD_RELEASE']
    require(len(counts) == len(snapshots) and len(ready) <= 1 and len(releases) <= 1,
            'missing/duplicate hold count/ready/release')
    timer = None
    original_barrier = None
    for index, (snapshot, count) in enumerate(zip(snapshots, counts)):
        require(count['phase_sequence'] == index + 1 and count['verification_errno'] == 0,
                'hold count sequence/error')
        require(snapshot['counts']['line'] < count['line'] < snapshot['end']['line'] and
                snapshot['counts']['mono_ns'] <= count['mono_ns'] <= snapshot['end']['mono_ns'],
                'hold counts outside own fault-count/phase-end bracket')
        require(count['stage'] == (1 if index == 0 else 4 if index == 1 else 3), 'hold snapshot stage')
        require(count['release_commits'] == int(index >= 2) and count['release_attempted'] is (index >= 2),
                'hold release attempt/commit snapshot mismatch')
        if index < 2:
            key = snapshot['owner']['selection']
            apps = [r['row'] for r in snapshot['owner']['records'] if r['kind'] == 'APP' and r['row']['token'] == key['application']]
            boxes = [r['state'] for r in snapshot['owner']['records'] if r['kind'] == 'DOMAIN' and r['domain'] == 'mailbox' and r['application'] == key['application']]
            require(len(apps) == len(boxes) == 1 and not any(apps[0][k] for k in ('closed','needs_cleanup','quarantined'))
                    and not any(boxes[0][k] for k in ('closed','quarantined')), 'held original application/mailbox local health')
        if index == 0:
            require(count['timer_present'] is False and count['timer_seconds'] == count['host_hold_calls'] == 0,
                    'blocked hold already has a timer or hold calls')
        else:
            require(count['timer_present'] is True, 'missing original hold timer')
            if index == 1:
                timer = base._selected_call(snapshot['owner'])['publication_since']
                require(timer is not None and timer == count['timer_seconds'], 'hold timer differs from actual completion')
                require(timer <= owner.U64_MAX // 1_000_000_000 - 5, 'hold deadline overflow')
                require((timer + 5) * 1_000_000_000 > snapshot['end']['mono_ns'], 'accepted snapshot exceeded original deadline')
                original_barrier = snapshot['counts']['barrier_attempts']
                require(count['host_hold_calls'] == 0, 'single packet thread cannot retry while emitting accepted snapshot')
            else:
                require(count['timer_seconds'] == timer, 'original hold timer changed')
                require(snapshot['counts']['barrier_attempts'] == original_barrier, 'old barrier grew after accepted snapshot')
            require(count['host_hold_calls'] >= counts[index - 1]['host_hold_calls'], 'hold counter decreased')
    if len(snapshots) == 1:
        require(not ready and not releases, 'ready/release before accepted snapshot')
    else:
        require(len(ready) == 1, 'complete accepted phase requires exact ready event')
        event = ready[0]
        require(event['accepted_sequence'] == 2 and (event['nonce_low'], event['nonce_high']) == (nonce_low, nonce_high)
                and event['timer_seconds'] == timer, 'held ready identity/timer mismatch')
        require(snapshots[1]['end']['line'] < event['line'] and snapshots[1]['end']['mono_ns'] <= event['held_ns'] <= event['mono_ns']
                < (timer + 5) * 1_000_000_000, 'held ready order/original deadline')
        require(event['host_hold_calls'] == 0, 'single packet thread cannot retry before emitting held ready')
        if len(snapshots) >= 3:
            require(event['line'] < snapshots[2]['begin']['line'] and event['host_hold_calls'] <= counts[2]['host_hold_calls'],
                    'ready outside accepted-to-terminal/recovery interval')
    release = releases[0] if releases else None
    if release:
        require(len(snapshots) >= 2 and ready, 'release lacks held ready')
        require(release['accepted_sequence'] == release['uart_sequence'] == 2 and release['request_sequence'] >= 3,
                'release sequence space mismatch')
        require((release['nonce_low'], release['nonce_high']) == (nonce_low, nonce_high) and
                release['timer_seconds'] == timer and release['errno'] == 0 and release['release_commits'] == 1,
                'release identity/timer/error/commit')
        digest = b''.join(release['ack_le' + str(i)].to_bytes(8, 'little') for i in range(4))
        require(any(digest), 'zero native release ACK digest')
        require(ready[0]['line'] < release['line'] and ready[0]['mono_ns'] <= release['begin_ns'] <= release['end_ns']
                < (timer + 5) * 1_000_000_000, 'release order/deadline')
        # Logging/copyout follows unlock and may interleave real send/RET output.
        # Its timestamps bound the whole attempt, not the exact scalar commit.
        for event in parsed['events']:
            require(event.get('begin_ns', event.get('mono_ns', release['begin_ns'])) >= release['begin_ns'],
                    'fault event predates release attempt')
        if len(snapshots) >= 3:
            require(release['line'] < snapshots[2]['begin']['line'] and release['end_ns'] <= snapshots[2]['begin']['mono_ns'],
                    'release record after terminal/recovery snapshot')
        release = dict(release, capture_sha256=digest.hex())
    if len(snapshots) >= 3:
        require(release is not None, 'terminal/recovery lacks successful one-shot release')
    if len(snapshots) == 4:
        require(counts[2]['host_hold_calls'] == counts[3]['host_hold_calls'], 'hold changed after terminal/recovery')
    if expect_held:
        require(len(snapshots) == 2 and release is None and not parsed['events'] and len(parsed['ret_prefix']) == 2,
                'physical accepted capture no longer has an unattempted held prefix')
    parsed['published_hold'] = dict(status='NATIVE_HOLD_METADATA_ONLY', counts=counts, ready=ready[0] if ready else None,
        release=release, publication_timer_seconds=timer, expected_held_prefix=expect_held,
        physical_accepted_return_capture_verified=False, application_acceptance=False, transport_acceptance=False)
    return parsed


def _published_original_retired(snapshots, mode):
    key = snapshots[0]['owner']['selection']
    original_tid = owner.original_worker(snapshots[0]['owner'])
    for snapshot in snapshots[2:]:
        records = snapshot['owner']['records']
        require(not any(row['kind'] == 'DELIVERY' and row['application'] == key['application'] and
                        row['row']['serial'] == key['delivery'] for row in records), 'published original delivery remains')
        require(not any(row['kind'] == 'CALL' and row['owner'] is not None and
                        row['owner']['response']['serial'] == key['ledger_serial'] for row in records),
                'published original completion claim remains')
        require(not any(row['kind'] == 'TAG' and row['class'] == 'responses' and
                        row['row']['serial'] == key['ledger_serial'] for row in records),
                'published original response tag remains')
        if mode == 'postpublish-notify':
            apps = [row['row'] for row in records if row['kind'] == 'APP' and row['row']['token'] == key['application']]
            workers = [row['row'] for row in records if row['kind'] == 'WORKER' and
                       row['application'] == key['application'] and row['row']['handle'] == key['worker']]
            require(len(apps) == 1 and apps[0]['closed'] and apps[0]['quarantined'], 'notification failure original app not closed/quarantined')
            require(len(workers) == 1 and workers[0]['tid'] == original_tid and workers[0]['delivery'] is None and
                    workers[0]['completed'] == key['delivery'], 'published original worker has no matching completed delivery')


def validate_capture(raw, *, mode, nonce_low, nonce_high, owner_contract):
    held = parse_envelopes(raw, mode=mode, nonce_low=nonce_low, nonce_high=nonce_high)
    original = base.validate_capture(raw, mode=mode, nonce_low=nonce_low, nonce_high=nonce_high, owner_contract=owner_contract)
    require(len(held['snapshots']) == 4, 'complete four-phase published run required')
    _published_original_retired(held['snapshots'], mode)
    return dict(schema_version=1, status='NATIVE_PUBLISHED_HOLD_METADATA_ONLY', phase_observations=held,
                original_phase_comparison=original, physical_accepted_return_capture_verified=False,
                application_acceptance=False, transport_acceptance=False, production_gate_credit=False,
                physical_full_ring_verified=False,
                missing_external_gates=['exact_compiled_native_and_client_sources', 'held_ioctl_and_UART_ACK_digest_join',
                    'physical_blocked_to_held_prepared_prefix', 'positive_actual_publication_ring_and_no_post_release_read',
                    'QMP_resume_and_durable_capture', 'actual_RET_launcher_raw_wait_and_owned_cleanup',
                    'same_OS_eight_HELLO_provenance_for_mode3'])
