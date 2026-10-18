#!/usr/bin/env python3
"""Fixed-path archival retirement; default is read-only validation.

The persistent mutex is never unlinked. flock releases it on process death.
A torn plan/journal is retained and quarantined, never repaired speculatively.
Execution requires an independently reviewed release and runs under sudo -A.
Historical observations are frozen evidence, never execution authority.
Ownership records exchange with empty directory sentinels and remain archived.
Sentinels keep the active names occupied until durable release authorization;
only rmdir releases them, so a newer regular ownership record is never deleted.

Supported publisher contract: one campaign coordinator, no concurrent project
build/cleanup worker, and ordinary publishers creating regular files with
O_CREAT|O_EXCL. The privileged census checks these prerequisites immediately
before mutations and sentinel release. This is NOT protection against an
arbitrary same-UID adversary swapping directories between the final check and
rmdir. Such directory publishers are excluded by the execution prerequisite.
"""
import argparse
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import signal
import time

REPO = Path('/home/holden/mckernel')
PUBLISHED_SCRIPT = 'scripts/native_rust_cutover_image_terminal_cleanup.py'
PUBLISHED_TESTS = 'scripts/tests/test_native_rust_cutover_image_terminal_cleanup.py'
SELFTEST = REPO / PUBLISHED_TESTS
NAMESPACE = Path('/home/holden/mckernel-work/scratch/rust-cutover-image-preparation-20261018-1')
NAMESPACE_ANCESTRY = [{'path': '/', 'device': 66306, 'inode': 2, 'mode': 16877, 'uid': 0, 'gid': 0}, {'path': '/home', 'device': 66306, 'inode': 45481985, 'mode': 16877, 'uid': 0, 'gid': 0}, {'path': '/home/holden', 'device': 66306, 'inode': 45481986, 'mode': 16877, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work', 'device': 66306, 'inode': 47459822, 'mode': 16893, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/scratch', 'device': 1828, 'inode': 2, 'mode': 16832, 'uid': 1000, 'gid': 1000}, {'path': '/home/holden/mckernel-work/scratch/rust-cutover-image-preparation-20261018-1', 'device': 1828, 'inode': 114855, 'mode': 16832, 'uid': 1000, 'gid': 1000}]
NAMESPACE_BINDING = {'device': 1828, 'inode': 114855, 'mode': 16832, 'uid': 1000, 'gid': 1000}
ROOT = Path('/home/holden/mckernel-work/scratch')
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
DEVICE = None  # A future, independently reviewed release binds the live device.
UID = GID = 1000
PREFIX = 'native-rust-cutover-image-terminal-cleanup-20261018-1'
CANDIDATE = None  # Derived only from the exact consumed image request at release validation.
ATTEMPT = Path('/home/holden/mckernel-work/scratch/rust-cutover-image-preparation-20261018-1/common-exclusion.json')
SHARED = ROOT / 'mckernel-heavy-operation.lock'
REQUEST = Path('/home/holden/mckernel-work/scratch/rust-cutover-image-preparation-20261018-1/image-request.json')
LEASE = Path('/home/holden/mckernel-work/scratch/rust-cutover-image-preparation-20261018-1/image-lease.json')
OUTPUT = Path('/home/holden/mckernel-work/scratch/rust-cutover-image-preparation-20261018-1/owner-work')
EVIDENCE = Path('/home/holden/mckernel-work/scratch/rust-cutover-image-preparation-20261018-1/owner-evidence')
MUTEX = ROOT / (PREFIX + '.mutex')
PLAN = ROOT / (PREFIX + '.plan.json')
JOURNAL = ROOT / (PREFIX + '.journal.jsonl')
CAPTURE = ROOT / (PREFIX + '.docker-logs.capture')
QUARANTINE = ROOT / (PREFIX + '.quarantine.json')
ARCHIVE_NAMES = (PREFIX + '.attempt.archive', PREFIX + '.shared.archive')
ROOT_LOCK = Path('/run/lock/mckernel-development.lock')
BASELINE_SOURCE_SHA = '6606af40114eb5b6019438c4127948081d80bbe65144d841e906a7cba84aabed'
NATIVE_BASELINE_SOURCE_SHA = '8449b4b87b2286d4dc3d08e0c5921d2d79e44f17920d0aaee3eae646993fc995'
KNOWN_TARGET = {'container_id': 'ae9652572cfe1610a2dd07b1f6a9833ab5a849d2d171a2ee47e5fb74e5e1d8d1', 'container_name': 'mckernel-image-9c6781bb95d0423ca7f8265aaadaa858', 'owner_nonce': '34dfb8c04bd34d94923624fbadcce00d', 'owner_pid': 852997, 'owner_starttime': '9746712'}
REQUEST_SHA = '590086796ab34e9e4cccdba33e2c43abcecfadc4281eeabe9a27096a8d211954'
IMAGE_CANDIDATE = '942c927b1ec93cc31284ff498455909d9bb2d0fc'
ROOT_TERMINAL = None  # Exact future nonce-bound guard-result.json proof.
CONTAINER = CONTAINER_NAME = OWNER_NONCE = OWNER_PID = OWNER_START = None
EXPECTED_EXIT = None
# Retain the root guard and all eight historical Docker clients as census roots.
WAITER_PIDS = ()  # Future exact guard command ledger supplies every current client PID.
BOOT_ID = None
RECORDS = {}
DIRS = {}
PROTECTED = []
TERMINAL = EVIDENCE / 'owner-receipt.json'
TERMINAL_SHA = TERMINAL_INODE = TERMINAL_SIZE = None
LIMIT = 1 << 20
# Preserve the reviewed authority1 actual-size caps and complete inventory bounds.
PROTECTED_LIMIT = 128 << 20
DOCUMENT_LIMIT = 256 << 20
INVENTORY_LIMIT = 400000
RELEASE = None
ROOT_LOCK_BINDING = None
EXPECTED_CONTAINER = None
PUBLISHER_CONTRACT = {
    'schema': 'fp-save-image.publisher-contract.v1',
    'coordination': 'sole-campaign-coordinator-no-concurrent-build-or-cleanup',
    'publishers': 'project-owned-regular-file-O_CREAT|O_EXCL-only',
    'census': 'root-full-process-and-container-before-transaction-and-every-rmdir',
    'excluded': 'arbitrary-same-UID-directory-substitution-after-final-check',
}
DEFERRED_SIGNALS = {signal.SIGHUP, signal.SIGINT, signal.SIGTERM, signal.SIGQUIT}

def namespace_ancestry():
    rows = []
    for path in reversed((NAMESPACE, *NAMESPACE.parents)):
        meta = path.lstat()
        if not stat.S_ISDIR(meta.st_mode):
            raise Refusal('namespace-ancestor-not-directory')
        rows.append(dict(path=str(path), device=meta.st_dev, inode=meta.st_ino,
                         mode=meta.st_mode, uid=meta.st_uid, gid=meta.st_gid))
    return rows


def metadata_identity(path):
    """Cheap complete output/evidence census; never follow a build symlink."""
    meta = path.lstat()
    if not (stat.S_ISREG(meta.st_mode) or stat.S_ISDIR(meta.st_mode) or stat.S_ISLNK(meta.st_mode)):
        raise Refusal('protected-inventory-type:' + str(path))
    row = {'path': str(path), 'device': meta.st_dev, 'inode': meta.st_ino,
           'mode': meta.st_mode, 'uid': meta.st_uid, 'gid': meta.st_gid,
           'size': meta.st_size, 'nlink': meta.st_nlink,
           'mtime_ns': meta.st_mtime_ns, 'ctime_ns': meta.st_ctime_ns}
    if stat.S_ISLNK(meta.st_mode):
        row['target'] = os.readlink(path)
    return row

def metadata_inventory(root):
    paths = []
    for path in root.rglob('*'):
        if len(paths) + 1 >= INVENTORY_LIMIT:
            raise Refusal('protected-inventory-bound')
        paths.append(path)
    return [metadata_identity(root)] + [metadata_identity(path) for path in sorted(paths)]

