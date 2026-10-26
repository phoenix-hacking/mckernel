"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

UNRELEASED persistent keeper/phase-bootstrap source. No runnable root main.
Root must independently release the exact keeper/capture and separately bind
retirement authorization. A held FD is never replaced by JSON evidence.
"""
import ctypes
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import select
import signal
import stat
import time

HERE = Path(__file__).resolve().parent
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
WALL_CUTOFF = 1793030133  # 2026-10-26T15:55:33Z, fixed parent window.
BOOT_CUTOFF = 827578.62070498
MONOTONIC_CUTOFF = 812240.493656513
COLLECTOR_REFERENCE = dict(path='/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current290-process-census-lifecycle-correction-source-1/census-runtime-bridge-source-1/census_runtime_bridge.py', bytes=8758, sha256='c9af3506af824af58c599a2aa8d7a1aae30b680a25c4bcc5ca87b8bcd1d20a2a')
FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')


class Refusal(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_module(path, expected):
    raw = path.read_bytes()
    need(sha(raw) == expected, 'keeper-source-binding:' + path.name)
    spec = importlib.util.spec_from_file_location('_keeper_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def require_launch(packet, raw_sha):
    need(packet.get('schema') == 'mckernel.current290.held-custody-keeper-source.v1'
         and packet.get('mode') == 'STANDBY_ONLY_UNTIL_SEPARATE_RETIREMENT_AUTH'
         and packet.get('author') == '/root', 'keeper-launch-binding')
    need(packet.get('old_actor') == dict(pid=1060806, starttime='80309560', fd=3,
               parent=1060803, pgid=1060803, boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'),
         'keeper-exact-old-root-actor')
    need(packet.get('original_outer_caller') == dict(pid=1060802, starttime='80309549')
         and packet.get('tool_session_id') == 65524, 'keeper-exact-original-outer-tool')
    need(packet.get('old_release_sha256') == '9c7589afa411c1b40fe02777facf69007b885d228632b12c3f34e5a091b517e9'
         and packet.get('old_plan_canonical_sha256') == '279b40f40ae69255914c064e92486fdfbb65ad798077206dc9c598d185e277f8',
         'keeper-old-release-plan-binding')
    need(packet.get('fixed_cutoffs') == [WALL_CUTOFF, MONOTONIC_CUTOFF, BOOT_CUTOFF], 'keeper-fixed-window')
    need(type(packet.get('standby_seconds')) in (int, float) and 0 < packet['standby_seconds'] <= 120,
         'keeper-pre-retirement-standby-bound')
    need(isinstance(raw_sha, str) and len(raw_sha) == 64, 'keeper-launch-raw-hash')
    need(packet.get('collector_reference') in (None, COLLECTOR_REFERENCE), 'collector-reference-not-exact-reviewed-bridge')
    need(packet.get('execution_release', {}).get('status') == 'PASS_EXECUTION_RELEASE'
         and packet['execution_release'].get('reviewer') not in (None, '', '/root')
         and packet['execution_release'].get('evidence_sha256'), 'keeper-independent-execution-release-required')
    return True


class Keeper:
    """Finite acquisition/retirement protocol; held post-retirement state persists.

    LocalOps is the concrete future adapter. Tests use disjoint ordinary private
    fixtures/mocks. This class neither invents an execution grant nor retries a
    signal, uncertain mutation, or consumed Root command.
    """
    def __init__(self, packet, raw_sha, ops):
        require_launch(packet, raw_sha)
        self.packet, self.raw_sha, self.ops = packet, raw_sha, ops
        self.custody = None
        self.state = 'NOT_ACQUIRED'
        self.retirement_intent_consumed = False
        self.signal_call_attempted = False
        self.command_consumed = False
        self.deadline = None
        self.configured = None
        self.tx = None

    def start(self):
        need(self.state == 'NOT_ACQUIRED', 'keeper-acquire-once')
        self.ops.clock_check()
        self.ops.capture_process(self.packet, self.raw_sha)
        self.custody = self.ops.acquire()
        if not self.custody.verified:
            self.state = 'HELD_UNVERIFIED_QUARANTINE'
            self.ops.publish('UNVERIFIED-CUSTODY-HOLD.json', dict(error=self.custody.error, retry=False))
            return self.state
        self.custody.verify_old_alive()
        self.ops.publish('HELD-CUSTODY.json', self.custody.proof)
        self.deadline = self.ops.now() + self.packet['standby_seconds']
        self.state = 'VERIFIED_STANDBY'
        return self.state

    def expire_before_retirement(self):
        need(self.state == 'VERIFIED_STANDBY' and not self.retirement_intent_consumed,
             'keeper-expire-before-retirement-only')
        need(self.ops.now() >= self.deadline, 'keeper-standby-deadline-not-reached')
        try:
            self.custody.verify_old_alive()
            self.ops.publish('PRE-RETIREMENT-DEADLINE-OLD-ACTOR-ALIVE.json', dict(new_copy_only=True, old_actor=self.packet['old_actor']))
            # Immediate repeated genuine old-holder verification follows durable
            # intent; no old actor signal/close/unlock exists on this path.
            self.custody.verify_old_alive()
            self.custody.close_new_copy_while_old_alive()
            self.state = 'CLOSED_NEW_COPY_OLD_ACTOR_RETAINED'
        except BaseException as error:
            self.state = 'HELD_QUARANTINE'
            self.ops.publish('PRE-RETIREMENT-DEADLINE-HOLD.json', dict(error=str(error), old_actor_unknown=True, custody_retained=True))
        return self.state

    def retire(self, command):
        need(self.state == 'VERIFIED_STANDBY' and not self.command_consumed,
             'keeper-retirement-once-from-verified-standby')
        self.ops.clock_check()
        need(self.ops.now() < self.deadline, 'keeper-retirement-command-after-deadline')
        self.ops.authorize_retirement(command, self.packet, self.raw_sha)
        self.custody.verify_old_alive()
        # Full original source/normal/typed/metadata checks with exactly the
        # authenticated completed-common archive alias; zero mutation here.
        self.configured = self.ops.configure_phase()
        self.custody.verify_old_alive()
        self.ops.clock_check()
        need(self.ops.now() < self.deadline, 'keeper-after-configure-retirement-deadline')
        self.command_consumed = True
        self.retirement_intent_consumed = True  # Before durable intent OR signal call.
        self.state = 'RETIREMENT_ATTEMPTED_CUSTODY_HELD'
        try:
            self.ops.publish('RETIREMENT-BUDGET-CONSUMED.json', dict(launch_sha256=self.raw_sha,
                             command_sha256=sha(canonical(command)), target=self.packet['old_actor'],
                             budget_intent_consumed=True, pidfd_sigkill_calls_allowed=1,
                             pidfd_sigkill_calls_attempted=0, numeric_or_group_signal_calls=0))
            self.custody.verify_old_alive()
            self.ops.clock_check()
            need(self.ops.now() < self.deadline, 'keeper-immediate-signal-retirement-deadline')
            self.signal_call_attempted = True
            self.ops.sole_pidfd_sigkill(self.custody.pidfd)
            exit_proof = self.ops.positive_pidfd_exit(self.custody.pidfd)
            need(exit_proof.get('pidfd_exit_ready') is True, 'keeper-positive-old-root-pidfd-exit')
            self.custody.verify_held_after_exit()
            self.ops.publish('OLD-ROOT-POSITIVE-PIDFD-EXIT.json', exit_proof)
            self.state = 'OLD_ROOT_EXITED_AWAITING_ORIGINAL_JOINS'
        except BaseException as error:
            self.state = 'HELD_QUARANTINE'
            self.ops.publish('RETIREMENT-UNCERTAINTY-HOLD.json', dict(error=str(error), custody_retained=True,
                             retry=False, signal_call_attempted=self.signal_call_attempted,
                             original_root_may_have_exited=True))
        return self.state

    def adopt_after_joins(self, receipt):
        need(self.state == 'OLD_ROOT_EXITED_AWAITING_ORIGINAL_JOINS', 'keeper-original-root-positive-exit-first')
        try:
            receipt = self.ops.authorize_join_receipt(receipt, self.packet, self.raw_sha)
            self.custody.verify_held_after_exit()
            self.tx = self.ops.bootstrap(self.configured, self.custody, receipt, self.packet)
            self.custody.verify_held_after_exit()
            self.ops.publish('PHASE-BOOTSTRAP-READY-CUSTODY-HELD.json', dict(old_plan_unmodified=True,
                             old_journal_prefix_events=4, remaining_indices=[1], cleanup_executed=False))
            self.state = 'PHASE_BOOTSTRAP_READY_CUSTODY_HELD'
        except BaseException as error:
            self.state = 'HELD_QUARANTINE'
            self.ops.publish('ADOPTION-HOLD.json', dict(error=str(error), custody_retained=True, retry=False))
        return self.state

    def serve(self, next_command):
        """Persistent sourceable keeper. Future reviewed wrapper supplies commands.

        No implicit exit/close after retirement or uncertainty. The source-only
        shared mutator is deliberately absent; final release is a later owner.
        """
        try:
            self.start()
            while True:
                if self.state == 'VERIFIED_STANDBY' and self.ops.now() >= self.deadline:
                    self.expire_before_retirement()
                if self.state == 'CLOSED_NEW_COPY_OLD_ACTOR_RETAINED':
                    return self.state
                command = next_command()
                if command is not None:
                    if command.get('operation') == 'RETIRE_EXACT_OLD_ROOT_PIDFD_ONLY':
                        self.retire(command)
                    elif command.get('operation') == 'ADOPT_AFTER_POSITIVE_ORIGINAL_JOINS':
                        self.adopt_after_joins(command['receipt'])
                    else:
                        raise Refusal('keeper-unknown-command')
                self.ops.sleep(0.2)
        except BaseException as error:
            # Keeper never exits/auto-closes a held post-copy FD on any exception.
            if self.custody is None:
                raise
            self.state = 'HELD_QUARANTINE'
            try:
                self.ops.publish('KEEPER-EXCEPTION-HOLD.json', dict(error=str(error), custody_retained=True))
            finally:
                self.ops.quarantine_wait()


class LocalCustody:
    """Concrete real held-FD adapter; no target operation is invoked on import."""
    def __init__(self, module, hold):
        self.module, self.p = module, module.adoption()
        self.fd, self.pidfd = hold.fd, hold.pidfd
        self.verified, self.error, self.proof = hold.verified, hold.error, hold.proof
        self.metadata = {field: getattr(os.fstat(self.fd), field) for field in FIELDS}
        self.closed = False

    def verify_old_alive(self):
        need(not self.closed and self.verified, 'keeper-private-copy-not-verified-held')
        self.module.actor_binding(self.p)
        self.module.live_pidfd(self.p, self.pidfd)
        self.p.verify_description_custody(self.fd, self.module.PID, self.module.TARGET_FD,
                                         self.p.ROOT_MUTEX, self.metadata)
        self.module.live_pidfd(self.p, self.pidfd)
        self.module.actor_binding(self.p)
        return True

    def verify_held_after_exit(self):
        need(not self.closed and self.verified, 'keeper-copy-not-held-after-exit')
        poller = select.poll()
        poller.register(self.pidfd, select.POLLIN)
        need(any(fd == self.pidfd and mask & select.POLLIN for fd, mask in poller.poll(0)),
             'keeper-positive-pidfd-exit-not-current')
        current, named = os.fstat(self.fd), os.stat(self.p.ROOT_MUTEX, follow_symlinks=False)
        need(all(getattr(current, key) == self.metadata[key] == getattr(named, key) for key in FIELDS),
             'keeper-held-copy-or-permanent-node-changed')
        need(fcntl.fcntl(self.fd, fcntl.F_GETFL) & os.O_ACCMODE == os.O_RDONLY
             and not os.get_inheritable(self.fd), 'keeper-private-readonly-held-copy')
        wanted = ['FLOCK', 'ADVISORY', 'WRITE', str(self.module.PID), '00:1b:4', '0', 'EOF']
        need(self.p.description_lock_rows(os.getpid(), self.fd) == [wanted], 'keeper-postexit-description-lock')
        global_rows = [line.split()[1:] for line in Path('/proc/locks').read_text().splitlines() if '00:1b:4' in line.split()]
        need(global_rows == [wanted], 'keeper-postexit-global-lock')
        after = os.fstat(self.fd)
        need(all(getattr(after, key) == self.metadata[key] for key in FIELDS), 'keeper-postexit-fd-raced')
        return True

    def close_new_copy_while_old_alive(self):
        self.verify_old_alive()
        os.close(self.fd)  # No LOCK_UN: duplicated descriptions share lock state.
        self.closed = True
        os.close(self.pidfd)


class LocalOps:
    """Concrete keeper operations; Root must release its wrapper/capture first."""
    def __init__(self, packet, raw_packet, evidence):
        require_launch(packet, sha(raw_packet))
        self.packet, self.raw_packet, self.evidence = packet, raw_packet, evidence
        self.custody_module = source_module(HERE / 'fixed_root_custody_standby.WITH-OUTER.SOURCE-ONLY.py', packet['source_hashes']['custody'])
        self.phase = source_module(HERE / 'phase_bootstrap.SOURCE-ONLY.py', packet['source_hashes']['phase'])
        need(sha(Path(__file__).read_bytes()) == packet['source_hashes']['keeper'], 'keeper-exact-own-source')
        self.p = self.phase.adoption()
        self.engine = None
        self.signal_attempted = False
        self.evidence_fd = None
        self.saved_signal_mask = None

    def now(self):
        return time.monotonic()

    def clock_check(self):
        need(time.time() < WALL_CUTOFF and time.monotonic() < MONOTONIC_CUTOFF
             and time.clock_gettime(time.CLOCK_BOOTTIME) < BOOT_CUTOFF, 'keeper-fixed-parent-window-ended')

    def capture_process(self, packet, raw_sha):
        # Actual execution wrapper must pre-create this reviewed disjoint output
        # directory and bind it in the exact grant. Open through no-follow walk.
        engine = self.phase.original_engine(self.p)
        self.evidence_fd, _ = engine.directory(self.evidence)
        meta = os.fstat(self.evidence_fd)
        expected = packet['evidence_directory_identity']
        need([meta.st_dev, meta.st_ino, meta.st_uid, meta.st_gid, stat.S_IMODE(meta.st_mode)] == expected,
             'keeper-exact-evidence-directory')
        need(os.listdir(self.evidence_fd) == [], 'keeper-evidence-directory-not-empty')
        rawstat = Path('/proc/self/stat').read_bytes()
        start = rawstat.rpartition(b') ')[2].split()[19].decode()
        self.self_identity = dict(pid=os.getpid(), starttime=start, pgid=os.getpgrp())
        self.publish('PROCESS.json', dict(scope=SCOPE, keeper=self.self_identity,
                     command_hex=Path('/proc/self/cmdline').read_bytes().hex(), launch_sha256=raw_sha,
                     source_hashes=packet['source_hashes'], old_actor=packet['old_actor']))
        self.saved_signal_mask = signal.pthread_sigmask(signal.SIG_BLOCK,
                                    {signal.SIGHUP, signal.SIGINT, signal.SIGTERM, signal.SIGQUIT})

    def acquire(self):
        hold = self.custody_module.acquire_exact_standby()
        return LocalCustody(self.custody_module, hold)

    def publish_bytes(self, name, raw):
        need(self.evidence_fd is not None and Path(name).name == name and len(raw) <= 1 << 20,
             'keeper-evidence-bound')
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.evidence_fd)
        try:
            os.fchown(fd, 1000, 1000)
            remaining = raw
            while remaining:
                count = os.write(fd, remaining)
                need(count > 0, 'keeper-evidence-no-progress')
                remaining = remaining[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(self.evidence_fd)
        return dict(path=str(self.evidence / name), bytes=len(raw), sha256=sha(raw))

    def publish(self, name, value):
        return self.publish_bytes(name, canonical(value) + b'\n')

    def configure_phase(self):
        self.engine = self.phase.original_engine(self.p)
        configured = self.phase.configure_phase_aware(self.p, self.engine)
        need(self.packet.get('collector_reference') == COLLECTOR_REFERENCE, 'keeper-new-diagnostic-collector-reference-required')
        authorization = self.pinned_document(self.packet.get('collector_delta_authorization'))
        manifest = self.phase.bind_diagnostic_census(self.p, self.engine, authorization)
        self.publish('DIAGNOSTIC-CENSUS-COMPOSITION.json', manifest)
        configured['diagnostic_composition_manifest'] = manifest
        return configured

    def pinned_document(self, ref):
        need(isinstance(ref, dict) and set(ref) == {'path', 'bytes', 'sha256'}, 'keeper-document-reference')
        raw = self.p.pinned_bytes(Path(ref['path']), ref['sha256'], ref['bytes'])
        return self.p.strict(raw)

    def authorize_retirement(self, command, packet, raw_sha):
        # The reviewed Root wrapper delivers this NEW command over its owned
        # channel only after actual standby evidence. No writable-file watcher,
        # inherited/consumed grant, or automatically created grant is accepted.
        need(isinstance(command, dict) and set(command) == {'operation', 'root_grant', 'independent_execution_review'}
             and command['operation'] == 'RETIRE_EXACT_OLD_ROOT_PIDFD_ONLY',
             'keeper-separate-root-retirement-auth-required')
        grant = self.pinned_document(command['root_grant'])
        review = self.pinned_document(command['independent_execution_review'])
        need(grant.get('operation') == 'RETIRE_EXACT_OLD_ROOT_PIDFD_ONLY'
             and grant.get('author') == '/root' and grant.get('keeper') == self.self_identity
             and grant.get('launch_sha256') == raw_sha and grant.get('target') == packet['old_actor']
             and grant.get('source_hashes') == packet['source_hashes']
             and grant.get('pidfd_sigkill_budget') == 1 and grant.get('numeric_or_group_signal_budget') == 0,
             'keeper-exact-root-retirement-grant')
        need(review.get('status') == 'PASS_EXECUTION_RELEASE' and review.get('reviewer') not in (None, '', '/root')
             and review.get('root_grant_sha256') == command['root_grant']['sha256']
             and review.get('source_hashes') == packet['source_hashes'], 'keeper-independent-retirement-release')

    def sole_pidfd_sigkill(self, pidfd):
        need(not self.signal_attempted, 'keeper-pidfd-signal-budget-consumed')
        self.signal_attempted = True
        libc = ctypes.CDLL(None, use_errno=True)
        libc.syscall.restype = ctypes.c_long
        result = libc.syscall(ctypes.c_long(424), ctypes.c_int(pidfd), ctypes.c_int(signal.SIGKILL),
                              ctypes.c_void_p(0), ctypes.c_uint(0))
        if result != 0:
            raise OSError(ctypes.get_errno(), 'keeper-pidfd-send-signal-no-retry')
        return result

    def positive_pidfd_exit(self, pidfd):
        poller = select.poll()
        poller.register(pidfd, select.POLLIN)
        events = poller.poll(5000)
        need(any(fd == pidfd and mask & select.POLLIN for fd, mask in events), 'keeper-old-root-exit-deadline')
        return dict(target=self.packet['old_actor'], pidfd_exit_ready=True,
                    original_outer_creator_joins_pending=True)

    def authorize_join_receipt(self, receipt, packet, raw_sha):
        need(isinstance(receipt, dict) and set(receipt) == {'receipt', 'root_grant', 'independent_execution_review'},
             'keeper-separate-root-original-join-auth-required')
        actual = self.pinned_document(receipt['receipt'])
        grant = self.pinned_document(receipt['root_grant'])
        review = self.pinned_document(receipt['independent_execution_review'])
        need(grant.get('operation') == 'ADOPT_AFTER_POSITIVE_ORIGINAL_JOINS'
             and grant.get('author') == '/root' and grant.get('keeper') == self.self_identity
             and grant.get('launch_sha256') == raw_sha and grant.get('target') == packet['old_actor']
             and grant.get('source_hashes') == packet['source_hashes']
             and grant.get('receipt_sha256') == receipt['receipt']['sha256'], 'keeper-exact-root-original-join-grant')
        need(review.get('status') == 'PASS_EXECUTION_RELEASE' and review.get('reviewer') not in (None, '', '/root')
             and review.get('root_grant_sha256') == receipt['root_grant']['sha256']
             and review.get('source_hashes') == packet['source_hashes'], 'keeper-independent-original-join-release')
        self.phase.require_retirement_and_joins(self.p, actual, packet)
        return actual

    def archive_original_quarantine(self, path, raw):
        need(self.engine.read_bounded(path) == raw and sha(raw) == self.p.QUARANTINE_SHA,
             'keeper-original-quarantine-bytes')
        metadata = self.engine.observe_identity(path)
        bytes_ref = self.publish_bytes('ORIGINAL-QUARANTINE.BYTES', raw)
        metadata_ref = self.publish('ORIGINAL-QUARANTINE.METADATA.json', metadata)
        need(self.engine.read_bounded(path) == raw and self.engine.observe_identity(path) == metadata,
             'keeper-original-quarantine-raced-during-archive')
        return dict(original_preserved=True, bytes=bytes_ref, metadata=metadata_ref)

    def bootstrap(self, configured, custody, receipt, packet):
        return self.phase.bootstrap_held_transaction(self.p, self.engine, configured, custody,
                        receipt, packet, self.archive_original_quarantine)

    def sleep(self, seconds):
        time.sleep(seconds)

    def quarantine_wait(self):
        while True:
            time.sleep(1)


if __name__ == '__main__':
    raise SystemExit('SOURCE ONLY: exact keeper/capture execution release is not supplied')
