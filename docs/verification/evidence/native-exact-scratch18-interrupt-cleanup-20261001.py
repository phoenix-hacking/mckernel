#!/usr/bin/env python3
"""Fixed-path archival retirement; default is read-only validation.

The persistent mutex is never unlinked. flock releases it on process death.
A torn plan/journal is retained and refused, never repaired speculatively.
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
import stat
import subprocess

ROOT = Path('/home/holden/mckernel-work/scratch')
DEVICE = 1831
UID = GID = 1000
ATTEMPT = ROOT / 'native-exact-candidate-operational-exclusion-scratch18.json'
SHARED = ROOT / 'mckernel-heavy-operation.lock'
LEASE = ROOT / 'native-exact-build-lease-scratch-18.json'
OUTPUT = ROOT / 'mckernel-exact-candidate-scratch-18-output'
EVIDENCE = ROOT / 'mckernel-exact-candidate-scratch-18-evidence'
MUTEX = ROOT / 'native-exact-scratch18-interrupt-cleanup.mutex'
PLAN = ROOT / 'native-exact-scratch18-interrupt-cleanup.plan.json'
JOURNAL = ROOT / 'native-exact-scratch18-interrupt-cleanup.journal.jsonl'
ARCHIVE_NAMES = ('native-exact-scratch18-interrupt-attempt.archive',
                 'native-exact-scratch18-interrupt-lease.archive',
                 'native-exact-scratch18-interrupt-shared.archive')
TERMINAL = EVIDENCE / 'inspect-terminal.json'
TERMINAL_SHA = 'c2196dd5b766dfc604a47c850b48b537a60c7043a22662f1953f9df5166426e6'
TERMINAL_INODE = 3571989
TERMINAL_SIZE = 9649
CONTAINER = 'fb3917d1485a1572815dcb9dcb505526f1f6da72f0db26372d0678822fe09193'
CONTAINER_NAME = 'mckernel-exact-9fb87f6fe3614764bebcd924b62b0fa8'
OWNER_PID = 3314709
OWNER_START = '107861476'
WAITER_PIDS = (3315128, 3315131)
OWNER_NONCE = '082111a619e44cf0a7d8b5d5863d0d46'
BOOT_ID = 'c733d83b-a5ae-4f91-9ce6-9f8ccf119afd'
RECORDS = {
    ATTEMPT: ('76bc6aa633d1098ac6e3f0f7a5b0701d002ccf3d5f8980427b2cb124eb67bf9e', 90734, 269),
    SHARED: ('c4ca1cabb6dadbe9f01b2403d22f9688c35953db0376db4c8d2fc7c7af74206d', 90733, 269),
    LEASE: ('a48f2d1f0f645f3f8e8de60365d0b9f8256c47ee6fb66074993f4328fedbc2fb', 90735, 174),
}
DIRS = {OUTPUT: (3571962, 4), EVIDENCE: (3571963, 13)}
LIMIT = 1 << 20
PUBLISHER_CONTRACT = {
    'schema': 'scratch18.publisher-contract.v1',
    'coordination': 'sole-campaign-coordinator-no-concurrent-build-or-cleanup',
    'publishers': 'project-owned-regular-file-O_CREAT|O_EXCL-only',
    'census': 'privileged-full-process-and-active-container-before-transaction-and-every-rmdir',
    'excluded': 'arbitrary-same-UID-directory-substitution-after-final-check',
}

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

def rename_exchange(fd, source, destination):
    """Atomically leave a directory sentinel at the active ownership name."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise Refusal('renameat2-unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(fd, os.fsencode(source), fd, os.fsencode(destination), 2):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))

def sudo_environment():
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
    if os.environ.get('SUDO_ASKPASS'):
        env['SUDO_ASKPASS'] = os.environ['SUDO_ASKPASS']
    return env

# Executed only by sudo's absolute Python, isolated from caller modules/env.
# Every listed stat must read/parse; disappearing processes cause a retryable
# refusal. Two full snapshots and unchanged boot identity authenticate scope.
PROC_CODE = r'''
import json,os,sys
caller=[int(sys.argv[2]),sys.argv[3]]
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
        elif argv and publisher(exe,argv): publishers.append([pid,str(start),exe])
        rows.append([pid,ppid,str(start)])
    if not found: raise ValueError('caller-missing')
    return sorted(rows),publishers
if os.geteuid()!=0: raise ValueError('not-root')
with open('/proc/sys/kernel/random/boot_id') as f: boot=f.read().strip()
first,pubs1=snapshot(); second,pubs2=snapshot()
with open('/proc/sys/kernel/random/boot_id') as f: after=f.read().strip()
if boot!=after: raise ValueError('boot-raced')
print(json.dumps({'schema':'scratch18.proc.v1','uid':os.geteuid(),'boot_id':boot,
                  'challenge':sys.argv[1],'caller':caller,'publishers':pubs1+pubs2,'snapshots':[first,second]}))
'''