def protected_files():
    """Preserve complete metadata census and only selected published byte joins."""
    if RELEASE is None:
        raise Refusal('release-not-configured')
    if os.path.lexists(LEASE):
        raise Refusal('request-lease-reappeared')
    for root in (OUTPUT, EVIDENCE):
        wanted = RELEASE['observation']['inventories'][str(root)]
        if metadata_inventory(root) != wanted:
            raise Refusal('protected-inventory-drift:' + str(root))
    if observe_identity(CANDIDATE) != RELEASE['observation']['candidate_root']:
        raise Refusal('candidate-root-drift')
    backup = RELEASE['observation']['backup_root']
    if observe_identity(Path(backup['path'])) != backup:
        raise Refusal('backup-root-drift')
    for row in PROTECTED:
        if observe_identity(Path(row['path'])) != row:
            raise Refusal('selected-artifact-or-receipt-drift:' + row['path'])

def capture_logs(present, execute=False, transaction=None):
    expected = read_bounded(EVIDENCE / 'attempt/container.log', maximum=PROTECTED_LIMIT)
    if os.path.lexists(CAPTURE):
        read_at_path(CAPTURE, expected)
        return
    if not present:
        raise Refusal('docker-log-capture-missing')
    raw = run_privileged_large(['/usr/bin/docker', '--host=unix:///var/run/docker.sock',
                                'logs', '--', CONTAINER])
    if raw != expected:
        raise Refusal('docker-log-mismatch')
    if execute:
        fd, _ = directory(ROOT)
        try:
            create_at(fd, CAPTURE.name, raw,
                      on_created=(lambda: setattr(transaction, 'mutation_started', True))
                      if transaction is not None else None)
        finally:
            os.close(fd)

def validate_container_profile(item):
    # Bind every recorded config/host-profile field, the command and exact mounts.
    for key in ('Id', 'Name', 'Image', 'Path', 'Args', 'Config', 'HostConfig', 'State',
                'Created', 'RestartCount', 'AppArmorProfile', 'Platform'):
        if canonical(item.get(key)) != canonical(EXPECTED_CONTAINER.get(key)):
            raise Refusal('container-profile-binding:' + key)
    if canonical(sorted(item.get('Mounts', []), key=lambda m: m['Destination'])) != canonical(sorted(
            EXPECTED_CONTAINER['Mounts'], key=lambda m: m['Destination'])):
        raise Refusal('container-mounts-binding')

class Refusal(ValueError):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()

def parse(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise Refusal('duplicate-json-key')
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, UnicodeError) as exc:
        raise Refusal('invalid-json') from exc

def identity(meta):
    return (meta.st_dev, meta.st_ino)

def read_bounded(path, maximum=DOCUMENT_LIMIT):
    fd, _ = directory(path.parent)
    opened = None
    try:
        opened = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        before = os.fstat(opened)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise Refusal('bounded-file-shape:' + str(path))
        chunks = []
        remaining = before.st_size + 1
        while remaining:
            raw = os.read(opened, min(remaining, 1 << 20))
            if not raw:
                break
            chunks.append(raw)
            remaining -= len(raw)
        raw = b''.join(chunks)
        after = os.fstat(opened)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_nlink', 'st_uid',
                  'st_gid', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(before, k) != getattr(after, k) for k in fields) or
                len(raw) != before.st_size or identity(before) != identity(
                    os.stat(path.name, dir_fd=fd, follow_symlinks=False))):
            raise Refusal('bounded-file-raced:' + str(path))
        return raw
    finally:
        if opened is not None:
            os.close(opened)
        os.close(fd)

def observe_identity(path):
    parent, _ = directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        meta = os.fstat(fd)
        if not (stat.S_ISREG(meta.st_mode) or stat.S_ISDIR(meta.st_mode)):
            raise Refusal('identity-type:' + str(path))
        row = {'path': str(path), 'device': meta.st_dev, 'inode': meta.st_ino,
               'mode': oct(stat.S_IMODE(meta.st_mode)), 'uid': meta.st_uid,
               'gid': meta.st_gid, 'size': meta.st_size, 'nlink': meta.st_nlink}
        if stat.S_ISREG(meta.st_mode):
            if meta.st_size > PROTECTED_LIMIT:
                raise Refusal('protected-file-size-bound:' + str(path))
            hashed = hashlib.sha256()
            remaining = meta.st_size + 1
            observed = 0
            while remaining:
                raw = os.read(fd, min(remaining, 1 << 20))
                if not raw:
                    break
                observed += len(raw)
                remaining -= len(raw)
                hashed.update(raw)
            if observed != meta.st_size:
                raise Refusal('protected-file-size-raced:' + str(path))
            row['sha256'] = hashed.hexdigest()
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_nlink', 'st_uid',
                  'st_gid', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(meta, key) != getattr(after, key) for key in fields) or
                identity(after) != identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False))):
            raise Refusal('identity-raced')
        return row
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)

def read_at_path(path, expected):
    row = observe_identity(path)
    if (row['device'] != DEVICE or row['mode'] != '0o600' or row['uid'] != UID or
            row['gid'] != GID or row['nlink'] != 1 or row['size'] != len(expected) or
            row.get('sha256') != digest(expected)):
        raise Refusal('retained-capture-bytes')

def create_at(parent, name, data, on_created=None):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=parent)
    try:
        if on_created is not None:
            on_created()
        os.fchown(fd, UID, GID)
        write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(parent)

def validate_mount():
    raw = subprocess.check_output(['/usr/bin/findmnt', '-J', '-T', str(ROOT), '-o',
                                   'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'], timeout=10)
    mounts = parse(raw)['filesystems']
    if len(mounts) != 1 or mounts[0] != RELEASE['observation']['mount']:
        raise Refusal('mount-drift')
    root = observe_identity(ROOT)
    expected = RELEASE['observation']['root']
    for key in ('path', 'device', 'inode', 'mode', 'uid', 'gid'):
        if root[key] != expected[key]:
            raise Refusal('root-identity-drift')

def validate_attempt_binding(target, request_identity):
    if (canonical({key: target.get(key) for key in KNOWN_TARGET}) != canonical(KNOWN_TARGET) or
            request_identity.get('path') != str(REQUEST) or request_identity.get('sha256') != REQUEST_SHA or
            not re.fullmatch('mckernel-image-[0-9a-f]{32}', str(target.get('container_name', ''))) or
            not re.fullmatch('[0-9a-f]{32}', str(target.get('owner_nonce', '')))):
        raise Refusal('exact-authority3-attempt-binding')

def image_request_binding(request):
    fixed = {'work_root': OUTPUT, 'owner_evidence_root': EVIDENCE,
             'output_root': OUTPUT / 'output', 'evidence_root': OUTPUT / 'evidence',
             'attempt_root': EVIDENCE / 'attempt', 'lease_path': LEASE,
             'common_exclusion_path': ATTEMPT}
    if (request.get('schema') != 'mckernel.native-exact-mckernel-image-container-request.v1' or
            request.get('candidate_sha') != IMAGE_CANDIDATE or
            any(request.get(key) != str(path) for key, path in fixed.items())):
        raise Refusal('image-request-namespace')
    for key in ('source_root', 'backup_root'):
        path = Path(request[key])
        if path != (NAMESPACE / 'materialized-source' if key == 'source_root' else ROOT / 'mckernel-exact-candidate-scratch-22-authority3-metadata-backup') or '..' in path.parts or path in (OUTPUT, EVIDENCE):
            raise Refusal('image-input-root-binding')
    return Path(request['source_root'])

def image_record_binding(path, row, owner, request, target, boot):
    common = path == ATTEMPT
    expected = {'schema': 'mckernel.native-exact-operational-exclusion.v1' if common else
                'mckernel.heavy-operation.v1', 'pid': target['owner_pid'],
                'starttime': target['owner_starttime'], 'boot_id': boot,
                'request_sha256': digest(json.dumps(request, sort_keys=True).encode()) if common else
                digest(canonical(request)), 'dev' if common else 'device': row['device'],
                'inode': row['inode']}
    if not common:
        expected['kind'] = 'image'
    if path not in (ATTEMPT, SHARED) or canonical(owner) != canonical(expected):
        raise Refusal('image-exclusion-owner-binding')

