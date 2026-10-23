#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Candidate for independent review; NOT an execution release. No default action.
Dispatcher supplies digest-bound independent release through existing root route.
Ownership is deliberately retained on success AND failure for separate retirement.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import stat
import subprocess
import time

BACKING = Path('/home/holden/mckernel-work/scratch.ext4')
MOUNT = Path('/home/holden/mckernel-work/scratch')
LOCK = Path('/run/lock/mckernel-development.lock')
SHARED = MOUNT / 'mckernel-heavy-operation.lock'
HELPER = Path('/home/holden/mckernel/scripts/native_rust_exact_disk_build_wrapper.py')
HELPER_SHA = 'c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1'
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
OLD = 110 * 2**30
TARGET = 142 * 2**30
OLD_BLOCKS = OLD // 4096
NEW_BLOCKS = TARGET // 4096
RESERVE = 288358
FEATURES = sorted(('has_journal ext_attr resize_inode dir_index filetype needs_recovery extent '
                   '64bit flex_bg sparse_super large_file huge_file dir_nlink extra_isize metadata_csum').split())
GEOMETRY = dict(block_size=4096, blocks_per_group=32768, descriptor_size=64,
                descriptor_blocks_before=14, descriptor_blocks_after=18,
                reserved_gdt_before=1018, reserved_gdt_after=1014,
                inodes_per_group=8192, inode_size=256, inode_blocks_per_group=512,
                inode_count_before=7208960, inode_count_after=9306112,
                features=FEATURES)
MAX_CAPTURE = 1 << 20
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


class Stop(RuntimeError):
    pass


def require(ok, message):
    if not ok:
        raise Stop(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def load_bound(path, sha256):
    path = Path(path)
    require(path.is_absolute() and path.resolve() == path, 'noncanonical bound file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= MAX_CAPTURE, 'invalid bound file')
        raw = os.read(fd, MAX_CAPTURE + 1)
        after = os.fstat(fd)
        require(before == after and os.stat(path, follow_symlinks=False) == after,
                'bound file changed')
    finally:
        os.close(fd)
    require(digest(raw) == sha256, 'bound file digest mismatch')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Stop('nonfinite JSON')))


def publish(path, value):
    raw = canonical(value) + b'\n'
    require(len(raw) <= MAX_CAPTURE, 'metadata overflow')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        parent = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)


def starttime(pid):
    return Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()[19]


class Runner:
    """Bound output; NEVER kill/retry an uncertain maintenance command."""
    def __init__(self, out, lockfd):
        self.out, self.lockfd, self.index = out, lockfd, 0

    def __call__(self, argv, timeout=20):
        self.index += 1
        prefix = self.out / ('%03d' % self.index)
        publish(str(prefix) + '.command.json', dict(scope=SCOPE, argv=argv, timeout=timeout))
        def limits():
            resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_CAPTURE, MAX_CAPTURE))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        with open(str(prefix) + '.stdout', 'xb') as stdout, open(str(prefix) + '.stderr', 'xb') as stderr:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'},
                                     pass_fds=(self.lockfd,), start_new_session=True, preexec_fn=limits)
            publish(str(prefix) + '.started.json', dict(pid=child.pid, starttime=starttime(child.pid)))
            try:
                rc = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                publish(str(prefix) + '.uncertain.json', dict(pid=child.pid, status='TIMEOUT_NOT_RETIRED'))
                raise Stop('timeout: child retains inherited permanent lock; no kill or successor')
        raw = Path(str(prefix) + '.stdout').read_bytes()
        err = Path(str(prefix) + '.stderr').read_bytes()
        publish(str(prefix) + '.terminal.json', dict(returncode=rc, stdout_bytes=len(raw), stderr_bytes=len(err)))
        require(rc == 0 and len(raw) < MAX_CAPTURE and len(err) < MAX_CAPTURE, 'command failed/output limit')
        return raw.decode(), err.decode()


def scalar(path):
    with open(path) as stream:
        value = stream.read(16385)
    require(len(value) <= 16384, 'scalar overflow')
    return value.strip()


