"""One dedicated in-container F08 Owner; source proposal, not an execution grant.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The HOST caller must retain this container/Owner on UNKNOWN; no killing phase.
"""
import ctypes
import errno
import fcntl
import hashlib
import importlib.util
import json
import math
import os
import re
import resource
import stat
import sys
import time
import traceback
from pathlib import Path

OUT = Path('/output')
OWNER_SHA = '3515d8907dabe319568945f224a553134a33373d5652bf7ded8656a9fd707994'
PIDFD_SHA = '068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'
PAYLOAD_SHA = 'b9cf237dbd3d6156f050418945d6fd60fd9738d6604f399013761865f6830447'
IHK_SHA = 'b7bcafd0923de851cd04b3934207e7217065e28434e95e505d4ed5fd4bfc96c2'
UDEV_SHA = '034fd62bb884d5ee2244966e96db2a40970de1a423f75057380fae67ea9d0cce'
CAP_SHA = '70e8dbe271e2ea63127fbc20270ce60541d1244f0b170888d258b86b2573bcbf'
ARGV = ['/usr/local/sbin/ihkmond', '-k', '1', '-i', '-1']
ENV = {'LANG': 'C', 'LC_ALL': 'C', 'PATH': '/usr/bin:/bin', 'TZ': 'UTC',
       'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': '/tmp'}


# Actual same-kernel backend/profile DATA is unissued at source preparation.
# The future reviewed normal Root parent pins real authority files and seals
# these inline context values into one root-owned, readonly operation input.
EXPECTED_CONTEXT = None
PROFILE_SHA = None
EXPECTED_CONTEXT_SHA = None
HOST_GUARD_SHA = '5c2f456402992f233b6a13d9aaf7fe2549391a029fcd3cd138d6664d794e3756'
ROOT_THREAD = '01a18bc3-e072-7810-9426-75101b0856c0'

def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def file_identity(path, expected):
    value = Path(path)
    digest = hashlib.sha256()
    with value.open('rb') as stream:
        before = os.fstat(stream.fileno())
        require(stat.S_ISREG(before.st_mode), 'required regular input: ' + path)
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    shape = lambda s: [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns]
    require(shape(before) == shape(after), 'input changed during read: ' + path)
    require(digest.hexdigest() == expected, 'input digest differs: ' + path)
    return {'path': path, 'identity': shape(before), 'sha256': expected,
            'resolved_path': str(value.resolve())}


def load_pinned(path, expected, name):
    identity = file_identity(path, expected)
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, 'pinned Python source loader unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    file_identity(path, expected)
    return module, identity