def image_layout(request):
    command = ['/driver.py', '--source-root', '/src', '--candidate-sha', request['candidate_sha'],
               '--ihk-sha', request['ihk_sha'], '--manifest', '/inputs.json',
               '--toolchain', '/toolchain.json', '--output', '/work/output',
               '--evidence', '/work/evidence', '--jobs', str(request['jobs']),
               '--timeout', str(request['timeout'])]
    mounts = [('/src', request['source_root'], 'bind', False),
              ('/inputs.json', request['source_manifest'], 'bind', False),
              ('/toolchain.json', request['toolchain_manifest'], 'bind', False),
              ('/driver.py', request['driver_path'], 'bind', False),
              ('/native_rust_exact_build_offline.py', request['provenance_path'], 'bind', False),
              ('/work', str(OUTPUT), 'bind', True)]
    if request.get('gitlink_manifest') is not None:
        mounts += [('/libdwarf-inputs.json', request['gitlink_manifest'], 'bind', False),
                   ('/src/executer/user/lib/libdwarf/libdwarf', request['gitlink_root'], 'bind', False)]
        command += ['--gitlink-manifest', '/libdwarf-inputs.json']
    roots = request['toolchain_roots']
    if (not isinstance(roots, list) or len(roots) != 2 or
            {row['container_path'] for row in roots} != {'/out', '/nightly'}):
        raise Refusal('image-v2-toolchain-mounts')
    mounts += [(row['container_path'], row['host_path'], 'bind', False) for row in roots]
    return command, sorted(mounts)

def image_owner_receipt_binding(receipt, item, receipt_sha):
    """Positive owner evidence alone never authorizes cleanup."""
    import importlib.util
    path = REPO / 'scripts/native_exact_scratch22_authority1_quarantine_recovery.py'
    spec = importlib.util.spec_from_file_location('image_receipt_mount_core', path)
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    if (receipt.get('schema') != 'mckernel.native-exact-mckernel-image-container-receipt.v1' or
            receipt.get('status') not in ('PASS', 'FAIL') or receipt.get('retired') is not True or
            receipt.get('terminal_container_retained') is not True or
            receipt.get('cleanup_separately_required') is not True or
            receipt.get('client_retirement_unproven', False) or
            receipt.get('candidate_sha') != IMAGE_CANDIDATE):
        raise Refusal('image-positive-owner-retirement')
    try:
        if core.inspect_comparison(receipt.get('terminal_container_info')) != core.inspect_comparison(item):
            raise Refusal('image-positive-owner-terminal-inspect')
    except core.Refusal as exc:
        raise Refusal('image-positive-owner-terminal-inspect') from exc


def image_receipt_binding(receipt, guard, target, item, receipt_sha):
    image_owner_receipt_binding(receipt, item, receipt_sha)
    if (canonical(receipt.get('exit_code')) != canonical(target['exit_code']) or
            (receipt.get('status') == 'PASS' and target['exit_code'] != 0) or
            any(receipt.get(key) != target[key] for key in ('container_id', 'container_name', 'owner_nonce')) or
            canonical(guard) != canonical({'owner_status': receipt['status'], 'owner_receipt_sha256': receipt_sha,
                      'container_id': target['container_id'], 'retired': True,
                      'retained_for_separate_cleanup': True, 'interrupted_signal': None})):
        raise Refusal('image-positive-owner-and-guard-retirement')


