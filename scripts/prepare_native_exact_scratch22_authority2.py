#!/usr/bin/env python3
"""Scratch22 authority2 source template; retirement authority is not released.

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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANCESTOR = ROOT / 'docs/verification/evidence/native-exact-candidate-delta-preparation-scratch18-20261001.py'
spec = importlib.util.spec_from_file_location('_scratch22_authority2_private_ancestor', ANCESTOR)
_IMPL = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_IMPL)
Refusal = _IMPL.Refusal
NAMES = {
    'CANDIDATE_NAME': 'mckernel-exact-candidate-scratch-22-authority2',
    'MANIFEST_NAME': 'native-exact-inputs-scratch-22-authority2.json',
    'REQUEST_NAME': 'native-exact-delta-request-scratch-22-authority2.json',
    'LOG_NAME': 'native-exact-candidate-delta-preparation-scratch-22-authority2.log',
    'TERMINAL_NAME': 'native-exact-candidate-delta-preparation-scratch-22-authority2-terminal.json',
    'LEASE_NAME': 'native-exact-build-lease-scratch-22-authority2.json',
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
})
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
    """Exactly the existing failure family's two source changes, never a reset."""
    pointer = release['repair_review']
    review = bound_json(pointer['path'], pointer['sha256'])
    if (review.get('decision') != 'PASS_MINIMAL_SOURCE_REPAIR' or
            review.get('implementation_ownership') is not False or
            not review.get('reviewer') or not review.get('implementation_author') or
            review['reviewer'] == review['implementation_author'] or
            review.get('baseline_candidate') != release['baseline'] or
            any(review.get(key) != release[key] for key in ('target', 'target_tree')) or
            set(review.get('files_sha256_delta', {})) != REPAIR_FILES):
        raise Refusal('independent exact two-file shutdown repair review required')
    for field, original in (('source_checks_baseline', 'source_checks'), ('source_review_baseline', 'source_review')):
        if any(review.get(field, {}).get(key) != release[original][key] for key in ('path', 'sha256')):
            raise Refusal('minimal repair review immutable source baseline binding differs')
    delta = release.get('exact_delta', [])
    if (len(delta) != 2 or {tuple(row[:2]) for row in delta} != {('M', rel) for rel in REPAIR_FILES} or
            any(len(row) != 3 for row in delta)):
        raise Refusal('authority2 target must contain only the two reviewed modifications')
    for rel, (old, new) in REPAIR_REPLACEMENTS.items():
        before = _IMPL.git(source, 'show', release['baseline'] + ':' + rel)
        after = _IMPL.git(source, 'show', release['target'] + ':' + rel)
        if (before.count(old) != 1 or before.replace(old, new, 1) != after or
                hashlib.sha256(before).hexdigest() != review['files_sha256_delta'][rel]['baseline_sha256'] or
                hashlib.sha256(after).hexdigest() != review['files_sha256_delta'][rel]['target_sha256']):
            raise Refusal('authority2 exact bounded repair source differs: ' + rel)
    return review


def validate_authority1_retirement(release):
    """Fail closed until the actual cleanup/recovery producers are reconciled.

    The failed authority1 container, 80-MiB capture, guard and exclusions must
    never be treated as abandoned. No future acceptance record is synthesized
    here. This source template needs a reviewed actual retirement integration.
    """
    raise Refusal('authority2 preparation not released: actual authority1 cleanup and quarantine recovery contracts pending')


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
    expected = ('scratch22-authority2.preparation-release.v1', 'PASS_PREPARATION_EXECUTION_RELEASE') if materialize else (
        'scratch22-authority2-source-admission-v1', 'PASS')
    if ((release.get('schema'), release.get('status')) != expected or
            release.get('attempt') != 'scratch22-authority2' or
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
             'tests_sha256': ROOT / 'scripts/tests/test_prepare_native_exact_scratch22_authority2.py',
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
                     for key in ('cleanup', 'cleanup_release', 'cleanup_postflight', 'source_checks', 'source_review', 'authority_review', 'repair_review')})
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


def alias_census(roots, shared):
    """Account for every link, authenticate bytes, and reject aliases/races."""
    roots = tuple(map(Path, roots))
    if not roots or len(set(roots)) != len(roots):
        raise Refusal('duplicate/missing alias roots')
    for root in roots:
        if not root.is_absolute() or root.is_symlink() or root.resolve() != root or not root.is_dir():
            raise Refusal('noncanonical alias root')
    count = None
    for rel, mode, oid in shared:
        if Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise Refusal('invalid evidence path')
        if any((root / rel).resolve() != root / rel for root in roots):
            raise Refusal('noncanonical evidence alias path')
        rows = [_IMPL.snapshot(root / rel) for root in roots]
        first = rows[0]
        # nlink must be fully explained by distinct authenticated paths.
        if first['nlink'] != len(roots) or any(row != first for row in rows):
            raise Refusal('incomplete authenticated alias census: ' + rel)
        if first['mode'] != (int(mode, 8) & 0o777) or _IMPL.git(
                ROOT, 'hash-object', '--no-filters', str(roots[0] / rel)).decode().strip() != oid:
            raise Refusal('unauthenticated alias bytes/mode: ' + rel)
        if [_IMPL.snapshot(root / rel) for root in roots] != rows:
            raise Refusal('alias census raced')
        if count is not None and count != first['nlink']:
            raise Refusal('inconsistent alias link topology')
        count = first['nlink']
    if count is None:
        raise Refusal('empty alias census')
    return count


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
    links = alias_census(roots, shared)
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
