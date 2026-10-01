#!/usr/bin/env python3
"""Exact fetched-source admission for the one-shot scratch18 recovery.

This release writes no ownership records. The bound helper owns all recovery
mutation, serialization, crash reconciliation and replay refusal.
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
RELEASE_REF = 'refs/remotes/origin/codex/local-native-staging-repair'
ANCESTORS = ('215d338c06cc70ca6bad471eb2d035fb5650246f',
             '89ab5c555aac9177a789efc67ddc775dacb25d6d')
PREFIX = 'docs/verification/evidence/'
PACKET = PREFIX + 'native-exact-scratch18-preowner-recovery-execution-20261001.py'
TEST = 'scripts/tests/test_native_exact_scratch18_preowner_recovery_execution_20261001.py'
HELPER = PREFIX + 'native-exact-scratch18-preowner-recovery-20261001.py'
FAILURE = PREFIX + 'native-exact-scratch18-build-admission-failure-20261001-1.json'
DEPENDENCIES = {
    HELPER: 'e02aa523c2280c39c66b1638ce86523f87703b45154517d98531305e6c48c33c',
    'scripts/tests/test_native_exact_scratch18_preowner_recovery_20261001.py': 'c759517ef912fc2a31a97787cd35849858c2defe3a283061da582b2d22aceee0',
    'scripts/native_rust_exact_disk_build_wrapper.py': 'ccfbd404ff2428c4eb8841948b761118a42bd25ed8875c583755e6a97d8f0393',
    'scripts/tests/test_native_rust_exact_disk_build_wrapper.py': '1f7c573fd03e27e6a61e5d9ad19718f9eb8409e6749654c313625d66a7c9bdc3',
    FAILURE: '40497b42fd0906cfe45af35ee07a9be736948db8cda84d036216e9670663aec7',
    PREFIX + 'native-exact-scratch18-build-execution-20261001.py': '072de9ddb8a9911a1183bdd086bdafdd50fbd2680065d17a66b64663adc8c185',
}
REQUEST = {'path': str(ROOT / 'native-exact-build-request-scratch-18-execution.json'),
           'sha256': '80de5f1c02867bcbee69752e186f7fc11d201c2df3c78887ea08aa85f92e2bd7',
           'normalized_sha256': '3312fb6e6297ec1abae6836720c6bb1c6c49d958a48acf665d9cc4070b547c06',
           'device': 1831, 'inode': 90729, 'mode': '0600', 'uid': 1000, 'gid': 1000}
LOCKS = {
    'attempt': {'path': str(ROOT / 'native-exact-candidate-operational-exclusion-scratch18.json'),
                'sha256': 'e39dc0fe3faf917a0aa8adb61e9aa64334bf5d107bd35fe4ad7d441a6beeca1e',
                'device': 1831, 'inode': 90731, 'mode': '0600', 'uid': 1000, 'gid': 1000},
    'shared': {'path': str(ROOT / 'mckernel-heavy-operation.lock'),
               'sha256': '3aa97b068d3e5246ff838417b32989b2760ca11680f8a65a978d949a9d85cdc5',
               'device': 1831, 'inode': 90730, 'mode': '0600', 'uid': 1000, 'gid': 1000},
}


class Refusal(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refusal('duplicate-json-key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs)


def read_regular(path, record=None):
    """No-follow walk; bind opened bytes and final directory entry identity."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('artifact-path')
    dfd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    fd = None
    try:
        for part in path.parts[1:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=dfd)
            os.close(dfd)
            dfd = nxt
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 16 << 20:
            raise Refusal('artifact-shape')
        data = bytearray()
        while len(data) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = os.fstat(fd)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        entry = os.stat(path.name, dir_fd=dfd, follow_symlinks=False)
        if (any(getattr(before, k) != getattr(after, k) for k in fields) or
                (entry.st_dev, entry.st_ino) != (before.st_dev, before.st_ino) or len(data) != before.st_size):
            raise Refusal('artifact-raced')
        if record is not None:
            actual = {'sha256': sha(data), 'device': before.st_dev, 'inode': before.st_ino,
                      'mode': '%04o' % stat.S_IMODE(before.st_mode), 'uid': before.st_uid, 'gid': before.st_gid}
            if any(record[key] != value for key, value in actual.items()):
                raise Refusal('artifact-binding')
        return bytes(data)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(dfd)