def parse_header(text):
    result = {}
    for line in text.splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            require(key not in result, 'duplicate ext4 field')
            result[key] = value.strip()
    return result


def required_header(blocks):
    require(blocks in (OLD_BLOCKS, NEW_BLOCKS), 'unsupported filesystem geometry')
    grown = blocks == NEW_BLOCKS
    return {'Filesystem UUID': UUID, 'Filesystem magic number': '0xEF53',
            'Filesystem state': 'clean', 'Errors behavior': 'Continue', 'Block count': str(blocks),
            'Reserved block count': str(RESERVE), 'Block size': '4096', 'Fragment size': '4096',
            'First block': '0', 'Blocks per group': '32768', 'Group descriptor size': '64',
            'Reserved GDT blocks': str(GEOMETRY['reserved_gdt_after' if grown else 'reserved_gdt_before']),
            'Inode count': str(GEOMETRY['inode_count_after' if grown else 'inode_count_before']),
            'Inodes per group': '8192', 'Inode size': '256', 'Inode blocks per group': '512',
            'Flex block group size': '16', 'First inode': '11',
            'Journal features': 'journal_incompat_revoke journal_64bit journal_checksum_v3',
            'Reserved blocks uid': '0 (user root)', 'Reserved blocks gid': '0 (group root)'}


