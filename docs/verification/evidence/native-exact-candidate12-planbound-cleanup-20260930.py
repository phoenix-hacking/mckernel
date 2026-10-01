#!/usr/bin/env python3
"""One-shot storage maintenance; no OS acceptance and no implicit execution release.

Release schema: mckernel.candidate12-cleanup-release.v1. The committed JSON must
equal the working file, be in a fetched commit after source_commit, and contain
status=PASS, finalization=PASS, source_commit, tool_sha256, tool_blob, plan
(the exact BINDING below), command (the complete Python argv), and outputs
(journal, receipt, status, quarantine absolute paths), retained_containers (the
exact CONTAINER_BINDINGS including authenticated receipt identities), absent_leases, and
dispatcher_exclusive=true. Run --validate-only to
check files/Git without census, output creation, or deletion. --execute requires
--release. Its committed bytes are resolved from the fetched REMOTE_REF, avoiding
a self-referential release commit hash in the command. The caller must supply an independently reviewed
release; this program does not author one. The dedicated flock serializes only
this cleanup tool; other builders do not honor it. No pathname API can exclude a malicious concurrent writer;
staging detects replacement before any irreversible deletion.
"""
import argparse
import contextlib
import ctypes
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys

REPO = Path('/home/holden/mckernel')
TOOL_PATH = 'docs/verification/evidence/native-exact-candidate12-planbound-cleanup-20260930.py'
REMOTE_REF = 'refs/remotes/origin/codex/local-native-staging-repair'
SCRATCH = '/home/holden/mckernel-work/scratch'
BINDING = {
    'path': SCRATCH + '/native-exact-candidate12-source-audit-reviewed-20260930-1.json',
    'sha256': 'eaba225bfeb8e58fa1a6a7d5cfe1ae622e5bb1f9355e359af16464968ac0f957',
    'size': 1612448, 'dev': 1831, 'ino': 90650, 'mode': 0o600, 'nlink': 1,
    'root': SCRATCH + '/mckernel-exact-candidate-4e99a82c-scratch-12',
    'identity': '1831:3693246',
    'commit': '4e99a82c9b87a7cf3d6002b75ec380fef37af7a1',
    'count': 2507, 'bytes': 9096966061, 'allocated': 9102798848,
}
MUTEX = SCRATCH + '/native-exact-candidate12-cleanup-operation.mutex'
LEASES = [SCRATCH + '/native-exact-build-lease-4e99a82c-scratch-12.json',
          SCRATCH + '/native-exact-mckernel-image-lease-4e99a82c-exportset-24.json']
CONTAINER = '053b5528de7605a712b7842b0145c7e777843c2fd14225174ac8959918a7d24f'
CONTAINER_NAME = '/mckernel-image-69d5302ef1b74816aec831cf959404ee'
HOST_CONTAINER = '4d15b3493f869a1b0a89f1dc16fda59e1c145b78e2b57308bed35f3d954e4f86'

# This is an immutable failed transaction, not a new input discovered at run
# time.  The staged-recovery mode below is deliberately bound to it so an
# operator cannot point a rename-back at a different failed cleanup attempt.
ATTEMPT2 = {
    'journal': {'path': SCRATCH + '/native-exact-candidate12-planbound-cleanup-20260930-2.journal.jsonl',
                'sha256': '4749ea4d1b97bc99959c1ec75c0f329682f834d075738264a44efde33ce90d02',
                'size': 3238188, 'dev': 1831, 'ino': 90655, 'mode': 0o600, 'nlink': 1},
    'receipt': {'path': SCRATCH + '/native-exact-candidate12-planbound-cleanup-20260930-2.receipt.json',
                'sha256': '83d22b06d9d143b3acc0508d738f6b1039184a5d2d473d314f5a1e3a65cd3c52',
                'size': 1399041, 'dev': 1831, 'ino': 90656, 'mode': 0o600, 'nlink': 1},
    'status': {'path': SCRATCH + '/native-exact-candidate12-planbound-cleanup-20260930-2.status.json',
               'sha256': 'b22762e6ef19ae31c4aad21fa2164ed9536e8d3b6b8c28e7aed886bc44d9484a',
               'size': 252, 'dev': 1831, 'ino': 90657, 'mode': 0o600, 'nlink': 1},
    'quarantine': {'path': SCRATCH + '/mckernel-exact-candidate-4e99a82c-scratch-12/.planbound-cleanup-20260930-2',
                   'dev': 1831, 'ino': 3701891, 'mode': 0o700, 'nlink': 2},
}
RECOVERY_SCHEMA = 'mckernel.candidate12-cleanup-recovery-release.v1'
_terminal_latched = False


def mount(source, destination, writable=False):
    return {'Source': source, 'Destination': destination, 'RW': writable, 'Type': 'bind',
            'Mode': '', 'Propagation': 'rprivate'}


def terminal_state(exit_code, started, finished):
    return {'Dead': False, 'Error': '', 'ExitCode': exit_code, 'FinishedAt': finished,
            'OOMKilled': False, 'Paused': False, 'Pid': 0, 'Restarting': False,
            'Running': False, 'StartedAt': started, 'Status': 'exited'}


def image_binding(export, name, nonce, proof_sha, proof_size, proof_ino, started, finished):
    """Expand only explicit immutable inventory rows below; never discover users."""
    prefix = SCRATCH + '/native-exact-mckernel-image-'
    suffix = '-4e99a82c-exportset-' + str(export)
    mounts = [mount(BINDING['root'], '/src'),
              mount(SCRATCH + '/native-exact-inputs-4e99a82c-scratch-12.json', '/inputs.json'),
              mount(prefix + 'toolchain' + suffix + '.json', '/toolchain.json'),
              mount(str(REPO) + '/scripts/native_rust_exact_mckernel_image_offline.py', '/driver.py'),
              mount(str(REPO) + '/scripts/native_rust_exact_build_offline.py', '/native_rust_exact_build_offline.py'),
              mount(prefix + 'work' + suffix, '/work', True),
              mount(SCRATCH + '/native-exact-build-output-4e99a82c-scratch-12', '/out'),
              mount(SCRATCH + '/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu'
                    if export == 24 else '/home/holden/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu', '/nightly')]
    if export in (23, 24):
        mounts += [mount(SCRATCH + '/native-exact-mckernel-gitlink-inputs-4e99a82c-exportset-23.json', '/libdwarf-inputs.json'),
                   mount(SCRATCH + '/native-exact-mckernel-gitlink-libdwarf-4e99a82c-exportset-23', '/src/executer/user/lib/libdwarf/libdwarf')]
    return {'Name': name, 'owner_nonce': nonce, 'RestartCount': 0,
            'State': terminal_state(1, started, finished),
            'proof_kind': 'image_owner_receipt',
            'proof': {'path': prefix + 'owner-evidence' + suffix + '/owner-receipt.json',
                      'sha256': proof_sha, 'size': proof_size, 'dev': 1831,
                      'ino': proof_ino, 'mode': 0o600, 'nlink': 1},
            'Mounts': mounts}


CONTAINER_BINDINGS = {
    CONTAINER: image_binding(24, CONTAINER_NAME, '09c96c3be751486ca7402481bb15b751',
        '4681bd9cdc65f62a1802cea888700437ba6c01b154cc8a094dd1719b0ec2080a', 17574, 1721765,
        '2026-09-30T22:05:50.737132162Z', '2026-09-30T22:07:04.669197043Z'),
    '282dff5ea9f3775fe8a8e2cdf8d767f86ea81b0f5a9a516a0e6ff817d1d36dde': image_binding(
        17, '/mckernel-image-2c383743e89540908f12dc9583e2847c', '44a459e57c534808bce9837596e1f125',
        '0fc0386d22935c9310815421077698f784e514d4770b8a5f0c00d40617db5b56', 15335, 1712444,
        '2026-09-30T19:39:28.64279337Z', '2026-09-30T19:40:24.157586738Z'),
    'a6e3772f3470c79a55807d38a12e0b02e84f4e0b12771d17742b99f55f2cb0ae': image_binding(
        18, '/mckernel-image-ce76ec9b4973421f8981f6cb63fa5af1', 'db5dfd5bfc7c461ba6ed28e9b4ea42ed',
        '7929772081c18f6218c4e8c782005c33a6e209caca87d4797f73fd7edfa9558c', 15336, 1712508,
        '2026-09-30T19:56:15.587595407Z', '2026-09-30T19:57:11.609545509Z'),
    '4dc6377ec81950703c1f539bfb2f491f6d9a5344d8930cd4db9fb166c6412707': image_binding(
        22, '/mckernel-image-d6f5a553c80b41c48f52ec26afb90439', 'c35d5f2a696c4a2d8f46d8be893337ba',
        '6f35ae64ae3023d17b89b6bad2b0fa81658659f4f75855af72d00564bf0c0255', 15335, 1720263,
        '2026-09-30T21:07:54.707069084Z', '2026-09-30T21:08:53.662880724Z'),
    '4f2b721b552eba9da33d5dffd664ef525b6d92e4d4d53dbf2adb1aa9cb1e8fb3': image_binding(
        23, '/mckernel-image-15024d3e89c64409b2146ecc9d969645', '385793b149644a3fa68cf1126ba54fab',
        'f37f23c81b5e2f685fd51ccb4b2a9c01c84e45650f8273c36f9fd8c073934622', 17422, 1721226,
        '2026-09-30T21:43:46.145094705Z', '2026-09-30T21:44:49.172326292Z'),
    HOST_CONTAINER: {
        'Name': '/mckernel-exact-a97aabd626bd41f59032728f2c1b5282',
        'owner_nonce': 'e18ba6fe48b4442bab26c4c8cb63c391', 'RestartCount': 0,
        'State': terminal_state(0, '2026-09-30T17:00:15.942063997Z', '2026-09-30T17:34:36.129077656Z'),
        'proof_kind': 'docker_inspect',
        'proof': {'path': SCRATCH + '/native-exact-build-evidence-4e99a82c-scratch-12/inspect-terminal.json',
                  'sha256': '96eb113aaba4436105c411d522928a80d1023a5a0e4060ba010cd37db22b36e6',
                  'size': 9713, 'dev': 1831, 'ino': 6641738, 'mode': 0o600, 'nlink': 1},
        'Mounts': [
            mount(SCRATCH + '/native-exact-build-evidence-4e99a82c-scratch-12', '/evidence', True),
            mount(BINDING['root'] + '/scripts/native_rust_exact_build_offline.py', '/driver.py'),
            mount(SCRATCH + '/native-exact-inputs-4e99a82c-scratch-12.json', '/inputs.json'),
            mount(BINDING['root'], '/src'),
            mount(SCRATCH + '/native-exact-assets-16445ab2', '/assets'),
            mount(SCRATCH + '/native-exact-build-output-4e99a82c-scratch-12', '/out', True),
        ],
    },
}
NOFOLLOW = os.O_NOFOLLOW | os.O_CLOEXEC


