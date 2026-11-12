"""Eight finite reporting controls; no real native, signal, account or FD effect.

Complete pinned modules execute in their own registered module namespaces.
Only explicitly listed primitive I/O and dependency boundaries are controlled.
No result establishes native acquisition, restoration, lifetime or retirement.
"""
import ast
import builtins
import errno
import hashlib
import json as real_json
import math
import os as real_os
import pathlib as real_pathlib
import resource
import stat
import sys
import threading
import types

HERE = real_pathlib.Path(__file__).resolve().parent
NONCE = '1' * 64
ROOT_FD = 77
LEASE_FD = 88
PIDFD = 99
REQUEST_PATH = '/fixture/native-request.json'
BOOT_ID = 'fixture-boot-id'
CASE_NAMES = (
    'constructor_before_retain_pause',
    'postacquisition_before_retain_pause',
    'report_format_secondary',
    'report_write_secondary',
    'report_fsync_secondary',
    'report_close_secondary',
    'signalled_wait_refused_after_report',
    'normal_wait_return_silent_unchanged',
)


def need(value, message):
    if not value:
        raise AssertionError(message)


def canonical(value):
    return real_json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def read_source(ref):
    raw = real_pathlib.Path(ref['path']).read_bytes()
    need(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'],
         'pinned source changed: ' + ref['path'])
    return raw


class ForbiddenEffect(AssertionError):
    pass


class PauseBoundary(BaseException):
    pass


class PrimaryFailure(RuntimeError):
    pass


class ControlledOS(types.ModuleType):
    """A memory-only effect provider; numeric descriptors never name real FDs."""
    def __init__(self, mode=None):
        super().__init__('os')
        for name in ('O_RDONLY', 'O_WRONLY', 'O_CREAT', 'O_EXCL', 'O_NOFOLLOW',
                     'O_CLOEXEC', 'O_DIRECTORY', 'O_APPEND'):
            setattr(self, name, getattr(real_os, name))
        self.WIFEXITED = real_os.WIFEXITED
        self.WEXITSTATUS = real_os.WEXITSTATUS
        self.WIFSIGNALED = real_os.WIFSIGNALED
        self.WTERMSIG = real_os.WTERMSIG
        self.mode = mode
        self.uid = 0
        self.events = []
        self.buffers = {1: b'', 2: b''}
        self.rows = {}
        self.next_input = 500
        self.next_report = 300
        self.wait_calls = []
        self.wait_status = 0
        self.report_open_hook = None
        self.open_error = None
        self.failure = OSError(errno.EIO, 'controlled reporting ' + str(mode))

    def __getattr__(self, name):
        raise ForbiddenEffect('undeclared OS effect: ' + name)

    def getpid(self):
        return 4242

    def getppid(self):
        return 4141

    def getuid(self):
        return self.uid

    def geteuid(self):
        return self.uid

    def fstat(self, fd):
        if fd == ROOT_FD:
            return types.SimpleNamespace(st_dev=1, st_ino=1001, st_uid=0,
                st_mode=stat.S_IFDIR | 0o700, st_nlink=1)
        if fd == LEASE_FD:
            return types.SimpleNamespace(st_dev=1, st_ino=1002, st_uid=0,
                st_mode=stat.S_IFREG | 0o600, st_nlink=1)
        row = self.rows[fd]
        need(row['kind'] == 'input' and row['state'] == 'HELD', 'live memory input')
        return types.SimpleNamespace(st_dev=1, st_ino=1003, st_uid=0,
            st_mode=stat.S_IFREG | 0o600, st_nlink=1)

    def getxattr(self, fd, name):
        need(fd == ROOT_FD and name == 'system.posix_acl_access', 'root ACL input')
        raise OSError(errno.ENODATA, 'controlled root has no access ACL')

    def input_handle(self):
        fd = self.next_input
        self.next_input += 1
        self.rows[fd] = {'kind': 'input', 'state': 'HELD', 'closes': 0}
        self.events.append(('request-input', fd))
        return fd

    def open(self, name, flags, mode, dir_fd=None):
        need(dir_fd == ROOT_FD and mode == 0o600, 'borrowed root and exact report mode')
        need(flags == self.O_WRONLY | self.O_CREAT | self.O_EXCL |
             self.O_NOFOLLOW | self.O_CLOEXEC, 'exact report creation flags')
        need(name.startswith('NATIVE-CONTEXT-DIAGNOSTIC-' + NONCE + '-4242-'),
             'only newly named private report may be opened')
        if self.report_open_hook is not None:
            self.report_open_hook()
        fd = self.next_report
        self.next_report += 1
        self.rows[fd] = {'kind': 'report', 'state': 'HELD', 'closes': 0}
        self.buffers[fd] = b''
        self.events.append(('report-open', fd))
        return fd

    def write(self, fd, raw):
        need(type(raw) is bytes and fd in self.buffers, 'declared report/notice write only')
        if fd >= 300 and self.mode == 'write':
            raise self.failure
        # Real diagnostic_write must handle partial writes, rather than a fixture copy.
        count = min(23, len(raw))
        self.buffers[fd] += raw[:count]
        self.events.append(('write', fd, count))
        return count

    def fsync(self, fd):
        need(fd == ROOT_FD or self.rows[fd]['kind'] == 'report', 'report/root sync only')
        self.events.append(('fsync', fd))
        if self.mode == 'fsync':
            raise self.failure

    def close(self, fd):
        need(fd not in (ROOT_FD, LEASE_FD, PIDFD, 1, 2), 'borrowed handle must not close')
        row = self.rows[fd]
        need(row['state'] == 'HELD' and row['closes'] == 0, 'one memory-handle close attempt')
        row['closes'] += 1
        row['state'] = 'CLOSE_ATTEMPTED_UNKNOWN'
        self.events.append(('close', fd, row['kind']))
        if row['kind'] == 'report' and self.mode == 'close':
            raise self.failure
        row['state'] = 'CLOSED'

    def waitpid(self, pid, options):
        need(pid == 5151 and options == 0 and not self.wait_calls,
             'only one scripted existing own wait result')
        self.wait_calls.append((pid, options))
        self.events.append(('wait-return', pid, self.wait_status))
        return pid, self.wait_status