def recovery_proof_binding(binding, obs):
    import importlib.util
    path = REPO / 'scripts/native_exact_scratch22_image_retirement_reconcile.py'
    spec = importlib.util.spec_from_file_location('cleanup_image_reconciliation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.validate_proof(binding, obs)
    except module.Refusal as exc:
        raise Refusal('image-reconciliation-proof: ' + str(exc)) from exc

def typed_source_binding(request, obs, selected_map):
    expected = {
        'source_derivative_sha256': 'fcb5abc924db6a0f88c3b240aae01e94c7309b88f2f9aaaca8fdb654c329c969',
        'materialization_sha256': 'd6c3b6334a7585c6ddeab62a551f64581cd8bed721ce3b181d8764663356ebba',
    }
    manifest = NAMESPACE / 'thin-inputs.json'
    receipt_path = NAMESPACE / 'materialization-receipt.json'
    pins = {str(manifest): 'a9d573a089623e001723d102df5eccec994b924a540e992b294cb88b4955465c',
            str(receipt_path): 'ebbb262ac54c99210bfd92528d6efb1796b416954c1005df3c39eb4dbb1fe2f1'}
    if (request.get('source_identity', {}).get('inode') != 493960 or
            any(request.get(key) != value for key, value in expected.items()) or
            request.get('candidate_identity_scope') != 'base_git_commit_only'):
        raise Refusal('typed-thin-source-required')
    for path, sha in pins.items():
        row = selected_map.get(path)
        if row is None or row.get('sha256') != sha or digest(read_bounded(Path(path))) != sha:
            raise Refusal('typed-source-receipt-pin')
    receipt = parse(read_bounded(receipt_path))
    if (receipt.get('status') != 'PASS_SOURCE_MATERIALIZATION_ONLY' or
            receipt.get('source') != str(CANDIDATE) or
            any(receipt.get(key) != value for key, value in expected.items()) or
            obs['candidate_root'].get('inode') != 493960):
        raise Refusal('typed-materialization-authority')


def configure(value, execute=False):
    """Future release only. No runtime identity is inherited from scratch21."""
    global RELEASE, DEVICE, BOOT_ID, ROOT_LOCK_BINDING, EXPECTED_CONTAINER, EXPECTED_EXIT
    global CONTAINER, CONTAINER_NAME, OWNER_NONCE, OWNER_PID, OWNER_START
    global RECORDS, PROTECTED, DIRS, TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE
    global CANDIDATE, ROOT_TERMINAL, WAITER_PIDS
    RELEASE = None
    if (not isinstance(value, dict) or value.get('schema') != 'fp-save-image.cleanup-release.v1' or
            value.get('status') != 'PASS_EXECUTION_RELEASE' or
            value.get('baseline_source_sha256') != BASELINE_SOURCE_SHA or
            value.get('script_sha256') != digest(read_bounded(Path(__file__).resolve())) or
            value.get('tests_sha256') != digest(read_bounded(
                SELFTEST)) or
            value.get('publisher_contract') != PUBLISHER_CONTRACT):
        raise Refusal('cleanup-not-released')
    for key in ('source_review', 'execution_review'):
        review = value.get(key) or {}
        if (review.get('status') != 'PASS' or not review.get('reviewer') or
                review.get('reviewer') == value.get('author') or not review.get('evidence_sha256')):
            raise Refusal('independent-review-required:' + key)
    if (not value.get('author') or value.get('fetched_source_verified') is not True or
            not value.get('git_commit') or not value.get('git_tree')):
        raise Refusal('source-git-binding-required')
    commit, tree = value['git_commit'], value['git_tree']
    if any(not isinstance(item, str) or len(item) != 40 or
           any(char not in '0123456789abcdef' for char in item) for item in (commit, tree)):
        raise Refusal('source-git-shape')
    if subprocess.check_output(['/usr/bin/git', '-C', str(REPO), 'rev-parse', commit + '^{tree}'],
                               timeout=10).decode().strip() != tree:
        raise Refusal('source-git-tree-binding')
    for relative, expected in ((PUBLISHED_SCRIPT, value['script_sha256']),
                               (PUBLISHED_TESTS, value['tests_sha256'])):
        if digest(subprocess.check_output(['/usr/bin/git', '-C', str(REPO), 'show', commit + ':' + relative],
                                           timeout=10)) != expected:
            raise Refusal('source-git-blob-binding')
    obs = value.get('observation') or {}
    required = {'mount', 'root', 'boot_id', 'root_lock', 'request', 'target', 'container_inspect',
                'retained_exclusions', 'request_lease_absent', 'inventories', 'candidate_root',
                'candidate_commit', 'candidate_tree', 'selected_files', 'backup_root', 'namespace_binding', 'namespace_ancestry', 'client_ledger'}
    proof_keys = set(obs) & {'guard_proof', 'recovery_proof'}
    if len(proof_keys) != 1:
        raise Refusal('exactly-one-positive-retirement-proof-required')
    proof_key = next(iter(proof_keys))
    required.add(proof_key)
    if set(obs) != required or obs.get('request_lease_absent') is not True:
        raise Refusal('future-runtime-observation-required')
    mount = obs['mount']
    if (mount.get('target') != str(ROOT) or mount.get('uuid') != UUID or
            mount.get('fstype') != 'ext4' or obs['boot_id'] != '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' or
            not {'rw', 'nodev', 'nosuid'} <= set(mount.get('options', '').split(','))):
        raise Refusal('fresh-mount-binding')
    device = obs['root'].get('device')
    if type(device) is not int or device <= 0 or obs['root'].get('path') != str(ROOT):
        raise Refusal('fresh-root-binding')
    if obs['namespace_binding'] != NAMESPACE_BINDING or obs['namespace_ancestry'] != NAMESPACE_ANCESTRY or namespace_ancestry() != NAMESPACE_ANCESTRY:
        raise Refusal('exact-namespace-binding')
    client_rows = obs['client_ledger']
    if not isinstance(client_rows, list) or not client_rows or any(set(r) != {'pid', 'status_path', 'status_sha256'} or type(r['pid']) is not int or r['pid'] <= 0 for r in client_rows):
        raise Refusal('positive-client-ledger-required')
    guard_capture = ROOT / 'native-rust-cutover-image-guard-20261018-2f005fdaeda24f1c91704b6f0ff830c4'
    if {r['status_path'] for r in client_rows} != {str(p) for p in guard_capture.glob('command-*/status.json')} or any(Path(r['status_path']).parent.parent != guard_capture for r in client_rows):
        raise Refusal('complete-current-guard-client-ledger-required')
    for row in client_rows:
        status = parse(read_bounded(Path(row['status_path'])))
        if digest(read_bounded(Path(row['status_path']))) != row['status_sha256'] or status.get('pid') != row['pid'] or status.get('state') != 'exited' or type(status.get('exit_code')) is not int or status['exit_code'] < 0 or status.get('client_retirement_unproven'):
            raise Refusal('positive-client-status-required')
    WAITER_PIDS = tuple(r['pid'] for r in client_rows)
    if len(set(WAITER_PIDS)) != len(WAITER_PIDS):
        raise Refusal('duplicate-client-pid')
    target, item = obs['target'], obs['container_inspect']
    keys = {'container_id', 'container_name', 'owner_nonce', 'image_id', 'owner_pid', 'owner_starttime', 'exit_code'}
    if (set(target) != keys or type(target['owner_pid']) is not int or target['owner_pid'] <= 0 or
            not isinstance(target['owner_starttime'], str) or not target['owner_starttime'].isdigit() or
            type(target['exit_code']) is not int or not 0 <= target['exit_code'] <= 255 or
            not isinstance(target['container_id'], str) or len(target['container_id']) != 64 or
            any(char not in '0123456789abcdef' for char in target['container_id']) or
            not target['container_name'] or not target['owner_nonce']):
        raise Refusal('future-owner-binding')
    validate_attempt_binding(target, obs['request'])
    state = item.get('State', {})
    wanted_state = {'Status': 'exited', 'Running': False, 'Paused': False, 'Restarting': False,
                    'OOMKilled': False, 'Dead': False, 'Pid': 0, 'ExitCode': target['exit_code'], 'Error': ''}
    if (any(canonical(state.get(key)) != canonical(wanted) for key, wanted in wanted_state.items()) or
            item.get('Id') != target['container_id'] or item.get('Name') != '/' + target['container_name'] or
            item.get('Image') != target['image_id'] or
            item.get('Config', {}).get('Labels', {}).get('mckernel.owner') != target['owner_nonce']):
        raise Refusal('exact-terminal-container-binding')
    lock = obs['root_lock']
    if (lock.get('path') != str(ROOT_LOCK) or lock.get('uid') != 0 or lock.get('gid') != 0 or
            lock.get('mode') != '0o644' or lock.get('nlink') != 1 or lock.get('size') != 0 or
            lock.get('sha256') != digest(b'') or type(lock.get('device')) is not int or
            type(lock.get('inode')) is not int or (lock['device'], lock['inode']) != (27, 4)):
        raise Refusal('fresh-root-lock-binding')
    if observe_identity(REQUEST) != obs['request']:
        raise Refusal('exact-request-binding')
    request = parse(read_bounded(REQUEST))
    CANDIDATE = image_request_binding(request)
    if request.get('candidate_sha') != obs['candidate_commit'] or request.get('image_id') != target['image_id']:
        raise Refusal('request-candidate-image-binding')
    config, host = item.get('Config', {}), item.get('HostConfig', {})
    profile = {'CpusetCpus': '2-5', 'NanoCpus': 4000000000, 'Memory': 12884901888,
               'MemorySwap': 12884901888, 'PidsLimit': 512, 'NetworkMode': 'none',
               'IpcMode': 'private', 'ReadonlyRootfs': True, 'Privileged': False,
               'CapDrop': ['ALL'], 'Init': True, 'SecurityOpt': ['no-new-privileges'],
               'Tmpfs': {'/tmp': 'rw,nodev,nosuid,size=256m'},
               'RestartPolicy': {'MaximumRetryCount': 0, 'Name': 'no'}, 'AutoRemove': False}
    expected_args, expected_mounts = image_layout(request)
    if (any(canonical(host.get(key)) != canonical(wanted) for key, wanted in profile.items()) or
            config.get('User') != '1000:1000' or config.get('Entrypoint') != ['/usr/bin/python3'] or
            config.get('Cmd') != expected_args or item.get('Args') != expected_args or
            item.get('Path') != '/usr/bin/python3' or config.get('Image') != target['image_id']):
        raise Refusal('reviewed-container-profile')
    if sorted((m.get('Destination'), m.get('Source'), m.get('Type'), m.get('RW'))
              for m in item.get('Mounts', []) if m.get('Type') == 'bind') != expected_mounts:
        raise Refusal('exact-image-mounts')
    extra_mounts = [m for m in item.get('Mounts', []) if m.get('Type') != 'bind']
    if extra_mounts and (len(extra_mounts) != 1 or extra_mounts[0].get('Type') != 'tmpfs' or
                         extra_mounts[0].get('Destination') != '/tmp' or extra_mounts[0].get('RW') is not True):
        raise Refusal('unexpected-image-mount')
    records = obs['retained_exclusions']
    if len(records) != 2 or {r['path'] for r in records} != {str(ATTEMPT), str(SHARED)}:
        raise Refusal('exact-exclusions-required')
    for row in records:
        if (row.get('device') != device or row.get('uid') != UID or row.get('gid') != GID or
                row.get('mode') != '0o600' or row.get('nlink') != 1 or
                type(row.get('inode')) is not int or row['inode'] <= 0 or
                observe_identity(Path(row['path'])) != row):
            raise Refusal('future-exclusion-binding')
        owner = parse(read_bounded(Path(row['path'])))
        image_record_binding(Path(row['path']), row, owner, request, target, obs['boot_id'])
    selected = obs['selected_files']
    selected_map = {r['path']: r for r in selected}
    if len(selected_map) != len(selected):
        raise Refusal('duplicate-selected-file')
    ROOT_TERMINAL = Path(obs[proof_key]['path'])
    if proof_key == 'guard_proof' and (ROOT_TERMINAL.name != 'guard-result.json' or ROOT_TERMINAL.parent.parent != ROOT or
            ROOT_TERMINAL.parent.name != 'native-rust-cutover-image-guard-20261018-2f005fdaeda24f1c91704b6f0ff830c4'):
        raise Refusal('image-guard-proof-path')
    joins = {'driver_path': 'driver_sha256', 'provenance_path': 'provenance_sha256',
             'host_owner_path': 'host_owner_sha256', 'source_manifest': 'source_manifest_sha256',
             'toolchain_manifest': 'toolchain_manifest_sha256'}
    if request.get('gitlink_manifest') is not None:
        joins['gitlink_manifest'] = 'gitlink_manifest_sha256'
    needed = {str(REQUEST), str(TERMINAL), str(ROOT_TERMINAL), str(EVIDENCE / 'attempt/container.log'),
              str(OUTPUT / 'evidence/receipt.json')}
    if target['exit_code'] == 0:
        needed.update(str(OUTPUT / relative) for relative in
                      ('output/build/kernel/mckernel.img', 'evidence/artifacts/mckernel.img'))
    needed.update(request[key] for key in joins)
    needed.update(row['status_path'] for row in client_rows)
    if not needed <= set(selected_map):
        raise Refusal('complete-receipt-and-source-joins-required')
    for key, hash_key in joins.items():
        if selected_map[request[key]].get('sha256') != request[hash_key]:
            raise Refusal('request-source-hash-binding')
    if selected_map[str(ROOT_TERMINAL)] != obs[proof_key]:
        raise Refusal('exact-image-guard-proof-binding')
    if proof_key == 'guard_proof':
        image_receipt_binding(parse(read_bounded(TERMINAL)), parse(read_bounded(ROOT_TERMINAL)),
                              target, item, selected_map[str(TERMINAL)]['sha256'])
    else:
        recovery_proof_binding(obs[proof_key], obs)
    if target['exit_code'] == 0 and not any(r.get('sha256') and
                                            str(r['path']).startswith(str(OUTPUT) + '/')
                                            for r in selected):
        raise Refusal('successful-output-artifact-required')
    if set(obs['inventories']) != {str(OUTPUT), str(EVIDENCE)}:
        raise Refusal('complete-inventories-required')
    if obs['candidate_root'].get('path') != str(CANDIDATE):
        raise Refusal('candidate-root-required')
    for key, row in (('source_identity', obs['candidate_root']), ('backup_identity', obs['backup_root'])):
        expected = request[key]
        if any(canonical(expected.get(k)) != canonical(v) for k, v in {
                'path': row['path'], 'dev': row['device'], 'inode': row['inode'],
                'uid': row['uid'], 'gid': row['gid'], 'mode': int(row['mode'], 8),
                'file_type': stat.S_IFDIR}.items()):
            raise Refusal('image-source-or-backup-identity')
    if obs['backup_root']['path'] != request['backup_root']:
        raise Refusal('image-backup-path')
    typed_source_binding(request, obs, selected_map)
    for path in (OUTPUT, EVIDENCE):
        if obs['inventories'][str(path)][0]['path'] != str(path):
            raise Refusal('inventory-root-binding')
    if value.get('transaction_paths') != transaction_paths():
        raise Refusal('transaction-path-binding')
    RELEASE, DEVICE, BOOT_ID = value, device, obs['boot_id']
    ROOT_LOCK_BINDING, EXPECTED_CONTAINER, EXPECTED_EXIT = lock, item, target['exit_code']
    CONTAINER, CONTAINER_NAME, OWNER_NONCE = target['container_id'], target['container_name'], target['owner_nonce']
    OWNER_PID, OWNER_START = target['owner_pid'], target['owner_starttime']
    RECORDS = {Path(r['path']): (r['sha256'], r['inode'], r['size']) for r in records}
    PROTECTED = selected
    terminal = selected_map[str(TERMINAL)]
    TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE = terminal['sha256'], terminal['inode'], terminal['size']
    DIRS = {path: (obs['inventories'][str(path)][0]['inode'],
                   obs['inventories'][str(path)][0]['nlink']) for path in (OUTPUT, EVIDENCE)}
    validate_mount()
    protected_files()

def transaction_paths():
    return [str(path) for path in (MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE)] + [
        str(ROOT / name) for name in ARCHIVE_NAMES]

def prepare_release(observation, git_commit, git_tree):
    """Bind only a supplied future runtime observation; always emit an unreleased draft."""
    return {'schema': 'fp-save-image.cleanup-release.v1', 'status': 'NOT_RELEASED',
            'author': None, 'script_sha256': digest(read_bounded(Path(__file__).resolve())),
            'tests_sha256': digest(read_bounded(SELFTEST)),
            'baseline_source_sha256': BASELINE_SOURCE_SHA, 'git_commit': git_commit, 'git_tree': git_tree,
            'fetched_source_verified': False, 'source_review': None, 'execution_review': None,
            'publisher_contract': PUBLISHER_CONTRACT, 'observation': observation,
            'transaction_paths': transaction_paths()}

def quarantine_wait():
    """Nonreturning hold. Signal deferral starts before transaction acquisition."""
    while True:
        try:
            time.sleep(60)
        except BaseException:
            # Diagnostics, handlers and interrupted waits cannot surrender ownership.
            # SIGKILL is intentionally outside this contract; sentinels survive it.
            pass

def terminal_result(status, plan):
    return {'schema': 'fp-save-image.cleanup-result.v1', 'status': status, 'terminal': True,
            'container_absent': True, 'container_id': CONTAINER, 'filesystem_uuid': UUID,
            'boot_id': BOOT_ID, 'release_sha256': digest(canonical(RELEASE)),
            'plan_sha256': digest(canonical(plan)),
            'plan': observe_identity(PLAN), 'journal': observe_identity(JOURNAL),
            'capture': observe_identity(CAPTURE),
            'archives': [observe_identity(ROOT / name) for name in ARCHIVE_NAMES],
            'publisher_contract': PUBLISHER_CONTRACT}

def directory(path):
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('noncanonical-directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    chain = [identity(os.fstat(fd))]
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
            chain.append(identity(os.fstat(fd)))
        return fd, chain
    except BaseException:
        os.close(fd)
        raise

def exists(fd, name):
    try:
        os.stat(name, dir_fd=fd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False

def read_at(fd, name, binding=None):
    opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    try:
        before = os.fstat(opened)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
            before.st_dev != DEVICE or before.st_size > LIMIT or
            stat.S_IMODE(before.st_mode) != 0o600 or
            (before.st_uid, before.st_gid) != (UID, GID)):
            raise Refusal('file-shape:' + name)
        data = bytearray()
        while len(data) <= before.st_size:
            chunk = os.read(opened, min(65536, before.st_size + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        after = os.fstat(opened)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(before, k) != getattr(after, k) for k in fields) or
            len(data) != before.st_size or
            identity(os.stat(name, dir_fd=fd, follow_symlinks=False)) != identity(before)):
            raise Refusal('file-raced:' + name)
        if binding is not None and (digest(data), before.st_ino, before.st_size) != binding:
            raise Refusal('file-binding:' + name)
        return bytes(data), before
    finally:
        os.close(opened)

def write_all(fd, data):
    while data:
        count = os.write(fd, data)
        if count <= 0:
            raise Refusal('write-no-progress')
        data = data[count:]

def rename_exchange(fd, source, destination, destination_fd=None):
    destination_fd = fd if destination_fd is None else destination_fd
    """Atomically leave a directory sentinel at the active ownership name."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise Refusal('renameat2-unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(fd, os.fsencode(source), destination_fd, os.fsencode(destination), 2):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))

# Executed only by root's absolute Python, isolated from caller modules/env.
# Every listed stat must read/parse; disappearing processes cause a retryable
# refusal. Two full snapshots and unchanged boot identity authenticate scope.
PROC_CODE = r'''
import json,os,sys
caller=[int(sys.argv[2]),sys.argv[3]]
caller_parent=int(open('/proc/'+str(caller[0])+'/stat','rb').read().rpartition(b') ')[2].split()[1])
heavy={'qemu-system-x86_64','qemu-system-aarch64','qemu-kvm','mcexec','firecracker',
       'rustc','cargo','make','ninja','buildah','gcc','g++','cc','clang','clang++'}
def publisher(exe,argv):
    name=os.path.basename(exe[:-10] if exe.endswith(' (deleted)') else exe)
    if name in heavy or name.startswith('qemu-system-'): return True
    if name in ('docker','podman') and any(a in ('build','run','start') for a in argv[1:]): return True
    for arg in argv:
        base=os.path.basename(arg)
        if (base.startswith(('native_rust_exact_','native-exact-','native_exact_')) and
            base.endswith(('.py','.sh')) and any(term in base for term in ('build','cleanup','recovery','prepare'))): return True
    return False
def snapshot():
    rows=[]; publishers=[]; found=False
    entries=os.listdir('/proc')
    if len(entries)>4096: raise ValueError('process-count')
    for name in entries:
        if not name.isdigit(): continue
        pid=int(name)
        with open('/proc/'+name+'/stat','rb') as f: raw=f.read(65537)
        if len(raw)>65536: raise ValueError('stat-size')
        left,sep,right=raw.rpartition(b') ')
        if not sep or not left.startswith(str(pid).encode()+b' ('): raise ValueError('stat-prefix')
        fields=right.split()
        if len(fields)<50 or fields[0] not in (b'R',b'S',b'D',b'Z',b'T',b't',b'X',b'x',b'K',b'W',b'P',b'I'): raise ValueError('stat-fields')
        for field in fields[1:]:
            digits=field[1:] if field.startswith(b'-') else field
            if not digits or any(c<48 or c>57 for c in digits): raise ValueError('stat-number')
        ppid=int(fields[1]); start=int(fields[19])
        if ppid<0 or start<0: raise ValueError('stat-number')
        with open('/proc/'+name+'/cmdline','rb') as f: command=f.read(65537)
        if len(command)>65536 or (command and not command.endswith(b'\0')): raise ValueError('cmdline-size-or-termination')
        argv=[a.decode('utf-8','strict') for a in command[:-1].split(b'\0')] if command else []
        if len(argv)>256 or any(len(a)>16384 for a in argv): raise ValueError('cmdline-arguments')
        if not argv and fields[0] not in (b'Z',b'X',b'x') and not (int(fields[6]) & 0x200000): raise ValueError('live-cmdline-empty')
        exe=os.readlink('/proc/'+name+'/exe') if argv else ''
        with open('/proc/'+name+'/stat','rb') as f: again=f.read(65537)
        check=again.rpartition(b') ')[2].split()
        if len(check)<50 or check[19]!=fields[19]: raise ValueError('process-raced')
        if pid==caller[0]:
            if str(start)!=caller[1]: raise ValueError('caller-raced')
            found=True
        elif argv and not (pid==caller_parent and os.path.basename(exe)=='sudo') and publisher(exe,argv): publishers.append([pid,str(start),exe])
        rows.append([pid,ppid,str(start)])
    if not found: raise ValueError('caller-missing')
    return sorted(rows),publishers
if os.geteuid()!=0: raise ValueError('not-root')
with open('/proc/sys/kernel/random/boot_id') as f: boot=f.read().strip()
first,pubs1=snapshot(); second,pubs2=snapshot()
with open('/proc/sys/kernel/random/boot_id') as f: after=f.read().strip()
if boot!=after: raise ValueError('boot-raced')
print(json.dumps({'schema':'fp-save-image.proc.v1','uid':os.geteuid(),'boot_id':boot,
                  'challenge':sys.argv[1],'caller':caller,'publishers':pubs1+pubs2,'snapshots':[first,second]}))
'''

def run_privileged(args):
    return root_command(args, LIMIT)

def run_privileged_large(args):
    return root_command(args, PROTECTED_LIMIT)

def root_command(args, limit):
    if os.geteuid() != 0:
        raise Refusal('root-execution-required-use-sudo-A')
    result = subprocess.run(args, env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'},
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30, check=False)
    if result.returncode or result.stderr or len(result.stdout) > limit:
        raise Refusal('root-command-failed:' + args[0])
    return result.stdout

def validate_process_report(report, challenge, caller):
    if (not isinstance(report, dict) or set(report) != {'schema','uid','boot_id','challenge','caller','publishers','snapshots'} or
        report['schema'] != 'fp-save-image.proc.v1' or type(report['uid']) is not int or report['uid'] != 0 or
        report['boot_id'] != BOOT_ID or report['challenge'] != challenge or report['caller'] != caller or
        not isinstance(report['snapshots'], list) or len(report['snapshots']) != 2):
        raise Refusal('process-report-binding')
    if report['publishers'] != []:
        raise Refusal('concurrent-build-or-cleanup-publisher')
    combined = {}
    for snapshot in report['snapshots']:
        if not isinstance(snapshot, list) or not snapshot:
            raise Refusal('process-snapshot-shape')
        seen = set()
        for row in snapshot:
            if (not isinstance(row, list) or len(row) != 3 or type(row[0]) is not int or row[0] <= 0 or
                type(row[1]) is not int or row[1] < 0 or not isinstance(row[2], str) or
                not row[2].isdigit() or row[0] in seen):
                raise Refusal('process-row-shape')
            seen.add(row[0])
            if row[0] == caller[0] and row[2] != caller[1]:
                raise Refusal('process-caller-binding')
            combined.setdefault(row[0], set()).add(row[1])
        if 1 not in seen or caller[0] not in seen:
            raise Refusal('process-snapshot-incomplete')
    related = {OWNER_PID, *WAITER_PIDS}
    while True:
        expanded = related | {pid for pid, parents in combined.items() if parents & related}
        if expanded == related:
            break
        related = expanded
    if related & set(combined):
        # PID reuse is also refused, including a changed owner starttime.
        raise Refusal('owner-waiter-or-descendant-present')

def process_absent():
    challenge = os.urandom(24).hex()
    raw_stat = Path('/proc/self/stat').read_bytes()
    caller = [os.getpid(), raw_stat.rpartition(b') ')[2].split()[19].decode('ascii')]
    raw = run_privileged(['/usr/bin/python3', '-I', '-B', '-c', PROC_CODE, challenge, str(caller[0]), caller[1]])
    validate_process_report(parse(raw), challenge, caller)

def docker(args):
    return run_privileged(['/usr/bin/docker', '--host=unix:///var/run/docker.sock', *args])

def census():
    process_absent()
    raw = docker(['ps', '-a', '--no-trunc', '--format', '{{json .}}'])
    candidates = []
    seen = set()
    for line in raw.splitlines():
        item = parse(line)
        if (not isinstance(item, dict) or not isinstance(item.get('ID'), str) or len(item['ID']) != 64 or
            any(c not in '0123456789abcdef' for c in item['ID']) or
            not isinstance(item.get('Names'), str) or not isinstance(item.get('Labels'), str) or
            item.get('State') not in ('created','restarting','running','removing','paused','exited','dead') or item['ID'] in seen):
            raise Refusal('container-inventory-shape')
        if item['State'] in ('running','restarting','paused','removing'):
            raise Refusal('concurrent-active-container')
        seen.add(item['ID'])
        labels = item['Labels'].split(',')
        if item['ID'] == CONTAINER or item['Names'] == CONTAINER_NAME or 'mckernel.owner='+OWNER_NONCE in labels:
            candidates.append(item)
    if not candidates:
        return False
    if len(candidates) != 1 or candidates[0]['ID'] != CONTAINER or candidates[0]['Names'] != CONTAINER_NAME:
        raise Refusal('container-inventory-binding')
    data = parse(docker(['inspect', '--type', 'container', CONTAINER]))
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise Refusal('container-inspect-shape')
    item = data[0]
    state = item.get('State')
    config = item.get('Config')
    if (not isinstance(state, dict) or not isinstance(config, dict) or
        item.get('Id') != CONTAINER or item.get('Name') != '/' + CONTAINER_NAME or
        not isinstance(config.get('Labels'), dict) or config['Labels'].get('mckernel.owner') != OWNER_NONCE or
        state.get('Status') != 'exited' or type(state.get('ExitCode')) is not int or state['ExitCode'] != EXPECTED_EXIT or
        state.get('Running') is not False or state.get('Pid') != 0):
        raise Refusal('container-retirement-binding')
    validate_container_profile(item)
    return True

class Transaction:
    def __init__(self):
        self.fd = self.mfd = self.rfd = self.nfd = None
        self.mutation_started = False
        self.root_locked = False
        if RELEASE is None:
            raise Refusal('release-not-configured')
        self.rfd = os.open(ROOT_LOCK, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            if observe_identity(ROOT_LOCK) != ROOT_LOCK_BINDING:
                raise Refusal('root-lock-binding')
            fcntl.flock(self.rfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.root_locked = True
            if identity(os.fstat(self.rfd)) != (ROOT_LOCK_BINDING['device'], ROOT_LOCK_BINDING['inode']):
                raise Refusal('root-lock-replaced')
            self.fd, self.chain = directory(ROOT)
            self.nfd, self.namespace_chain = directory(NAMESPACE)
            self.pinned()
        except BaseException:
            self.close()
            raise
        if os.fstat(self.fd).st_dev != DEVICE:
            self.close()
            raise Refusal('scratch-device')
        for path in (ATTEMPT, SHARED, MUTEX, PLAN, JOURNAL, CAPTURE, OUTPUT, EVIDENCE):
            wanted_parent = NAMESPACE if path in (ATTEMPT, OUTPUT, EVIDENCE) else ROOT
            if path.parent != wanted_parent:
                self.close()
                raise Refusal('fixed-path-parent')

    def parent_fd(self, path):
        if path in (ATTEMPT, OUTPUT, EVIDENCE) and path.parent == NAMESPACE:
            return self.nfd
        if path in (SHARED, MUTEX, PLAN, JOURNAL, CAPTURE, QUARANTINE) and path.parent == ROOT:
            return self.fd
        raise Refusal('unmapped-fixed-path')

    def close(self):
        for name in ('mfd', 'nfd', 'fd', 'rfd'):
            fd = getattr(self, name, None)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)
        self.root_locked = False

    def pinned(self):
        validate_mount()
        if (observe_identity(ROOT_LOCK) != ROOT_LOCK_BINDING or
                identity(os.fstat(self.rfd)) != (ROOT_LOCK_BINDING['device'], ROOT_LOCK_BINDING['inode'])):
            raise Refusal('root-lock-replaced')
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != BOOT_ID:
            raise Refusal('boot-drift')
        fd, chain = directory(ROOT)
        os.close(fd)
        if chain != self.chain:
            raise Refusal('ancestor-replaced')
        nfd, nchain = directory(NAMESPACE)
        try:
            meta = os.fstat(nfd)
            actual = dict(device=meta.st_dev, inode=meta.st_ino, mode=meta.st_mode, uid=meta.st_uid, gid=meta.st_gid)
            if (actual != NAMESPACE_BINDING or namespace_ancestry() != NAMESPACE_ANCESTRY or nchain != self.namespace_chain or
                    identity(os.fstat(self.nfd)) != identity(meta) or meta.st_dev != DEVICE):
                raise Refusal('namespace-parent-replaced')
        finally:
            os.close(nfd)
        if self.mfd is not None and identity(os.stat(MUTEX.name, dir_fd=self.fd, follow_symlinks=False)) != identity(os.fstat(self.mfd)):
            raise Refusal('mutex-replaced')

    def preserved(self):
        self.pinned()
        for path, (inode, nlink) in DIRS.items():
            fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.parent_fd(path))
            try:
                meta = os.fstat(fd)
                if (identity(meta) != (DEVICE, inode) or meta.st_nlink != nlink or
                    stat.S_IMODE(meta.st_mode) != 0o700 or (meta.st_uid, meta.st_gid) != (UID, GID)):
                    raise Refusal('preserved-directory-binding')
                if path == EVIDENCE:
                    read_at(fd, TERMINAL.name, (TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE))
                if identity(os.stat(path.name, dir_fd=self.parent_fd(path), follow_symlinks=False)) != identity(meta):
                    raise Refusal('preserved-directory-raced')
            finally:
                os.close(fd)

    def lock(self, execute):
        self.pinned()
        if not exists(self.fd, MUTEX.name):
            if not execute:
                return
            try:
                self.mfd = os.open(MUTEX.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
                self.mutation_started = True
                os.fchown(self.mfd, UID, GID)
            except FileExistsError:
                pass
        if self.mfd is None:
            self.mfd = os.open(MUTEX.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        meta = os.fstat(self.mfd)
        if (not stat.S_ISREG(meta.st_mode) or identity(meta)[0] != DEVICE or meta.st_size != 0 or
            meta.st_nlink != 1 or stat.S_IMODE(meta.st_mode) != 0o600 or (meta.st_uid, meta.st_gid) != (UID, GID)):
            raise Refusal('mutex-binding')
        try:
            fcntl.flock(self.mfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refusal('cleanup-busy') from exc
        self.pinned()
        if execute:
            os.fsync(self.mfd)
            os.fsync(self.fd)

    def expected_plan(self, sentinels):
        return {'schema': 'fp-save-image.terminal-cleanup.v1', 'root': str(ROOT),
                'release_sha256': digest(canonical(RELEASE)),
                'filesystem_uuid': UUID, 'root_lock': ROOT_LOCK_BINDING,
                'ancestry': [list(x) for x in self.chain], 'device': DEVICE,
                'mutex': list(identity(os.fstat(self.mfd))) if self.mfd is not None else None,
                'journal_identity': list(identity(os.stat(JOURNAL.name, dir_fd=self.fd, follow_symlinks=False)))
                    if exists(self.fd, JOURNAL.name) else None,
                'owner': [BOOT_ID, OWNER_PID, OWNER_START], 'waiters': list(WAITER_PIDS),
                'container': [CONTAINER, CONTAINER_NAME, OWNER_NONCE],
                'namespace': {'path': str(NAMESPACE), 'binding': NAMESPACE_BINDING, 'ancestry': NAMESPACE_ANCESTRY, 'chain': [list(x) for x in self.namespace_chain]},
                'records': [[str(p), str(p.parent), archive, *RECORDS[p]]
                            for p, archive in zip((ATTEMPT, SHARED), ARCHIVE_NAMES)],
                'sentinels': sentinels,
                'publisher_contract': PUBLISHER_CONTRACT,
                'directories': [[p.name, *DIRS[p]] for p in (OUTPUT, EVIDENCE)],
                'terminal': [TERMINAL.name, TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE]}

    def pristine(self):
        self.preserved()
        if exists(self.fd, JOURNAL.name):
            raise Refusal('journal-without-plan')
        for path, archive in zip((ATTEMPT, SHARED), ARCHIVE_NAMES):
            read_at(self.parent_fd(path), path.name, RECORDS[path])
            if exists(self.fd, archive):
                # A crash during preparation has not touched any active record.
                # Retain unbound preparation, rather than adopt a foreign dir.
                raise Refusal('unbound-sentinel-preparation')

    def sentinel(self, name, expected, parent_fd=None):
        parent_fd = self.fd if parent_fd is None else parent_fd
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
        try:
            meta = os.fstat(fd)
            if (meta.st_dev != DEVICE or list(identity(meta)) != expected or meta.st_nlink != 2 or
                stat.S_IMODE(meta.st_mode) != 0o700 or (meta.st_uid, meta.st_gid) != (UID, GID) or
                os.listdir(fd)):
                raise Refusal('sentinel-binding')
            if identity(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != identity(meta):
                raise Refusal('sentinel-raced')
        finally:
            os.close(fd)

    def load_plan(self):
        raw, _ = read_at(self.fd, PLAN.name)
        value = parse(raw)
        sentinels = value.get('sentinels') if isinstance(value, dict) else None
        if (not isinstance(sentinels, list) or len(sentinels) != 2 or
            any(not isinstance(row, list) or len(row) != 2 or
                type(row[0]) is not int or row[0] != DEVICE or
                type(row[1]) is not int or row[1] <= 0 for row in sentinels) or
            len({tuple(row) for row in sentinels}) != 2):
            raise Refusal('plan-sentinel-binding')
        plan = self.expected_plan(sentinels)
        if raw != canonical(plan) + b'\n':
            raise Refusal('plan-binding')
        return plan

    def prepare(self):
        self.pristine()
        sentinels = []
        for archive in ARCHIVE_NAMES:
            self.pinned()
            os.mkdir(archive, 0o700, dir_fd=self.fd)
            self.mutation_started = True
            fd = os.open(archive, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
            try:
                os.fchown(fd, UID, GID)
                expected = list(identity(os.fstat(fd)))
                self.sentinel(archive, expected)
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(self.fd)
            sentinels.append(expected)
        self.create(JOURNAL.name, b'')
        plan = self.expected_plan(sentinels)
        self.create(PLAN.name, canonical(plan) + b'\n')
        return plan

    def create(self, name, data):
        self.pinned()
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        self.mutation_started = True
        try:
            os.fchown(fd, UID, GID)
            write_all(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.fd)

    def state(self, plan):
        self.preserved()
        if exists(self.fd, PLAN.name):
            raw, _ = read_at(self.fd, PLAN.name)
            if raw != canonical(plan) + b'\n':
                raise Refusal('plan-binding')
        else:
            raise Refusal('missing-plan')
        rows = []
        if exists(self.fd, JOURNAL.name):
            raw, _ = read_at(self.fd, JOURNAL.name)
            if raw and not raw.endswith(b'\n'):
                raise Refusal('torn-journal')
            rows = [parse(line) for line in raw.splitlines()]
        legal = [(event, index) for index in range(2)
                 for event in ('before_exchange', 'after_exchange', 'release', 'after_release')] + [('complete', 2)]
        if len(rows) > len(legal):
            raise Refusal('journal-after-complete')
        previous = digest(canonical(plan))
        for seq, row in enumerate(rows):
            event, index = legal[seq]
            body = {'event': event, 'index': index, 'sequence': seq,
                    'plan_sha256': digest(canonical(plan)), 'previous': previous,
                    'plan_identity': list(identity(os.stat(PLAN.name, dir_fd=self.fd, follow_symlinks=False)))}
            wanted = dict(body, hash=digest(canonical(body)))
            if canonical(row) != canonical(wanted) or canonical(row) + b'\n' != raw.splitlines(keepends=True)[seq]:
                raise Refusal('journal-prefix-binding')
            previous = wanted['hash']
        paths = (ATTEMPT, SHARED)
        actual = []
        for index, path in enumerate(paths):
            phase = min(max(len(rows) - 4 * index, 0), 4)
            archive = ARCHIVE_NAMES[index]
            sentinel = plan['sentinels'][index]
            archived_meta = os.stat(archive, dir_fd=self.fd, follow_symlinks=False)
            if stat.S_ISDIR(archived_meta.st_mode):
                if phase not in (0, 1):
                    raise Refusal('exchange-state-regression')
                self.sentinel(archive, sentinel)
                read_at(self.parent_fd(path), path.name, RECORDS[path])
                actual.append('before_exchange')
                continue
            read_at(self.fd, archive, RECORDS[path])
            if phase == 0:
                raise Refusal('unplanned-exchange')
            if exists(self.parent_fd(path), path.name):
                active_meta = os.stat(path.name, dir_fd=self.parent_fd(path), follow_symlinks=False)
                if stat.S_ISDIR(active_meta.st_mode):
                    if phase == 4:
                        raise Refusal('sentinel-reappeared-after-release')
                    self.sentinel(path.name, sentinel, self.parent_fd(path))
                    actual.append('after_exchange')
                    continue
                # A fresh ordinary owner may acquire the name after release.
                # Validate its shape only; never remove or claim its ownership.
                read_at(self.parent_fd(path), path.name)
            if phase < 3:
                raise Refusal('unauthorized-sentinel-release')
            actual.append('after_release')
        return rows, actual

    def append(self, plan, rows, event, index):
        self.pinned()
        raw, before = read_at(self.fd, JOURNAL.name)
        if raw != b''.join(canonical(row) + b'\n' for row in rows):
            raise Refusal('journal-raced')
        body = {'event': event, 'index': index, 'sequence': len(rows),
                'plan_sha256': digest(canonical(plan)),
                'plan_identity': list(identity(os.stat(PLAN.name, dir_fd=self.fd, follow_symlinks=False))),
                'previous': rows[-1]['hash'] if rows else digest(canonical(plan))}
        row = dict(body, hash=digest(canonical(body)))
        fd = os.open(JOURNAL.name, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=self.fd)
        try:
            if identity(os.fstat(fd)) != identity(before):
                raise Refusal('journal-replaced')
            write_all(fd, canonical(row) + b'\n')
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.fd)
        rows.append(row)

    def run(self, execute):
        if os.path.lexists(QUARANTINE):
            raise Refusal('quarantined-independent-reconciliation-required')
        self.lock(execute)
        protected_files()
        if execute and exists(self.fd, PLAN.name):
            self.mutation_started = True  # Reconciliation owns a prior transaction.
        plan = self.load_plan() if exists(self.fd, PLAN.name) else None
        if plan is None:
            if execute and (exists(self.fd, JOURNAL.name) or any(
                    exists(self.fd, name) for name in ARCHIVE_NAMES)):
                self.mutation_started = True  # Prior unbound mutation is uncertain.
            self.pristine()
            rows, actual = [], []
        else:
            rows, actual = self.state(plan)
        present = census()
        if not present and plan is None:
            raise Refusal('container-absent-before-plan')
        capture_logs(present, execute, transaction=self)
        self.pinned()
        if len(rows) == 9:
            if present:
                raise Refusal('terminal-container-reappeared')
            return terminal_result('PASS_TERMINAL_REPLAY', plan)
        if not execute:
            return {'status': 'PASS_VALIDATE_ONLY', 'terminal': False, 'events': len(rows),
                    'container_present': present, 'publisher_contract': PUBLISHER_CONTRACT}
        if plan is None:
            plan = self.prepare()
        if not exists(self.fd, JOURNAL.name):
            self.create(JOURNAL.name, b'')
        if present:
            # Require the same exited identity immediately before removal.
            protected_files()
            capture_logs(True, execute=True, transaction=self)
            if not census():
                raise Refusal('container-disappeared-before-rm')
            self.pinned()
            self.mutation_started = True
            removed = docker(['rm', '--', CONTAINER]).strip()
            if removed not in (CONTAINER.encode(), CONTAINER_NAME.encode()):
                raise Refusal('container-remove-response')
        if census():
            raise Refusal('container-still-present')
        self.pinned()
        for index, path in enumerate((ATTEMPT, SHARED)):
            protected_files()
            rows, actual = self.state(plan)
            if len(rows) >= 4 * index + 4:
                continue
            if census():
                raise Refusal('container-reappeared')
            self.preserved()
            if len(rows) == 4 * index:
                self.append(plan, rows, 'before_exchange', index)
            rows, actual = self.state(plan)
            if actual[index] == 'before_exchange':
                read_at(self.parent_fd(path), path.name, RECORDS[path])
                self.sentinel(ARCHIVE_NAMES[index], plan['sentinels'][index])
                self.pinned()
                # Atomic exchange never vacates the active ownership pathname.
                # A foreign capture fails validation while its sentinel stays
                # active; neither object is deleted or speculatively rolled back.
                rename_exchange(self.parent_fd(path), path.name, ARCHIVE_NAMES[index], self.fd)
                os.fsync(self.parent_fd(path))
                os.fsync(self.fd)
            os.fsync(self.fd)
            rows, actual = self.state(plan)
            if len(rows) == 4 * index + 1:
                self.append(plan, rows, 'after_exchange', index)
            if len(rows) == 4 * index + 2:
                self.append(plan, rows, 'release', index)
            rows, actual = self.state(plan)
            if actual[index] == 'after_exchange':
                if census():
                    raise Refusal('container-reappeared-before-release')
                protected_files()
                self.sentinel(path.name, plan['sentinels'][index], self.parent_fd(path))
                self.pinned()
                # This is the intended release point. A raced-in regular file
                # causes ENOTDIR and remains intact; replay preserves that owner.
                os.rmdir(path.name, dir_fd=self.parent_fd(path))
                os.fsync(self.parent_fd(path))
            os.fsync(self.fd)
            rows, actual = self.state(plan)
            self.append(plan, rows, 'after_release', index)
        rows, actual = self.state(plan)
        protected_files()
        if census():
            raise Refusal('container-reappeared')
        self.preserved()
        self.append(plan, rows, 'complete', 2)
        self.state(plan)
        return terminal_result('PASS_EXECUTED', plan)

def recover(execute=False):
    # Defer ordinary termination before acquiring any cleanup lock or mutating.
    # Successful/preflight paths restore delivery only after all held locks close.
    # Uncertain mutation never reaches restoration: quarantine holds indefinitely.
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS) if execute else None
    tx = None
    try:
        tx = Transaction()
        return tx.run(execute)
    except BaseException as error:
        # The preserved root lock remains held while durable quarantine is written.
        # No ownership name is ever unlinked or restored speculatively.
        if execute and tx is not None and tx.fd is not None and tx.root_locked and tx.mutation_started:
            try:
                tx.create(QUARANTINE.name, canonical({
                    'schema': 'fp-save-image.cleanup-quarantine.v1',
                    'release_sha256': digest(canonical(RELEASE)),
                    'error_type': type(error).__name__,
                    'requires': 'independent-exact-state-reconciliation'}) + b'\n')
            except BaseException:
                pass
            try:
                print(json.dumps({'status': 'QUARANTINED_ROOT_LOCK_HELD',
                                  'error_type': type(error).__name__,
                                  'requires': 'independent-exact-state-reconciliation'}), flush=True)
            except BaseException:
                pass
            quarantine_wait()
        raise
    finally:
        if tx is not None:
            tx.close()
        if previous_mask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', type=Path)
    parser.add_argument('--release-sha256')
    parser.add_argument('--prepare-observation', type=Path)
    parser.add_argument('--observation-sha256')
    parser.add_argument('--git-commit')
    parser.add_argument('--git-tree')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.prepare_observation:
            if args.execute or args.release or not args.git_commit or not args.git_tree:
                raise Refusal('prepare-arguments')
            raw = read_bounded(args.prepare_observation)
            if digest(raw) != args.observation_sha256:
                raise Refusal('observation-file-digest')
            print(json.dumps(prepare_release(parse(raw), args.git_commit, args.git_tree), sort_keys=True))
            return 0
        if not args.release or not args.release_sha256:
            raise Refusal('exact-release-required')
        raw = read_bounded(args.release)
        if digest(raw) != args.release_sha256:
            raise Refusal('release-file-digest')
        configure(parse(raw), execute=args.execute)
        if os.geteuid() != 0:
            raise Refusal('root-execution-required-use-sudo-A')
        result = recover(args.execute)
    except (Refusal, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())