class Refusal(Exception):
    """Messages are fixed codes: never include subprocess output or credentials."""


def require(value, code):
    if not value:
        raise Refusal(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(path):
    p = str(path)
    require(p.startswith('/') and str(Path(p)) == p and
            all(x not in ('.', '..') for x in p.split('/')[1:]) and
            not any(ord(x) < 32 for x in p), 'path-noncanonical')
    return p


def inside(path, base):
    return path == base or path.startswith(base.rstrip('/') + '/')


@contextlib.contextmanager
def directory(path):
    """Resolve every component using no-follow directory descriptors."""
    p = canonical(path)
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW)
    try:
        for component in p.split('/')[1:]:
            if not component:
                continue
            nxt = os.open(component, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW,
                          dir_fd=fd)
            os.close(fd)
            fd = nxt
        yield fd
    finally:
        os.close(fd)


@contextlib.contextmanager
def opened(path, flags=os.O_RDONLY):
    p = Path(canonical(path))
    with directory(str(p.parent)) as parent:
        fd = os.open(p.name, flags | NOFOLLOW, dir_fd=parent)
        try:
            yield fd
        finally:
            os.close(fd)


def hash_fd(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    h = hashlib.sha256()
    while True:
        b = os.read(fd, 1024 * 1024)
        if not b:
            return h.hexdigest()
        h.update(b)


def metadata(s):
    return {'dev': s.st_dev, 'ino': s.st_ino, 'mode': stat.S_IMODE(s.st_mode),
            'size': s.st_size, 'mtime_ns': s.st_mtime_ns, 'nlink': s.st_nlink}


def verify_fd(fd, row):
    before = os.fstat(fd)
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, 'file-type-link')
    require(all(metadata(before)[k] == row[k] for k in metadata(before) if k in row),
            'file-metadata')
    require(hash_fd(fd) == row['sha256'], 'file-content')
    require(metadata(os.fstat(fd)) == metadata(before), 'file-changed-during-read')


def read_json(path, binding=None):
    with opened(path) as fd:
        if binding:
            verify_fd(fd, binding)
        else:
            s = os.fstat(fd)
            require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'json-type-link')
        os.lseek(fd, 0, os.SEEK_SET)
        chunks = []
        while True:
            b = os.read(fd, 1024 * 1024)
            if not b:
                break
            chunks.append(b)
        data = b''.join(chunks)
        if binding:
            require(sha(data) == binding['sha256'], 'json-content-race')
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'json-duplicate-key')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs), data


def git_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0')
    return env


def git(repo, *args):
    p = subprocess.run(['git', '-c', 'safe.directory=' + str(repo), '-C', str(repo),
                        *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       env=git_env(), timeout=90)
    require(p.returncode == 0, 'git-command-failed')
    return p.stdout


def committed_file(commit, path, row):
    entry = git(REPO, 'ls-tree', '-z', commit, '--', path).split(b'\0')
    require(len(entry) == 2 and entry[-1] == b'', 'git-tree-entry')
    header, name = entry[0].split(b'\t', 1)
    mode, kind, blob = header.decode('ascii').split()
    require(name.decode() == path and kind == 'blob' and blob == row['blob'] and
            mode == ('100755' if row['mode'] & 0o111 else '100644'), 'git-identity-mode')
    p = subprocess.Popen(['git', '-c', 'safe.directory=' + str(REPO), '-C', str(REPO),
                          'cat-file', 'blob', blob], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, env=git_env())
    h = hashlib.sha256()
    size = 0
    try:
        while True:
            b = p.stdout.read(1024 * 1024)
            if not b:
                break
            size += len(b)
            h.update(b)
        require(p.wait(timeout=90) == 0, 'git-blob-failed')
        require(size == row['size'] and h.hexdigest() == row['sha256'], 'git-content')
    finally:
        p.stdout.close()
        if p.poll() is None:
            p.kill()
            p.wait()


def validate_protected(plan):
    rows = plan['safety_census']['protected']
    require([r['path'] for r in rows] == plan['protected_paths'] and
            len(set(plan['protected_paths'])) == len(rows), 'protected-set')
    for row in rows:
        if row['type'] == 'directory':
            with directory(row['path']) as fd:
                s = os.fstat(fd)
                require((s.st_dev, s.st_ino, stat.S_IMODE(s.st_mode)) ==
                        (row['dev'], row['ino'], row['mode']), 'protected-directory')
        else:
            require(row['type'] == 'file', 'protected-type')
            with opened(row['path']) as fd:
                verify_fd(fd, row)


def evidence_shape(plan, staged=False):
    """Exact no-follow census, including otherwise invisible extra empty dirs."""
    base = plan['candidate_root'] + '/docs/verification/evidence'
    expected_files = {r['path'][len(base) + 1:] for r in plan['targets']}
    expected_dirs = {''}
    for name in expected_files:
        parent = str(Path(name).parent)
        while parent != '.':
            expected_dirs.add(parent)
            parent = str(Path(parent).parent)
    dirs, files = set(), set()

    def visit(fd, relative):
        dirs.add(relative)
        for name in os.listdir(fd):
            child = relative + '/' + name if relative else name
            s = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(s.st_mode):
                sub = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                try:
                    actual = os.fstat(sub)
                    require((s.st_dev, s.st_ino) == (actual.st_dev, actual.st_ino),
                            'subtree-directory-race')
                    visit(sub, child)
                    again = os.stat(name, dir_fd=fd, follow_symlinks=False)
                    require((s.st_dev, s.st_ino) == (again.st_dev, again.st_ino),
                            'subtree-directory-race')
                finally:
                    os.close(sub)
            else:
                require(stat.S_ISREG(s.st_mode), 'subtree-special-or-symlink')
                files.add(child)

    with directory(base) as fd:
        visit(fd, '')
    require(dirs == expected_dirs and files == (set() if staged else expected_files),
            'subtree-set')


def quarantine_shape(qfd, rows):
    require(set(os.listdir(qfd)) == {str(i) for i in range(len(rows))}, 'quarantine-set')
    for i, row in enumerate(rows):
        verify_name(qfd, str(i), row)


def validate_plan(path, binding=None):
    binding = BINDING if binding is None else binding
    require(str(path) == binding['path'], 'plan-path')
    plan, _ = read_json(path, binding)
    require(set(plan) == {'candidate_commit', 'candidate_identity', 'candidate_root',
                         'nested_delta_preserved', 'preserved', 'protected_paths',
                         'safety_census', 'schema', 'status', 'targets'}, 'plan-schema')
    require(plan['schema'] == 'mckernel.exact-git-source-audit.v1' and
            plan['status'] == 'AUDIT_PASS' and plan['preserved'] == [] and
            plan['nested_delta_preserved'] is True, 'plan-status')
    root = canonical(plan['candidate_root'])
    require(root == binding['root'] and plan['candidate_commit'] == binding['commit']
            and plan['candidate_identity'] == binding['identity'], 'plan-binding')
    with directory(root) as fd:
        s = os.fstat(fd)
        require(str(s.st_dev) + ':' + str(s.st_ino) == binding['identity'], 'root-identity')
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == binding['commit'], 'root-head')
    rows = plan['targets']
    require(len(rows) == binding['count'] and
            sum(r['size'] for r in rows) == binding['bytes'] and
            sum(r['allocated_bytes'] for r in rows) == binding['allocated'], 'target-totals')
    names = set()
    inodes = set()
    for row in rows:
        require(set(row) == {'allocated_bytes', 'blob', 'dev', 'ino', 'mode', 'mtime_ns',
                            'nlink', 'path', 'restore_git_path', 'sha256', 'size'}, 'row-schema')
        path = canonical(row['path'])
        require(path.startswith(root + '/docs/verification/evidence/') and
                path == root + '/' + row['restore_git_path'] and
                path not in names and (row['dev'], row['ino']) not in inodes and
                row['nlink'] == 1 and row['mode'] in (0o644, 0o755), 'target-path-set')
        require(not any(inside(path, canonical(p)) or inside(p, path)
                        for p in plan['protected_paths']), 'target-protected')
        names.add(path)
        inodes.add((row['dev'], row['ino']))
        with opened(path) as fd:
            verify_fd(fd, row)
        committed_file(binding['commit'], row['restore_git_path'], row)
    evidence_shape(plan)
    validate_protected(plan)
    return plan


def run(argv):
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    return {'argv': argv, 'returncode': p.returncode,
            'stdout': p.stdout.decode('utf-8', 'strict'),
            'stderr': p.stderr.decode('utf-8', 'strict')}


def unescape_mount(s):
    return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m.group(1), 8)), s)


def pinned_references(*pairs):
    refs = []
    for fd, path in pairs:
        s = os.fstat(fd)
        require(stat.S_ISDIR(s.st_mode) and
                fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY,
                'self-reference-type-access')
        refs.append({'pid': os.getpid(), 'fd': fd, 'dev': s.st_dev, 'ino': s.st_ino,
                     'access': 'r', 'path': path})
    return refs


