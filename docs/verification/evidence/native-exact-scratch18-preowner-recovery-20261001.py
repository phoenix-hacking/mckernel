#!/usr/bin/env python3
"""Candidate recovery of exactly two retained scratch18 ownership records.

Independent execution release is required. No public API accepts observation
reports or alternative paths. The private engine supports disposable tests.
"""
import argparse
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import types

REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
EVIDENCE = Path(__file__).with_name('native-exact-scratch18-build-admission-failure-20261001-1.json')
FAILURE_SHA256 = '40497b42fd0906cfe45af35ee07a9be736948db8cda84d036216e9670663aec7'
# Candidate dependency binding, not independent acceptance or execution release.
WRAPPER_SHA256 = 'ccfbd404ff2428c4eb8841948b761118a42bd25ed8875c583755e6a97d8f0393'
BOOT_ID = 'c733d83b-a5ae-4f91-9ce6-9f8ccf119afd'
ARCHIVE = 'native-exact-scratch18-preowner-archives'
MUTEX = 'native-exact-scratch18-preowner-recovery.mutex'
PLAN = 'plan.json'
JOURNAL = 'journal.jsonl'
MAX_RECORD = 1 << 20


class Refusal(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def _json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refusal('duplicate-json-key')
            result[key] = value
        return result
    try:
        return json.loads(data, object_pairs_hook=pairs)
    except (ValueError, UnicodeError) as exc:
        raise Refusal('invalid-json') from exc


def _identity(st):
    return {'device': st.st_dev, 'inode': st.st_ino}


def _directory(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise Refusal('noncanonical-directory')
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


def _read_at(dfd, name, record=None, limit=MAX_RECORD):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=dfd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > limit:
            raise Refusal('artifact-shape')
        data = bytearray()
        while len(data) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = os.fstat(fd)
        stable = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        if any(getattr(before, k) != getattr(after, k) for k in stable) or len(data) != before.st_size:
            raise Refusal('artifact-changed-during-read')
        if _identity(os.stat(name, dir_fd=dfd, follow_symlinks=False)) != _identity(before):
            raise Refusal('artifact-replaced')
        if record is not None:
            actual = dict(_identity(before), sha256=sha(data), mode='%04o' % stat.S_IMODE(before.st_mode),
                          uid=before.st_uid, gid=before.st_gid)
            if any(actual[key] != record[key] for key in actual):
                raise Refusal('artifact-binding')
        return bytes(data), before
    finally:
        os.close(fd)


def _read_path(path, expected, limit=MAX_RECORD):
    fd = _directory(Path(path).parent)
    try:
        data, meta = _read_at(fd, Path(path).name, limit=limit)
        if sha(data) != expected:
            raise Refusal('artifact-hash')
        return data, meta
    finally:
        os.close(fd)


def _module(path, expected):
    data, _ = _read_path(path, expected)
    module = types.ModuleType('_bound_scratch18_dependency')
    module.__file__ = str(path)
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module


def _starttime(pid):
    try:
        return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]
    except FileNotFoundError:
        return None


def _owner():
    return {'pid': os.getpid(), 'starttime': _starttime(os.getpid()),
            'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}


def load_failure():
    return _json(_read_path(EVIDENCE, FAILURE_SHA256)[0])


def _prepared(failure, rootfd):
    rec = dict(failure['request'], device=os.fstat(rootfd).st_dev)
    if Path(rec['path']).parent != ROOT:
        raise Refusal('request-parent')
    raw, _ = _read_at(rootfd, Path(rec['path']).name, rec)
    request = _json(raw)
    if sha(canonical(request)) != rec['normalized_sha256']:
        raise Refusal('request-normalized-hash')
    for key in ('owner_path', 'driver_path', 'provenance_path', 'input_manifest',
                'image_receipt', 'ihk_overlay_path'):
        digest_key = 'ihk_overlay_sha256' if key == 'ihk_overlay_path' else key + '_sha256'
        _read_path(request[key], request[digest_key], limit=16 << 20)
    packet = _module(EVIDENCE.with_name('native-exact-scratch18-build-execution-20261001.py'),
                     failure['packet_sha256'])
    for path, digest in ((packet.LOG, packet.LOG_SHA256), (packet.TERMINAL, packet.TERMINAL_SHA256),
                         (packet.IHK / 'test/ihklib/whitebox/src/driver/mckernel/syscall.c', packet.OVERLAY_RESULT_SHA256)):
        _read_path(path, digest)
    for label in ('output', 'evidence'):
        path = Path(request[label + '_root'])
        if path.parent != ROOT:
            raise Refusal('prepared-parent')
        fd = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=rootfd)
        try:
            expected = failure['postflight'][label]
            if _identity(os.fstat(fd)) != {k: expected[k] for k in ('device', 'inode')} or os.listdir(fd):
                raise Refusal('prepared-directory-changed')
        finally:
            os.close(fd)
    if Path(request['lease_path']).parent != ROOT or _exists(rootfd, Path(request['lease_path']).name):
        raise Refusal('build-lease-present')
    return request


def observe_production(failure, rootfd):
    """Run the authenticated wrapper's read-only census as its real script.

    Its observer authenticates the wrapper ancestor, so importing and calling
    its privileged function directly would be invalid. The census-only command
    delegates to its process/lease observers without acquiring operation locks.
    """
    path = REPO / 'scripts/native_rust_exact_disk_build_wrapper.py'
    wrapper = _module(path, WRAPPER_SHA256)
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != BOOT_ID:
        raise Refusal('boot-binding')
    owner = failure['owner_identity']
    if owner != {'pid': 3288332, 'starttime': '107474009', 'current_state': 'absent'}:
        raise Refusal('retained-owner-binding')
    # PID reuse is conservatively refused, regardless of the replacement start.
    if _starttime(owner['pid']) is not None:
        raise Refusal('retained-owner-not-absent')
    request = _prepared(failure, rootfd)
    rec = dict(failure['request'], device=os.fstat(rootfd).st_dev)
    command = ['/usr/bin/python3', '-I', '-B', str(path), rec['path'],
               '--census-only', '--request-sha256', rec['sha256']]
    result = wrapper._run_bounded_observer(command, b'', wrapper._sudo_environment(), timeout=90)
    _read_path(path, WRAPPER_SHA256)
    if result.returncode or len(result.stdout) > MAX_RECORD:
        raise Refusal('wrapper-census-failed')
    report = _json(result.stdout)
    keys = {'schema', 'status', 'execution_released', 'boot_id', 'request',
            'processes', 'containers', 'leases', 'resources'}
    if (not isinstance(report, dict) or set(report) != keys or
            report['schema'] != 'mckernel.heavy-recovery-census.v1' or
            report['status'] != 'PASS_READ_ONLY' or report['execution_released'] is not False or
            report['boot_id'] != BOOT_ID or report['request'] != rec):
        raise Refusal('wrapper-census-binding')
    domains = {k: report[k] for k in ('processes', 'containers', 'leases', 'resources')}
    wrapper._validate_census_domains(domains)
    history = _module(REPO / 'scripts/native_exact_historical_lease_observer.py',
                      wrapper.HISTORICAL_OBSERVER_SHA256)
    expected = []
    for suffix, inode, size, digest, pid, start, evidence in history.LEASES:
        expected.append({'path': str(ROOT / ('native-exact-build-lease-' + suffix + '.json')),
                         'device': os.fstat(rootfd).st_dev, 'inode': inode, 'size': size, 'sha256': digest,
                         'pid': pid, 'starttime': start, 'evidence_sha256': history.EVIDENCE_BINDINGS[evidence][1]})
    if sorted(report['leases'], key=lambda x: x['path']) != sorted(expected, key=lambda x: x['path']):
        raise Refusal('historical-lease-set')
    names = {name for name in os.listdir(rootfd)
             if name.startswith('native-exact-build-lease-') and name.endswith('.json')}
    if {str(ROOT / name) for name in names} != {row['path'] for row in expected}:
        raise Refusal('lease-set-changed')
    for row in expected:
        meta = os.stat(Path(row['path']).name, dir_fd=rootfd, follow_symlinks=False)
        if not stat.S_ISREG(meta.st_mode) or (meta.st_dev, meta.st_ino, meta.st_size) != (row['device'], row['inode'], row['size']):
            raise Refusal('historical-lease-replaced')
    # Running-only census cannot prove no exited container was created. Query
    # all containers newer than the retained last-container identity as well.
    retained = failure['postflight']['latest_mckernel_container_before_attempt']
    baseline = retained['id']
    inspect = ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock',
               'inspect', '--type', 'container', '--format', '{{json .}}', baseline]
    boundary = wrapper._run_bounded_observer(inspect, b'', wrapper._sudo_environment())
    if boundary.returncode:
        raise Refusal('container-boundary-unavailable')
    container = _json(boundary.stdout)
    if (not isinstance(container, dict) or container.get('Id') != baseline or
            container.get('Name') != '/' + retained['name'] or
            not isinstance(container.get('State'), dict) or
            container['State'].get('Status') != retained['state']):
        raise Refusal('container-boundary-changed')
    command = ['/usr/bin/sudo', '-A', '/usr/bin/docker', '--host=unix:///var/run/docker.sock',
               'ps', '-a', '--no-trunc', '--filter', 'since=' + baseline, '--format', '{{json .}}']
    newer = wrapper._run_bounded_observer(command, b'', wrapper._sudo_environment())
    if newer.returncode or newer.stdout.strip():
        raise Refusal('new-or-unverifiable-container')
    resources = report['resources']
    if (resources['host_free'] < max(16 * 2**30, request['host_floor']) + wrapper.DISPATCHER_EMERGENCY_BYTES or
            resources['scratch_free'] < max(12 * 2**30, request['scratch_floor']) + wrapper.DISPATCHER_EMERGENCY_BYTES or
            resources['memory_available'] < wrapper.EXPECTED_LIMITS['Memory']):
        raise Refusal('capacity-floor')
    # Recheck the actual request/artifacts and owner after external observations.
    if _prepared(failure, rootfd) != request or _starttime(owner['pid']) is not None:
        raise Refusal('post-census-binding')
    return report


