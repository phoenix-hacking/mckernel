#!/usr/bin/env python3
"""SOURCE_PENDING_REVIEW: resume the retained scratch18 request unchanged.

Recovery postflight and independent execution review remain external gates.
Validation performs the real recovery census but no recovery mutation. This
packet never publishes a request and never invokes the consumed build packet.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import types

REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
REVIEW_STATE = 'SOURCE_PENDING_REVIEW'
RELEASE_REF = 'refs/remotes/origin/codex/local-native-staging-repair'
ANCESTORS = ('89ab5c555aac9177a789efc67ddc775dacb25d6d',
             '215d338c06cc70ca6bad471eb2d035fb5650246f',
             '126a70890b258d7f21e08bfd5c77fe51c3c77e65',
             'd224cb46c2c52609f01e3b0601493e9443e2d365')
PREFIX = 'docs/verification/evidence/'
PACKET = PREFIX + 'native-exact-scratch18-build-resume-execution-20261001.py'
TEST = 'scripts/tests/test_native_exact_scratch18_build_resume_execution_20261001.py'
WRAPPER = 'scripts/native_rust_exact_disk_build_wrapper.py'
HELPER = PREFIX + 'native-exact-scratch18-preowner-recovery-20261001.py'
FAILURE = PREFIX + 'native-exact-scratch18-build-admission-failure-20261001-1.json'
DEPENDENCIES = {
    WRAPPER: 'ccfbd404ff2428c4eb8841948b761118a42bd25ed8875c583755e6a97d8f0393',
    'scripts/tests/test_native_rust_exact_disk_build_wrapper.py': '1f7c573fd03e27e6a61e5d9ad19718f9eb8409e6749654c313625d66a7c9bdc3',
    HELPER: 'e02aa523c2280c39c66b1638ce86523f87703b45154517d98531305e6c48c33c',
    'scripts/tests/test_native_exact_scratch18_preowner_recovery_20261001.py': 'c759517ef912fc2a31a97787cd35849858c2defe3a283061da582b2d22aceee0',
    PREFIX + 'native-exact-scratch18-preowner-recovery-execution-20261001.py': '1d11aa9aeeba932a33f1f455513d5d2c337d0d8134e696b2dadffa0dc051df40',
    'scripts/tests/test_native_exact_scratch18_preowner_recovery_execution_20261001.py': '2a3d8d15826398b228485942b08c163e67cde23ebcdd595b04229f0d02dd5e87',
    FAILURE: '40497b42fd0906cfe45af35ee07a9be736948db8cda84d036216e9670663aec7',
    PREFIX + 'native-exact-scratch18-build-execution-20261001.py': '072de9ddb8a9911a1183bdd086bdafdd50fbd2680065d17a66b64663adc8c185',
}
REQUEST = ROOT / 'native-exact-build-request-scratch-18-execution.json'
REQUEST_SHA256 = '80de5f1c02867bcbee69752e186f7fc11d201c2df3c78887ea08aa85f92e2bd7'
CANONICAL_SHA256 = '3312fb6e6297ec1abae6836720c6bb1c6c49d958a48acf665d9cc4070b547c06'
ARCHIVE = ROOT / 'native-exact-scratch18-preowner-archives'
MUTEX = ROOT / 'native-exact-scratch18-preowner-recovery.mutex'
ATTEMPT = ROOT / 'native-exact-candidate-operational-exclusion-scratch18.json'
SHARED = ROOT / 'mckernel-heavy-operation.lock'
LEASE = ROOT / 'native-exact-build-lease-scratch-18.json'
OUTPUT = ROOT / 'mckernel-exact-candidate-scratch-18-output'
EVIDENCE = ROOT / 'mckernel-exact-candidate-scratch-18-evidence'
PLAN_SHA256 = '75a1c79f93068829ede93c7211b7143f470e3dd75eee3c62fb24b2a75560e07e'
# path, device, inode, nlink, mode, uid, gid, size, exact byte hash.
RECORDS = (
    (REQUEST, 1831, 90729, 1, 0o600, 1000, 1000, 2973, REQUEST_SHA256),
    (ARCHIVE / 'attempt.archive', 1831, 90731, 1, 0o600, 1000, 1000, 269,
     'e39dc0fe3faf917a0aa8adb61e9aa64334bf5d107bd35fe4ad7d441a6beeca1e'),
    (ARCHIVE / 'shared.archive', 1831, 90730, 1, 0o600, 1000, 1000, 269,
     '3aa97b068d3e5246ff838417b32989b2760ca11680f8a65a978d949a9d85cdc5'),
    (ARCHIVE / 'plan.json', 1831, 3571965, 1, 0o600, 1000, 1000, 1109,
     '4d25263b8f3034d047411090949307348f51b9a54e766defe663b9cd814a990e'),
    (ARCHIVE / 'journal.jsonl', 1831, 3571966, 1, 0o600, 1000, 1000, 1493,
     '73b9102f8242f83f9a058955be3ed2415607ad72fa66018aa88c210623d13d7f'),
    (MUTEX, 1831, 90732, 1, 0o600, 1000, 1000, 0,
     'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
)

class Refusal(ValueError): pass

def sha(data): return hashlib.sha256(data).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()

def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise Refusal('duplicate-json-key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs)

def directory(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts: raise Refusal('noncanonical-path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nxt
        return fd
    except BaseException:
        os.close(fd); raise

def read_regular(path, record=None):
    path = Path(path); dfd = directory(path.parent); fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 16 << 20:
            raise Refusal('artifact-shape')
        data = bytearray()
        while len(data) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(data)))
            if not block: break
            data.extend(block)
        after = os.fstat(fd); entry = os.stat(path.name, dir_fd=dfd, follow_symlinks=False)
        fields = ('st_dev', 'st_ino', 'st_nlink', 'st_mode', 'st_uid', 'st_gid',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if (any(getattr(before, k) != getattr(after, k) for k in fields) or
            any(getattr(before, k) != getattr(entry, k) for k in fields) or len(data) != before.st_size):
            raise Refusal('artifact-raced')
        if record is not None:
            actual = (path, before.st_dev, before.st_ino, before.st_nlink,
                      stat.S_IMODE(before.st_mode), before.st_uid, before.st_gid, before.st_size, sha(data))
            if actual != record: raise Refusal('artifact-binding')
        return bytes(data)
    finally:
        if fd is not None: os.close(fd)
        os.close(dfd)

def check_directory(path, inode, names):
    fd = directory(path)
    try:
        st = os.fstat(fd)
        if (st.st_dev, st.st_ino, stat.S_IMODE(st.st_mode), st.st_uid, st.st_gid) != (1831, inode, 0o700, 1000, 1000):
            raise Refusal('directory-binding')
        if set(os.listdir(fd)) != set(names): raise Refusal('directory-contents')
    finally: os.close(fd)

def git(args):
    environment = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C', 'LC_ALL': 'C',
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_SYSTEM': '/dev/null',
                   'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_NO_REPLACE_OBJECTS': '1',
                   'GIT_TERMINAL_PROMPT': '0'}
    result = subprocess.run(['/usr/bin/git', '--no-replace-objects', '--git-dir', str(REPO / '.git'), *args],
                            env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if result.returncode: raise Refusal('git-check-failed:' + args[0])
    return result.stdout

def sources(commit):
    if not isinstance(commit, str) or re.fullmatch('[0-9a-f]{40}', commit) is None:
        raise Refusal('release-commit')
    if git(['rev-parse', '--verify', RELEASE_REF + '^{commit}']).decode().strip() != commit:
        raise Refusal('release-ref-mismatch')
    git(['cat-file', 'commit', commit])
    for ancestor in ANCESTORS: git(['merge-base', '--is-ancestor', ancestor, commit])
    result = {}
    for relative in (*DEPENDENCIES, PACKET, TEST):
        raw = read_regular(REPO / relative)
        if relative in DEPENDENCIES and sha(raw) != DEPENDENCIES[relative]:
            raise Refusal('dependency-hash:' + relative)
        if git(['show', commit + ':' + relative]) != raw: raise Refusal('release-blob:' + relative)
        result[relative] = raw
    return result

def retained():
    raw = {row[0]: read_regular(row[0], row) for row in RECORDS}
    request = strict_json(raw[REQUEST])
    if sha(canonical(request)) != CANONICAL_SHA256: raise Refusal('request-canonical-binding')
    if sha(canonical(strict_json(raw[ARCHIVE / 'plan.json']))) != PLAN_SHA256:
        raise Refusal('plan-canonical-binding')
    terminal = strict_json(raw[ARCHIVE / 'journal.jsonl'].splitlines()[-1])
    if (terminal.get('event') != 'complete' or type(terminal.get('state')) is not int or
        terminal['state'] != 2 or terminal.get('plan_sha256') != PLAN_SHA256):
        raise Refusal('recovery-terminal-binding')
    if any(os.path.lexists(path) for path in (ATTEMPT, SHARED, LEASE)):
        raise Refusal('live-ownership-path-present')
    if request.get('output_root') != str(OUTPUT) or request.get('evidence_root') != str(EVIDENCE) or request.get('lease_path') != str(LEASE):
        raise Refusal('prepared-request-paths')
    check_directory(ARCHIVE, 3571964, ('attempt.archive', 'shared.archive', 'plan.json', 'journal.jsonl'))
    check_directory(OUTPUT, 3571962, ())
    check_directory(EVIDENCE, 3571963, ())
    return request

def module(relative, data):
    loaded = types.ModuleType('_bound_scratch18_resume_dependency')
    loaded.__file__ = str(REPO / relative)
    exec(compile(data, loaded.__file__, 'exec'), loaded.__dict__)
    return loaded

def final_bindings(commit, bound, request):
    if sources(commit) != bound: raise Refusal('source-raced')
    if retained() != request: raise Refusal('request-raced')

def admit(commit):
    bound = sources(commit)
    request = retained()
    recovery = module(HELPER, bound[HELPER]).recover(False)
    if (not isinstance(recovery, dict) or set(recovery) != {'status', 'state', 'terminal'} or
        recovery['status'] != 'PASS_VALIDATE_ONLY' or type(recovery['state']) is not int or
        recovery['state'] != 2 or recovery['terminal'] is not True):
        raise Refusal('recovery-not-terminal')
    result = module(WRAPPER, bound[WRAPPER]).validate_request(request)
    if (not isinstance(result, dict) or set(result) != {'status', 'execution_released', 'request_sha256'} or
        result['status'] != 'PASS_COMPATIBILITY_ONLY' or result['execution_released'] is not False or
        result['request_sha256'] != CANONICAL_SHA256):
        raise Refusal('downstream-validation')
    final_bindings(commit, bound, request)
    return bound, request

def wrapper_argv():
    return ['/usr/bin/python3', '-E', '-s', '-B', str(REPO / WRAPPER), str(REQUEST),
            '--launcher-aggregate-gib', '16.2158']

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--release-commit', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        bound, request = admit(args.release_commit)
        if args.execute:
            final_bindings(args.release_commit, bound, request)
            command = wrapper_argv()
            # Exact script invocation is required by privileged caller
            # authentication; wrapper reacquires fresh shared/attempt locks.
            os.execv(command[0], command)
            raise Refusal('exec-returned')
        print(json.dumps({'status': 'PASS_VALIDATE_ONLY', 'execution_released': False,
                          'request_sha256': REQUEST_SHA256, 'release_commit': args.release_commit}, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc)}, sort_keys=True))
        return 1

if __name__ == '__main__': raise SystemExit(main())
