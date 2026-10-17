#!/usr/bin/env python3
"""Scratch22 authority2 preparation with exact actual retirement evidence joins.

The caller supplies an independently reviewed release's exact SHA-256; this
module never guesses a target from HEAD or transfers scratch21 authority.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import os
import stat
import subprocess
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANCESTOR = ROOT / 'docs/verification/evidence/native-exact-candidate-delta-preparation-scratch18-20261001.py'
spec = importlib.util.spec_from_file_location('_scratch22_authority3_private_ancestor', ANCESTOR)
_IMPL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_IMPL)
Refusal = _IMPL.Refusal
NAMES = {
    'CANDIDATE_NAME': 'mckernel-exact-candidate-scratch-22-authority3',
    'MANIFEST_NAME': 'native-exact-inputs-scratch-22-authority3.json',
    'REQUEST_NAME': 'native-exact-delta-request-scratch-22-authority3.json',
    'LOG_NAME': 'native-exact-candidate-delta-preparation-scratch-22-authority3.log',
    'TERMINAL_NAME': 'native-exact-candidate-delta-preparation-scratch-22-authority3-terminal.json',
    'LEASE_NAME': 'native-exact-build-lease-scratch-22-authority3.json',
    # This is the owner's ABI slot, not the new attempt's namespace.
    'EXCLUSION_NAME': 'native-exact-candidate-operational-exclusion-scratch18.json',
    'INTERMEDIATE_CANDIDATE_NAME': 'mckernel-exact-candidate-ddb8d7d5-scratch-16',
    'PREVIOUS_CANDIDATE_NAME': 'mckernel-exact-candidate-scratch-18',
}
ALIASES = (
    'mckernel-exact-candidate-1e95abdc-scratch-15',
    'mckernel-exact-candidate-ddb8d7d5-scratch-16',
    'mckernel-exact-candidate-scratch-18',
    'mckernel-exact-candidate-50b08432-scratch-17',
    'mckernel-exact-candidate-scratch-20',
    'mckernel-exact-candidate-scratch-21',
    'mckernel-exact-candidate-scratch-22',
    'mckernel-exact-candidate-scratch-22-authority1',
    'mckernel-exact-candidate-scratch-22-authority2',
)
SOURCE_BASE = '1e95abdc2b124c19f16b88cdb21600c768a10c2d'
OWNER = 'scripts/native_rust_exact_build_container_owner.py'
ACTIVE_EXCLUSION = '/home/holden/mckernel-work/scratch/' + NAMES['EXCLUSION_NAME']
SCRATCH_UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
SCRATCH21_CONTAINER = 'e1f6dd145149c026c46adb82c3f3addb9e3c9e2a12b0d71a6813f00895220ea9'
AUTHORITY_FILES = frozenset({
    'scripts/native_exact_historical_lease_observer.py',
    'scripts/native_rust_exact_disk_build_wrapper.py',
    'scripts/tests/test_native_exact_historical_lease_observer.py',
    'scripts/tests/test_native_rust_exact_disk_build_wrapper.py',
})
AUTHORITY_AUTHOR_RECORD = 'docs/verification/evidence/historical-lease-authority-repair-20261017.json'
REPAIR_FILES = frozenset({
    'host-kernel/native-rust/ihk_smp_x86_64.rs',
    'scripts/tests/fixtures/shutdown_v6_provider.rs',
    'host-kernel/kbuild/stage-manifest.json',
    'scripts/rocky_rust_staging.py',
    'host-kernel/native-rust/ihk-mapping-foundation-contract-v1.json',
    'host-kernel/contracts/native-rust-unsafe-ffi-ledger-v1.json',
})
COMPANION_FILES = REPAIR_FILES - {
    'host-kernel/native-rust/ihk_smp_x86_64.rs',
    'scripts/tests/fixtures/shutdown_v6_provider.rs',
}
AUTHORITY2_CONTAINER = '63c2d2570315c693bc06befaa37d1408ded53896b35d13d80bc4d7b9ecdba9cb'
AUTHORITY2_REQUEST = Path('/home/holden/mckernel-work/scratch/native-exact-build-request-scratch-22-authority2.execution.json')
AUTHORITY2_REQUEST_SHA256 = 'c38fdd289b8f688a92449b0d68c2216412f10c3bc7ceedf563246ef8086cb565'
REPAIR_REPLACEMENTS = {
    'host-kernel/native-rust/ihk_smp_x86_64.rs': (
        b'fn shutdown_v6_post_effect(error: kernel::Error) -> i64 {',
        b'fn shutdown_v6_post_effect(error: kernel::error::Error) -> i64 {'),
    'scripts/tests/fixtures/shutdown_v6_provider.rs': (
        b'mod kernel { pub type Error = i32; }',
        b'mod kernel {\n'
        b'    pub mod error { pub type Error = i32; }\n'
        b'    // Historical mutation driver names kernel::Error in its replacement text.\n'
        b'    // The separate target-export regression deliberately provides no root alias.\n'
        b'    pub type Error = error::Error;\n}'),
}
RECOVERY_PROFILE = ROOT / 'docs/verification/evidence/scratch22-authority1-root-quarantine-recovery-independent-review-20261017.json'
RECOVERY_PROFILE_SHA256 = 'be4ea78f63872e69f9f1463d0587a9d6ebe6eeab5fbec923588101c5c89e4a19'
RECOVERY_ORIGINAL_FAILURE_SHA256 = {
    '/home/holden/mckernel-work/scratch/scratch22-authority1-quarantine-recovery-execution-20261017.stderr':
        'a5b9268da8ce645636691b72c2b5848acbaf6611ec244b669da63bcbcd9ec006',
    '/home/holden/mckernel-work/scratch/native-exact-scratch22-authority1-quarantine-recovery-20261017.before1.process.json':
        '921f27731a6fd4d554b83f6f9b3001f5f465677f3bb317ae9bf41544d6a4da2d',
    '/home/holden/mckernel-work/scratch/scratch22-authority1-recovery-environment-inspect-20261017.json':
        '5fb9f8983ca81c5857203e7d6ac290af5a81e9aa74392b1f3d79c1dd267d770f',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refusal('duplicate authority JSON key')
        result[key] = value
    return result


def bound_json(path, checksum):
    """Read an immutable, externally digest-bound regular authority record."""
    if not isinstance(checksum, str) or len(checksum) != 64 or any(
            c not in '0123456789abcdef' for c in checksum):
        raise Refusal('external authority SHA-256 required')
    path = Path(path)
    before = _IMPL.snapshot(path)
    raw = path.read_bytes()
    if before != _IMPL.snapshot(path) or hashlib.sha256(raw).hexdigest() != checksum:
        raise Refusal('authority digest/race mismatch')
    record = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(record, dict):
        raise Refusal('authority object required')
    return record


def validate_source_authority(source, release):
    """Retain immutable RS011 baseline; allow only the exact reviewed repair."""
    repair = validate_repair_review(source, release)
    authority = release['source_checks']
    record = bound_json(authority['path'], authority['sha256'])
    if record.get('status') != 'PASS_SOURCE_CHECKS_ONLY':
        raise Refusal('accepted source checks required')
    checks = record.get('source_checks', [])
    if len(checks) < 5 or any(row.get('exit_code') != 0 for row in checks):
        raise Refusal('ordered source checks incomplete')
    expected_checks = ('native_rust_build_surface_audit.py', 'rocky_rust_staging.py',
                       'ihk_native_lifecycle_check.py', 'native_rust_unsafe_ffi_ledger.py',
                       'scripts.tests.test_native_rust_unsafe_ffi_ledger')
    for row, expected in zip(checks, expected_checks):
        command = row.get('command', '')
        command = ' '.join(command) if isinstance(command, list) else command
        if not isinstance(command, str) or expected not in command:
            raise Refusal('ordered source check command mismatch')
    files = record.get('files', [])
    if not files:
        raise Refusal('source checks missing exact file identities')
    for row in files:
        rel = row['path']
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise Refusal('nonrelative source authority path')
        baseline = _IMPL.git(source, 'show', release['baseline'] + ':' + rel)
        if hashlib.sha256(baseline).hexdigest() != row['sha256']:
            raise Refusal('immutable RS011 baseline blob mismatch: ' + rel)
        target = _IMPL.git(source, 'show', release['target'] + ':' + rel)
        expected = repair['files_sha256_delta'][rel]['target_sha256'] if rel in REPAIR_FILES else row['sha256']
        if hashlib.sha256(target).hexdigest() != expected:
            raise Refusal('source authority target blob mismatch: ' + rel)
    pointer = release['source_review']
    review = bound_json(pointer['path'], pointer['sha256'])
    if review.get('decision') != 'PASS_SOURCE_AUTHORITY':
        raise Refusal('independent source authority review required')
    author_record = review.get('author_record', {})
    if any(author_record.get(key) != authority[key] for key in ('path', 'sha256')):
        raise Refusal('source review author record mismatch')
    if any(review.get('files_sha256', {}).get(row['path']) != row['sha256'] for row in files):
        raise Refusal('source review file bindings mismatch')


def validate_repair_review(source, release):
    """Exactly two type paths and four reviewed metadata companions."""
    pointer = release['repair_review']
    review = bound_json(pointer['path'], pointer['sha256'])
    if (review.get('schema') != 'mckernel.s22-digest-companion-independent-review.v1' or
            review.get('decision') != 'PASS_MINIMAL_SOURCE_REPAIR' or
            review.get('implementation_ownership') is not False or
            not review.get('reviewer') or not review.get('implementation_author') or
            review['reviewer'] == review['implementation_author'] or
            review.get('baseline_candidate') != release['baseline'] or
            any(review.get(key) != release[key] for key in ('target', 'target_tree')) or
            set(review.get('files_sha256_delta', {})) != REPAIR_FILES):
        raise Refusal('independent exact six-file source companion review required')
    for field, original in (('source_checks_baseline', 'source_checks'), ('source_review_baseline', 'source_review')):
        if any(review.get(field, {}).get(key) != release[original][key] for key in ('path', 'sha256')):
            raise Refusal('minimal repair review immutable source baseline binding differs')
    if review.get('current_source_checks') != release['current_source_checks']:
        raise Refusal('current source-check review binding differs')
    delta = release.get('exact_delta', [])
    if (len(delta) != 6 or {tuple(row[:2]) for row in delta} != {('M', rel) for rel in REPAIR_FILES} or
            any(len(row) != 3 for row in delta)):
        raise Refusal('authority3 target must contain only the six reviewed modifications')
    for rel in REPAIR_FILES:
        before = _IMPL.git(source, 'show', release['baseline'] + ':' + rel)
        after = _IMPL.git(source, 'show', release['target'] + ':' + rel)
        if (hashlib.sha256(before).hexdigest() != review['files_sha256_delta'][rel]['baseline_sha256'] or
                hashlib.sha256(after).hexdigest() != review['files_sha256_delta'][rel]['target_sha256']):
            raise Refusal('authority3 exact bounded repair source differs: ' + rel)
        if rel in REPAIR_REPLACEMENTS:
            old, new = REPAIR_REPLACEMENTS[rel]
            if before.count(old) != 1 or before.replace(old, new, 1) != after:
                raise Refusal('authority3 original literal repair changed: ' + rel)
    validate_current_source_checks(release, review)
    return review


def validate_current_source_checks(release, review):
    pointer = release['current_source_checks']
    record = bound_json(pointer['path'], pointer['sha256'])
    if (record.get('schema') != 'mckernel.s22-digest-companion.v1' or
            record.get('status') != 'PASS_SOURCE_COMPANION_BINDINGS'):
        raise Refusal('actual current companion source checks required')
    checks = record.get('checks', [])
    expected = ('native_rust_build_surface_audit.py', 'rocky_rust_staging.py',
                'ihk_native_lifecycle_check.py', 'native_rust_unsafe_ffi_ledger.py',
                'scripts.tests.test_native_rust_unsafe_ffi_ledger')
    if len(checks) != 5:
        raise Refusal('exact five current source checks required')
    for row, command_part in zip(checks, expected):
        command = row.get('command', '')
        command = ' '.join(command) if isinstance(command, list) else command
        if row.get('exit_code') != 0 or not isinstance(command, str) or command_part not in command:
            raise Refusal('current ordered source check failed or differs')
    hashes = record.get('current_files_sha256', {})
    if (set(hashes) != COMPANION_FILES or any(
            hashes[rel] != review['files_sha256_delta'][rel]['target_sha256'] for rel in COMPANION_FILES)):
        raise Refusal('current companion check target hash map differs')


def validate_authority1_retirement(release):
    """Consume actual producer results and independent postflights, never drafts."""
    recovery_pointer = release['authority1_recovery']
    recovery = bound_json(recovery_pointer['path'], recovery_pointer['sha256'])
    pointer = release['authority1_recovery_review']
    review = bound_json(pointer['path'], pointer['sha256'])
    require_retirement_review(review, 'scratch22-authority1.quarantine-recovery-postflight-review.v1',
                              'PASS_PROCESS_RECOVERY_POSTFLIGHT')
    if review.get('result') != recovery_pointer:
        raise Refusal('authority1 recovery postflight result differs')
    recovery_release = bound_json(review['release']['path'], review['release']['sha256'])
    prepared = bound_json(review['prepared']['path'], review['prepared']['sha256'])
    profile = bound_json(RECOVERY_PROFILE, RECOVERY_PROFILE_SHA256)
    if (recovery.get('schema') != 'scratch22-authority1.quarantine-recovery-complete.v1' or
            recovery.get('status') != 'COMPLETE_PROCESS_RECOVERY' or
            recovery.get('build_status') != 'FAIL' or recovery.get('cleanup_required') is not True or
            recovery.get('acceptance_credit') is not False or
            recovery.get('profile_sha256') != RECOVERY_PROFILE_SHA256 or
            review.get('profile_sha256') != RECOVERY_PROFILE_SHA256 or
            recovery.get('release_sha256') != review['release']['sha256'] or
            recovery.get('prepared_sha256') != review['prepared']['sha256'] or
            recovery.get('source_checkpoint') != review.get('source_checkpoint') or
            recovery.get('source_checkpoint') != recovery_release.get('source_checkpoint') or
            recovery_release.get('schema') != 'scratch22-authority1.quarantine-recovery-release.v1' or
            recovery_release.get('status') != 'PASS_EXECUTION_RELEASE'):
        raise Refusal('authority1 actual complete recovery binding differs')
    guard = profile['bound_guard']
    target = dict(pid=guard['pid'], starttime=guard['starttime'], parent=guard['parent_pid'],
                  boot_id=guard['boot_id'], uid=guard['uid'], gid=guard['gid'], threads=guard['threads'])
    if (recovery.get('target') != target or prepared.get('target') != target or
            prepared.get('schema') != 'scratch22-authority1.quarantine-recovery-prepared.v1' or
            prepared.get('status') != 'PREPARED_PROCESS_RETIREMENT' or
            prepared.get('signal_budget') != 1 or prepared.get('build_status') != 'FAIL' or
            any(prepared.get(key) != recovery.get(key) for key in
                ('profile_sha256', 'release_sha256', 'source_checkpoint', 'original_failure_sha256')) or
            recovery.get('sole_signal') != dict(syscall=424, signal=9, returncode=0) or
            recovery.get('replacement_root_lock') != [guard['root_lock']['device'], guard['root_lock']['inode']] or
            recovery.get('original_failure_sha256') != RECOVERY_ORIGINAL_FAILURE_SHA256 or
            recovery_release.get('original_failure_sha256') != RECOVERY_ORIGINAL_FAILURE_SHA256):
        raise Refusal('authority1 sole process-retirement proof differs')
    exit_proof = recovery.get('exit_proof', {})
    events = exit_proof.get('events', [])
    if (exit_proof.get('pidfd_exit_ready') is not True or len(events) != 1 or
            len(events[0]) != 2 or type(events[0][0]) is not int or events[0][0] < 0 or
            type(events[0][1]) is not int or not events[0][1] & 1 or events[0][1] & ~17):
        raise Refusal('authority1 positive pidfd exit proof missing')
    before = prepared.get('before', [])
    after = recovery.get('after', {})
    if (len(before) != 2 or not before[0].get('inputs') or
            before[0]['inputs'] != before[1].get('inputs') or
            after.get('inputs') != before[0]['inputs'] or not after.get('root_locks') or
            not isinstance(recovery.get('deferred_signals'), list)):
        raise Refusal('authority1 original inputs/lock recovery proof differs')
    for original, checksum in RECOVERY_ORIGINAL_FAILURE_SHA256.items():
        if _IMPL.digest(Path(original)) != checksum:
            raise Refusal('authority1 original recovery failure changed')

    cleanup_pointer = release['authority1_cleanup']
    result = bound_json(cleanup_pointer['path'], cleanup_pointer['sha256'])
    pointer = release['authority1_cleanup_review']
    cleanup_review = bound_json(pointer['path'], pointer['sha256'])
    require_retirement_review(cleanup_review, 'scratch22-authority1.cleanup-postflight-review.v1',
                              'PASS_TERMINAL_CLEANUP_POSTFLIGHT')
    if (cleanup_review.get('result') != cleanup_pointer or
            cleanup_review.get('container_absent') is not True or
            cleanup_review.get('exclusions_absent') is not True or
            result.get('schema') != 'scratch22-authority1.cleanup-result.v1' or
            result.get('status') not in ('PASS_EXECUTED', 'PASS_TERMINAL_REPLAY') or
            result.get('terminal') is not True or result.get('container_absent') is not True or
            result.get('container_id') != profile['retirement_proof']['container']['id'] or
            result.get('filesystem_uuid') != SCRATCH_UUID or result.get('boot_id') != target['boot_id'] or
            result.get('release_sha256') != cleanup_review.get('release_canonical_sha256') or
            result.get('archives') != cleanup_review.get('archives')):
        raise Refusal('authority1 accepted terminal cleanup binding differs')
    # The accepted postflight binds the raw large release AND its canonical
    # digest. Hash the raw file as a stream; do not reparse its 146-MB inventory.
    authority = cleanup_review['release']
    if _IMPL.snapshot(Path(authority['path']))['sha256'] != authority['sha256']:
        raise Refusal('authority1 cleanup raw release changed')
    for key in ('plan', 'journal', 'capture'):
        row = result[key]
        if cleanup_review.get(key) != {name: row[name] for name in ('path', 'sha256')}:
            raise Refusal('authority1 cleanup evidence postflight differs: ' + key)
    validate_authority1_cleanup_journal(result)
    return dict(recovery=recovery, cleanup=result)


def require_retirement_review(review, schema, decision):
    if (review.get('schema') != schema or review.get('decision') != decision or
            not review.get('reviewer') or review['reviewer'] == '/root' or
            review.get('implementation_ownership') is not False):
        raise Refusal('independent accepted authority1 retirement review required')


def validate_authority1_cleanup_journal(result, schema='scratch22-authority1.terminal-cleanup.v1'):
    """Authenticate the actual terminal transaction and archived originals."""
    plan_raw = bound_identity(result['plan'])
    plan = json.loads(plan_raw, object_pairs_hook=unique_object)
    plan_sha = hashlib.sha256(canonical(plan)).hexdigest()
    if (plan.get('schema') != schema or
            plan.get('root') != str(_IMPL.DEFAULT_SCRATCH) or
            plan.get('filesystem_uuid') != SCRATCH_UUID or
            plan.get('release_sha256') != result['release_sha256'] or
            plan_sha != result.get('plan_sha256') or plan_raw != canonical(plan) + b'\n'):
        raise Refusal('authority1 actual cleanup plan differs')
    journal = bound_identity(result['journal']).splitlines(keepends=True)
    legal = [(event, index) for index in range(2) for event in
             ('before_exchange', 'after_exchange', 'release', 'after_release')] + [('complete', 2)]
    if len(journal) != len(legal):
        raise Refusal('authority1 actual cleanup journal incomplete')
    previous = plan_sha
    for sequence, (line, (event, index)) in enumerate(zip(journal, legal)):
        body = dict(event=event, index=index, sequence=sequence, plan_sha256=plan_sha,
                    previous=previous, plan_identity=[result['plan']['device'], result['plan']['inode']])
        expected = dict(body, hash=hashlib.sha256(canonical(body)).hexdigest())
        if line != canonical(expected) + b'\n':
            raise Refusal('authority1 actual cleanup journal chain differs')
        previous = expected['hash']
    archives = result.get('archives', [])
    records = plan.get('records', [])
    if len(archives) != 2 or len(records) != 2 or len({row['path'] for row in archives}) != 2:
        raise Refusal('authority1 cleanup archive inventory differs')
    for record, archive in zip(records, archives):
        if (len(record) != 5 or Path(archive['path']).name != record[1] or
                (archive['sha256'], archive['inode'], archive['size']) != tuple(record[2:])):
            raise Refusal('authority1 cleanup archive plan differs')
        bound_identity(archive)
    # The large capture was independently sealed already; stream its exact
    # hash/metadata again without materializing its complete bytes in memory.
    row = result['capture']
    observed = _IMPL.snapshot(Path(row['path']))
    meta = os.lstat(row['path'])
    wanted = dict(path=row['path'], device=observed['device'], inode=observed['inode'],
                  mode=oct(stat.S_IMODE(meta.st_mode)), uid=meta.st_uid, gid=meta.st_gid,
                  size=observed['size'], nlink=observed['nlink'], sha256=observed['sha256'])
    if row != wanted:
        raise Refusal('authority1 cleanup preserved capture differs')


def validate_authority2_retirement(release):
    """Positive failed-build retirement and separately accepted cleanup only."""
    terminal_pointer = release['authority2_terminal']
    terminal = bound_json(terminal_pointer['path'], terminal_pointer['sha256'])
    receipt_pointer = release['authority2_receipt']
    receipt = bound_json(receipt_pointer['path'], receipt_pointer['sha256'])
    request = bound_json(AUTHORITY2_REQUEST, AUTHORITY2_REQUEST_SHA256)
    if (terminal.get('schema') != 'scratch22-authority2.heavy-build-terminal.v1' or
            terminal.get('request_sha256') != AUTHORITY2_REQUEST_SHA256 or
            terminal.get('returncode') != 1 or terminal.get('wrapper_result') != receipt or
            receipt.get('status') != 'FAIL' or receipt.get('exit_code') != 1 or
            receipt.get('retired') is not True or receipt.get('client_retirement_unproven') is True or
            receipt.get('cleanup_separately_required') is not True or
            receipt.get('terminal_container_retained') is not True or
            receipt.get('terminal_container_info_current') is not True or
            receipt.get('container_id') != AUTHORITY2_CONTAINER or receipt.get('request') != request):
        raise Refusal('authority2 positive FAIL retirement proof differs')
    state = receipt.get('terminal_container_info', {}).get('State', {})
    if (state.get('Status') != 'exited' or state.get('Pid') != 0 or
            state.get('ExitCode') != 1 or state.get('OOMKilled') is not False):
        raise Refusal('authority2 stopped non-OOM container proof differs')
    statuses = {rel: row for rel, row in receipt.get('evidence', {}).items()
                if rel.startswith('command-') and rel.endswith('/status.json')}
    if len(statuses) != 7:
        raise Refusal('authority2 exact seven client statuses required')
    evidence = Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority2-evidence')
    for rel, row in statuses.items():
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise Refusal('authority2 client status path differs')
        status = bound_json(evidence / rel, row['sha256'])
        if (status.get('state') != 'exited' or status.get('exit_code') != 0 or any(
                status.get(flag) for flag in ('client_retirement_unproven', 'forced_client_retirement',
                                             'retirement_unproven', 'surviving_process_group', 'reap_error'))):
            raise Refusal('authority2 client retirement not positive')
    pointer = release['authority2_cleanup']
    result = bound_json(pointer['path'], pointer['sha256'])
    review_pointer = release['authority2_cleanup_review']
    review = bound_json(review_pointer['path'], review_pointer['sha256'])
    require_retirement_review(review, 'scratch22-authority2.cleanup-postflight-review.v1',
                              'PASS_TERMINAL_CLEANUP_POSTFLIGHT')
    if (review.get('terminal') != terminal_pointer or review.get('receipt') != receipt_pointer or
            review.get('result') != pointer or review.get('container_absent') is not True or
            review.get('exclusions_absent') is not True or
            result.get('schema') != 'scratch22-authority2.cleanup-result.v1' or
            result.get('status') not in ('PASS_EXECUTED', 'PASS_TERMINAL_REPLAY') or
            result.get('terminal') is not True or result.get('container_absent') is not True or
            result.get('container_id') != AUTHORITY2_CONTAINER or
            result.get('filesystem_uuid') != SCRATCH_UUID or
            result.get('release_sha256') != review.get('release_canonical_sha256') or
            result.get('archives') != review.get('archives')):
        raise Refusal('authority2 accepted terminal cleanup postflight differs')
    raw_release = review['release']
    if _IMPL.snapshot(Path(raw_release['path']))['sha256'] != raw_release['sha256']:
        raise Refusal('authority2 cleanup raw release changed')
    for key in ('plan', 'journal', 'capture'):
        if review.get(key) != {name: result[key][name] for name in ('path', 'sha256')}:
            raise Refusal('authority2 cleanup evidence postflight differs')
    validate_authority1_cleanup_journal(result, schema='scratch22-authority2.terminal-cleanup.v1')
    return result


def validate_authority_review(source, release):
    """Require the independent exact observer repair in addition to old RS011."""
    pointer = release['authority_review']
    review = bound_json(pointer['path'], pointer['sha256'])
    if (review.get('decision') != 'PASS_SOURCE_AUTHORITY' or
            review.get('implementation_ownership') is not False or not review.get('reviewer')):
        raise Refusal('independent authority1 source review required')
    hashes = review.get('files_sha256', {})
    if set(hashes) != AUTHORITY_FILES:
        raise Refusal('authority1 fixed four-file review allowlist mismatch')
    author_pointer = review['author_record']
    if author_pointer.get('path') != AUTHORITY_AUTHOR_RECORD:
        raise Refusal('authority1 original author record required')
    author = bound_json(author_pointer['path'], author_pointer['sha256'])
    if (not author.get('author') or review['reviewer'] == author['author'] or
            author.get('files_sha256') != hashes or author.get('checks', {}).get('status') != 'PASS'):
        raise Refusal('authority1 independent author/check/hash binding mismatch')
    for rel, checksum in hashes.items():
        if hashlib.sha256(_IMPL.git(source, 'show', release['target'] + ':' + rel)).hexdigest() != checksum:
            raise Refusal('authority1 reviewed target blob mismatch: ' + rel)


def validate_cleanup(release):
    """Accept the actual terminal transaction result, never a draft/release."""
    pointer = release['cleanup']
    result = bound_json(pointer['path'], pointer['sha256'])
    if (result.get('schema') != 'scratch21.cleanup-result.v1' or
            result.get('status') not in ('PASS_EXECUTED', 'PASS_TERMINAL_REPLAY') or
            result.get('terminal') is not True or result.get('container_absent') is not True):
        raise Refusal('accepted scratch21 terminal cleanup required')
    if result.get('container_id') != SCRATCH21_CONTAINER or result.get('filesystem_uuid') != SCRATCH_UUID:
        raise Refusal('scratch21 cleanup container/filesystem mismatch')
    authority = release['cleanup_release']
    cleanup_release = bound_json(authority['path'], authority['sha256'])
    if (cleanup_release.get('schema') != 'scratch21.cleanup-release.v1' or
            cleanup_release.get('status') != 'PASS_EXECUTION_RELEASE' or
            hashlib.sha256(canonical(cleanup_release)).hexdigest() != result.get('release_sha256')):
        raise Refusal('scratch21 executed cleanup release mismatch')
    for key in ('source_review', 'execution_review'):
        review = cleanup_release.get(key, {})
        if (review.get('status') != 'PASS' or not review.get('reviewer') or
                review['reviewer'] == cleanup_release.get('author') or not review.get('evidence_sha256')):
            raise Refusal('scratch21 original independent cleanup review missing')
    observation = cleanup_release.get('observation', {})
    if (observation.get('boot_id') != result.get('boot_id') or
            observation.get('mount', {}).get('uuid') != SCRATCH_UUID):
        raise Refusal('scratch21 cleanup observation mismatch')
    blobs = {key: bound_identity(result[key]) for key in ('plan', 'journal', 'capture')}
    archives = result.get('archives', [])
    if len(archives) != 2:
        raise Refusal('scratch21 cleanup archive inventory incomplete')
    for row in archives:
        bound_identity(row)
    plan = json.loads(blobs['plan'], object_pairs_hook=unique_object)
    plan_sha = hashlib.sha256(canonical(plan)).hexdigest()
    if (plan.get('schema') != 'scratch21.terminal-cleanup.v1' or
            plan.get('release_sha256') != result.get('release_sha256') or
            plan.get('filesystem_uuid') != SCRATCH_UUID or plan.get('root') != str(_IMPL.DEFAULT_SCRATCH) or
            plan_sha != result.get('plan_sha256') or
            blobs['plan'] != canonical(plan) + b'\n'):
        raise Refusal('scratch21 terminal plan binding mismatch')
    records = plan.get('records', [])
    if len(records) != 2 or len({row['path'] for row in archives}) != 2:
        raise Refusal('scratch21 archive plan inventory mismatch')
    for record, archive in zip(records, archives):
        if (len(record) != 5 or Path(archive['path']).name != record[1] or
                (archive['sha256'], archive['inode'], archive['size']) != tuple(record[2:])):
            raise Refusal('scratch21 archive plan binding mismatch')
    legal = [(event, index) for index in range(2) for event in
             ('before_exchange', 'after_exchange', 'release', 'after_release')] + [('complete', 2)]
    journal = blobs['journal']
    lines = journal.splitlines(keepends=True)
    if len(lines) != len(legal):
        raise Refusal('scratch21 cleanup journal not complete')
    previous = plan_sha
    for sequence, (line, (event, index)) in enumerate(zip(lines, legal)):
        row = json.loads(line, object_pairs_hook=unique_object)
        body = dict(event=event, index=index, sequence=sequence, plan_sha256=plan_sha,
                    previous=previous, plan_identity=[result['plan']['device'], result['plan']['inode']])
        expected = dict(body, hash=hashlib.sha256(canonical(body)).hexdigest())
        if row != expected or line != canonical(expected) + b'\n':
            raise Refusal('scratch21 cleanup journal chain mismatch')
        previous = expected['hash']
    pointer = release['cleanup_postflight']
    postflight = bound_json(pointer['path'], pointer['sha256'])
    if (postflight.get('schema') != 'scratch21.cleanup-postflight-review.v1' or
            postflight.get('decision') != 'PASS_CLEANUP' or
            postflight.get('result_sha256') != release['cleanup']['sha256'] or
            postflight.get('release_sha256') != result['release_sha256']):
        raise Refusal('accepted exact cleanup postflight review required')
    return result


def bound_identity(row):
    """Verify actual cleanup producer identity dictionaries without relabeling."""
    path = Path(row['path'])
    if not path.is_absolute() or path.resolve() != path:
        raise Refusal('noncanonical cleanup evidence path')
    before = _IMPL.snapshot(path)
    meta = os.lstat(path)
    expected = dict(path=str(path), device=before['device'], inode=before['inode'],
                    mode=oct(stat.S_IMODE(meta.st_mode)), uid=meta.st_uid, gid=meta.st_gid,
                    size=before['size'], nlink=before['nlink'], sha256=before['sha256'])
    raw = path.read_bytes()
    if row != expected or _IMPL.snapshot(path) != before or hashlib.sha256(raw).hexdigest() != before['sha256']:
        raise Refusal('scratch21 cleanup evidence drift')
    return raw


def validate_release(source, path, checksum, materialize=False):
    release = bound_json(path, checksum)
    expected = ('scratch22-authority3.preparation-release.v1', 'PASS_PREPARATION_EXECUTION_RELEASE') if materialize else (
        'scratch22-authority3-source-admission-v1', 'PASS')
    if ((release.get('schema'), release.get('status')) != expected or
            release.get('attempt') != 'scratch22-authority3' or
            release.get('execution_released') is not False):
        raise Refusal('accepted scratch22 ' + ('preparation execution' if materialize else 'source-only') + ' release required')
    for key in ('target', 'target_tree', 'baseline'):
        value = release.get(key)
        if not isinstance(value, str) or len(value) != 40 or any(
                c not in '0123456789abcdef' for c in value):
            raise Refusal('exact released ' + key + ' required')
    if release.get('source_base') != SOURCE_BASE:
        raise Refusal('released source base mismatch')
    validate_cleanup(release)
    validate_source_authority(source, release)
    validate_authority_review(source, release)
    validate_authority1_retirement(release)
    validate_authority2_retirement(release)
    target = release['target']
    fetched = release.get('fetched_ref')
    if not isinstance(fetched, str) or not fetched.startswith('refs/remotes/origin/'):
        raise Refusal('exact fetched origin ref required')
    for revision, expected in ((fetched, target), (target + '^{commit}', target),
                               (target + '^{tree}', release['target_tree']),
                               (target + '^', release['baseline'])):
        if _IMPL.git(source, 'rev-parse', '--verify', revision).decode().strip() != expected:
            raise Refusal('released/fetched source identity mismatch: ' + revision)
    delta = release.get('exact_delta')
    if not isinstance(delta, list) or not delta or any(
            not isinstance(row, list) or len(row) != 3 for row in delta):
        raise Refusal('released exact delta required')
    _IMPL.raw_delta(source, old=release['baseline'], target=target,
                    expected=tuple(map(tuple, delta)))
    owner = ast.parse(_IMPL.git(source, 'show', target + ':' + OWNER).decode())
    slots = [ast.literal_eval(node.value) for node in owner.body
             if isinstance(node, ast.Assign) and any(
                 isinstance(name, ast.Name) and name.id == 'OPERATIONAL_EXCLUSION_PATH'
                 for name in node.targets)]
    if slots != [ACTIVE_EXCLUSION]:
        raise Refusal('candidate owner active exclusion mismatch (scratch20 family)')
    if materialize:
        validate_preparation_release(source, release)
    return release


def validate_preparation_release(source, release):
    """Fresh preparation authority binds code and actual prerequisite evidence."""
    paths = {'script_sha256': Path(__file__).resolve(),
             'tests_sha256': ROOT / 'scripts/tests/test_prepare_native_exact_scratch22_authority3.py',
             'ancestor_sha256': ANCESTOR}
    expected = {key: _IMPL.digest(path) for key, path in paths.items()}
    if any(release.get(key) != checksum for key, checksum in expected.items()):
        raise Refusal('preparation source hash drift')
    controller = release.get('controller')
    if (not isinstance(controller, str) or len(controller) != 40 or any(
            c not in '0123456789abcdef' for c in controller) or
            _IMPL.git(source, 'rev-parse', '--verify', 'HEAD').decode().strip() != controller):
        raise Refusal('preparation controller mismatch')
    for key, path in paths.items():
        rel = path.relative_to(ROOT).as_posix()
        if hashlib.sha256(_IMPL.git(source, 'show', controller + ':' + rel)).hexdigest() != expected[key]:
            raise Refusal('preparation controller blob mismatch')
    expected.update({key + '_sha256': release[key]['sha256']
                     for key in ('cleanup', 'cleanup_release', 'cleanup_postflight', 'source_checks', 'source_review', 'authority_review', 'repair_review',
                                 'authority1_recovery', 'authority1_recovery_review', 'authority1_cleanup', 'authority1_cleanup_review',
                                 'current_source_checks', 'authority2_terminal', 'authority2_receipt', 'authority2_cleanup', 'authority2_cleanup_review')})
    pointer = release['preparation_review']
    review = bound_json(pointer['path'], pointer['sha256'])
    if (review.get('decision') != 'PASS_PREPARATION_EXECUTION' or
            not release.get('author') or not review.get('reviewer') or
            review['reviewer'] == release['author'] or
            review.get('implementation_ownership') is not False or
            review.get('reviewed_inputs_sha256') != expected or
            review.get('target') != release['target'] or
            review.get('target_tree') != release['target_tree']):
        raise Refusal('independent exact preparation execution review required')


def live_preparation_boundary(scratch, release):
    """Check the existing filesystem/isolation contract immediately before use."""
    binding = release['live_binding']
    scratch = Path(scratch)
    if (str(scratch) != str(_IMPL.DEFAULT_SCRATCH) or scratch.is_symlink() or
            scratch.resolve() != scratch or scratch.stat().st_dev != binding.get('scratch_device') or
            Path('/proc/sys/kernel/random/boot_id').read_text().strip() != binding.get('boot_id')):
        raise Refusal('fresh scratch device/boot binding mismatch')
    proc = subprocess.run(['/usr/bin/findmnt', '--json', '--target', str(scratch),
                           '--output', 'TARGET,FSTYPE,UUID,OPTIONS'],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
                          env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'})
    if proc.returncode:
        raise Refusal('fresh scratch mount observation failed')
    mounts = json.loads(proc.stdout).get('filesystems', [])
    if len(mounts) != 1:
        raise Refusal('ambiguous scratch mount')
    mount = mounts[0]
    if (mount.get('target') != str(scratch) or mount.get('uuid') != SCRATCH_UUID or
            binding.get('scratch_uuid') != SCRATCH_UUID or mount.get('fstype') != 'ext4' or
            not {'rw', 'nodev', 'nosuid'} <= set(mount.get('options', '').split(','))):
        raise Refusal('fresh scratch UUID/profile mismatch')
    _IMPL.capacity(scratch)


def _alias_phase_metadata(path, directory=False):
    """No content read: canonical path, type and a complete mutation fence."""
    path = Path(path)
    try:
        if not path.is_absolute() or path.resolve(strict=True) != path:
            raise Refusal('noncanonical evidence alias path')
        meta = os.lstat(path)
        if not (stat.S_ISDIR(meta.st_mode) if directory else stat.S_ISREG(meta.st_mode)):
            raise Refusal('alias path type differs')
        return (meta.st_dev, meta.st_ino, meta.st_mode, meta.st_size, meta.st_nlink,
                meta.st_mtime_ns, meta.st_ctime_ns, meta.st_uid, meta.st_gid)
    except OSError as error:
        raise Refusal('alias path metadata unavailable: ' + str(path)) from error


def _alias_inode_digest(path, expected):
    """Authenticate one descriptor in one bounded pass, with path/fstat fences."""
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
        def metadata():
            meta = os.fstat(descriptor)
            return (meta.st_dev, meta.st_ino, meta.st_mode, meta.st_size, meta.st_nlink,
                    meta.st_mtime_ns, meta.st_ctime_ns, meta.st_uid, meta.st_gid)
        if metadata() != expected or _alias_phase_metadata(path) != expected:
            raise Refusal('alias descriptor/path changed before content authentication')
        blob = hashlib.sha1(b'blob ' + str(expected[3]).encode('ascii') + b'\0')
        content = hashlib.sha256()
        consumed = 0
        while True:
            block = os.read(descriptor, min(1 << 20, expected[3] - consumed + 1))
            if not block:
                break
            consumed += len(block)
            if consumed > expected[3]:
                raise Refusal('alias content size grew during authentication')
            blob.update(block)
            content.update(block)
        if consumed != expected[3] or metadata() != expected or _alias_phase_metadata(path) != expected:
            raise Refusal('alias content metadata raced during authentication')
        return blob.hexdigest(), content.hexdigest()
    except OSError as error:
        raise Refusal('alias descriptor authentication unavailable: ' + str(path)) from error
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _alias_phase_proof(roots, shared):
    """Authenticate each inode once in THIS phase; fence every alias and root."""
    roots = tuple(map(Path, roots))
    if not roots or len(set(roots)) != len(roots):
        raise Refusal('duplicate/missing alias roots')
    root_metadata = tuple(_alias_phase_metadata(root, directory=True) for root in roots)
    if len({row[:2] for row in root_metadata}) != len(roots):
        raise Refusal('alias root inode duplicated')
    plans = []
    for rel, mode, oid in shared:
        relative = Path(rel)
        if relative.is_absolute() or '..' in relative.parts or relative.as_posix() != rel:
            raise Refusal('invalid evidence path')
        paths = tuple(root / rel for root in roots)
        rows = tuple(_alias_phase_metadata(path) for path in paths)
        first = rows[0]
        # Every link has a distinct authenticated path; unknown links refuse.
        if first[4] != len(roots) or any(row != first for row in rows):
            raise Refusal('incomplete authenticated alias census: ' + rel)
        if stat.S_IMODE(first[2]) != (int(mode, 8) & 0o777):
            raise Refusal('unauthenticated alias bytes/mode: ' + rel)
        plans.append((paths, rows, oid))
    if not plans:
        raise Refusal('empty alias census')
    # Local to one invocation only. Subsequent validation phases read again.
    authenticated = {}
    for paths, rows, oid in plans:
        first = rows[0]
        key = first[:2]
        if key not in authenticated:
            blob, checksum = _alias_inode_digest(paths[0], first)
            authenticated[key] = (first, blob, checksum)
        if authenticated[key][:2] != (first, oid):
            raise Refusal('unauthenticated alias bytes/inode: ' + str(paths[0]))
    # Recheck ALL paths after ALL content reads, including earlier rows whose
    # inode might change while a later row was being authenticated.
    for paths, before, _ in plans:
        if tuple(_alias_phase_metadata(path) for path in paths) != before:
            raise Refusal('alias census raced')
    if tuple(_alias_phase_metadata(root, directory=True) for root in roots) != root_metadata:
        raise Refusal('alias root metadata raced')
    proofs = {}
    for paths, rows, oid in plans:
        for path, metadata in zip(paths, rows):
            proofs[path] = (metadata, oid, authenticated[metadata[:2]][2])
    return roots, root_metadata, proofs


def alias_census(roots, shared):
    return len(_alias_phase_proof(roots, shared)[0])


@contextmanager
def _inherited_alias_phase(phase, shared):
    """Reuse this phase's proof only for exact known paths in the pinned ancestor."""
    if hashlib.sha256(ANCESTOR.read_bytes()).hexdigest() != '23d2dcc45db9e9268456a202e46c0e25e982b13d91413271cf00452d0564a731':
        raise Refusal('inherited alias callback contract changed')
    original_snapshot, original_git, original_check = _IMPL.snapshot, _IMPL.git, _IMPL.check_shared
    active = phase

    def known(path):
        path = Path(path)
        roots, root_metadata, proofs = active
        if path not in proofs:
            return None
        metadata, oid, checksum = proofs[path]
        if (_alias_phase_metadata(path) != metadata or
                tuple(_alias_phase_metadata(root, directory=True) for root in roots) != root_metadata):
            raise Refusal('inherited shared alias proof metadata changed')
        return metadata, oid, checksum

    def snapshot(path):
        proof = known(path)
        if proof is None:
            return original_snapshot(path)
        metadata, _, checksum = proof
        return dict(zip(('device', 'inode', 'mode', 'size', 'nlink', 'mtime_ns'),
                        (metadata[0], metadata[1], stat.S_IMODE(metadata[2]),
                         metadata[3], metadata[4], metadata[5])), sha256=checksum)

    def git(repo, *args, **kwargs):
        if len(args) == 3 and args[:2] == ('hash-object', '--no-filters') and not kwargs:
            proof = known(args[2])
            if proof is not None:
                return (proof[1] + '\n').encode('ascii')
        return original_git(repo, *args, **kwargs)

    def check(candidate, scratch15, scratch16, previous_candidate, rows,
              expected_initial_links=3, additional_shared_roots=()):
        nonlocal active
        # Only the exact initially authenticated set may use this adapter.
        if [(row['path'], row['blob']) for row in rows] != [(rel, oid) for rel, _, oid in shared]:
            raise Refusal('inherited shared set differs from authenticated phase')
        roots = (scratch15, scratch16, previous_candidate, *additional_shared_roots, candidate)
        fresh = _alias_phase_proof(roots, shared)
        if len(roots) != expected_initial_links + 1:
            raise Refusal('inherited final alias count differs')
        saved, active = active, fresh
        try:
            result = original_check(candidate, scratch15, scratch16, previous_candidate, rows,
                                    expected_initial_links, additional_shared_roots)
            for path in fresh[2]:
                known(path)
            return result
        finally:
            active = saved

    _IMPL.snapshot, _IMPL.git, _IMPL.check_shared = snapshot, git, check
    try:
        yield
    finally:
        _IMPL.snapshot, _IMPL.git, _IMPL.check_shared = original_snapshot, original_git, original_check


