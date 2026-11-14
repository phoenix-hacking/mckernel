#!/usr/bin/env python3
"""Exact one-shot retirement of the reviewed idle authority1 quarantine guard.

No container/exclusion cleanup or workload authority. No numeric/group signal
fallback. Execution requires the fixed profile and a future exact source review.
"""
import argparse
import ast
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import time

REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
PROFILE = REPO / 'docs/verification/evidence/scratch22-authority1-root-quarantine-recovery-independent-review-20261017.json'
PROFILE_SHA = 'be4ea78f63872e69f9f1463d0587a9d6ebe6eeab5fbec923588101c5c89e4a19'
PROC_SOURCE = REPO / 'scripts/native_exact_scratch21_terminal_cleanup.py'
PROC_SOURCE_SHA = '6606af40114eb5b6019438c4127948081d80bbe65144d841e906a7cba84aabed'
SELF = REPO / 'scripts/native_exact_scratch22_authority1_quarantine_recovery.py'
TEST = REPO / 'scripts/tests/test_native_exact_scratch22_authority1_quarantine_recovery.py'
PREFIX = ROOT / 'native-exact-scratch22-authority1-quarantine-recovery-20261017.correction1'
ORIGINAL_FAILURE_SHA256 = {
    str(ROOT / 'scratch22-authority1-quarantine-recovery-execution-20261017.stderr'):
        'a5b9268da8ce645636691b72c2b5848acbaf6611ec244b669da63bcbcd9ec006',
    str(ROOT / 'native-exact-scratch22-authority1-quarantine-recovery-20261017.before1.process.json'):
        '921f27731a6fd4d554b83f6f9b3001f5f465677f3bb317ae9bf41544d6a4da2d',
    str(ROOT / 'scratch22-authority1-recovery-environment-inspect-20261017.json'):
        '5fb9f8983ca81c5857203e7d6ac290af5a81e9aa74392b1f3d79c1dd267d770f',
}
PREPARED = Path(str(PREFIX) + '.prepared.json')
COMPLETE = Path(str(PREFIX) + '.complete.json')
QUARANTINE = Path(str(PREFIX) + '.quarantine.json')
LOCK = Path('/run/lock/mckernel-development.lock')
PID, START, PARENT = 80259, '718109', 80258
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
ABSENT = {80867, 80988, 81001, 81013, 81026, 81085, 207427, 207440}
LEASE = ROOT / 'native-exact-build-lease-scratch-22-authority1.json'
DEFERRED_SIGNALS = (signal.SIGHUP, signal.SIGINT, signal.SIGTERM, signal.SIGQUIT)
SMALL_LIMIT = 1 << 20
FILE_LIMIT = 128 << 20


