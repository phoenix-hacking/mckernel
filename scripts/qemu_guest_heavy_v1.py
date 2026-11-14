#!/usr/bin/env python3
"""Reviewed guest source contract. No CLI operation grants an execution release.

The request must be an exact fetched Git blob; its source commit binds this
helper, the shell and the common lock provider. A caller-supplied hash alone is
not release authority. The two source switches enable the common contract;
each guest still needs separate execution review and a fetched request.
Failed admission/retirement leaves claims intact.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import stat
import subprocess
import sys
import tarfile
import time
import types

HEAVY_ENTRY_CONTRACT_RELEASED = True
ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / 'scripts/native_rust_exact_disk_build_wrapper.py'
SOURCES = ('scripts/qemu_guest_heavy_v1.py', 'scripts/qemu-mckernel-guest.sh',
           'scripts/native_rust_exact_disk_build_wrapper.py')
REQUIRED_LOGS = ('serial.log', 'debugcon.log', 'qemu-startup.log',
                 'qmp-status.jsonl', 'guest-command.log', 'guest-cleanup.log',
                 'guest-evidence.tar', 'guest-evidence.tar.sha256',
                 'guest-evidence/SHA256SUMS', 'run-status.json',
                 'heavy-operation-acquire.json', 'qemu-started.json')

# Only the isolated inline bootstrap supplies these before executing this exact
# source snapshot. A normal file import is useful for unit tests, not admission.
_AUTHENTICATED_SOURCES = globals().get('_AUTHENTICATED_SOURCES')
_AUTHENTICATED_IDENTITIES = globals().get('_AUTHENTICATED_IDENTITIES')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_file(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), 'not a regular file')
        require(before.st_size <= 64 * 1024**2, 'metadata/evidence file exceeds bounded read')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            data = stream.read()
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                 before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size,
                 after.st_mtime_ns, after.st_ctime_ns), 'file changed while reading')
        return data
    finally:
        os.close(fd)


def file_sha(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode), 'not a regular input')
        sha = hashlib.sha256()
        while True:
            data = os.read(fd, 1024 * 1024)
            if not data:
                break
            sha.update(data)
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns),
                'input changed while hashing')
        return sha.hexdigest()
    finally:
        os.close(fd)


def fsync_dir(path):
    fd = os.open(str(path), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exclusive_write(path, data):
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        if callable(data):
            data = data(os.fstat(fd))
        position = 0
        while position < len(data):
            count = os.write(fd, data[position:])
            require(isinstance(count, int) and count > 0, 'write made no progress')
            position += count
        os.fsync(fd)
    finally:
        os.close(fd)
    fsync_dir(Path(path).parent)


def write_claim(path, record):
    def content(info):
        record['device'] = info.st_dev
        record['inode'] = info.st_ino
        return encode(record)
    exclusive_write(path, content)


def canonical(path):
    candidate = Path(path)
    require(candidate.is_absolute() and str(candidate.resolve()) == str(candidate),
            'path must be absolute and fully resolved')
    return candidate


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def identity(pid):
    require(type(pid) is int and pid > 1, 'invalid PID')
    raw = Path('/proc', str(pid), 'stat').read_text()
    return {'pid': pid, 'starttime': raw.rsplit(')', 1)[1].split()[19],
            'boot_id': boot_id()}


def process_state(expected):
    require(expected['boot_id'] == boot_id(), 'boot identity changed')
    try:
        actual = identity(expected['pid'])
    except FileNotFoundError:
        return 'absent'
    require(actual == expected, 'PID incarnation changed; reconciliation required')
    return 'same'


def signal_exact(expected, sig):
    if process_state(expected) == 'absent':
        return
    # A pidfd closes the stat-to-kill reuse race. Do not fall back to kill(pid).
    fd = pidfd_open(expected['pid'])
    try:
        require(process_state(expected) == 'same', 'process changed before signal')
        pidfd_signal(fd, sig)
    finally:
        os.close(fd)


def pidfd_syscall(number, *args):
    # Python 3.8 and the retained Conda 3.9 lack the stdlib wrappers. These are
    # the x86_64 Linux pidfd syscalls, with no PID-based signal fallback.
    require(platform.system() == 'Linux' and platform.machine() == 'x86_64', 'unsupported pidfd platform')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    result = libc.syscall(ctypes.c_long(number), *[ctypes.c_long(arg) for arg in args])
    if result < 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code))
    return result


def pidfd_open(pid):
    return pidfd_syscall(434, pid, 0)


def pidfd_signal(fd, sig):
    return pidfd_syscall(424, fd, sig, 0, 0)


def retire_process(expected, seconds=4):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if process_state(expected) == 'absent':
            return
        signal_exact(expected, sig)
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if process_state(expected) == 'absent':
                return
            time.sleep(0.1)
    require(process_state(expected) == 'absent', 'process survives bounded TERM/KILL')


def git(*args):
    # Authority comes from this repository's fetched object database, never
    # from the launcher's PATH, GIT_DIR, config injection, alternates or replace
    # environment. No inherited environment is passed to the verifier process.
    environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C',
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_SYSTEM': '/dev/null',
                   'GIT_CONFIG_GLOBAL': '/dev/null'}
    return subprocess.check_output(
        ['/usr/bin/git', '--no-pager', '--no-replace-objects',
         '--git-dir=' + str(ROOT / '.git'), '--work-tree=' + str(ROOT), *args],
        env=environment, cwd=str(ROOT), stderr=subprocess.PIPE)


def fetched(commit):
    require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'bad commit')
    refs = git('for-each-ref', '--format=%(refname)', '--contains', commit,
               'refs/remotes/origin/').splitlines()
    require(bool(refs), 'commit is not in fetched origin history')


def file_binding(path):
    path = canonical(path)
    if path.is_dir():
        rows = []
        for child in sorted(path.rglob('*')):
            require(not child.is_symlink(), 'symlink in input tree')
            if child.is_file():
                rows.append([str(child.relative_to(path)), file_sha(child)])
            else:
                require(child.is_dir(), 'special input tree member')
        return {'path': str(path), 'sha256': digest(encode(rows)), 'kind': 'tree'}
    return {'path': str(path), 'sha256': file_sha(path), 'kind': 'file'}


def observed_limits():
    entries = Path('/proc/self/cgroup').read_text().splitlines()
    unified = [line[3:] for line in entries if line.startswith('0::')]
    require(len(unified) == 1 and '..' not in Path(unified[0]).parts, 'unified cgroup required')
    group = Path('/sys/fs/cgroup') / unified[0].lstrip('/')
    result = {'affinity': sorted(os.sched_getaffinity(0)), 'network': 'restricted-user-ssh'}
    for key, filename in (('memory_bytes', 'memory.max'), ('swap_bytes', 'memory.swap.max'),
                          ('pids', 'pids.max')):
        result[key] = int((group / filename).read_text().strip())
    require(set(result['affinity']) <= {2, 3, 4, 5} and result['affinity'], 'CPU profile expanded')
    require(0 < result['memory_bytes'] <= 12 * 1024**3 and result['swap_bytes'] == 0 and
            0 < result['pids'] <= 512, 'cgroup profile expanded')
    return result


def authenticate(request_path, expected_hash, fetched_commit, actual):
    fetched(fetched_commit)
    request_path = canonical(request_path)
    relative = str(request_path.relative_to(ROOT))
    raw = read_file(request_path)
    require(digest(raw) == expected_hash and git('show', fetched_commit + ':' + relative) == raw,
            'request is not the exact hash-bound fetched blob')
    request = strict_json(raw)
    require(set(request) == {'schema', 'release', 'source_commit', 'sources', 'config',
                             'controller', 'inputs', 'limits'}, 'unknown or missing request fields')
    require(request['schema'] == 'mckernel.guest-heavy.v1' and
            request['release'] == 'REVIEWED_EXECUTION', 'request not released')
    fetched(request['source_commit'])
    require(set(request['sources']) == set(SOURCES), 'source binding set mismatch')
    require(isinstance(_AUTHENTICATED_SOURCES, dict) and set(_AUTHENTICATED_SOURCES) == set(SOURCES),
            'helper was not executed from authenticated bootstrap snapshot')
    snapshots = {}
    for relative in SOURCES:
        source = _AUTHENTICATED_SOURCES[relative]
        require(type(source) is bytes and digest(source) == request['sources'][relative] and
                git('show', request['source_commit'] + ':' + relative) == source,
                'helper/runner/provider source mismatch')
        snapshots[relative] = source
    verify_source_identities()
    require(request['controller'] == identity(actual['controller_pid']), 'controller binding mismatch')
    require(actual['controller_pid'] == os.getppid(), 'admission helper is not a child of controller')
    require(request['config'] == actual['config'], 'resolved guest configuration mismatch')
    config = actual['config']
    require(config['keep_running'] == '0' and config['keep_overlay'] == '0' and
            config['guest_cleanup'] == '1' and config['guest_cmd'] and
            config['guest_evidence_dir'], 'guest retirement/evidence required')
    require(request['inputs'] == [file_binding(path) for path in actual['input_paths']],
            'guest input binding mismatch')
    require(request['limits'] == observed_limits(), 'resource profile mismatch')
    require(0 < int(config['cpus']) <= 4, 'guest CPU limit exceeded')
    memory = re.fullmatch(r'([1-9][0-9]*)([MG]?)', config['memory'])
    require(memory is not None, 'unsupported guest memory size')
    memory_bytes = int(memory[1]) * (1024**3 if memory[2] == 'G' else 1024**2)
    require(memory_bytes <= request['limits']['memory_bytes'], 'guest memory exceeds profile')
    require(0 < int(config['guest_cleanup_timeout']) <= 300 and
            0 < int(config['guest_cmd_timeout']) <= 3600, 'bounded command and cleanup deadlines required')
    argv = config['qemu_argv']
    require(argv[0] == str(canonical(argv[0])) and '-daemonize' in argv and
            'restrict=on' in argv[argv.index('-nic') + 1], 'unresolved or unrestricted QEMU argv')
    canonical(config['log_dir'])
    require(not os.path.lexists(config['log_dir']), 'evidence root already exists')
    require(config['overlay'] == config['log_dir'] + '/guest-overlay.qcow2', 'overlay root mismatch')
    fd = pidfd_open(actual['controller_pid'])
    os.close(fd)
    return request, snapshots


def verify_source_identities():
    require(isinstance(_AUTHENTICATED_IDENTITIES, dict) and
            set(_AUTHENTICATED_IDENTITIES) == set(SOURCES), 'bootstrap source identities missing')
    for relative, expected in _AUTHENTICATED_IDENTITIES.items():
        info = (ROOT / relative).lstat()
        observed = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
        require(stat.S_ISREG(info.st_mode) and observed == expected, 'source path/identity changed')


def provider(snapshot, expected_hash, expected_identity):
    require(type(snapshot) is bytes and digest(snapshot) == expected_hash, 'provider snapshot hash mismatch')
    info = PROVIDER.lstat()
    require(stat.S_ISREG(info.st_mode) and
            (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) == expected_identity,
            'provider path/identity changed before execution')
    # Never ask SourceFileLoader (or sys.modules/__pycache__) to reopen or
    # substitute code after validation. This namespace is private to this call.
    module = types.ModuleType('guest_heavy_provider_snapshot')
    module.__file__ = str(PROVIDER)
    exec(compile(snapshot, str(PROVIDER), 'exec', dont_inherit=True), module.__dict__)
    return module


def admit(request_path, expected_hash, fetched_commit, actual):
    request, snapshots = authenticate(request_path, expected_hash, fetched_commit, actual)
    common = provider(snapshots['scripts/native_rust_exact_disk_build_wrapper.py'],
                      request['sources']['scripts/native_rust_exact_disk_build_wrapper.py'],
                      _AUTHENTICATED_IDENTITIES['scripts/native_rust_exact_disk_build_wrapper.py'])
    verify_source_identities()
    require(HEAVY_ENTRY_CONTRACT_RELEASED and common.HEAVY_ENTRY_CONTRACT_RELEASED,
            'shared build/image/guest entry contract not released')
    lock = canonical(common.SHARED_HEAVY_LOCK_PATH)
    # Do not create the parent or evidence directory before exclusive admission.
    record = {'schema': 'mckernel.heavy-operation.guest.v1', 'kind': 'guest',
              'controller': request['controller'], 'request_sha256': expected_hash,
              'fetched_commit': fetched_commit, 'request': request, 'qemu': None}
    write_claim(lock, record)
    root = Path(request['config']['log_dir'])
    root.mkdir(mode=0o700)
    fsync_dir(root.parent)
    exclusive_write(root / 'heavy-operation-acquire.json', encode({'lock': str(lock), 'record': record}))


def acquired(root):
    root = canonical(root)
    token = strict_json(read_file(root / 'heavy-operation-acquire.json'))
    lock = canonical(token['lock'])
    current = strict_json(read_file(lock))
    original = dict(current)
    original['qemu'] = None
    original['device'] = token['record']['device']
    original['inode'] = token['record']['inode']
    require(original == token['record'], 'shared lock owner changed')
    info = lock.lstat()
    require((info.st_dev, info.st_ino) == (current['device'], current['inode']), 'shared claim inode changed')
    require(process_state(current['controller']) == 'same', 'controller disappeared')
    require(current['request']['config']['log_dir'] == str(root), 'evidence root changed')
    return lock, current


def qemu_command(pid):
    argv = Path('/proc', str(pid), 'cmdline').read_bytes().split(b'\0')[:-1]
    executable = str(Path('/proc', str(pid), 'exe').resolve())
    return argv, executable


def register_qemu(root, pid):
    lock, record = acquired(root)
    require(record['qemu'] is None, 'QEMU identity already registered')
    expected = identity(pid)
    argv, executable = qemu_command(pid)
    require(argv == [arg.encode() for arg in record['request']['config']['qemu_argv']], 'QEMU argv changed')
    require(executable == record['request']['config']['qemu_argv'][0],
            'QEMU executable changed')
    require(identity(pid) == expected, 'QEMU incarnation changed during registration')
    record['qemu'] = expected
    # Prepared O_EXCL file plus atomic rename: crash leaves old claim or complete
    # new claim, never a truncated shared claim or an interval without exclusion.
    update = Path(str(lock) + '.guest-' + record['request_sha256'] + '.update')
    write_claim(update, record)
    acquired(root)
    os.replace(str(update), str(lock))
    fsync_dir(lock.parent)
    exclusive_write(Path(root) / 'qemu-started.json', encode(expected))


def archive_members(root):
    members = {}
    require((root / 'guest-evidence.tar').stat().st_size <= 64 * 1024**2, 'archive exceeds evidence bound')
    with tarfile.open(str(root / 'guest-evidence.tar'), 'r:') as archive:
        for entry in archive:
            name = entry.name
            while name.startswith('./'):
                name = name[2:]
            if entry.isdir():
                require(name in ('', '.') or (not Path(name).is_absolute() and '..' not in Path(name).parts),
                        'unsafe archive directory')
                continue
            require(entry.isfile() and name and not Path(name).is_absolute() and
                    '..' not in Path(name).parts and name not in members, 'unsafe/duplicate archive member')
            members[name] = archive.extractfile(entry).read()
    require('SHA256SUMS' in members, 'archive manifest missing')
    expected = {}
    for line in members['SHA256SUMS'].decode().splitlines():
        sha, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        while name.startswith('./'):
            name = name[2:]
        require(name not in expected and name in members and name != 'SHA256SUMS', 'unsafe manifest member')
        require(sha == digest(members[name]), 'archive manifest digest mismatch')
        expected[name] = sha
    require(set(expected) == set(members) - {'SHA256SUMS'} and expected, 'archive manifest coverage mismatch')
    return members


def extract_evidence(root):
    root = canonical(root)
    acquired(root)
    members = archive_members(root)
    destination = root / 'guest-evidence'
    destination.mkdir(mode=0o700)
    for name, data in members.items():
        target = destination / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        exclusive_write(target, data)
    fsync_dir(destination)
    fsync_dir(root)


def seal_and_release(root, status):
    root = canonical(root)
    lock, record = acquired(root)
    require(record['qemu'] is not None, 'QEMU identity was never registered')
    require(set(status) == {'cleanup_rc', 'evidence_rc', 'command_rc'} and
            all(type(v) is int for v in status.values()), 'invalid final status')
    exclusive_write(root / 'run-status.json', encode(status))
    require(status['cleanup_rc'] == 0 and status['evidence_rc'] == 0,
            'cleanup or evidence collection failed; retaining lock')
    require(process_state(record['qemu']) == 'absent', 'QEMU retirement incomplete')
    overlay = Path(record['request']['config']['overlay'])
    require(not os.path.lexists(overlay), 'overlay remains')
    members = {}
    for name in REQUIRED_LOGS:
        members[name] = digest(read_file(root / name))
    archive_hash = members['guest-evidence.tar']
    require(read_file(root / 'guest-evidence.tar.sha256').decode().split() ==
            [archive_hash, 'guest-evidence.tar'], 'archive digest mismatch')
    manifest = read_file(root / 'guest-evidence/SHA256SUMS').decode().splitlines()
    require(bool(manifest), 'empty guest manifest')
    listed = set()
    for line in manifest:
        sha, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        while name.startswith('./'):
            name = name[2:]
        require(name not in listed and name != 'SHA256SUMS', 'duplicate/self manifest member')
        listed.add(name)
        target = root / 'guest-evidence' / name
        require(root / 'guest-evidence' in target.resolve().parents, 'unsafe manifest member')
        members['guest-evidence/' + name] = digest(read_file(target))
        require(members['guest-evidence/' + name] == sha, 'manifest member mismatch')
    contents = archive_members(root)
    require(set(contents) == listed | {'SHA256SUMS'}, 'archive/manifest member set mismatch')
    for name, data in contents.items():
        require(read_file(root / 'guest-evidence' / name) == data, 'archive/extracted bytes mismatch')
    for name in members:
        fd = os.open(str(root / name), os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        fsync_dir((root / name).parent)
    fsync_dir(root)
    seal = {'schema': 'mckernel.guest-seal.v1', 'request_sha256': record['request_sha256'],
            'controller': record['controller'], 'qemu': record['qemu'], 'members': members,
            'status': status}
    exclusive_write(root / 'evidence-seal.json', encode(seal))
    require(strict_json(read_file(root / 'evidence-seal.json')) == seal, 'seal readback mismatch')
    for name, sha in members.items():
        require(digest(read_file(root / name)) == sha, 'sealed evidence changed')
    exclusive_write(root / 'heavy-operation-result.json', encode({
        'status': 'RETIRED', 'evidence_seal_sha256': digest(encode(seal)), 'qemu': record['qemu']}))
    require(process_state(record['qemu']) == 'absent' and not os.path.lexists(overlay),
            'retirement changed before release')
    _, final = acquired(root)
    require(final == record, 'lock changed before release')
    lock.unlink()
    fsync_dir(lock.parent)


def main():
    require(_AUTHENTICATED_SOURCES is not None, 'direct helper execution is forbidden; use shell bootstrap')
    verify_source_identities()
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('admit', 'register', 'state', 'stop', 'seal', 'extract'))
    parser.add_argument('arguments', nargs='*')
    args = parser.parse_args()
    if args.operation == 'admit':
        admit(*args.arguments, strict_json(sys.stdin.buffer.read()))
    elif args.operation == 'register':
        register_qemu(args.arguments[0], int(args.arguments[1]))
    elif args.operation == 'extract':
        extract_evidence(args.arguments[0])
    elif args.operation in ('state', 'stop'):
        _, record = acquired(args.arguments[0])
        require(record['qemu'] is not None, 'QEMU identity missing')
        if args.operation == 'stop':
            retire_process(record['qemu'])
        else:
            require(process_state(record['qemu']) == 'same', 'QEMU is absent')
    else:
        seal_and_release(args.arguments[0], strict_json(sys.stdin.buffer.read()))


if __name__ == '__main__':
    main()
