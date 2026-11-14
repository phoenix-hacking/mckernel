#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One NEW failed-validation exception. Never imports a normal release API, never
signals a numeric PID/group, and never modifies the permanent development mutex.
Only pure mock backends may run before a new exact Root/execution-review release.
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
import resource
import select
import signal
import stat
import time

PID, START, PARENT = 997661, '79134158', 842942
OWNER, OWNER_START = 998188, '79143668'
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
PROTECTED = (842942, 842940, 842938, 843517, 843520)
PERMANENT = Path('/run/lock/mckernel-development.lock')
SHARED = Path('/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock')
REFERENCE_SHA = '3fdb4dde4dbbd5d07d85d68c02e68d4aee3acca45dce12be3479f3252765abd6'
REFERENCE = Path('/home/holden/mckernel/scripts/native_exact_scratch22_authority1_quarantine_recovery.py')
DEADLINES = (1793030133, 812240.493656513, 827578.62070498)
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size',
          'st_mtime_ns', 'st_ctime_ns')


class Refusal(RuntimeError):
    pass


def need(condition, message):
    if not condition:
        raise Refusal(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refusal('nonfinite JSON')))


def protected_identity(rows):
    # Scheduling state is volatile; compare births/parents while checking that
    # every individual observation is positively alive, never zombie/exited.
    return {pid: {key: row[key] for key in ('pid', 'parent', 'starttime')}
            for pid, row in rows.items()}


def validate_packet(packet):
    need(packet['schema'] == 'owner15.failed-validation-recovery.v1', 'wrong recovery family')
    need(packet['target'] == dict(pid=PID, starttime=START, parent=PARENT, fd=3),
         'target is not the exact quarantined caller')
    need(PID not in PROTECTED and tuple(packet['protected_pids']) == PROTECTED,
         'protected model/watch controls differ')
    need(packet['owner'] == dict(pid=OWNER, starttime=OWNER_START, returncode=1),
         'failed owner identity differs')
    need(packet['boot_id'] == BOOT and tuple(packet['deadlines']) == DEADLINES,
         'fixed launch clock authority differs')
    need(packet['action_budget'] == dict(shared_unlink=1, pidfd_sigkill=1,
                                        numeric_signal=0, group_signal=0,
                                        normal_release=0, permanent_mutations=0),
         'action budget differs')
    expected = packet['shared_record']
    need(expected == dict(schema='mckernel.heavy-operation.v1', kind='image', pid=OWNER,
                          starttime=OWNER_START, boot_id=BOOT, device=1828, inode=116861,
                          request_sha256='576e75028709c54f3e644a6c2d15d542be2e4389e8814a35eebbea0820b58b50'),
         'shared canonical tuple differs')
    need(packet['shared_path'] == str(SHARED) and packet['permanent_path'] == str(PERMANENT),
         'record or permanent path differs')
    need(packet['expected_shared_bytes'] == 268, 'exact shared byte length differs')


def validate_snapshot(value, packet, shared_present, protected_baseline=None):
    """Pure gate over actual observations, also exercised by mock negatives."""
    need(value['boot_id'] == BOOT, 'boot differs')
    caller = value['caller']
    binding = packet['caller_binding']
    need(isinstance(binding, dict), 'exact full caller binding is still unqualified')
    need(caller == binding, 'full caller identity/argv/exe/FD differs')
    need(caller['pid'] == PID and caller['starttime'] == START and caller['parent'] == PARENT,
         'caller birth or parent differs')
    need(caller['uid'] == caller['gid'] == 1000 and caller['threads'] == 1
         and caller['children'] == [] and caller['pgid'] == caller['session'] == PID,
         'caller is not the sole childless process/session owner')
    need(caller['fd3_node'] == [27, 4] and caller['permanent_fds'] == [3],
         'sole FD3 permanent-node ownership differs')
    need(value['flocks'] == [['FLOCK', 'ADVISORY', 'WRITE', str(PID), '00:1b:4', '0', 'EOF']],
         'caller no longer holds sole permanent flock')
    need(value['owner_absent'] is True and value['absent_paths'] == packet['absent_paths'],
         'failed owner or a prevalidation-absent path exists')
    need(value['namespaces'] == packet['prepared_namespaces'], 'prepared directory identity differs')
    need(value['permanent'] == packet['permanent_identity'], 'permanent node differs')
    need(value['shared_present'] is shared_present, 'shared live-path state differs')
    need(set(value['protected']) == {str(pid) for pid in PROTECTED}, 'protected set differs')
    for pid, identity in value['protected'].items():
        need(identity['pid'] == int(pid) and identity['state'] not in ('Z', 'X', 'x'),
             'protected process is not positively alive')
    need(value['protected'][str(PARENT)]['starttime'] == packet['protected_model_starttime'],
         'protected parent model birth differs')
    if protected_baseline is not None:
        need(protected_identity(value['protected']) == protected_identity(protected_baseline),
             'protected process identity changed')


