#!/usr/bin/env python3
"""Own one bounded UID1000 Linux collector rebuild.

Infrastructure only: this owner performs no guest or application acceptance.
The root parent owns the regular shared lock; the private reviewed watchdog
inherits it until the Docker container is removed and absence verified.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import stat
import subprocess
import sys
import time
import traceback

REPO = Path('/home/holden/mckernel')
WORK = Path('/home/holden/mckernel-work')
FIXTURES = REPO / 'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1'
LOCK = Path('/run/lock/mckernel-development.lock')
DOCKER = '/usr/bin/docker'
PYTHON = '/usr/bin/python3'
IMAGE_ID = 'sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94'
IMAGE_MANIFEST_SHA = 'c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a'
ORCHESTRATOR_SHA = '6e6311ac7059eb97f1cba2eb9606bdc7e82016e381cb47a732ca5b274c216ab3'
SUPERVISOR_SHA = 'cba4b4d50d68f9afd5aa8a4c2d830ec0b800f7fd7dfd07774911d5fd1b99c7e7'
HELPER_SHA = '6ae0e29dbebf2593f91b4cfa19a5252a157241b83715b2243826cf528efca0e2'
CGROUP = {
    '/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us': '100000',
    '/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us': '400000',
    '/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes': '12884901888',
    '/sys/fs/cgroup/memory/mckernel-dev/memory.use_hierarchy': '1',
    '/sys/fs/cgroup/pids/mckernel-dev/pids.max': '512',
}
PINNED_INPUTS = {
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/collector.c': '09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/contract.md': '194813f9cd1e49de63afb611c989c8574f3ecdd87c18ea5f634a7d205a88d7f3',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/fixture.c': 'd2c33206cb1dc938b31ef83c5827f3aae2ca4e78740178d0df2f221015bdfc6d',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/root-profile.md': '68350568cca75248a85a3e43cdcf1ca85e1197dff24713aa4fc01128c47ddb52',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/root_inside.py': '1eab68ce627271bb97febfd51c3455e5267280009ad0f1b6249ae92f5d568e19',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/root_profile.py': 'a65d104d76ec7ce3918d667ac02b1cea92c1a80cae321360b01c12190f2f6dd6',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/run_collector_tests.py': '691aee973f9ea5e79cdf7766b87c69e0d5d5a01ff334b8674cd099c776125bb5',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/sha256.c': '8a8a93d4e7f7d1562f044671a673b48e96dc152ad65bd294f082b7b20b4a39e1',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/sha256.h': '52cfafeecb6c411f7df956e6d444068185e17177bd8f21ed1270a2d06ce50e97',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/sha256_harness.c': 'cb5b4634f38be0121254f0ac7080ed134e134d7ada7cbddd4b45315362bd4ce9',
    'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/tests.md': '8d5249cef4565120ffeaad2949a011f32ac2a405b3b95d61a02e7e528236dacc',
    'scripts/tests/fixtures/application-collector-v1/request.c': 'c072005948e479e6f50d3f647bf649301741365d7c034c72d3047df3f85cc3ab',
    'scripts/tests/fixtures/application-collector-v1/request.h': 'e767e217104d3b89b0b6d0f74e37f8150600c0b078d40799e75d14f3ede8d00e',
    'scripts/application-tests/supervisor.py': '8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873',
}
CID = re.compile(r'^[0-9a-f]{64}$')
NONCE = re.compile(r'^[0-9a-f]{32}$')
MAX_FILE = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(actual, expected):
    """Compare daemon JSON values without allowing bool/int aliasing."""
    return type(actual) is type(expected) and actual == expected


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def reviewed_owner():
    path = FIXTURES / 'root_orchestrator.py'
    require(digest(path) == ORCHESTRATOR_SHA, 'reviewed orchestrator drift')
    spec = importlib.util.spec_from_file_location('reviewed_root_orchestrator', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    require(digest(module.FIXTURES / 'supervisor_host38.py') == SUPERVISOR_SHA,
            'reviewed host supervisor drift')
    return module


def stat_identity(value):
    info = value if hasattr(value, 'st_mode') else os.fstat(value)
    return {'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid,
            'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode), 'size': info.st_size,
            'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns, 'links': info.st_nlink}


def directory(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path, 'canonical directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            require(part not in ('', '.', '..'), 'canonical directory component')
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = next_fd
        result, fd = fd, -1
        return result
    finally:
        if fd >= 0: os.close(fd)


def regular(path, maximum=MAX_FILE):
    path = Path(path); parent = directory(path.parent)
    try: fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=parent)
    finally: os.close(parent)
    try:
        before = os.fstat(fd); require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'regular file bound')
        parts = []; total = 0
        while total <= maximum:
            block = os.read(fd, min(65536, maximum + 1 - total))
            if not block: break
            parts.append(block); total += len(block)
        after = os.fstat(fd); require(total == before.st_size and stat_identity(before) == stat_identity(after), 'file changed')
        raw = b''.join(parts)
        return raw, {'path': str(path), **stat_identity(before), 'sha256': hashlib.sha256(raw).hexdigest()}
    finally: os.close(fd)


def write(path, raw):
    path = Path(path); parent = directory(path.parent)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
        try:
            view = memoryview(raw)
            while view:
                n = os.write(fd, view); require(n > 0, 'short artifact write'); view = view[n:]
            os.fsync(fd)
        finally: os.close(fd)
        os.fsync(parent)
    finally: os.close(parent)


def save(path, value):
    write(path, (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key'); result[key] = value
        return result
    def constant(value): raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def expected_create(nonce, mount):
    name = 'mckernel-collector-' + nonce
    return [DOCKER, 'create', '--pull=never', '--init', '--name', name, '--label',
            'mckernel.collector.owner=' + nonce, '--cpus=4', '--cpuset-cpus=2-5',
            '--cgroup-parent=/mckernel-dev', '--memory=12g', '--memory-swap=12g',
            '--pids-limit=512', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--read-only', '--network=none', '--user=1000:1000', '--ulimit', 'core=0',
            '--ulimit', 'nofile=4096:4096', '--tmpfs', '/tmp:rw,nodev,nosuid,size=256m',
            '--mount', 'type=bind,src=' + str(REPO) + ',dst=/workspace,readonly',
            '--mount', 'type=bind,src=' + str(mount) + ',dst=/work', '--env', 'TMPDIR=/work/tmp',
            '--env', 'HOME=/tmp', '--env', 'PYTHONDONTWRITEBYTECODE=1', '--workdir=/work',
            '--entrypoint=/usr/bin/python3', IMAGE_ID, '-B',
            '/workspace/docs/verification/evidence/stability-linux-collector-rebuild-20260915.py']


def one_inspect(raw):
    rows = strict_json(raw); require(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict, 'one inspect row'); return rows[0]


def owned(row, config):
    require(type(row.get('Id')) is str and CID.fullmatch(row['Id']), 'full container ID')
    if config.get('container_id') is not None: require(row['Id'] == config['container_id'], 'container ID changed')
    require(row.get('Name') == '/' + config['name'] and row.get('Image') == IMAGE_ID, 'name/image identity')
    require(row.get('Config', {}).get('Labels', {}).get('mckernel.collector.owner') == config['nonce'], 'owner label')
    return row['Id']


class Commands(reviewed_owner().Commands):
    """Use the reviewed root Commands implementation and its stream oracle."""
    def __init__(self, host, supervisor, deadline=None):
        super().__init__(host, 'owner', supervisor, deadline)


def first_failure(host, phase, error):
    try: save(Path(host) / 'first-failure.json', {'phase': phase, 'type': type(error).__name__, 'message': str(error), 'monotonic': time.monotonic(), 'application_acceptance': False, 'transport_acceptance': False})
    except FileExistsError: pass


def lookup(commands, config, label):
    filters = ['label=mckernel.collector.owner=' + config['nonce'], 'name=^/' + config['name'] + '$']
    if config.get('container_id') is not None: filters.append('id=' + config['container_id'])
    found = []
    for n, value in enumerate(filters):
        raw, _ = commands.run('%s-lookup-%d' % (label, n), [DOCKER, 'container', 'ls', '--all', '--no-trunc', '--filter', value, '--format', '{{.ID}}'])
        lines = raw.decode('ascii').splitlines(); require(len(lines) <= 1 and all(CID.fullmatch(x) for x in lines), 'bounded lookup')
        found.append(lines)
    require(all(row == found[0] for row in found), 'lookup ambiguity')
    if not found[0]: return None
    raw, _ = commands.run(label + '-inspect', [DOCKER, 'inspect', found[0][0]])
    row = one_inspect(raw); owned(row, config); return row


def full_build_inspect(row, config, image=None, retained_image=None):
    cid = owned(row, config)
    helper = '/workspace/docs/verification/evidence/stability-linux-collector-rebuild-20260915.py'
    require(row.get('Path') == PYTHON and row.get('Args') == ['-B', helper], 'actual fixed entry point')
    c, h = row.get('Config'), row.get('HostConfig'); require(type(c) is dict and type(h) is dict, 'complete inspect objects')
    if image is not None:
        inherited = image.get('Config', {})
        require(image.get('Id') == IMAGE_ID and image.get('Architecture') == 'amd64' and image.get('Os') == 'linux', 'immutable image identity')
        if retained_image is not None:
            require(image.get('Config') == retained_image.get('Config') and image.get('RootFS') == retained_image.get('RootFS'), 'immutable image config/rootfs')
        expected_labels = dict(inherited.get('Labels') or {}); expected_labels['mckernel.collector.owner'] = config['nonce']
    else:
        inherited = {}; expected_labels = {'mckernel.collector.owner': config['nonce']}
    for key, value in {'User': '1000:1000', 'Image': IMAGE_ID, 'WorkingDir': '/work',
            'Entrypoint': [PYTHON], 'Cmd': ['-B', helper], 'Labels': expected_labels,
            'Tty': False, 'OpenStdin': False, 'StdinOnce': False, 'AttachStdin': False,
            'Domainname': ''}.items():
        require(same(c.get(key), value), 'container Config.' + key)
    require(c.get('Hostname') == cid[:12] and c.get('Volumes') in (None, {}) and c.get('ExposedPorts') in (None, {}) and c.get('Healthcheck') in (None, {}) and c.get('OnBuild') in (None, []) and c.get('StopSignal') in (None, '', 'SIGTERM'), 'no hidden Config execution')
    allowed_config = {'Hostname', 'Domainname', 'User', 'AttachStdin', 'AttachStdout', 'AttachStderr', 'ExposedPorts', 'Tty', 'OpenStdin', 'StdinOnce', 'Env', 'Cmd', 'Healthcheck', 'ArgsEscaped', 'Image', 'Volumes', 'WorkingDir', 'Entrypoint', 'NetworkDisabled', 'MacAddress', 'OnBuild', 'Labels', 'StopSignal', 'StopTimeout', 'Shell'}
    require(set(c) <= allowed_config, 'unreviewed Config field')
    require(c.get('Shell') in (None, inherited.get('Shell')) and c.get('MacAddress', '') == '' and c.get('StopTimeout') in (None, 10) and c.get('NetworkDisabled', False) is False, 'reviewed inherited config defaults')
    for key in ('AttachStdout', 'AttachStderr', 'ArgsEscaped'):
        require(key not in c or type(c[key]) is bool, 'actual boolean output config')
    env = c.get('Env', []); require(type(env) is list and all(isinstance(item, str) and '=' in item and '\x00' not in item and not item.startswith('LD_') for item in env), 'literal environment')
    values = {}
    for item in env:
        key, value = item.split('=', 1); require(key and key not in values, 'unique environment key'); values[key] = value
    expected_env = {'TMPDIR': '/work/tmp', 'HOME': '/tmp', 'PYTHONDONTWRITEBYTECODE': '1'}
    if image is not None:
        expected_env = dict(item.split('=', 1) for item in (image.get('Config', {}).get('Env') or [])); expected_env.update(TMPDIR='/work/tmp', HOME='/tmp', PYTHONDONTWRITEBYTECODE='1')
    require(values == expected_env, 'exact helper environment')
    expected = {'NetworkMode': 'none', 'Privileged': False, 'ReadonlyRootfs': True, 'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'], 'Memory': 12884901888, 'MemorySwap': 12884901888, 'NanoCpus': 4000000000, 'CpusetCpus': '2-5', 'PidsLimit': 512, 'CgroupParent': '/mckernel-dev', 'Init': True, 'PidMode': '', 'UTSMode': '', 'UsernsMode': '', 'IpcMode': 'private', 'Runtime': 'runc', 'AutoRemove': False, 'PublishAllPorts': False, 'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0}, 'Tmpfs': {'/tmp': 'rw,nodev,nosuid,size=256m'}}
    for key, value in expected.items(): require(same(h.get(key), value), 'actual HostConfig.' + key)
    require(any(same(h.get('GroupAdd'), value) for value in (None, [])), 'no supplemental groups')
    empty = {'Binds', 'ContainerIDFile', 'Links', 'PortBindings', 'VolumesFrom', 'CapAdd', 'GroupAdd', 'Dns', 'DnsOptions', 'DnsSearch', 'ExtraHosts', 'Devices', 'DeviceCgroupRules', 'DeviceRequests', 'Sysctls', 'StorageOpt', 'Annotations', 'VolumeDriver', 'ConsoleSize', 'LxcConf', 'Cgroup', 'CpusetMems', 'Isolation', 'BlkioDeviceReadBps', 'BlkioDeviceWriteBps', 'BlkioDeviceReadIOps', 'BlkioDeviceWriteIOps', 'BlkioWeightDevice'}
    zero = {'CpuShares', 'CpuPeriod', 'CpuQuota', 'CpuRealtimePeriod', 'CpuRealtimeRuntime', 'MemoryReservation', 'KernelMemory', 'KernelMemoryTCP', 'BlkioWeight', 'CpuCount', 'CpuPercent', 'IOMaximumIOps', 'IOMaximumBandwidth'}
    extra = {'Mounts', 'Ulimits', 'MaskedPaths', 'ReadonlyPaths', 'CgroupnsMode', 'ShmSize', 'OomKillDisable', 'MemorySwappiness', 'OomScoreAdj', 'LogConfig'}
    require(set(h) <= set(expected) | empty | zero | extra, 'unreviewed HostConfig field')
    for key in empty:
        if key in h:
            allowed = (None, [0, 0]) if key == 'ConsoleSize' else (None, '', [], {})
            require(any(same(h[key], value) for value in allowed), 'nonempty additional HostConfig.' + key)
    for key in zero:
        if key in h: require(type(h[key]) is int and h[key] == 0, 'additional resource override: ' + key)
    require(h.get('CgroupnsMode') in ('host', 'private', '') and same(h.get('ShmSize'), 67108864) and any(same(h.get('OomKillDisable'), value) for value in (None, False)) and any(same(h.get('MemorySwappiness'), value) for value in (None, -1)) and same(h.get('OomScoreAdj'), 0), 'reviewed daemon namespace/OOM defaults')
    require(h.get('LogConfig') in ({'Type': 'json-file', 'Config': {}}, {'Type': 'local', 'Config': {}}), 'local default Docker log sink')
    require(same(sorted(h.get('Ulimits', []), key=lambda item: item.get('Name', '')), [{'Hard': 0, 'Name': 'core', 'Soft': 0}, {'Hard': 4096, 'Name': 'nofile', 'Soft': 4096}]), 'exact ulimits')
    for key, minimum in (('MaskedPaths', {'/proc/kcore', '/proc/keys', '/proc/latency_stats', '/proc/timer_list', '/proc/scsi', '/sys/firmware'}), ('ReadonlyPaths', {'/proc/bus', '/proc/fs', '/proc/irq', '/proc/sys', '/proc/sysrq-trigger'})):
        paths = h.get(key); require(type(paths) is list and len(paths) == len(set(paths)) and minimum <= set(paths) and all(isinstance(item, str) and item.startswith(('/proc/', '/sys/')) and '..' not in item.split('/') for item in paths), 'daemon protection paths')
    require(type(h.get('Mounts')) is list and len(h['Mounts']) == 2, 'exact requested build mounts')
    pairs = set()
    for item in h['Mounts']:
        require(set(item) <= {'Type', 'Source', 'Target', 'ReadOnly', 'Consistency', 'BindOptions'} and item.get('Type') == 'bind' and item.get('Consistency', '') == '' and item.get('BindOptions') in (None, {}, {'Propagation': 'rprivate'}), 'requested bind options')
        value = item.get('ReadOnly', False); require(type(value) is bool, 'requested bind readonly type')
        pair = (item.get('Source'), item.get('Target'), value); require(pair not in pairs, 'unique requested bind'); pairs.add(pair)
    require(pairs == {(str(REPO), '/workspace', True), (config['mount'], '/work', False)}, 'requested bind identities')
    require(type(row.get('Mounts')) is list and len(row['Mounts']) in (2, 3), 'complete actual build mounts')
    actual_pairs = set()
    tmpfs = 0
    for item in row['Mounts']:
        if item.get('Type') == 'tmpfs':
            require(item.get('Destination') == '/tmp' and item.get('RW') is True and item.get('Source', '') == '', 'only private /tmp tmpfs')
            tmpfs += 1; continue
        require(set(item) <= {'Type', 'Source', 'Destination', 'Driver', 'Mode', 'RW', 'Propagation', 'Name'} and item.get('Type') == 'bind' and type(item.get('RW')) is bool and item.get('Propagation') == 'rprivate', 'actual bind options')
        pair = (item.get('Source'), item.get('Destination'), item.get('RW'), item.get('Propagation')); require(pair not in actual_pairs, 'unique actual bind'); actual_pairs.add(pair)
    require(actual_pairs == {(str(REPO), '/workspace', False, 'rprivate'), (config['mount'], '/work', True, 'rprivate')} and tmpfs <= 1, 'actual private mount identities')
    networks = row.get('NetworkSettings', {}).get('Networks'); require(type(networks) is dict and set(networks) == {'none'}, 'none network')
    require(all(networks['none'].get(key, '') == '' for key in ('IPAddress', 'GlobalIPv6Address', 'Gateway', 'IPv6Gateway', 'MacAddress')), 'no network endpoint')
    require(row.get('NetworkSettings', {}).get('Ports') in (None, {}), 'no published ports')


def mapped(path, output, mount):
    value = Path(path)
    for prefix, target in ((Path('/workspace'), REPO), (Path('/work/stability-linux-collector-build-20260915-2'), output)):
        try: relative = value.relative_to(prefix)
        except ValueError: continue
        require('..' not in relative.parts, 'mapped path')
        return target / relative
    if value.is_absolute() and str(value).startswith('/usr/'): return mount / 'compiler-inputs' / str(value).lstrip('/')
    raise ValueError('unmapped artifact: ' + str(value))


def verify_build_record(mount, host):
    mount, host = Path(mount), Path(host); output = mount / 'stability-linux-collector-build-20260915-2'
    container_output = Path('/work/stability-linux-collector-build-20260915-2')
    raw, record_identity = regular(output / 'record.json'); record = strict_json(raw)
    record_keys = {'schema_version', 'status', 'started_utc', 'finished_utc', 'phase', 'commands', 'inputs',
        'compiler_dependencies', 'compiled_outputs', 'loader_dependencies', 'helper', 'application_acceptance',
        'backend_enabled', 'guest_execution', 'root_positive_execution', 'scope', 'sha_cases', 'builder_cases',
        'clean_launch_requirement'}
    require(set(record) == record_keys and same(record.get('schema_version'), 1), 'exact build record schema')
    expected_scope = 'Pinned Linux collector rebuild after retained close_range/EPERM root failure; SHA9 and builder rejection only'
    require(record.get('status') == 'PASS_LINUX_COLLECTOR_REBUILD_SHA9_BUILDER_NEGATIVE_ONLY' and record.get('application_acceptance') is False and record.get('backend_enabled') is False and record.get('guest_execution') is False and record.get('root_positive_execution') is False and record.get('scope') == expected_scope and record.get('phase') == 'builder-negative' and record.get('clean_launch_requirement') == 'root execution must bind close_fds, empty pass_fds and nofile=4096:4096', 'build-only flags/scope')
    require(len(record.get('inputs', [])) == 14 and len(record.get('compiled_outputs', [])) == 16 and len(record.get('compiler_dependencies', [])) == 176 and len(record.get('commands', [])) == 20, 'exact build counts')
    require(record.get('helper', {}).get('sha256') == HELPER_SHA, 'helper binding')
    verified = []
    def artifact(row):
        require(type(row) is dict and set(row) == {'path', 'size', 'sha256'} and type(row.get('path')) is str and type(row.get('size')) is int and row['size'] >= 0 and type(row.get('sha256')) is str and re.fullmatch(r'[0-9a-f]{64}', row['sha256']), 'artifact row')
        data, identity = regular(mapped(row['path'], output, mount)); require(len(data) == row['size'] and identity['sha256'] == row['sha256'], 'artifact binding'); verified.append(identity)
    artifact(record['helper']); require(record['helper']['path'] == '/workspace/docs/verification/evidence/stability-linux-collector-rebuild-20260915.py' and record['helper']['sha256'] == HELPER_SHA, 'exact helper bytes')
    retained_helper_raw, retained_helper_identity = regular(output / 'helper.py'); require(retained_helper_identity['sha256'] == HELPER_SHA, 'retained helper bytes'); verified.append(retained_helper_identity)
    seen_inputs = set()
    for row in record['inputs']:
        require(type(row) is dict and set(row) == {'original', 'retained'}, 'exact pinned input row')
        original_path = Path(row['original']['path'])
        try:
            relative = str(original_path.relative_to('/workspace'))
        except ValueError:
            raise ValueError('pinned input workspace path')
        require(PINNED_INPUTS.get(relative) == row['original']['sha256'], 'pinned input hash: ' + relative)
        require(relative not in seen_inputs, 'duplicate pinned input: ' + relative); seen_inputs.add(relative)
        if relative == 'scripts/application-tests/supervisor.py': expected_retained = container_output / 'supervisor.py'
        elif relative.startswith('scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/'): expected_retained = container_output / 'source/linux-sealed-v1' / Path(relative).name
        else: expected_retained = container_output / 'source' / Path(relative).name
        require(Path(row['retained']['path']) == expected_retained, 'exact retained input path: ' + relative)
        artifact(row['original']); artifact(row['retained']); require(row['original']['sha256'] == row['retained']['sha256'] and row['original']['size'] == row['retained']['size'], 'retained equality')
    require(seen_inputs == set(PINNED_INPUTS), 'complete pinned input set')
    dependency_originals = set()
    for row in record['compiler_dependencies']:
        require(type(row) is dict and set(row) == {'original', 'retained'} and type(row['original']) is dict and set(row['original']) == {'path', 'size', 'sha256'}, 'compiler dependency row')
        original = Path(row['original']['path']); retained = Path(row['retained']['path'])
        require(str(original).startswith(('/usr/', '/work/stability-linux-collector-build-20260915-2/')), 'compiler dependency must be container path')
        require(type(row['original']['size']) is int and row['original']['size'] >= 0 and re.fullmatch(r'[0-9a-f]{64}', row['original'].get('sha256', '')), 'compiler dependency original identity')
        require(str(original) not in dependency_originals, 'duplicate compiler dependency')
        dependency_originals.add(str(original))
        require(retained == container_output / 'compiler-inputs' / str(original).lstrip('/'), 'compiler dependency retained path')
        artifact(row['retained']); require(row['original']['sha256'] == row['retained']['sha256'] and row['original']['size'] == row['retained']['size'], 'retained equality')
    expected_outputs = {str(container_output / (name + suffix)) for name in ('request', 'sha256', 'collector', 'fixture', 'sha256_harness') for suffix in ('.o', '.d')}
    expected_outputs.update(str(container_output / (name + suffix)) for name in ('linux-collector', 'fixture', 'sha256-harness') for suffix in ('', '.map'))
    require({row.get('path') for row in record['compiled_outputs']} == expected_outputs, 'exact compiled output set')
    for row in record['compiled_outputs']: artifact(row)
    dependency_files = set()
    for name in ('request', 'sha256', 'collector', 'fixture', 'sha256_harness'):
        dep_raw, _ = regular(output / (name + '.d'))
        text_value = dep_raw.decode('utf-8').split(':', 1); require(len(text_value) == 2, 'compiler dependency file syntax')
        for item in shlex.split(text_value[1].replace('\\\n', ' ')):
            dep = Path(item)
            if not dep.is_absolute(): dep = container_output / dep
            dep = Path(os.path.normpath(str(dep)))
            require(dep.is_absolute() and '..' not in dep.parts, 'canonical compiler dependency')
            dependency_files.add(str(dep))
    require(dependency_files == dependency_originals, 'exact compiler dependency-file membership')
    expected_labels = ['compiler-version'] + ['compile-' + name for name in ('request', 'sha256', 'collector', 'fixture', 'sha256_harness')]
    expected_labels += [phase + '-' + name for name in ('linux-collector', 'fixture', 'sha256-harness') for phase in ('link', 'elf', 'disassembly', 'loader')]
    expected_labels += ['sha9', 'builder-negative']
    root = str(container_output)
    def p(name): return root + '/' + name
    expected_argv = [[ '/usr/bin/gcc', '--version' ]]
    for name, src in (('request', 'source/request.c'), ('sha256', 'source/linux-sealed-v1/sha256.c'), ('collector', 'source/linux-sealed-v1/collector.c'), ('fixture', 'source/linux-sealed-v1/fixture.c'), ('sha256_harness', 'source/linux-sealed-v1/sha256_harness.c')):
        expected_argv.append(['/usr/bin/gcc', '-std=c11', '-D_GNU_SOURCE', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-fno-pie', '-MD', '-MF', p(name + '.d'), '-c', p(src), '-o', p(name + '.o')])
    for name, objects in (('linux-collector', ('request.o', 'sha256.o', 'collector.o')), ('fixture', ('fixture.o',)), ('sha256-harness', ('sha256.o', 'sha256_harness.o'))):
        expected_argv.append(['/usr/bin/gcc', '-no-pie'] + [p(obj) for obj in objects] + ['-Wl,-Map=' + p(name + '.map'), '-o', p(name)])
        expected_argv.append(['/usr/bin/readelf', '-h', '-l', '-d', p(name)])
        expected_argv.append(['/usr/bin/objdump', '-d', p(name)])
        expected_argv.append(['/usr/bin/ldd', p(name)])
    expected_argv += [[p('sha256-harness')], ['/usr/bin/python3', '-B', p('source/linux-sealed-v1/run_collector_tests.py'), '--collector', p('linux-collector'), '--fixture', p('fixture'), '--supervisor', p('supervisor.py'), '--attempt-root', p('builder-negative'), '--builder-only']]
    require([row.get('label') for row in record['commands']] == expected_labels and [row.get('argv') for row in record['commands']] == expected_argv, 'exact build command sequence/argv')
    exact_env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C', 'TZ': 'UTC', 'TMPDIR': p('tmp')}
    for index, row in enumerate(record['commands']):
        label, argv = expected_labels[index], expected_argv[index]
        require(type(row) is dict and set(row) == {'label', 'argv', 'environment', 'collection'}, 'exact command row schema: ' + label)
        require(row.get('environment') == exact_env, 'exact outer command environment: ' + label)
        collection = row['collection']; require(collection.get('status') == 'COMPLETED' and type(collection.get('raw_wait_status')) is int and collection.get('raw_wait_status') == 0 and collection.get('cleanup_complete') is True and collection.get('application_acceptance') is False, 'build command result')
        for clock in ('payload_monotonic_started', 'payload_monotonic_deadline', 'payload_completion_observed_monotonic'):
            require(type(collection.get(clock)) in (int, float) and math.isfinite(collection[clock]), 'finite command clock: ' + label)
        require(collection['payload_monotonic_started'] <= collection['payload_completion_observed_monotonic'] < collection['payload_monotonic_deadline'], 'command observed before exclusive deadline: ' + label)
        require(collection.get('argv') == argv and collection.get('cwd') == root and collection.get('env') == exact_env, 'exact collected command context: ' + label)
        require(collection.get('uid') == 1000 and collection.get('gid') == 1000 and collection.get('groups') == [1000] and collection.get('stdin') == {'kind': 'devnull'} and collection.get('stdin_path') is None, 'exact collected command identity: ' + label)
        require(collection.get('wait_status') == {'kind': 'exited', 'code': 0} and collection.get('descendants') == [] and collection.get('descendant_records_omitted') == 0, 'exact command exit/descendants: ' + label)
        limit = 65536 if label == 'sha9' else 8 * 1024 * 1024
        timeout = 10.0 if label == 'sha9' else (60.0 if label == 'builder-negative' else 120.0)
        require(collection.get('stdout_limit_bytes') == limit and collection.get('stderr_limit_bytes') == limit and collection.get('timeout_seconds') == timeout and collection.get('cleanup_timeout_seconds') == 15.0, 'exact collection bounds: ' + label)
        for stream_name in ('stdout', 'stderr'):
            stream = collection.get('streams', {}).get(stream_name); require(type(stream) is dict, 'stream row: ' + label)
            stream_artifact = stream.get('artifact'); artifact(stream_artifact)
            require(stream_artifact['path'] == p(label + '-collection/' + stream_name + '.bin'), 'exact stream destination: ' + label)
            for counter in ('bytes_observed', 'bytes_retained', 'discarded_observed_bytes', 'limit_bytes'):
                require(type(stream.get(counter)) is int, 'plain stream counter: ' + label)
            require(stream.get('eof') is True and stream.get('truncated') is False and stream.get('discarded_observed_bytes') == 0 and stream.get('limit_bytes') == limit and stream.get('bytes_observed') == stream_artifact['size'] and stream.get('bytes_retained') == stream_artifact['size'], 'complete stream retention: ' + label)
    require(record.get('sha_cases') == 9 and record.get('builder_cases') == 1, 'SHA9/builder counts')
    sha9_stdout = b'PASS empty\nPASS abc\nPASS multi-56\nPASS boundary-55\nPASS boundary-56\nPASS boundary-63\nPASS boundary-64\nPASS boundary-65\nPASS rejected-update-preserves-state\n'
    sha9_out, _ = regular(mapped(record['commands'][-2]['collection']['streams']['stdout']['artifact']['path'], output, mount)); sha9_err, _ = regular(mapped(record['commands'][-2]['collection']['streams']['stderr']['artifact']['path'], output, mount))
    require(sha9_out == sha9_stdout and sha9_err == b'', 'literal SHA9 stdout/stderr')
    builder_out, _ = regular(mapped(record['commands'][-1]['collection']['streams']['stdout']['artifact']['path'], output, mount)); builder_err, _ = regular(mapped(record['commands'][-1]['collection']['streams']['stderr']['artifact']['path'], output, mount)); require(builder_out == b'PASS builder-identity\nRETAINED /work/stability-linux-collector-build-20260915-2/builder-negative\n' and builder_err == b'', 'literal builder stdout/stderr')
    builder_raw, builder_identity = regular(output / 'builder-negative/result.json'); verified.append(builder_identity); builder = strict_json(builder_raw)
    require(set(builder) == {'application_acceptance', 'backend_enabled', 'cases', 'euid', 'inputs', 'kind', 'schema_version', 'status', 'uid'} and same(builder.get('schema_version'), 1) and builder.get('kind') == 'actual-linux-sealed-collector-infrastructure-tests', 'exact builder result schema')
    require(builder.get('status') == 'PASS_INFRASTRUCTURE_ONLY' and builder.get('application_acceptance') is False and builder.get('backend_enabled') is False and builder.get('uid') == 1000 and builder.get('euid') == 1000, 'builder infrastructure-only result')
    require(builder.get('cases') == [{'case': 'builder-identity', 'observed_status': 'BLOCKED', 'status': 'PASS_INFRASTRUCTURE_ONLY'}], 'exact builder case')
    require(type(builder.get('inputs')) is list and len(builder['inputs']) == 4, 'exact builder inputs')
    builder_expected = {p('linux-collector'), p('fixture'), p('supervisor.py'), p('source/linux-sealed-v1/run_collector_tests.py')}
    require({row.get('path') for row in builder['inputs']} == builder_expected and all(type(row) is dict and set(row) == {'path', 'size_bytes', 'sha256'} and type(row.get('size_bytes')) is int and re.fullmatch(r'[0-9a-f]{64}', row.get('sha256', '')) for row in builder['inputs']), 'exact builder input identities')
    for row in builder['inputs']:
        data, identity = regular(mapped(row['path'], output, mount)); require(len(data) == row['size_bytes'] and identity['sha256'] == row['sha256'], 'builder input artifact binding')
    expected_loaders = [
        {'path': '/lib64/libc.so.6', 'size': 2339896, 'sha256': 'b058f87d66478fec923f183c89ac2abd008c4ab5fc6cc5096676b921bb5addd4'},
        {'path': '/lib64/ld-linux-x86-64.so.2', 'size': 930600, 'sha256': '0853c866a70b198f4d3b0ccb7350e0356f6bf1f8340a69b9b728128c13bb7c1b'},
    ]
    loaders = record.get('loader_dependencies'); require(loaders == expected_loaders, 'exact immutable-image loader identities')
    write(host / 'build-record.json', raw); save(host / 'build-bindings.json', {'record': record_identity, 'verified': verified, 'loader_scope': 'container-only immutable image paths', 'application_acceptance': False, 'transport_acceptance': False})
    return record, record_identity


def recovery_journal(host, prefix, state):
    number = state['attempts'][-1]['number']; write(Path(host) / ('%s-recovery-%03d.json' % (prefix, number)), (json.dumps(state, indent=2, sort_keys=True) + '\n').encode())


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--attempt-number', type=int, required=True); parser.add_argument('--owner-sha256', required=True); args = parser.parse_args()
    require(os.getuid() == os.geteuid() == 0 and 1 <= args.attempt_number <= 999999, 'root bounded attempt')
    owner_path = Path(__file__).resolve(); require(digest(owner_path) == args.owner_sha256, 'owner source identity')
    helper = REPO / 'docs/verification/evidence/stability-linux-collector-rebuild-20260915.py'; require(digest(helper) == HELPER_SHA, 'helper source identity')
    reviewed = reviewed_owner(); suffix = '20260915-%d' % args.attempt_number
    host = WORK / ('scratch/stability-linux-collector-build-owner-' + suffix); mount = WORK / ('scratch/stability-linux-collector-build-mount-' + suffix)
    require(not host.exists() and not host.is_symlink() and not mount.exists() and not mount.is_symlink(), 'fresh paths')
    os.umask(0o077); host.mkdir(mode=0o700); (host / 'docker-home').mkdir(mode=0o700); (host / 'docker-config').mkdir(mode=0o700); mount.mkdir(mode=0o700); os.chown(mount, 1000, 1000); os.chmod(mount, 0o700); mount_identity = os.stat(mount); require(mount_identity.st_uid == 1000 and mount_identity.st_gid == 1000 and stat.S_IMODE(mount_identity.st_mode) == 0o700, 'UID1000 build mount identity')
    lock_fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600); require(stat.S_ISREG(os.fstat(lock_fd).st_mode) and os.fstat(lock_fd).st_uid == 0 and os.fstat(lock_fd).st_nlink == 1, 'root regular lock'); fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    nonce = os.urandom(16).hex(); name = 'mckernel-collector-' + nonce
    config = {'host': str(host), 'mount': str(mount), 'nonce': nonce, 'name': name, 'image': IMAGE_ID, 'container_id': None, 'application_acceptance': False, 'transport_acceptance': False}
    result = {'status': 'FAIL', 'application_acceptance': False, 'transport_acceptance': False, 'backend_enabled': False, 'diagnostic_errors': [], 'watchdog_raw_wait_status': None}
    commands = watch = control = supervisor = None
    def interrupted(number, _frame):
        error = RuntimeError('owner signal ' + str(number))
        result['diagnostic_errors'].append(str(error)); first_failure(host, 'owner-signal', error)
        raise KeyboardInterrupt(str(error))
    for signal_number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(signal_number, interrupted)
    try:
        supervisor_path = FIXTURES / 'supervisor_host38.py'; supervisor_raw, supervisor_identity = regular(supervisor_path); require(supervisor_identity['sha256'] == SUPERVISOR_SHA, 'supervisor identity'); write(host / 'supervisor.py', supervisor_raw); orchestrator_raw, orchestrator_identity = regular(FIXTURES / 'root_orchestrator.py'); require(orchestrator_identity['sha256'] == ORCHESTRATOR_SHA, 'orchestrator identity'); write(host / 'root_orchestrator.py', orchestrator_raw)
        spec = importlib.util.spec_from_file_location('owner_supervisor', host / 'supervisor.py'); supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor); commands = Commands(host, supervisor)
        save(host / 'docker-client.json', commands.docker_identity); commands.run('mountpoint', ['/usr/bin/mountpoint', '-q', str(WORK / 'scratch')]); label, _ = commands.run('scratch-label', ['/usr/bin/findmnt', '-n', '-o', 'LABEL', '--target', str(WORK / 'scratch')]); require(label == b'mckernel-scratch\n', 'scratch label')
        cgroup = {path: Path(path).read_text().strip() for path in CGROUP}; require(cgroup == CGROUP, 'exact cgroup')
        image_manifest_raw, image_manifest_identity = regular(WORK / 'logs/image-native.json', 4 * 1024 * 1024); require(image_manifest_identity['sha256'] == IMAGE_MANIFEST_SHA, 'image manifest'); retained_image = strict_json(image_manifest_raw)[0]; require(retained_image.get('Id') == IMAGE_ID, 'manifest image ID'); image_raw, _ = commands.run('image-inspect', [DOCKER, 'image', 'inspect', IMAGE_ID]); image = one_inspect(image_raw); require(image.get('Config') == retained_image.get('Config') and image.get('RootFS') == retained_image.get('RootFS'), 'image manifest/config/rootfs binding')
        require(lookup(commands, config, 'precreate') is None, 'fresh lookup'); create = expected_create(nonce, mount); save(host / 'create-argv.json', {'argv': create, 'application_acceptance': False}); result['create_submitted_monotonic'] = time.monotonic(); created, _ = commands.run('create', create); require(re.fullmatch(rb'[0-9a-f]{64}\n', created), 'create full ID')
        config.update(container_id=created[:-1].decode('ascii'), orchestrator_sha256=ORCHESTRATOR_SHA, deadline_monotonic=time.monotonic() + 300); config['disarm'] = 'DISARM ' + nonce + ' ' + config['container_id'] + '\n'; config_raw = (json.dumps(config, sort_keys=True, allow_nan=False) + '\n').encode(); write(host / 'watchdog-config.json', config_raw); config_identity = regular(host / 'watchdog-config.json')[1]
        row = lookup(commands, config, 'before-start'); require(row is not None and row['State']['Status'] == 'created' and row['State']['Running'] is False, 'created state'); full_build_inspect(row, config, image, retained_image); require(regular(host / 'watchdog-config.json')[1] == config_identity, 'immutable watchdog config')
        read_fd, control = os.pipe2(os.O_CLOEXEC); out = os.open(host / 'watchdog.stdout.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600); err = os.open(host / 'watchdog.stderr.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        try: watch = subprocess.Popen([PYTHON, '-I', '-B', str(host / 'root_orchestrator.py'), '--watchdog', str(host / 'watchdog-config.json'), str(read_fd), str(lock_fd)], stdin=subprocess.DEVNULL, stdout=out, stderr=err, env={}, close_fds=True, pass_fds=(read_fd, lock_fd), start_new_session=True)
        finally: os.close(read_fd); os.close(out); os.close(err)
        deadline = time.monotonic() + 5
        while not (host / 'watchdog-ready.json').exists() and time.monotonic() < deadline:
            require(os.waitid(os.P_PID, watch.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None, 'watchdog early exit'); time.sleep(0.01)
        ready = strict_json(regular(host / 'watchdog-ready.json')[0]); actual = supervisor._process_identity(watch.pid); require(ready['pid'] == watch.pid and ready['subreaper'] is True and ready['deadline_monotonic'] == config['deadline_monotonic'] and ready['lock_identity'] == stat_identity(lock_fd) and digest(host / 'root_orchestrator.py') == ORCHESTRATOR_SHA and actual['ppid'] == os.getpid() and actual['pgid'] == actual['session'] == watch.pid and all(ready['identity'][key] == actual[key] for key in ('pid', 'ppid', 'pgid', 'session', 'starttime_ticks')), 'watchdog identity gate'); result['watchdog_process'] = actual
        _, attached = commands.run('start-attach', [DOCKER, 'start', '--attach', config['container_id']], config['deadline_monotonic'] - time.monotonic()); require(attached['payload_completion_observed_monotonic'] < config['deadline_monotonic'], 'attach deadline')
        row = lookup(commands, config, 'after-exit'); require(row is not None, 'retained exit'); full_build_inspect(row, config, image, retained_image); state = row['State']; require(state.get('Status') == 'exited' and state.get('Running') is False and state.get('Paused') is False and state.get('Restarting') is False and state.get('OOMKilled') is False and state.get('Dead') is False and state.get('ExitCode') == 0 and state.get('Error') == '', 'normal exited state'); record, ident = verify_build_record(mount, host); result.update(collected_infrastructure_candidate=True, build_record_sha256=ident['sha256'], build_status=record['status'])
    except BaseException as error:
        result['first_failure'] = {'type': type(error).__name__, 'message': str(error)}; first_failure(host, 'owner', error); save(host / 'owner-error.json', {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()})
    finally:
        def cleanup_signal(number, _frame):
            message = 'signal ' + str(number); result['diagnostic_errors'].append(message); first_failure(host, 'cleanup-signal', RuntimeError(message))
        for signal_number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(signal_number, cleanup_signal)
        if commands is not None and result.get('create_submitted_monotonic') is not None:
            try: result['cleanup'] = reviewed.recover_cleanup(commands, config, 'owner-final', journal=lambda state: recovery_journal(host, 'owner-final', state))
            except BaseException as error: result['diagnostic_errors'].append(str(error)); first_failure(host, 'cleanup', error)
        if control is not None and result.get('cleanup', {}).get('absence_verified') is True:
            try: os.write(control, config['disarm'].encode())
            except BaseException as error: result['diagnostic_errors'].append(str(error)); first_failure(host, 'disarm', error)
        if control is not None: os.close(control); control = None
        if watch is not None:
            try:
                end = time.monotonic() + 210
                while time.monotonic() < end:
                    pid, raw = os.waitpid(watch.pid, os.WNOHANG)
                    if pid: result['watchdog_raw_wait_status'] = raw; break
                    time.sleep(0.05)
                if result['watchdog_raw_wait_status'] is None: result['diagnostic_errors'].append('watchdog wait expired'); result['watchdog_rescue'] = supervisor._rescue_worker(watch, 15)
                require(result['watchdog_raw_wait_status'] == 0, 'watchdog raw zero'); watcher = strict_json(regular(host / 'watchdog-result.json')[0]); require(watcher.get('status') == 'DISARMED_AFTER_VERIFIED_ABSENCE', 'watchdog status')
            except BaseException as error: result['diagnostic_errors'].append(str(error)); first_failure(host, 'watchdog-reap', error)
        try:
            trees = [reviewed.inventory(host)];
            if mount.exists(): trees.append(reviewed.inventory(mount))
            save(host / 'original-tree-inventory.json', {'trees': trees, 'ownership_changed': False, 'root_owned_output_preserved': True, 'application_acceptance': False})
        except BaseException as error: result['diagnostic_errors'].append(str(error)); first_failure(host, 'inventory', error)
        cleanup = result.get('cleanup', {})
        if result.get('collected_infrastructure_candidate') is True and not result.get('first_failure') and not result.get('diagnostic_errors') and not (host / 'first-failure.json').exists() and cleanup.get('absence_verified') is True and cleanup.get('evidence_complete') is True and cleanup.get('first_failure') is None and result.get('watchdog_raw_wait_status') == 0: result['status'] = 'PASS_LINUX_COLLECTOR_BUILD_OWNER_INFRASTRUCTURE_ONLY'
        result['finished_monotonic'] = time.monotonic(); save(host / 'result.json', result)
        if cleanup.get('absence_verified') is True and result.get('watchdog_raw_wait_status') == 0: os.close(lock_fd)
    print(result['status'] + ' ' + str(host), flush=True); return 0 if result['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '--watchdog': reviewed_owner().watchdog(Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
    raise SystemExit(main())