def snapshot(run, sizes):
    require(BACKING.resolve() == BACKING, 'backing canonical path changed')
    meta = os.stat(BACKING, follow_symlinks=False)
    require(stat.S_ISREG(meta.st_mode) and
            (meta.st_dev, meta.st_ino, meta.st_uid, meta.st_gid, stat.S_IMODE(meta.st_mode), meta.st_size)
            == (66306, 47468427, 0, 0, 0o600, sizes[0]), 'backing identity/size changed')
    mounts = json.loads(run(['/usr/bin/findmnt', '-J', '-T', str(MOUNT), '-o',
                             'SOURCE,TARGET,FSTYPE,UUID,OPTIONS'])[0])['filesystems']
    require(len(mounts) == 1, 'mount count changed')
    mount = mounts[0]
    require(mount['target'] == str(MOUNT) and mount['fstype'] == 'ext4' and mount['uuid'] == UUID
            and set(mount['options'].split(',')) == {'rw', 'nosuid', 'nodev', 'relatime'}, 'mount changed')
    device = mount['source']
    require(re.fullmatch('/dev/loop[0-9]+', device) is not None, 'not a loop device')
    devmeta = os.stat(device)
    require(stat.S_ISBLK(devmeta.st_mode) and os.major(devmeta.st_rdev) == 7, 'not loop block device')
    mountmeta = os.stat(MOUNT, follow_symlinks=False)
    require(MOUNT.resolve() == MOUNT and stat.S_ISDIR(mountmeta.st_mode)
            and mountmeta.st_dev == devmeta.st_rdev, 'mounted directory/device disagreement')
    sysbase = Path('/sys/dev/block/%d:%d' % (os.major(devmeta.st_rdev), os.minor(devmeta.st_rdev)))
    loops = json.loads(run(['/usr/sbin/losetup', '--list', '--json', '--output',
                            'NAME,MAJ:MIN,BACK-FILE,BACK-INO,BACK-MAJ:MIN,SIZELIMIT,OFFSET,AUTOCLEAR,RO', device])[0])['loopdevices']
    require(len(loops) == 1, 'loop count changed')
    loop = loops[0]
    require(loop['name'] == device and loop['back-file'] == str(BACKING)
            and loop['maj:min'] == '%d:%d' % (os.major(devmeta.st_rdev), os.minor(devmeta.st_rdev))
            and type(loop['back-ino']) is int and loop['back-ino'] == meta.st_ino
            and loop['back-maj:min'] == '%d:%d' % (os.major(meta.st_dev), os.minor(meta.st_dev))
            and int(loop['offset']) == 0 and int(loop['sizelimit']) == 0
            and loop['autoclear'] is True and loop['ro'] is False, 'loop binding changed')
    for name, expected in [('loop/backing_file', str(BACKING)), ('loop/offset', '0'),
                           ('loop/sizelimit', '0'), ('queue/logical_block_size', '512'),
                           ('queue/physical_block_size', '512'), ('size', str(sizes[1] // 512))]:
        require(scalar(sysbase / name) == expected, 'loop sysfs mismatch: ' + name)
    text, _ = run(['/usr/sbin/dumpe2fs', '-h', device])
    header = parse_header(text)
    expected = required_header(sizes[2])
    require(all(header.get(k) == v for k, v in expected.items()), 'filesystem geometry/reserve/health mismatch')
    require('Filesystem features' in header and sorted(header['Filesystem features'].split()) == FEATURES,
            'unsupported/missing filesystem features (resize_inode required)')
    require(int(header.get('FS Error count', '0')) == 0, 'filesystem recorded errors')
    health = Path('/sys/fs/ext4') / Path(device).name
    require(scalar(health / 'errors_count') == '0' and scalar(health / 'warning_count') == '0',
            'runtime filesystem errors/warnings')
    return dict(device=device, devnum=devmeta.st_rdev, header=header, allocated=meta.st_blocks * 512)


def capacity(allocated, host_extra, scratch_extra):
    require(type(host_extra) is int and host_extra >= 2**30 and type(scratch_extra) is int and scratch_extra >= 0,
            'explicit aggregate capture/metadata/emergency budgets required')
    host = os.statvfs(BACKING.parent)
    scratch = os.statvfs(MOUNT)
    gap = max(0, TARGET - allocated)
    require(host.f_bavail * host.f_frsize >= 16 * 2**30 + gap + host_extra, 'host full-growth floor failed')
    require(scratch.f_bavail * scratch.f_frsize >= 12 * 2**30 + scratch_extra, 'scratch floor failed')


def execute_steps(run, observe, capacity_check):
    """Small mockable state machine; a failed check prevents EVERY successor."""
    first = observe((OLD, OLD, OLD_BLOCKS))
    capacity_check(first['allocated'])
    run(['/usr/bin/truncate', '--size=' + str(TARGET), '--', str(BACKING)])
    after_file = observe((TARGET, OLD, OLD_BLOCKS))
    require(after_file['device'] == first['device'] and after_file['devnum'] == first['devnum'], 'loop identity changed')
    capacity_check(after_file['allocated'])
    run(['/usr/sbin/losetup', '--set-capacity', first['device']])
    after_loop = observe((TARGET, TARGET, OLD_BLOCKS))
    require(after_loop['device'] == first['device'] and after_loop['devnum'] == first['devnum'], 'loop identity changed')
    capacity_check(after_loop['allocated'])
    output, error = run(['/usr/sbin/resize2fs', first['device'], str(NEW_BLOCKS)], timeout=600)
    require(not re.search(r'fallback|falling back|old-style|error|failed|Old resize interface requested\.|'
                          r'Performing an on-line resize', output + error, re.I), 'resize fallback/error')
    last = observe((TARGET, TARGET, NEW_BLOCKS))
    require(last['device'] == first['device'] and last['devnum'] == first['devnum'], 'loop identity changed')
    # Reserved GDT blocks legitimately decrease as descriptor blocks are added.
    fields = ('Filesystem features', 'Block size', 'Blocks per group', 'Group descriptor size',
              'Inodes per group', 'Inode size', 'Errors behavior', 'Journal features')
    require(all(k in first['header'] and k in last['header'] and first['header'][k] == last['header'][k]
                for k in fields), 'filesystem features missing/changed')
    capacity_check(last['allocated'])
    return last


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True)
    parser.add_argument('--release-sha256', required=True)
    args = parser.parse_args(argv)
    release = load_bound(args.release, args.release_sha256)
    require(release.get('status') == 'PASS_EXECUTION_RELEASE' and release.get('scope') == SCOPE
            and release.get('execution_count') == 1, 'one-shot independent release required')
    require(release.get('source_sha256') == digest(Path(__file__).read_bytes()), 'source release mismatch')
    review = load_bound(**release['independent_review'])
    payload = {k: v for k, v in release.items() if k != 'independent_review'}
    require(review.get('decision') == 'PASS_EXECUTION' and review.get('implementation_ownership') is False
            and review.get('reviewer') and review['reviewer'] != release.get('author')
            and review.get('reviewed_release_payload_sha256') == digest(canonical(payload)), 'independent review mismatch')
    require(release.get('historical_128m_attempt_disposition') == 'NOT_EXECUTED_RESOLVED'
            and release.get('stock_resize2fs_fallback_risk_explicitly_accepted') is True,
            'historical disposition/stock internal-fallback review missing')
    qualification = load_bound(**release['filesystem_qualification'])
    require(qualification.get('status') == 'PASS_NATIVE_EXT4_GROWTH_110_TO_142'
            and qualification.get('uuid') == UUID and qualification.get('expected_reserved_blocks') == RESERVE
            and qualification.get('kernel_vendor_binding_verified') is True
            and qualification.get('resize2fs_vendor_binding_verified') is True
            and qualification.get('geometry') == GEOMETRY
            and qualification.get('kernel_release') == os.uname().release
            and qualification.get('kernel_version_signature') == scalar('/proc/version_signature')
            and qualification.get('resize2fs_sha256') == digest(Path('/usr/sbin/resize2fs').read_bytes())
            and qualification.get('dumpe2fs_sha256') == digest(Path('/usr/sbin/dumpe2fs').read_bytes()),
            'exact installed filesystem/tool qualification required')
    require(os.geteuid() == 0 and os.sched_getaffinity(0) == {7}, 'existing CPU7 root route required')
    out = Path(release['capture_directory'])
    require(out.is_absolute() and out.resolve() == out and str(out).startswith(str(BACKING.parent / 'host-preparation') + '/')
            and out.is_dir() and not list(out.iterdir()), 'fresh external capture directory required')
    lockfd = os.open(LOCK, os.O_RDONLY | os.O_NOFOLLOW)
    lockmeta = os.fstat(lockfd)
    require(stat.S_ISREG(lockmeta.st_mode) and (lockmeta.st_dev, lockmeta.st_ino) == (27, 4)
            and os.stat(LOCK, follow_symlinks=False) == lockmeta, 'permanent mutex changed')
    fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    # A root-route observer must provide fresh positive retirement and finite
    # exact active-consumer reconciliation; absence of launcher PIDs is insufficient.
    retirement = load_bound(**release['retirement'])
    require(retirement.get('status') == 'PASS_POSITIVE_RETIREMENT' and retirement.get('boot_id') ==
            scalar('/proc/sys/kernel/random/boot_id') and 0 <= time.time() - retirement['observed_epoch'] <= 60
            and retirement.get('scratch_writers') == [] and retirement.get('qemu_tasks') == []
            and retirement.get('docker_tasks') == [] and retirement.get('live_leases') == []
            and retirement.get('active_110gib_consumers_reconciled') is True
            and retirement.get('protected_scratch21_unchanged') is True, 'fresh campaign retirement missing')
    require(digest(HELPER.read_bytes()) == HELPER_SHA, 'shared-heavy protocol source changed')
    spec = importlib.util.spec_from_file_location('existing_heavy_protocol', HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    # Existing O_EXCL + fsync record protocol. No release/unlink in this program.
    shared, record = helper._acquire_lock(SHARED, release, 'scratch-growth-maintenance')
    publish(out / 'retained-owner.json', dict(path=str(shared), record=record, permanent_mutex=[27, 4]))
    run = Runner(out, lockfd)
    try:
        result = execute_steps(run, lambda sizes: snapshot(run, sizes),
                               lambda allocated: capacity(allocated, release['host_extra_bytes'], release['scratch_extra_bytes']))
        publish(out / 'result.json', dict(status='PASS_GROWTH_POSTCHECKS_OWNERSHIP_RETAINED', result=result,
                                         workload_released=False, ownership_retired=False))
    except BaseException as error:
        publish(out / 'failure.json', dict(status='STOP_OWNERSHIP_RETAINED', error=repr(error),
                                          replay_allowed=False, shrink_allowed=False))
        raise


if __name__ == '__main__':
    main()