def recover(packet, ops):
    """Finite ordered protocol; Ops must not retry an uncertain mutation/signal."""
    validate_packet(packet)
    ops.authorize(packet)
    ops.verify_static_failure(packet)
    pidfd = ops.pidfd_open()
    shared_fd = None
    budget_consumed, signal_attempted, unlinked = False, False, False
    try:
        ops.bind_pidfd(pidfd)
        first = ops.snapshot(shared_present=True)
        validate_snapshot(first, packet, True)
        protected = first['protected']

        def checkpoint(label, present):
            ops.bind_pidfd(pidfd)
            current = ops.snapshot(shared_present=present)
            validate_snapshot(current, packet, present, protected)
            ops.check_clock()
            return current

        ops.claim_evidence()
        ops.publish('INITIAL-HELD-STATE.json', first)
        checkpoint('before-shared-open', True)
        shared_fd, record = ops.open_shared()
        need(record['raw_sha256'] == packet['expected_shared_sha256']
             and digest(bytes.fromhex(record['raw_hex'])) == packet['expected_shared_sha256']
             and record['value'] == packet['shared_record']
             and record['metadata'] == packet['shared_original_identity'],
             'shared record bytes/tuple/inode metadata differ')
        checkpoint('before-archive', True)
        archive = ops.archive_record(record)
        ops.verify_archive(archive)
        checkpoint('before-shared-unlink', True)
        ops.recheck_shared(shared_fd, linked=True)
        ops.publish('SHARED-UNLINK-BUDGET-CONSUMED.json',
                    dict(path=str(SHARED), record=record, archive=archive, calls_allowed=1))
        # Recheck after durable intent, immediately before the only unlink.
        checkpoint('immediate-shared-unlink', True)
        ops.recheck_shared(shared_fd, linked=True)
        unlinked = 'UNCERTAIN_CALL_ATTEMPTED'
        ops.unlink_shared(shared_fd)
        unlinked = True
        checkpoint('after-shared-unlink', False)
        ops.verify_archive(archive)
        ops.recheck_shared(shared_fd, linked=False)
        checkpoint('immediate-signal-budget', False)
        budget_consumed = True
        ops.publish('SIGNAL-BUDGET-CONSUMED.json',
                    dict(target=packet['target'], syscall=424, signal=9, calls_allowed=1,
                         shared_unlinked=True, archive=archive))
        # The durable consumed marker precedes this last authentication and the
        # actual call. Any exception from now on forbids another signal attempt.
        checkpoint('immediate-pidfd-signal', False)
        ops.verify_archive(archive)
        ops.recheck_shared(shared_fd, linked=False)
        signal_attempted = True
        signal_result = ops.sole_sigkill(pidfd)
        exit_proof = ops.exit_ready(pidfd)
        need(exit_proof.get('pidfd_exit_ready') is True, 'positive pidfd exit not proven')
        after = ops.postflight(protected, archive)
        result = dict(scope=SCOPE, status='FAILED_VALIDATION_RECOVERY',
                      local_postflight=True, Root_creator_join_and_group_postflight_pending=True,
                      target=packet['target'], owner=packet['owner'], archive=archive,
                      signal=signal_result, positive_exit=exit_proof, postflight=after,
                      action_budget_consumed=dict(shared_unlink=1, pidfd_sigkill=1),
                      normal_cleanup_credit=False, default_native_or_retirement_credit=False,
                      new_heavy_admission=False)
        ops.publish('FAILED-VALIDATION-RECOVERY.json', result)
        return result
    except BaseException as error:
        ops.preserve_failure(dict(scope=SCOPE, status='FAILED_VALIDATION_RECOVERY_HOLD',
                                  error=type(error).__name__ + ': ' + str(error),
                                  shared_unlinked=unlinked, signal_budget_consumed=budget_consumed,
                                  signal_attempted=signal_attempted, retry_authority=False,
                                  caller_lock_required_until_signal=not signal_attempted,
                                  new_heavy_admission=False))
        raise
    finally:
        if shared_fd is not None:
            ops.close(shared_fd)
        ops.close(pidfd)
        ops.finish()