class ControlledJSON(types.ModuleType):
    def __init__(self, mode):
        super().__init__('json')
        self.loads = real_json.loads
        self.mode = mode
        self.format_error = RuntimeError('controlled payload serialization failure')

    def dumps(self, value, *args, **kwargs):
        if self.mode == 'format' and type(value) is dict and 'source_component' in value:
            raise self.format_error
        return real_json.dumps(value, *args, **kwargs)


class Registry:
    def __init__(self, mapping):
        self.mapping = mapping
        self.prior = {}

    def __enter__(self):
        for name, module in self.mapping.items():
            self.prior[name] = sys.modules.get(name)
            sys.modules[name] = module
        return self

    def __exit__(self, *unused):
        for name, module in self.prior.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module


def module(name, **values):
    result = types.ModuleType(name)
    result.__dict__.update(values)
    return result


class Harness:
    def __init__(self, pins, mode=None):
        self.pins = pins
        self.io = ControlledOS(mode)
        self.json = ControlledJSON(mode)
        self.pause_calls = 0
        self.pause_hook = None
        self.flock_calls = []
        self.poll_calls = []
        self.runtime_checks = []
        self.preconditions = []
        self.cfg = {'kind': 'mckernel-native-signal-operation-v1', 'nonce': NONCE,
            'boot_id': BOOT_ID, 'caps': {'utc': 110, 'boot': 110, 'mono': 110, 'boot_id': BOOT_ID},
            'watchdog_pid': 4141, 'watchdog_birth': '333',
            'runtime': {'path': '/fixture/runtime', 'sha256': '3' * 64},
            'owner': {'path': '/fixture/owner.py', 'sha256': '4' * 64},
            'native': {}, 'operation_root': {'device': 1, 'inode': 1001,
                'uid': 0, 'mode': 0o700, 'nlink': 1}}
        self.raw = canonical(self.cfg)
        self.request_sha = hashlib.sha256(self.raw).hexdigest()
        self.opaque_owner = module('native_diagnostic_container_owner', __file__='/fixture/owner.py')
        harness = self

        class MemoryPath:
            def __init__(self, path):
                self.path = path

            def read_text(self):
                need(self.path == '/proc/sys/kernel/random/boot_id', 'only scripted boot text')
                return BOOT_ID + '\n'

        class MemoryPoll:
            def register(self, fd, event):
                need(fd == PIDFD and event == 1, 'scripted own pidfd readiness')

            def poll(self, milliseconds):
                need(type(milliseconds) is int and 1 <= milliseconds <= 1000, 'bounded ready poll')
                harness.poll_calls.append(milliseconds)
                return [(PIDFD, 1)]

        def pause():
            harness.pause_calls += 1
            need(harness.pause_calls == 1, 'one observed original hold boundary')
            if harness.pause_hook is not None:
                harness.pause_hook()
            raise PauseBoundary()

        def pinned(path, digest, limit=2 * 1024 * 1024):
            need(path == REQUEST_PATH and digest == harness.request_sha and len(harness.raw) <= limit,
                 'only memory request input, never a protected or real path')
            return harness.io.input_handle(), harness.raw

        def runtime(path, digest):
            need((path, digest) == ('/fixture/runtime', '3' * 64), 'scripted runtime input')
            harness.runtime_checks.append((path, digest))

        def flock(fd, flags):
            need(fd == LEASE_FD and flags == 6, 'declared memory lease flock primitive')
            harness.flock_calls.append((fd, flags))

        def sha(value):
            need(type(value) is str and len(value) == 64 and all(x in '0123456789abcdef' for x in value),
                 'nonce input shape')
            return value

        def unique(pairs):
            result = {}
            for key, value in pairs:
                need(key not in result, 'memory request duplicate key')
                result[key] = value
            return result

        self.mapping = {
            'os': self.io, 'json': self.json,
            'time': module('time', time=lambda: 100, monotonic=lambda: 100,
                clock_gettime=lambda clock: 100, CLOCK_BOOTTIME=7,
                time_ns=lambda: 1001, monotonic_ns=lambda: 2002),
            'pathlib': module('pathlib', Path=MemoryPath),
            'signal': module('signal', pause=pause, SIGTERM=15, SIGKILL=9),
            'select': module('select', poll=MemoryPoll, POLLIN=1),
            'fcntl': module('fcntl', flock=flock, LOCK_EX=2, LOCK_NB=4),
            'graph_observations': module('graph_observations', canonical=canonical,
                process=lambda pid: ('444' if pid == 5151 else '333', 1, 1001)),
            'custody_protocol_v2': module('custody_protocol_v2', sha256_hex=sha, boot_now=lambda: 100),
            'root_bootstrap': module('root_bootstrap', pinned_root_file=pinned),
            'runtime_binding': module('runtime_binding', verify_current=runtime),
            'native_current_owner': module('native_current_owner', birth=lambda pid: '333', unique=unique),
            'native_diagnostic_container_owner': self.opaque_owner,
            'native_source_binding': module('native_source_binding'),
            'compositor': module('compositor'), 'operation_supervisor': module('operation_supervisor'),
            'deferred_fork': module('deferred_fork'), 'pidfd_compat': module('pidfd_compat'),
            'immutable_epoch': module('immutable_epoch'), 'adapter': module('adapter'),
            'union_server_guarded': module('union_server_guarded', UnionChannel=type('ForbiddenUnion', (), {})),
        }
        for name in ('ownership_latch', 'inplace_custody', 'graph_producer',
                     'native_resource_admission', 'operation_watchdog', 'supervisor_entry'):
            self.mapping[name] = module(name, __file__=pins['modules'][name]['path'])

    def __enter__(self):
        self.registry = Registry(self.mapping)
        self.registry.__enter__()
        try:
            allowed_stdlib = {'fcntl', 'hashlib', 'json', 'math', 'sys', 'os', 'select',
                'resource', 'signal', 'time', 'stat', 'struct', 'errno', 'base64',
                'pathlib', 'threading'}

            def no_real_open(*args, **kwargs):
                raise ForbiddenEffect('SUT builtin open has no real filesystem authority')

            def controlled_import(name, globals=None, locals=None, fromlist=(), level=0):
                need(level == 0 and (name in self.mapping or name in allowed_stdlib),
                     'only declared inert/stdlib imports: ' + name)
                return builtins.__import__(name, globals, locals, fromlist, level)

            for name in ('ownership_latch', 'inplace_custody', 'graph_producer',
                         'native_resource_admission', 'operation_watchdog', 'supervisor_entry'):
                ref = self.pins['modules'][name]
                # Complete bytes, imports and globals, not AST-transplanted functions.
                self.mapping[name].__dict__['__builtins__'] = dict(vars(builtins),
                    open=no_real_open, __import__=controlled_import)
                exec(compile(read_source(ref), ref['path'], 'exec'), self.mapping[name].__dict__)
            self.latches = self.mapping['ownership_latch']
            self.native = self.mapping['native_resource_admission']
            self.graph = self.mapping['graph_producer']
            self.watchdog = self.mapping['operation_watchdog']
            self.supervisor = self.mapping['supervisor_entry']
            self.check_globals()
            return self
        except BaseException:
            self.registry.__exit__(None, None, None)
            raise

    def __exit__(self, *unused):
        self.registry.__exit__(*unused)

    def check_globals(self):
        for mod, names in ((self.supervisor, ('_report_native_failure', 'verify_actual_operation_gates', '_run_named_native')),
                           (self.watchdog, ('report_native_context', '_persist_native_context', 'report_native_wait',
                            'capture_raw_exception', 'render_raw_failure', 'own', 'close_once'))):
            for name in names:
                fn = getattr(mod, name)
                need(fn.__globals__ is mod.__dict__ and fn.__code__.co_filename == mod.__file__,
                     'actual complete module namespace/source: ' + name)
            need(mod.os is self.io and mod.sys is sys and mod.json is self.json,
                 'actual imported controlled effect namespace')
            need(mod.source is self.mapping['inplace_custody'], 'actual imported source module')
        need(self.watchdog.math is math and self.watchdog.hashlib is hashlib,
             'renderer real imported helper globals')
        need(self.watchdog.CustodyLatch is self.latches.CustodyLatch,
             'actual watchdog latch class')
        need(self.native.NativeAdmission.retain_unknown.__globals__ is self.native.__dict__,
             'actual native retention function/global UNKNOWN')

    def request(self):
        value = self.native.VerifiedNativeRequest(REQUEST_PATH, self.request_sha)
        need(type(value) is self.native.VerifiedNativeRequest and value.cfg == self.cfg,
             'genuine request constructor and verify against controlled read inputs')
        return value

    def native_watchdog(self):
        request = self.request()
        value = self.watchdog.Watchdog(ROOT_FD, LEASE_FD, NONCE, 5151, PIDFD,
            '444', 110, 1, native_request=request)
        value.latch = self.latches.CustodyLatch('SUPERVISOR_BOUND')
        return value

    def report_rows(self):
        return [(fd, row) for fd, row in self.io.rows.items() if row['kind'] == 'report']

    def assert_report_closed(self):
        rows = self.report_rows()
        need(len(rows) == 1 and rows[0][1]['closes'] == 1 and rows[0][1]['state'] == 'CLOSED',
             'only own new report handle closed once')
        need(self.watchdog.OWNED[0]['state'] == 'CLOSED' and 'fd' not in self.watchdog.OWNED[0],
             'genuine own/close_once consumption')

    def assert_report_success(self):
        need(len(self.watchdog.NATIVE_REPORT_BOUNDARIES) == 1 and
             self.watchdog.NATIVE_REPORT_BOUNDARIES[0]['private_record_complete'] is True,
             'intended complete private report must be observed')
        need(not self.watchdog.SECONDARY and not self.watchdog.NATIVE_REPORT_SECONDARY,
             'no unexpected global, birth, rendering or report secondary')
        self.assert_report_closed()

    def assert_notice_private(self, secret):
        need(self.io.buffers[1] == b'' and self.io.buffers[2], 'first captured stderr notice only')
        need(secret.encode() not in self.io.buffers[2], 'private primary text absent from notice')
        notice = real_json.loads(self.io.buffers[2])
        need(notice['native_authority_or_release'] is False and
             notice['primary_raw_exception_and_traceback_retained'] is True,
             'notice remains reporting DATA only')


