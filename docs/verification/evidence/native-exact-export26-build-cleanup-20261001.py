#!/usr/bin/env python3
"""One-shot exportset-26 retirement. Source only; a pinned release is required.

The independently reviewed command supplies the release commit and SHA256.
That commit contains this helper and the release, whose packet hash binds this
helper without embedding the release hash in its own source. No force/volume
removal is supported. The exclusion is retained in a fixed durable quarantine
even on success. This packet never unlinks it; later maintenance requires its
own authorization. Every uncertainty leaves recoverable exclusion bytes.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess

REPO = Path('/home/holden/mckernel')
SCRATCH = Path('/home/holden/mckernel-work/scratch')
CANDIDATE = 'c81aeaca5cedd893981a058444fa11a03a49a744'
CONTAINER = 'f37e71e0731fb6cd4068746225d65eb1b372d6ba88c929def94ae889caa4c68e'
NAME = 'mckernel-image-b4bbcea94b854c40a6da36b1c80469d0'
NONCE = '1b589373ab0c4ce59128f021a27bfad7'
IMAGE = 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'
OLD_CONTAINER = 'aef5164c5209f62b5f1be6d545f34001779d2ed78008235114890f981635708b'
OLD_NAME = 'mckernel-image-bc0df6c9bd6d4234a1ec686df14ec493'
OWNER = SCRATCH / 'native-exact-mckernel-image-owner-evidence-c81aeaca-exportset-26'
WORK = SCRATCH / 'native-exact-mckernel-image-work-c81aeaca-exportset-26'
OWNER_RECEIPT = OWNER / 'owner-receipt.json'
DRIVER_RECEIPT = WORK / 'evidence/receipt.json'
LOG = OWNER / 'attempt/container.log'
REQUEST = SCRATCH / 'native-exact-mckernel-image-request-c81aeaca-exportset-26.json'
LEASE = SCRATCH / 'native-exact-mckernel-image-lease-c81aeaca-exportset-26.json'
EXCLUSION = SCRATCH / 'native-exact-candidate-operational-exclusion-exportset-26.json'
EXCLUSION_SHA = '8099da3fbac5e6cfc3722af036614d7e5434c8988a7d2e172581bac64a606c86'
EXCLUSION_ID = (1831, 90699)
LOG_SHA = '3265a9f6bacbb32e7f0222543ac7a70a83685b567636cabcaa0647ffd50baa24'
EVIDENCE = SCRATCH / 'native-exact-export26-build-cleanup-20261001-3'
QUARANTINE = '.native-exact-export26-build-cleanup-20261001-3-quarantine'
RELEASE_PATH = 'docs/verification/evidence/native-exact-export26-build-cleanup-release-20261001-3.json'
PACKET_PATH = 'docs/verification/evidence/native-exact-export26-build-cleanup-20261001.py'
PINNED_FILES = {
    OWNER_RECEIPT: '462d3f7c3d8426c7b6a08085481fa470b9bd9b05a3d659390b313074291ef301',
    DRIVER_RECEIPT: '9ead2e935ad1e0bb791d8ab0da8221a68eb7a5f3b64a1c571c3a2e4ad6c632c6',
    LOG: LOG_SHA,
    REQUEST: 'bfe96ee458677468e29c5f5efbde0c369a05363348ed666c2624d894be9c1e98',
    WORK / 'output/build/kernel/mckernel.img': 'fa6685543160fcaa5000b535ec8bd6fc70230465109564c3fb2beecb95bf39ed',
    WORK / 'output/build/kernel/mckernel.img.map': '9a27435ca9faf2be359ae8a23f6f9e5d71a8701ccdcb2349e0d420f7b22bb7b3',
    WORK / 'output/build/kernel/rust/mckernel_rust.o': '532af6482181b68dfa4f6176fd50de34a999b53bbae9167f9c7cde0b3af70f92',
    SCRATCH / 'native-exact-candidate-operational-exclusion-exportset-25.json': '2eeed65d24ff927cee2421ff49dc3ee0351f682cf96e71517afa375a3f3d7c18',
    SCRATCH / 'native-exact-mckernel-image-owner-evidence-6fed3a10-exportset-25/owner-receipt.json': 'df80c9c506e47bb3b5905cd5970e077dfa8744e9cd60422bb9c0c2f927c98785',
    SCRATCH / 'native-exact-mckernel-image-work-6fed3a10-exportset-25/evidence/receipt.json': '7b69305655bd071b77ae79d6b3173bb8ffb03a46be03b6b84317978d7cf4e467',
}
CLIENTS = {
    'command-0427f7724e03488490d3e4e92cc4807b': 2421624,
    'command-d52b0fe6b8a344128ff1f85d5880de27': 2421637,
    'command-c9e9350f28a34e8295c761fc9bfa0e99': 2421649,
    'command-50ca5c304e0544619cc9ea1ad0510680': 2421661,
    'command-d653dec8a711466d8e064fffc0af9954': 2421723,
    'command-e4537e815c804d90a656cf2e88891a5c': 2424530,
    'command-0ea00086082f457b840aade62710a00c': 2424542,
}
CLIENT_SHA = {
    'command-0427f7724e03488490d3e4e92cc4807b': '9a682f9e5b0e69ccb5f6b413eaee584331bd8353fc2dd263d00154f8990a464b',
    'command-d52b0fe6b8a344128ff1f85d5880de27': '0f997324cf310db59634a888d5bedcfb75421a617284b806dc930b200c37974e',
    'command-c9e9350f28a34e8295c761fc9bfa0e99': '139dfb2b72f4417bda28be54390093ef5952c1c36b967df480bd8837741c2c57',
    'command-50ca5c304e0544619cc9ea1ad0510680': '3eab3a73c8a265b0e3ea91e0178046b3d6d7b5cfa4b4953a8a092e4cfb03c561',
    'command-d653dec8a711466d8e064fffc0af9954': '0d5a7482eed9deccc9d2455753c0c41cb7688155d29da42f6d56cfbea5bede2b',
    'command-e4537e815c804d90a656cf2e88891a5c': '4ebbbcabf42c114f421e33802064d4cff9614c868c6cb1354f662752609a2a2f',
    'command-0ea00086082f457b840aade62710a00c': '39e12925bb5b94cf2eb636e9584389bd1b1c2070bf93f1641c08493bd565c32d',
}
SIGNALS = {signal.SIGINT, signal.SIGTERM, signal.SIGHUP}
# This historical read-only bind has exactly two names. Both names, including
# the otherwise unrelated retained candidate alias, must authenticate together.
# No other hardlinked input is admitted by this exception.
HARDLINK_PATHS = (
    REPO / 'scripts/native_rust_exact_build_offline.py',
    Path('/home/holden/mckernel-exact-candidate-d0947e0c/scripts/native_rust_exact_build_offline.py'),
)
HARDLINK_METADATA = (66306, 47485298, 2, 27338, 0o600, 1000)
HARDLINK_SHA = 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a'


class Error(RuntimeError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def open_directory(path):
    """Walk absolute parents without accepting symlinks."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Error('absolute no-traversal path required')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def _read_stable_file(path, limit, required_links):
    parent = open_directory(Path(path).parent)
    fd = None
    try:
        fd = os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != required_links or before.st_size > limit:
            raise Error('unbounded/nonordinary file: ' + str(path))
        chunks = []
        count = 0
        while True:
            data = os.read(fd, min(1 << 20, limit - count + 1))
            if not data:
                break
            chunks.append(data)
            count += len(data)
            if count > limit:
                raise Error('file grew beyond bound')
        after = os.fstat(fd)
        named = os.stat(Path(path).name, dir_fd=parent, follow_symlinks=False)
        fields = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_nlink, s.st_mtime_ns, s.st_ctime_ns)
        if fields(before) != fields(after) or fields(after) != fields(named):
            raise Error('file changed during read')
        return b''.join(chunks), after
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def read_file(path, limit=128 << 20):
    path = Path(path)
    if path not in HARDLINK_PATHS:
        return _read_stable_file(path, limit, 1)
    observed = {}
    for alias in HARDLINK_PATHS:
        data, st = _read_stable_file(alias, limit, 2)
        identity = (st.st_dev, st.st_ino, st.st_nlink, st.st_size,
                    stat.S_IMODE(st.st_mode), st.st_uid)
        if identity != HARDLINK_METADATA or sha(data) != HARDLINK_SHA:
            raise Error('exact hardlink bind identity/bytes mismatch')
        observed[alias] = (data, st)
    # Recheck both names after the pair was read: an alias change must not be
    # hidden by authenticating the primary and alias at different instants.
    for alias, (data, before) in observed.items():
        again, after = _read_stable_file(alias, limit, 2)
        fields = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_nlink,
                            s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if again != data or fields(before) != fields(after):
            raise Error('exact hardlink bind changed during authentication')
    return observed[path]