def inherited_arguments(release, scratch, links):
    """Explicitly bind EVERY inherited default, including Python frozen values."""
    roots = tuple(Path(scratch) / name for name in ALIASES)
    result = dict(
        execute=False, old=release['baseline'], baseline=release['baseline'],
        source_base=SOURCE_BASE, target=release['target'],
        ihk_expected=_IMPL.IHK, overlay_sha=_IMPL.OVERLAY_SHA256,
        overlay_result_sha=_IMPL.OVERLAY_RESULT_SHA256, assets_root=_IMPL.ASSETS,
        image_receipt=_IMPL.RECEIPT, image_id=_IMPL.IMAGE_ID,
        exclusion=ACTIVE_EXCLUSION, image_receipt_sha256=_IMPL.RECEIPT_SHA256,
        overlay_base_sha256=_IMPL.OVERLAY_BASE_BLOB_SHA,
        overlay_result_commit=_IMPL.OVERLAY_RESULT_COMMIT_SHA,
        scratch16=roots[1], previous_candidate=roots[2],
        expected_shared_files=_IMPL.EXPECTED_SHARED_FILES,
        expected_initial_links=links, additional_shared_roots=roots[3:],
        expected_delta=tuple(map(tuple, release['exact_delta'])),
    )
    defaults = {name for name, param in inspect.signature(_IMPL.prepare).parameters.items()
                if param.default is not inspect.Parameter.empty}
    if set(result) != defaults:
        raise Refusal('unbound inherited defaults (scratch19 family)')
    return result


