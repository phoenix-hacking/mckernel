"""Three changed controller contracts; all process/RPC/storage effects are fakes.

The admitted test runner, never the preparation author, executes this file.
Load the full actual component/compat and the unchanged full Campaign ClassDef.
No Campaign constructor, live controller, account, ledger, process or socket call.
"""
import ast
import ctypes
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import types

HERE = Path(__file__).resolve().parent
INPUTS = json.loads((HERE / 'INPUTS.json').read_text())
assert sys.version_info[:2] == (3, 8), 'qualified HOST Python3.8 required'


def checked(key):
    row = INPUTS[key]
    raw = Path(row['path']).read_bytes()
    assert len(raw) == row['bytes']
    assert hashlib.sha256(raw).hexdigest() == row['sha256']
    return row['path'], raw


MODULE_PATH, MODULE_RAW = checked('component')
COMPAT_PATH, COMPAT_RAW = checked('compat')
CONTROLLER_PATH, CONTROLLER_RAW = checked('controller')


class Clock:
    CLOCK_BOOTTIME = 7

    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def clock_gettime(self, clock):
        assert clock == self.CLOCK_BOOTTIME
        return self.now


def exception_contains(error, target, seen=None):
    if error is target:
        return True
    if error is None:
        return False
    if seen is None:
        seen = set()
    if id(error) in seen:
        return False
    seen.add(id(error))
    if isinstance(error, (tuple, list)):
        return any(exception_contains(x, target, seen) for x in error)
    for name in ('primary', 'secondary', 'interrupt', '__cause__', '__context__',
                 'native_primary_error', 'native_secondary_errors',
                 'native_close_errors'):
        if exception_contains(getattr(error, name, None), target, seen):
            return True
    return False


class Channel:
    def __init__(self, env, name, peer_uid=0):
        self.env, self.name, self.peer_uid = env, name, peer_uid
        self.close_error = None
        self.sent = bytearray()
        self.incoming = bytearray()

    def settimeout(self, value):
        assert value > 0

    def bind(self, path):
        assert path.startswith('/test-only/')

    def listen(self, backlog):
        assert backlog == 1

    def setblocking(self, value):
        assert value is False

    def accept(self):
        if self.env.accepted:
            raise BlockingIOError()
        self.env.accepted = True
        return self.env.peer, None

    def connect(self, path):
        assert path == '/test-only/client.sock'

    def getsockopt(self, level, option, length):
        assert length == 12
        pid = 5101 if self.peer_uid == 0 else 4100
        return struct.pack('3i', pid, self.peer_uid, self.peer_uid)

    def send(self, data):
        self.sent.extend(data)
        if len(self.sent) >= 4:
            n = struct.unpack('!I', self.sent[:4])[0]
            if len(self.sent) == n + 4:
                request = json.loads(bytes(self.sent[4:]))
                m = self.env.module
                row = dict(schema=m.SCHEMA, authority=None, native_grant=False,
                    scope='fresh-current-controller-account-data-only',
                    request=request, controller_pid=4100, controller_birth='9001',
                    thread_id=m.ROOT_THREAD, guardian_run_id='fake-only',
                    credit_run_id=m.CREDIT_RUN, credit_budget={'fake_only': True},
                    observed_boot=self.env.clock.now,
                    expires_boot=self.env.clock.now + 5.0, boot_id='fake-boot',
                    source_sha256=m.LOADED_SOURCE_SHA256)
                raw = json.dumps(row, sort_keys=True, separators=(',', ':')).encode()
                self.incoming.extend(struct.pack('!I', len(raw)) + raw)
        return len(data)

    def recv(self, n):
        assert self.incoming
        value = bytes(self.incoming[:n])
        del self.incoming[:n]
        return value

    def close(self):
        self.env.trace.append('close:' + self.name)
        if self.close_error is not None:
            raise self.close_error


class QuietPoll:
    def register(self, handle, events):
        pass

    def poll(self, timeout):
        assert timeout == 0
        return []