def write_json(name, value):
    data = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    with (OUT / name).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(str(OUT), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def snapshot_owner():
    pid = os.getpid()
    proc = Path('/proc/self')
    raw_status = (proc / 'status').read_text()
    fields = dict(line.split(':', 1) for line in raw_status.splitlines() if ':' in line)
    raw_stat = (proc / 'stat').read_text()
    fds = {}
    for name in sorted(os.listdir(str(proc / 'fd')), key=int):
        fd = int(name)
        try:
            value = os.fstat(fd)
            target = os.readlink(str(proc / 'fd' / name))
            fds[name] = {'target': target, 'device': value.st_dev, 'inode': value.st_ino,
                         'mode': value.st_mode, 'descriptor_flags': fcntl.fcntl(fd, fcntl.F_GETFD),
                         'status_flags': fcntl.fcntl(fd, fcntl.F_GETFL)}
        except OSError as exc:
            if exc.errno not in (errno.ENOENT, errno.EBADF):
                raise
            # listdir's own descriptor can already have been closed.
    libc = ctypes.CDLL(None, use_errno=True)
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    child_subreaper = ctypes.c_int(-1)
    if libc.prctl(37, ctypes.addressof(child_subreaper), 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'GET_CHILD_SUBREAPER')
    root = os.stat('/')
    return {'pid': pid, 'birth': raw_stat.rsplit(') ', 1)[1].split()[19],
            'namespace': {n: os.stat(str(proc / 'ns' / n)).st_ino for n in ('pid', 'mnt')},
            'root': [root.st_dev, root.st_ino],
            'uid': [int(x) for x in fields['Uid'].split()],
            'gid': [int(x) for x in fields['Gid'].split()],
            'tasks': sorted(os.listdir(str(proc / 'task')), key=int),
            'fds': fds, 'signals': {n: fields[n].strip() for n in ('SigBlk', 'SigIgn', 'SigCgt')},
            'subreaper': child_subreaper.value, 'raw_stat': raw_stat, 'raw_status': raw_status}


def retain_owner(owner, exc):
    # This call never returns. Keep the same object and every method-owned handle.
    raw_primary = (exc, BaseException.__dict__['__traceback__'].__get__(exc, type(exc)))
    raw_secondaries = []
    try:
        owner._f08_caller_raw_primary = raw_primary
        owner._f08_caller_raw_secondaries = raw_secondaries
        write_json('CALLER-UNKNOWN.json', {
            'status': 'UNKNOWN_RETAIN_SAME_OWNER_CONTAINER_AND_CHARGE',
            'error_type': type(exc).__name__, 'error': str(exc),
            'traceback': ''.join(traceback.format_exception(type(exc), exc, raw_primary[1])),
            'owner_pid': os.getpid(), 'method_status': getattr(owner, '_f08_custody', {}).get('status'),
            'no_automatic_signal_exit_or_removal': True})
    except BaseException as diagnostic_error:
        try:
            raw_secondaries.append((diagnostic_error, BaseException.__dict__['__traceback__'].__get__(diagnostic_error, type(diagnostic_error))))
        except BaseException:
            pass
    while True:
        try:
            time.sleep(60)
        except BaseException as keeper_error:
            try:
                raw_secondaries.append((keeper_error, BaseException.__dict__['__traceback__'].__get__(keeper_error, type(keeper_error))))
            except BaseException:
                pass



def closed_input_guard(value, nonce):
    require(type(value) is dict and set(value) == {
        'schema', 'Root_thread_id', 'invocation', 'operation_nonce', 'profile_sha256',
        'expected_context_sha256', 'source_permission_ref', 'provider_lifetime_owner_ref',
        'issued_utc_ns', 'issued_mono_ns', 'expires_after_seconds'}, 'closed Root context input guard')
    require(value['schema'] == 'mckernel.m15.f08.Root-genuine-context-input-guard.v1' and
            value['Root_thread_id'] == ROOT_THREAD and
            value['invocation'] == 'invocation20261112T094452Z-12a4bea0' and
            value['operation_nonce'] == nonce, 'same Root fresh context input')
    require(value['profile_sha256'] == PROFILE_SHA and value['expected_context_sha256'] == EXPECTED_CONTEXT_SHA,
            'actual reviewed profile/context input differs')
    require(type(value['expires_after_seconds']) is int and value['expires_after_seconds'] == 300,
            'exact bounded context input lifetime')
    for name in ('issued_utc_ns', 'issued_mono_ns'):
        require(type(value[name]) is int and value[name] > 0, 'actual input issuance clock')
    require(0 <= (time.time_ns() - value['issued_utc_ns']) / 1e9 <= 300 and
            0 <= (time.monotonic_ns() - value['issued_mono_ns']) / 1e9 <= 300, 'stale Root context input')
    for name in ('source_permission_ref', 'provider_lifetime_owner_ref'):
        ref = value[name]
        require(type(ref) is dict and set(ref) == {'path', 'bytes', 'sha256'} and
                type(ref['path']) is str and ref['path'].startswith('/') and
                type(ref['bytes']) is int and ref['bytes'] > 0 and
                re.fullmatch('[0-9a-f]{64}', ref['sha256']) is not None, 'pinned current Root context authority reference')
    return value

def require_provider_context(operation):
    context = operation['provider_context']
    require(type(context) is dict and set(context) == {'schema', 'static', 'input_guard', 'publisher_before'},
            'closed genuine context DATA required')
    require(context['schema'] == 'mckernel.m15.f08.real-existing-udev-context-binding.v2' and
            context['static'] == EXPECTED_CONTEXT, 'exact selected genuine context')
    guarded = closed_input_guard(context['input_guard'], operation['nonce'])
    before = context['publisher_before']
    require(type(before) is dict and set(before) == {'proof', 'original_cli'}, 'actual before guard envelope')
    proof = before['proof']
    require(type(proof) is dict and set(proof) == {
        'schema', 'phase', 'operation_nonce', 'expected_context_sha256', 'actor_source_sha256',
        'actor_uid', 'actor_gid', 'observed_utc_ns', 'observed_mono_ns', 'observed',
        'input_and_executable_FDs_closed', 'direct_children_empty',
        'service_package_queries_or_socket_send_or_signal_or_namespace_change'}, 'closed actual publisher guard proof')
    require(proof['schema'] == 'mckernel.m15.f08.actual-selected-publisher-lifetime-guard.v1' and
            proof['phase'] == 'before' and proof['operation_nonce'] == operation['nonce'] and
            proof['expected_context_sha256'] == EXPECTED_CONTEXT_SHA and proof['actor_source_sha256'] == HOST_GUARD_SHA,
            'actual pinned before guard source/nonce')
    require(proof['actor_uid'] == proof['actor_gid'] == 0 and proof['observed'] == EXPECTED_CONTEXT['observed_tuple'] and
            proof['input_and_executable_FDs_closed'] is True and proof['direct_children_empty'] is True and
            proof['service_package_queries_or_socket_send_or_signal_or_namespace_change'] is False,
            'actual current publisher tuple or closure differs')
    for kind, clock in (('utc', time.time_ns()), ('mono', time.monotonic_ns())):
        key = 'observed_' + kind + '_ns'
        require(type(proof[key]) is int and proof[key] >= guarded['issued_' + kind + '_ns'] and
                0 <= (clock - proof[key]) / 1e9 <= 300, 'current publisher before proof freshness')
    cli = before['original_cli']
    require(type(cli) is dict and set(cli) == {
        'label', 'pid', 'birth', 'exit', 'direct_wait_joined', 'streams_closed',
        'receipt_persisted', 'lifecycle_UNKNOWN', 'resource_charge_retained'}, 'closed original before-guard CLI receipt')
    require(cli['label'] == 'provider-context-before' and type(cli['pid']) is int and cli['pid'] > 0 and
            type(cli['birth']) is str and cli['birth'].isdigit() and int(cli['birth']) > 0 and cli['exit'] == 0 and
            cli['direct_wait_joined'] is True and cli['streams_closed'] is True and cli['receipt_persisted'] is True and
            cli['lifecycle_UNKNOWN'] is False and cli['resource_charge_retained'] is False,
            'genuine original before-guard wait/streams required')
    return context

def consumer_context_bookend(operation):
    context = require_provider_context(operation)
    observed = {'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    require(observed['boot_id'] == EXPECTED_CONTEXT['observed_tuple']['boot_id'], 'consumer boot differs')
    for name, key in (('net', 'expected_consumer_netns'), ('user', 'expected_consumer_userns')):
        path = '/proc/self/ns/' + name
        st = os.stat(path)
        observed[name] = {'device': st.st_dev, 'inode': st.st_ino, 'link': os.readlink(path)}
        require(observed[name] == EXPECTED_CONTEXT[key], 'actual consumer namespace differs: ' + name)
    path = '/run/udev/control'
    st = os.lstat(path)
    require(stat.S_ISSOCK(st.st_mode), 'genuine control endpoint must be a socket')
    observed['control'] = {'device': st.st_dev, 'inode': st.st_ino, 'uid': st.st_uid, 'gid': st.st_gid,
                           'mode': oct(stat.S_IMODE(st.st_mode)), 'nlink': st.st_nlink, 'bytes': st.st_size,
                           'mtime_ns': str(st.st_mtime_ns), 'ctime_ns': str(st.st_ctime_ns),
                           'status': 'OBSERVED', 'path': path, 'kind': 'SOCKET'}
    require(observed['control'] == EXPECTED_CONTEXT['observed_tuple']['control_node'],
            'actual consumer control physical identity/mode differs')
    observed['F_OK_under_UID1000'] = os.access(path, os.F_OK)
    require(observed['F_OK_under_UID1000'] is True, 'genuine control path unavailable under actual consumer UID')
    observed['input_guard'] = context['input_guard']
    return observed



def bind_active_backend(operation):
    global EXPECTED_CONTEXT, PROFILE_SHA, EXPECTED_CONTEXT_SHA
    value = os.lstat('/input/F08-OPERATION.json')
    require(stat.S_ISREG(value.st_mode) and value.st_uid == value.st_gid == 0 and
            stat.S_IMODE(value.st_mode) == 0o444 and value.st_nlink == 1,
            'actual immutable Root-sealed active operation DATA required')
    module, source = load_pinned('/input/owned_process.py', OWNER_SHA, 'f08_active_inside_owner')
    actual_caller_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    pins = {'inside_owner_sha256': OWNER_SHA, 'inside_caller_sha256': actual_caller_sha,
            'pidfd_sha256': PIDFD_SHA, 'payload_sha256': PAYLOAD_SHA,
            'ihklib_sha256': IHK_SHA, 'libudev_sha256': UDEV_SHA, 'libcap_sha256': CAP_SHA,
            'source_contract_sha256': '519defcd6719e1e55e44fb0de4f607061c59dd2cdf6d45024e3ad470c414a4ea'}
    # This consumes the normal Root parent's pinned admission projection.
    # It does not mint a grant, resolve a hold or substitute for that parent.
    observer = module.ActiveKmsgObserver(operation, pins)
    static = operation['provider_context']['static']
    require(type(static) is dict and set(static) == {
        'schema', 'source_contract_sha256', 'monitor', 'expected_consumer_netns',
        'expected_consumer_userns', 'observed_tuple', 'publisher_package_DB_metadata',
        'publisher_package_scope', 'saved_package_DATA_sha256', 'saved_service_DATA_sha256'},
        'closed source-derived genuine static publisher context')
    require(static['schema'] == 'mckernel.m15.f08.closed-static-genuine-context.v1' and
            static['publisher_package_scope'] ==
            'INSTALLED_DATABASE_ONLY_NO_ARCHIVE_SIGNATURE_SOURCE_OR_PROTOCOL_AUTHENTICATION',
            'existing honest provider-context provenance scope')
    EXPECTED_CONTEXT = static
    PROFILE_SHA = observer.backend['profile_ref']['sha256']
    EXPECTED_CONTEXT_SHA = observer.backend['expected_context_ref']['sha256']
    return module, source, observer


def main():
    os.umask(0o077)
    require(len(sys.argv) == 5 and sys.argv[1] == '--operation' and
            sys.argv[2] == '/input/F08-OPERATION.json' and sys.argv[3] == '--operation-sha256' and
            re.fullmatch('[0-9a-f]{64}', sys.argv[4]) is not None, 'exact Root-bound operation arguments required')
    require(os.getuid() == os.geteuid() == 1000 and os.getgid() == os.getegid() == 1000,
            'actual nonroot1000:1000 actor required')
    require(sys.platform == 'linux' and os.uname().machine == 'x86_64', 'selected Linux x86_64 runtime required')
    require(os.sched_getaffinity(0) == {7}, 'actual HOST CPU7 affinity required')
    require(resource.getrlimit(resource.RLIMIT_AS) == (536870912, 536870912), 'actual inside AS512 profile required')
    require(resource.getrlimit(resource.RLIMIT_CORE) == (0, 0), 'actual inside core0 profile required')
    require(resource.getrlimit(resource.RLIMIT_FSIZE) == (33554432, 33554432), 'actual inside fsize32MiB profile required')
    require(resource.getrlimit(resource.RLIMIT_CPU) == (60, 60), 'actual inside CPU60 profile required')
    require(Path.cwd() == OUT and OUT.is_dir() and not list(OUT.iterdir()), 'fresh disjoint empty /output required')
    operation_identity = file_identity('/input/F08-OPERATION.json', sys.argv[4])
    operation_raw = Path('/input/F08-OPERATION.json').read_bytes()
    require(hashlib.sha256(operation_raw).hexdigest() == sys.argv[4], 'consumed operation DATA digest differs')
    operation = json.loads(operation_raw)
    require(set(operation) == {'schema', 'invocation', 'nonce', 'ready_timeout_seconds',
                               'stop_timeout_seconds', 'payload_argv', 'payload_env', 'payload_cwd', 'provider_context',
                               'backend_binding'},
            'exact operation DATA schema required')
    require(operation['schema'] == 'mckernel.m15.f08.inside-active-kmsg-operation-inputs.v1' and
            operation['invocation'] == '20261112T094452Z-12a4bea0' and
            type(operation['nonce']) is str and re.fullmatch('[0-9a-f]{64}', operation['nonce']) is not None,
            'same invocation and fresh Root-issued nonce required')
    require(operation['payload_argv'] == ARGV and operation['payload_env'] == ENV and
            operation['payload_cwd'] == '/output', 'operation payload binding differs')
    for key in ('ready_timeout_seconds', 'stop_timeout_seconds'):
        value = operation[key]
        require(type(value) in (int, float) and math.isfinite(value) and value > 0,
                'Root-issued positive finite deadline required')
    require(operation['ready_timeout_seconds'] <= 30 and operation['stop_timeout_seconds'] <= 15,
            'bounded active case ready/stop deadlines')
    try:
        owner_module, owner_source, active_observer = bind_active_backend(operation)
        context_before = consumer_context_bookend(operation)
        write_json('CONTEXT-BEFORE.json', context_before)
    except BaseException as context_error:
        raw_context_error = (context_error, BaseException.__dict__['__traceback__'].__get__(context_error, type(context_error)))
        try:
            write_json('CONTEXT-REJECTED.json', {
                'status': 'FAILED_BEFORE_OWNER_CREATION_NO_DAEMON_STARTED',
                'error_type': type(context_error).__name__, 'error': str(context_error),
                'traceback': ''.join(traceback.format_exception(type(context_error), context_error, raw_context_error[1])),
                'operation_input': operation_identity, 'HOST_custody_and_charge': 'EXTERNAL_RETAINED'})
        except BaseException as report_error:
            raw_context_reporting_error = (report_error, BaseException.__dict__['__traceback__'].__get__(report_error, type(report_error)))
        raise
    artifacts = [file_identity(path, sha) for path, sha in (
        ('/usr/local/sbin/ihkmond', PAYLOAD_SHA),
        ('/usr/local/lib64/libihk.so', IHK_SHA),
        ('/usr/lib64/libudev.so.1.7.10', UDEV_SHA),
        ('/usr/lib64/libcap.so.2.69', CAP_SHA))]
    pidfd_module, pidfd_source = load_pinned('/input/pidfd_compat.py', PIDFD_SHA, 'f08_inside_pidfd')
    # Native or selected Linux x86_64 UAPI support is evaluated only HERE.
    pidfd_module.require_implementation()
    pre = snapshot_owner()
    require(pre['tasks'] == [str(os.getpid())], 'dedicated sole-threaded inside Owner required')
    child_file = Path('/proc/self/task') / str(os.getpid()) / 'children'
    require(not child_file.read_text().strip(), 'dedicated child-free inside Owner required')
    write_json('OWNER-BEFORE.json', {'owner': pre, 'artifacts': artifacts,
                                   'owner_source': owner_source, 'pidfd_source': pidfd_source,
                                   'operation_input': operation_identity,
                                   'raw_mountinfo': Path('/proc/self/mountinfo').read_text(),
                                   'runtime': {'python': sys.version, 'uname': list(os.uname())}})
    # Register this exact object before the existing constructor sets subreaper.
    owner = owner_module.ActiveKmsgOwner.__new__(owner_module.ActiveKmsgOwner)
    try:
        owner_module.Owner.__init__(owner, OUT)
        owner._f08_preconstructor_baseline = pre
        owner._f08_operation = {'inputs': operation, 'identity': operation_identity}
        owner._f08_artifacts = artifacts
        owner._f08_active_observer = active_observer
        result = owner.run_ihkmond_active_kmsg(ARGV, ENV, '/output', operation['ready_timeout_seconds'],
                                       operation['stop_timeout_seconds'], 'ihkmond-main-k1-i-1-real-add-remove',
                                       pidfd_api=pidfd_module)
        require(result['status'] == 'PASS' and result['launcher_parent_joined'] and
                result['daemon_parent_joined'] and result['readiness_observed'] and
                result['stop_attempted'] and result['stop_successful'] and result['pidfd_closed'] and
                result['launcher_streams_closed'] and not result['children_after_waits'],
                'actual inside Owner closure is incomplete')
        observation = result['active_kmsg_observation']
        require(observation['ring']['source_literal_present'] is True and
                observation['ring']['before_TERM'] is True and
                observation['notification101_delivery'] == observation['syslog_receiver_delivery'] ==
                observation['hungup_or_status2_delivery'] == 'UNPROVED' and
                observation['full_F08_acceptance'] is False,
                'actual add/remove/ring evidence cannot become notification/syslog/hungup acceptance')
        context_after = consumer_context_bookend(operation)
        require(context_after == context_before, 'selected consumer context changed across real daemon case')
        monitor = result['readiness_raw']['monitor_netlink']
        require(len(monitor) == 1 and monitor[0]['protocol'] == 15 and monitor[0]['groups'] == 2,
                'actual unchanged udev monitor must show protocol15/group2')
        require(file_identity('/input/F08-OPERATION.json', sys.argv[4]) == operation_identity,
                'closed operation input changed across case')
        write_json('CONTEXT-AFTER.json', context_after)
        write_json('RESULT.json', {'status': 'PASS', 'case': 'ihkmond-main-k1-i-1-real-add-remove',
                                  'owner_pid': os.getpid(), 'owner_birth': pre['birth'],
                                  'operation_input': operation_identity, 'case_result': result,
                                  'genuine_context_before': context_before, 'genuine_context_after': context_after,
                                  'actual_monitor_protocol15_group2': True,
                                  'active_kmsg_observation': observation,
                                  'notification101_syslog_hungup_or_fullF08_acceptance': False,
                                  'scope': 'One real mcos0 add/ordinary-boot/remove retained-kmsg observation only',
                                  'HOST_cli_container_Root_join_and_retirement': 'EXTERNAL_UNPROVED',
                                  'F08_or_milestone_acceptance': False})
    except BaseException as exc:
        retain_owner(owner, exc)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
