#!/usr/bin/env python3
"""Exact isolated root collector attempt. Host root only; no catalog acceptance."""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import select
import signal
import stat
import subprocess
import sys
import time
import traceback


REPO = Path('/home/holden/mckernel')
WORK = Path('/home/holden/mckernel-work')
BUILD = WORK / 'scratch/stability-linux-collector-build-20260913-1'
FIXTURES = REPO / 'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1'
LOCK = Path('/run/lock/mckernel-development.lock')
DOCKER = '/usr/bin/docker'
PYTHON = '/usr/bin/python3'
BUILD_SHA = '72ad1e2e01b00c9ccb664096d8c81852f8892b7eb87dab894dc0f59e5d23f783'
IMAGE_SHA = 'c881faf78539b1698aa9cfe24e0b82562442a58de18666bf59a447b72607e95a'
IMAGE_ID = 'sha256:46d47ba9223a03f4c99db99758b741b2b58694a44cc083e13d4a7e7c78edfd94'
PLANNER_SHA = 'a65d104d76ec7ce3918d667ac02b1cea92c1a80cae321360b01c12190f2f6dd6'
SUPERVISOR_SHA = '8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873'
HOST_SUPERVISOR_SHA = 'cba4b4d50d68f9afd5aa8a4c2d830ec0b800f7fd7dfd07774911d5fd1b99c7e7'
MAX_FILE = 16 * 1024 * 1024
MAX_TREE = 256 * 1024 * 1024
MAX_MEMBERS = 8192
CID = re.compile(r'[0-9a-f]{64}')
NONCE = re.compile(r'[0-9a-f]{32}')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def same(actual, expected):
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return set(actual) == set(expected) and all(same(actual[key], value) for key, value in expected.items())
    if type(expected) is list:
        return len(actual) == len(expected) and all(same(a, b) for a, b in zip(actual, expected))
    return actual == expected


def pairs(rows):
    result = {}
    for key, value in rows:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def strict_json(raw):
    def bad(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)


def directory(path):
    require(path.is_absolute() and path.resolve(strict=True) == path, 'canonical directory')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = next_fd
        result = fd; fd = -1
        return result
    finally:
        if fd >= 0:
            os.close(fd)


def stat_identity(info):
    return {'device': info.st_dev, 'inode': info.st_ino, 'uid': info.st_uid,
            'gid': info.st_gid, 'mode': stat.S_IMODE(info.st_mode), 'size': info.st_size,
            'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns,
            'links': info.st_nlink}


def regular(path, maximum=MAX_FILE):
    parent = directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
    finally:
        os.close(parent)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum, 'regular file bound: ' + str(path))
        chunks = []; total = 0
        while total <= maximum:
            part = os.read(fd, min(65536, maximum + 1 - total))
            if not part:
                break
            chunks.append(part); total += len(part)
        after = os.fstat(fd)
        require(total == before.st_size and stat_identity(before) == stat_identity(after), 'file changed: ' + str(path))
        raw = b''.join(chunks)
        return raw, {'path': str(path), **stat_identity(before), 'sha256': hashlib.sha256(raw).hexdigest()}
    finally:
        os.close(fd)