def prepare(*, release_path, release_sha256, source=ROOT,
            scratch=_IMPL.DEFAULT_SCRATCH, execute=False, materialize=False):
    if execute:
        raise Refusal('scratch22 adapter forbids execute/materialization')
    source, scratch = Path(source), Path(scratch)
    release = validate_release(source, release_path, release_sha256, materialize=materialize)
    roots = tuple(scratch / name for name in ALIASES)
    old = {rel: (mode, kind, oid) for mode, kind, oid, rel in
           _IMPL.tree_entries(source, release['baseline'])}
    sizes = {}
    for row in _IMPL.git(source, 'ls-tree', '-rlz', release['target']).split(b'\0'):
        if row:
            meta, rel = row.split(b'\t', 1)
            fields = meta.split()
            if fields[1] == b'blob':
                sizes[rel.decode()] = int(fields[3])
    shared = [(rel, mode, oid) for mode, kind, oid, rel in
              _IMPL.tree_entries(source, release['target'])
              if kind == 'blob' and sizes[rel] > 1 << 20 and
              rel.startswith('docs/verification/evidence/') and
              old.get(rel) == (mode, kind, oid) and (roots[0] / rel).exists() and
              mode in ('100644', '100755')]
    if len(shared) != _IMPL.EXPECTED_SHARED_FILES:
        raise Refusal('incomplete 486-file evidence census')
    phase = _alias_phase_proof(roots, shared)
    links = len(phase[0])
    args = inherited_arguments(release, scratch, links)
    for name, value in dict(NAMES, TARGET=release['target'],
                            TARGET_TREE=release['target_tree'],
                            BASELINE=release['baseline'], SOURCE_BASE=SOURCE_BASE,
                            FETCHED_REF=release['fetched_ref'],
                            EXACT_DELTA=args['expected_delta']).items():
        setattr(_IMPL, name, value)
    if materialize:
        live_preparation_boundary(scratch, release)
        args['execute'] = True
    with _inherited_alias_phase(phase, shared):
        result = _IMPL.prepare(source, roots[0], scratch, **args)
    if materialize:
        if result.get('status') != 'PASS_PREPARE_ONLY':
            raise Refusal('inherited preparation did not complete')
        validate_prepared_request(scratch / NAMES['CANDIDATE_NAME'], result['request'])
    result.update(alias_roots=list(map(str, roots)), authenticated_initial_links=links,
                  expected_materialized_links=links + 1, execution_released=False,
                  canonical_owner_request_validation=('PASS' if materialize else
                      'REQUIRED_AFTER_SEPARATELY_RELEASED_MATERIALIZATION'))
    return result


