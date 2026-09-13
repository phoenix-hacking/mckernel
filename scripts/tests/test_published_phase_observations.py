#!/usr/bin/env python3
"""Synthetic native hold metadata; no guest, physical reads, ioctl or acceptance."""
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
hold = load('published_phase_subject', ROOT / 'scripts/application-tests/published_phase_observations.py')
prior = load('prior_literal_phase_fixture', Path(__file__).with_name('test_phase_observations.py'))
EVIDENCE = Path(tempfile.mkdtemp(prefix='stability-published-phase-tests-'))
INDEX = itertools.count(1)
print('PUBLISHED_PHASE_TEST_EVIDENCE', EVIDENCE, flush=True)
def keep(raw, label):
    target = EVIDENCE / f'{next(INDEX):04d}-{label}.bin'
    target.write_bytes(raw)
    return target

def fixture(mode='postpublish-notify'):
    raw, contract = prior.fixture(mode)
    number = 2 if mode == 'postpublish-notify' else 3
    lines = raw.splitlines(keepends=True)
    output = []
    sequence = 0
    for line in lines:
        if b'STABILITY_PHASE_SNAPSHOT_BEGIN ' in line:
            sequence += 1
        if number == 2 and sequence >= 3:
            if b'STABILITY_OWNER_APP ' in line:
                line = line.replace(b'closed: false', b'closed: true')
            if b'domain=mailbox application=Some(7) ' in line:
                line = line.replace(b'workers_total=0 workers_emitted=0', b'workers_total=1 workers_emitted=1')
                output.append(line)
                output.append(f'ihk_smp_x86_64: STABILITY_OWNER_WORKER version=1 sequence={sequence} application=Some(7) ordinal=0 row=Worker {{ index: 4, handle: 12, tid: 102, delivery: None, completed: Some(13) }}\n'.encode())
                continue
        output.append(line)
        if b'STABILITY_FAULT_COUNTS ' in line:
            at = [1150000000,3350000000,7150000000,13150000000][sequence-1]
            output.append(f'ihk_smp_x86_64: STABILITY_HOLD_COUNTS version=1 mode={number} phase_sequence={sequence} stage={1 if sequence==1 else 4 if sequence==2 else 3} timer_present={str(sequence>1).lower()} timer_seconds={3 if sequence>1 else 0} host_hold_calls={0 if sequence<3 else 5} release_commits={int(sequence>=3)} release_attempted={str(sequence>=3).lower()} verification_errno=0 mono_ns={at}\n'.encode())
        if b'STABILITY_PHASE_SNAPSHOT_END version=1 phase_sequence=2 ' in line:
            output.append(f'ihk_smp_x86_64: STABILITY_HOLD_READY version=1 mode={number} accepted_sequence=2 nonce_low=0000000000001234 nonce_high=000000000000abcd timer_seconds=3 held_ns=3410000000 host_hold_calls=0 mono_ns=3420000000\n'.encode())
            output.append(f'ihk_smp_x86_64: STABILITY_HOLD_RELEASE version=1 mode={number} request_sequence=3 accepted_sequence=2 uart_sequence=2 nonce_low=0000000000001234 nonce_high=000000000000abcd ack_le0=0123456789abcdef ack_le1=0123456789abcdef ack_le2=0123456789abcdef ack_le3=0123456789abcdef errno=0 release_commits=1 timer_seconds=3 begin_ns=3450000000 end_ns=3460000000\n'.encode())
    result = b''.join(output)
    keep(result, 'literal-' + mode)
    (EVIDENCE / f'{next(INDEX):04d}-contract.json').write_text(json.dumps(contract, indent=2)+'\n')
    return result, contract