def constructor_case(pins):
    with Harness(pins) as h:
        request = h.request()
        lease = h.graph.RootLease(LEASE_FD, ROOT_FD, NONCE, 4141, '333')
        h.io.uid = 1000  # primitive constructor failure before self.request/nonce exist

        def report_before_retain():
            admission = h.supervisor._NATIVE_OWNERS[-1]
            need(admission.state == 'INITIALIZING' and not hasattr(admission, 'request') and
                 not hasattr(admission, 'nonce'), 'real partially initialized admission attributes')

        def pause_after_retain():
            admission = h.supervisor._NATIVE_OWNERS[-1]
            need(admission.state == 'UNKNOWN_RETAINED' and admission in h.native.UNKNOWN,
                 'genuine retain_unknown precedes original pause')
            need(len(h.watchdog.NATIVE_REPORT_BOUNDARIES) == 1, 'report precedes retain/pause')

        h.io.report_open_hook = report_before_retain
        h.pause_hook = pause_after_retain
        try:
            h.supervisor.verify_actual_operation_gates(request, ROOT_FD, lease, h.opaque_owner)
        except PauseBoundary:
            pass
        else:
            raise AssertionError('original retained pause boundary was bypassed')
        admission = h.supervisor._NATIVE_OWNERS[0]
        primary = admission.failure
        need(type(admission) is h.native.NativeAdmission and admission.root_fd == ROOT_FD,
             'real preallocated native object retained')
        need(type(primary) is RuntimeError and primary.args == ('actual root native owner required',),
             'actual constructor primary, not an injected fake constructor')
        phase, raw, tb = h.supervisor._NATIVE_DIAGNOSTIC_PRIMARY[0]
        need(phase == 'NATIVE_ADMISSION_CONSTRUCTOR_FAILED' and raw is primary and tb is primary.__traceback__,
             'supervisor retained original primary/TB')
        boundary = h.watchdog.NATIVE_REPORT_BOUNDARIES[0]
        need(boundary['error'] is primary and boundary['traceback'] is tb and
             boundary['caller_root_fd_borrowed_not_owned'] == ROOT_FD and boundary['private_record_complete'],
             'report uses verified caller request/root, not missing admission fields')
        h.assert_report_success()
        h.assert_notice_private('actual root native owner required')
        need(h.pause_calls == 1 and not h.io.wait_calls, 'no wait/acquisition/release')