def checked(path, expected):
    data, st = read_file(path)
    if sha(data) != expected:
        raise Error('hash mismatch: ' + str(path))
    return data, st


def absent(path):
    # Permission/I/O failures are not evidence of absence.
    try:
        os.lstat(path)
    except FileNotFoundError:
        return
    raise Error('must be absent: ' + str(path))


def retired():
    absent(LEASE)
    for pid in (2420278, *CLIENTS.values()):
        absent('/proc/' + str(pid))
    for name, pid in CLIENTS.items():
        row = json.loads(checked(OWNER / 'attempt' / name / 'status.json', CLIENT_SHA[name])[0])
        if row.get('pid') != pid or row.get('state') != 'exited' or row.get('exit_code') != 0:
            raise Error('client status identity changed')


def exclusion(path=None):
    path = EXCLUSION if path is None else path
    data, st = checked(path, EXCLUSION_SHA)
    if (st.st_dev, st.st_ino) != EXCLUSION_ID or st.st_uid != 1000 or stat.S_IMODE(st.st_mode) != 0o600 or len(data) != 269:
        raise Error('exclusion identity/mode/size changed')
    return data


def snapshot():
    rows = {}
    for path, expected in PINNED_FILES.items():
        _, st = checked(path, expected)
        rows[str(path)] = [st.st_dev, st.st_ino, st.st_size, stat.S_IMODE(st.st_mode), expected]
    receipt = json.loads(read_file(OWNER_RECEIPT)[0])
    if receipt.get('candidate_sha') != CANDIDATE or receipt.get('owner_nonce') != NONCE or receipt.get('status') != 'PASS':
        raise Error('owner receipt semantic mismatch')
    # Docker rm without volume flags must not touch any bind source. Record and
    # compare their identities, and hashes for ordinary-file binds, at both ends.
    old_receipt_path = SCRATCH / 'native-exact-mckernel-image-owner-evidence-6fed3a10-exportset-25/owner-receipt.json'
    old_receipt = json.loads(read_file(old_receipt_path)[0])
    binds = receipt['terminal_container_info']['Mounts'] + old_receipt['terminal_container_info']['Mounts']
    binds += [{'Source': str(p)} for p in (OWNER, WORK / 'evidence', old_receipt_path.parent,
              SCRATCH / 'native-exact-mckernel-image-work-6fed3a10-exportset-25/evidence')]
    for bind in binds:
        path = Path(bind['Source'])
        parent = open_directory(path.parent)
        try:
            st = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        finally:
            os.close(parent)
        if stat.S_ISDIR(st.st_mode):
            rows[str(path)] = [st.st_dev, st.st_ino, stat.S_IMODE(st.st_mode)]
        elif stat.S_ISREG(st.st_mode):
            data, st = read_file(path)
            rows[str(path)] = [st.st_dev, st.st_ino, st.st_size, stat.S_IMODE(st.st_mode), sha(data)]
        else:
            raise Error('nonordinary bind source')
    return rows


