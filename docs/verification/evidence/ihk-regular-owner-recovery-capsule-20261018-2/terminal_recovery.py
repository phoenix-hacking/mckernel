#!/usr/bin/env python3
"""One fixed failed-owner recovery. No live operation without a hash-bound release.

Observation is a separate root-only, read-only release. Terminal mutation needs
an independent release bound to that actual report, not to the failed receipt.
All failures preserve old bytes; uncertainty after owner signal holds root lock.
"""
import argparse
import errno
import re
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import select
import resource
import signal
import stat
import subprocess
import time

BASE = Path('/home/holden/mckernel-work/host-preparation/ihk-regular-owner-recovery-20261018-2')
ROOT = Path('/home/holden/mckernel-work/scratch')
ARCHIVE_PREFIX = 'ihk-regular-owner-recovery-20261018-2'
PACKET = BASE / 'packet.json'
SELF = BASE / 'terminal_recovery.py'
TEST = BASE / 'test_terminal_recovery.py'
ROOT_LOCK = Path('/run/lock/mckernel-development.lock')
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
OWNER = 1057705
WAITER = 1057703
WAITER_START = '13318757'
START = '13318764'
CID = '3e173850a69a0debb2a8aee918cf9ea4f50525d3859e53178c80f934219c5213'
NONCE = '196ae0d069494667b4e4e2d610ca506c'
NAME = 'mckernel-external-' + NONCE
RECORDS = (
    ROOT / 'native-ihk-strict-objtool-pilot.lease.json',
    ROOT / 'native-ihk-strict-objtool-pilot-operational-exclusion.json',
    ROOT / 'mckernel-heavy-operation.lock',
)
ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
LIMIT = 8 << 20


class Refusal(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def pairs(rows):
        out = {}
        for key, value in rows:
            need(key not in out, 'duplicate JSON key')
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs)


def directory(path):
    # Copied from native_fp_save_image_terminal_cleanup.directory: open every
    # ancestor without symlink traversal; never trust an absolute basename alone.
    need(path.is_absolute() and '..' not in path.parts, 'noncanonical directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd
    except BaseException:
        os.close(fd)
        raise


def metadata(meta):
    return {key: getattr(meta, 'st_' + key) for key in
            ('dev', 'ino', 'mode', 'uid', 'gid', 'nlink', 'size', 'mtime_ns', 'ctime_ns')}


def snapshot(path, maximum=LIMIT):
    parent = directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= maximum,
             'bounded regular singleton required: ' + str(path))
        raw = bytearray()
        while len(raw) <= before.st_size:
            part = os.read(fd, min(65536, before.st_size + 1 - len(raw)))
            if not part:
                break
            raw.extend(part)
        need(metadata(before) == metadata(os.fstat(fd)) == metadata(
             os.stat(path.name, dir_fd=parent, follow_symlinks=False)) and len(raw) == before.st_size,
             'file raced: ' + str(path))
        return dict(path=str(path), metadata=metadata(before), sha256=sha(raw)), bytes(raw)
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)


def checked(path, wanted):
    row, raw = snapshot(path)
    need(row == wanted, 'generation/bytes changed: ' + str(path))
    return raw