def postacquisition_case(pins):
    with Harness(pins) as h:
        primary = OSError(errno.EIO, 'controlled source acquisition callback failure')
        held = h.native.NativeAdmission.__new__(h.native.NativeAdmission)
        held.state = 'CLAIMED'; held.claim_fd = None; held.root_fd = ROOT_FD
        held.failure = None; h.preconditions.append(held)
        original_gate = h.supervisor.verify_actual_operation_gates

        def supplied_opaque_admission(request, root_fd, lease, owner):
            need(type(request) is h.native.VerifiedNativeRequest and request.cfg == h.cfg and
                 root_fd == ROOT_FD and type(lease) is h.graph.RootLease and owner is h.opaque_owner,
                 'explicit inert admission precondition input binding')
            held.request = request; held.cfg = request.cfg; held.lease = lease; held.nonce = NONCE
            return held

        class SourceBoundary:
            def __init__(self, admission):
                need(admission is held, 'same opaque typed admission input')
                self.admission = admission

            def acquire(self):
                raise primary

        # This ONE declared dependency boundary models an already-supplied opaque
        # typed admission for the reporting seam. It proves no gate/acquisition.
        h.supervisor.verify_actual_operation_gates = supplied_opaque_admission
        h.mapping['native_source_binding'].NativeSourceCustody = SourceBoundary

        def before_retain():
            need(held.state == 'CLAIMED' and held.failure is None,
                 'postacquisition report precedes actual retain_unknown')

        def after_retain():
            need(held.state == 'UNKNOWN_RETAINED' and held.failure is primary and held in h.native.UNKNOWN,
                 'real typed object and actual retain_unknown hold')

        h.io.report_open_hook = before_retain; h.pause_hook = after_retain
        try:
            h.supervisor._run_named_native(REQUEST_PATH, h.request_sha, ROOT_FD, LEASE_FD)
        except PauseBoundary:
            pass
        else:
            raise AssertionError('postacquisition original pause boundary was bypassed')
        finally:
            h.supervisor.verify_actual_operation_gates = original_gate
        phase, raw, tb = h.supervisor._NATIVE_DIAGNOSTIC_PRIMARY[0]
        need(phase == 'NATIVE_SUPERVISOR_POST_ACQUISITION_FAILED' and raw is primary and tb is primary.__traceback__,
             'real caller postacquisition failure primary/TB identity')
        need(h.watchdog.NATIVE_REPORT_BOUNDARIES[0]['error'] is primary and
             len(h.supervisor._NATIVE_OWNERS) == 3 and
             h.supervisor._NATIVE_OWNERS[2].admission is held,
             'real caller retains request/lease/source; supplied admission is explicit fixture input')
        h.assert_report_success(); h.assert_notice_private(primary.args[1])
        need(h.pause_calls == 1 and not h.io.wait_calls and not hasattr(held, 'completion'),
             'no NativeCompletion, retirement or native acquisition manufactured')