def run(argv, timeout=30):
    # Preserve inherited SUDO_ASKPASS without reading or executing it ourselves.
    env = os.environ.copy()
    env.update(LC_ALL='C', PATH='/usr/bin:/bin', DOCKER_CONFIG='/nonexistent', GIT_NO_REPLACE_OBJECTS='1', GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null')
    return subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, env=env, check=False)


def git(*args):
    p = run(['/usr/bin/git', '-C', str(REPO), *args])
    if p.returncode:
        raise Error('git authentication failed')
    return p.stdout


def release_guard(commit, expected):
    if Path(__file__).absolute() != REPO / PACKET_PATH:
        raise Error('helper must run at its reviewed absolute path')
    if not re.fullmatch('[0-9a-f]{40}', commit) or not re.fullmatch('[0-9a-f]{64}', expected):
        raise Error('independently pinned release commit/hash required')
    if git('rev-parse', commit + '^{commit}').decode().strip() != commit:
        raise Error('release commit unavailable')
    git('merge-base', '--is-ancestor', commit, 'refs/remotes/origin/codex/local-native-staging-repair')
    raw = git('show', commit + ':' + RELEASE_PATH)
    if sha(raw) != expected or read_file(REPO / RELEASE_PATH)[0] != raw:
        raise Error('committed release mismatch')
    packet = read_file(REPO / PACKET_PATH)[0]
    if git('show', commit + ':' + PACKET_PATH) != packet:
        raise Error('committed helper mismatch')
    d = json.loads(raw)
    required = {
        'schema': 'mckernel.export26-cleanup-release.v1',
        'status': 'PASS_EXECUTION_EXPORT26_CLEANUP',
        'packet_sha256': sha(packet), 'candidate_sha': CANDIDATE,
        'container_id': CONTAINER, 'container_name': NAME, 'owner_nonce': NONCE,
        'image_id': IMAGE, 'exclusion_sha256': EXCLUSION_SHA,
        'exclusion_device_inode': '1831:90699', 'evidence_root': str(EVIDENCE),
        'log_sha256': LOG_SHA, 'invocations': 1,
        'owner_receipt_sha256': PINNED_FILES[OWNER_RECEIPT],
        'driver_receipt_sha256': PINNED_FILES[DRIVER_RECEIPT],
    }
    if any(d.get(k) != v for k, v in required.items()):
        raise Error('release field mismatch')
    return raw