class Effects:
    """Only explicit lower effects; none delegate to actual process/state APIs."""
    def __init__(self):
        self.trace, self.syscalls = [], []
        self.clock = Clock()
        self.accepted = False
        self.verification_error = False
        self.fd = 700
        self.peer = Channel(self, 'peer')
        self.listener = Channel(self, 'listener')
        self.client = Channel(self, 'client', 1000)
        self.is_client = False
        self.module = None

    def syscall(self, nr, pid, flags):
        self.syscalls.append([nr.value, pid.value, flags.value])
        return self.fd

    def fcntl(self, fd, command):
        assert fd == self.fd
        if self.verification_error:
            raise OSError('controlled pidfd verification failure')
        return 1 if command == 1 else 0

    def close_fd(self, fd):
        self.trace.append('close:pidfd:%d' % fd)

    def unlink(self, path):
        assert path.startswith('/test-only/')
        self.trace.append('unlink:socket')

    def socket(self, family, kind):
        return self.client if self.is_client else self.listener


def load_environment():
    env = Effects()
    fake_os = types.SimpleNamespace(getpid=lambda: 4100, geteuid=lambda: 0,
        close=env.close_fd, O_NONBLOCK=0x800,
        lstat=lambda path: types.SimpleNamespace(st_mode=stat.S_IFSOCK | 0o600,
            st_uid=1000, st_dev=31, st_ino=41),
        unlink=env.unlink, chmod=lambda path, mode: None,
        fsencode=os.fsencode, path=types.SimpleNamespace(lexists=lambda path: False))
    assert not hasattr(fake_os, 'pidfd_open')
    compat = types.ModuleType('pidfd_compat')
    compat.__file__ = COMPAT_PATH
    exec(compile(COMPAT_RAW, COMPAT_PATH, 'exec'), compat.__dict__)
    compat.os = fake_os
    compat.fcntl = types.SimpleNamespace(fcntl=env.fcntl, F_GETFD=1,
        F_GETFL=3, FD_CLOEXEC=1)
    compat._syscall = lambda: env.syscall
    sys.modules['pidfd_compat'] = compat
    module = types.ModuleType('native_current_owner')
    module.__file__ = MODULE_PATH
    exec(compile(MODULE_RAW, MODULE_PATH, 'exec'), module.__dict__)
    env.module = module
    module.os = fake_os
    module.time = env.clock
    module.birth = lambda pid: '9001'
    module.select = types.SimpleNamespace(poll=QuietPoll, POLLIN=1,
        POLLHUP=16, POLLERR=8)
    module.socket = types.SimpleNamespace(socket=env.socket, AF_UNIX=1,
        SOCK_STREAM=1, SOL_SOCKET=1, SO_PEERCRED=17)
    module.secrets = types.SimpleNamespace(token_hex=lambda size: 'a' * 64)

    class BoundPath:
        def __init__(self, path):
            self.path = path

        def read_bytes(self):
            assert self.path == MODULE_PATH
            return MODULE_RAW

        def read_text(self):
            assert self.path == '/proc/sys/kernel/random/boot_id'
            return 'fake-boot\n'

    module.Path = BoundPath
    sys.modules['native_current_owner'] = module
    tree = ast.parse(CONTROLLER_RAW, filename=CONTROLLER_PATH)
    campaign = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Campaign')
    # Exact entire ClassDef, without running launcher imports, main or constructor.
    namespace = dict(RPC=object(), time=env.clock, sys=sys, os=fake_os,
        TERMINAL_CODES={'paused': 10}, restart_advice=lambda state: 'fake-only')
    exec(compile(ast.Module(body=[campaign], type_ignores=[]),
                 CONTROLLER_PATH, 'exec'), namespace)
    env.campaign_type = namespace['Campaign']
    return env