def secondary_case(pins, mode):
    with Harness(pins, mode) as h:
        primary = PrimaryFailure('private-original-primary-' + mode)
        try:
            raise primary
        except PrimaryFailure:
            tb = primary.__traceback__
            stored = h.watchdog.report_native_context(ROOT_FD, 'TEST_SECONDARY_' + mode,
                NONCE, h.request_sha, primary)
        need(stored is False, 'failed private persistence cannot claim completion')
        boundary = h.watchdog.NATIVE_REPORT_BOUNDARIES[0]
        need(boundary['error'] is primary and boundary['traceback'] is tb and
             boundary['private_record_complete'] is False, 'raw primary/TB survives secondary')
        need(h.watchdog.RAW_FAILURES[0]['error'] is primary and
             h.watchdog.RAW_FAILURES[0]['traceback'] is tb, 'qualified raw object retention')
        expected_error = h.json.format_error if mode == 'format' else h.io.failure
        need(any(error is expected_error for label, error in h.watchdog.SECONDARY),
             'actual failing lower effect retained separately')
        need(any(row['error'] is expected_error for row in h.watchdog.RAW_FAILURES),
             'secondary raw object/TB retained')
        if mode == 'format':
            need(not h.report_rows() and not h.watchdog.OWNED, 'serialization failed before any report open')
        elif mode == 'close':
            row = h.watchdog.OWNED[0]
            need(row['state'] == 'CLOSE_ATTEMPTED_UNKNOWN' and 'fd' not in row,
                 'real close consumes owned handle before uncertain close')
            need(len(h.report_rows()) == 1 and h.report_rows()[0][1]['closes'] == 1,
                 'one uncertain close only')
            h.watchdog.close_once(row)
            need(h.report_rows()[0][1]['closes'] == 1, 'no numeric close retry')
        else:
            h.assert_report_closed()
        h.assert_notice_private(primary.args[0])
        need(not h.io.wait_calls and h.pause_calls == 0, 'reporter cannot wait/pause/retire')