def create(path, raw):
    parent = directory(path.parent)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            os.fchown(fd, 1000, 1000)
            while raw:
                count = os.write(fd, raw)
                need(count > 0, 'write made no progress')
                raw = raw[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(parent)
    finally:
        os.close(parent)


def statrow(pid):
    raw = Path('/proc/' + str(pid) + '/stat').read_bytes()
    need(len(raw) <= 65536, 'proc stat bound')
    left, sep, right = raw.rpartition(b') ')
    fields = right.split()
    need(sep and left.startswith(str(pid).encode() + b' (') and len(fields) >= 50, 'proc stat shape')
    return dict(pid=pid, ppid=int(fields[1]), pgid=int(fields[2]), sid=int(fields[3]),
                starttime=fields[19].decode('ascii'), state=fields[0].decode('ascii'))


def process_snapshot_once(progress):
    need(os.geteuid() == 0, 'root census required')
    entries = os.listdir('/proc')
    need(len(entries) <= 8192, 'process count bound')
    progress['enumerated_pids'] = sorted(int(x) for x in entries if x.isdigit())
    rows = []
    for value in entries:
        if not value.isdigit():
            continue
        pid = int(value)
        before = statrow(pid)  # ANY unreadable/raced row refuses; absence alone is insufficient.
        cmd = Path('/proc/' + value + '/cmdline').read_bytes()
        need(len(cmd) <= 65536 and (not cmd or cmd.endswith(b'\0')), 'proc cmdline bound')
        argv = [x.decode('utf-8', 'strict') for x in cmd[:-1].split(b'\0')] if cmd else []
        exe = os.readlink('/proc/' + value + '/exe') if argv else ''
        after = statrow(pid)
        need(all(after[k] == before[k] for k in ('pid', 'ppid', 'pgid', 'sid', 'starttime')), 'proc row raced')
        meta = Path('/proc/' + value).stat()
        rows.append(dict(before, uid=meta.st_uid, exe=exe, argv=argv))
        progress['observed_rows'] = list(rows)
    need(any(r['pid'] == 1 for r in rows) and any(r['pid'] == os.getpid() for r in rows), 'incomplete process census')
    return sorted(rows, key=lambda r: r['pid'])

def process_snapshot_retry(evidence,stem,clock=time.monotonic):
    need(re.fullmatch(r'[a-z0-9-]{1,64}',stem) is not None,'census evidence stem')
    deadline=clock()+3.0
    for attempt in range(3):
        progress={'attempt':attempt,'enumerated_pids':[],'observed_rows':[]}
        try:
            rows=process_snapshot_once(progress)
            need(clock()<=deadline,'whole census wall budget exhausted')
        except BaseException as exc:
            progress.update(status='FAILED_WHOLE_CENSUS_DISCARDED',error_type=type(exc).__name__,error=str(exc),filename=getattr(exc,'filename',None),errno=getattr(exc,'errno',None))
            create(evidence/(stem+'-%d.json'%attempt),canonical(progress))
            retry=(isinstance(exc,OSError) and exc.errno==errno.ENOENT and isinstance(exc.filename,str) and re.fullmatch(r'/proc/[0-9]+(?:/(?:stat|cmdline|exe))?',exc.filename) is not None)
            if not retry:raise
            need(attempt<2 and clock()<deadline,'whole census disappearance retry budget exhausted')
        else:
            progress.update(status='COMPLETE',observed_rows=rows)
            create(evidence/(stem+'-%d.json'%attempt),canonical(progress))
            return rows
    raise Refusal('unreachable census retry exhaustion')
def process_pair_retry(evidence,stem):
    before=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    rows=[process_snapshot_retry(evidence,stem+'-before'),process_snapshot_retry(evidence,stem+'-after')]
    need(before==BOOT==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'boot changed')
    return rows


def process_pair():
    raise Refusal('unscoped census forbidden; use evidence-bound whole-census retry')


def validate_processes(snapshots, packet, owner_live):
    need(len(snapshots) == 2, 'two root snapshots required')
    roots = {OWNER, *packet['client_roots']}
    need(WAITER not in roots, 'waiter is distinct from owner/client roots')
    heavy = {'make', 'ninja', 'rustc', 'cargo', 'gcc', 'g++', 'cc', 'clang', 'clang++',
             'mcexec', 'firecracker', 'qemu-kvm', 'buildah'}
    for rows in snapshots:
        bypid = {r['pid']: r for r in rows}
        need(len(bypid) == len(rows) and 1 in bypid, 'bad full process census')
        owner = bypid.get(OWNER)
        waiter = bypid.get(WAITER)
        if owner_live:
            need(waiter is not None and waiter['starttime'] == WAITER_START and
                 waiter['argv'] == packet['waiter_argv'] and waiter['exe'] == packet['waiter_exe'] and
                 waiter['uid'] == 1000 and owner is not None and owner['ppid'] == WAITER,
                 'exact outer waiter/owner relation unproven')
            need(owner is not None and owner['starttime'] == START and owner['uid'] == 1000 and
                 owner['argv'] == packet['owner_argv'] and owner['exe'] == packet['owner_exe'] and
                 owner['state'] in ('S', 'R'), 'exact live quarantined owner unproven')
        else:
            need(owner is None and waiter is None, 'owner/waiter present or PID reused')
        related = set(roots)
        while True:
            expanded = related | {r['pid'] for r in rows if r['ppid'] in related}
            if expanded == related:
                break
            related = expanded
        allowed = {OWNER} if owner_live else set()
        need(not ((related & set(bypid)) - allowed), 'client/owner descendant or reused PID present')
        need(not any((r['pgid'] in packet['client_roots'] or r['sid'] in packet['client_roots'])
                     for r in rows), 'client group/session remains live')
        ancestors = {os.getpid()}
        parent = os.getpid()
        while parent in bypid and bypid[parent]['ppid'] != parent:
            parent = bypid[parent]['ppid']
            ancestors.add(parent)
        for row in rows:
            name = os.path.basename(row['exe'])
            if row['pid'] != OWNER and row['pid'] not in ancestors:
                for arg in row['argv']:
                    base = os.path.basename(arg)
                    need(not (base.startswith(('native_rust_exact_', 'native-exact-', 'native_exact_', 'native_running_')) and
                              base.endswith(('.py', '.sh')) and any(term in base for term in
                              ('build', 'cleanup', 'recovery', 'owner', 'guest'))), 'concurrent project publisher')
                need(name not in heavy and not name.startswith('qemu-system-'), 'concurrent heavy process')
                need(not (name in ('docker', 'podman') and any(
                    a in ('build', 'run', 'start', 'create', 'rm', 'stop', 'kill') for a in row['argv'][1:])),
                    'concurrent container mutation')
        # Target must not be the launcher, server, current controller or its ancestors.
        protected = set(packet['protected_pids']) | {os.getpid(), WAITER}
        ppid = os.getpid()
        while ppid in bypid and bypid[ppid]['ppid'] != ppid:
            ppid = bypid[ppid]['ppid']
            protected.add(ppid)
        need(OWNER not in protected, 'protected control process target')


def owner_lock():
    meta = ROOT_LOCK.lstat()
    need(stat.S_ISREG(meta.st_mode) and (meta.st_dev, meta.st_ino, meta.st_uid, meta.st_gid) == (27, 4, 0, 0),
         'persistent root lock identity differs')
    # /proc/locks gives the flock owner, and fdinfo ties the owner descriptor to
    # the same inode. Never infer ownership merely from a path or an absent PID.
    wanted = '%02x:%02x:%d' % (os.major(27), os.minor(27), 4)
    matching = [line for line in Path('/proc/locks').read_text().splitlines()
                if len(line.split()) >= 8 and line.split()[5] == wanted]
    need(len(matching) == 1 and matching[0].split()[1:5] == ['FLOCK', 'ADVISORY', 'WRITE', str(OWNER)],
         'exact owner root flock not proven')
    fds = []
    for value in os.listdir('/proc/%d/fd' % OWNER):
        path = Path('/proc/%d/fd/%s' % (OWNER, value))
        info = path.stat()
        if (info.st_dev, info.st_ino) == (27, 4):
            raw = Path('/proc/%d/fdinfo/%s' % (OWNER, value)).read_text()
            need(any('FLOCK' in line and 'WRITE %d %s ' % (OWNER, wanted) in line for line in raw.splitlines()),
                 'owner descriptor flock unproven')
            fds.append(dict(fd=int(value), fdinfo=raw))
    need(bool(fds), 'owner root-lock descriptor absent')
    return dict(metadata=metadata(meta), proc_lock=matching[0], descriptors=fds)


def mount():
    got = subprocess.run(['/usr/bin/findmnt', '-J', '-T', str(ROOT), '-o',
                          'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'], env=ENV,
                         stdin=subprocess.DEVNULL, capture_output=True, timeout=10, check=False)
    need(got.returncode == 0 and not got.stderr and len(got.stdout) <= 65536, 'findmnt failed')
    rows = parse(got.stdout)['filesystems']
    need(len(rows) == 1 and rows[0]['target'] == str(ROOT) and rows[0]['source'] == '/dev/loop36' and
         rows[0]['uuid'] == UUID and rows[0]['fstype'] == 'ext4' and rows[0]['maj:min'] == '7:36' and
         {'rw', 'nosuid', 'nodev'} <= set(rows[0]['options'].split(',')) and ROOT.stat().st_dev == 1828,
         'scratch mount binding differs')
    backing = Path('/sys/block/loop36/loop/backing_file').read_text().strip()
    size = int(Path('/sys/block/loop36/size').read_text().strip()) * 512
    need(size == 110 * 2**30, 'scratch loop size differs')
    backing_path = Path(backing)
    need(backing_path == Path('/home/holden/mckernel-work/scratch.ext4'), 'scratch backing path differs')
    parent = directory(backing_path.parent)
    try:
        meta = os.stat(backing_path.name, dir_fd=parent, follow_symlinks=False)
        need(stat.S_ISREG(meta.st_mode) and meta.st_size == size and meta.st_nlink == 1, 'backing file shape differs')
        binding = {k: getattr(meta, 'st_' + k) for k in ('dev', 'ino', 'mode', 'uid', 'gid', 'size', 'nlink')}
    finally:
        os.close(parent)
    return dict(mount=rows[0], backing=backing, backing_identity=binding, size_bytes=size)


def pins(packet, records=True):
    for row in packet.get('artifact_files', []):
        checked(Path(row['path']), row)
    wanted = {row['path']: row for row in packet['files']}
    for path, row in wanted.items():
        if records or Path(path) not in RECORDS:
            checked(Path(path), row)
    for item in packet['directories']:
        path = Path(item['path'])
        fd = directory(path)
        try:
            meta = os.fstat(fd)
            need({k: getattr(meta, 'st_' + k) for k in ('dev', 'ino', 'mode', 'uid', 'gid')} == item['metadata'],
                 'input/evidence namespace differs')
            # Namespace exact name inventory detects extra and missing evidence.
            if 'names' in item:
                need(sorted(str(p.relative_to(path)) for p in path.rglob('*')) == item['names'],
                     'evidence name inventory differs')
        finally:
            os.close(fd)
    return wanted


def fixed_docker_child_limits():
    # Accepted observer-resource correction: Go Docker needs 2 GiB address
    # space. Never pass the Python observer's 256 MiB soft limit to the CLI.
    resource.setrlimit(resource.RLIMIT_AS, (2 * 2**30, 2 * 2**30))


def pidfd_open(pid):
    # This host's reviewed architecture is Linux x86_64. Anaconda Python 3.9
    # omits the os/signal wrappers; use the same kernel operations directly.
    need(os.uname().sysname == 'Linux' and os.uname().machine == 'x86_64', 'pidfd ABI architecture differs')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    result = libc.syscall(ctypes.c_long(434), ctypes.c_int(pid), ctypes.c_uint(0))
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return int(result)


def pidfd_signal(fd, number):
    need(os.uname().sysname == 'Linux' and os.uname().machine == 'x86_64', 'pidfd ABI architecture differs')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    result = libc.syscall(ctypes.c_long(424), ctypes.c_int(fd), ctypes.c_int(number),
                          ctypes.c_void_p(0), ctypes.c_uint(0))
    if result < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def bound_pidfd(pid, start):
    fd = pidfd_open(pid)
    try:
        need(statrow(pid)['starttime'] == start, 'pidfd process start differs')
        need(not select.select([fd], [], [], 0)[0], 'pidfd process already dead')
        return fd
    except BaseException:
        os.close(fd)
        raise


class Docker:
    """Only fixed root Docker calls. Capture original transport exit and group proof."""
    def __init__(self, evidence):
        self.evidence, self.count = evidence, 0
        self.unproven = False

    def call(self, args):
        self.count += 1
        stem = self.evidence / ('client-%02d' % self.count)
        argv = ['/usr/bin/docker', '--host=unix:///var/run/docker.sock', *args]
        # Establish exception ownership before spawn. Popen retains its direct
        # child unreaped until our communicate; no numeric PID/PGID signals.
        proc = None
        child_pidfd = None
        pidfd_bound = False
        out, err = b'', b''
        joined = group_closed = False
        status = dict(argv=argv, pid=None, identity=None, state='launching')
        try:
            proc = subprocess.Popen(argv, env=ENV, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, start_new_session=True,
                                    preexec_fn=fixed_docker_child_limits)
            status['pid'] = proc.pid
            identity = statrow(proc.pid)
            need(identity['pid'] == proc.pid and identity['ppid'] == os.getpid() and
                 identity['pgid'] == identity['sid'] == proc.pid, 'new direct Docker child identity differs')
            status['identity'] = identity
            child_pidfd = pidfd_open(proc.pid)
            current = statrow(proc.pid)
            need(all(current[k] == identity[k] for k in ('pid','ppid','pgid','sid','starttime')),
                 'new direct Docker child PIDFD/start binding differs')
            pidfd_bound = True
            status['state'] = 'started'
            create(stem.with_suffix('.started.json'), canonical(status))
            out, err = proc.communicate(timeout=30)
            joined = True
            need(len(out) + len(err) <= LIMIT, 'Docker output bound')
            status.update(state='exited', exit_code=proc.returncode)
            rows = process_pair_retry(self.evidence,'docker-client-%d' % self.count)
            need(not any(r['pid'] == proc.pid or r['pgid'] == proc.pid or r['sid'] == proc.pid
                         for group in rows for r in group), 'new Docker client group unproven')
            group_closed = True
            status['root_group_retired'] = True
            need(proc.returncode == 0 and (not err or args[0] == 'logs'), 'Docker command failed')
            create(stem.with_suffix('.status.json'), canonical(status))
            create(stem.with_suffix('.stdout'), out)
            create(stem.with_suffix('.stderr'), err)
            return out + err if args[0] == 'logs' else out
        except BaseException as original:
            # Mark uncertainty BEFORE fallible cleanup or evidence writes.
            self.unproven = True
            cleanup = dict(direct_joined=joined, complete_group_absence=group_closed,
                           pidfd_acquired=child_pidfd is not None, pidfd_start_bound=pidfd_bound, signal_sent=False, errors=[])
            status.update(state='failed', error_type=type(original).__name__, error=str(original),
                          root_group_retired=False, cleanup=cleanup)
            if proc is not None:
                if not joined and child_pidfd is not None and pidfd_bound:
                    try:
                        pidfd_signal(child_pidfd, signal.SIGKILL)
                        cleanup['signal_sent'] = True
                    except ProcessLookupError:
                        cleanup['errors'].append({'stage':'pidfd-signal','error':'ProcessLookupError'})
                    except BaseException as exc:
                        cleanup['errors'].append({'stage':'pidfd-signal','error':str(exc)})
                if not joined:
                    try:
                        out, err = proc.communicate(timeout=5)
                        joined = True
                        cleanup['direct_joined'] = True
                        cleanup['exit_code'] = proc.returncode
                    except BaseException as exc:
                        cleanup['errors'].append({'stage':'direct-join','error':str(exc)})
                if joined and not group_closed:
                    try:
                        rows = process_pair_retry(self.evidence,'docker-client-%d-failure' % self.count)
                        need(not any(r['pid'] == proc.pid or r['pgid'] == proc.pid or r['sid'] == proc.pid
                                     for group in rows for r in group), 'failed Docker client group unproven')
                        group_closed = True
                        cleanup['complete_group_absence'] = True
                    except BaseException as exc:
                        cleanup['errors'].append({'stage':'group-closure','error':str(exc)})
            # These unique failure captures never overwrite a partial original.
            # Logging failure cannot skip child cleanup, direct wait or closure.
            for suffix,payload in [('.failure-status.json',status),
                                   ('.failure-stdout',out),('.failure-stderr',err)]:
                try:
                    raw = canonical(payload) if suffix == '.failure-status.json' else payload
                    create(stem.with_suffix(suffix),raw)
                except BaseException as exc:
                    cleanup['errors'].append({'stage':'failure-evidence'+suffix,'error':str(exc)})
            if proc is not None and not (joined and group_closed):
                # Preserve Popen/PIDFD/known identity AND the caller's full stack
                # (including any reacquired root FD). This function makes no
                # assertion about which caller currently owns root27:4.
                hold_client_quarantine(stem,status,proc,child_pidfd)
            raise
        finally:
            if child_pidfd is not None:
                os.close(child_pidfd)


def hold_client_quarantine(stem,status,proc,child_pidfd):
    """Retain unresolved owned child and caller stack; never infer root ownership."""
    try:create(stem.with_suffix('.client-quarantine.json'),canonical(dict(
        status='QUARANTINED_UNRESOLVED_OWN_DIRECT_CLIENT',controller_pid=os.getpid(),
        controller_starttime=statrow(os.getpid())['starttime'],client=status,
        root_mutex_ownership='NOT_ASSERTED_BY_DOCKER_CLIENT',original_records_or_guards_retained=True)))
    except BaseException:pass
    while True:
        try:time.sleep(60)
        except BaseException:pass


def mount_rows(rows):
    # Same complete-row contract as the frozen external-module owner's
    # mount_rows: destinations are unique absolute strings; retain every field,
    # value, type and row count, sorting only the serialized complete rows.
    need(isinstance(rows, list) and all(isinstance(r, dict) for r in rows), 'mount shape')
    targets = [r.get('Destination') for r in rows]
    need(all(isinstance(t, str) and t.startswith('/') for t in targets) and
         len(set(targets)) == len(targets), 'duplicate/nonabsolute mount target')
    return sorted(canonical(row) for row in rows)


def container_identity(item):
    need(isinstance(item, dict), 'container identity shape')
    normalized = dict(item)
    normalized['Mounts'] = [parse(raw) for raw in mount_rows(item.get('Mounts'))]
    return canonical(normalized)


def observation_packet_join(observation, packet, current_sha):
    return observation.get('packet_sha256') == current_sha


def container(docker, packet):
    raw = docker.call(['ps', '-a', '--no-trunc', '--format', '{{json .}}'])
    targets = []
    seen = set()
    for line in raw.splitlines():
        row = parse(line)
        need(isinstance(row, dict) and isinstance(row.get('ID'), str) and len(row['ID']) == 64 and
             all(c in '0123456789abcdef' for c in row['ID']) and row['ID'] not in seen and
             isinstance(row.get('Names'), str) and isinstance(row.get('Labels'), str), 'container census row shape')
        seen.add(row['ID'])
        need(row.get('State') in ('created', 'exited', 'dead'), 'concurrent active container')
        if row.get('ID') == CID or row.get('Names') == NAME or 'mckernel.owner=' + NONCE in row.get('Labels', '').split(','):
            targets.append(row)
    need(len(targets) == 1 and targets[0]['ID'] == CID and targets[0]['Names'] == NAME,
         'exact container inventory unproven')
    rows = parse(docker.call(['inspect', '--type', 'container', CID]))
    need(isinstance(rows, list) and len(rows) == 1, 'inspect shape')
    item = rows[0]
    expected = packet['container']
    for key in ('Id', 'Name', 'Image', 'Path', 'Args', 'Config', 'HostConfig', 'State',
                'Created', 'RestartCount', 'AppArmorProfile', 'Platform'):
        need(item.get(key) == expected.get(key), 'container profile drift: ' + key)
    need(mount_rows(item.get('Mounts')) == mount_rows(expected.get('Mounts')), 'container profile drift: Mounts')
    state = item['State']
    need(item['Id'] == CID and item['Name'] == '/' + NAME and
         item['Config']['Labels']['mckernel.owner'] == NONCE and state['Status'] == 'exited' and
         state['Pid'] == 0 and state['ExitCode'] == 0 and state['Running'] is False and
         state['OOMKilled'] is False, 'container not exact stopped retained target')
    logs = docker.call(['logs', '--', CID])
    need(sha(logs) == packet['container_log_sha256'], 'container log bytes differ')
    return item


def absence(docker):
    for query in ('name=^/' + NAME + '$', 'label=mckernel.owner=' + NONCE, 'id=' + CID):
        need(docker.call(['ps', '-a', '--quiet', '--no-trunc', '--filter', query]).strip() == b'',
             'container absence unproven')
    need(not docker.unproven, 'cleanup client retirement unproven')


def archive_failure_files(packet, evidence):
    archive = evidence / 'verified-failure-files'
    os.mkdir(archive, 0o700)
    copied = []
    total = 0
    for index, row in enumerate(packet['files']):
        raw = checked(Path(row['path']), row)
        total += len(raw)
        need(total <= LIMIT, 'failure archive total bound')
        target = archive / ('%03d.raw' % index)
        create(target, raw)
        need(snapshot(target)[0]['sha256'] == row['sha256'], 'failure archive bytes differ')
        copied.append(dict(original=row, archive=str(target)))
    create(evidence / 'verified-failure-archive.json', canonical(dict(
        status='EXACT_FAILURE_FILES_ARCHIVED', files=copied, bytes=total,
        implementation_success=False, old_transport_latch_cleared=False)))
    pins(packet)


def resources():
    reserve = 8 << 20
    host = os.statvfs('/')
    scratch = os.statvfs(ROOT)
    result = dict(host_free=host.f_bavail * host.f_frsize, scratch_free=scratch.f_bavail * scratch.f_frsize)
    need(result['host_free'] >= 16 * 2**30 + reserve and result['scratch_free'] >= 12 * 2**30 + reserve,
         'continuing host/scratch floors plus 8 MiB recovery capture reserve required')
    return result


def observe(packet, evidence):
    need(os.getuid() == os.geteuid() == 0, 'use independently released sudo -A root command')
    check_stop()
    pins(packet)
    mounted = mount()
    need(mounted == packet['scratch'], 'loop/backing mount drift')
    measured = resources()
    locks = owner_lock()
    rows = process_pair_retry(evidence,'observe-before')
    validate_processes(rows, packet, True)
    docker = Docker(evidence)
    item = container(docker, packet)
    rows_after = process_pair_retry(evidence,'observe-after')
    validate_processes(rows_after, packet, True)
    pins(packet)
    need(owner_lock() == locks, 'owner lock changed during observation')
    return dict(schema='mckernel.ihk-failed-owner-root-observation.v1', status='PASS_READ_ONLY_ROOT_OBSERVATION',
                boot_id=BOOT, packet_sha256=sha(snapshot(PACKET)[1]), source_bindings=source_bindings(), monotonic=time.monotonic(), owner_lock=locks,
                process_snapshots=rows, final_process_snapshots=rows_after, container=item,
                scratch=mounted, resources=measured, old_failure_preserved=True,
                old_transport_latch_cleared=False, observer=dict(pid=os.getpid(), starttime=statrow(os.getpid())['starttime']))


def exchange(parent, source, dest):
    # Same renameat2(RENAME_EXCHANGE) primitive as the proven cleanup scripts.
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    need(rename is not None, 'renameat2 unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(parent, os.fsencode(source), parent, os.fsencode(dest), 2):
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def record_geometry(parent, records, sentinels, exchanged=0, released=0):
    need(len(records) == len(sentinels) == 3, 'exact three regular records required')
    for index,(record,row) in enumerate(zip(records,sentinels)):
        need(record['path'] == str(ROOT / row['active']), 'record active path differs')
        if index < exchanged:
            archived = snapshot(ROOT / row['archive'])[0]
            need(archived['sha256'] == record['sha256'] and all(archived['metadata'][k] == record['metadata'][k] for k in ('dev','ino','mode','uid','gid','nlink','size','mtime_ns')), 'archived original generation/bytes differ')
            if index < released:
                try: os.stat(row['active'],dir_fd=parent,follow_symlinks=False)
                except FileNotFoundError: pass
                else: raise Refusal('released ownership name republished')
            else: guard(parent,row['active'],row)
        else:
            checked(ROOT / row['active'],record)
            guard(parent,row['archive'],row)

def guard(parent,name,row):
    st=os.stat(name,dir_fd=parent,follow_symlinks=False)
    need(stat.S_ISDIR(st.st_mode) and stat.S_IMODE(st.st_mode)==0o700 and st.st_uid==0 and st.st_gid==0 and st.st_nlink==2 and (st.st_dev,st.st_ino)==(row['dev'],row['ino']),'root guard generation/metadata differs')
    fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
    try:
        fst=os.fstat(fd)
        need(metadata(fst)==metadata(st) and not os.listdir(fd),'guard fd raced or nonempty')
    finally:os.close(fd)

def journal_row(fd,value):
    raw=canonical(value)
    offset=0
    while offset<len(raw):
        count=os.write(fd,raw[offset:])
        need(type(count) is int and 0<count<=len(raw)-offset,'journal write made invalid/no progress')
        offset+=count
    os.fsync(fd)

def claim_records(packet, evidence, boundary):
    """One new three-REGULAR-record transaction; never resume interrupted plans."""
    wanted = {r['path']: r for r in packet['files']}
    records = [wanted[str(p)] for p in RECORDS]
    parent = directory(ROOT);jfd = None
    try:
        boundary()
        for index,path in enumerate(RECORDS):
            raw = checked(path,records[index])
            create(evidence / ('record-%d.raw' % index),raw)
            create(evidence / ('record-%d.metadata.json' % index),canonical(records[index]))
        create(evidence / 'archive-complete.json',canonical({'records':records}))
        sentinels=[]
        for index,path in enumerate(RECORDS):
            boundary()
            name=ARCHIVE_PREFIX+'.record-%d.sentinel'%index
            os.mkdir(name,0o700,dir_fd=parent);os.fsync(parent)
            st=os.stat(name,dir_fd=parent,follow_symlinks=False)
            row={'active':path.name,'archive':name,'dev':st.st_dev,'ino':st.st_ino}
            guard(parent,name,row);sentinels.append(row)
        create(evidence/'plan.json',canonical({'records':records,'sentinels':sentinels}))
        create(evidence/'journal.jsonl',b'')
        jfd=os.open(evidence/'journal.jsonl',os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW)
        for index,row in enumerate(sentinels):
            boundary();record_geometry(parent,records,sentinels,index)
            journal_row(jfd,{'stage':'exchange-intent','index':index})
            exchange(parent,row['active'],row['archive']);os.fsync(parent)
            record_geometry(parent,records,sentinels,index+1)
            journal_row(jfd,{'stage':'exchange-complete','index':index})
        create(evidence/'release-authorized.json',canonical({'status':'THREE_RECORDS_ARCHIVED_AND_CLAIMED','sentinels':sentinels}))
        for index,row in enumerate(sentinels):
            boundary();record_geometry(parent,records,sentinels,3,index)
            journal_row(jfd,{'stage':'release-intent','index':index})
            os.rmdir(row['active'],dir_fd=parent);os.fsync(parent)
            record_geometry(parent,records,sentinels,3,index+1)
            journal_row(jfd,{'stage':'release-complete','index':index})
        boundary();record_geometry(parent,records,sentinels,3,3)
        check_stop()
        create(evidence/'complete.json',canonical({'status':'EXACT_REGULAR_OWNER_TERMINAL_RECOVERED','implementation_success':False,'old_failure_preserved':True,'old_transport_latch_cleared':False,'external_tool_session_97778_positive_join':'ROOT_DISPATCHER_PENDING'}))
    finally:
        if jfd is not None: os.close(jfd)
        os.close(parent)


def hold_quarantine(evidence, fd, error, acquired=True):
    try:
        create(evidence / 'quarantine.json', canonical(dict(
               status='QUARANTINED_ROOT_LOCK_HELD' if acquired else 'QUARANTINED_RECORD_GUARDS_RETAINED',
               pid=os.getpid(), root_lock=[27, 4], root_mutex_acquired=acquired, error=str(error))))
    except BaseException:
        pass
    while True:
        try:
            time.sleep(60)
        except BaseException:
            pass


def acquire_root_mutex(fd, timeout=10):
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            need(time.monotonic() < deadline, 'root mutex handoff race/timeout')
            time.sleep(0.05)


def recover(packet, evidence, observation):
    # Run all fresh observations while original owner still holds its mutex.
    now = observe(packet, evidence)
    create(evidence / 'fresh-pre-signal-root-observation.json', canonical(now))
    need(observation['status'] == 'PASS_READ_ONLY_ROOT_OBSERVATION' and
         observation_packet_join(observation, packet, now['packet_sha256']) and observation['owner_lock'] == now['owner_lock'] and
         observation['scratch'] == now['scratch'] and
         container_identity(observation['container']) == container_identity(now['container']),
         'independent fresh observation binding differs')
    waiter_pidfd = bound_pidfd(WAITER, WAITER_START)
    pidfd = bound_pidfd(OWNER, START)
    rfd = os.open(ROOT_LOCK, os.O_RDONLY | os.O_NOFOLLOW)
    mutated = False
    acquired = False
    signal_sent = False
    try:
        need((os.fstat(rfd).st_dev, os.fstat(rfd).st_ino) == (27, 4), 'root-lock opened wrong inode')
        pins(packet)
        check_stop()
        validate_processes(process_pair_retry(evidence,'pre-signal'), packet, True)
        owner_lock()
        need(not select.select([pidfd], [], [], 0)[0], 'owner pidfd already exited')
        create(evidence / 'owner-retirement-intent.json', canonical(dict(owner_pid=OWNER, starttime=START,
               signal='SIGKILL', reason='exact source quarantine catches all cooperative signals',
               guard='three original exclusion records remain intact until root mutex reacquired')))
        mutated = True
        # pidfd points to the validated process even if numeric PID changes later.
        check_stop()
        pidfd_signal(pidfd, signal.SIGKILL)
        signal_sent = True
        check_stop()
        need(bool(select.select([pidfd], [], [], 10)[0]), 'owner pidfd retirement timeout')
        need(bool(select.select([waiter_pidfd], [], [], 10)[0]), 'outer waiter positive join timeout')
        acquire_root_mutex(rfd)
        acquired = True
        need((ROOT_LOCK.lstat().st_dev, ROOT_LOCK.lstat().st_ino) == (27, 4), 'root mutex replaced')
        pins(packet)
        deadline = time.monotonic() + 10
        while True:
            try:
                former = statrow(OWNER)
            except FileNotFoundError:
                break
            need(former['starttime'] == START and former['state'] in ('Z', 'X', 'x'), 'owner PID reused or remains live')
            need(time.monotonic() < deadline, 'dead owner not reaped before census')
            time.sleep(0.05)
        await_absent(WAITER, WAITER_START)
        check_stop()
        validate_processes(process_pair_retry(evidence,'post-retirement'), packet, False)
        create(evidence / 'owner-retired-root-mutex-reacquired.json', canonical(dict(
               retired_owner=[BOOT, OWNER, START], pidfd_readable=True, root_lock=[27, 4],
               joined_waiter=[BOOT, WAITER, WAITER_START], waiter_pidfd_readable=True,
               controller=[os.getpid(), statrow(os.getpid())['starttime']])))
        docker = Docker(evidence / 'postflight')
        os.mkdir(docker.evidence, 0o700)
        container(docker, packet)
        need(not docker.unproven, 'new transport group uncertain')
        archive_failure_files(packet, evidence)
        docker.call(['rm', '--', CID])  # Exact verified stopped CID only.
        absence(docker)
        boundary_count=[0]
        def boundary():
            check_stop()
            need((os.fstat(rfd).st_dev, os.fstat(rfd).st_ino) == (27, 4) and
                 (ROOT_LOCK.lstat().st_dev, ROOT_LOCK.lstat().st_ino) == (27, 4), 'root mutex changed')
            fcntl.flock(rfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            need(mount() == packet['scratch'], 'scratch changed at transaction boundary')
            resources()
            pins(packet, records=False)
            boundary_count[0] += 1
            validate_processes(process_pair_retry(evidence,'boundary-%d'%boundary_count[0]), packet, False)
            absence(docker)
        boundary()
        claim_records(packet, evidence, boundary)
        check_stop()
    except BaseException as exc:
        if mutated:
            # If reacquisition failed the unchanged common/shared records still
            # exclude cooperative work; preserve that fact and never pretend lock.
            if not acquired:
                create(evidence / 'handoff-unproven.json', canonical(dict(status='RECORDS_RETAINED_HANDOFF_UNPROVEN',
                       error=str(exc), owner_signal_sent=signal_sent, root_mutex_acquired=False)))
            hold_quarantine(evidence, rfd, exc, acquired=acquired)
        raise
    finally:
        os.close(pidfd)
        os.close(waiter_pidfd)
        os.close(rfd)


def source_bindings():
    return {name:sha(snapshot(BASE/name)[1]) for name in ('terminal_recovery.py','test_terminal_recovery.py','packet.json')}

def authorize(path, digest, mode):
    row,raw=snapshot(path);need(row['sha256']==digest,'release bytes differ');release=parse(raw)
    packet=parse(snapshot(PACKET)[1]);bindings=source_bindings()
    need(release.get('status') == ('PASS_REGULAR_READ_ONLY_OBSERVATION_RELEASE' if mode=='observe' else 'PASS_EXACT_REGULAR_RECOVERY_RELEASE') and release.get('author') and release.get('reviewer') and release['author']!=release['reviewer'] and type(release.get('execution_count')) is int and release['execution_count']==1 and release.get('sources')==bindings and release.get('boot_id')==BOOT and release.get('no_concurrent_publishers') is True and release.get('owner')==packet['owner'] and release.get('outer')==packet['waiter'],'independent exact new-generation one-shot release required')
    if mode=='observe':
        need(release.get('read_only') is True,'read-only observation required');return packet,None
    need(release.get('pidfd_sigkill_only')==[BOOT,OWNER,START] and release.get('signal_parent_launcher_server') is False and release.get('remove_exact_stopped_container')==CID and release.get('archive_release_exact_three_regular_records') is True and release.get('positive_natural_outer_join')==[WAITER,WAITER_START],'exact terminal operations not released')
    ref=release['root_observation'];obsrow,obsraw=snapshot(Path(ref['path']));need(obsrow['sha256']==ref['sha256'],'root observation bytes differ');observation=parse(obsraw)
    need(observation.get('status')=='PASS_READ_ONLY_ROOT_OBSERVATION' and observation.get('source_bindings')==bindings and observation.get('packet_sha256')==bindings['packet.json'] and 0<=time.monotonic()-observation['monotonic']<=1800,'new exact root observation expired or source mismatch')
    validate_processes(observation['process_snapshots'],packet,True);validate_processes(observation['final_process_snapshots'],packet,True)
    return packet,observation

STOP_REQUEST=None
STOP_COUNT=0

def termination_latch(number,frame):
    global STOP_REQUEST,STOP_COUNT
    if STOP_REQUEST is None: STOP_REQUEST=number
    STOP_COUNT=min(STOP_COUNT+1,2147483647)

def check_stop():
    need(STOP_REQUEST is None,'termination request latched during exact recovery: %s'%STOP_REQUEST)

def await_absent(pid,start,timeout=10):
    deadline=time.monotonic()+timeout
    while True:
        try: row=statrow(pid)
        except FileNotFoundError:return
        need(row['starttime']==start and row['state'] in ('Z','X','x'),'retired PID reused/still live')
        need(time.monotonic()<deadline,'retired process not reaped');time.sleep(.05)


def main():
    global STOP_REQUEST,STOP_COUNT
    STOP_REQUEST=None;STOP_COUNT=0
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('mode',choices=('observe','recover'));parser.add_argument('--release',required=True,type=Path);parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
    need(os.getuid()==os.geteuid()==0,'root-only independently released command')
    resource.setrlimit(resource.RLIMIT_AS,(256*2**20,2*2**30))
    packet,observation=authorize(args.release,args.release_sha256,args.mode)
    evidence=BASE/(args.mode+'-evidence');os.mkdir(evidence,0o700);os.chown(evidence,1000,1000)
    handlers={number:signal.signal(number,termination_latch) for number in (signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGINT)}
    try:
        try:
            if args.mode=='observe': create(evidence/'root-observation.json',canonical(observe(packet,evidence)))
            else: recover(packet,evidence,observation)
        except BaseException as exc:
            try:create(evidence/'failure.json',canonical({'status':'FAIL_PRESERVED','error':str(exc)}))
            except BaseException:pass
            raise
    finally:
        for number,prior in handlers.items():signal.signal(number,prior)


if __name__ == '__main__':
    main()