def run_privileged(args):
    result = subprocess.run(['/usr/bin/sudo', '-A', *args], env=sudo_environment(),
                            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30, check=False)
    if result.returncode or result.stderr or len(result.stdout) > LIMIT:
        raise Refusal('privileged-observer-failed')
    return result.stdout

def validate_process_report(report, challenge, caller):
    if (not isinstance(report, dict) or set(report) != {'schema','uid','boot_id','challenge','caller','publishers','snapshots'} or
        report['schema'] != 'scratch18.proc.v1' or type(report['uid']) is not int or report['uid'] != 0 or
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
        state.get('Status') != 'exited' or type(state.get('ExitCode')) is not int or state['ExitCode'] != 143 or
        state.get('Running') is not False or state.get('Pid') != 0):
        raise Refusal('container-retirement-binding')
    return True

class Transaction:
    def __init__(self):
        self.fd, self.chain = directory(ROOT)
        self.mfd = None
        if os.fstat(self.fd).st_dev != DEVICE:
            self.close()
            raise Refusal('scratch-device')
        for path in (ATTEMPT, LEASE, SHARED, MUTEX, PLAN, JOURNAL, OUTPUT, EVIDENCE):
            if path.parent != ROOT:
                self.close()
                raise Refusal('fixed-path-parent')

    def close(self):
        for name in ('mfd', 'fd'):
            fd = getattr(self, name, None)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)

    def pinned(self):
        fd, chain = directory(ROOT)
        os.close(fd)
        if chain != self.chain:
            raise Refusal('ancestor-replaced')
        if self.mfd is not None and identity(os.stat(MUTEX.name, dir_fd=self.fd, follow_symlinks=False)) != identity(os.fstat(self.mfd)):
            raise Refusal('mutex-replaced')

    def preserved(self):
        self.pinned()
        for path, (inode, nlink) in DIRS.items():
            fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
            try:
                meta = os.fstat(fd)
                if (identity(meta) != (DEVICE, inode) or meta.st_nlink != nlink or
                    stat.S_IMODE(meta.st_mode) != 0o700 or (meta.st_uid, meta.st_gid) != (UID, GID)):
                    raise Refusal('preserved-directory-binding')
                if path == EVIDENCE:
                    read_at(fd, TERMINAL.name, (TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE))
                if identity(os.stat(path.name, dir_fd=self.fd, follow_symlinks=False)) != identity(meta):
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
        return {'schema': 'scratch18.interrupt-cleanup.v5', 'root': str(ROOT),
                'ancestry': [list(x) for x in self.chain], 'device': DEVICE,
                'mutex': list(identity(os.fstat(self.mfd))) if self.mfd is not None else None,
                'owner': [BOOT_ID, OWNER_PID, OWNER_START], 'waiters': list(WAITER_PIDS),
                'container': [CONTAINER, CONTAINER_NAME, OWNER_NONCE],
                'records': [[p.name, archive, *RECORDS[p]]
                            for p, archive in zip((ATTEMPT, LEASE, SHARED), ARCHIVE_NAMES)],
                'sentinels': sentinels,
                'publisher_contract': PUBLISHER_CONTRACT,
                'directories': [[p.name, *DIRS[p]] for p in (OUTPUT, EVIDENCE)],
                'terminal': [TERMINAL.name, TERMINAL_SHA, TERMINAL_INODE, TERMINAL_SIZE]}

    def pristine(self):
        self.preserved()
        if exists(self.fd, JOURNAL.name):
            raise Refusal('journal-without-plan')
        for path, archive in zip((ATTEMPT, LEASE, SHARED), ARCHIVE_NAMES):
            read_at(self.fd, path.name, RECORDS[path])
            if exists(self.fd, archive):
                # A crash during preparation has not touched any active record.
                # Retain unbound preparation, rather than adopt a foreign dir.
                raise Refusal('unbound-sentinel-preparation')

    def sentinel(self, name, expected):
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
        try:
            meta = os.fstat(fd)
            if (meta.st_dev != DEVICE or list(identity(meta)) != expected or meta.st_nlink != 2 or
                stat.S_IMODE(meta.st_mode) != 0o700 or (meta.st_uid, meta.st_gid) != (UID, GID) or
                os.listdir(fd)):
                raise Refusal('sentinel-binding')
            if identity(os.stat(name, dir_fd=self.fd, follow_symlinks=False)) != identity(meta):
                raise Refusal('sentinel-raced')
        finally:
            os.close(fd)

    def load_plan(self):
        raw, _ = read_at(self.fd, PLAN.name)
        value = parse(raw)
        sentinels = value.get('sentinels') if isinstance(value, dict) else None
        if (not isinstance(sentinels, list) or len(sentinels) != 3 or
            any(not isinstance(row, list) or len(row) != 2 or
                type(row[0]) is not int or row[0] != DEVICE or
                type(row[1]) is not int or row[1] <= 0 for row in sentinels) or
            len({tuple(row) for row in sentinels}) != 3):
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
            fd = os.open(archive, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.fd)
            try:
                expected = list(identity(os.fstat(fd)))
                self.sentinel(archive, expected)
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(self.fd)
            sentinels.append(expected)
        plan = self.expected_plan(sentinels)
        self.create(PLAN.name, canonical(plan) + b'\n')
        return plan

    def create(self, name, data):
        self.pinned()
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        try:
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
        legal = [(event, index) for index in range(3)
                 for event in ('before_exchange', 'after_exchange', 'release', 'after_release')] + [('complete', 3)]
        if len(rows) > len(legal):
            raise Refusal('journal-after-complete')
        previous = digest(canonical(plan))
        for seq, row in enumerate(rows):
            event, index = legal[seq]
            body = {'event': event, 'index': index, 'sequence': seq,
                    'plan_sha256': digest(canonical(plan)), 'previous': previous}
            wanted = dict(body, hash=digest(canonical(body)))
            if canonical(row) != canonical(wanted) or canonical(row) + b'\n' != raw.splitlines(keepends=True)[seq]:
                raise Refusal('journal-prefix-binding')
            previous = wanted['hash']
        paths = (ATTEMPT, LEASE, SHARED)
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
                read_at(self.fd, path.name, RECORDS[path])
                actual.append('before_exchange')
                continue
            read_at(self.fd, archive, RECORDS[path])
            if phase == 0:
                raise Refusal('unplanned-exchange')
            if exists(self.fd, path.name):
                active_meta = os.stat(path.name, dir_fd=self.fd, follow_symlinks=False)
                if stat.S_ISDIR(active_meta.st_mode):
                    if phase == 4:
                        raise Refusal('sentinel-reappeared-after-release')
                    self.sentinel(path.name, sentinel)
                    actual.append('after_exchange')
                    continue
                # A fresh ordinary owner may acquire the name after release.
                # Validate its shape only; never remove or claim its ownership.
                read_at(self.fd, path.name)
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
        self.lock(execute)
        plan = self.load_plan() if exists(self.fd, PLAN.name) else None
        if plan is None:
            self.pristine()
            rows, actual = [], []
        else:
            rows, actual = self.state(plan)
        present = census()
        self.pinned()
        if len(rows) == 13:
            if present:
                raise Refusal('terminal-container-reappeared')
            return {'status': 'PASS_TERMINAL_REPLAY', 'terminal': True, 'publisher_contract': PUBLISHER_CONTRACT}
        if not execute:
            return {'status': 'PASS_VALIDATE_ONLY', 'terminal': False, 'events': len(rows),
                    'container_present': present, 'publisher_contract': PUBLISHER_CONTRACT}
        if plan is None:
            plan = self.prepare()
        if not exists(self.fd, JOURNAL.name):
            self.create(JOURNAL.name, b'')
        if present:
            # Require the same exited identity immediately before removal.
            if not census():
                raise Refusal('container-disappeared-before-rm')
            removed = docker(['rm', '--', CONTAINER]).strip()
            if removed not in (CONTAINER.encode(), CONTAINER_NAME.encode()):
                raise Refusal('container-remove-response')
        if census():
            raise Refusal('container-still-present')
        for index, path in enumerate((ATTEMPT, LEASE, SHARED)):
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
                read_at(self.fd, path.name, RECORDS[path])
                self.sentinel(ARCHIVE_NAMES[index], plan['sentinels'][index])
                self.pinned()
                # Atomic exchange never vacates the active ownership pathname.
                # A foreign capture fails validation while its sentinel stays
                # active; neither object is deleted or speculatively rolled back.
                rename_exchange(self.fd, path.name, ARCHIVE_NAMES[index])
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
                self.sentinel(path.name, plan['sentinels'][index])
                self.pinned()
                # This is the intended release point. A raced-in regular file
                # causes ENOTDIR and remains intact; replay preserves that owner.
                os.rmdir(path.name, dir_fd=self.fd)
            os.fsync(self.fd)
            rows, actual = self.state(plan)
            self.append(plan, rows, 'after_release', index)
        rows, actual = self.state(plan)
        if census():
            raise Refusal('container-reappeared')
        self.preserved()
        self.append(plan, rows, 'complete', 3)
        self.state(plan)
        return {'status': 'PASS_EXECUTED', 'terminal': True, 'plan_sha256': digest(canonical(plan)),
                'publisher_contract': PUBLISHER_CONTRACT}

def recover(execute=False):
    tx = Transaction()
    try:
        return tx.run(execute)
    finally:
        tx.close()

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = recover(args.execute)
    except (Refusal, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