def signalled_case(pins):
    with Harness(pins) as h:
        value = h.native_watchdog()
        h.io.wait_status = 15  # synthetic POSIX wait-status DATA; no signal is sent

        def report_before_guard():
            need(value.wait_status is None, 'report immediately follows existing wait before old guard')

        h.io.report_open_hook = report_before_guard
        try:
            value.supervise()
        except RuntimeError as error:
            need(error.args == ('exact current direct native supervisor join required',),
                 'unchanged real NativeParentRetirement WIFEXITED refusal')
        else:
            raise AssertionError('synthetic signalled result cannot pass actual refusal')
        need(h.io.wait_calls == [(5151, 0)] and value.wait_status == 15,
             'single actual caller wait invocation with scripted result')
        need(value.state == value.latch.state == 'UNKNOWN_RETAINED' and value.latch.failure and
             len(value.latch.retained) == 1 and
             type(value.latch.retained[0]) is h.native.NativeParentRetirement,
             'actual sticky latch retains genuine partial refusal object')
        data = h.watchdog.NATIVE_REPORT_BOUNDARIES[0]['wait_data']
        need(data == {'requested_pid': 5151, 'expected_supervisor_birth': '444',
            'returned_pid': 5151, 'raw_wait_status': 15, 'WIFEXITED': False,
            'exit_status': None, 'WIFSIGNALED': True, 'term_signal': 15,
            'request_type': 'native_resource_admission.VerifiedNativeRequest',
            'request_exact_current_type': True, 'one_existing_own_waitpid_return_only': True,
            'native_validation_or_success': False}, 'raw existing wait DATA preserved exactly')
        h.assert_report_success()
        need(h.io.buffers[1] == h.io.buffers[2] == b'' and h.poll_calls,
             'successful private wait report silent; readiness avoids all signal branches')