def check_lsof(lsof, owned, root, scratch):
    """Validate a complete filesystem census, including paths outside candidate.

    ``+D`` is deliberately not used: lsof can return rc=1 for an otherwise
    successful recursive directory walk (notably on FUSE).  A mount-scoped
    census must be rc=0 and contain complete NUL records.  Every name is
    resolved without following symlinks and is bound to the emitted dev/ino.
    """
    require(lsof['returncode'] == 0 and not lsof['stderr'] and lsof['stdout'],
            'open-references-or-incomplete-census')
    # lsof 4.93.2's ``-F0pfaDint`` format is not merely NUL separated.  A
    # process set is ``pPID\\0\\n`` followed by one or more complete file
    # sets, each ``fFD\\0aACCESS\\0tTYPE\\0DDEV\\0iINO\\0nPATH\\0\\n``.
    # Do not normalize the newlines: doing so used to accept orphan PIDs,
    # trailing garbage and records spliced into a different process set.
    data = lsof['stdout']
    pos, records, process_ids = 0, [], set()

    def field(tag):
        nonlocal pos
        require(pos < len(data) and data[pos] == tag, 'lsof-fields')
        end = data.find('\0', pos + 1)
        require(end > pos + 1, 'lsof-fields')
        value = data[pos + 1:end]
        require('\n' not in value and '\r' not in value, 'lsof-fields')
        pos = end + 1
        return value

    while pos < len(data):
        pid_text = field('p')
        require(pid_text.isdigit() and int(pid_text) > 0, 'lsof-pid')
        pid = int(pid_text)
        require(pid not in process_ids and pos < len(data) and data[pos] == '\n',
                'lsof-fields')
        process_ids.add(pid)
        pos += 1
        file_count = 0
        while pos < len(data) and data[pos] == 'f':
            fd_text = field('f')
            access = field('a')
            kind = field('t')
            device = field('D')
            inode = field('i')
            name = field('n')
            require(fd_text.isdigit() and access in {'r', 'w', 'u', '-'} and
                    kind in {'DIR', 'REG', 'CHR', 'BLK', 'FIFO', 'LINK', 'SOCK'} and
                    inode.isdigit() and re.fullmatch(r'(0x)?[0-9a-fA-F]+', device),
                    'lsof-fields')
            require(pos < len(data) and data[pos] == '\n', 'lsof-fields')
            pos += 1
            records.append((pid, {'f': fd_text, 'a': access, 't': kind,
                                  'D': device, 'i': inode, 'n': name}))
            file_count += 1
        require(file_count > 0, 'lsof-fields')
        # The only legal next byte begins a fresh process set.  In particular
        # this rejects extra blank lines and a final orphan separator.
        require(pos == len(data) or data[pos] == 'p', 'lsof-fields')
    root_stat = os.stat(root, follow_symlinks=False)
    candidate_ids = {(root_stat.st_dev, root_stat.st_ino)}
    # Bind every currently present candidate/quarantine object by identity so
    # an outside hard-link is not mistaken for an unrelated scratch record.
    pending = [root]
    while pending:
        current_path = pending.pop()
        try:
            entries = list(os.scandir(current_path))
        except OSError:
            raise Refusal('lsof-path')
        for entry in entries:
            try:
                entry_stat = entry.stat(follow_symlinks=False)
            except OSError:
                raise Refusal('lsof-path')
            candidate_ids.add((entry_stat.st_dev, entry_stat.st_ino))
            if stat.S_ISDIR(entry_stat.st_mode):
                pending.append(entry.path)
    candidate_ids.update((r['dev'], r['ino']) for r in owned if inside(r['path'], root))
    require(records, 'lsof-empty-records')
    expected_by_key = {}
    expected_tuples = set()
    for witness in owned:
        require(set(witness) == {'pid', 'fd', 'dev', 'ino', 'access', 'path'} and
                type(witness['pid']) is int and witness['pid'] > 0 and
                type(witness['fd']) is int and witness['fd'] >= 0 and
                witness['access'] == 'r' and canonical(witness['path']) == witness['path'],
                'self-reference-binding')
        try:
            witness_stat = os.stat(witness['path'], follow_symlinks=False)
        except OSError:
            raise Refusal('self-reference-binding')
        require(stat.S_ISDIR(witness_stat.st_mode) and
                (witness_stat.st_dev, witness_stat.st_ino) ==
                (witness['dev'], witness['ino']), 'self-reference-binding')
        witness_key = (witness['pid'], witness['fd'])
        bound = (witness['pid'], witness['fd'], witness['access'], 'DIR',
                 witness['dev'], witness['ino'], witness['path'])
        # ``owned`` is an additional pin held by the transaction.  Test and
        # collector code may report that very descriptor again in witnesses;
        # it is one declaration, not a second descriptor that can be omitted.
        if witness_key in expected_by_key:
            require(expected_by_key[witness_key] == bound, 'self-reference-binding')
            continue
        require(bound not in expected_tuples, 'self-reference-binding')
        expected_by_key[witness_key] = bound
        expected_tuples.add(bound)
    seen = set()
    seen_owned = set()
    for pid, row in records:
        key = (pid, int(row['f']))
        require(key not in seen, 'lsof-duplicate')
        seen.add(key)
        require(row['n'].startswith('/') and canonical(row['n']) == row['n'],
                'lsof-path')
        try:
            target = Path(row['n'])
            with directory(str(target.parent)) as parent:
                st = os.stat(target.name, dir_fd=parent, follow_symlinks=False)
        except (OSError, ValueError):
            raise Refusal('lsof-path')
        require(not stat.S_ISLNK(st.st_mode), 'lsof-path-alias')
        require((st.st_dev, st.st_ino) == (int(row['D'], 16), int(row['i'])),
                'lsof-device-inode')
        kinds = ((stat.S_ISDIR(st.st_mode), 'DIR'), (stat.S_ISREG(st.st_mode), 'REG'),
                 (stat.S_ISCHR(st.st_mode), 'CHR'), (stat.S_ISBLK(st.st_mode), 'BLK'),
                 (stat.S_ISFIFO(st.st_mode), 'FIFO'), (stat.S_ISLNK(st.st_mode), 'LINK'),
                 (stat.S_ISSOCK(st.st_mode), 'SOCK'))
        require(any(ok and row['t'] == kind for ok, kind in kinds), 'lsof-fields')
        in_candidate = inside(row['n'], root)
        observed = (pid, int(row['f']), row['a'], row['t'], st.st_dev, st.st_ino, row['n'])
        if not in_candidate:
            require((st.st_dev, st.st_ino) not in candidate_ids, 'lsof-path-alias')
        if in_candidate:
            require(observed in expected_tuples, 'open-references-or-incomplete-census')
        if key in expected_by_key:
            require(observed == expected_by_key[key], 'self-reference-drift')
            seen_owned.add(observed)
        elif observed in expected_tuples:
            # A matching pathname with a substituted descriptor or PID must
            # not satisfy a different declared witness.
            raise Refusal('self-reference-drift')
        # The candidate is normally below the scratch mount; membership in
        # the mount is therefore not itself an alias.  Identity checks above
        # are what reject an outside hard-link/symlink alias.
    require(seen_owned == expected_tuples, 'open-references-or-incomplete-census')


def mount_set(mounts):
    result = []
    for row in mounts:
        require(isinstance(row['RW'], bool), 'container-mount-rw')
        result.append(json.dumps(row, sort_keys=True))
    require(len(set(result)) == len(result), 'container-mount-duplicate')
    return sorted(result)


def verify_container(obj, expected):
    s, h = obj['State'], obj['HostConfig']
    require(obj['Name'] == expected['Name'] and
            mount_set(obj['Mounts']) == mount_set(expected['Mounts']) and
            obj['Config']['Labels']['mckernel.owner'] == expected['owner_nonce'] and
            type(obj['RestartCount']) is int and obj['RestartCount'] == expected['RestartCount'] == 0 and
            json.dumps(s, sort_keys=True) == json.dumps(expected['State'], sort_keys=True) and
            s['Status'] == 'exited' and type(s['Pid']) is int and s['Pid'] == 0 and
            type(s['ExitCode']) is int and s['ExitCode'] == expected['State']['ExitCode'] and
            all(s[k] is False for k in ('Running', 'Paused', 'Restarting', 'Dead', 'OOMKilled')) and
            h['RestartPolicy'] == {'Name': 'no', 'MaximumRetryCount': 0} and
            h['AutoRemove'] is False, 'container-terminal-binding')


def validate_container_proofs():
    for cid, expected in CONTAINER_BINDINGS.items():
        proof = expected['proof']
        obj, _ = read_json(proof['path'], proof)
        if expected['proof_kind'] == 'image_owner_receipt':
            require(obj['container_id'] == cid and
                    '/' + obj['container_name'].lstrip('/') == expected['Name'] and
                    obj['owner_nonce'] == expected['owner_nonce'], 'container-owner-proof')
            obj = obj['terminal_container_info']
        else:
            require(expected['proof_kind'] == 'docker_inspect', 'container-proof-kind')
        require(obj['Id'] == cid, 'container-proof-id')
        verify_container(obj, expected)


def check_census(census, root, owned=()):
    scratch = canonical(census.get('scratch_mount', SCRATCH))
    require(scratch == canonical(SCRATCH), 'scratch-mount')
    witnesses = census.get('witnesses', [])
    require(any(w.get('path') == scratch for w in witnesses) and
            any(w.get('path') == root for w in tuple(owned) + tuple(witnesses)),
            'scratch-witness-missing')
    require(all(set(w) == {'pid', 'fd', 'dev', 'ino', 'access', 'path'} and
                type(w['pid']) is int and w['pid'] > 0 and type(w['fd']) is int and w['fd'] >= 0 and
                w['access'] == 'r' and canonical(w['path']) == w['path']
                for w in witnesses), 'scratch-witness-missing')
    for witness in witnesses:
        path = canonical(witness['path'])
        try:
            s = os.stat(path, follow_symlinks=False)
        except OSError:
            raise Refusal('scratch-witness-missing')
        require(stat.S_ISDIR(s.st_mode) and (s.st_dev, s.st_ino) ==
                (witness['dev'], witness['ino']), 'scratch-witness-missing')
    check_lsof(census['lsof'], tuple(owned) + tuple(witnesses), root, scratch)
    validate_container_proofs()
    mounts = []
    for line in census['mountinfo'].splitlines():
        left, right = line.split(' - ', 1)
        fields = left.split()
        require(len(fields) >= 6 and len(right.split()) >= 3, 'mountinfo-schema')
        mounts.append((fields[2], unescape_mount(fields[3]),
                       unescape_mount(fields[4]), right.split()[0]))
    containing = [m for m in mounts if inside(root, m[2])]
    require(containing, 'mount-missing')
    main = max(containing, key=lambda m: len(m[2]))
    require(main[1] == '/' and main[3] == 'ext4', 'mount-unknown-root')
    with directory(root) as fd:
        device = os.fstat(fd).st_dev
    require(main[0] == str(os.major(device)) + ':' + str(os.minor(device)), 'mount-device')
    with directory(scratch) as fd:
        scratch_device = os.fstat(fd).st_dev
    scratch_mounts = [m for m in mounts if m[2] == scratch]
    require(len(scratch_mounts) == 1 and
            scratch_mounts[0][0] == str(os.major(scratch_device)) + ':' +
            str(os.minor(scratch_device)), 'scratch-mount')
    require(not any(inside(m[2], root) for m in mounts), 'mount-descendant')
    require(not any(m != main and m[0] == main[0] for m in mounts), 'mount-alias')
    require(census['findmnt']['returncode'] == 0 and not census['findmnt']['stderr'],
            'findmnt-failed')
    ids = census['ids']
    require(len(ids) == len(set(ids)) and set(ids) == set(census['inspect']) and
            ids == census['ids_after'], 'container-set-changed')
    retained = set()
    intersections = set()
    for cid in ids:
        obj = census['inspect'][cid]
        require(obj['Id'] == cid and re.fullmatch('[a-f0-9]{64}', cid), 'container-id')
        require(isinstance(obj['Mounts'], list), 'container-mount-schema')
        hits = False
        for mount in obj['Mounts']:
            source = mount['Source']
            if not source and mount['Type'] == 'tmpfs':
                continue
            canonical(source)
            require(os.path.realpath(source) == source, 'container-unknown-alias')
            hits |= inside(source, root) or inside(root, source)
        if cid in CONTAINER_BINDINGS:
            retained.add(cid)
            require(hits, 'retained-container-binding')
            verify_container(obj, CONTAINER_BINDINGS[cid])
        if hits:
            intersections.add(cid)
            require(cid in CONTAINER_BINDINGS, 'container-intersection')
    require(retained == set(CONTAINER_BINDINGS), 'retained-container-absent')
    require(intersections == set(CONTAINER_BINDINGS), 'container-intersection-set')