def _exists(dfd, name):
    try:
        os.stat(name, dir_fd=dfd, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False


def _write_all(fd, data):
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if type(written) is not int or written <= 0:
            raise Refusal('write-no-progress')
        offset += written


def _create(dfd, name, data):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
    try:
        _write_all(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.fsync(dfd)


def _rename_noreplace(sfd, source, dfd, destination):
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise Refusal('renameat2-unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(sfd, os.fsencode(source), dfd, os.fsencode(destination), 1):
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))


class _Transaction:
    def __init__(self, failure, root, device):
        self.failure, self.root = failure, Path(root)
        self.rfd = _directory(root)
        self.afd = self.mfd = None
        if os.fstat(self.rfd).st_dev != device:
            os.close(self.rfd)
            raise Refusal('scratch-device')
        self.root_identity = _identity(os.fstat(self.rfd))
        self.device = device

    def close(self):
        for fd in (self.afd, self.mfd, self.rfd):
            if fd is not None:
                os.close(fd)

    def pinned(self):
        fd = _directory(self.root)
        try:
            if _identity(os.fstat(fd)) != self.root_identity:
                raise Refusal('scratch-parent-replaced')
        finally:
            os.close(fd)
        if self.afd is not None:
            named = os.stat(ARCHIVE, dir_fd=self.rfd, follow_symlinks=False)
            if not stat.S_ISDIR(named.st_mode) or _identity(named) != _identity(os.fstat(self.afd)):
                raise Refusal('archive-parent-replaced')
        if self.mfd is not None:
            named = os.stat(MUTEX, dir_fd=self.rfd, follow_symlinks=False)
            if _identity(named) != _identity(os.fstat(self.mfd)):
                raise Refusal('mutex-replaced')

    def lock(self):
        self.mfd = os.open(MUTEX, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                           0o600, dir_fd=self.rfd)
        meta = os.fstat(self.mfd)
        if (not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or meta.st_size != 0 or
                meta.st_uid != os.geteuid() or stat.S_IMODE(meta.st_mode) != 0o600):
            raise Refusal('mutex-binding')
        try:
            fcntl.flock(self.mfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refusal('recovery-busy') from exc
        os.fsync(self.mfd)
        os.fsync(self.rfd)
        self.pinned()

    def open_archive(self):
        try:
            os.mkdir(ARCHIVE, 0o700, dir_fd=self.rfd)
            os.fsync(self.rfd)
        except FileExistsError:
            pass
        self.afd = os.open(ARCHIVE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.rfd)
        meta = os.fstat(self.afd)
        if meta.st_dev != self.device or meta.st_uid != os.geteuid() or stat.S_IMODE(meta.st_mode) != 0o700:
            raise Refusal('archive-binding')

    def plan(self):
        rows = []
        for label in ('attempt', 'shared'):
            original = self.failure['retained_locks'][label]
            if original.get('device', self.device) != self.device:
                raise Refusal('lock-device')
            rec = dict(original, device=self.device)
            if Path(rec['path']).parent != self.root:
                raise Refusal('lock-parent')
            rows.append({'label': label, 'source': Path(rec['path']).name,
                         'destination': label + '.archive', 'identity': rec})
        if rows[0]['source'] == rows[1]['source']:
            raise Refusal('duplicate-source')
        return {'schema': 'mckernel.scratch18-recovery-plan.v2',
                'failure_sha256': sha(canonical(self.failure)), 'wrapper_sha256': WRAPPER_SHA256,
                'root': str(self.root), 'root_identity': self.root_identity,
                'archive_identity': _identity(os.fstat(self.afd)),
                'mutex_identity': _identity(os.fstat(self.mfd)), 'moves': rows}

    def state(self, plan):
        states = []
        for row in plan['moves']:
            source = _exists(self.rfd, row['source'])
            dest = _exists(self.afd, row['destination'])
            if source == dest:
                raise Refusal('ambiguous-lock-state')
            _read_at(self.rfd if source else self.afd,
                     row['source'] if source else row['destination'], row['identity'])
            states.append('live' if source else 'archived')
        allowed = [('live', 'live'), ('archived', 'live'), ('archived', 'archived')]
        if tuple(states) not in allowed:
            raise Refusal('invalid-transition-order')
        return allowed.index(tuple(states))

    def events(self, plan):
        if not _exists(self.afd, JOURNAL):
            return []
        raw, meta = _read_at(self.afd, JOURNAL)
        if meta.st_uid != os.geteuid() or stat.S_IMODE(meta.st_mode) != 0o600 or not raw.endswith(b'\n'):
            raise Refusal('journal-binding')
        events = [_json(line) for line in raw.splitlines()]
        previous = '0' * 64
        for index, event in enumerate(events):
            if (event.get('sequence') != index or event.get('previous') != previous or
                    event.get('plan_sha256') != sha(canonical(plan))):
                raise Refusal('journal-chain')
            previous = sha(canonical(event))
        return events

    def reconcile_journal(self, events, actual):
        """Reject regressions, invented transitions and malformed owner records."""
        frontier, pending = 0, None
        terminal = False
        for row in events:
            if terminal:
                raise Refusal('journal-after-complete')
            kind = row['event']
            if kind == 'owner':
                owner = row.get('owner')
                if (not isinstance(owner, dict) or set(owner) != {'pid', 'starttime', 'boot_id'} or
                        type(owner['pid']) is not int or owner['pid'] <= 0 or
                        not isinstance(owner['starttime'], str) or not owner['starttime'].isdigit() or
                        owner['boot_id'] != _owner()['boot_id']):
                    raise Refusal('journal-owner')
            elif kind == 'before':
                if row.get('move') != frontier or frontier >= 2:
                    raise Refusal('journal-transition')
                pending = frontier
            elif kind == 'after':
                if row.get('move') != frontier or pending != frontier:
                    raise Refusal('journal-transition')
                frontier += 1
                pending = None
            elif kind == 'reconciled':
                target = row.get('state')
                allowed = (frontier, frontier + 1) if pending == frontier else (frontier,)
                if type(target) is not int or target not in allowed:
                    raise Refusal('journal-transition')
                if target != frontier:
                    frontier, pending = target, None
            elif kind == 'complete':
                if type(row.get('state')) is not int or row['state'] != 2 or frontier != 2:
                    raise Refusal('journal-transition')
                terminal = True
            else:
                raise Refusal('journal-transition')
        allowed = (frontier, frontier + 1) if pending == frontier else (frontier,)
        if actual not in allowed:
            raise Refusal('journal-state-regression')
        return terminal

    def journal(self, plan, events, event, **fields):
        self.pinned()
        record = dict(fields, event=event, sequence=len(events), plan_sha256=sha(canonical(plan)),
                      previous=sha(canonical(events[-1])) if events else '0' * 64)
        if not events:
            _create(self.afd, JOURNAL, canonical(record) + b'\n')
        else:
            fd = os.open(JOURNAL, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW, dir_fd=self.afd)
            try:
                raw, meta = _read_at(self.afd, JOURNAL)
                if _identity(meta) != _identity(os.fstat(fd)) or raw != b''.join(canonical(x) + b'\n' for x in events):
                    raise Refusal('journal-replaced')
                _write_all(fd, canonical(record) + b'\n')
                os.fsync(fd)
            finally:
                os.close(fd)
            os.fsync(self.afd)
        events.append(record)

    def run(self, observe, execute):
        observe(self.failure, self.rfd)
        if not execute:
            if _exists(self.rfd, ARCHIVE):
                self.afd = os.open(ARCHIVE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self.rfd)
                self.mfd = os.open(MUTEX, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=self.rfd)
                plan = self.plan()
                raw, _ = _read_at(self.afd, PLAN)
                if raw != canonical(plan) + b'\n':
                    raise Refusal('plan-binding')
                state = self.state(plan)
                terminal = self.reconcile_journal(self.events(plan), state)
            else:
                for record in self.failure['retained_locks'].values():
                    if Path(record['path']).parent != self.root:
                        raise Refusal('lock-parent')
                    _read_at(self.rfd, Path(record['path']).name, dict(record, device=self.device))
                state = 0
                terminal = False
            self.pinned()
            return {'status': 'PASS_VALIDATE_ONLY', 'state': state, 'terminal': terminal}
        self.lock()
        observe(self.failure, self.rfd)
        self.open_archive()
        plan = self.plan()
        if _exists(self.afd, PLAN):
            raw, meta = _read_at(self.afd, PLAN)
            if raw != canonical(plan) + b'\n' or meta.st_uid != os.geteuid() or stat.S_IMODE(meta.st_mode) != 0o600:
                raise Refusal('plan-binding')
        else:
            if os.listdir(self.afd):
                raise Refusal('unplanned-archive-content')
            for row in plan['moves']:
                _read_at(self.rfd, row['source'], row['identity'])
            _create(self.afd, PLAN, canonical(plan) + b'\n')
        state = self.state(plan)
        events = self.events(plan)
        if self.reconcile_journal(events, state):
            # The exclusive recovery mutex is still held. A valid completion
            # is immutable evidence, never permission for another transaction.
            raise Refusal('recovery-already-complete')
        owners = [row['owner'] for row in events if row['event'] == 'owner']
        if owners:
            prior = owners[-1]
            if prior['boot_id'] != _owner()['boot_id'] or _starttime(prior['pid']) is not None:
                raise Refusal('recovery-owner-not-absent')
        elif state != 0:
            raise Refusal('unowned-transition')
        for index in range(state):
            if not any(e['event'] == 'before' and e.get('move') == index for e in events):
                raise Refusal('unplanned-transition')
        self.journal(plan, events, 'owner', owner=_owner())
        # Reconcile rename-before-journal crashes and sync both directory entries
        # before acknowledging the observed state or performing another move.
        os.fsync(self.rfd)
        os.fsync(self.afd)
        self.journal(plan, events, 'reconciled', state=state)
        for index in range(state, 2):
            observe(self.failure, self.rfd)
            self.pinned()
            if self.state(plan) != index:
                raise Refusal('state-raced')
            self.journal(plan, events, 'before', move=index)
            row = plan['moves'][index]
            _read_at(self.rfd, row['source'], row['identity'])
            self.pinned()
            _rename_noreplace(self.rfd, row['source'], self.afd, row['destination'])
            os.fsync(self.rfd)
            os.fsync(self.afd)
            if self.state(plan) != index + 1:
                raise Refusal('post-rename-state')
            self.journal(plan, events, 'after', move=index)
        self.journal(plan, events, 'complete', state=2)
        return {'status': 'PASS', 'plan_sha256': sha(canonical(plan)),
                'journal': str(self.root / ARCHIVE / JOURNAL),
                'archives': [str(self.root / ARCHIVE / row['destination']) for row in plan['moves']]}


def _recover(failure, root, device, observe, execute=False):
    transaction = _Transaction(failure, root, device)
    try:
        return transaction.run(observe, execute)
    finally:
        transaction.close()


def recover(execute=False):
    return _recover(load_failure(), ROOT, 1831, observe_production, execute)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = recover(args.execute)
    except (Refusal, OSError) as exc:
        print(json.dumps({'status': 'REFUSED', 'reason': str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
