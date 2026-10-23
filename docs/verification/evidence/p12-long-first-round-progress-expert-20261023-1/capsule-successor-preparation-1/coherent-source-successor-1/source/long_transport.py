"""Explicit long transport only; no workload or physical acceptance authority.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import hashlib
import json
import math
import os
import resource
from pathlib import Path
import stat
import time

ROOT = Path(__file__).resolve().parent
PROFILE = dict(version=1, work_ns=3600000000000, wall_ns=7200000000000,
               min_launches=100, round_cap=2048, trace_cap=268435456)
HOST_OUTPUT = dict(schema='mckernel.p12.host-output.v1',
                   parent='/home/holden/mckernel-work/native-runs/l12b1/p',
                   retention_parent='/home/holden/mckernel-work/native-runs/l12b1',
                   device=66306, uid=1000, gid=1000, mode=0o700,
                   scratch_output_bytes=0)
DOCKER_LOG = {'Type': 'none', 'Config': {}}
# Exact distro startLogging returns before creating a logger/copier for none.
# Attached stdout/stderr remain bounded by the existing owner capture path.
DOCKER_LOG_BYTES = 0
UNUSED_SLACK_BYTES = 96 * 2**20
DAEMON_ALLOCATION_BINDING = {'mode': 'none', 'persistent_logfile_bytes': 0,
    'source_package': 'docker.io-app=26.1.3-0ubuntu1~20.04.1',
    'container_source_sha256': '6ed6a9d2a3a32ecf6cbb91eaefdb5925c1316e8ea35e0856b7bb85530d143739',
    'source_branch': 'engine/container/container.go:633-636',
    'runtime_requirement': 'exact HostConfig.LogConfig none with empty Config; no LONG logs request'}
# Separate direct-file capture storage; no claim that post-join32MiB hashing limits writes.
EXTERNAL_CAPTURE = dict(command_count=1, stream_slots=2, retained_copies=1,
                        stream_file_bytes=384 * 2**20)
EXTERNAL_CAPTURE_BYTES = (EXTERNAL_CAPTURE['command_count'] * EXTERNAL_CAPTURE['stream_slots'] *
                          EXTERNAL_CAPTURE['retained_copies'] * EXTERNAL_CAPTURE['stream_file_bytes'])
# No final wrapper/argv/path/copy binding exists in this private cohort.
EXTERNAL_CAPTURE_BINDING = {'schema': 'mckernel.p12.exact-LONG-owner-capture-binding.v1', 'controller_path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/capsule-successor-preparation-1/coherent-source-successor-1/capture_root_LONG.NOT-RELEASED.py', 'controller_sha256': '87eae37f7aef716896168e93b89e3bd230d8227dd90dd39ee2803aa59345b1b3', 'request_path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/capsule-successor-preparation-1/coherent-source-successor-1/CAPTURE-REQUEST.json', 'capture_directory': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/capsule-successor-preparation-1/coherent-source-successor-1/actual-capture-1', 'command_source_path': '/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/capsule-successor-preparation-1/coherent-source-successor-1/source/native_diagnostic_container_owner.py', 'command_interpreter': '/home/holden/anaconda3/bin/python3', 'controller_interpreter': '/home/holden/anaconda3/bin/python3', 'command_count': 1, 'stream_slots': 2, 'stream_file_bytes': 402653184, 'retained_copies': 1, 'soft_wall_seconds': 8100, 'no_forcekill': True, 'persistent_retirement_wait': True, 'owner_runtime_release_digest': 'Bound after independent release by finalrequest+exactownerargv; omitted here to avoid source/release digest cycle', 'owner_digest': 'Bound after source freeze by finalrequest/ownerCLI; omitted here to avoid selfdigest cycle'}
TRANSPORT = dict(docker_log=DOCKER_LOG, docker_log_bytes=DOCKER_LOG_BYTES, unused_slack_bytes=UNUSED_SLACK_BYTES, host_output=HOST_OUTPUT, schema='mckernel.p12.long-transport-profile.v2',
                 producer=PROFILE, inner_seconds=7800, outer_seconds=8100,
                 serial_bytes=384 * 2**20, shared_capture_bytes=512 * 2**20,
                 trace_bytes=256 * 2**20, other_stream_bytes=4 * 2**20,
                 qmp_bytes=24 * 2**20, per_app_bytes=1024, per_app_timeout_ms=10000,
                 file_bytes=384 * 2**20, attempt_file_slots=7,
                 metadata_bytes=32 * 2**20, external_capture=EXTERNAL_CAPTURE,
                 external_capture_bytes=EXTERNAL_CAPTURE_BYTES,
                 logical_growth_bytes=(7 * 384 + 512 + 32) * 2**20 + UNUSED_SLACK_BYTES + DOCKER_LOG_BYTES + EXTERNAL_CAPTURE_BYTES)
FILES = ('native_diagnostic.py', 'native_diagnostic_runner.py',
         'native_diagnostic_backend.py', 'native_diagnostic_container_owner.py',
         'qmp_capture.py', 'repaired_image_authority.py', 'composite_module_binding.py',
         'p12_long_session.py', 'long_transport.py')


def need(ok, why):
    if not ok:
        raise ValueError(why)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def stable(path, cap=1048576):
    path = Path(path)
    need(path.is_absolute() and path.resolve() == path, 'canonical long-profile input')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= cap, 'bounded long-profile input')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(cap + 1)
        after, named = os.fstat(fd), path.lstat()
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        need(len(raw) == before.st_size and all(getattr(before, k) == getattr(after, k) == getattr(named, k)
             for k in fields), 'long-profile input changed')
        return raw
    finally:
        os.close(fd)


def is_long(manifest):
    if 'pair_long_session' not in manifest:
        return False
    profile = manifest['pair_long_session']
    need(type(profile) is dict and profile == PROFILE and all(type(profile[k]) is int for k in PROFILE),
         'exact typed producer long profile')
    need('pair' in manifest and 'pair_rounds' not in manifest, 'long profile requires pair and excludes fixed rounds')
    return True


def deadline(value, long_profile=False, outer=False):
    need(type(value) in (int, float) and math.isfinite(value), 'finite transport deadline')
    if long_profile:
        need(value == TRANSPORT['outer_seconds' if outer else 'inner_seconds'], 'exact long transport deadline')
    elif outer:
        need(330 <= value <= 600, 'outer deadline must exceed inner cleanup')
    else:
        need(0 < value <= 3600, 'finite short transport deadline')
    return value


def file_limit(long_profile):
    need(type(long_profile) is bool, 'typed file-limit mode')
    return TRANSPORT['file_bytes'] if long_profile else 32 * 2**20


def require_fsize(long_profile):
    bound = file_limit(long_profile)
    need(resource.getrlimit(resource.RLIMIT_FSIZE) == (bound, bound),
         'exact inherited soft/hard FSIZE required')
    return bound


def _host_directory(path, expected_path, expected_device, *, fresh=False):
    """Descriptor-walk a separately bound host output parent; never create it."""
    raw = os.fspath(path)
    need(type(expected_path) is str and type(expected_device) is int and
         type(fresh) is bool, 'typed host output binding')
    value = Path(raw)
    need(raw == expected_path and value.is_absolute() and
         str(value) == raw and value.resolve(strict=True) == value,
         'exact canonical host output parent')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in value.parts[1:]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = nxt
        info = os.fstat(fd)
        need(stat.S_ISDIR(info.st_mode) and info.st_dev == expected_device and
             info.st_uid == HOST_OUTPUT['uid'] and info.st_gid == HOST_OUTPUT['gid'] and
             stat.S_IMODE(info.st_mode) == HOST_OUTPUT['mode'],
             'private uid/gid1000 mode0700 host-device output parent')
        need(not fresh or not os.listdir(fd), 'fresh empty host output parent required')
        return (info.st_dev, info.st_ino)
    finally:
        os.close(fd)


def _host_output(path, binding, *, fresh=False):
    """Apply a source/release-bound layout without creating any output."""
    identity = _host_directory(path, binding['parent'], binding['device'], fresh=fresh)
    # Only outer admission sees the unmounted retention base. Inside the
    # container its ancestor is synthetic; the exact p bind still has host dev.
    if fresh:
        _host_directory(binding['retention_parent'], binding['retention_parent'], binding['device'])
        need(sorted(os.listdir(binding['retention_parent'])) == ['p'],
             'fresh dedicated host retention parent required')
    return identity


def output_parent(path, *, fresh=False):
    return _host_output(path, HOST_OUTPUT, fresh=fresh)


def output_attempt(path):
    value = Path(path)
    need(value.name.startswith('attempt-') and len(value.name) == 40 and
         all(c in '0123456789abcdef' for c in value.name[8:]), 'exact long output attempt name')
    output_parent(value.parent)
    _host_directory(value, str(value), HOST_OUTPUT['device'])
    return value


def readonly_input(path, parent):
    value = Path(path)
    scratch = Path('/home/holden/mckernel-work/scratch')
    need(value.is_absolute() and value.resolve(strict=True) == value and
         scratch in value.parents and Path(parent) not in (value, *value.parents),
         'long input must be canonical readonly scratch outside host output')
    return value


def validate_profile(profile):
    need(type(profile) is dict and canonical(profile) == canonical(TRANSPORT),
         'exact typed transport and host-output profile')
    return profile


def growth_requirements(admission):
    """Validate independently reviewed full physical-growth terms, without cleanup credit."""
    keys = {'host_floor_bytes', 'scratch_floor_bytes', 'remaining_backing_growth_bytes',
            'emergency_bytes', 'campaign_bytes', 'scratch_input_growth_bytes'}
    need(type(admission) is dict and set(admission) == keys and
         all(type(v) is int and v >= 0 for v in admission.values()),
         'complete typed physical growth admission')
    need(admission['host_floor_bytes'] == 16 * 2**30 and
         admission['scratch_floor_bytes'] == 12 * 2**30 and
         admission['emergency_bytes'] > 0 and admission['campaign_bytes'] > 0,
         'preserved storage floors and separately reviewed reserves')
    return dict(host_required_bytes=admission['host_floor_bytes'] +
                admission['remaining_backing_growth_bytes'] + TRANSPORT['logical_growth_bytes'] +
                admission['emergency_bytes'] + admission['campaign_bytes'],
                scratch_required_bytes=admission['scratch_floor_bytes'] +
                admission['scratch_input_growth_bytes'] + admission['emergency_bytes'] +
                admission['campaign_bytes'])


def require_growth(admission, host_available, scratch_available, backing_gap):
    required = growth_requirements(admission)
    need(all(type(v) is int and v >= 0 for v in
             (host_available, scratch_available, backing_gap)), 'typed live storage observation')
    need(admission['remaining_backing_growth_bytes'] >= backing_gap,
         'full live sparse backing gap required')
    need(host_available >= required['host_required_bytes'], 'HOST floor plus complete physical growth')
    need(scratch_available >= required['scratch_required_bytes'], 'scratch floor plus remaining input growth')
    return required


def live_growth(admission, parent):
    """Outer-only fresh measurements; no storage or reservation mutation."""
    scratch = Path('/home/holden/mckernel-work/scratch')
    uuid = Path('/dev/disk/by-uuid/2a5768c8-718d-4914-bdc0-6b32c5a92a52')
    device = scratch.stat().st_dev
    block = uuid.stat()
    need(stat.S_ISBLK(block.st_mode) and block.st_rdev == device,
         'scratch UUID and live mounted device')
    backing = Path('/home/holden/mckernel-work/scratch.ext4')
    loop = Path('/sys/dev/block/%d:%d/loop/backing_file' % (os.major(device), os.minor(device)))
    need(loop.read_text().strip() == str(backing), 'live scratch loop backing identity')
    need(backing.resolve(strict=True) == backing, 'canonical scratch backing')
    fd = os.open(backing, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_size == 110 * 2**30 and
             info.st_dev == Path(parent).stat().st_dev and info.st_dev != device,
             'exact110GiB host sparse backing and distinct output filesystem')
        gap = max(0, info.st_size - info.st_blocks * 512)
    finally:
        os.close(fd)
    host, other = os.statvfs(parent), os.statvfs(scratch)
    return require_growth(admission, host.f_bavail * host.f_frsize,
                          other.f_bavail * other.f_frsize, gap)


def validate_release(path, expected_sha, manifest_path, nonce, parent, *, clock=time.time, boot_id=None):
    need(DAEMON_ALLOCATION_BINDING is not None,
         'daemon none-mode source authority not bound; execution blocked')
    need(EXTERNAL_CAPTURE_BINDING is not None,
         'final external capture wrapper/argv/paths/copy count not bound; execution blocked')
    output_parent(parent)
    readonly_input(path, parent)
    readonly_input(manifest_path, parent)
    raw = stable(Path(path))
    need(digest(raw) == expected_sha, 'exact long release digest')
    value = json.loads(raw)
    keys = {'schema', 'status', 'profile', 'manifest', 'nonce', 'attempt_parent', 'boot_id',
            'expires_unix', 'execution_count', 'source_sha256', 'author', 'independent_review', 'storage_admission'}
    need(type(value) is dict and set(value) == keys and
         value['schema'] == 'mckernel.p12.long-transport-release.v2' and
         value['status'] == 'PASS_EXECUTION_RELEASE' and value['profile'] == TRANSPORT,
         'new exact long transport release required')
    validate_profile(value['profile'])
    growth_requirements(value['storage_admission'])
    manifest_raw = stable(Path(manifest_path), 4 * 2**20)
    manifest = json.loads(manifest_raw)
    need(is_long(manifest) and value['manifest'] == dict(path=str(manifest_path), sha256=digest(manifest_raw)),
         'long release exact manifest join')
    need(value['nonce'] == nonce and value['attempt_parent'] == str(parent), 'long release attempt join')
    boot = boot_id if boot_id is not None else Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    need(value['boot_id'] == boot and type(value['execution_count']) is int and value['execution_count'] == 1,
         'long release current boot and one execution')
    now = clock()
    need(type(value['expires_unix']) in (int, float) and math.isfinite(value['expires_unix']) and
         now <= value['expires_unix'] <= now + 600, 'fresh long transport release')
    sources = value['source_sha256']
    need(type(sources) is dict and set(sources) == set(FILES), 'complete long runtime source cohort')
    for name in FILES:
        need(digest(stable(ROOT / name, 2 * 2**20)) == sources[name], 'long runtime source drift')
    review = value['independent_review']
    need(type(review) is dict and set(review) == {'status', 'reviewer', 'implementation_ownership', 'payload_sha256'} and
         review['status'] == 'PASS' and review['implementation_ownership'] is False and
         type(value['author']) is str and value['author'] and type(review['reviewer']) is str and
         review['reviewer'] and review['reviewer'] != value['author'] and
         review['payload_sha256'] == digest(canonical({k: v for k, v in value.items() if k != 'independent_review'})),
         'independent exact long release review')
    return value


def compact_observation(observation):
    result = {k: v for k, v in observation.items() if k not in ('serial', 'debugcon')}
    result['capture_refs'] = {name: dict(bytes=len(observation[name].encode('utf-8')),
        sha256=digest(observation[name].encode('utf-8'))) for name in ('serial', 'debugcon')}
    return result


def hydrate_observation(observation, texts):
    need(type(observation) is dict and 'capture_refs' in observation and
         'serial' not in observation and 'debugcon' not in observation, 'compact long observation required')
    result = {k: v for k, v in observation.items() if k != 'capture_refs'}
    need(set(observation['capture_refs']) == {'serial', 'debugcon'}, 'exact long retained capture roles')
    for name in ('serial', 'debugcon'):
        raw = texts[name].encode('utf-8')
        need(len(raw) <= TRANSPORT['serial_bytes' if name == 'serial' else 'other_stream_bytes'] and
             observation['capture_refs'][name] == dict(bytes=len(raw), sha256=digest(raw)),
             'original long capture hash/size join')
        result[name] = texts[name]
    return result