def validate_prepared_request(candidate, request_path):
    """Later read-only boundary: real candidate owner validation, no execution."""
    request = json.loads(Path(request_path).read_text())
    if any(request.get(k) is not v for k, v in {
            'preparation_only': True, 'execution_released': False,
            'executable': False, 'release_required': True,
            'operational_exclusion_consumed': False}.items()):
        raise Refusal('preparation request is executable or released')
    candidate = Path(candidate)
    if candidate.name != NAMES['CANDIDATE_NAME'] or request.get('source_root') != str(candidate):
        raise Refusal('fresh scratch22 candidate binding required')
    if request.get('operational_exclusion_path') != ACTIVE_EXCLUSION:
        raise Refusal('candidate owner active exclusion mismatch')
    with _IMPL.candidate_modules(candidate) as (_, __, owner_mod):
        owner = owner_mod.BuildOwner(request)
        owner.validate()
        if owner.docker is not None:
            raise Refusal('unexpected Docker construction')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True)
    parser.add_argument('--release-sha256', required=True)
    parser.add_argument('--materialize', action='store_true',
                        help='create fresh preparation only under an exact independent preparation release')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(prepare(release_path=args.release,
                                 release_sha256=args.release_sha256,
                                 materialize=args.materialize), sort_keys=True))
    except (Refusal, OSError, ValueError, KeyError) as error:
        parser.exit(2, 'REFUSED: ' + str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