class PublishedPhaseTests(unittest.TestCase):
    def validate(self, raw, contract, mode='postpublish-notify'):
        path = keep(raw, 'checked')
        result = hold.validate_capture(raw, mode=mode, nonce_low=0x1234, nonce_high=0xabcd, owner_contract=contract)
        path.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
        return result
    def reject(self, raw, contract, mode='postpublish-notify'):
        with self.assertRaises(hold.ObservationError):
            self.validate(raw, contract, mode)
    def changed(self, raw, old, new):
        self.assertIn(old, raw)
        changed = raw.replace(old, new)
        self.assertNotEqual(changed, raw)
        return changed
    def test_both_modes_complete_metadata_only(self):
        for mode in ('postpublish-notify','recoverable-backpressure'):
            raw, contract = fixture(mode)
            result = self.validate(raw, contract, mode)
            self.assertEqual(result['status'], 'NATIVE_PUBLISHED_HOLD_METADATA_ONLY')
            self.assertFalse(result['application_acceptance'])
            self.assertFalse(result['transport_acceptance'])
            self.assertFalse(result['physical_accepted_return_capture_verified'])
            self.assertEqual(result['phase_observations']['published_hold']['release']['capture_sha256'], 'efcdab8967452301'*4)
    def test_blocked_and_held_prefixes(self):
        raw, _ = fixture()
        prefix = raw.split(b'ihk_smp_x86_64: STABILITY_HOLD_RELEASE',1)[0]
        keep(prefix,'held-prefix')
        result = hold.parse_envelopes(prefix,mode='postpublish-notify',nonce_low=0x1234,nonce_high=0xabcd,expect_held=True)
        self.assertEqual(len(result['snapshots']),2)
        blocked = raw.split(b'mcctrl: STABILITY_RET_ENTER',1)[0]
        keep(blocked,'blocked-prefix')
        self.assertEqual(len(hold.parse_envelopes(blocked,mode='postpublish-notify',nonce_low=0x1234,nonce_high=0xabcd)['snapshots']),1)
        with self.assertRaises(hold.ObservationError):
            hold.parse_envelopes(raw,mode='postpublish-notify',nonce_low=0x1234,nonce_high=0xabcd,expect_held=True)
    def test_missing_duplicate_and_unknown_hold_records(self):
        raw, contract = fixture()
        for marker in (b'STABILITY_HOLD_COUNTS ',b'STABILITY_HOLD_READY ',b'STABILITY_HOLD_RELEASE '):
            line=next(line for line in raw.splitlines(keepends=True) if marker in line)
            self.reject(raw.replace(line,b'',1),contract)
            self.reject(raw.replace(line,line+line,1),contract)
        self.reject(raw+b'ihk_smp_x86_64: STABILITY_HOLD_UNKNOWN version=1\n',contract)
    def test_hold_record_schema_and_native_producer(self):
        raw, contract = fixture()
        for old,new in [(b'ihk_smp_x86_64: STABILITY_HOLD_READY',b'mcctrl: STABILITY_HOLD_READY'),
                        (b'STABILITY_HOLD_READY version=1',b'STABILITY_HOLD_READY version=2'),
                        (b'timer_present=true',b'timer_present=1'),
                        (b'host_hold_calls=5',b'host_hold_calls=1000001'),
                        (b'STABILITY_HOLD_RELEASE version=1 mode=2',b'STABILITY_HOLD_RELEASE version=1 mode=3')]:
            self.reject(self.changed(raw,old,new),contract)
        self.reject(raw.replace(b'STABILITY_HOLD_READY ',b'STABILITY_HOLD_READY \x00',1),contract)
    def test_accepted_timer_and_state_cannot_change(self):
        raw, contract = fixture()
        for old,new in [(b'phase_sequence=2 stage=4',b'phase_sequence=2 stage=5'),
                        (b'timer_present=true timer_seconds=3',b'timer_present=true timer_seconds=4'),
                        (b'held_ns=3410000000',b'held_ns=3300000000'),
                        (b'accepted_sequence=2 nonce_low=0000000000001234',b'accepted_sequence=1 nonce_low=0000000000001234')]:
            self.reject(self.changed(raw,old,new),contract)
    def test_release_identity_digest_errors_and_deadline(self):
        raw, contract = fixture()
        for old,new in [(b'request_sequence=3 accepted_sequence=2',b'request_sequence=2 accepted_sequence=2'),
                        (b'uart_sequence=2',b'uart_sequence=3'),
                        (b'errno=0 release_commits=1 timer_seconds=3 begin_ns=',b'errno=-5 release_commits=1 timer_seconds=3 begin_ns='),
                        (b'begin_ns=3450000000 end_ns=3460000000',b'begin_ns=3400000000 end_ns=3460000000'),
                        (b'begin_ns=3450000000 end_ns=3460000000',b'begin_ns=3450000000 end_ns=8000000000')]:
            self.reject(self.changed(raw,old,new),contract)
        self.reject(self.changed(raw,b'0123456789abcdef',b'0000000000000000'),contract)
    def test_counts_must_stay_inside_their_envelope(self):
        raw, contract = fixture()
        line=next(line for line in raw.splitlines(keepends=True) if b'STABILITY_HOLD_COUNTS ' in line)
        self.reject(line+raw.replace(line,b'',1),contract)
        self.reject(self.changed(raw,b'mono_ns=3350000000',b'mono_ns=3500000000'),contract)
    def test_release_log_may_follow_actual_publication(self):
        raw, contract = fixture()
        line=next(line for line in raw.splitlines(keepends=True) if b'STABILITY_HOLD_RELEASE ' in line)
        modified=line.replace(b'end_ns=3460000000',b'end_ns=3700000000')
        target=next(line for line in raw.splitlines(keepends=True) if b'STABILITY_RET_LEAVE ' in line)
        raw=raw.replace(line,b'',1).replace(target,modified+target,1)
        self.validate(raw,contract)
    def test_release_log_may_follow_ret_leave(self):
        raw, contract = fixture()
        release=next(line for line in raw.splitlines(keepends=True) if b'STABILITY_HOLD_RELEASE ' in line)
        changed=release.replace(b'end_ns=3460000000',b'end_ns=6100000000')
        ret=next(line for line in raw.splitlines(keepends=True) if b'STABILITY_RET_LEAVE ' in line)
        raw=raw.replace(release,b'',1).replace(ret,ret+changed,1)
        self.validate(raw,contract)
    def test_held_local_health_including_exact_prefix(self):
        raw, _ = fixture()
        prefix=raw.split(b'ihk_smp_x86_64: STABILITY_HOLD_RELEASE',1)[0]
        rows=prefix.splitlines(keepends=True)
        for marker,field in [(b'STABILITY_OWNER_APP ',b'closed'),(b'STABILITY_OWNER_APP ',b'needs_cleanup'),(b'STABILITY_OWNER_APP ',b'quarantined'),(b'domain=mailbox application=Some(7) ',b'closed'),(b'domain=mailbox application=Some(7) ',b'quarantined')]:
            changed=[line.replace(field+b': false',field+b': true') if marker in line and b'sequence=2 ' in line else line for line in rows]
            self.assertNotEqual(rows,changed)
            keep(b''.join(changed),'local-unhealthy-held-prefix')
            with self.assertRaises(hold.ObservationError):
                hold.parse_envelopes(b''.join(changed),mode='postpublish-notify',nonce_low=0x1234,nonce_high=0xabcd,expect_held=True)
    def test_impossible_single_thread_emitting_and_ready_retries(self):
        raw, contract = fixture()
        for marker in (b'phase_sequence=2 stage=4',b'STABILITY_HOLD_READY '):
            rows=[line.replace(b'host_hold_calls=0',b'host_hold_calls=1') if marker in line else line for line in raw.splitlines(keepends=True)]
            self.reject(b''.join(rows),contract)
    def test_published_worker_and_original_app_boundaries(self):
        raw, contract = fixture()
        for old,new in [(b'delivery: None, completed: Some(13)',b'delivery: Some(13), completed: Some(13)'),
                        (b'delivery: None, completed: Some(13)',b'delivery: None, completed: Some(14)'),
                        (b'needs_cleanup: true, closed: true',b'needs_cleanup: true, closed: false')]:
            self.reject(self.changed(raw,old,new),contract)
    def test_old_barrier_and_post_release_hold_counters_are_stable(self):
        raw, contract = fixture()
        rows=raw.splitlines(keepends=True)
        changed=[line.replace(b'host_hold_calls=5',b'host_hold_calls=6') if b'STABILITY_HOLD_COUNTS ' in line and b'phase_sequence=4 ' in line else line for line in rows]
        self.reject(b''.join(changed),contract)
        changed=[line.replace(b'barrier_attempts=0',b'barrier_attempts=1').replace(b'barrier_calls=0',b'barrier_calls=1') if i>next(j for j,line in enumerate(rows) if b'STABILITY_RET_LEAVE ' in line) else line for i,line in enumerate(rows)]
        self.reject(b''.join(changed),contract)

if __name__=='__main__':
    unittest.main(verbosity=2)