def write(path, raw):
    parent = directory(path.parent)
    try:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent)
        try:
            view = memoryview(raw)
            while view:
                count = os.write(fd, view)
                require(count > 0, 'short retained artifact write')
                view = view[count:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(parent)
    finally:
        os.close(parent)


def save(path, value):
    write(path, (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())


def first_failure(host, phase, error):
    record = {'phase': phase, 'monotonic': time.monotonic(), 'type': type(error).__name__,
              'message': str(error), 'application_acceptance': False, 'transport_acceptance': False}
    try:
        save(host / 'first-failure.json', record)
        print('FIRST_FAILURE ' + str(host / 'first-failure.json') + ' ' + phase, flush=True)
    except FileExistsError:
        pass


def safe_first_failure(host, phase, error, sink):
    """Diagnostics never escape an ownership/recovery boundary."""
    try:
        first_failure(host, phase, error)
    except BaseException as diagnostic:
        if len(sink) < 32:
            sink.append({'phase': phase, 'type': type(diagnostic).__name__,
                         'message': str(diagnostic)[:1024]})


def load_source(path, expected, name):
    raw, identity = regular(path)
    require(identity['sha256'] == expected, 'frozen source identity: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(regular(path)[1] == identity, 'source changed during import')
    return module


def collection_ok(report, root, *, zero=True):
    require(type(report) is dict and report.get('status') == 'COMPLETED' and
            report.get('cleanup_complete') is True and report.get('application_acceptance') is False,
            'complete command collection/cleanup')
    raw = report.get('raw_wait_status')
    require(type(raw) is int and os.WIFEXITED(raw), 'actual normal command wait')
    if zero:
        require(raw == 0, 'actual zero command exit')
    for key in ('payload_monotonic_started', 'payload_monotonic_deadline', 'payload_completion_observed_monotonic'):
        require(type(report.get(key)) in (int, float) and math.isfinite(report[key]), 'finite observed command clock')
    require(report['payload_monotonic_started'] <= report['payload_completion_observed_monotonic'] <
            report['payload_monotonic_deadline'], 'command observed before exclusive deadline')
    streams = report.get('streams')
    require(type(streams) is dict, 'command streams')
    for name in ('stdout', 'stderr'):
        row = streams.get(name)
        require(type(row) is dict and row.get('eof') is True and row.get('truncated') is False,
                'complete command stream')
        data, identity = regular(root / (name + '.bin'), 1024 * 1024)
        for field in ('bytes_observed', 'bytes_retained', 'discarded_observed_bytes'):
            require(type(row.get(field)) is int, 'plain stream counter')
        require(row['bytes_observed'] == row['bytes_retained'] == len(data) and row['discarded_observed_bytes'] == 0,
                'complete retained command bytes')
        require(row['artifact']['sha256'] == identity['sha256'] and row['artifact']['size'] == len(data), 'stream artifact binding')


class Commands:
    def __init__(self, host, prefix, supervisor, deadline=None):
        self.host, self.prefix, self.supervisor = host, prefix, supervisor
        self.number = 0
        self.deadline = deadline
        self.env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
                    'HOME': str(host / 'docker-home'), 'DOCKER_CONFIG': str(host / 'docker-config'),
                    'DOCKER_HOST': 'unix:///var/run/docker.sock', 'PYTHONDONTWRITEBYTECODE': '1'}
        self.docker_identity = regular(Path(DOCKER).resolve(strict=True), 64 * 1024 * 1024)[1]

    def run(self, label, argv, seconds=15, *, zero=True):
        require(self.number < 96 and type(argv) is list and argv[0] in (DOCKER, PYTHON, '/usr/bin/mountpoint', '/usr/bin/findmnt'), 'bounded exact command family')
        self.number += 1
        target = self.host / f'{self.prefix}-{self.number:03d}-{label}'
        if argv[0] == DOCKER:
            require(regular(Path(DOCKER).resolve(strict=True), 64 * 1024 * 1024)[1] == self.docker_identity, 'Docker client changed')
        if self.deadline is not None:
            seconds = min(seconds, self.deadline - time.monotonic() - 16)
        require(seconds >= 1, 'command phase budget exhausted')
        try:
            report = self.supervisor.run_supervised(argv, cwd=str(self.host), env=self.env, attempt_dir=target,
                timeout_seconds=seconds, cleanup_timeout_seconds=15,
                stdout_limit_bytes=1024 * 1024, stderr_limit_bytes=1024 * 1024)
            save(self.host / (target.name + '-returned.json'), report)
            collection_ok(report, target, zero=zero)
            return regular(target / 'stdout.bin', 1024 * 1024)[0], report
        except BaseException as error:
            first_failure(self.host, self.prefix + ':' + label, error)
            raise


def mapped(path):
    value = Path(path)
    for prefix, target in ((Path('/workspace'), REPO),
                           (Path('/work/stability-linux-collector-build-20260913-1'), BUILD)):
        try:
            relative = value.relative_to(prefix)
        except ValueError:
            continue
        require('..' not in relative.parts, 'canonical retained build reference')
        return target / relative
    raise ValueError('unmapped retained build reference: ' + path)


def bind_build(host):
    raw, identity = regular(BUILD / 'record.json')
    require(identity['sha256'] == BUILD_SHA, 'exact actual build record')
    record = strict_json(raw)
    require(record['status'] == 'PASS_LINUX_COLLECTOR_BUILD_SHA9_BUILDER_NEGATIVE_ONLY' and
            record['application_acceptance'] is False and record['backend_enabled'] is False and
            record['root_positive_execution'] is False, 'build-only prerequisites')
    write(host / 'build-record.json', raw)
    checks = []
    def verify(row, copy_name=None):
        source = mapped(row['path'])
        data, actual = regular(source)
        require(type(row['size']) is int and len(data) == row['size'] and actual['sha256'] == row['sha256'], 'build artifact binding: ' + str(source))
        checks.append(actual)
        if copy_name is not None:
            write(host / copy_name, data)
    require(len(record['inputs']) == 14 and len(record['compiled_outputs']) == 16 and
            len(record['compiler_dependencies']) == 176 and len(record['commands']) == 20, 'exact retained build inventory')
    for row in record['inputs']:
        verify(row['original']); verify(row['retained'])
    for row in record['compiler_dependencies']:
        verify(row['retained'])
        require(row['retained']['sha256'] == row['original']['sha256'] and
                row['retained']['size'] == row['original']['size'], 'archived compiler input identity')
    for row in record['compiled_outputs']:
        verify(row)
    for row in record['commands']:
        collection = row['collection']
        require(collection['status'] == 'COMPLETED' and type(collection['raw_wait_status']) is int and
                collection['raw_wait_status'] == 0 and collection['cleanup_complete'] is True,
                'actual build command result')
        for name in ('stdout', 'stderr'):
            verify(collection['streams'][name]['artifact'])
    verify(record['source_review'], 'build-source-review.json')
    save(host / 'build-bindings.json', {'build_record': identity, 'verified': checks,
         'container_only_loader_references': record['loader_dependencies'],
         'loader_scope': 'exact same immutable image required; no host substitution for container library paths',
         'application_acceptance': False})
    return checks


def expected_create(profile, nonce):
    name = 'mckernel-collector-' + nonce
    return [DOCKER, 'create', '--pull=never', '--init', '--name', name, '--label', 'mckernel.collector.owner=' + nonce,
        '--cpus=4', '--cpuset-cpus=2-5', '--cgroup-parent=/mckernel-dev', '--memory=12g', '--memory-swap=12g',
        '--pids-limit=512', '--cap-drop=ALL', '--security-opt=no-new-privileges', '--read-only', '--network=none',
        '--user=0:0', '--group-add=0', '--ulimit', 'core=0', '--ulimit', 'nofile=4096:4096',
        '--tmpfs', '/tmp:rw,nodev,nosuid,size=256m', '--mount', 'type=bind,src=' + str(REPO) + ',dst=/workspace,readonly',
        '--mount', 'type=bind,src=' + str(profile / 'inputs') + ',dst=/inputs,readonly',
        '--mount', 'type=bind,src=' + str(profile / 'work') + ',dst=/work',
        '--env', 'TMPDIR=/work/tmp', '--env', 'HOME=/tmp', '--env', 'PYTHONDONTWRITEBYTECODE=1',
        '--workdir=/work', '--entrypoint=/usr/bin/python3', IMAGE_ID, '/inputs/root_inside.py']


def plan_check(plan, profile, host):
    require(type(plan) is dict and type(plan.get('schema_version')) is int and plan['schema_version'] == 1 and
            plan['kind'] == 'linux-sealed-root-container-command-plan' and plan['status'] == 'PREPARED_NOT_EXECUTED' and
            plan['application_acceptance'] is False and plan['backend_enabled'] is False, 'exact planner schema/status')
    nonce = plan['profile_nonce']
    require(type(nonce) is str and NONCE.fullmatch(nonce) is not None, 'random owner nonce')
    name = 'mckernel-collector-' + nonce
    require(plan['container_name'] == name and plan['root'] == str(profile) and plan['required_lock'] == str(LOCK), 'plan ownership paths')
    commands = {'image_inspect': [DOCKER, 'image', 'inspect', IMAGE_ID], 'create': expected_create(profile, nonce),
                'inspect_before_start': [DOCKER, 'inspect', name], 'start_attach': [DOCKER, 'start', '--attach', name],
                'inspect_after_exit': [DOCKER, 'inspect', name], 'stop_owned': [DOCKER, 'stop', '--time=20', name],
                'remove_owned': [DOCKER, 'rm', '--force', name], 'inspect_removed': [DOCKER, 'inspect', name]}
    require(plan['commands'] == commands, 'exact complete argv plan; no extra flags')
    require(plan['command_limits_seconds'] == {'image_inspect': 15, 'create': 30, 'inspect_before_start': 15,
            'start_attach': 300, 'inspect_after_exit': 15, 'stop_owned': 30, 'remove_owned': 30, 'inspect_removed': 15}, 'exact command limits')
    require(plan['image_identity']['sha256'] == IMAGE_SHA and plan['helper_identity']['sha256'] == PLANNER_SHA,
            'planner/image input identities')
    require(regular(profile / 'original-container-run.py')[0] == regular(WORK / 'setup/container-run.py')[0], 'original wrapper preservation')
    require(regular(profile / 'root-profile-helper.py')[0] == regular(host / 'root_profile.py')[0], 'retained planner identity')
    return {'schema_version': 1, 'host': str(host), 'profile': str(profile), 'nonce': nonce,
            'name': name, 'image': IMAGE_ID, 'container_id': None}


def one_inspect(raw):
    rows = strict_json(raw)
    require(type(rows) is list and len(rows) == 1 and type(rows[0]) is dict, 'one complete Docker inspect row')
    return rows[0]


def owned(row, config):
    require(type(row.get('Id')) is str and CID.fullmatch(row['Id']) is not None, 'actual full container ID')
    require(config['container_id'] is None or row['Id'] == config['container_id'], 'original container ID')
    require(row.get('Name') == '/' + config['name'] and row.get('Image') == IMAGE_ID and
            row.get('Config', {}).get('Labels', {}).get('mckernel.collector.owner') == config['nonce'], 'exact name/image/owner label')
    return row['Id']


def env_map(rows):
    require(type(rows) is list, 'literal environment list')
    result = {}
    for entry in rows:
        require(type(entry) is str and '=' in entry and '\x00' not in entry, 'literal environment entry')
        name, value = entry.split('=', 1)
        require(name and name not in result, 'unique environment key')
        result[name] = value
    return result


def full_inspect(row, config, image):
    cid = owned(row, config)
    require(row.get('Path') == PYTHON and row.get('Args') == ['/inputs/root_inside.py'], 'actual fixed entry point')
    c, h = row['Config'], row['HostConfig']
    require(type(c) is dict and type(h) is dict, 'complete actual config objects')
    expected_env = env_map(image['Config']['Env'])
    expected_env.update(TMPDIR='/work/tmp', HOME='/tmp', PYTHONDONTWRITEBYTECODE='1')
    labels = dict(image['Config']['Labels']); labels['mckernel.collector.owner'] = config['nonce']
    for key, value in {'User': '0:0', 'Image': IMAGE_ID, 'WorkingDir': '/work', 'Entrypoint': [PYTHON],
            'Cmd': ['/inputs/root_inside.py'], 'Labels': labels, 'Tty': False, 'OpenStdin': False,
            'StdinOnce': False, 'AttachStdin': False, 'Domainname': ''}.items():
        require(same(c.get(key), value), 'container Config.' + key)
    require(env_map(c['Env']) == expected_env, 'exact image-plus-profile environment')
    require(c.get('Hostname') == cid[:12] and c.get('Volumes') in (None, {}) and
            c.get('ExposedPorts') in (None, {}) and c.get('Healthcheck') in (None, {}) and
            c.get('OnBuild') in (None, []) and c.get('StopSignal') in (None, '', 'SIGTERM'), 'no hidden config execution/mount/port')
    config_keys = {'Hostname', 'Domainname', 'User', 'AttachStdin', 'AttachStdout', 'AttachStderr', 'ExposedPorts',
        'Tty', 'OpenStdin', 'StdinOnce', 'Env', 'Cmd', 'Healthcheck', 'ArgsEscaped', 'Image', 'Volumes', 'WorkingDir',
        'Entrypoint', 'NetworkDisabled', 'MacAddress', 'OnBuild', 'Labels', 'StopSignal', 'StopTimeout', 'Shell'}
    require(set(c) <= config_keys, 'unreviewed container Config field')
    require(c.get('Shell') in (None, image['Config'].get('Shell')) and c.get('MacAddress', '') == '' and
            c.get('StopTimeout') in (None, 10) and c.get('NetworkDisabled', False) is False,
            'reviewed inherited config defaults')
    for key in ('AttachStdout', 'AttachStderr', 'ArgsEscaped'):
        require(key not in c or type(c[key]) is bool, 'actual boolean output config')
    expected = {'NetworkMode': 'none', 'Privileged': False, 'ReadonlyRootfs': True, 'CapDrop': ['ALL'],
        'SecurityOpt': ['no-new-privileges'], 'GroupAdd': ['0'], 'Memory': 12884901888,
        'MemorySwap': 12884901888, 'NanoCpus': 4000000000, 'CpusetCpus': '2-5', 'PidsLimit': 512,
        'CgroupParent': '/mckernel-dev', 'Init': True, 'PidMode': '', 'UTSMode': '', 'UsernsMode': '',
        'IpcMode': 'private', 'Runtime': 'runc', 'AutoRemove': False, 'PublishAllPorts': False,
        'RestartPolicy': {'Name': 'no', 'MaximumRetryCount': 0}, 'Tmpfs': {'/tmp': 'rw,nodev,nosuid,size=256m'}}
    for key, value in expected.items():
        require(same(h.get(key), value), 'actual HostConfig.' + key)
    empty = {'Binds', 'ContainerIDFile', 'Links', 'PortBindings', 'VolumesFrom', 'CapAdd', 'Dns', 'DnsOptions',
        'DnsSearch', 'ExtraHosts', 'Devices', 'DeviceCgroupRules', 'DeviceRequests', 'Sysctls', 'StorageOpt',
        'Annotations', 'VolumeDriver', 'ConsoleSize', 'LxcConf', 'Cgroup', 'CpusetMems', 'Isolation',
        'BlkioDeviceReadBps', 'BlkioDeviceWriteBps', 'BlkioDeviceReadIOps', 'BlkioDeviceWriteIOps', 'BlkioWeightDevice'}
    zero = {'CpuShares', 'CpuPeriod', 'CpuQuota', 'CpuRealtimePeriod', 'CpuRealtimeRuntime', 'MemoryReservation',
        'KernelMemory', 'KernelMemoryTCP', 'BlkioWeight', 'CpuCount', 'CpuPercent', 'IOMaximumIOps', 'IOMaximumBandwidth'}
    extra = {'Mounts', 'Ulimits', 'MaskedPaths', 'ReadonlyPaths', 'CgroupnsMode', 'ShmSize', 'OomKillDisable',
             'MemorySwappiness', 'OomScoreAdj', 'LogConfig'}
    require(set(h) <= set(expected) | empty | zero | extra, 'unreviewed HostConfig field')
    for key in empty:
        if key in h:
            allowed = (None, [0, 0]) if key == 'ConsoleSize' else (None, '', [], {})
            require(any(same(h[key], value) for value in allowed), 'nonempty additional HostConfig.' + key)
    for key in zero:
        if key in h:
            require(type(h[key]) is int and h[key] == 0, 'additional resource override: ' + key)
    require(h.get('CgroupnsMode') in ('host', 'private', '') and same(h.get('ShmSize'), 67108864) and
            any(same(h.get('OomKillDisable'), value) for value in (None, False)) and
            any(same(h.get('MemorySwappiness'), value) for value in (None, -1)) and
            same(h.get('OomScoreAdj'), 0), 'reviewed daemon namespace/OOM defaults')
    require(h.get('LogConfig') in ({'Type': 'json-file', 'Config': {}}, {'Type': 'local', 'Config': {}}), 'local default Docker log sink')
    require(same(sorted(h['Ulimits'], key=lambda item: item['Name']),
            [{'Name': 'core', 'Hard': 0, 'Soft': 0}, {'Name': 'nofile', 'Hard': 4096, 'Soft': 4096}]), 'exact ulimits')
    for key, minimum in (
            ('MaskedPaths', {'/proc/kcore', '/proc/keys', '/proc/latency_stats', '/proc/timer_list', '/proc/scsi', '/sys/firmware'}),
            ('ReadonlyPaths', {'/proc/bus', '/proc/fs', '/proc/irq', '/proc/sys', '/proc/sysrq-trigger'})):
        value = h.get(key)
        require(type(value) is list and all(type(item) is str and item.startswith(('/proc/', '/sys/')) and
                '..' not in item.split('/') for item in value) and len(value) == len(set(value)) and minimum <= set(value),
                'retained daemon default protection paths: ' + key)
    expected_mounts = {(str(REPO), '/workspace'): False,
        (str(Path(config['profile']) / 'inputs'), '/inputs'): False,
        (str(Path(config['profile']) / 'work'), '/work'): True}
    requested = h.get('Mounts')
    require(type(requested) is list and len(requested) == 3, 'exact HostConfig mount count')
    seen = {}
    for mount in requested:
        require(set(mount) <= {'Type', 'Source', 'Target', 'ReadOnly', 'Consistency', 'BindOptions'} and
                mount.get('Type') == 'bind' and mount.get('Consistency', '') == '' and
                mount.get('BindOptions') in (None, {}, {'Propagation': 'rprivate'}), 'bind options only')
        pair = (mount['Source'], mount['Target'])
        require(pair not in seen and type(mount.get('ReadOnly', False)) is bool, 'unique bind mount')
        seen[pair] = not mount.get('ReadOnly', False)
    require(seen == expected_mounts, 'exact requested bind mount identities and permissions')
    seen = {}; tmpfs = 0
    require(type(row.get('Mounts')) is list and len(row['Mounts']) in (3, 4), 'complete actual mount inventory')
    for mount in row['Mounts']:
        if mount.get('Type') == 'tmpfs':
            require(mount.get('Destination') == '/tmp' and mount.get('RW') is True and mount.get('Source', '') == '', 'only private /tmp tmpfs')
            tmpfs += 1; continue
        pair = (mount.get('Source'), mount.get('Destination'))
        require(mount.get('Type') == 'bind' and mount.get('Propagation') == 'rprivate' and
                type(mount.get('RW')) is bool and pair not in seen, 'actual private bind')
        seen[pair] = mount['RW']
    require(seen == expected_mounts and tmpfs <= 1, 'no extra actual mounts')
    networks = row.get('NetworkSettings', {}).get('Networks')
    require(type(networks) is dict and set(networks) == {'none'}, 'only none network')
    require(all(networks['none'].get(key, '') == '' for key in ('IPAddress', 'GlobalIPv6Address', 'Gateway', 'IPv6Gateway', 'MacAddress')), 'no routable network endpoint')
    require(row['NetworkSettings'].get('Ports') in (None, {}), 'no published ports')


def lookup(commands, config, label):
    filters = [('owner', 'label=mckernel.collector.owner=' + config['nonce']),
               ('name', 'name=^/' + config['name'] + '$')]
    if config['container_id'] is not None:
        filters.append(('id', 'id=' + config['container_id']))
    found = []
    for key, value in filters:
        raw, _ = commands.run(label + '-' + key, [DOCKER, 'container', 'ls', '--all', '--no-trunc', '--filter', value, '--format', '{{.ID}}'])
        lines = raw.decode('ascii').splitlines()
        require(len(lines) <= 1 and all(CID.fullmatch(line) is not None for line in lines), 'bounded unique owner lookup')
        found.append(lines)
    require(all(rows == found[0] for rows in found), 'container name/label/ID lookup ambiguity')
    if not found[0]:
        return None
    raw, _ = commands.run(label + '-inspect', [DOCKER, 'inspect', found[0][0]])
    row = one_inspect(raw)
    owned(row, config)
    return row


def cleanup(commands, config, label):
    path = commands.host / 'cleanup.lock'
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    deadline = time.monotonic() + 180
    acquired = False
    result = {'started_monotonic': time.monotonic(), 'absence_verified': False, 'errors': []}
    try:
        while time.monotonic() < deadline:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); acquired = True; break
            except BlockingIOError:
                time.sleep(0.05)
        require(acquired, 'bounded cleanup coordination lock')
        commands.deadline = deadline
        row = lookup(commands, config, label + '-locate')
        if row is not None:
            config['container_id'] = owned(row, config)
            if row['State'].get('Running') is True or row['State'].get('Paused') is True:
                try:
                    commands.run(label + '-stop', [DOCKER, 'stop', '--time=20', config['container_id']], 30)
                except BaseException as error:
                    result['errors'].append(str(error))
            # Revalidate identity immediately before force removal, including
            # when the bounded stop command failed. Never remove by name alone.
            row = lookup(commands, config, label + '-before-remove')
            if row is not None:
                commands.run(label + '-remove', [DOCKER, 'rm', '--force', owned(row, config)], 30)
        require(lookup(commands, config, label + '-absent') is None, 'owned container still present')
        result['absence_verified'] = True
    except BaseException as error:
        first_failure(commands.host, label + ':cleanup', error)
        result['errors'].append(str(error))
    finally:
        result['finished_monotonic'] = time.monotonic()
        commands.deadline = None
        if acquired:
            fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        save(commands.host / (label + '-cleanup.json'), result)
    return result


class RecoveryOwner:
    """Retains serialization while each bounded cleanup pass is retried."""
    def __init__(self, commands, config, label, *, max_passes=None, clock=time.monotonic,
                 sleeper=time.sleep, journal=None):
        self.commands, self.config, self.label = commands, config, label
        self.max_passes, self.clock, self.sleeper, self.journal = max_passes, clock, sleeper, journal
        self.state = 'RECOVERING'
        self.attempts = []
        self.first_failure = None
        self.journal_errors = []
        self.journal_error_count = 0

    def remember_journal_error(self, number, error):
        self.journal_error_count += 1
        if len(self.journal_errors) < 64:
            self.journal_errors.append({'attempt': number, 'type': type(error).__name__,
                                        'message': str(error)[:1024]})

    def outcome(self, absence_verified):
        return {'state': self.state, 'absence_verified': absence_verified,
                'evidence_complete': self.journal_error_count == 0,
                'journal_error_count': self.journal_error_count,
                'journal_errors': self.journal_errors,
                'attempts': self.attempts, 'first_failure': self.first_failure,
                'recovery_owner': {'pid': os.getpid(), 'reason': self.label}}

    def recover(self):
        number = 0
        while self.max_passes is None or number < self.max_passes:
            number += 1
            self.commands.number = 0
            try:
                result = cleanup(self.commands, self.config, self.label + '-%03d' % number)
            except BaseException as error:
                result = {'absence_verified': False, 'errors': [str(error)]}
            attempt = {'number': number, 'monotonic': self.clock(), 'result': result}
            if len(self.attempts) >= 64:
                self.attempts.pop(0)
            self.attempts.append(attempt)
            if result.get('absence_verified') is True:
                self.state = 'ABSENCE_VERIFIED'
                if self.journal is not None:
                    try:
                        self.journal({'state': self.state, 'attempts': self.attempts,
                                      'first_failure': self.first_failure,
                                      'recovery_owner': {'pid': os.getpid(), 'reason': self.label}})
                    except BaseException as error:
                        self.remember_journal_error(number, error)
                return self.outcome(True)
            if self.first_failure is None:
                errors = result.get('errors') or ['cleanup pass failed']
                self.first_failure = {'attempt': number, 'reason': errors[0]}
            if self.journal is not None:
                try:
                    self.journal({'state': 'RECOVERING', 'attempts': self.attempts,
                                  'first_failure': self.first_failure,
                                  'recovery_owner': {'pid': os.getpid(), 'reason': self.label}})
                except BaseException as error:
                    self.remember_journal_error(number, error)
            if self.max_passes is not None and number >= self.max_passes:
                break
            try:
                self.sleeper(1)
            except BaseException as error:
                if self.first_failure is None:
                    self.first_failure = {'attempt': number, 'reason': 'backoff: ' + str(error)}
        self.state = 'RECOVERING'
        return self.outcome(False)


def recover_cleanup(commands, config, label, *, max_passes=None, clock=time.monotonic,
                    sleeper=time.sleep, journal=None):
    """Controlled-cycle API; production's default retries until absence."""
    return RecoveryOwner(commands, config, label, max_passes=max_passes,
                         clock=clock, sleeper=sleeper, journal=journal).recover()


def release_lock_allowed(cleanup_result, watchdog_status):
    return (cleanup_result.get('absence_verified') is True and watchdog_status == 0)


def infrastructure_pass_allowed(result, host):
    cleanup_result = result.get('cleanup', {})
    return (result.get('collected_infrastructure_candidate') is True and
            not result.get('diagnostic_errors') and not (host / 'first-failure.json').exists() and
            result.get('watchdog_raw_wait_status') == 0 and
            cleanup_result.get('absence_verified') is True and
            cleanup_result.get('evidence_complete') is True and
            cleanup_result.get('first_failure') is None)


def recovery_journal(host, prefix, state):
    number = state['attempts'][-1]['number']
    write(host / ('%s-recovery-%03d.json' % (prefix, number)),
          (json.dumps(state, indent=2, sort_keys=True) + '\n').encode())


def recheck(checks):
    for expected in checks:
        require(regular(Path(expected['path']))[1] == expected, 'bound source/artifact drift: ' + expected['path'])


def inventory(root):
    rows = []; total = 0; stack = [root]
    while stack:
        path = stack.pop()
        require(len(rows) < MAX_MEMBERS, 'full tree inventory member cap')
        info = path.lstat()
        kind = ('directory' if stat.S_ISDIR(info.st_mode) else 'file' if stat.S_ISREG(info.st_mode)
                else 'symlink' if stat.S_ISLNK(info.st_mode) else 'fifo' if stat.S_ISFIFO(info.st_mode) else None)
        require(kind is not None, 'unreviewed output file type')
        row = {'path': str(path.relative_to(root)), 'type': kind, **stat_identity(info)}
        if kind == 'file':
            raw, identity = regular(path)
            total += len(raw); require(total <= MAX_TREE, 'full tree byte cap')
            require(stat_identity(info) == {key: identity[key] for key in stat_identity(info)}, 'inventory changed before hash')
            row['sha256'] = identity['sha256']
        elif kind == 'symlink':
            row['target'] = os.readlink(path)
            require(stat_identity(path.lstat()) == stat_identity(info), 'symlink changed')
        elif kind == 'directory':
            with os.scandir(path) as entries:
                children = []
                for entry in entries:
                    require(len(rows) + len(stack) + len(children) < MAX_MEMBERS, 'bounded directory enumeration')
                    children.append(path / entry.name)
                stack.extend(sorted(children, reverse=True))
        rows.append(row)
    return {'root': str(root), 'member_count': len(rows), 'regular_bytes': total, 'members': rows,
            'ownership_changed': False, 'root_owned_output_preserved': True}


def watchdog(config_path, pipe_fd, lock_fd):
    config = strict_json(regular(config_path)[0])
    host = Path(config['host'])
    require(os.getuid() == os.geteuid() == 0, 'actual root watchdog')
    require(stat.S_ISFIFO(os.fstat(pipe_fd).st_mode), 'private inherited control pipe')
    require(stat_identity(os.fstat(lock_fd)) == stat_identity(LOCK.stat()), 'inherited serialization lock identity')
    require(CID.fullmatch(config['container_id']) is not None and NONCE.fullmatch(config['nonce']) is not None and
            config['name'] == 'mckernel-collector-' + config['nonce'] and config['image'] == IMAGE_ID, 'watchdog owned identity')
    require(regular(Path(__file__).resolve())[1]['sha256'] == config['orchestrator_sha256'], 'watchdog retained source')
    supervisor = load_source(host / 'supervisor.py', HOST_SUPERVISOR_SHA, 'root_watchdog_supervisor')
    supervisor._set_subreaper()
    commands = Commands(host, 'watchdog', supervisor)
    interrupted = []
    def remember_signal(number, frame):
        if not interrupted:
            interrupted.append(number)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, remember_signal)
    deadline = config['deadline_monotonic']
    require(type(deadline) in (int, float) and math.isfinite(deadline) and
            time.monotonic() - 300 <= deadline <= time.monotonic() + 300, 'bounded original watchdog deadline')
    save(host / 'watchdog-ready.json', {'pid': os.getpid(), 'identity': supervisor._process_identity(os.getpid()),
         'deadline_monotonic': deadline, 'lock_identity': stat_identity(os.fstat(lock_fd)), 'subreaper': True})
    reason = None; data = b''; release_lock = False; diagnostic_errors = []
    try:
        while reason is None:
            if interrupted:
                reason = 'watchdog interrupted'; break
            if time.monotonic() >= deadline:
                reason = 'independent 300-second deadline'; break
            ready, _, _ = select.select([pipe_fd], [], [], max(0, min(0.1, deadline - time.monotonic())))
            if not ready:
                continue
            part = os.read(pipe_fd, 256)
            if not part:
                reason = 'parent control pipe EOF'; break
            data += part
            expected = ('DISARM ' + config['nonce'] + ' ' + config['container_id'] + '\n').encode()
            if len(data) > len(expected) or not expected.startswith(data):
                reason = 'malformed private disarm'; break
            if data == expected:
                require(lookup(commands, config, 'disarm-absence') is None, 'disarm requires actual absence')
                require(time.monotonic() < deadline, 'disarm verified before independent deadline')
                save(host / 'watchdog-result.json', {'status': 'DISARMED_AFTER_VERIFIED_ABSENCE',
                     'finished_monotonic': time.monotonic(), 'container_id': config['container_id'],
                     'application_acceptance': False})
                release_lock = True
                return 0
        safe_first_failure(host, 'watchdog', RuntimeError(reason), diagnostic_errors)
        result = recover_cleanup(commands, config, 'watchdog',
                                 journal=lambda state: recovery_journal(host, 'watchdog', state))
        result['evidence_complete'] = result.get('evidence_complete', True) and not diagnostic_errors
        save(host / 'watchdog-result.json', {'status': 'WATCHDOG_TRIGGERED', 'reason': reason, 'cleanup': result,
             'diagnostic_errors': diagnostic_errors,
             'finished_monotonic': time.monotonic(), 'application_acceptance': False})
        release_lock = result.get('absence_verified') is True
        return 1
    except BaseException as error:
        safe_first_failure(host, 'watchdog', error, diagnostic_errors)
        result = recover_cleanup(commands, config, 'watchdog-exception',
                                 journal=lambda state: recovery_journal(host, 'watchdog-exception', state))
        release_lock = result.get('absence_verified') is True
        save(host / 'watchdog-exception.json', {'error': str(error), 'cleanup': result,
             'diagnostic_errors': diagnostic_errors})
        return 1
    finally:
        os.close(pipe_fd)
        if release_lock:
            os.close(lock_fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt-number', type=int, required=True)
    parser.add_argument('--source-sha256', required=True)
    args = parser.parse_args()
    require(os.getuid() == os.geteuid() == 0 and 1 <= args.attempt_number <= 999999, 'actual root and bounded fresh attempt number')
    source_raw, source_identity = regular(Path(__file__).resolve())
    require(CID.fullmatch(args.source_sha256) is not None and source_identity['sha256'] == args.source_sha256,
            'explicit reviewed orchestrator source hash')
    suffix = '20260913-' + str(args.attempt_number)
    host = WORK / ('scratch/stability-linux-sealed-root-host-' + suffix)
    profile = WORK / ('scratch/stability-linux-sealed-root-tests-' + suffix)
    require(not host.exists() and not host.is_symlink() and not profile.exists() and not profile.is_symlink(), 'both dedicated attempts must be fresh')
    os.umask(0o077)
    lock_fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    require(stat.S_ISREG(os.fstat(lock_fd).st_mode) and os.fstat(lock_fd).st_uid == 0 and os.fstat(lock_fd).st_nlink == 1, 'root-owned regular shared lock')
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    host.mkdir(mode=0o700)
    for leaf in ('docker-home', 'docker-config'):
        (host / leaf).mkdir(mode=0o700)
    config = None; watch = None; control = None; supervisor = None; commands = None
    result = {'status': 'FAIL', 'application_acceptance': False, 'transport_acceptance': False,
              'backend_enabled': False, 'host_root': str(host), 'profile_root': str(profile),
              'started_monotonic': time.monotonic(), 'watchdog_raw_wait_status': None,
              'diagnostic_errors': []}
    checks = []
    def interrupted(number, frame):
        safe_first_failure(host, 'host-signal', RuntimeError('signal ' + str(number)), result['diagnostic_errors'])
        raise KeyboardInterrupt
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, interrupted)
    try:
        write(host / 'root_orchestrator.py', source_raw)
        for name, source, expected in (
                ('root_profile.py', FIXTURES / 'root_profile.py', PLANNER_SHA),
                ('original-supervisor.py', REPO / 'scripts/application-tests/supervisor.py', SUPERVISOR_SHA),
                ('supervisor.py', FIXTURES / 'supervisor_host38.py', HOST_SUPERVISOR_SHA),
                ('image-native.json', WORK / 'logs/image-native.json', IMAGE_SHA)):
            raw, identity = regular(source)
            require(identity['sha256'] == expected, 'reviewed prerequisite source: ' + name)
            write(host / name, raw); checks.append(identity)
        wrapper, wrapper_identity = regular(WORK / 'setup/container-run.py')
        write(host / 'original-container-run.py', wrapper); checks.append(wrapper_identity)
        checks.append(source_identity)
        checks.extend(bind_build(host))
        supervisor = load_source(host / 'supervisor.py', HOST_SUPERVISOR_SHA, 'root_host_supervisor')
        commands = Commands(host, 'host', supervisor)
        commands.run('mountpoint', ['/usr/bin/mountpoint', '-q', str(WORK / 'scratch')])
        label, _ = commands.run('scratch-label', ['/usr/bin/findmnt', '-n', '-o', 'LABEL', '--target', str(WORK / 'scratch')])
        require(label == b'mckernel-scratch\n', 'exact scratch filesystem label')
        planner_output, _ = commands.run('planner', [PYTHON, '-I', '-B', str(host / 'root_profile.py'),
            '--build-root', str(BUILD), '--attempt-root', str(profile)], 30)
        require(planner_output == (str(profile / 'plan.json') + '\n').encode(), 'exact planner output')
        raw, _ = regular(profile / 'plan.json')
        write(host / 'plan.json', raw)
        plan = strict_json(raw)
        config = plan_check(plan, profile, host)
        image_raw, _ = commands.run('image-inspect', [DOCKER, 'image', 'inspect', IMAGE_ID])
        image = one_inspect(image_raw)
        retained_image = strict_json(regular(host / 'image-native.json')[0])[0]
        require(image['Id'] == IMAGE_ID and image['Config'] == retained_image['Config'] and
                image['Architecture'] == 'amd64' and image['Os'] == 'linux' and
                image['RootFS'] == retained_image['RootFS'], 'exact immutable image configuration/rootfs')
        require(lookup(commands, config, 'precreate') is None, 'fresh random container name and owner label')
        recheck(checks)
        # Once create has been submitted its effect is ambiguous on failure.
        # The finally path always queries the exact unique owner/name, even if
        # no container ID was returned. It never promotes this failure to PASS.
        result['create_submitted_monotonic'] = time.monotonic()
        created, _ = commands.run('create', plan['commands']['create'], 30)
        require(re.fullmatch(rb'[0-9a-f]{64}\n', created) is not None, 'one actual create ID')
        config['container_id'] = created[:-1].decode('ascii')
        row = lookup(commands, config, 'before-start')
        require(row is not None and row['State']['Status'] == 'created' and row['State']['Running'] is False,
                'actual newly created stopped container')
        full_inspect(row, config, image)
        input_manifest = strict_json(regular(profile / 'inputs/inputs.json')[0])
        require(input_manifest['profile_nonce'] == config['nonce'] and input_manifest['image'] == IMAGE_ID,
                'actual profile manifest owner/image')
        expected_files = {'linux-collector': BUILD / 'linux-collector', 'fixture': BUILD / 'fixture',
            'sha256-harness': BUILD / 'sha256-harness', 'root_inside.py': FIXTURES / 'root_inside.py',
            'run_collector_tests.py': FIXTURES / 'run_collector_tests.py',
            'supervisor.py': REPO / 'scripts/application-tests/supervisor.py'}
        require(type(input_manifest.get('schema_version')) is int and input_manifest['schema_version'] == 1 and
                input_manifest['kind'] == 'linux-sealed-root-profile-inputs' and
                input_manifest['application_acceptance'] is False and input_manifest['backend_enabled'] is False and
                set(input_manifest['files']) == set(expected_files), 'exact six copied profile inputs')
        for leaf, entry in input_manifest['files'].items():
            data, identity = regular(profile / 'inputs' / leaf)
            original_data, original_identity = regular(expected_files[leaf])
            require(type(entry['size_bytes']) is int and data == original_data and identity['sha256'] == entry['sha256'] and
                    len(data) == entry['size_bytes'] and entry['source']['path'] == str(expected_files[leaf]) and
                    entry['source']['sha256'] == original_identity['sha256'], 'actual copied input bytes and original selector')
        recheck(checks)
        config.update(orchestrator_sha256=source_identity['sha256'], deadline_monotonic=time.monotonic() + 300)
        save(host / 'watchdog-config.json', config)
        read_fd, control = os.pipe2(os.O_CLOEXEC)
        out = os.open(host / 'watchdog.stdout.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        err = os.open(host / 'watchdog.stderr.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        try:
            watch = subprocess.Popen([PYTHON, '-I', '-B', str(host / 'root_orchestrator.py'), '--watchdog',
                str(host / 'watchdog-config.json'), str(read_fd), str(lock_fd)], stdin=subprocess.DEVNULL,
                stdout=out, stderr=err, env={}, close_fds=True, pass_fds=(read_fd, lock_fd), start_new_session=True)
        finally:
            os.close(read_fd); os.close(out); os.close(err)
        ready_deadline = time.monotonic() + 5
        while not (host / 'watchdog-ready.json').exists() and time.monotonic() < ready_deadline:
            require(os.waitid(os.P_PID, watch.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None, 'watchdog failed before ready')
            time.sleep(0.01)
        ready = strict_json(regular(host / 'watchdog-ready.json')[0])
        require(ready['pid'] == watch.pid and ready['subreaper'] is True and
                ready['deadline_monotonic'] == config['deadline_monotonic'], 'actual independent watchdog ready')
        actual_watch = supervisor._process_identity(watch.pid)
        require(actual_watch['ppid'] == os.getpid() and actual_watch['pgid'] == actual_watch['session'] == watch.pid and
                all(ready['identity'][key] == actual_watch[key] for key in
                    ('pid', 'ppid', 'pgid', 'session', 'starttime_ticks')), 'actual fork-owned watchdog identity')
        result['watchdog_process'] = actual_watch
        require(time.monotonic() < config['deadline_monotonic'], 'start before watchdog deadline')
        result['start_submitted_monotonic'] = time.monotonic()
        _, attached = commands.run('start-attach', [DOCKER, 'start', '--attach', config['container_id']],
                                  config['deadline_monotonic'] - time.monotonic())
        require(attached['payload_completion_observed_monotonic'] < config['deadline_monotonic'], 'attach observed before original watchdog deadline')
        row = lookup(commands, config, 'after-exit')
        require(row is not None, 'container retained after actual exit')
        full_inspect(row, config, image)
        state = row['State']
        require(state['Status'] == 'exited' and state['Running'] is False and state['Paused'] is False and
                state['Restarting'] is False and state['OOMKilled'] is False and state['Dead'] is False and
                type(state['ExitCode']) is int and state['ExitCode'] == 0 and state['Error'] == '', 'actual normal container completion')
        inner = strict_json(regular(profile / 'work/root-result.json')[0])
        require(inner['status'] == 'PASS_LINUX_INFRASTRUCTURE_ONLY' and inner['application_acceptance'] is False and
                inner['backend_enabled'] is False and inner['profile_nonce'] == config['nonce'], 'actual fixed root entrypoint result')
        recheck(checks)
        result['collected_infrastructure_candidate'] = True
    except BaseException as error:
        safe_first_failure(host, 'host-orchestration', error, result['diagnostic_errors'])
        save(host / 'host-error.json', {'type': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc()})
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, lambda number, frame: safe_first_failure(host, 'cleanup-signal', RuntimeError('signal ' + str(number)), result['diagnostic_errors']))
        def final_error(label, error):
            safe_first_failure(host, label, error, result['diagnostic_errors'])
            try:
                save(host / (label + '-error.json'), {'type': type(error).__name__, 'error': str(error),
                                                    'traceback': traceback.format_exc()})
            except BaseException as diagnostic:
                safe_first_failure(host, label + '-save', diagnostic, result['diagnostic_errors'])
        if config is not None and commands is not None:
            try:
                result['cleanup'] = recover_cleanup(commands, config, 'host-final',
                                                    journal=lambda state: recovery_journal(host, 'host-final', state))
            except BaseException as error:
                final_error('host-cleanup', error)
        if control is not None:
            try:
                if result.get('cleanup', {}).get('absence_verified') is True:
                    message = ('DISARM ' + config['nonce'] + ' ' + config['container_id'] + '\n').encode()
                    try:
                        require(os.write(control, message) == len(message), 'complete private watchdog disarm')
                    except BrokenPipeError:
                        pass
            except BaseException as error:
                final_error('host-disarm', error)
            finally:
                os.close(control); control = None
        if watch is not None:
            try:
                wait_deadline = time.monotonic() + 210
                while time.monotonic() < wait_deadline:
                    pid, raw = os.waitpid(watch.pid, os.WNOHANG)
                    if pid:
                        result['watchdog_raw_wait_status'] = raw
                        watch.returncode = supervisor._host38_waitstatus_to_exitcode(raw)
                        break
                    time.sleep(0.05)
                if watch.returncode is None:
                    safe_first_failure(host, 'watchdog-wait', RuntimeError('watchdog failed bounded completion'), result['diagnostic_errors'])
                    result['watchdog_rescue'] = supervisor._rescue_worker(watch, 15)
                require(result['watchdog_raw_wait_status'] == 0, 'actual clean watchdog exit after absence')
                watcher = strict_json(regular(host / 'watchdog-result.json')[0])
                require(watcher['status'] == 'DISARMED_AFTER_VERIFIED_ABSENCE', 'watchdog did not trigger')
            except BaseException as error:
                final_error('host-watchdog-reap', error)
        try:
            require(result.get('cleanup', {}).get('absence_verified') is True, 'verified final container absence')
            recheck(checks)
        except BaseException as error:
            final_error('host-finalization', error)
        finally:
            if control is not None:
                os.close(control)
            result['finished_monotonic'] = time.monotonic()
            try:
                trees = [inventory(host)]
                if profile.exists():
                    trees.append(inventory(profile))
                save(host / 'original-tree-inventory.json', {'trees': trees, 'ownership_changed': False,
                     'scope': 'all existing attempt members before this inventory and final result; parent archives final metadata too'})
                if infrastructure_pass_allowed(result, host):
                    result['status'] = 'PASS_ROOT_COLLECTOR_INFRASTRUCTURE_ONLY'
            except BaseException as error:
                safe_first_failure(host, 'original-tree-inventory', error, result['diagnostic_errors'])
                result['inventory_error'] = str(error)
            save(host / 'result.json', result)
            # Do not explicitly unlock the shared open-file description. If
            # the parent fails while its watchdog still lives, that inherited
            # descriptor must continue holding serialization through cleanup.
            if release_lock_allowed(result.get('cleanup', {}), result.get('watchdog_raw_wait_status')):
                os.close(lock_fd)
    print(result['status'] + ' ' + str(host), flush=True)
    return 0 if result['status'] == 'PASS_ROOT_COLLECTOR_INFRASTRUCTURE_ONLY' else 1


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == '--watchdog':
        raise SystemExit(watchdog(Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])))
    raise SystemExit(main())