def normal_case(pins):
    with Harness(pins) as h:
        value = h.native_watchdog()
        need(h.watchdog.report_native_wait(value, 5151, 0) is True, 'actual normal wait DATA report')
        data = h.watchdog.NATIVE_REPORT_BOUNDARIES[0]['wait_data']
        need(data['raw_wait_status'] == 0 and data['WIFEXITED'] is True and
             data['exit_status'] == 0 and data['WIFSIGNALED'] is False and data['term_signal'] is None,
             'normal supplied wait result decoded')
        need(h.io.buffers[1] == h.io.buffers[2] == b'' and not h.io.wait_calls,
             'normal report silent and adds no wait')
        h.assert_report_success()
        # Reuse unchanged normal-return scope; never fake a positive retirement.
        old = ast.parse(read_source(pins['baseline_watchdog']))
        new = ast.parse(read_source(pins['modules']['operation_watchdog']))
        def supervise(tree):
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Watchdog')
            return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'supervise')
        baseline = supervise(old); candidate = supervise(new)
        report = [n for n in candidate.body[1].body if isinstance(n, ast.If) and
            len(n.body) == 1 and isinstance(n.body[0], ast.Expr) and
            isinstance(n.body[0].value, ast.Call) and
            isinstance(n.body[0].value.func, ast.Name) and n.body[0].value.func.id == 'report_native_wait']
        need(len(report) == 1, 'one source-added report call')
        candidate.body[1].body.remove(report[0])
        need(ast.dump(candidate, include_attributes=False) == ast.dump(baseline, include_attributes=False),
             'all original control/return/status/retirement logic unchanged')
        need(not hasattr(value, 'native_terminal') and value.latch.retained == [] and
             value.state == 'HELD', 'no positive native retirement object/result manufactured')


def main():
    pins = real_json.loads((HERE / 'SOURCE-PINS.json').read_bytes())
    for ref in list(pins['modules'].values()) + [pins['baseline_watchdog']]:
        read_source(ref)
    cases = []
    functions = [lambda: constructor_case(pins), lambda: postacquisition_case(pins)]
    functions += [lambda mode=mode: secondary_case(pins, mode) for mode in ('format', 'write', 'fsync', 'close')]
    functions += [lambda: signalled_case(pins), lambda: normal_case(pins)]
    for name, function in zip(CASE_NAMES, functions):
        function()
        cases.append({'name': name, 'pass': True})
    for ref in list(pins['modules'].values()) + [pins['baseline_watchdog']]:
        read_source(ref)
    print(real_json.dumps({'status': 'PASS_EIGHT_REPORTING_ONLY_CONTROLS_DATA_NOT_NATIVE_OR_OWNERSHIP_PROOF',
        'cases': cases, 'native_or_IHK_or_account_or_original_process_execution': False,
        'original81012_and_all_holds_unchanged': True}, sort_keys=True, separators=(',', ':')))


if __name__ == '__main__':
    main()
