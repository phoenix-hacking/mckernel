#!/usr/bin/env python3
"""One-shot storage maintenance; no OS acceptance and no implicit execution release.

Release schema: mckernel.scratch13-cleanup-release.v1. The committed JSON must
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
TOOL_PATH = 'docs/verification/evidence/native-exact-scratch13-planbound-evidence-cleanup-20261001.py'
REMOTE_REF = 'refs/remotes/origin/codex/local-native-staging-repair'
SCRATCH = '/home/holden/mckernel-work/scratch'
BINDING = {
    # The reviewed audit plan is deliberately a later, separately released
    # input.  These zero counters fail closed until its exact binding is
    # installed; tests replace this whole row with a disposable fixture.
    'path': SCRATCH + '/native-exact-retained-candidate-6fed3a10-source-evidence-plan-20261001.json',
    'sha256': '0' * 64,
    'size': 0, 'dev': 1831, 'ino': 0, 'mode': 0o600, 'nlink': 1,
    'root': SCRATCH + '/mckernel-exact-candidate-6fed3a10-scratch-13',
    'identity': '1831:3169097',
    'commit': '6fed3a1022db0b4f9828dd42a8bd8f88fc052053',
    'count': 0, 'bytes': 0, 'allocated': 0,
}
MUTEX = SCRATCH + '/native-exact-scratch13-cleanup-operation.mutex'
LEASES = [SCRATCH + '/native-exact-build-lease-6fed3a10-scratch-13.json',
          SCRATCH + '/native-exact-mckernel-image-lease-6fed3a10-exportset-25.json']
CONTAINER = 'aef5164c5209f62b5f1be6d545f34001779d2ed78008235114890f981635708b'
CONTAINER_NAME = '/mckernel-image-bc0df6c9bd6d4234a1ec686df14ec493'
# The failed build has one retained terminal Docker identity.  Keep the alias
# for the inherited census/recovery code, but never invent a second container.
HOST_CONTAINER = CONTAINER

_UNSUPPORTED_RECOVERY = {}
# No staged-recovery identity exists for this fresh adapter.  Recovery is
# intentionally unsupported until a real failed transaction is independently
# retained and reviewed; fabricated journal/quarantine hashes are forbidden.
_terminal_latched = False
_terminal_committed = False
_terminal_result = None
_terminal_depth = 0


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
    suffix = '-6fed3a10-exportset-' + str(export)
    mounts = [mount(BINDING['root'], '/src'),
              mount(SCRATCH + '/native-exact-inputs-6fed3a10-scratch-13.json', '/inputs.json'),
              mount(prefix + 'toolchain' + suffix + '.json', '/toolchain.json'),
              mount(str(REPO) + '/scripts/native_rust_exact_mckernel_image_offline.py', '/driver.py'),
              mount(str(REPO) + '/scripts/native_rust_exact_build_offline.py', '/native_rust_exact_build_offline.py'),
              mount(prefix + 'work' + suffix, '/work', True),
              # The failed exportset-25 receipt intentionally retained the
              # prior output root; it is a protected failure input, not a
              # newly discovered cleanup target.
              mount(SCRATCH + '/native-exact-build-output-4e99a82c-scratch-12', '/out'),
              mount(SCRATCH + '/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu'
                    if export == 25 else '/home/holden/.rustup/toolchains/nightly-x86_64-unknown-linux-gnu', '/nightly')]
    if export == 25:
        mounts += [mount(SCRATCH + '/native-exact-mckernel-gitlink-inputs-6fed3a10-exportset-25.json', '/libdwarf-inputs.json'),
                   mount(SCRATCH + '/native-exact-mckernel-gitlink-libdwarf-6fed3a10-exportset-25', '/src/executer/user/lib/libdwarf/libdwarf')]
    return {'Name': name, 'owner_nonce': nonce, 'RestartCount': 0,
            'State': terminal_state(1, started, finished),
            'proof_kind': 'image_owner_receipt',
            'proof': {'path': prefix + 'owner-evidence' + suffix + '/owner-receipt.json',
                      'sha256': proof_sha, 'size': proof_size, 'dev': 1831,
                      'ino': proof_ino, 'mode': 0o600, 'nlink': 1},
            'Mounts': mounts}


CONTAINER_BINDINGS = {
    # This is the sole retained terminal identity from exportset-25.  The
    # owner receipt is the authenticated proof; no prior build container is
    # admitted by this fresh cleanup adapter.
    CONTAINER: image_binding(
        25, CONTAINER_NAME, '5630f734cf3249d38945489942d03fad',
        'df80c9c506e47bb3b5905cd5970e077dfa8744e9cd60422bb9c0c2f927c98785',
        17574, 1723593,
        '2026-10-01T03:16:26.008470799Z', '2026-10-01T03:17:40.771963574Z'),
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
    rows = plan['protected_inventory']
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


def protected_overlap(plan, path):
    """Return true only for an exact protected object, not anchor paths."""
    root = plan['candidate_root']
    anchors = {root, root + '/docs/verification/evidence'}
    return any(p not in anchors and
               (inside(path, canonical(p)) or inside(p, path))
               for p in plan['protected_paths'])


def validate_preserved_git_status(commit, row):
    """Prove a preserved row is not an exact committed Git duplicate."""
    raw = git(REPO, 'ls-tree', '-z', commit, '--', row['restore_git_path'])
    if not raw:
        require(row['blob'] is None, 'preserved-git-identity')
        return
    fields = raw.rstrip(b'\0').split(b'\t', 1)
    require(len(fields) == 2, 'preserved-git-tree')
    mode, kind, blob = fields[0].decode('ascii').split()
    require(kind == 'blob' and fields[1].decode() == row['restore_git_path'] and
            row['blob'] == blob, 'preserved-git-identity')
    committed = git(REPO, 'cat-file', 'blob', blob)
    require(sha(committed) != row['sha256'] or len(committed) != row['size'] or
            mode != ('100755' if row['mode'] & 0o111 else '100644'),
            'preserved-is-exact-git-duplicate')


def evidence_shape(plan, staged=False):
    """Exact no-follow census, including otherwise invisible extra empty dirs."""
    base = plan['candidate_root'] + '/docs/verification/evidence'
    # Preserved rows remain live throughout staging and deletion. Re-open each
    # descriptor and re-authenticate bytes/metadata before every irreversible
    # phase; shape-only checks are insufficient for these non-target files.
    for row in plan.get('preserved', []):
        with opened(row['path']) as fd:
            verify_fd(fd, row)
        validate_preserved_git_status(plan['candidate_commit'], row)
    expected_files = {r['path'][len(base) + 1:]
                      for r in plan['targets'] + plan.get('preserved', [])}
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
    preserved_files = {r['path'][len(base) + 1:] for r in plan.get('preserved', [])}
    require(dirs == expected_dirs and files == (preserved_files if staged else expected_files),
            'subtree-set')


def quarantine_shape(qfd, rows):
    require(set(os.listdir(qfd)) == {str(i) for i in range(len(rows))}, 'quarantine-set')
    for i, row in enumerate(rows):
        verify_name(qfd, str(i), row)


def validate_plan(path, binding=None):
    binding = BINDING if binding is None else binding
    require(str(path) == binding['path'], 'plan-path')
    plan, _ = read_json(path, binding)
    v1 = {'anchor_inventory', 'candidate_commit', 'candidate_identity',
          'candidate_root', 'nested_delta_preserved', 'preserved',
          'protected_inventory', 'protected_paths', 'schema', 'status', 'targets'}
    require(set(plan) == v1, 'plan-schema')
    require(plan['schema'] == 'mckernel.exact-git-source-audit.v1' and
            plan['status'] == 'AUDIT_PASS' and
            isinstance(plan['preserved'], list) and
            plan['nested_delta_preserved'] is True, 'plan-status')
    root = canonical(plan['candidate_root'])
    require(root == binding['root'] and plan['candidate_commit'] == binding['commit']
            and plan['candidate_identity'] == binding['identity'], 'plan-binding')
    with directory(root) as fd:
        s = os.fstat(fd)
        require(str(s.st_dev) + ':' + str(s.st_ino) == binding['identity'], 'root-identity')
    anchors = []
    for anchor in (root, root + '/docs/verification/evidence'):
        with directory(anchor) as fd:
            s = os.fstat(fd)
            anchors.append({'path': anchor, 'type': 'directory', 'dev': s.st_dev,
                            'ino': s.st_ino, 'mode': stat.S_IMODE(s.st_mode)})
    require(plan['anchor_inventory'] == anchors, 'anchor-inventory')
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
        require(not protected_overlap(plan, path), 'target-protected')
        names.add(path)
        inodes.add((row['dev'], row['ino']))
        with opened(path) as fd:
            verify_fd(fd, row)
        committed_file(binding['commit'], row['restore_git_path'], row)
    for row in plan.get('preserved', []):
        require(set(row) == {'allocated_bytes', 'blob', 'dev', 'ino', 'mode', 'mtime_ns',
                             'nlink', 'path', 'restore_git_path', 'sha256', 'size'}, 'preserved-row-schema')
        target = canonical(row['path'])
        require(target.startswith(root + '/docs/verification/evidence/') and
                target == root + '/' + row['restore_git_path'] and
                target not in names and (row['dev'], row['ino']) not in inodes and
                row['nlink'] == 1 and row['mode'] in (0o644, 0o755) and
                not protected_overlap(plan, target), 'preserved-path-set')
        names.add(target); inodes.add((row['dev'], row['ino']))
        with opened(target) as fd:
            verify_fd(fd, row)
        validate_preserved_git_status(binding['commit'], row)
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
    require(release['schema'] == 'mckernel.scratch13-cleanup-release.v1' and
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
            require(inside(path, output_root) and path != output_root and
                    not inside(path, root) and not protected_overlap(plan, path),
                    'output-protected')
        with directory(str(Path(path).parent)):
            pass


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
            # The final census alone cannot authenticate preserved files or
            # protected objects. Revalidate both immediately before PASS is
            # published, so a late drift can never be reported as success.
            evidence_shape(plan, staged=True)
            validate_protected(plan)
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
                progress = transaction_progress(plan)
                try:
                    journal.append({'event': 'transaction-entered'})
                    result = transact(plan, outputs, journal, progress)
                except BaseException as error:
                    result = escaped_transaction(plan, outputs, journal, progress, error)
            publish(outputs['receipt'], result)
            publish(outputs['status'], {'status': result['status'], 'receipt': outputs['receipt'],
                                        'journal': outputs['journal']})
            return result
        finally:
            journal.close()
    finally:
        os.close(mutex)
def result_exit_code(result):
    return 0 if result['status'] == 'PASS' else 130 if result.get('interrupted') else 1


def main(argv=None, cli=False):
    args = parse_args(argv)
    return _main(args)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--validate-only', action='store_true')
    mode.add_argument('--execute', action='store_true')
    parser.add_argument('--plan', default=BINDING['path'])
    parser.add_argument('--release')
    for key in ('journal', 'receipt', 'status', 'quarantine'):
        parser.add_argument('--' + key)
    return parser.parse_args(argv)


def _main(args):
    try:
        if args.validate_only:
            validate_plan(args.plan)
            print('VALIDATION_PASS; no mutation or runtime acceptance')
            return 0
        outputs = {k: getattr(args, k) for k in ('journal', 'receipt', 'status', 'quarantine')}
        require(all(outputs.values()), 'output-paths-required')
        require(args.release, 'release-required')
        release_commit = git(REPO, 'rev-parse', REMOTE_REF).decode().strip()
        command = [sys.executable, str(Path(__file__).absolute()), *sys.argv[1:]]
        result = execute(args.plan, args.release, release_commit, outputs, command)
        print('STORAGE_' + result['status'])
        return result_exit_code(result)
    except BaseException as error:
        print('FAIL_CLOSED: ' + (str(error) if isinstance(error, Refusal)
                                else type(error).__name__), file=sys.stderr)
        return 1


def cli_exit():
    code = main(cli=True)
    if _terminal_committed:
        # Python's implicit stream flush can change exit 0 to 120. Perform
        # best-effort delivery explicitly and keep the durable outcome through
        # the final syscall, with the committed terminal handler still installed.
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except BaseException:
                pass
        os._exit(code)
    raise SystemExit(code)


if __name__ == '__main__':
    cli_exit()