def collect_census(root):
    def ids():
        result = run(['sudo', '-A', 'docker', 'ps', '-aq', '--no-trunc'])
        require(result['returncode'] == 0 and not result['stderr'], 'docker-ps-failed')
        rows = result['stdout'].splitlines()
        require(all(re.fullmatch('[a-f0-9]{64}', r) for r in rows), 'docker-ps-id')
        return sorted(rows), result
    before, ps_before = ids()
    mount_probe = run(['findmnt', '-T', SCRATCH, '-o', 'TARGET', '-n'])
    require(mount_probe['returncode'] == 0 and not mount_probe['stderr'], 'scratch-mount')
    scratch = canonical(mount_probe['stdout'].strip())
    with directory(scratch) as scratch_fd, directory(root) as root_fd:
        witnesses = pinned_references((scratch_fd, scratch), (root_fd, root))
        lsof = run(['sudo', '-A', 'lsof', '-nP', '-w', '-F0pfaDint', '+f', '--', scratch])
    inspections = {}
    commands = []
    for cid in before:
        result = run(['sudo', '-A', 'docker', 'inspect', cid])
        require(result['returncode'] == 0 and not result['stderr'], 'docker-inspect-failed')
        obj = json.loads(result['stdout'])
        require(isinstance(obj, list) and len(obj) == 1, 'docker-inspect-schema')
        # Retain full Mounts/State/RestartPolicy, excluding unrelated environment.
        obj = obj[0]
        inspections[cid] = {k: obj[k] for k in ('Id', 'Name', 'Mounts', 'State', 'RestartCount')}
        inspections[cid]['Config'] = {'Labels': {
            'mckernel.owner': (obj.get('Config', {}).get('Labels') or {}).get('mckernel.owner')}}
        inspections[cid]['HostConfig'] = {k: obj['HostConfig'][k]
                                        for k in ('RestartPolicy', 'AutoRemove')}
        commands.append(result['argv'])
    after, ps_after = ids()
    census = {'time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'scratch_mount': scratch, 'witnesses': witnesses, 'lsof': lsof,
              'findmnt': run(['findmnt', '-T', root, '-o', 'SOURCE,FSTYPE,MAJ:MIN,TARGET']),
              'mountinfo': Path('/proc/self/mountinfo').read_text(),
              'ids': before, 'ids_after': after, 'inspect': inspections,
              'ps_before': ps_before, 'ps_after': ps_after, 'inspect_commands': commands}
    return census


def validate_release(path, release_commit, outputs, command, binding=None):
    binding = BINDING if binding is None else binding
    require(path and release_commit and re.fullmatch('[a-f0-9]{40}', release_commit),
            'release-required')
    path = canonical(path)
    require(inside(path, str(REPO) + '/docs/verification/') and path.endswith('.json'),
            'release-path')
    release, raw = read_json(path)
    relpath = str(Path(path).relative_to(REPO))
    git(REPO, 'merge-base', '--is-ancestor', release_commit, REMOTE_REF)
    require(git(REPO, 'show', release_commit + ':' + relpath) == raw, 'release-not-committed')
    require(set(release) == {'schema', 'status', 'finalization', 'source_commit',
                            'tool_sha256', 'tool_blob', 'plan', 'command', 'outputs',
                            'absent_leases', 'dispatcher_exclusive', 'retained_containers'},
            'release-schema')
    source = release['source_commit']
    require(re.fullmatch('[a-f0-9]{40}', source) and source != release_commit,
            'release-source')
    git(REPO, 'merge-base', '--is-ancestor', source, release_commit)
    require(release['schema'] == 'mckernel.candidate12-cleanup-release.v1' and
            release['status'] == release['finalization'] == 'PASS' and
            release['plan'] == binding and release['outputs'] == outputs and
            release['command'] == command and release['dispatcher_exclusive'] is True,
            'release-binding')
    require(release['absent_leases'] == LEASES, 'release-leases')
    require(release['retained_containers'] == CONTAINER_BINDINGS, 'release-containers')
    validate_container_proofs()
    for lease in release['absent_leases']:
        require(inside(canonical(lease), SCRATCH) and not os.path.lexists(lease), 'active-lease')
    with opened(str(REPO / TOOL_PATH)) as fd:
        actual = hash_fd(fd)
    require(actual == release['tool_sha256'] and
            sha(git(REPO, 'show', source + ':' + TOOL_PATH)) == actual and
            git(REPO, 'rev-parse', source + ':' + TOOL_PATH).decode().strip() ==
            release['tool_blob'], 'release-tool')
    require(git(REPO, 'show', release_commit + ':' + TOOL_PATH) ==
            git(REPO, 'show', source + ':' + TOOL_PATH), 'release-tool-changed')
    return release


def validate_recovery_plan(path, binding=None):
    """Authenticate the plan without dereferencing its intentionally absent files."""
    binding = BINDING if binding is None else binding
    require(str(path) == binding['path'], 'plan-path')
    plan, _ = read_json(path, binding)
    require(set(plan) == {'candidate_commit', 'candidate_identity', 'candidate_root',
                         'nested_delta_preserved', 'preserved', 'protected_paths',
                         'safety_census', 'schema', 'status', 'targets'}, 'plan-schema')
    require(plan['schema'] == 'mckernel.exact-git-source-audit.v1' and
            plan['status'] == 'AUDIT_PASS' and plan['preserved'] == [] and
            plan['nested_delta_preserved'] is True, 'plan-status')
    root = canonical(plan['candidate_root'])
    require(root == binding['root'] and plan['candidate_commit'] == binding['commit'] and
            plan['candidate_identity'] == binding['identity'], 'plan-binding')
    with directory(root) as fd:
        s = os.fstat(fd)
        require(str(s.st_dev) + ':' + str(s.st_ino) == binding['identity'], 'root-identity')
    require(git(root, 'rev-parse', 'HEAD').decode().strip() == binding['commit'], 'root-head')
    rows = plan['targets']
    require(len(rows) == binding['count'] and sum(r['size'] for r in rows) == binding['bytes'] and
            sum(r['allocated_bytes'] for r in rows) == binding['allocated'], 'target-totals')
    names, inodes = set(), set()
    for row in rows:
        require(set(row) == {'allocated_bytes', 'blob', 'dev', 'ino', 'mode', 'mtime_ns',
                             'nlink', 'path', 'restore_git_path', 'sha256', 'size'}, 'row-schema')
        target = canonical(row['path'])
        require(target.startswith(root + '/docs/verification/evidence/') and
                target == root + '/' + row['restore_git_path'] and target not in names and
                (row['dev'], row['ino']) not in inodes and row['nlink'] == 1 and
                row['mode'] in (0o644, 0o755), 'target-path-set')
        require(not any(inside(target, canonical(p)) or inside(p, target)
                        for p in plan['protected_paths']), 'target-protected')
        names.add(target); inodes.add((row['dev'], row['ino']))
        committed_file(binding['commit'], row['restore_git_path'], row)
    validate_protected(plan)
    return plan


def _attempt_file(name):
    row = ATTEMPT2[name]
    value, raw = read_json(row['path'], row)
    require(sha(raw) == row['sha256'], 'attempt2-' + name + '-content')
    return value


def validate_attempt2(plan):
    """Bind the immutable failed staging transaction, including its exact journal."""
    receipt = _attempt_file('receipt')
    status = _attempt_file('status')
    # The journal is JSONL rather than one JSON object, but has the same
    # private-regular-file and identity requirements as the two JSON outputs.
    with opened(ATTEMPT2['journal']['path']) as fd:
        verify_fd(fd, ATTEMPT2['journal'])
        os.lseek(fd, 0, os.SEEK_SET)
        raw = b''.join(iter(lambda: os.read(fd, 1024 * 1024), b''))
    events = [json.loads(line, object_pairs_hook=lambda values: _unique_pairs(values))
              for line in raw.splitlines()]
    require(events and all(isinstance(event, dict) for event in events), 'attempt2-journal-json')
    kinds = [event.get('event') for event in events]
    require(not ({'delete-intent', 'deleted', 'irreversible-delete-admitted'} & set(kinds)),
            'attempt2-journal-deletion')
    # The only legal failed path is complete staging followed by rejected
    # admission.  Index/order checks make a truncated or spliced journal fail.
    require(kinds[:5] == ['admitted', 'census', 'transaction-entered',
                          'quarantine-intent', 'quarantine-created'], 'attempt2-journal-prefix')
    cursor = 5
    for index, row in enumerate(plan['targets']):
        require(cursor + 1 < len(events) and events[cursor].get('event') == 'stage-intent' and
                events[cursor].get('index') == index and events[cursor].get('restore') == row and
                events[cursor + 1] == {'event': 'staged', 'index': index}, 'attempt2-journal-stage')
        cursor += 2
    require(kinds[cursor:] == ['staging-complete', 'post-staging-census', 'failure'],
            'attempt2-journal-suffix')
    failure = events[-1]
    require(failure.get('status') == 'FAIL' and failure.get('phase') == 'staged-admission' and
            failure.get('error') == 'open-references-or-incomplete-census' and
            failure.get('attempted') is None and failure.get('states') == ['staged'] * len(plan['targets']),
            'attempt2-journal-failure')
    require(receipt.get('status') == 'FAIL' and receipt.get('phase') == 'staged-admission' and
            receipt.get('error') == 'open-references-or-incomplete-census' and
            receipt.get('interrupted') is False and receipt.get('attempted') is None and
            receipt.get('states') == ['staged'] * len(plan['targets']) and
            receipt.get('restoration') == plan['targets'] and
            receipt.get('quarantine') == ATTEMPT2['quarantine']['path'], 'attempt2-receipt')
    require(status == {'status': 'FAIL', 'receipt': ATTEMPT2['receipt']['path'],
                       'journal': ATTEMPT2['journal']['path']}, 'attempt2-status')
    return receipt


