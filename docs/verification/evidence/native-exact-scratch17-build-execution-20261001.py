#!/usr/bin/env python3
"""Fail-closed admission for one prepared scratch17 host build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import importlib.util

REPO = Path('/home/holden/mckernel')
ORIGINAL = Path('/home/holden/mckernel-work/scratch/native-exact-delta-request-50b08432-scratch-17.json')
ORIGINAL_SHA256 = '852f7d8f652079828cd30377de30d7d810e7747e8e0703a1efb65ae09cedb852'
MANIFEST_SHA256 = 'cbdfac7bc5b9e3c03e112335d12eeca3420835f630c134c269fbf7ca7f0a92bc'
WRAPPER = REPO / 'scripts/native_rust_exact_disk_build_wrapper.py'
WRAPPER_SHA256 = '578d34e8fa96a08a0729edb9ff58ffa9d66837bbf30eed8cb75fa9da9f7f26b1'
RELEASE_PATH = 'scripts/native_rust_exact_disk_build_wrapper.py'
RELEASE_REF = 'refs/remotes/origin/codex/local-native-staging-repair'
SOURCE_CHECKPOINT = '844dd6aa652fe285897749060069fffd34c28344'
RECEIPT_SHA256 = '18225919a44e2c07e87a66711c8d1c9483d10e15da91fa5d7fcb7339ff888172'
EXPECTED_LIMITS = {'NanoCpus': 4000000000, 'CpusetCpus': '2-5',
                   'Memory': 12 * 2 ** 30, 'MemorySwap': 12 * 2 ** 30,
                   'PidsLimit': 512, 'NetworkMode': 'none'}
PACKET_PATH = 'docs/verification/evidence/native-exact-scratch17-build-execution-20261001.py'
TEST_PATH = 'scripts/tests/test_native_exact_scratch17_build_execution_20261001.py'
EXPORTSET = '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch17.json'
DERIVED = Path('/home/holden/mckernel-work/scratch/native-exact-build-request-50b08432-scratch-17-execution.json')
LOG = Path('/home/holden/mckernel-work/scratch/native-exact-candidate-delta-preparation-50b08432-scratch-17.log')
TERMINAL = Path('/home/holden/mckernel-work/scratch/native-exact-candidate-delta-preparation-50b08432-scratch-17-terminal.json')
LEASE = Path('/home/holden/mckernel-work/scratch/native-exact-build-lease-50b08432-scratch-17.json')
CANDIDATE = Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-50b08432-scratch-17')
IHK = CANDIDATE / 'ihk'
OVERLAY = CANDIDATE / 'host-kernel/exact-build/ihk-clear-host-pte-overlay.patch'
OUTPUT = Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-50b08432-scratch-17-output')
EVIDENCE = Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-50b08432-scratch-17-evidence')
LOG_SHA256 = '0f02a34a77d132b425a6e3f58eaa9a90b177b6599e37359d05ce97c30adcb1a8'
TERMINAL_SHA256 = 'e5d7b5bc58b2584d811978a68f885ca6db6bd312935d7607096d1c0dc2080bee'
IHK_HEAD = '3114d9e7101ad52030eb3effa849a5c108972a1f'
OVERLAY_SHA256 = 'cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7'
OVERLAY_RESULT_SHA256 = '7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77'
CANDIDATE_SHA = '50b084322610a9326b1b7b528edd4cd73b635632'
OWNER_SHA256 = '57a5af06e6339030dad727fef655d4bd3550f65c9e60553090511f42426f077a'
DRIVER_SHA256 = 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a'
TERMINAL_NON_RELEASABLE = True
SUCCESSOR_REQUIREMENTS = (
    'fresh commit-derived candidate/request/manifest with exact owner and provenance bindings',
    'source-reviewed shared build/image/guest entry lock integration and execution release',
    'authenticated read-only historical lease observer execution review',
    'actual downstream validation before derived-request publication',
)

class Refusal(ValueError):
    pass

def git_env():
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C', 'LC_ALL': 'C', 'TZ': 'UTC'}
    env.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'})
    return env

def git_run(args, **kwargs):
    kwargs['env'] = git_env()
    return subprocess.run(['/usr/bin/git', *args], **kwargs)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def regular(path, expected):
    st = os.lstat(path)
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or sha(Path(path).read_bytes()) != expected:
        raise Refusal('artifact-binding')

def lexists(path):
    return os.path.lexists(str(path))

def directory(path):
    st = os.lstat(path)
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
        raise Refusal('directory-binding')

def json_bytes(data):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise Refusal('duplicate-json-key')
            out[key] = value
        return out
    try: return json.loads(data.decode(), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc: raise Refusal('invalid-json') from exc

def git_blob(commit):
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise Refusal('release-commit')
    resolved = git_run(['--git-dir', str(REPO / '.git'), 'rev-parse', '--verify', RELEASE_REF + '^{commit}'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if resolved.returncode or resolved.stdout.decode().strip() != commit: raise Refusal('release-ref-mismatch')
    if git_run(['--git-dir', str(REPO / '.git'), 'cat-file', 'commit', commit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        raise Refusal('release-commit-not-fetched')
    for path, expected in ((RELEASE_PATH, WRAPPER_SHA256),):
        p = git_run(['--git-dir', str(REPO / '.git'), 'show', f'{commit}:{path}'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if p.returncode or sha(p.stdout) != expected: raise Refusal('release-wrapper-hash')
    for path, current in ((PACKET_PATH, Path(__file__).read_bytes()), (TEST_PATH, (REPO / TEST_PATH).read_bytes())):
        p = git_run(['--git-dir', str(REPO / '.git'), 'show', f'{commit}:{path}'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if p.returncode or p.stdout != current: raise Refusal('release-source-blob')
    for ancestor in (SOURCE_CHECKPOINT, CANDIDATE_SHA):
        if git_run(['--git-dir', str(REPO / '.git'), 'merge-base', '--is-ancestor', ancestor, commit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            raise Refusal('release-ancestry')

def validate_inputs(release_commit):
    data = Path(ORIGINAL).read_bytes()
    if sha(data) != ORIGINAL_SHA256: raise Refusal('original-request-hash')
    request = json_bytes(data)
    if request.get('input_manifest_sha256') != MANIFEST_SHA256 or request.get('release_required') is not True:
        raise Refusal('manifest-or-release-binding')
    if request.get('operational_exclusion_path') != EXPORTSET:
        raise Refusal('original-exclusion')
    preparation = {'preparation_only': True, 'execution_released': False,
                   'executable': False, 'operational_exclusion_consumed': False}
    if any(request.get(key) is not value for key, value in preparation.items()):
        raise Refusal('original-preparation-state')
    bound_paths = {'source_root': CANDIDATE, 'ihk_overlay_path': OVERLAY,
                   'output_root': OUTPUT, 'evidence_root': EVIDENCE,
                   'lease_path': LEASE}
    for key, expected in bound_paths.items():
        if request.get(key) != str(expected): raise Refusal('source-artifact-binding')
    expected_fields = {'candidate_sha': CANDIDATE_SHA, 'ihk_overlay_base_sha': IHK_HEAD,
                       'ihk_overlay_sha256': OVERLAY_SHA256,
                       'ihk_overlay_result_blob_sha256': OVERLAY_RESULT_SHA256,
                       'owner_path': str(CANDIDATE / 'scripts/native_rust_exact_build_container_owner.py'),
                       'owner_path_sha256': OWNER_SHA256,
                       'provenance_path': str(CANDIDATE / 'scripts/native_rust_exact_build_offline.py'),
                       'provenance_path_sha256': DRIVER_SHA256,
                       'driver_path': str(CANDIDATE / 'scripts/native_rust_exact_build_offline.py'),
                       'driver_path_sha256': DRIVER_SHA256}
    for key, expected in expected_fields.items():
        if request.get(key) != expected: raise Refusal('request-hash-binding')
    regular(Path(request['owner_path']), request['owner_path_sha256'])
    regular(Path(request['provenance_path']), request['provenance_path_sha256'])
    regular(Path(request['driver_path']), request['driver_path_sha256'])
    if request.get('image_receipt_sha256') != RECEIPT_SHA256:
        raise Refusal('image-receipt-binding')
    regular(Path(request['image_receipt']), RECEIPT_SHA256)
    if request.get('limits') != EXPECTED_LIMITS:
        raise Refusal('resource-limits-binding')
    expected_resources = {
        'launcher_aggregate_memory_gib': '16.2158', 'timeout': 19800,
        'host_floor': 16 * 2 ** 30, 'scratch_floor': 12 * 2 ** 30,
        'host_measure_root': '/', 'scratch_measure_root': '/home/holden/mckernel-work/scratch',
        'memory_allocation_roots': [str(CANDIDATE), str(CANDIDATE.parent / (CANDIDATE.name + '-metadata-backup'))],
    }
    for key, expected in expected_resources.items():
        if request.get(key) != expected: raise Refusal('resource-reconciliation-binding')
    regular(LOG, LOG_SHA256); regular(TERMINAL, TERMINAL_SHA256); regular(WRAPPER, WRAPPER_SHA256)
    terminal = json_bytes(Path(TERMINAL).read_bytes())
    if terminal.get('returncode') != 0 or terminal.get('log') != str(LOG) or terminal.get('log_sha256') != LOG_SHA256:
        raise Refusal('terminal-binding')
    manifest = Path(request['input_manifest'])
    regular(manifest, MANIFEST_SHA256)
    for path in (CANDIDATE, IHK, OVERLAY):
        if lexists(path) and Path(path).is_symlink(): raise Refusal('source-symlink')
    if git_run(['--git-dir', str(CANDIDATE / '.git'), '--work-tree', str(CANDIDATE), 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode().strip() != CANDIDATE_SHA:
        raise Refusal('candidate-head')
    if git_run(['--git-dir', str(IHK / '.git'), '--work-tree', str(IHK), 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.decode().strip() != IHK_HEAD:
        raise Refusal('ihk-head')
    regular(OVERLAY, OVERLAY_SHA256)
    result_file = IHK / 'test/ihklib/whitebox/src/driver/mckernel/syscall.c'
    regular(result_file, OVERLAY_RESULT_SHA256)
    directory(OUTPUT); directory(EVIDENCE)
    if any(OUTPUT.iterdir()) or any(EVIDENCE.iterdir()): raise Refusal('output-not-empty')
    if lexists(LEASE) or lexists(EXPORTSET) or lexists(DERIVED): raise Refusal('destination-present')
    git_blob(release_commit)
    return request

def derive(request):
    result = dict(request)
    changes = {'preparation_only': False, 'execution_released': True, 'executable': True}
    result.update(changes)
    if result.get('release_required') is not True or set(result) != set(request): raise Refusal('request-shape')
    for key in request:
        if key not in changes and result[key] != request[key]: raise Refusal('unexpected-value-change')
    return result

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def payload(data):
    return canonical(data) + b'\n'

def publish(data):
    content = payload(data)
    fd = os.open(DERIVED, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        offset = 0
        while offset < len(content):
            written = os.write(fd, content[offset:])
            if written <= 0: raise Refusal('short-publish')
            offset += written
        os.fsync(fd)
    finally: os.close(fd)
    dfd = os.open(DERIVED.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(dfd)
    finally: os.close(dfd)
    return sha(content), sha(canonical(data)), len(content)

def wrapper_argv():
    return [sys.executable, '-E', '-s', '-B', str(WRAPPER), str(DERIVED), '--launcher-aggregate-gib', '16.2158']

def validate_downstream(request):
    regular(WRAPPER, WRAPPER_SHA256)
    spec = importlib.util.spec_from_file_location('_scratch17_admission', WRAPPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_request(request)

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--release-commit', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if TERMINAL_NON_RELEASABLE:
        print(json.dumps({'status': 'TERMINAL_NON_RELEASABLE',
                          'reason': 'immutable prepared candidate does not bind current owner contract',
                          'successor_requirements': SUCCESSOR_REQUIREMENTS}, sort_keys=True))
        return 2
    derived = derive(validate_inputs(args.release_commit))
    validate_downstream(derived)
    if not args.execute:
        print(json.dumps({'status': 'PASS_VALIDATE_ONLY', 'byte_sha256': sha(payload(derived)), 'canonical_sha256': sha(canonical(derived)), 'release_commit': args.release_commit}, sort_keys=True))
        return 0
    publish(derived)
    os.execv(wrapper_argv()[0], wrapper_argv())
    return 127

if __name__ == '__main__': raise SystemExit(main())