class Refusal(RuntimeError):
    pass


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refusal('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refusal('nonfinite JSON')))


def directory(path):
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('noncanonical path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                          dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def file_identity(path, keep=False, maximum=FILE_LIMIT):
    """Stream SHA256; stable metadata excludes atime and never follows an alias."""
    parent = directory(path.parent)
    fd = None
    try:
        # The sole fixed root-owned executable cannot use O_NOATIME as holden.
        # Its reviewed node/hash is stable without atime; no received-file fallback.
        noatime = 0 if path == Path('/usr/bin/python3.8') else os.O_NOATIME
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | noatime | os.O_CLOEXEC |
                     os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum or before.st_nlink != 1:
            raise Refusal('protected regular file shape')
        digest, chunks, count = hashlib.sha256(), [], 0
        while count <= before.st_size:
            raw = os.read(fd, min(1 << 20, before.st_size + 1 - count))
            if not raw:
                break
            digest.update(raw)
            count += len(raw)
            if keep:
                chunks.append(raw)
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        after = os.fstat(fd)
        linked = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if (count != before.st_size or any(getattr(before, k) != getattr(after, k) for k in fields) or
                any(getattr(before, k) != getattr(linked, k) for k in fields)):
            raise Refusal('protected file changed')
        row = dict(path=str(path), device=before.st_dev, inode=before.st_ino,
                   size=before.st_size, mode=stat.S_IMODE(before.st_mode),
                   uid=before.st_uid, gid=before.st_gid, nlink=before.st_nlink,
                   sha256=digest.hexdigest())
        return row, b''.join(chunks) if keep else None
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def read_json(path, expected=None):
    row, raw = file_identity(path, keep=True, maximum=SMALL_LIMIT)
    if expected is not None and row['sha256'] != expected:
        raise Refusal('JSON digest differs')
    return strict(raw)


def publish(path, raw):
    parent = directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW |
                     os.O_CLOEXEC, 0o600, dir_fd=parent)
        remaining = memoryview(raw)
        while remaining:
            count = os.write(fd, remaining)
            if count <= 0:
                raise Refusal('publication made no progress')
            remaining = remaining[count:]
        os.fsync(fd)
        os.fsync(parent)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def proc_bytes(path, maximum=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        raw = os.read(fd, maximum + 1)
        if len(raw) > maximum:
            raise Refusal('proc observation exceeds bound')
        return raw
    finally:
        os.close(fd)


def proc_stat(pid):
    raw = proc_bytes('/proc/%d/stat' % pid, 4096).decode()
    prefix, separator, tail = raw.rpartition(') ')
    fields = tail.split()
    if not separator or not prefix.startswith(str(pid) + ' (') or len(fields) < 20:
        raise Refusal('process stat malformed')
    return fields


def boot_check():
    if proc_bytes('/proc/sys/kernel/random/boot_id', 128).decode().strip() != BOOT:
        raise Refusal('current boot differs')


def bind_release(path, expected):
    release = read_json(path, expected)
    profile = read_json(PROFILE, PROFILE_SHA)
    if (release.get('schema') != 'scratch22-authority1.quarantine-recovery-release.v1' or
            release.get('status') != 'PASS_EXECUTION_RELEASE' or
            release.get('profile_sha256') != PROFILE_SHA or
            release.get('execution_count') != 1 or type(release.get('execution_count')) is not int or
            release.get('fetched_source_verified') is not True or
            not re.fullmatch('[0-9a-f]{40}', str(release.get('source_checkpoint', '')))):
        raise Refusal('exact recovery release required')
    if (os.getuid(), os.getgid(), os.geteuid(), os.getegid()) != (1000, 1000, 1000, 1000):
        raise Refusal('ordinary holden process required')
    if os.uname().machine != 'x86_64' or os.sched_getaffinity(0) != {0}:
        raise Refusal('reviewed x86_64 CPU0 profile required')
    files = {str(SELF.relative_to(REPO)): file_identity(SELF)[0]['sha256'],
             str(TEST.relative_to(REPO)): file_identity(TEST)[0]['sha256']}
    review = read_json(Path(release['source_review']['path']), release['source_review']['sha256'])
    if (review.get('decision') != 'PASS_SOURCE' or review.get('implementation_ownership') is not False or
            not review.get('reviewer') or review['reviewer'] == release.get('author') or
            review.get('files_sha256') != files or release.get('files_sha256') != files or
            review.get('profile_sha256') != PROFILE_SHA or
            review.get('source_checkpoint') != release['source_checkpoint']):
        raise Refusal('independent exact recovery source review required')
    if profile.get('decision') != 'PASS_PROPOSED_PROCESS_RETIREMENT_PROFILE':
        raise Refusal('reviewed process retirement profile required')
    if release.get('original_failure_sha256') != ORIGINAL_FAILURE_SHA256:
        raise Refusal('preserved original recovery failure bindings required')
    for original, digest in ORIGINAL_FAILURE_SHA256.items():
        if file_identity(Path(original))[0]['sha256'] != digest:
            raise Refusal('preserved original recovery evidence differs')
    for fixed in (PREPARED, COMPLETE, QUARANTINE):
        if os.path.lexists(fixed):
            raise Refusal('one-shot recovery already materialized')
    return release, profile


def profile_inputs(profile):
    guard, proof = profile['bound_guard'], profile['retirement_proof']
    result = [guard['quarantine'], proof['canonical_stdout'], proof['owner_receipt'], proof['request'],
              *proof['persistent_exclusions']]
    result.append(dict(path=guard['source'], sha256=guard['source_sha256']))
    result.append(dict(path=guard['exe'], device=guard['exe_device'], inode=guard['exe_inode'],
                       size=guard['exe_size'], sha256=guard['exe_sha256']))
    result.append(dict(path=proof['container']['terminal_path'], size=proof['container']['terminal_size'],
                       sha256=proof['container']['terminal_sha256']))
    return [{key: value for key, value in row.items()
             if key in ('path', 'device', 'inode', 'size', 'sha256')} for row in result]


def protected_inputs(release, profile):
    expected = profile_inputs(profile)
    supplied = release.get('protected_inputs', {})
    if set(supplied) != {row['path'] for row in expected}:
        raise Refusal('complete fixed protected input bindings required')
    observed = {}
    for historical in expected:
        path = Path(historical['path'])
        row, _ = file_identity(path)
        if row != supplied[str(path)] or any(row.get(k) != value for k, value in historical.items()):
            raise Refusal('protected original identity differs')
        observed[str(path)] = row
    status_rows = release.get('client_statuses', [])
    evidence = Path(profile['retirement_proof']['owner_receipt']['path']).parent
    if len(status_rows) != 7 or len({r['path'] for r in status_rows}) != 7:
        raise Refusal('seven exact client statuses required')
    pids = set()
    for expected_row in status_rows:
        path = Path(expected_row['path'])
        if path.parent.parent != evidence or not re.fullmatch('command-[0-9a-f]{32}', path.parent.name) or path.name != 'status.json':
            raise Refusal('client status outside fixed evidence')
        row, raw = file_identity(path, keep=True, maximum=SMALL_LIMIT)
        value = strict(raw)
        if (row != expected_row or set(value) != {'argv', 'timeout', 'state', 'pid', 'exit_code'} or
                value['state'] != 'exited' or type(value['exit_code']) is not int or value['exit_code'] != 0 or
                type(value['pid']) is not int or value['pid'] in pids or
                value['argv'][:4] != ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock']):
            raise Refusal('Docker client retirement status differs')
        pids.add(value['pid'])
        observed[str(path)] = row
    if pids != set(profile['retirement_proof']['docker_client_pids']) or os.path.lexists(LEASE):
        raise Refusal('client identity or request lease differs')
    proof = profile['retirement_proof']
    request = read_json(Path(proof['request']['path']))
    if sha(canonical(request)[:-1]) != proof['request']['normalized_sha256']:
        raise Refusal('normalized request differs')
    for pointer in proof['persistent_exclusions']:
        owner = read_json(Path(pointer['path']))
        if (owner.get('pid') != proof['owner']['pid'] or owner.get('starttime') != proof['owner']['starttime'] or
                owner.get('boot_id') != BOOT or owner.get('request_sha256') != proof['request']['normalized_sha256']):
            raise Refusal('persistent exclusion owner differs')
    quarantine = read_json(Path(profile['bound_guard']['quarantine']['path']))
    if quarantine.get('pid') != PID or quarantine.get('reason') != profile['bound_guard']['quarantine']['reason']:
        raise Refusal('original quarantine record differs')
    return observed


def guard_identity(profile):
    boot_check()
    guard = profile['bound_guard']
    fields = proc_stat(PID)
    if fields[19] != START or int(fields[1]) != PARENT or fields[0] in ('Z', 'X', 'x'):
        raise Refusal('guard start/parent/state differs')
    status = dict(line.split(':', 1) for line in proc_bytes('/proc/%d/status' % PID).decode().splitlines() if ':' in line)
    if (status.get('Uid', '').split() != ['1000'] * 4 or status.get('Gid', '').split() != ['1000'] * 4 or
            status.get('Threads', '').strip() != '1'):
        raise Refusal('guard credentials or thread count differs')
    if proc_bytes('/proc/%d/cmdline' % PID) != b'\0'.join(arg.encode() for arg in guard['argv']) + b'\0':
        raise Refusal('guard argv differs')
    if os.readlink('/proc/%d/exe' % PID) != guard['exe']:
        raise Refusal('guard executable link differs')
    exe = os.stat('/proc/%d/exe' % PID)
    if (exe.st_dev, exe.st_ino, exe.st_size) != (guard['exe_device'], guard['exe_inode'], guard['exe_size']):
        raise Refusal('guard executable node differs')
    if file_identity(Path(guard['source']))[0]['sha256'] != guard['source_sha256']:
        raise Refusal('guard source differs')
    if proc_stat(PID)[19] != START:
        raise Refusal('guard raced during identity read')
    return dict(pid=PID, starttime=START, parent=PARENT, boot_id=BOOT, uid=1000, gid=1000, threads=1)


def lock_rows():
    rows = []
    for line in proc_bytes('/proc/locks', SMALL_LIMIT).decode().splitlines():
        fields = line.split()
        if '->' in fields:
            fields.remove('->')
        if len(fields) != 8:
            raise Refusal('kernel lock report malformed')
        major, minor, inode = fields[5].split(':')
        if (int(major, 16), int(minor, 16), int(inode)) == (0, 27, 4):
            rows.append(fields[1:])
    return rows


def require_lock_holder(pid):
    rows = lock_rows()
    if len(rows) != 1 or rows[0] != ['FLOCK', 'ADVISORY', 'WRITE', str(pid), '00:1b:4', '0', 'EOF']:
        raise Refusal('sole preserved root flock holder differs')
    return rows


def process_code():
    row, raw = file_identity(PROC_SOURCE, keep=True, maximum=SMALL_LIMIT)
    if row['sha256'] != PROC_SOURCE_SHA:
        raise Refusal('accepted process census source differs')
    tree = ast.parse(raw)
    matches = [node.value for node in tree.body if isinstance(node, ast.Assign) and
               any(isinstance(t, ast.Name) and t.id == 'PROC_CODE' for t in node.targets)]
    if len(matches) != 1:
        raise Refusal('accepted process census constant is ambiguous')
    return ast.literal_eval(matches[0])


def root_readonly(argv):
    env = dict(PATH='/usr/bin:/bin', LANG='C', LC_ALL='C')
    if 'SUDO_ASKPASS' in os.environ:
        env['SUDO_ASKPASS'] = os.environ['SUDO_ASKPASS']
    result = subprocess.run(['/usr/bin/sudo', '-A', '--', *argv], env=env,
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=30, check=False)
    if result.returncode or result.stderr or len(result.stdout) > SMALL_LIMIT:
        raise Refusal('approved root read-only observation failed')
    return result.stdout


def validate_process_report(report, challenge, caller, before):
    if (set(report) != {'schema', 'uid', 'boot_id', 'challenge', 'caller', 'publishers', 'snapshots'} or
            report['schema'] != 'scratch21.proc.v1' or type(report['uid']) is not int or report['uid'] != 0 or
            report['boot_id'] != BOOT or report['challenge'] != challenge or report['caller'] != caller or
            not isinstance(report['snapshots'], list) or len(report['snapshots']) != 2):
        raise Refusal('root process report binding differs')
    publishers = [[PID, START, '/usr/bin/python3.8']] * 2 if before else []
    if report['publishers'] != publishers:
        raise Refusal('unexpected live publisher')
    for snapshot in report['snapshots']:
        seen = {}
        for row in snapshot:
            if (not isinstance(row, list) or len(row) != 3 or type(row[0]) is not int or row[0] <= 0 or
                    type(row[1]) is not int or row[1] < 0 or not isinstance(row[2], str) or
                    not row[2].isdigit() or row[0] in seen):
                raise Refusal('root process row malformed')
            seen[row[0]] = row
        if 1 not in seen or caller[0] not in seen or seen[caller[0]][2] != caller[1] or ABSENT & set(seen):
            raise Refusal('root process census incomplete or owner/client present')
        if before and seen.get(PID) != [PID, PARENT, START]:
            raise Refusal('exact guard absent from pre-signal census')
        if not before and PID in seen and seen[PID] != [PID, PARENT, START]:
            raise Refusal('post-signal guard PID was reused')
        if any(row[1] == PID for row in seen.values()):
            raise Refusal('guard has a descendant')


def inspect_comparison(value):
    """Docker's Mounts map has no iteration order; all other data stays exact."""
    if not isinstance(value, dict) or not isinstance(value.get('Mounts'), list):
        raise Refusal('Docker inspect Mounts shape differs')
    destinations = set()
    for mount in value['Mounts']:
        if (not isinstance(mount, dict) or not isinstance(mount.get('Destination'), str) or
                not mount['Destination'].startswith('/') or mount['Destination'] in destinations):
            raise Refusal('Docker inspect mount destination missing or duplicate')
        destinations.add(mount['Destination'])
    result = dict(value)
    result['Mounts'] = sorted(value['Mounts'], key=lambda mount: mount['Destination'])
    return canonical(result)


def snapshot(label, release, profile, before):
    inputs = protected_inputs(release, profile)
    if before:
        guard_identity(profile)
        locks = require_lock_holder(PID)
    else:
        boot_check()
        locks = require_lock_holder(os.getpid())
    caller = [os.getpid(), proc_stat(os.getpid())[19]]
    challenge = os.urandom(24).hex()
    raw = root_readonly(['/usr/bin/python3', '-I', '-B', '-c', process_code(), challenge,
                         str(caller[0]), caller[1]])
    validate_process_report(strict(raw), challenge, caller, before)
    captures = {}
    def capture(kind, raw):
        path = Path(str(PREFIX) + '.' + label + '.' + kind)
        publish(path, raw)
        captures[kind] = dict(path=str(path), sha256=sha(raw), size=len(raw))
    capture('process.json', raw)
    proof = profile['retirement_proof']
    container = proof['container']
    raw = root_readonly(['/usr/bin/docker', '--host=unix:///var/run/docker.sock', 'inspect',
                         '--type', 'container', container['id']])
    capture('inspect.json', raw)  # Preserve even malformed/mismatching observations.
    observed = strict(raw)
    retained = read_json(Path(container['terminal_path']), container['terminal_sha256'])
    if (not isinstance(observed, list) or len(observed) != 1 or
            inspect_comparison(observed[0]) != inspect_comparison(retained)):
        raise Refusal('exact stopped Docker container differs')
    state = retained['State']
    if state.get('Status') != 'exited' or state.get('Pid') != 0 or state.get('ExitCode') != 1 or state.get('OOMKilled') is not False:
        raise Refusal('retained container is not positively stopped')
    raw = root_readonly(['/usr/bin/docker', '--host=unix:///var/run/docker.sock', 'ps', '-a',
                         '--no-trunc', '--format', '{{json .}}'])
    target, ids = [], set()
    for line in raw.splitlines():
        row = strict(line)
        if (not re.fullmatch('[0-9a-f]{64}', str(row.get('ID', ''))) or row['ID'] in ids or
                row.get('State') not in ('created', 'restarting', 'running', 'removing', 'paused', 'exited', 'dead')):
            raise Refusal('Docker census malformed')
        ids.add(row['ID'])
        if row['State'] in ('running', 'restarting', 'removing', 'paused'):
            raise Refusal('another active container exists')
        if row['ID'] == container['id'] or row.get('Names') == proof['owner']['container_name'] or \
                'mckernel.owner=' + proof['owner']['nonce'] in row.get('Labels', '').split(','):
            target.append(row)
    if (len(target) != 1 or target[0]['ID'] != container['id'] or
            target[0].get('Names') != proof['owner']['container_name']):
        raise Refusal('retained container inventory identity differs')
    capture('containers.jsonl', raw)
    boot_check()
    return dict(inputs=inputs, captures=captures, root_locks=locks)


def pidfd_open():
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    fd = libc.syscall(434, ctypes.c_int(PID), ctypes.c_uint(0))
    if fd < 0:
        raise OSError(ctypes.get_errno(), 'pidfd_open unavailable; no fallback')
    return int(fd)


def bind_pidfd(fd, profile):
    fields = dict(line.split(':', 1) for line in proc_bytes('/proc/self/fdinfo/%d' % fd, 4096).decode().splitlines() if ':' in line)
    if fields.get('Pid', '').strip() != str(PID):
        raise Refusal('pidfd target identity differs')
    return guard_identity(profile)


def sole_sigkill(fd):
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    code = libc.syscall(424, ctypes.c_int(fd), ctypes.c_int(signal.SIGKILL), ctypes.c_void_p(), ctypes.c_uint(0))
    if code != 0:
        raise OSError(ctypes.get_errno(), 'pidfd signal failed; never retry')
    return dict(syscall=424, signal=int(signal.SIGKILL), returncode=0)


def exit_ready(fd):
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    rows = poller.poll(30000)
    if (len(rows) != 1 or rows[0][0] != fd or not rows[0][1] & select.POLLIN or
            rows[0][1] & ~(select.POLLIN | select.POLLHUP)):
        raise Refusal('positive pidfd exit readiness unavailable')
    return dict(pidfd_exit_ready=True, events=rows)


def acquire_root_lock():
    parent = directory(LOCK.parent)
    fd = None
    try:
        fd = os.open(LOCK.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent)
        meta = os.fstat(fd)
        linked = os.stat(LOCK.name, dir_fd=parent, follow_symlinks=False)
        if (not stat.S_ISREG(meta.st_mode) or (meta.st_dev, meta.st_ino) != (27, 4) or
                meta.st_uid != 0 or meta.st_gid != 0 or meta.st_nlink != 1 or
                stat.S_IMODE(meta.st_mode) != 0o644 or meta.st_size != 0 or
                (linked.st_dev, linked.st_ino) != (27, 4)):
            raise Refusal('preserved root lock identity differs')
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result, fd = fd, None
        return result
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def quarantine_hold(lockfd):
    # No writer, diagnostic, signal handler or interrupted wait can return from
    # uncertain post-signal recovery. Reacquire the replacement flock if available.
    while True:
        if lockfd is None:
            try:
                lockfd = acquire_root_lock()
            except BaseException:
                pass
        try:
            if not os.path.lexists(QUARANTINE):
                publish(QUARANTINE, canonical(dict(status='RECOVERY_UNCERTAIN_ROOT_GUARD',
                                                  pid=os.getpid(), replacement_lock_held=lockfd is not None)))
        except BaseException:
            pass
        try:
            time.sleep(60)
        except BaseException:
            pass


def execute(release_path, checksum):
    release, profile = bind_release(release_path, checksum)
    lockfd = pidfd = None
    attempted = complete = False
    requested, handlers = [], {}
    def defer(number, _frame):
        if not requested:
            requested.append(number)
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS)
    try:
        for number in DEFERRED_SIGNALS:
            handlers[number] = signal.getsignal(number)
            signal.signal(number, defer)
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        first = snapshot('before1', release, profile, True)
        pidfd = pidfd_open()
        target = bind_pidfd(pidfd, profile)
        second = snapshot('before2', release, profile, True)
        if first['inputs'] != second['inputs'] or requested:
            raise Refusal('pre-signal proof drift or termination requested')
        target = bind_pidfd(pidfd, profile)
        prepared = dict(schema='scratch22-authority1.quarantine-recovery-prepared.v1',
                        status='PREPARED_PROCESS_RETIREMENT', profile_sha256=PROFILE_SHA,
                        original_failure_sha256=ORIGINAL_FAILURE_SHA256,
                        release_sha256=checksum, source_checkpoint=release['source_checkpoint'],
                        signal_budget=1, target=target, before=[first, second], build_status='FAIL')
        publish(PREPARED, canonical(prepared))
        bind_pidfd(pidfd, profile)
        require_lock_holder(PID)
        if requested:
            raise Refusal('termination requested before sole signal')
        attempted = True  # An uncertain syscall response consumes the sole budget.
        signalled = sole_sigkill(pidfd)
        exited = exit_ready(pidfd)
        lockfd = acquire_root_lock()
        after = snapshot('after', release, profile, False)
        if after['inputs'] != first['inputs']:
            raise Refusal('retained inputs changed after process retirement')
        require_lock_holder(os.getpid())
        record = dict(schema='scratch22-authority1.quarantine-recovery-complete.v1',
                      status='COMPLETE_PROCESS_RECOVERY', profile_sha256=PROFILE_SHA,
                      original_failure_sha256=ORIGINAL_FAILURE_SHA256,
                      release_sha256=checksum, prepared_sha256=sha(canonical(prepared)),
                      source_checkpoint=release['source_checkpoint'], target=target,
                      sole_signal=signalled, exit_proof=exited, after=after,
                      replacement_root_lock=[27, 4], deferred_signals=requested,
                      build_status='FAIL', cleanup_required=True, acceptance_credit=False)
        publish(COMPLETE, canonical(record))
        complete = True
        return dict(status=record['status'], receipt=str(COMPLETE), receipt_sha256=sha(canonical(record)),
                    build_status='FAIL', cleanup_required=True)
    except BaseException:
        if attempted and not complete:
            quarantine_hold(lockfd)
        raise
    finally:
        if lockfd is not None and complete:
            os.close(lockfd)
        if pidfd is not None:
            os.close(pidfd)
        if not attempted or complete:
            signal.pthread_sigmask(signal.SIG_BLOCK, DEFERRED_SIGNALS)
            for number, handler in handlers.items():
                signal.signal(number, handler)
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--release-sha256', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if not args.execute:
        raise Refusal('explicit --execute and exact reviewed release required')
    print(json.dumps(execute(args.release, args.release_sha256), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