def _unique_pairs(values):
    result = {}
    for key, value in values:
        require(key not in result, 'json-duplicate-key')
        result[key] = value
    return result


def validate_recovery_release(path, release_commit, outputs=None, command=None, binding=None):
    binding = BINDING if binding is None else binding
    require(path and release_commit and re.fullmatch('[a-f0-9]{40}', release_commit), 'release-required')
    path = canonical(path)
    require(inside(path, str(REPO) + '/docs/verification/') and path.endswith('.json'), 'release-path')
    release, raw = read_json(path)
    relpath = str(Path(path).relative_to(REPO))
    git(REPO, 'merge-base', '--is-ancestor', release_commit, REMOTE_REF)
    require(git(REPO, 'show', release_commit + ':' + relpath) == raw, 'release-not-committed')
    require(set(release) == {'schema', 'status', 'finalization', 'source_commit', 'tool_sha256',
                             'tool_blob', 'test_path', 'test_sha256', 'test_blob', 'plan', 'staged_manifest', 'command', 'outputs', 'quarantine',
                             'absent_leases', 'dispatcher_exclusive', 'retained_containers'}, 'release-schema')
    source = release['source_commit']
    require(re.fullmatch('[a-f0-9]{40}', source) and source != release_commit, 'release-source')
    git(REPO, 'merge-base', '--is-ancestor', source, release_commit)
    require(release['schema'] == RECOVERY_SCHEMA and release['status'] == release['finalization'] == 'PASS' and
            release['plan'] == binding and
            (command is None or release['command'] == command) and
            (outputs is None or release['outputs'] == outputs) and
            release['quarantine'] == ATTEMPT2['quarantine']['path'] and
            release['dispatcher_exclusive'] is True, 'release-binding')
    require(release['absent_leases'] == LEASES and release['retained_containers'] == CONTAINER_BINDINGS,
            'release-inventory')
    require(isinstance(release['command'], list) and release['command'] and
            '--recover-staged' in release['command'] and
            set(release['outputs']) == {'journal', 'receipt', 'status', 'quarantine'} and
            all(isinstance(value, str) and canonical(value) == value
                for value in release['outputs'].values()), 'release-command-outputs')
    validate_container_proofs()
    for lease in LEASES:
        require(inside(canonical(lease), SCRATCH) and not os.path.lexists(lease), 'active-lease')
    with opened(str(REPO / TOOL_PATH)) as fd:
        actual = hash_fd(fd)
    require(actual == release['tool_sha256'] and sha(git(REPO, 'show', source + ':' + TOOL_PATH)) == actual and
            git(REPO, 'rev-parse', source + ':' + TOOL_PATH).decode().strip() == release['tool_blob'],
            'release-tool')
    require(git(REPO, 'show', release_commit + ':' + TOOL_PATH) ==
            git(REPO, 'show', source + ':' + TOOL_PATH), 'release-tool-changed')
    test_path = release['test_path']
    require(isinstance(test_path, str) and test_path.startswith('scripts/tests/') and
            not test_path.startswith('/') and re.fullmatch('[a-f0-9]{64}', release['test_sha256']) and
            re.fullmatch('[a-f0-9]{40}', release['test_blob']), 'release-test-binding')
    with opened(str(REPO / test_path)) as fd:
        test_actual = hash_fd(fd)
    require(test_actual == release['test_sha256'] and
            sha(git(REPO, 'show', source + ':' + test_path)) == test_actual and
            git(REPO, 'rev-parse', source + ':' + test_path).decode().strip() == release['test_blob'] and
            git(REPO, 'show', release_commit + ':' + test_path) ==
            git(REPO, 'show', source + ':' + test_path), 'release-test')
    manifest_binding = release['staged_manifest']
    require(set(manifest_binding) == {'path', 'sha256', 'size'}, 'recovery-manifest-binding')
    manifest_path = manifest_binding['path']
    require(isinstance(manifest_path, str) and manifest_path.startswith('docs/verification/') and
            not manifest_path.startswith('/') and re.fullmatch('[a-f0-9]{64}', manifest_binding['sha256']) and
            type(manifest_binding['size']) is int and manifest_binding['size'] > 0,
            'recovery-manifest-binding')
    manifest, manifest_raw = read_json(str(REPO / manifest_path))
    require(len(manifest_raw) == manifest_binding['size'] and sha(manifest_raw) == manifest_binding['sha256'] and
            git(REPO, 'show', source + ':' + manifest_path) == manifest_raw and
            git(REPO, 'show', release_commit + ':' + manifest_path) == manifest_raw,
            'recovery-manifest-content')
    require(set(manifest) == {'schema', 'status', 'plan', 'attempt2', 'quarantine', 'targets'} and
            manifest['schema'] == 'mckernel.candidate12-cleanup-staged-manifest.v1' and
            manifest['status'] == 'PASS' and manifest['plan'] == binding and
            manifest['attempt2'] == ATTEMPT2 and manifest['quarantine'] == ATTEMPT2['quarantine']['path'] and
            isinstance(manifest['targets'], list), 'recovery-manifest')
    release['_staged_manifest'] = manifest
    return release


def write_all(fd, data):
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        require(written > 0, 'short-write-zero')
        offset += written


class Journal:
    def __init__(self, path):
        self.path = path
        p = Path(canonical(path))
        with directory(str(p.parent)) as parent:
            self.fd = os.open(p.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                              os.O_APPEND | NOFOLLOW, 0o600, dir_fd=parent)
            try:
                os.fsync(self.fd)
                os.fsync(parent)
            except BaseException:
                os.close(self.fd)
                raise

    def append(self, record):
        write_all(self.fd, (json.dumps(record, sort_keys=True) + '\n').encode())
        os.fsync(self.fd)

    def close(self):
        os.close(self.fd)


class FDJournal:
    """A pre-created evidence writer: its parent and inode remain pinned."""
    def __init__(self, fd):
        self.fd = fd

    def append(self, record):
        write_all(self.fd, (json.dumps(record, sort_keys=True) + '\n').encode())
        os.fsync(self.fd)

    def close(self):
        pass


def publish(path, record):
    journal = Journal(path)
    try:
        journal.append(record)
    finally:
        journal.close()


def rename_noreplace(srcfd, src, dstfd, dst):
    libc = ctypes.CDLL(None, use_errno=True)
    fn = libc.renameat2
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
                   ctypes.c_uint]
    fn.restype = ctypes.c_int
    if fn(srcfd, os.fsencode(src), dstfd, os.fsencode(dst), 1) != 0:
        raise OSError(ctypes.get_errno(), 'rename-noreplace-failed')


def verify_name(parent, name, row):
    fd = os.open(name, os.O_RDONLY | NOFOLLOW, dir_fd=parent)
    try:
        verify_fd(fd, row)
        a, b = os.fstat(fd), os.stat(name, dir_fd=parent, follow_symlinks=False)
        require(metadata(a) == metadata(b), 'pathname-replacement')
    finally:
        os.close(fd)


def verify_quarantine(rootfd, qname, qfd):
    actual = os.stat(qname, dir_fd=rootfd, follow_symlinks=False)
    held = os.fstat(qfd)
    require(stat.S_ISDIR(actual.st_mode) and
            (actual.st_dev, actual.st_ino, stat.S_IMODE(actual.st_mode)) ==
            (held.st_dev, held.st_ino, 0o700), 'quarantine-replaced')


def output_paths(outputs, plan, output_root=None):
    output_root = SCRATCH if output_root is None else output_root
    require(set(outputs) == {'journal', 'receipt', 'status', 'quarantine'} and
            len(set(outputs.values())) == 4, 'output-schema')
    root = plan['candidate_root']
    q = Path(canonical(outputs['quarantine']))
    require(str(q.parent) == root and q.name.startswith('.planbound-cleanup-'),
            'quarantine-location')
    for key, path in outputs.items():
        canonical(path)
        require(not os.path.lexists(path), 'output-collision')
        if key != 'quarantine':
            require(inside(path, output_root) and path != output_root and not inside(path, root) and
                    not any(inside(path, p) or inside(p, path)
                            for p in plan['protected_paths']), 'output-protected')
        with directory(str(Path(path).parent)):
            pass


def recovery_output_paths(outputs, plan, output_root=None):
    """Recovery has exactly three fresh evidence files and one old quarantine."""
    output_root = SCRATCH if output_root is None else output_root
    require(set(outputs) == {'journal', 'receipt', 'status', 'quarantine'} and
            len(set(outputs.values())) == 4, 'recovery-output-schema')
    require(outputs['quarantine'] == ATTEMPT2['quarantine']['path'], 'recovery-quarantine-path')
    for key in ('journal', 'receipt', 'status'):
        path = canonical(outputs[key])
        require(not os.path.lexists(path) and inside(path, output_root) and path != output_root and
                not inside(path, plan['candidate_root']) and
                not any(inside(path, p) or inside(p, path) for p in plan['protected_paths']),
                'recovery-output-path')
        with directory(str(Path(path).parent)):
            pass