def campaign_context(env):
    m = env.module
    c = env.campaign_type.__new__(env.campaign_type)
    c.controlled = True
    c.native_owner_control_failed = False
    c.native_owner_control = None
    c.directory = Path('/test-only')
    c.args = types.SimpleNamespace(credit_run_id=m.CREDIT_RUN, hours=0,
        grace_seconds=1, repair_agent_failures=False,
        stop_after_m14_m15=False, heartbeat_seconds=1)
    c.credit_guard = types.SimpleNamespace(identifier=m.CREDIT_RUN, initialized=True)
    c.state = dict(thread_id=m.ROOT_THREAD, worker_pid=4100, worker_start='9001')
    c.rpc = types.SimpleNamespace(close=lambda: env.trace.append('rpc:close'), close_errors=[])
    c.stop_now, c.stop_reason = False, None
    c.checkpoint_requested, c.stopping = False, False
    c.active, c.goal = {}, {'status': 'paused'}
    c.log_dir, c.state_path = Path('/test-only/log'), Path('/test-only/state.json')
    c.save = lambda **fields: env.trace.append('receipt')
    c.begin = lambda: None
    c.stop = lambda: env.trace.append('stop')
    c.record_stop_diagnostic = lambda *a, **k: None
    c.output = types.SimpleNamespace(notice=lambda text: None,
        close=lambda: env.trace.append('output:close'))
    return c


def open_server(env, campaign):
    server = env.module.CurrentOwnerServer.__new__(env.module.CurrentOwnerServer)
    server.__init__(campaign)
    campaign.native_owner_control = server
    server.poll()
    assert len(server.clients) == 1 and server.clients[0][3] == env.fd
    return server


def compatibility_family():
    env = load_environment()
    c = campaign_context(env)
    server = open_server(env, c)
    assert env.syscalls == [[434, 5101, 0]]
    server.close()
    env.is_client = True
    session = env.module.CurrentOwnerSession.__new__(env.module.CurrentOwnerSession)
    session.__init__('/test-only/client.sock', 4100, '9001',
        env.module.LOADED_SOURCE_SHA256, 'b' * 64, 'c' * 64)
    assert session.pidfd == env.fd and session.data['native_grant'] is False
    assert env.syscalls == [[434, 5101, 0], [434, 4100, 0]]
    session.close()
    adopted = []
    for side in ('server', 'client'):
        e = load_environment()
        e.verification_error = True
        if side == 'server':
            c = campaign_context(e)
            obj = e.module.CurrentOwnerServer.__new__(e.module.CurrentOwnerServer)
            obj.__init__(c)
            try:
                obj.poll()
            except e.module.pidfd_compat.PidfdVerificationError as error:
                assert error.fd == e.fd
            else:
                raise AssertionError('verification must fail')
            assert e.trace.count('close:pidfd:700') == 1
            obj.close()
        else:
            e.is_client = True
            obj = e.module.CurrentOwnerSession.__new__(e.module.CurrentOwnerSession)
            try:
                obj.__init__('/test-only/client.sock', 4100, '9001',
                    e.module.LOADED_SOURCE_SHA256, 'b' * 64, 'c' * 64)
            except e.module.pidfd_compat.PidfdVerificationError as error:
                assert error.fd == e.fd and obj.pidfd == error.fd
            else:
                raise AssertionError('verification must fail')
            obj.close()
            assert e.trace.count('close:pidfd:700') == 1
        adopted.append(side)
    return dict(native_api_absent=True, actual_compat_syscalls=env.syscalls,
        verification_fd_custody=adopted, data_native_grant=False)