def docker(*args):
    return run(['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host', 'unix:///var/run/docker.sock', *args])


def census(result):
    if result.returncode != 0 or result.stderr.strip() or not result.stdout.strip():
        raise Error('daemon census unsuccessful or empty')
    try:
        rows = [json.loads(line) for line in result.stdout.splitlines()]
    except (ValueError, TypeError):
        raise Error('malformed daemon census')
    ids = [x.get('ID') for x in rows]
    if any(not isinstance(x, str) or not re.fullmatch('[0-9a-f]{64}', x) for x in ids) or len(set(ids)) != len(ids):
        raise Error('invalid/duplicate full container IDs')
    old = [x for x in rows if x['ID'] == OLD_CONTAINER]
    if len(old) != 1 or old[0].get('Names') != OLD_NAME or old[0].get('State') != 'exited':
        raise Error('exportset-25 retained failure changed/absent')
    return rows


def inspect(result):
    if result.returncode != 0 or result.stderr.strip():
        raise Error('inspect failed')
    try:
        rows = json.loads(result.stdout)
        if not isinstance(rows, list) or len(rows) != 1:
            raise Error('inspect cardinality')
        x = rows[0]
        state = x['State']
        good = (x['Id'] == CONTAINER and x['Name'] == '/' + NAME and x['Image'] == IMAGE and
                x['Config']['Labels']['mckernel.owner'] == NONCE and
                state['Status'] == 'exited' and state['Pid'] == 0 and state['ExitCode'] == 0 and
                state['Running'] is False and state['OOMKilled'] is False and state['Paused'] is False and
                state['Restarting'] is False and state['Dead'] is False)
        if not good:
            raise Error('container identity or terminal state changed')
        retained = json.loads(read_file(OWNER_RECEIPT)[0])['terminal_container_info']
        # Docker may reorder Mounts between inspect calls.  Authenticate the
        # complete rows as an unordered multiset: sorting canonical rows
        # preserves cardinality and duplicate rows while rejecting any field
        # mutation, omission, or added duplicate.
        mounts = lambda value: sorted(json.dumps(row, sort_keys=True,
                                                 separators=(',', ':'))
                                      for row in value)
        if mounts(x['Mounts']) != mounts(retained['Mounts']) or x['HostConfig'] != retained['HostConfig']:
            raise Error('container mount/profile changed')
        return x
    except (KeyError, TypeError, ValueError):
        raise Error('malformed inspect')


class Journal:
    def __init__(self):
        self.parent = open_directory(EVIDENCE.parent)
        self.fd = None
        try:
            os.mkdir(EVIDENCE.name, 0o700, dir_fd=self.parent)
            os.fsync(self.parent)
            self.fd = os.open(EVIDENCE.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.parent)
        except BaseException:
            os.close(self.parent)
            raise

    def put(self, name, data):
        if '/' in name or name in ('.', '..'):
            raise Error('invalid evidence name')
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        try:
            view = memoryview(data)
            while view:
                n = os.write(fd, view)
                if n <= 0:
                    raise Error('short evidence write')
                view = view[n:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.fd)

    def event(self, name, **fields):
        self.put(name + '.json', (json.dumps(fields, sort_keys=True) + '\n').encode())

    def capture(self, name, result):
        self.put(name + '.stdout', result.stdout)
        self.put(name + '.stderr', result.stderr)
        self.event(name, returncode=result.returncode)

    def close(self):
        os.close(self.fd)
        os.close(self.parent)


class Cancellation:
    def __init__(self):
        self.received = []
        self.original = {}

    def handler(self, signum, _frame):
        self.received.append(signum)

    def __enter__(self):
        for sig in SIGNALS:
            self.original[sig] = signal.signal(sig, self.handler)
        return self

    def check(self):
        if self.received or SIGNALS.intersection(signal.sigpending()):
            raise Error('interrupted; retained state requires inspection')

    def __exit__(self, *_):
        for sig, previous in self.original.items():
            signal.signal(sig, previous)