def precreate_recovery_outputs(outputs):
    """Create and retain all result files before the first recovery rename."""
    result = {}
    try:
        for key in ('journal', 'receipt', 'status'):
            p = Path(outputs[key])
            with directory(str(p.parent)) as parent:
                fd = os.open(p.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | NOFOLLOW,
                             0o600, dir_fd=parent)
                try:
                    os.fsync(fd)
                    os.fsync(parent)
                    current = os.stat(p.name, dir_fd=parent, follow_symlinks=False)
                    require(metadata(current) == metadata(os.fstat(fd)), 'recovery-output-replaced')
                    # Duplicate the directory descriptor so it remains held beyond
                    # the context manager and no later compound parent resolution
                    # can redirect publication.
                    result[key] = (os.dup(parent), fd, metadata(os.fstat(parent)))
                except BaseException:
                    os.close(fd)
                    raise
        # Multiple fresh files commonly share one parent; record its identity
        # after the complete creation set, not after the first entry.
        for key, (parent, fd, _) in tuple(result.items()):
            result[key] = (parent, fd, metadata(os.fstat(parent)))
        return result
    except BaseException:
        for parent, fd, _ in result.values():
            os.close(fd); os.close(parent)
        raise


def close_recovery_outputs(opened_outputs):
    for parent, fd, _ in opened_outputs.values():
        try:
            os.close(fd)
        finally:
            os.close(parent)


def output_parent_held(entry):
    parent, _, expected = entry
    require(metadata(os.fstat(parent)) == expected, 'recovery-output-parent-replaced')


def write_precreated(entry, record, replace=False):
    parent, fd, _ = entry
    output_parent_held(entry)
    if replace:
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
    else:
        require(os.lseek(fd, 0, os.SEEK_END) == 0, 'recovery-output-not-empty')
    write_all(fd, (json.dumps(record, sort_keys=True) + '\n').encode())
    os.fsync(fd)
    os.fsync(parent)


@contextlib.contextmanager
def terminal_latch():
    global _terminal_latched
    _terminal_latched = False
    def latch(signum, frame):
        del signum, frame
        global _terminal_latched
        _terminal_latched = True
    previous = {sig: signal.signal(sig, latch) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        yield
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)


def require_unlatched():
    require(not _terminal_latched, 'terminal-signal-latched')


def demote_recovery_result(result, code):
    result = dict(result)
    result['status'] = 'FAIL'
    result['publication_error'] = code
    result['interrupted'] = result.get('interrupted', False) or _terminal_latched
    return result


def publish_recovery_result(open_outputs, result, outputs, journal):
    """Never return/pass a PASS record when either publication edge failed."""
    try:
        require_unlatched()
        os.fsync(journal.fd)
        require_unlatched()
    except BaseException as error:
        result = demote_recovery_result(result, 'journal-finalize-' + type(error).__name__)
    try:
        require_unlatched()
        write_precreated(open_outputs['receipt'], result)
        require_unlatched()
    except BaseException as error:
        result = demote_recovery_result(result, 'receipt-' + type(error).__name__)
        try: write_precreated(open_outputs['receipt'], result, replace=True)
        except BaseException: result['receipt_failure'] = True
    status_record = {'status': result['status'], 'receipt': outputs['receipt'],
                     'journal': outputs['journal']}
    try:
        require_unlatched()
        write_precreated(open_outputs['status'], status_record)
        require_unlatched()
    except BaseException as error:
        result = demote_recovery_result(result, 'status-' + type(error).__name__)
        # A status failure must not leave the preceding PASS receipt as an
        # apparent acceptance.  Both rewrites are best-effort but individually
        # fsynced and are attempted even if the other one faults.
        for key, record in (('receipt', result),
                            ('status', {'status': 'FAIL', 'receipt': outputs['receipt'],
                                        'journal': outputs['journal']})):
            try: write_precreated(open_outputs[key], record, replace=True)
            except BaseException: result[key + '_failure'] = True
    if _terminal_latched and result['status'] == 'PASS':
        result = demote_recovery_result(result, 'terminal-latch')
    return result


def location(parent, name, row):
    try:
        verify_name(parent, name, row)
        return 'expected'
    except FileNotFoundError:
        return 'missing'
    except BaseException:
        return 'wrong-or-unreadable'


def reconcile_rename(row, qfd, index):
    target = Path(row['path'])
    try:
        with directory(str(target.parent)) as parent:
            source = location(parent, target.name, row)
    except BaseException:
        source = 'wrong-or-unreadable'
    quarantine = location(qfd, str(index), row)
    observations = {'source': source, 'quarantine': quarantine}
    if observations == {'source': 'expected', 'quarantine': 'missing'}:
        return 'original', observations
    if observations == {'source': 'missing', 'quarantine': 'expected'}:
        return 'staged', observations
    return 'uncertain', observations


def transaction_progress(plan):
    # This owner survives every transaction stack frame and descriptor cleanup.
    # Until the transaction initializes its state, original locations are unknown.
    return {'phase': 'transaction-entered', 'attempted': None, 'result': None,
            'states': ['transaction-uncertain'] * len(plan['targets'])}


def escaped_transaction(plan, outputs, journal, progress, error):
    previous = progress['result']
    result = dict(previous) if previous is not None else {
        'phase': progress['phase'], 'attempted': progress['attempted'],
        'restore_commit': plan['candidate_commit'], 'restoration': plan['targets'],
        'quarantine': outputs['quarantine'],
    }
    result.update(status='FAIL', states=list(progress['states']),
                  error=str(error) if isinstance(error, Refusal) else type(error).__name__,
                  interrupted=result.get('interrupted', False) or isinstance(error, KeyboardInterrupt),
                  escaped_after_transaction_entry=True)
    if previous is not None:
        result['prior_status'] = previous['status']
    # Publish the in-memory result first: failure even in the evidence writer
    # must not destroy the known per-file states seen by execute's outer owner.
    progress['result'] = result
    try:
        journal.append({'event': 'transaction-unwind-failure', **result})
    except BaseException:
        result['journal_failure'] = True
    return result


def transact(plan, outputs, journal, progress=None):
    progress = transaction_progress(plan) if progress is None else progress
    try:
        return _transact(plan, outputs, journal, progress)
    except BaseException as error:
        # Covers quarantine close, root-directory __exit__, and interrupted
        # failure handling/return, which lie outside _transact's rollback block.
        return escaped_transaction(plan, outputs, journal, progress, error)


def _transact(plan, outputs, journal, progress):
    """Called only after release, flock, full validation, and durable census."""
    root = plan['candidate_root']
    rows = plan['targets']
    states = progress['states'] = ['original'] * len(rows)
    attempted = progress['attempted'] = None
    phase = progress['phase'] = 'staging'
    qname = Path(outputs['quarantine']).name
    qfd = None
    destinations = None
    result = None
    with directory(root) as rfd:
        try:
            s = os.fstat(rfd)
            require(str(s.st_dev) + ':' + str(s.st_ino) == plan['candidate_identity'],
                    'transaction-root-identity')
            evidence_shape(plan)
            journal.append({'event': 'quarantine-intent', 'path': outputs['quarantine']})
            os.mkdir(qname, 0o700, dir_fd=rfd)
            os.fsync(rfd)
            qfd = os.open(qname, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=rfd)
            require(os.fstat(qfd).st_dev == os.fstat(rfd).st_dev, 'quarantine-device')
            journal.append({'event': 'quarantine-created', 'identity': metadata(os.fstat(qfd))})
            for i, row in enumerate(rows):
                attempted = progress['attempted'] = i
                verify_quarantine(rfd, qname, qfd)
                target = Path(row['path'])
                name = str(i)
                with directory(str(target.parent)) as parent:
                    verify_name(parent, target.name, row)
                    states[i] = 'stage-uncertain'
                    journal.append({'event': 'stage-intent', 'index': i,
                                    'state': states[i], 'restore': row})
                    rename_noreplace(parent, target.name, qfd, name)
                    states[i] = 'staged-unverified'
                    os.fsync(parent)
                    os.fsync(qfd)
                    verify_name(qfd, name, row)
                    states[i] = 'staged'
                    journal.append({'event': 'staged', 'index': i})
            # No irreversible deletion before the complete staged set is proved.
            evidence_shape(plan, staged=True)
            quarantine_shape(qfd, rows)
            validate_protected(plan)
            journal.append({'event': 'staging-complete', 'count': len(rows)})
            # A failed fresh admission keeps the complete staged set recoverable.
            phase = progress['phase'] = 'staged-admission'
            attempted = progress['attempted'] = None
            owned = pinned_references((rfd, root), (qfd, outputs['quarantine']))
            census = collect_census(root)
            journal.append({'event': 'post-staging-census', 'census': census,
                            'owned_references': owned})
            check_census(census, root, owned)
            for lease in LEASES:
                require(not os.path.lexists(lease), 'active-lease')
            validate_protected(plan)
            evidence_shape(plan, staged=True)
            verify_quarantine(rfd, qname, qfd)
            quarantine_shape(qfd, rows)
            journal.append({'event': 'irreversible-delete-admitted', 'count': len(rows)})
            phase = progress['phase'] = 'deleting'
            for i, row in enumerate(rows):
                attempted = progress['attempted'] = i
                verify_quarantine(rfd, qname, qfd)
                journal.append({'event': 'delete-intent', 'index': i, 'restore': row})
                verify_name(qfd, str(i), row)
                states[i] = 'unlink-uncertain'
                os.unlink(str(i), dir_fd=qfd)
                states[i] = 'deleted-not-durable'
                os.fsync(qfd)
                states[i] = 'deleted'
                journal.append({'event': 'deleted', 'index': i})
            census = collect_census(root)
            journal.append({'event': 'final-census', 'census': census,
                            'owned_references': owned})
            check_census(census, root, owned)
            attempted = progress['attempted'] = None
            result = {'status': 'PASS', 'phase': 'complete', 'attempted': attempted,
                      'states': states, 'restore_commit': plan['candidate_commit'],
                      'restoration': rows, 'quarantine': outputs['quarantine']}
            progress['result'] = result
            phase = progress['phase'] = 'complete'
            journal.append({'event': 'complete', 'count': len(rows)})
        except BaseException as error:
            code = str(error) if isinstance(error, Refusal) else type(error).__name__
            rollback = []
            interrupted = isinstance(error, KeyboardInterrupt)
            if phase == 'staging' and qfd is not None:
                uncertain = False
                for i, row in enumerate(rows):
                    if states[i] not in ('stage-uncertain', 'staged-unverified'):
                        continue
                    where, observations = reconcile_rename(row, qfd, i)
                    states[i] = 'stage-uncertain' if where == 'uncertain' else where
                    uncertain |= where == 'uncertain'
                    rollback.append({'index': i, 'status': states[i], 'locations': observations})
                    try:
                        journal.append({'event': 'stage-reconciled', 'index': i,
                                        'state': states[i], 'locations': observations})
                    except BaseException:
                        rollback.append({'index': i, 'error': 'reconciliation-journal-failure'})
                for i in reversed(range(len(rows))):
                    if uncertain or states[i] != 'staged':
                        continue
                    target = Path(rows[i]['path'])
                    try:
                        where, observations = reconcile_rename(rows[i], qfd, i)
                        require(where == 'staged', 'rollback-location-uncertain')
                        states[i] = 'restore-uncertain'
                        journal.append({'event': 'rollback-intent', 'index': i,
                                        'state': states[i]})
                        with directory(str(target.parent)) as parent:
                            rename_noreplace(qfd, str(i), parent, target.name)
                            states[i] = 'restored-not-durable'
                            os.fsync(parent)
                            os.fsync(qfd)
                            verify_name(parent, target.name, rows[i])
                            states[i] = 'restored'
                        rollback.append({'index': i, 'status': states[i]})
                        try:
                            journal.append({'event': 'restored', 'index': i})
                        except BaseException:
                            rollback.append({'index': i, 'error': 'restored-journal-failure'})
                    except BaseException as rollback_error:
                        interrupted |= isinstance(rollback_error, KeyboardInterrupt)
                        where, observations = reconcile_rename(rows[i], qfd, i)
                        states[i] = ('restored-not-durable' if where == 'original' else
                                     'staged' if where == 'staged' else 'restore-uncertain')
                        if where == 'original':
                            try:
                                with directory(str(target.parent)) as parent:
                                    os.fsync(parent)
                                    os.fsync(qfd)
                                    verify_name(parent, target.name, rows[i])
                                states[i] = 'restored'
                            except BaseException as durability_error:
                                interrupted |= isinstance(durability_error, KeyboardInterrupt)
                        reconciled = {'event': 'rollback-reconciled', 'index': i,
                                      'state': states[i], 'locations': observations,
                                      'error': type(rollback_error).__name__}
                        try:
                            journal.append(reconciled)
                        except BaseException:
                            rollback.append({'index': i, 'error': 'reconciliation-journal-failure'})
                        rollback.append({'index': i, 'status': states[i],
                                         'locations': observations,
                                         'error': type(rollback_error).__name__})
                        if where == 'uncertain':
                            break
            result = {'status': 'FAIL', 'phase': phase, 'attempted': attempted,
                      'error': code, 'interrupted': interrupted,
                      'states': states, 'rollback': rollback,
                      'restore_commit': plan['candidate_commit'], 'restoration': rows,
                      'quarantine': outputs['quarantine']}
            progress['result'] = result
            try:
                journal.append({'event': 'failure', **result})
            except BaseException:
                result['journal_failure'] = True
        finally:
            if qfd is not None:
                os.close(qfd)
    return result