def cleanup_family():
    close_order = ['close:peer', 'close:pidfd:700', 'close:listener', 'unlink:socket']
    env = load_environment()
    c = campaign_context(env)
    server = open_server(env, c)
    interrupt, receipt = KeyboardInterrupt('close interrupt'), OSError('receipt failure')
    env.peer.close_error = interrupt
    env.trace.clear()
    c.state['thread_id'] = 'controlled-context-failure'

    def fail_receipt(**fields):
        env.trace.append('receipt')
        raise receipt

    c.save = fail_receipt
    try:
        c.poll_native_owner_control()
    except BaseException as error:
        assert error is interrupt and exception_contains(error, receipt)
    else:
        raise AssertionError('original close interruption must escape receipt failure')
    assert env.trace == close_order + ['receipt']
    assert server.close_state == 'UNKNOWN_RETAINED'
    before = list(env.trace)
    try:
        server.close()
    except env.module.ChannelCleanupError:
        pass
    else:
        raise AssertionError('uncertain close must stay retained')
    assert env.trace == before  # no ambiguous close retry

    e = load_environment()
    c = campaign_context(e)
    server = open_server(e, c)
    original = KeyboardInterrupt('original shutdown interrupt')
    nested = KeyboardInterrupt('secondary close interrupt')
    stop_error, receipt_error, output_error = (OSError('stop failure'),
        OSError('shutdown receipt failure'), OSError('output-close failure'))
    e.peer.close_error = nested
    e.trace.clear()

    def fail_begin():
        raise original

    def fail_stop():
        e.trace.append('stop')
        raise stop_error

    def fail_save(**fields):
        e.trace.append('receipt')
        raise receipt_error

    def fail_output():
        e.trace.append('output:close')
        raise output_error

    c.begin, c.stop, c.save = fail_begin, fail_stop, fail_save
    c.output.close = fail_output
    try:
        c.run()
    except BaseException as error:
        assert error is original
        for secondary in (nested, stop_error, receipt_error, output_error):
            assert exception_contains(error, secondary)
    else:
        raise AssertionError('original interruption must escape all shutdown failures')
    assert e.trace == close_order + ['stop', 'rpc:close', 'receipt', 'output:close']

    normal = load_environment()
    c = campaign_context(normal)
    server = open_server(normal, c)
    normal.trace.clear()
    assert c.run() == 10 and server.close_state == 'CLOSED'
    assert normal.trace == close_order + ['stop', 'rpc:close', 'receipt', 'output:close']
    return dict(poll_close_order=close_order, poll_original_interrupt=True,
        receipt_preserved=True, uncertain_close_not_retried=True,
        shutdown_original_interrupt=True, all_shutdown_secondary_errors=True,
        normal_shutdown_exit=10, native_or_resource_release=False)


def deadline_family():
    e = load_environment()

    class Fragments:
        def __init__(self):
            raw = b'{"x":1}'
            self.frame = bytearray(struct.pack('!I', len(raw)) + raw)
            self.timeouts, self.sends, self.recvs = [], 0, 0

        def settimeout(self, value):
            self.timeouts.append(value)

        def send(self, data):
            self.sends += 1
            e.clock.now += 20
            return len(data)

        def recv(self, n):
            self.recvs += 1
            take = n if self.recvs == 1 else 1
            result = bytes(self.frame[:take])
            del self.frame[:take]
            e.clock.now += 20
            return result

    sock = Fragments()
    deadline = 60.0
    e.module.send(sock, {'request': 'data-only'}, deadline)
    try:
        e.module.receive(sock, deadline)
    except RuntimeError as error:
        assert str(error) == 'current control total deadline'
    else:
        raise AssertionError('fragment progress must not renew the shared deadline')
    assert e.clock.now == deadline and sock.timeouts == [60.0, 40.0, 20.0]
    assert (sock.sends, sock.recvs) == (1, 2)
    return dict(one_shared_deadline=60, timeouts=sock.timeouts,
        send_calls=sock.sends, recv_calls=sock.recvs,
        expired_at=e.clock.now, fragments_cannot_renew=True)


result = dict(status='PASS_THREE_CHANGED_CONTROLLER_CONTRACTS',
    families=dict(compatibility=compatibility_family(), cleanup=cleanup_family(),
                  deadline=deadline_family()), actual_external_effects=0,
    actual_Campaign_constructor=False, native_admission=False)
print(json.dumps(result, sort_keys=True, separators=(',', ':')))
