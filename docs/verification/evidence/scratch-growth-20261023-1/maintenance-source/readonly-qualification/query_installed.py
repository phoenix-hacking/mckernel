#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Preparation source only: bounded READ-ONLY installed/loop/ext4 metadata query.
No filesystem, loop, reserve, module, Docker, guest or ownership-record mutation.
This emits evidence, not the vendor-source qualification or an execution release.
"""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import stat
import subprocess
import time

SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
APPROVED = Path('/home/holden/mckernel/docs/verification/evidence/scratch-growth-20261023-1/maintenance-source/grow_scratch.py')
APPROVED_SHA = '932f92710d7fb5dfd7bc4e66eedb9684059dd9b328bad7ae3a7c3edf872b3a84'
KERNEL = '5.15.0-139-generic'
MAX_STREAM = 256 << 10
MAX_REPORT = 4 << 20
RECORDS = []
DEADLINE = None
LOCKFD = None


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def stable_file(path, maximum):
    path = Path(path).resolve(strict=True)
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        a = os.fstat(fd)
        need(stat.S_ISREG(a.st_mode) and a.st_size <= maximum, 'bounded regular file required: ' + str(path))
        sha, md5, size = hashlib.sha256(), hashlib.md5(), 0
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            size += len(block)
            need(size <= maximum, 'file growth: ' + str(path))
            sha.update(block)
            md5.update(block)
        b, c = os.fstat(fd), path.stat()
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_uid', 'st_gid', 'st_nlink',
                  'st_size', 'st_mtime_ns', 'st_ctime_ns')
        need(size == b.st_size and all(getattr(a, key) == getattr(b, key) == getattr(c, key) for key in fields),
             'file changed while hashing: ' + str(path))
        return dict(path=str(path), sha256=sha.hexdigest(), md5=md5.hexdigest(), size=size,
                    device=b.st_dev, inode=b.st_ino, uid=b.st_uid, gid=b.st_gid, mode=oct(stat.S_IMODE(b.st_mode)))
    finally:
        os.close(fd)


def small_text(path, maximum=512 << 10):
    with open(path) as stream:
        text = stream.read(maximum + 1)
    need(len(text.encode()) <= maximum, 'text bound: ' + str(path))
    return text


def run(argv, timeout=3):
    allowed = ('/usr/bin/findmnt', '/usr/sbin/losetup', '/usr/sbin/dumpe2fs', '/usr/bin/dpkg-query')
    need(argv[0] in allowed, 'readonly command whitelist')
    need(argv[0] != '/usr/sbin/losetup' or '--list' in argv, 'losetup mutation refused')
    need(argv[0] != '/usr/sbin/dumpe2fs' or argv[1] == '-h', 'header query only')
    left = DEADLINE - time.monotonic()
    need(left > 0, 'query deadline')
    # Fixed metadata leaf commands remain inside the outer owned process group.
    # TimeoutExpired kills/joins this direct READ-ONLY command; no replay follows.
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=min(timeout, left), pass_fds=(LOCKFD,),
                                env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'})
    except subprocess.TimeoutExpired as error:
        RECORDS.append(dict(argv=argv, timed_out=True, stdout=(error.stdout or b'')[:MAX_STREAM].decode(errors='replace'),
                            stderr=(error.stderr or b'')[:MAX_STREAM].decode(errors='replace')))
        raise
    need(len(result.stdout) <= MAX_STREAM and len(result.stderr) <= MAX_STREAM, 'command stream overflow')
    RECORDS.append(dict(argv=argv, returncode=result.returncode, stdout=result.stdout.decode(), stderr=result.stderr.decode()))
    need(result.returncode == 0, 'read-only metadata command failed')
    return result.stdout.decode(), result.stderr.decode()


def capacity(module):
    backing = module.BACKING.stat()
    host, scratch = os.statvfs(module.BACKING.parent), os.statvfs(module.MOUNT)
    need(module.MOUNT.stat().st_dev != module.BACKING.parent.stat().st_dev, 'distinct HOST and scratch')
    allocated = backing.st_blocks * 512
    gap = max(0, module.TARGET - allocated)
    host_free, scratch_free = host.f_bavail * host.f_frsize, scratch.f_bavail * scratch.f_frsize
    return dict(backing_allocated_bytes=allocated, full_remaining_sparse_gap_to_142gib=gap,
                host_available_bytes=host_free, scratch_available_bytes=scratch_free,
                host_floor_bytes=16 * 2**30, scratch_floor_bytes=12 * 2**30,
                host_margin_after_full_gap_and_floor=host_free - gap - 16 * 2**30,
                scratch_margin_above_floor=scratch_free - 12 * 2**30,
                all_lane_extra_budget_grant=None, admission_granted=False)


def main():
    global DEADLINE, LOCKFD
    begin = time.monotonic()
    DEADLINE = begin + 28
    report = dict(scope=SCOPE, status='FAIL_READONLY_QUERY_PRESERVE_ALL', commands=RECORDS,
                  vendor_source_qualification=False, mutation_performed=False, workload_released=False,
                  stock_resize2fs_fallback_risk_explicitly_accepted=None)
    try:
        need(os.geteuid() == 0 and os.sched_getaffinity(0) == {7}, 'reviewed CPU7 root metadata route required')
        for number, expected in [(resource.RLIMIT_AS, (2 << 30, 2 << 30)),
                                 (resource.RLIMIT_CPU, (30, 30)), (resource.RLIMIT_FSIZE, (8 << 20, 8 << 20)),
                                 (resource.RLIMIT_CORE, (0, 0)), (resource.RLIMIT_NOFILE, (256, 256))]:
            need(resource.getrlimit(number) == expected, 'exact reviewed root query resource limits required')
        need(os.uname().release == KERNEL, 'frozen installed kernel changed')
        approved = stable_file(APPROVED, 1 << 20)
        need(approved['sha256'] == APPROVED_SHA, 'approved candidate2 source changed')
        spec = importlib.util.spec_from_file_location('source_approved_growth', APPROVED)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # __main__ is NOT invoked; no growth/ownership code executes.
        LOCKFD = os.open(module.LOCK, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        a, b = os.fstat(LOCKFD), os.stat(module.LOCK, follow_symlinks=False)
        need(stat.S_ISREG(a.st_mode) and (a.st_dev, a.st_ino) == (27, 4)
             and (b.st_dev, b.st_ino) == (27, 4), 'permanent27:4 identity')
        fcntl.flock(LOCKFD, fcntl.LOCK_EX | fcntl.LOCK_NB)
        report['permanent_lock'] = [a.st_dev, a.st_ino]
        report['approved_snapshot_source'] = approved
        report['before'] = module.snapshot(run, (module.OLD, module.OLD, module.OLD_BLOCKS))
        report['capacity_before'] = capacity(module)
        report['kernel_release'] = os.uname().release
        report['kernel_version_signature'] = small_text('/proc/version_signature', 16384).strip()
        report['loaded_ext4_srcversion'] = (small_text('/sys/module/ext4/srcversion', 16384).strip()
                                            if Path('/sys/module/ext4/srcversion').exists() else None)
        cmdline = small_text('/proc/cmdline', 16384)
        report['boot_image_argument'] = [word for word in cmdline.split() if word.startswith('BOOT_IMAGE=')]
        packages = ['e2fsprogs', 'linux-image-' + KERNEL, 'linux-modules-' + KERNEL]
        package_text, _ = run(['/usr/bin/dpkg-query', '-W',
                               '-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n', *packages])
        report['package_versions_sources'] = package_text
        checks = [('e2fsprogs', 'sbin/resize2fs'), ('e2fsprogs', 'sbin/dumpe2fs'),
                  ('linux-image-' + KERNEL, 'boot/vmlinuz-' + KERNEL),
                  ('linux-modules-' + KERNEL, 'boot/config-' + KERNEL)]
        report['installed_selected_files'] = []
        manifests = {}
        for package, relative in checks:
            if package not in manifests:
                manifest = Path('/var/lib/dpkg/info') / (package + '.md5sums')
                rows = small_text(manifest).splitlines()
                manifests[package] = dict(line.split(None, 1)[::-1] for line in rows)
            expected = manifests[package].get(relative)
            need(expected is not None, 'selected package manifest entry missing')
            item = stable_file('/' + relative, 32 << 20)
            need(item['md5'] == expected, 'installed selected file differs from package manifest')
            item.update(package=package, package_manifest_md5=expected,
                        package_manifest_path='/var/lib/dpkg/info/' + package + '.md5sums')
            report['installed_selected_files'].append(item)
        config = small_text('/boot/config-' + KERNEL)
        selected = ('CONFIG_EXT4_FS=', 'CONFIG_64BIT=', 'CONFIG_X86_64=')
        report['selected_running_release_config'] = [line for line in config.splitlines() if line.startswith(selected)]
        need('CONFIG_EXT4_FS=y' in report['selected_running_release_config'], 'expected built-in ext4 configuration changed')
        report['qualified_geometry_candidate'] = module.GEOMETRY
        report['after'] = module.snapshot(run, (module.OLD, module.OLD, module.OLD_BLOCKS))
        # Full headers retain volatile free/journal counters; equality is only
        # required for stable identity and the independently approved geometry.
        need(all(report['before'][key] == report['after'][key] for key in ('device', 'devnum')),
             'selected loop identity changed during readonly query')
        keys = [*module.required_header(module.OLD_BLOCKS), 'Filesystem features']
        need(all(report['before']['header'][key] == report['after']['header'][key] for key in keys),
             'selected filesystem geometry changed during readonly query')
        report['capacity_after'] = capacity(module)
        report['status'] = 'PASS_READONLY_INSTALLED_METADATA_NOT_VENDOR_SOURCE_QUALIFICATION'
    except BaseException as error:
        report['error'] = repr(error)
    finally:
        report['elapsed_seconds'] = time.monotonic() - begin
        raw = json.dumps(report, sort_keys=True, allow_nan=False)
        need(len(raw.encode()) <= MAX_REPORT, 'whole readonly report overflow')
        print(raw, flush=True)
        if LOCKFD is not None:
            os.close(LOCKFD)
    return 0 if report['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    raise SystemExit(main())