def execute(plan_path, release_path, release_commit, outputs, command):
    # Release is checked before locking, census, or any output creation.
    release = validate_release(release_path, release_commit, outputs, command)
    with directory(str(Path(MUTEX).parent)) as mutex_parent:
        mutex = os.open(Path(MUTEX).name, os.O_RDWR | os.O_CREAT | NOFOLLOW,
                        0o600, dir_fd=mutex_parent)
        try:
            os.fsync(mutex)
            os.fsync(mutex_parent)
        except BaseException:
            os.close(mutex)
            raise
    try:
        s = os.fstat(mutex)
        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and
                stat.S_IMODE(s.st_mode) == 0o600 and s.st_uid == os.geteuid(), 'mutex-identity')
        fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with opened(MUTEX) as current:
            require(metadata(os.fstat(current)) == metadata(s), 'mutex-replaced')
        plan = validate_plan(plan_path)
        output_paths(outputs, plan)
        journal = Journal(outputs['journal'])
        try:
            journal.append({'event': 'admitted', 'plan': BINDING, 'outputs': outputs,
                            'command': command, 'release_commit': release_commit,
                            'mutex': {'path': MUTEX, **metadata(s)},
                            'absent_leases': release['absent_leases']})
            try:
                census = collect_census(plan['candidate_root'])
                journal.append({'event': 'census', 'census': census})
                check_census(census, plan['candidate_root'])
                for lease in release['absent_leases']:
                    require(not os.path.lexists(lease), 'active-lease')
            except BaseException as error:
                result = {'status': 'FAIL', 'phase': 'preflight', 'attempted': None,
                          'states': ['original'] * len(plan['targets']),
                          'error': str(error) if isinstance(error, Refusal) else type(error).__name__,
                          'interrupted': isinstance(error, KeyboardInterrupt),
                          'restore_commit': plan['candidate_commit'], 'restoration': plan['targets']}
                journal.append({'event': 'failure', **result})
            else:
                # The untouched-originals handler above is unreachable once we
                # enter the transaction. Keep the state owner across the call
                # in case an interruption escapes even its unwind handler.
                progress = transaction_progress(plan)
                try:
                    journal.append({'event': 'transaction-entered'})
                    result = transact(plan, outputs, journal, progress)
                except BaseException as error:
                    result = escaped_transaction(plan, outputs, journal, progress, error)
            # Publication failure leaves the already durable journal intact.
            publish(outputs['receipt'], result)
            publish(outputs['status'], {'status': result['status'], 'receipt': outputs['receipt'],
                                        'journal': outputs['journal']})
            return result
        finally:
            journal.close()
    finally:
        os.close(mutex)


def recovery_quarantine(rootfd, qfd):
    qname = Path(ATTEMPT2['quarantine']['path']).name
    verify_quarantine(rootfd, qname, qfd)
    held = os.fstat(qfd)
    expected = ATTEMPT2['quarantine']
    require((held.st_dev, held.st_ino, stat.S_IMODE(held.st_mode), held.st_nlink) ==
            (expected['dev'], expected['ino'], expected['mode'], expected['nlink']),
            'attempt2-quarantine-identity')


def recovery_destinations(rfd, plan):
    """Pin every destination directory below the authenticated root descriptor."""
    root = plan['candidate_root']
    result = {'': (os.dup(rfd), directory_identity(os.fstat(rfd)), None, None)}
    try:
        wanted = sorted({str(Path(row['restore_git_path']).parent) for row in plan['targets']},
                        key=lambda value: (len(Path(value).parts), value))
        for relative in wanted:
            require(relative != '.' and not relative.startswith('/') and '..' not in Path(relative).parts,
                    'recovery-destination-relative')
            current = ''
            for component in Path(relative).parts:
                child = component if not current else current + '/' + component
                if child in result:
                    current = child
                    continue
                parentfd, _, _, _ = result[current]
                fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=parentfd)
                try:
                    named = os.stat(component, dir_fd=parentfd, follow_symlinks=False)
                    require(directory_identity(named) == directory_identity(os.fstat(fd)),
                            'recovery-destination-component')
                    result[child] = (fd, directory_identity(os.fstat(fd)), current, component)
                except BaseException:
                    os.close(fd); raise
                current = child
        return result
    except BaseException:
        close_recovery_destinations(result)
        raise


def close_recovery_destinations(destinations):
    for fd, _, _, _ in destinations.values():
        try: os.close(fd)
        except OSError: pass


def directory_identity(s):
    return (s.st_dev, s.st_ino, stat.S_IMODE(s.st_mode), s.st_nlink)


def validate_recovery_destinations(rfd, plan, destinations):
    """Bind held descriptors to the currently reachable root namespace."""
    with directory(plan['candidate_root']) as live_root:
        require(directory_identity(os.fstat(live_root)) == directory_identity(os.fstat(rfd)),
                'recovery-root-replaced')
    require(directory_identity(os.fstat(rfd)) == destinations[''][1], 'recovery-root-held-drift')
    for relative, (fd, identity, parent_relative, name) in destinations.items():
        require(directory_identity(os.fstat(fd)) == identity, 'recovery-destination-held-drift')
        if parent_relative is not None:
            parentfd = destinations[parent_relative][0]
            live = os.stat(name, dir_fd=parentfd, follow_symlinks=False)
            require(directory_identity(live) == identity, 'recovery-destination-replaced')


def recovery_parent(destinations, row):
    relative = str(Path(row['restore_git_path']).parent)
    require(relative in destinations, 'recovery-destination-missing')
    return destinations[relative][0]


def recovery_evidence_shape(plan, destinations, staged=False):
    expected_files = {str(Path(row['restore_git_path']).relative_to('docs/verification/evidence'))
                      for row in plan['targets']}
    expected_dirs = {''}
    for name in expected_files:
        parent = str(Path(name).parent)
        while parent != '.':
            expected_dirs.add(parent); parent = str(Path(parent).parent)
    efd = destinations['docs/verification/evidence'][0]
    dirs, files = set(), set()
    def visit(fd, relative):
        dirs.add(relative)
        for name in os.listdir(fd):
            child = relative + '/' + name if relative else name
            s = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(s.st_mode):
                sub = os.open(name, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=fd)
                try:
                    require(metadata(os.fstat(sub)) == metadata(s), 'recovery-subtree-directory-race')
                    visit(sub, child)
                    require(metadata(os.stat(name, dir_fd=fd, follow_symlinks=False)) == metadata(s),
                            'recovery-subtree-directory-race')
                finally: os.close(sub)
            else:
                require(stat.S_ISREG(s.st_mode), 'recovery-subtree-special-or-symlink')
                files.add(child)
    visit(efd, '')
    require(dirs == expected_dirs and files == (set() if staged else expected_files), 'recovery-subtree-set')


def recovery_original_evidence(plan, destinations):
    """Final content-and-metadata proof using only held destination descriptors."""
    validate_recovery_destinations(destinations[''][0], plan, destinations)
    recovery_evidence_shape(plan, destinations)
    for row in plan['targets']:
        verify_name(recovery_parent(destinations, row), Path(row['path']).name, row)


def reconcile_recovery_rename(row, qfd, index, destinations):
    source = location(recovery_parent(destinations, row), Path(row['path']).name, row)
    quarantine = location(qfd, str(index), row)
    observations = {'source': source, 'quarantine': quarantine}
    if observations == {'source': 'expected', 'quarantine': 'missing'}:
        return 'original', observations
    if observations == {'source': 'missing', 'quarantine': 'expected'}:
        return 'staged', observations
    return 'uncertain', observations


def recovery_result(plan, outputs, states, status, phase, error=None, interrupted=False):
    result = {'status': status, 'phase': phase, 'states': list(states),
              'restore_commit': plan['candidate_commit'], 'restoration': plan['targets'],
              'quarantine': outputs['quarantine'], 'interrupted': interrupted}
    if error is not None:
        result['error'] = error
    return result