def git(args):
    env = {'PATH': '/usr/bin:/bin', 'HOME': '/nonexistent', 'LANG': 'C', 'LC_ALL': 'C',
           'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
           'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0'}
    result = subprocess.run(['/usr/bin/git', '--git-dir', str(REPO / '.git'), *args],
                            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if result.returncode:
        raise Refusal('git-check-failed:' + args[0])
    return result.stdout


def sources(commit):
    if not isinstance(commit, str) or re.fullmatch('[0-9a-f]{40}', commit) is None:
        raise Refusal('release-commit')
    if git(['rev-parse', '--verify', RELEASE_REF + '^{commit}']).decode().strip() != commit:
        raise Refusal('release-ref-mismatch')
    git(['cat-file', 'commit', commit])
    for ancestor in ANCESTORS:
        git(['merge-base', '--is-ancestor', ancestor, commit])
    bound = {}
    for path in (*DEPENDENCIES, PACKET, TEST):
        data = read_regular(REPO / path)
        if path in DEPENDENCIES and sha(data) != DEPENDENCIES[path]:
            raise Refusal('dependency-hash:' + path)
        if git(['show', commit + ':' + path]) != data:
            raise Refusal('release-blob:' + path)
        bound[path] = data
    return bound


def retained(bound):
    failure = strict_json(bound[FAILURE])
    if dict(failure['request'], device=1831) != REQUEST:
        raise Refusal('failure-request-binding')
    if {key: dict(value, device=1831) for key, value in failure['retained_locks'].items()} != LOCKS:
        raise Refusal('failure-lock-binding')
    raw = read_regular(REQUEST['path'], REQUEST)
    if sha(canonical(strict_json(raw))) != REQUEST['normalized_sha256']:
        raise Refusal('request-canonical-binding')
    for record in LOCKS.values():
        read_regular(record['path'], record)


def admit(commit):
    bound = sources(commit)
    retained(bound)
    module = types.ModuleType('_exact_scratch18_recovery')
    module.__file__ = str(REPO / HELPER)
    exec(compile(bound[HELPER], module.__file__, 'exec'), module.__dict__)
    # Real production observers are mandatory; there is no CLI observation input.
    result = module.recover(False)
    if (not isinstance(result, dict) or set(result) != {'status', 'state', 'terminal'} or
            result['status'] != 'PASS_VALIDATE_ONLY' or type(result['state']) is not int or
            result['state'] != 0 or result['terminal'] is not False):
        raise Refusal('recovery-state')
    # Repeat exact source/ref and inode checks after the potentially long census.
    if sources(commit) != bound:
        raise Refusal('source-raced')
    retained(bound)
    return module, result


def execution_result(result):
    archive = ROOT / 'native-exact-scratch18-preowner-archives'
    if (not isinstance(result, dict) or
            set(result) != {'status', 'plan_sha256', 'journal', 'archives'} or
            result['status'] != 'PASS' or not isinstance(result['plan_sha256'], str) or
            re.fullmatch('[0-9a-f]{64}', result['plan_sha256']) is None or
            result['journal'] != str(archive / 'journal.jsonl') or
            result['archives'] != [str(archive / 'attempt.archive'), str(archive / 'shared.archive')]):
        raise Refusal('recovery-execution-result')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--release-commit', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        module, result = admit(args.release_commit)
        if args.execute:
            # Execute the already authenticated, compiled bytes. Reopening the
            # pathname here would introduce a source replacement race.
            result = execution_result(module.recover(True))
        print(json.dumps(dict(result, release_commit=args.release_commit), sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc)}, sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
