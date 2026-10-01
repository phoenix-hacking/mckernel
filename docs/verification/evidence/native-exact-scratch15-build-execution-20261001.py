#!/usr/bin/env python3
"""Fail-closed admission for one prepared scratch15 host build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

REPO = Path('/home/holden/mckernel')
ORIGINAL = Path('/home/holden/mckernel-work/scratch/native-exact-build-request-1e95abdc-scratch-15.json')
ORIGINAL_SHA256 = '1c18211bde1005ee0dab8b7251df2854b005cb8768347ff5063878621c7cd8d8'
MANIFEST_SHA256 = 'b1f827a82b9f7cc06164a716e341d62f2d78f187ece452bf1a7f985cd94a6749'
WRAPPER = REPO / 'scripts/native_rust_exact_disk_build_wrapper.py'
WRAPPER_SHA256 = '94a2abea359725515dae16d21f081f6bb1a1482cfae8055b1b08f22fc396ff0d'
RELEASE_PATH = 'scripts/native_rust_exact_disk_build_wrapper.py'
RELEASE_REF = 'refs/remotes/origin/codex/local-native-staging-repair'
PACKET_PATH = 'docs/verification/evidence/native-exact-scratch15-build-execution-20261001.py'
TEST_PATH = 'scripts/tests/test_native_exact_scratch15_build_execution_20261001.py'
EXPORTSET = '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch15-exportset-27.json'
DERIVED = Path('/home/holden/mckernel-work/scratch/native-exact-build-request-1e95abdc-scratch-15-execution.json')
LOG = Path('/home/holden/mckernel-work/scratch/native-exact-candidate-preparation-1e95abdc-scratch-15.log')
TERMINAL = Path('/home/holden/mckernel-work/scratch/native-exact-candidate-preparation-1e95abdc-scratch-15-terminal.json')
LEASE = Path('/home/holden/mckernel-work/scratch/native-exact-build-lease-1e95abdc-scratch-15.json')
CANDIDATE = Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-1e95abdc-scratch-15')
IHK = CANDIDATE / 'ihk'
OVERLAY = CANDIDATE / 'host-kernel/exact-build/ihk-clear-host-pte-overlay.patch'
OUTPUT = Path('/home/holden/mckernel-work/scratch/native-exact-build-output-1e95abdc-scratch-15')
EVIDENCE = Path('/home/holden/mckernel-work/scratch/native-exact-build-evidence-1e95abdc-scratch-15')
LOG_SHA256 = '7d8d91bff694371f07a6ad8bb4c9cc3ad63c2b63f339db1f2f608c04a25f6a31'
TERMINAL_SHA256 = 'fd564ce351116abe7d94e85505ff058a23f30682499d02d65e91e874e3b6f004'
IHK_HEAD = '3114d9e7101ad52030eb3effa849a5c108972a1f'
OVERLAY_SHA256 = 'cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7'
OVERLAY_RESULT_SHA256 = '7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77'
CANDIDATE_SHA = '1e95abdc2b124c19f16b88cdb21600c768a10c2d'
OWNER_SHA256 = 'a8c4c9fc61fab312e3a6e48e93b417453ec12e6543d6adbb7038933f92e79155'
DRIVER_SHA256 = 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a'

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
    if git_run(['--git-dir', str(REPO / '.git'), 'merge-base', '--is-ancestor', CANDIDATE_SHA, commit], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        raise Refusal('release-ancestry')

def validate_inputs(release_commit):
    data = Path(ORIGINAL).read_bytes()
    if sha(data) != ORIGINAL_SHA256: raise Refusal('original-request-hash')
    request = json_bytes(data)
    if request.get('input_manifest_sha256') != MANIFEST_SHA256 or request.get('release_required') is not True:
        raise Refusal('manifest-or-release-binding')
    if request.get('operational_exclusion_path') != '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-exportset-16.json':
        raise Refusal('original-exclusion')
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
    changes = {'operational_exclusion_path': EXPORTSET, 'operational_exclusion_consumed': False,
               'preparation_only': False, 'execution_released': True, 'executable': True}
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

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--release-commit', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    derived = derive(validate_inputs(args.release_commit))
    if not args.execute:
        print(json.dumps({'status': 'PASS_VALIDATE_ONLY', 'byte_sha256': sha(payload(derived)), 'canonical_sha256': sha(canonical(derived)), 'release_commit': args.release_commit}, sort_keys=True))
        return 0
    publish(derived)
    os.execv(wrapper_argv()[0], wrapper_argv())
    return 127

if __name__ == '__main__': raise SystemExit(main())