def recover_staged(plan, outputs, journal):
    """Reverse only the authenticated attempt-2 staging, fail closed on any drift."""
    rows = plan['targets']
    states = ['staged'] * len(rows)
    qfd = None
    destinations = None
    phase = 'recovery-admission'
    root = plan['candidate_root']
    try:
        with directory(root) as rfd:
            qname = Path(outputs['quarantine']).name
            qfd = os.open(qname, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=rfd)
            try:
                recovery_quarantine(rfd, qfd)
                evidence_shape(plan, staged=True)
                quarantine_shape(qfd, rows)
                validate_protected(plan)
                # Retain the complete destination hierarchy before admission.
                destinations = recovery_destinations(rfd, plan)
                validate_recovery_destinations(rfd, plan, destinations)
                # Re-hash authenticated inputs directly before the first
                # namespace mutation.  This remains useful even after release
                # validation, which intentionally happened before the mutex.
                validate_recovery_plan(BINDING['path'])
                validate_attempt2(plan)
                recovery_quarantine(rfd, qfd)
                validate_recovery_destinations(rfd, plan, destinations)
                recovery_evidence_shape(plan, destinations, staged=True)
                quarantine_shape(qfd, rows)
                owned = pinned_references((rfd, root), (qfd, outputs['quarantine']))
                census = collect_census(root)
                journal.append({'event': 'recovery-census', 'census': census,
                                'owned_references': owned})
                check_census(census, root, owned)
                for lease in LEASES:
                    require(not os.path.lexists(lease), 'active-lease')
                require_unlatched()
                journal.append({'event': 'recovery-admitted', 'count': len(rows),
                                'attempt2': ATTEMPT2})
                phase = 'restoring'
                for index in reversed(range(len(rows))):
                    row = rows[index]
                    require_unlatched()
                    recovery_quarantine(rfd, qfd)
                    validate_recovery_destinations(rfd, plan, destinations)
                    parent = recovery_parent(destinations, row)
                    target_name = Path(row['path']).name
                    require(not _name_exists(parent, target_name), 'recovery-destination-exists')
                    verify_name(qfd, str(index), row)
                    journal.append({'event': 'restore-intent', 'index': index, 'restore': row})
                    states[index] = 'restore-uncertain'
                    require_unlatched()
                    rename_noreplace(qfd, str(index), parent, target_name)
                    require_unlatched()
                    states[index] = 'restored-not-durable'
                    os.fsync(parent); os.fsync(qfd)
                    verify_name(parent, target_name, row)
                    states[index] = 'restored'
                    journal.append({'event': 'restored', 'index': index})
                phase = 'final-scan'
                require_unlatched()
                recovery_quarantine(rfd, qfd)
                require(not os.listdir(qfd), 'recovery-quarantine-not-empty')
                recovery_original_evidence(plan, destinations)
                validate_protected(plan)
                require_unlatched()
                census = collect_census(root)
                journal.append({'event': 'recovery-final-census', 'census': census,
                                'owned_references': owned})
                check_census(census, root, owned)
                for lease in LEASES:
                    require(not os.path.lexists(lease), 'active-lease')
                recovery_original_evidence(plan, destinations)
                validate_protected(plan)
                require_unlatched()
                result = recovery_result(plan, outputs, states, 'PASS', 'complete')
                journal.append({'event': 'recovery-complete', 'count': len(rows)})
                return result
            except BaseException as error:
                # Never let an evidence-writer fault suppress independent
                # reconciliation of later rows.  This reports every observed
                # location, including rows never reached by the forward loop.
                interrupted = isinstance(error, KeyboardInterrupt) or _terminal_latched
                reconciliation = []
                for index, row in enumerate(rows):
                    where, observations = (reconcile_recovery_rename(row, qfd, index, destinations)
                                           if destinations is not None else
                                           reconcile_rename(row, qfd, index))
                    states[index] = ('restored' if where == 'original' else
                                     'staged' if where == 'staged' else 'restore-uncertain')
                    entry = {'index': index, 'state': states[index], 'locations': observations}
                    reconciliation.append(entry)
                    try:
                        journal.append({'event': 'recovery-reconciled', **entry})
                    except BaseException:
                        entry['journal_failure'] = True
                result = recovery_result(plan, outputs, states, 'FAIL', phase,
                                         str(error) if isinstance(error, Refusal) else type(error).__name__,
                                         interrupted)
                result['reconciliation'] = reconciliation
                try:
                    journal.append({'event': 'recovery-failure', **result})
                except BaseException:
                    result['journal_failure'] = True
                return result
            finally:
                if destinations is not None:
                    close_recovery_destinations(destinations)
                os.close(qfd)
    except BaseException as error:
        return recovery_result(plan, outputs, states, 'FAIL', phase,
                               str(error) if isinstance(error, Refusal) else type(error).__name__,
                               isinstance(error, KeyboardInterrupt) or _terminal_latched)


def _name_exists(parent, name):
    try:
        os.stat(name, dir_fd=parent, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def validate_live_staged_recovery(plan):
    """Read-only recovery admission probe; it intentionally creates no outputs."""
    root = plan['candidate_root']
    with directory(root) as rfd:
        qname = Path(ATTEMPT2['quarantine']['path']).name
        qfd = os.open(qname, os.O_RDONLY | os.O_DIRECTORY | NOFOLLOW, dir_fd=rfd)
        destinations = None
        try:
            recovery_quarantine(rfd, qfd)
            destinations = recovery_destinations(rfd, plan)
            validate_recovery_destinations(rfd, plan, destinations)
            recovery_evidence_shape(plan, destinations, staged=True)
            quarantine_shape(qfd, plan['targets'])
            validate_protected(plan)
            owned = pinned_references((rfd, root), (qfd, ATTEMPT2['quarantine']['path']))
            census = collect_census(root)
            check_census(census, root, owned)
            for lease in LEASES:
                require(not os.path.lexists(lease), 'active-lease')
            require_unlatched()
        finally:
            if destinations is not None:
                close_recovery_destinations(destinations)
            os.close(qfd)


def execute_recovery(plan_path, release_path, release_commit, outputs, command):
    """Dedicated --recover-staged entry point; it never enters _transact."""
    release = validate_recovery_release(release_path, release_commit, outputs, command)
    with directory(str(Path(MUTEX).parent)) as mutex_parent:
        mutex = os.open(Path(MUTEX).name, os.O_RDWR | os.O_CREAT | NOFOLLOW, 0o600, dir_fd=mutex_parent)
        try:
            os.fsync(mutex); os.fsync(mutex_parent)
        except BaseException:
            os.close(mutex); raise
    try:
        s = os.fstat(mutex)
        require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1 and stat.S_IMODE(s.st_mode) == 0o600 and
                s.st_uid == os.geteuid(), 'mutex-identity')
        fcntl.flock(mutex, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with opened(MUTEX) as current:
            require(metadata(os.fstat(current)) == metadata(s), 'mutex-replaced')
        plan = validate_recovery_plan(plan_path)
        require(release['_staged_manifest']['targets'] == plan['targets'], 'recovery-manifest-targets')
        receipt = validate_attempt2(plan)
        del receipt
        recovery_output_paths(outputs, plan)
        open_outputs = precreate_recovery_outputs(outputs)
        try:
            with terminal_latch():
                journal = FDJournal(open_outputs['journal'][1])
                result = None
                try:
                    journal.append({'event': 'recovery-admitted', 'plan': BINDING, 'attempt2': ATTEMPT2,
                                    'outputs': outputs, 'command': command, 'release_commit': release_commit,
                                    'mutex': {'path': MUTEX, **metadata(s)},
                                    'absent_leases': release['absent_leases']})
                    result = recover_staged(plan, outputs, journal)
                except BaseException as error:
                    result = recovery_result(plan, outputs, ['restore-uncertain'] * len(plan['targets']),
                                             'FAIL', 'recovery-entered',
                                             str(error) if isinstance(error, Refusal) else type(error).__name__,
                                             isinstance(error, KeyboardInterrupt) or _terminal_latched)
                    try:
                        journal.append({'event': 'recovery-unwind-failure', **result})
                    except BaseException:
                        result['journal_failure'] = True
                return publish_recovery_result(open_outputs, result, outputs, journal)
        finally:
            close_recovery_outputs(open_outputs)
    finally:
        os.close(mutex)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--validate-only', action='store_true')
    mode.add_argument('--validate-recovery', action='store_true')
    mode.add_argument('--execute', action='store_true')
    mode.add_argument('--recover-staged', action='store_true')
    parser.add_argument('--plan', default=BINDING['path'])
    parser.add_argument('--release')
    for key in ('journal', 'receipt', 'status', 'quarantine'):
        parser.add_argument('--' + key)
    args = parser.parse_args(argv)
    try:
        if args.validate_only:
            validate_plan(args.plan)
            print('VALIDATION_PASS; no mutation or runtime acceptance')
            return 0
        if args.validate_recovery:
            require(args.release, 'release-required')
            release_commit = git(REPO, 'rev-parse', REMOTE_REF).decode().strip()
            release = validate_recovery_release(args.release, release_commit)
            plan = validate_recovery_plan(args.plan)
            require(release['_staged_manifest']['targets'] == plan['targets'], 'recovery-manifest-targets')
            validate_attempt2(plan)
            with terminal_latch():
                validate_live_staged_recovery(plan)
            print('RECOVERY_VALIDATION_PASS; no output or candidate mutation')
            return 0
        outputs = {k: getattr(args, k) for k in ('journal', 'receipt', 'status', 'quarantine')}
        require(all(outputs.values()), 'output-paths-required')
        require(args.release, 'release-required')
        release_commit = git(REPO, 'rev-parse', REMOTE_REF).decode().strip()
        command = [sys.executable, str(Path(__file__).absolute()), *sys.argv[1:]]
        result = (execute_recovery(args.plan, args.release, release_commit, outputs, command)
                  if args.recover_staged else
                  execute(args.plan, args.release, release_commit, outputs, command))
        print(('RECOVERY_' if args.recover_staged else 'STORAGE_') + result['status'])
        return 0 if result['status'] == 'PASS' else 130 if result.get('interrupted') else 1
    except BaseException as error:
        print('FAIL_CLOSED: ' + (str(error) if isinstance(error, Refusal)
                                else type(error).__name__), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