def rename_noreplace(srcfd, name, dstfd):
    libc = ctypes.CDLL(None, use_errno=True)
    fn = getattr(libc, 'renameat2', None)
    if fn is None or fn(srcfd, name.encode(), dstfd, name.encode(), 1):
        raise Error('quarantine rename failed')


def quarantine_exclusion(journal, cancellation):
    parent = open_directory(EXCLUSION.parent)
    qfd = None
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)
    try:
        cancellation.check()
        exclusion(EXCLUSION)
        os.mkdir(QUARANTINE, 0o700, dir_fd=parent)
        os.fsync(parent)
        qfd = os.open(QUARANTINE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        journal.event('quarantine-intent', path=str(EXCLUSION), quarantine=QUARANTINE)
        cancellation.check()
        rename_noreplace(parent, EXCLUSION.name, qfd)
        os.fsync(parent)
        os.fsync(qfd)
        moved = EXCLUSION.parent / QUARANTINE / EXCLUSION.name
        exclusion(moved)
        journal.event('quarantined', path=str(moved), sha256=EXCLUSION_SHA)
        cancellation.check()
        # Retention is the terminal state, including after failures in directory
        # fsync, final preservation checks, or PASS publication. Never unlink.
        exclusion(moved)
        os.fsync(qfd)
        journal.event('exclusion-retained', path=str(moved), sha256=EXCLUSION_SHA)
    finally:
        if qfd is not None:
            os.close(qfd)
        os.close(parent)
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def execute(commit, release_sha):
    release = release_guard(commit, release_sha)
    with Cancellation() as cancellation:
        cancellation.check()
        retired()
        exclusion()
        before = snapshot()
        # The fixed O_EXCL directory is the durable one-shot claim. Never retry
        # it automatically, including failures before Docker removal.
        journal = Journal()
        try:
            journal.put('release.json', release)
            journal.event('protected-before', paths=before)
            initial = docker('ps', '-a', '--no-trunc', '--format', '{{json .}}')
            journal.capture('census-before', initial)
            rows = census(initial)
            if len([x for x in rows if x['ID'] == CONTAINER and x.get('Names') == NAME and x.get('State') == 'exited']) != 1:
                raise Error('target absent or changed before removal')
            inspected = docker('inspect', CONTAINER)
            journal.capture('inspect-before', inspected)
            inspect(inspected)
            live_log = docker('logs', CONTAINER)
            journal.capture('logs-before', live_log)
            if live_log.returncode != 0 or sha(live_log.stdout + live_log.stderr) != LOG_SHA:
                raise Error('live log differs from retained log')
            journal.put('retained-container.log', checked(LOG, LOG_SHA)[0])
            retired()
            exclusion()
            if snapshot() != before:
                raise Error('protected inputs changed before removal')
            cancellation.check()
            journal.event('remove-intent', container=CONTAINER)
            cancellation.check()
            removed = docker('rm', '--no-prune', CONTAINER)
            journal.capture('remove-result', removed)
            if removed.returncode != 0 or removed.stderr.strip() or removed.stdout.strip() != CONTAINER.encode():
                raise Error('container removal uncertain')
            cancellation.check()
            final = docker('ps', '-a', '--no-trunc', '--format', '{{json .}}')
            journal.capture('census-after', final)
            rows = census(final)
            if any(x['ID'] == CONTAINER or x.get('Names') == NAME for x in rows):
                raise Error('container still present')
            journal.event('absence-proven', container=CONTAINER)
            retired()
            if snapshot() != before:
                raise Error('protected inputs changed after removal')
            cancellation.check()
            quarantine_exclusion(journal, cancellation)
            cancellation.check()
            if snapshot() != before:
                raise Error('protected inputs changed at completion')
            absent(EXCLUSION)
            retained_path = EXCLUSION.parent / QUARANTINE / EXCLUSION.name
            exclusion(retained_path)
            journal.event('PASS', container=CONTAINER, exclusion_sha256=EXCLUSION_SHA,
                          retained_exclusion_path=str(retained_path),
                          retained_exclusion_device_inode=list(EXCLUSION_ID),
                          original_exclusion_absent=True,
                          scope='terminal exportset-26 container removed; exact exclusion retained in quarantine')
        except BaseException as exc:
            try:
                journal.event('FAIL', error=type(exc).__name__, detail=str(exc)[:2048],
                              exclusion_may_be_quarantined=True)
            except BaseException:
                pass
            raise
        finally:
            journal.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release-commit', required=True)
    parser.add_argument('--release-sha256', required=True)
    args = parser.parse_args(argv)
    execute(args.release_commit, args.release_sha256)


if __name__ == '__main__':
    main()