def proc_bytes_complete(path, maximum=65536):
    """Preserve the reviewed flags/byte bound while consuming short reads to EOF."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        chunks, count = [], 0
        while True:
            # Reading one extra byte retains the original max+1 overflow oracle.
            # A nonempty short read is not EOF. Each iteration consumes at least
            # one byte or exits, so the original byte bound also bounds iterations.
            raw = os.read(fd, maximum + 1 - count)
            if not raw:
                return b''.join(chunks)
            count += len(raw)
            if count > maximum:
                raise Refusal('proc observation exceeds bound')
            chunks.append(raw)
    finally:
        os.close(fd)


def reviewed_algorithms():
    """Load definitions only; historical main/release/PID80259 never executes."""
    raw = REFERENCE.read_bytes()
    need(len(raw) == 28680 and digest(raw) == REFERENCE_SHA, 'historical algorithm source differs')
    names = {'sha', 'canonical', 'strict', 'directory', 'file_identity', 'proc_bytes', 'proc_stat',
             'boot_check', 'guard_identity', 'lock_rows', 'require_lock_holder',
             'pidfd_open', 'bind_pidfd', 'sole_sigkill', 'exit_ready'}
    nodes = [node for node in ast.parse(raw).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    need({node.name for node in nodes} == names, 'reviewed algorithm extraction differs')
    namespace = dict(ctypes=ctypes, hashlib=hashlib, json=json, os=os, Path=Path, re=re,
                     select=select, signal=signal, stat=stat, time=time, Refusal=Refusal,
                     PID=PID, START=START, PARENT=PARENT, BOOT=BOOT,
                     SMALL_LIMIT=1 << 20, FILE_LIMIT=32 << 20)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(REFERENCE), 'exec'), namespace)
    # Only observer transport changes; exact identity/soleholder/action algorithms stay unchanged.
    namespace['proc_bytes'] = proc_bytes_complete
    return namespace


class LocalOps:
    """Real adapter. Constructed only by gated CLI; never by pure mock tests."""
    def __init__(self, packet, packet_sha, grant_path, grant_sha, review_path, review_sha):
        self.packet, self.grant_path, self.grant_sha = packet, grant_path, grant_sha
        self.packet_sha = packet_sha
        self.review_path, self.review_sha = review_path, review_sha
        self.ns = reviewed_algorithms()
        self.evidence = Path(packet['action_root'])
        self.evidence_fd = None
        self.shared_parent = None
        self.shared_original = None
        self.shared_unlink_called = False
        self.signal_called = False
        self.granted = False

    def pinned(self, row, keep=False):
        actual, raw = self.ns['file_identity'](Path(row['path']), keep=keep, maximum=32 << 20)
        need(actual['sha256'] == row['sha256'] and actual['size'] == row['bytes'],
             'immutable input differs: ' + row['path'])
        return raw if keep else actual

    def authorize(self, packet):
        need(os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000,
             'ordinary holden execution required')
        need(os.uname().machine == 'x86_64' and os.sched_getaffinity(0) == {7},
             'exact x86_64 ordinary control CPU7 required')
        need(resource.getrlimit(resource.RLIMIT_CPU) == (resource.RLIM_INFINITY,) * 2,
             'no inherited outer CPU kill during mutation')
        need(resource.getrlimit(resource.RLIMIT_AS)[0] == 2 << 30, 'exact 2GiB address-space profile')
        grant_raw = self.grant_path.read_bytes()
        review_raw = self.review_path.read_bytes()
        need(digest(grant_raw) == self.grant_sha and digest(review_raw) == self.review_sha,
             'exact new grant/review hashes required')
        grant, review = strict(grant_raw), strict(review_raw)
        need(grant.get('authority') == '/root' and grant.get('decision') == 'GRANT_FAILED_VALIDATION_RECOVERY_ONCE'
             and grant.get('execution_count') == 1 and grant.get('packet_sha256') == self.packet_sha
             and grant.get('review_sha256') == self.review_sha
             and grant.get('source_sha256') == digest(Path(__file__).read_bytes()), 'new exact Root grant required')
        need(review.get('decision') == 'PASS_FAILED_VALIDATION_RECOVERY_EXECUTION'
             and review.get('implementation_ownership') is False
             and review.get('reviewer') not in ('/root', '', None)
             and review.get('packet_sha256') == grant['packet_sha256']
             and review.get('source_sha256') == grant['source_sha256'], 'independent exact execution review required')
        need(packet['caller_binding'] is not None, 'full exact caller binding not prepared')
        self.check_clock()
        self.granted = True

    def verify_static_failure(self, packet):
        need(self.granted, 'actions are not granted')
        for row in packet['immutable_inputs']:
            self.pinned(row)
        refs = strict(self.pinned(packet['references'], keep=True))
        join = strict(self.pinned(refs['owner_join'], keep=True))
        need(join['pid'] == OWNER and join['starttime'] == OWNER_START and join['returncode'] == 1
             and all(join[key] is True for key in ('direct_child_joined', 'group_absent', 'closed_streams'))
             and join['error'] is None and join['retirement_error'] is None, 'raw failed-owner join differs')
        stderr = self.pinned(refs['owner_stderr'], keep=True)
        need(stderr.endswith(b'__main__.OwnerError: common exclusion path differs or is retired\n')
             and b'line 1996, in _reuse_validate_request_base' in stderr
             and b'bound = self.validate()' in stderr, 'actual prevalidation failure differs')
        quarantine = strict(self.pinned(refs['quarantine'], keep=True))
        need(quarantine['holder_pid'] == PID and quarantine['holder_fd'] == 3
             and quarantine['owner_joined'] is True and quarantine['owner_started'] is True,
             'retained exact caller quarantine differs')
        # The independent execution review binds packet/source proof hashes:
        # acquire at 2175 precedes validate at 2177; common/attempt/lease/Docker
        # follow at 2184/2191/2194/2195. No owner receipt is invented or required.

    def check_clock(self):
        need(time.time() < DEADLINES[0] and time.monotonic() < DEADLINES[1]
             and time.clock_gettime(time.CLOCK_BOOTTIME) < DEADLINES[2], 'fixed window ended')

    def pidfd_open(self):
        need(self.granted, 'pidfd operation not granted')
        return self.ns['pidfd_open']()

    def bind_pidfd(self, fd):
        return self.ns['bind_pidfd'](fd, dict(bound_guard=self.packet['caller_binding']['guard']))

    def node(self, path):
        row = os.lstat(path)
        return dict(device=row.st_dev, inode=row.st_ino, mode=stat.S_IMODE(row.st_mode),
                    uid=row.st_uid, gid=row.st_gid, nlink=row.st_nlink, size=row.st_size)

    def namespaces(self):
        rows = []
        for expected in self.packet['prepared_namespaces']:
            path = Path(expected['path'])
            fd = self.ns['directory'](path)
            try:
                meta = os.fstat(fd)
                rows.append(dict(path=str(path), device=meta.st_dev, inode=meta.st_ino,
                                 mode=stat.S_IMODE(meta.st_mode), uid=meta.st_uid, gid=meta.st_gid,
                                 entries=sorted(os.listdir(fd))))
            finally:
                os.close(fd)
        return rows

    def absent(self):
        rows = []
        for name in self.packet['absent_paths']:
            try:
                os.lstat(name)
            except FileNotFoundError:
                rows.append(name)
            else:
                raise Refusal('prevalidation path now exists: ' + name)
        try:
            os.lstat('/proc/%d' % OWNER)
        except FileNotFoundError:
            return rows
        raise Refusal('failed owner PID present or reused; no recovery authority')

    def protected(self):
        rows = {}
        for pid in PROTECTED:
            fields = self.ns['proc_stat'](pid)
            rows[str(pid)] = dict(pid=pid, parent=int(fields[1]), starttime=fields[19], state=fields[0])
        return rows

    def caller(self):
        binding = self.packet['caller_binding']
        actual = self.ns['guard_identity'](dict(bound_guard=binding['guard']))
        fields = self.ns['proc_stat'](PID)
        children = self.ns['proc_bytes']('/proc/%d/task/%d/children' % (PID, PID)).split()
        need(len(os.listdir('/proc/%d/task' % PID)) == 1, 'task count differs')
        lock_fds = []
        for item in os.listdir('/proc/%d/fd' % PID):
            need(item.isdigit(), 'unknown caller FD entry')
            row = os.stat('/proc/%d/fd/%s' % (PID, item))
            if (row.st_dev, row.st_ino) == (27, 4):
                lock_fds.append(int(item))
        fd3 = os.stat('/proc/%d/fd/3' % PID)
        actual.update(children=[int(pid) for pid in children], pgid=int(fields[2]),
                      session=int(fields[3]), fd3_node=[fd3.st_dev, fd3.st_ino],
                      permanent_fds=sorted(lock_fds), guard=binding['guard'])
        return actual

    def snapshot(self, shared_present):
        actual_shared = os.path.lexists(SHARED)
        return dict(boot_id=self.ns['proc_bytes']('/proc/sys/kernel/random/boot_id', 128).decode().strip(),
                    caller=self.caller(), flocks=self.ns['require_lock_holder'](PID),
                    owner_absent=True, absent_paths=self.absent(), namespaces=self.namespaces(),
                    permanent=self.node(PERMANENT), shared_present=actual_shared,
                    protected=self.protected())

    def held(self):
        self.ns['guard_identity'](dict(bound_guard=self.packet['caller_binding']['guard']))
        self.ns['require_lock_holder'](PID)
        self.check_clock()

    def claim_evidence(self):
        self.held()
        parent = self.ns['directory'](self.evidence.parent)
        try:
            os.mkdir(self.evidence.name, 0o700, dir_fd=parent)
            os.fsync(parent)
        finally:
            os.close(parent)
        self.evidence_fd = self.ns['directory'](self.evidence)

    def publish_bytes(self, name, raw, require_held=True):
        need(self.evidence_fd is not None and Path(name).name == name, 'unclaimed evidence/name')
        if require_held:
            self.held()
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=self.evidence_fd)
        try:
            pending = memoryview(raw)
            while pending:
                count = os.write(fd, pending)
                need(count > 0, 'durable evidence write made no progress')
                pending = pending[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.evidence_fd)

    def publish(self, name, value):
        self.publish_bytes(name, canonical(value) + b'\n',
                           require_held=name not in ('FAILED-VALIDATION-RECOVERY.json', 'FAILURE-HOLD.json'))

    def read_shared_fd(self, fd):
        before = os.fstat(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        raw = os.read(fd, 269)
        after = os.fstat(fd)
        need(all(getattr(before, key) == getattr(after, key) for key in FIELDS), 'shared FD changed')
        return before, raw

    def open_shared(self):
        self.held()
        self.shared_parent = self.ns['directory'](SHARED.parent)
        fd = os.open(SHARED.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                     dir_fd=self.shared_parent)
        try:
            meta, raw = self.read_shared_fd(fd)
            need(stat.S_ISREG(meta.st_mode) and meta.st_dev == 1828 and meta.st_ino == 116861
                 and meta.st_uid == meta.st_gid == 1000 and stat.S_IMODE(meta.st_mode) == 0o600
                 and meta.st_nlink == 1 and meta.st_size == len(raw) == 268, 'shared node shape differs')
            linked = os.stat(SHARED.name, dir_fd=self.shared_parent, follow_symlinks=False)
            need(all(getattr(meta, key) == getattr(linked, key) for key in FIELDS), 'shared pathname differs')
            self.shared_original = dict(fields={key: getattr(meta, key) for key in FIELDS},
                                        full_fstat={name: getattr(meta, name) for name in dir(meta)
                                                    if name.startswith('st_') and isinstance(getattr(meta, name), (int, float))},
                                        raw=raw)
            full_lstat = {name: getattr(linked, name) for name in dir(linked)
                          if name.startswith('st_') and isinstance(getattr(linked, name), (int, float))}
            return fd, dict(raw_hex=raw.hex(), raw_sha256=digest(raw), value=strict(raw),
                            metadata=self.shared_original['fields'], full_fstat=self.shared_original['full_fstat'],
                            full_lstat=full_lstat)
        except BaseException:
            os.close(fd)
            raise

    def recheck_shared(self, fd, linked):
        meta, raw = self.read_shared_fd(fd)
        need(raw == self.shared_original['raw'] and meta.st_dev == 1828 and meta.st_ino == 116861,
             'shared retained FD bytes/node differs')
        if linked:
            row = os.stat(SHARED.name, dir_fd=self.shared_parent, follow_symlinks=False)
            need(all(getattr(meta, key) == self.shared_original['fields'][key]
                     and getattr(meta, key) == getattr(row, key) for key in FIELDS),
                 'shared live path/FD identity differs before unlink')
        else:
            need(meta.st_nlink == 0 and not os.path.lexists(SHARED), 'shared unlink not positively observed')

    def archive_record(self, record):
        self.publish_bytes('SHARED-RECORD.ORIGINAL-BYTES', bytes.fromhex(record['raw_hex']))
        self.publish('SHARED-RECORD.ORIGINAL-METADATA.json', record)
        return dict(bytes_path=str(self.evidence / 'SHARED-RECORD.ORIGINAL-BYTES'),
                    metadata_path=str(self.evidence / 'SHARED-RECORD.ORIGINAL-METADATA.json'),
                    raw_sha256=record['raw_sha256'], metadata_sha256=digest(canonical(record) + b'\n'))

    def verify_archive(self, archive):
        for name, sha in ((archive['bytes_path'], archive['raw_sha256']),
                          (archive['metadata_path'], archive['metadata_sha256'])):
            row, _ = self.ns['file_identity'](Path(name), maximum=1 << 20)
            need(row['sha256'] == sha and row['uid'] == row['gid'] == 1000
                 and row['mode'] == 0o600, 'durable archive verification differs')

    def unlink_shared(self, fd):
        need(not self.shared_unlink_called, 'shared unlink budget already consumed')
        self.held()
        self.recheck_shared(fd, linked=True)
        self.shared_unlink_called = True
        os.unlink(SHARED.name, dir_fd=self.shared_parent)
        os.fsync(self.shared_parent)
        self.recheck_shared(fd, linked=False)

    def sole_sigkill(self, fd):
        need(not self.signal_called, 'signal budget already consumed; no retry')
        self.signal_called = True
        return self.ns['sole_sigkill'](fd)

    def exit_ready(self, fd):
        return self.ns['exit_ready'](fd)

    def postflight(self, protected_baseline, archive):
        self.ns['boot_check']()
        protected = self.protected()
        need(all(row['state'] not in ('Z', 'X', 'x') for row in protected.values())
             and protected_identity(protected) == protected_identity(protected_baseline),
             'protected process identity changed')
        self.absent()
        need(self.namespaces() == self.packet['prepared_namespaces'], 'prepared directory changed')
        need(not os.path.lexists(SHARED), 'shared path reappeared')
        self.verify_archive(archive)
        free = []
        for _ in range(2):
            need(self.node(PERMANENT) == self.packet['permanent_identity'], 'permanent node changed')
            parent = self.ns['directory'](PERMANENT.parent)
            fd = None
            try:
                fd = os.open(PERMANENT.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
                             dir_fd=parent)
                row = os.fstat(fd)
                need((row.st_dev, row.st_ino) == (27, 4), 'permanent open identity differs')
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                need(self.ns['lock_rows']() == [['FLOCK', 'ADVISORY', 'WRITE', str(os.getpid()),
                                                '00:1b:4', '0', 'EOF']], 'new permanent holder appeared')
                free.append(dict(device=27, inode=4, nonblocking_acquired=True))
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                if fd is not None:
                    os.close(fd)
                os.close(parent)
        need(self.ns['lock_rows']() == [], 'permanent lock not free after probes')
        return dict(permanent_unchanged_free_observations=free, shared_absent=True,
                    protected=protected_baseline, archive_valid=True,
                    Root_tool10088_join_and_group_absence='EXTERNAL_PENDING')

    def preserve_failure(self, value):
        if self.evidence_fd is not None:
            self.publish('FAILURE-HOLD.json', value)

    def close(self, fd):
        os.close(fd)

    def finish(self):
        for fd in (self.shared_parent, self.evidence_fd):
            if fd is not None:
                os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', required=True, type=Path)
    parser.add_argument('--packet-sha256', required=True)
    parser.add_argument('--root-grant', required=True, type=Path)
    parser.add_argument('--root-grant-sha256', required=True)
    parser.add_argument('--execution-review', required=True, type=Path)
    parser.add_argument('--execution-review-sha256', required=True)
    parser.add_argument('--execute', action='store_true', required=True)
    args = parser.parse_args()
    raw = args.packet.read_bytes()
    need(digest(raw) == args.packet_sha256, 'exact frozen packet bytes required')
    packet = strict(raw)
    ops = LocalOps(packet, args.packet_sha256, args.root_grant, args.root_grant_sha256,
                   args.execution_review, args.execution_review_sha256)
    recover(packet, ops)


if __name__ == '__main__':
    main()
