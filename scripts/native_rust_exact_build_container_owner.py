#!/usr/bin/env python3
"""One offline build owner; a crash never authorizes automatic lease stealing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid

if __package__:
    from . import native_rust_exact_build_offline as provenance
else:
    import native_rust_exact_build_offline as provenance

LIMITS = {'NanoCpus': 4000000000, 'CpusetCpus': '2-5',
          'Memory': 12 * 2**30, 'MemorySwap': 12 * 2**30,
          'PidsLimit': 512, 'NetworkMode': 'none'}
# This is the reviewed host-wide aggregate budget.  A source on tmpfs consumes
# host memory in addition to the container's fixed cgroup reservation.
MEMORY_AGGREGATE_LIMIT = 24 * 2**30
RESOURCE_ARGS = ['--cpus=4', '--cpuset-cpus=2-5', '--memory=12g',
                 '--memory-swap=12g', '--pids-limit=512']
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
       'TZ': 'UTC', 'PYTHONHASHSEED': '0', 'GIT_TERMINAL_PROMPT': '0',
       'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_CONFIG_NOSYSTEM': '1',
       'GIT_CONFIG_GLOBAL': '/dev/null'}
SUDO_DOCKER_PREFIX = ('/usr/bin/sudo', '-A', '/usr/bin/docker',
                      '--host=unix:///var/run/docker.sock')


def docker_env():
    """Return the reviewed client environment without exposing askpass data."""
    environment = dict(ENV)
    if 'SUDO_ASKPASS' in os.environ:
        # sudo alone receives this inherited value; it is never logged,
        # serialized, or included in the container environment.
        environment['SUDO_ASKPASS'] = os.environ['SUDO_ASKPASS']
    return environment


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    with temporary.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def inventory(root):
    return {str(p.relative_to(root)): {'sha256': digest(p), 'size': p.stat().st_size}
            for p in sorted(Path(root).rglob('*')) if p.is_file() and not p.is_symlink()}


def exact_sha(value, size=40):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{%d}' % size, value):
        raise ValueError('invalid exact SHA identity')
    return value


def regular(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('not a regular non-symlink file: ' + str(path))
    return path


def roots_disjoint(paths):
    resolved = [Path(p).resolve(strict=True) for p in paths]
    for i, path in enumerate(resolved):
        if any(path == other or path in other.parents or other in path.parents
               for other in resolved[i + 1:]):
            raise ValueError('input/output roots overlap')


def validate_memory_allocation_roots(source_root, values):
    """Return canonical, disjoint allocation roots for host-memory admission."""
    if not isinstance(values, list) or not values:
        raise ValueError('memory_allocation_roots must be a nonempty JSON list')
    source = Path(source_root).resolve(strict=True)
    roots = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError('memory allocation root is not a path string')
        root = Path(value)
        if not root.is_absolute() or root.is_symlink() or not root.is_dir():
            raise ValueError('invalid memory allocation root: ' + str(root))
        resolved = root.resolve(strict=True)
        # A symlink in any supplied path component makes the root an alias,
        # even if its final component is itself an ordinary directory.
        component = Path(root.anchor)
        for part in root.parts[1:]:
            component /= part
            if component.is_symlink():
                raise ValueError('memory allocation root contains symlink: ' + str(root))
        for other in roots:
            if (resolved == other or resolved.samefile(other)):
                raise ValueError('duplicate or alias memory allocation root')
            if resolved in other.parents or other in resolved.parents:
                raise ValueError('overlapping memory allocation roots')
        roots.append(resolved)
    if source not in roots:
        raise ValueError('memory_allocation_roots must include source_root')
    return roots


def _git_config_entries(config):
    """Yield lower-case (section, key, value) entries without includes."""
    section = ''
    for number, raw in enumerate(config.read_text().splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith(('#', ';')):
            continue
        if line.startswith('[') and line.endswith(']'):
            header = line[1:-1].strip()
            section = header.split(None, 1)[0].lower()
            if section in ('include', 'includeif'):
                raise ValueError('git config include indirection: %s:%d' % (config, number))
            continue
        if '=' not in line:
            raise ValueError('invalid git config entry: %s:%d' % (config, number))
        key, value = (part.strip() for part in line.split('=', 1))
        yield section, key.lower(), value


def _validate_git_metadata(source_root, label):
    """Require a self-contained, non-linked Git metadata directory."""
    source_root = Path(source_root)
    git_dir = source_root / '.git'
    if git_dir.is_symlink() or not git_dir.is_dir():
        raise ValueError('%s requires a self-contained .git directory' % label)

    # A symlink anywhere below .git can redirect object, config, or hook reads
    # outside the sole /src bind.  lstat-based walking also catches broken links.
    for directory, subdirectories, files in os.walk(git_dir, followlinks=False):
        for name in [*subdirectories, *files]:
            entry = Path(directory) / name
            if entry.is_symlink():
                raise ValueError('%s .git metadata symlink: %s' % (label, entry))

    if (git_dir / 'commondir').exists():
        raise ValueError('%s .git commondir indirection' % label)
    for alternate in (git_dir / 'objects' / 'info' / 'alternates',
                      git_dir / 'objects' / 'info' / 'http-alternates'):
        if alternate.exists():
            raise ValueError('%s .git alternates indirection' % label)

    config = git_dir / 'config'
    if config.is_symlink() or not config.is_file():
        raise ValueError('%s .git config is not a regular file' % label)
    for section, key, value in _git_config_entries(config):
        if section in ('include', 'includeif'):
            raise ValueError('%s .git config include indirection' % label)
        if (section == 'core' and key in ('hooksPath'.lower(), 'fsmonitor')) or \
                (section == 'core' and key in ('excludesfile', 'attributesfile')):
            raise ValueError('%s .git config metadata indirection: core.%s' % (label, key))
        if section == 'core' and key == 'worktree' and value:
            candidate = Path(value).expanduser()
            if not candidate.is_absolute():
                candidate = git_dir / candidate
            candidate = candidate.resolve(strict=False)
            root = source_root.resolve(strict=True)
            if candidate != root and root not in candidate.parents:
                raise ValueError('%s external core.worktree' % label)


def validate_git_roots(source_root):
    """Validate both repositories before any lease or container is created."""
    _validate_git_metadata(source_root, 'source_root')
    _validate_git_metadata(Path(source_root) / 'ihk', 'source_root/ihk')


_MEMORY_BACKED_FILESYSTEMS = frozenset(('tmpfs', 'ramfs'))
# Deliberately small: these are the reviewed ordinary-storage filesystems for
# this owner.  Treating an unfamiliar type as disk can undercount host RAM
# (for example a memory-backed FUSE filesystem), so it is not an admission
# shortcut.
_ORDINARY_STORAGE_FILESYSTEMS = frozenset(('ext4', 'xfs'))


def _unescape_mountinfo_path(value):
    """Strictly decode the four pathname escapes emitted by show_mountinfo."""
    if not isinstance(value, bytes):
        raise RuntimeError('mount inventory pathname is not bytes')
    decoded = bytearray()
    index = 0
    allowed = {0o40, 0o11, 0o12, 0o134}
    while index < len(value):
        byte = value[index]
        if byte != ord('\\'):
            if byte in (0, ord(' '), ord('\t'), ord('\n')):
                raise RuntimeError('unescaped mount inventory pathname byte')
            decoded.append(byte)
            index += 1
            continue
        escaped = value[index + 1:index + 4]
        if len(escaped) != 3 or any(digit < ord('0') or digit > ord('7')
                                    for digit in escaped):
            raise RuntimeError('malformed mount inventory escape')
        character = int(escaped, 8)
        if character not in allowed:
            raise RuntimeError('unsupported mount inventory escape')
        decoded.append(character)
        index += 4
    if b'\0' in decoded:
        raise RuntimeError('NUL mount inventory pathname')
    return bytes(decoded)


def _mountinfo_token(value, label):
    try:
        return value.decode('ascii')
    except UnicodeDecodeError as exc:
        raise RuntimeError('non-ASCII mount inventory %s: %s' % (label, exc))


def _mountinfo_path(value, number):
    value = _unescape_mountinfo_path(value)
    if not value.startswith(b'/'):
        raise RuntimeError('nonabsolute mount inventory path: %d' % number)
    if value != b'/':
        components = value.split(b'/')[1:]
        if (value.endswith(b'/') or b'' in components or
                any(component in (b'.', b'..') for component in components)):
            raise RuntimeError('nonnormalized mount inventory path: %d' % number)
    return os.fsdecode(value)


def _mountinfo_device(value, number):
    fields = value.split(b':')
    if len(fields) != 2 or not all(field.isdigit() for field in fields):
        raise RuntimeError('invalid mount inventory major:minor: %d' % number)
    major, minor = (int(field) for field in fields)
    if major < 0 or minor < 0:
        raise RuntimeError('invalid mount inventory major:minor: %d' % number)
    return '%d:%d' % (major, minor)


def _mountinfo_options(value, number):
    options = value.split(b',')
    if not options or any(not option for option in options) or not any(
            option in (b'ro', b'rw') for option in options):
        raise RuntimeError('invalid mount inventory options: %d' % number)


def _mountinfo_optional_fields(values, number):
    for value in values:
        if value == b'unbindable':
            continue
        name, separator, identifier = value.partition(b':')
        if (not separator or name not in (b'shared', b'master', b'propagate_from') or
                not identifier.isdigit()):
            raise RuntimeError('invalid mount inventory optional field: %d' % number)


def _mount_inventory():
    """Return authoritative mounts in this namespace, or fail closed.

    ``st_dev`` cannot distinguish a same-device bind mount from its parent.
    Mountinfo names every mountpoint, including file mounts, and is therefore
    the admission authority for a root's descendants.
    """
    try:
        records = []
        raw = Path('/proc/self/mountinfo').read_bytes()
        lines = raw.split(b'\n')
        for number, line in enumerate(lines, 1):
            if not line:
                if number == len(lines):
                    continue
                raise RuntimeError('empty mount inventory record: %d' % number)
            left, separator, right = line.partition(b' - ')
            fields = left.split(b' ')
            trailer = right.split(b' ')
            if (not separator or len(fields) < 6 or len(trailer) < 3 or
                    any(not field for field in [*fields, *trailer])):
                raise RuntimeError('invalid mount inventory record: %d' % number)
            if not fields[0].isdigit() or int(fields[0]) <= 0:
                raise RuntimeError('invalid mount inventory ID: %d' % number)
            if not fields[1].isdigit():
                raise RuntimeError('invalid mount inventory parent ID: %d' % number)
            _mountinfo_options(fields[5], number)
            _mountinfo_optional_fields(fields[6:], number)
            records.append({'mount_id': _mountinfo_token(fields[0], 'ID'),
                            'parent_id': _mountinfo_token(fields[1], 'parent ID'),
                            'mountpoint': _mountinfo_path(fields[4], number),
                            'filesystem': _mountinfo_token(trailer[0], 'filesystem'),
                            'device': _mountinfo_device(fields[2], number)})
        if not records:
            raise RuntimeError('empty mount inventory')
        return records
    except (OSError, ValueError) as exc:
        raise RuntimeError('mount inventory unavailable: ' + str(exc))


def _mount_for_path(path, mounts=None):
    """Return one unambiguous most-specific mount record containing *path*."""
    target = Path(path).resolve(strict=True)
    matches = []
    for record in _mount_inventory() if mounts is None else mounts:
        mountpoint = Path(record['mountpoint'])
        if target == mountpoint or mountpoint in target.parents:
            matches.append(record)
    if not matches:
        raise RuntimeError('filesystem classification unknown')
    longest = max(len(record['mountpoint']) for record in matches)
    selected = [record for record in matches if len(record['mountpoint']) == longest]
    if len(selected) != 1:
        raise RuntimeError('ambiguous stacked mount for allocation root: ' + str(target))
    return selected[0]


def _filesystem_type(path, binding=None):
    """Return the filesystem type from the authoritative mount inventory."""
    try:
        if binding is not None:
            if str(Path(path).resolve(strict=True)) != binding['path']:
                raise RuntimeError('allocation binding path mismatch')
            return binding['mount']['filesystem']
        return _mount_for_path(path)['filesystem']
    except (OSError, ValueError, KeyError, RuntimeError):
        return 'unknown'


def _filesystem_classification(filesystem):
    if filesystem in _MEMORY_BACKED_FILESYSTEMS:
        return 'memory-backed'
    if filesystem in _ORDINARY_STORAGE_FILESYSTEMS:
        return 'ordinary-storage'
    raise RuntimeError('memory allocation filesystem unsupported: ' + str(filesystem))


def _reject_descendant_mounts(root, mounts):
    """Reject any nested mount, even when it shares root's device number."""
    root = Path(root).resolve(strict=True)
    for record in mounts:
        mountpoint = Path(record['mountpoint'])
        if root in mountpoint.parents:
            raise RuntimeError('candidate allocation root contains nested mount: ' +
                               str(mountpoint))


def _root_identity(root):
    """Return the lstat identity that must remain bound to an admission root."""
    canonical = Path(root).resolve(strict=True)
    try:
        info = os.lstat(str(canonical))
    except OSError as exc:
        raise RuntimeError('candidate allocation root lstat failed: ' + str(exc))
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError('candidate allocation root is not a directory')
    return {'path': str(canonical), 'device': info.st_dev, 'inode': info.st_ino,
            'file_type': stat.S_IFMT(info.st_mode)}


def _mount_identity(record):
    """The complete procfs identity that binds a root to its visible mount."""
    try:
        return {'mount_id': record['mount_id'], 'parent_id': record['parent_id'],
                'device': record['device'], 'mountpoint': record['mountpoint'],
                'filesystem': record['filesystem']}
    except KeyError as exc:
        raise RuntimeError('mount inventory identity missing field: ' + str(exc))


def _mount_scope(root, mounts):
    """Capture the root mount plus every strict descendant mount identity."""
    root = Path(root).resolve(strict=True)
    selected = _mount_identity(_mount_for_path(root, mounts))
    descendants = sorted((_mount_identity(record) for record in mounts
                          if root in Path(record['mountpoint']).parents),
                         key=lambda record: (record['mountpoint'], record['mount_id']))
    if descendants:
        raise RuntimeError('candidate allocation root contains nested mount: ' +
                           descendants[0]['mountpoint'])
    return {'mount': selected, 'descendants': descendants}


def _validate_root_mount_device(root, scope):
    """Bind the visible mount's major:minor to the root lstat device."""
    actual = '%d:%d' % (os.major(root['device']), os.minor(root['device']))
    if scope['mount']['device'] != actual:
        raise RuntimeError('allocation root mount device mismatch: expected %s got %s' %
                           (actual, scope['mount']['device']))


def _capture_allocation_binding(root):
    """Take a stable root/mount snapshot, rejecting changes while it is read."""
    before_mounts = _mount_inventory()
    before_root = _root_identity(root)
    before_scope = _mount_scope(before_root['path'], before_mounts)
    after_mounts = _mount_inventory()
    after_root = _root_identity(before_root['path'])
    after_scope = _mount_scope(after_root['path'], after_mounts)
    if before_root != after_root or before_scope != after_scope:
        raise RuntimeError('candidate allocation root mount identity changed during binding')
    _validate_root_mount_device(before_root, before_scope)
    return {'path': before_root['path'], 'root': before_root,
            'mount': before_scope['mount'], 'descendants': before_scope['descendants']}


def _revalidate_allocation_binding(binding):
    """Fail closed if root identity, selected mount, or nested mounts changed."""
    root = binding['path']
    identity = _root_identity(root)
    mounts = _mount_inventory()
    scope = _mount_scope(root, mounts)
    if (identity != binding['root'] or scope['mount'] != binding['mount'] or
            scope['descendants'] != binding['descendants']):
        raise RuntimeError('candidate allocation root mount identity changed')
    _validate_root_mount_device(identity, scope)


def _allocated_bytes(root, binding=None):
    """Count allocated blocks after proving root has no descendant mounts.

    This is admission accounting, so an unreadable directory or a raced entry
    is not equivalent to an empty one.  Fail closed before the lease exists.
    """
    if binding is None:
        binding = _capture_allocation_binding(root)
    root = Path(binding['path'])
    current_root = _root_identity(root)
    if current_root != binding['root']:
        raise RuntimeError('candidate allocation root mount identity changed before walk')
    try:
        root_info = os.lstat(str(root))
    except OSError as exc:
        raise RuntimeError('candidate allocation root lstat failed: ' + str(exc))
    if ({'path': str(root), 'device': root_info.st_dev, 'inode': root_info.st_ino,
         'file_type': stat.S_IFMT(root_info.st_mode)} != binding['root']):
        raise RuntimeError('candidate allocation root mount identity changed before walk')
    device = root_info.st_dev

    def failed_walk(exc):
        raise RuntimeError('candidate allocation walk failed: ' + str(exc))

    def entry_info(path):
        try:
            return os.lstat(str(path))
        except OSError as exc:
            raise RuntimeError('candidate allocation lstat failed: %s: %s' % (path, exc))

    def allocated(info, path):
        blocks = info.st_blocks
        if (not isinstance(blocks, int) or isinstance(blocks, bool) or
                blocks < 0):
            raise RuntimeError('candidate allocation blocks invalid: ' + str(path))
        # Python integers cannot overflow, but the receipt must remain
        # representable by the reviewed host accounting interface.  Do not
        # conflate a large non-tmpfs source with host-memory consumption.
        if blocks > sys.maxsize // 512:
            raise RuntimeError('candidate allocation blocks overflow: ' + str(path))
        return blocks * 512

    total = 0
    for directory, directories, files in os.walk(str(root), followlinks=False,
                                                 onerror=failed_walk):
        directory_info = entry_info(directory)
        if (directory_info.st_dev != device or stat.S_ISLNK(directory_info.st_mode) or
                not stat.S_ISDIR(directory_info.st_mode)):
            raise RuntimeError('candidate allocation walk escaped root device')
        kept = []
        for name in directories:
            entry = Path(directory) / name
            info = entry_info(entry)
            if stat.S_ISLNK(info.st_mode):
                continue
            if info.st_dev != device:
                raise RuntimeError('candidate allocation walk crossed device: ' + str(entry))
            if not stat.S_ISDIR(info.st_mode):
                raise RuntimeError('candidate allocation walk contains non-directory: ' + str(entry))
            value = allocated(info, entry)
            if total > sys.maxsize - value:
                raise RuntimeError('candidate allocation total overflow')
            total += value
            kept.append(name)
        directories[:] = kept
        for name in files:
            entry = Path(directory) / name
            info = entry_info(entry)
            if stat.S_ISLNK(info.st_mode):
                continue
            if info.st_dev != device:
                raise RuntimeError('candidate allocation walk crossed device: ' + str(entry))
            value = allocated(info, entry)
            if total > sys.maxsize - value:
                raise RuntimeError('candidate allocation total overflow')
            total += value
    value = allocated(root_info, root)
    if total > sys.maxsize - value:
        raise RuntimeError('candidate allocation total overflow')
    total += value
    # A mount created while walking must not turn a successful pre-walk probe
    # into an implicit exclusion.  Recheck before returning the admission sum.
    _revalidate_allocation_binding(binding)
    return total


def measure(host, scratch, host_floor=16 * 2**30, scratch_floor=12 * 2**30,
            source_root=None, output_root=None, memory_allocation_roots=None):
    host = Path(host)
    scratch = Path(scratch)
    host_free = shutil.disk_usage(str(host)).free
    scratch_free = shutil.disk_usage(str(scratch)).free
    observed = {'host_free': host_free, 'host_device': host.stat().st_dev,
                'scratch_free': scratch_free, 'scratch_device': scratch.stat().st_dev}
    if (source_root is not None and output_root is not None and
            memory_allocation_roots is not None):
        source = Path(source_root).resolve(strict=True)
        output = Path(output_root)
        allocation_rows = []
        allocation_total = 0
        tmpfs_total = 0
        memory_backed_total = 0
        memory_backed_filesystems = set()
        allocation_bindings = []
        source_row = None
        for root in memory_allocation_roots:
            root = Path(root)
            binding = _capture_allocation_binding(root)
            filesystem = _filesystem_type(root, binding=binding)
            if filesystem == 'unknown':
                raise RuntimeError('memory allocation filesystem classification unknown')
            classification = _filesystem_classification(filesystem)
            allocated = _allocated_bytes(root, binding=binding)
            _revalidate_allocation_binding(binding)
            if (not isinstance(allocated, int) or isinstance(allocated, bool) or
                    allocated < 0 or allocation_total > sys.maxsize - allocated):
                raise RuntimeError('memory allocation unknown')
            row = {'path': str(root), 'device': root.stat().st_dev,
                   'filesystem': filesystem, 'free': shutil.disk_usage(str(root)).free,
                   'allocated_bytes': allocated,
                   'memory_effect_bytes': allocated if classification == 'memory-backed' else 0}
            allocation_rows.append(row)
            allocation_bindings.append(binding)
            allocation_total += allocated
            if classification == 'memory-backed':
                if memory_backed_total > sys.maxsize - allocated:
                    raise RuntimeError('memory allocation memory-backed total overflow')
                memory_backed_total += allocated
                memory_backed_filesystems.add(filesystem)
            if filesystem == 'tmpfs':
                if tmpfs_total > sys.maxsize - allocated:
                    raise RuntimeError('memory allocation tmpfs total overflow')
                tmpfs_total += allocated
            if root == source:
                source_row = row
        if source_row is None:
            raise RuntimeError('source root missing from memory allocation measurement')
        # Root A may change while root B is being scanned.  The aggregate is
        # admissible only when every captured binding still names the exact
        # lstat/mount snapshot that supplied its accounting contribution.
        for binding in allocation_bindings:
            _revalidate_allocation_binding(binding)
        observed.update(source_free=source_row['free'],
                        source_device=source_row['device'],
                        source_filesystem=source_row['filesystem'],
                        output_free=shutil.disk_usage(str(output)).free,
                        output_device=output.stat().st_dev,
                        output_filesystem=_filesystem_type(output),
                        candidate_allocated_bytes=source_row['allocated_bytes'],
                        memory_allocation_roots=allocation_rows,
                        memory_allocation_bindings=allocation_bindings,
                        memory_allocation_total_bytes=allocation_total,
                        memory_allocation_tmpfs_bytes=tmpfs_total,
                        memory_allocation_memory_backed_bytes=memory_backed_total,
                        container_tmpfs_bytes=256 * 2**20)
        if not memory_backed_filesystems:
            effect_classification = 'none'
        elif len(memory_backed_filesystems) == 1:
            effect_classification = next(iter(memory_backed_filesystems))
        else:
            effect_classification = 'mixed-memory-backed'
        observed['candidate_memory_effect'] = {
            'classification': effect_classification,
            'bytes': memory_backed_total}
        observed['aggregate_memory_limit'] = MEMORY_AGGREGATE_LIMIT
        observed['aggregate_memory_required'] = memory_backed_total + LIMITS['Memory']
        if observed['aggregate_memory_required'] > MEMORY_AGGREGATE_LIMIT:
            raise RuntimeError('candidate/container memory aggregate failed: ' +
                               json.dumps(observed))
    mem = Path('/proc/meminfo').read_text().split('MemAvailable:', 1)[1].split()[0]
    observed['memory_available'] = int(mem) * 1024
    if (observed['host_free'] < max(16 * 2**30, host_floor) or
            observed['scratch_free'] < max(12 * 2**30, scratch_floor) or
            observed['memory_available'] < 16 * 2**30):
        raise RuntimeError('measured resource floor failed: ' + json.dumps(observed))
    return observed


class Lease:
    def __init__(self, path, name):
        self.path = Path(path)
        self.nonce = uuid.uuid4().hex
        start = Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19]
        self.record = {'pid': os.getpid(), 'starttime': start, 'nonce': self.nonce,
                       'container_name': name, 'state': 'owned'}

    def acquire(self):
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(self.record, stream)
            stream.flush()
            os.fsync(stream.fileno())

    def release(self):
        if json.loads(self.path.read_text()).get('nonce') != self.nonce:
            raise RuntimeError('lease ownership changed')
        self.path.unlink()


class OwnerInterrupted(RuntimeError):
    pass


class CliSignals:
    """CLI-only handlers latch termination; imports do not alter handlers.

    Docker waits observe the latch promptly. Retirement commands run to their
    bounded deadlines even if a second TERM/INT arrives during cleanup.
    """
    def __init__(self):
        self.requested = None
        self.cleaning = False

    def __enter__(self):
        self.previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
        for sig in self.previous:
            signal.signal(sig, self.receive)
        return self

    def receive(self, signum, frame):
        if self.requested is None:
            self.requested = signum

    def check(self):
        if self.requested is not None and not self.cleaning:
            raise OwnerInterrupted('owner interrupted by signal %d' % self.requested)

    def __exit__(self, *exc):
        for sig, handler in self.previous.items():
            signal.signal(sig, handler)


class Docker:
    def __init__(self, log, signals=None, sudo=False):
        self.log = Path(log)
        self.signals = signals
        self.client_retirement_unproven = False
        self.command_prefix = SUDO_DOCKER_PREFIX if sudo else ('docker',)

    def _surviving_group_members(self, pgid):
        members = []
        try:
            entries = Path('/proc').glob('[0-9]*/stat')
            for stat in entries:
                try:
                    fields = stat.read_text().rsplit(')', 1)[1].split()
                    if len(fields) > 2 and int(fields[2]) == pgid:
                        members.append(int(stat.parent.name))
                except FileNotFoundError:
                    continue
                except PermissionError:
                    self.client_retirement_unproven = True
                except (ValueError, IndexError):
                    self.client_retirement_unproven = True
        except (FileNotFoundError, PermissionError):
            self.client_retirement_unproven = True
        return members

    def _record_client_exit(self, code, status):
        status['exit_code'] = code
        if self.command_prefix == SUDO_DOCKER_PREFIX and code is not None and code < 0:
            # A signalled sudo wrapper cannot attest that its privileged child
            # retired. That child may have escaped this process group, so an
            # empty group scan or a terminal container snapshot is insufficient.
            # This latch must survive subsequent successful cleanup commands.
            self.client_retirement_unproven = True
            status['client_retirement_unproven'] = True

    def _retire_client(self, process, status):
        """TERM the client group, then boundedly reap it; KILL is unproven."""
        if process is None:
            return
        if process.poll() is not None:
            self._record_client_exit(process.returncode, status)
            survivors = self._surviving_group_members(process.pid)
            if survivors:
                self.client_retirement_unproven = True
                status['client_survivors'] = survivors
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except BaseException as exc:
            self.client_retirement_unproven = True
            status['client_term_error'] = str(exc)
        try:
            process.wait(timeout=5)
        except BaseException as exc:
            self.client_retirement_unproven = True
            status['client_term_wait_error'] = str(exc)
        if process.poll() is None:
            self.client_retirement_unproven = True
            status['client_forced'] = True
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except BaseException as exc:
                self.client_retirement_unproven = True
                status['client_kill_error'] = str(exc)
            try:
                process.wait(timeout=5)
            except BaseException as exc:
                self.client_retirement_unproven = True
                status['client_reap_error'] = str(exc)
        self._record_client_exit(process.returncode, status)
        survivors = self._surviving_group_members(process.pid)
        if survivors:
            self.client_retirement_unproven = True
            status['client_survivors'] = survivors

    def call(self, args, timeout=120, check=True):
        if self.signals:
            self.signals.check()
        # These files are the primary evidence, not a buffer flushed by the
        # owner after command completion. Child writes survive owner SIGKILL.
        capture = self.log.parent / ('command-' + uuid.uuid4().hex)
        capture.mkdir()
        stdout_path, stderr_path = capture / 'stdout', capture / 'stderr'
        command = [*self.command_prefix, *args]
        status = {'argv': command, 'timeout': timeout, 'state': 'starting'}
        atomic(capture / 'status.json', status)
        with self.log.open('a') as stream:
            stream.write('$ ' + json.dumps(command) + '\n[capture ' + str(capture) + ']\n')
            stream.flush()
            os.fsync(stream.fileno())
        process = None
        try:
            with stdout_path.open('xb', buffering=0) as stdout, stderr_path.open('xb', buffering=0) as stderr:
                # A separate client process group permits exact client rundown;
                # container retirement remains the owner's independent duty.
                process = subprocess.Popen(command, env=docker_env(), stdout=stdout,
                                           stderr=stderr, start_new_session=True)
                status.update(state='running', pid=process.pid)
                atomic(capture / 'status.json', status)
                deadline = time.monotonic() + timeout
                while True:
                    if self.signals:
                        self.signals.check()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise RuntimeError('docker command timed out: ' + args[0])
                    try:
                        code = process.wait(timeout=min(0.1, remaining))
                        self._record_client_exit(code, status)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                os.fsync(stdout.fileno())
                os.fsync(stderr.fileno())
            status.update(state='exited', exit_code=code)
        except BaseException as exc:
            status.update(state='failed', error=str(exc))
            if process is not None:
                self._retire_client(process, status)
            raise
        finally:
            atomic(capture / 'status.json', status)
            with self.log.open('a') as stream:
                stream.write('[command status ' + json.dumps(status) + ']\n')
        result = subprocess.CompletedProcess(command, code,
                                             stdout_path.read_text(errors='replace'),
                                             stderr_path.read_text(errors='replace'))
        if check and result.returncode:
            raise RuntimeError('docker command failed: ' + args[0])
        return result


# Keep the real implementation distinguishable from test/injected clients;
# only the former is allowed to receive the privileged owner prefix.
_REAL_DOCKER = Docker


def inspect(docker, name):
    rows = json.loads(docker.call(['inspect', name]).stdout)
    if len(rows) != 1 or rows[0].get('Name') != '/' + name:
        raise RuntimeError('ambiguous container identity')
    return rows[0]


def check_profile(info, image, nonce, network='none', readonly=True, cap_add=()):
    expected = dict(LIMITS, NetworkMode=network)
    host = info.get('HostConfig', {})
    for key, value in expected.items():
        if host.get(key) != value:
            raise RuntimeError('effective limit mismatch: ' + key)
    if (host.get('Privileged') is not False or host.get('ReadonlyRootfs') != readonly or
            host.get('CapDrop') != ['ALL'] or
            host.get('SecurityOpt') != ['no-new-privileges'] or
            host.get('Init') is not True or host.get('PidMode', '') != '' or
            host.get('IpcMode') != 'private' or host.get('Devices') or
            host.get('DeviceRequests') or host.get('Binds') or
            sorted(host.get('CapAdd') or []) != sorted(cap_add) or
            host.get('CgroupParent', '') != ''):
        raise RuntimeError('effective isolation mismatch')
    if (info.get('Image') != image or
            info.get('Config', {}).get('Labels', {}).get('mckernel.owner') != nonce or
            info.get('State', {}).get('Status') != 'created'):
        raise RuntimeError('effective image/owner/state mismatch')


def retire(docker, name, nonce):
    """Observe terminal status; stop/kill return codes are not retirement proof."""
    info = inspect(docker, name)
    if info.get('Config', {}).get('Labels', {}).get('mckernel.owner') != nonce:
        raise RuntimeError('refusing retirement of another owner')
    if info['State'].get('Running') or info['State'].get('Status') in ('restarting', 'paused'):
        docker.call(['stop', '--time', '15', name], timeout=30, check=False)
        info = inspect(docker, name)
        if info['State'].get('Running'):
            docker.call(['kill', name], timeout=30, check=False)
        docker.call(['wait', name], timeout=30)
        info = inspect(docker, name)
    if (info['State'].get('Running') or info['State'].get('Pid', 0) != 0 or
            info['State'].get('Status') not in ('exited', 'created', 'dead')):
        raise RuntimeError('container retirement unproven; lease retained')
    return info


class BuildOwner:
    def __init__(self, request, docker=None, signals=None):
        self.r = dict(request)
        self.docker = docker
        self.signals = signals

    def validate(self):
        r = self.r
        exact_sha(r['candidate_sha'])
        if not re.fullmatch('sha256:[0-9a-f]{64}', r['image_id']):
            raise ValueError('full immutable image ID required')
        root_keys = ('source_root', 'assets_root', 'output_root', 'evidence_root',
                     'host_measure_root', 'scratch_measure_root')
        for key in root_keys:
            if key not in r:
                raise ValueError('missing required root: ' + key)
            p = Path(r[key])
            if not p.is_absolute() or p.is_symlink() or not p.is_dir() or ',' in str(p):
                raise ValueError('invalid root: ' + key)
        measurement_roots = [Path(r['host_measure_root']), Path(r['scratch_measure_root'])]
        if measurement_roots[0].stat().st_dev == measurement_roots[1].stat().st_dev:
            raise ValueError('measurement roots must be on distinct devices')
        validate_git_roots(r['source_root'])
        roots_disjoint([r[k] for k in ('source_root', 'assets_root', 'output_root', 'evidence_root')])
        if any(any(Path(r[k]).iterdir()) for k in ('output_root', 'evidence_root')):
            raise ValueError('fresh output/evidence roots required')
        if not 0 < r['timeout'] <= 19800:
            raise ValueError('timeout exceeds reviewed 330 minutes')
        if os.getuid() == 0 or os.geteuid() == 0:
            raise ValueError('offline build owner must be an unprivileged user')
        self.memory_allocation_roots = validate_memory_allocation_roots(
            r['source_root'], r.get('memory_allocation_roots'))
        for key in ('image_receipt', 'input_manifest', 'driver_path'):
            if digest(regular(r[key])) != r[key + '_sha256']:
                raise ValueError(key + ' hash mismatch')
        image = json.loads(Path(r['image_receipt']).read_text())
        if image.get('status') != 'PASS' or image.get('image_id') != r['image_id']:
            raise ValueError('image receipt is not successful or identity differs')
        manifest = json.loads(Path(r['input_manifest']).read_text())
        if manifest.get('candidate_sha') != r['candidate_sha']:
            raise ValueError('manifest candidate mismatch')
        # Run the same bounded provenance verifier before lease acquisition or
        # any Docker client construction. No partial/legacy manifest may reach
        # the privileged build path.
        try:
            provenance.verify_inputs(Path(r['source_root']), r['candidate_sha'],
                                     Path(r['assets_root']), manifest,
                                     provenance.Runner())
        except provenance.BuildError as error:
            raise ValueError('candidate input admission failed: ' + str(error))
        self.measurement = measure(r['host_measure_root'], r['scratch_measure_root'],
                                   r.get('host_floor', 0), r.get('scratch_floor', 0),
                                   source_root=r['source_root'], output_root=r['output_root'],
                                   memory_allocation_roots=self.memory_allocation_roots)

    def run(self):
        self.validate()
        r = self.r
        evidence = Path(r['evidence_root'])
        # Only this real-owner factory may select the privileged immutable
        # client prefix. Injected Docker implementations remain unprivileged.
        if self.docker is not None:
            docker = self.docker
        elif Docker is _REAL_DOCKER:
            docker = Docker(evidence / 'docker.log', signals=self.signals, sudo=True)
        else:
            # A substituted client is an injected test/preparation transport;
            # it must never inherit the real owner's executable prefix.
            docker = Docker(evidence / 'docker.log', signals=self.signals)
        name = 'mckernel-exact-' + uuid.uuid4().hex
        lease = Lease(r['lease_path'], name)
        lease.acquire()
        receipt = {'status': 'FAIL', 'candidate_sha': r['candidate_sha'],
                   'container_name': name, 'owner': lease.record, 'request': r,
                   'measurement': self.measurement, 'retired': False}
        attempted = False
        try:
            image = json.loads(docker.call(['image', 'inspect', r['image_id']]).stdout)[0]
            if image.get('Id') != r['image_id'] or image.get('Architecture') != 'amd64':
                raise RuntimeError('actual image identity mismatch')
            mounts = [(r['source_root'], '/src', True), (r['assets_root'], '/assets', True),
                      (r['output_root'], '/out', False), (r['evidence_root'], '/evidence', False),
                      (r['driver_path'], '/driver.py', True), (r['input_manifest'], '/inputs.json', True)]
            args = ['create', '--name', name, '--label', 'mckernel.owner=' + lease.nonce,
                    '--init', '--network=none', '--ipc=private', *RESOURCE_ARGS,
                    '--user', '%d:%d' % (os.getuid(), os.getgid()),
                    '--cap-drop=ALL', '--security-opt=no-new-privileges', '--read-only',
                    '--tmpfs', '/tmp:rw,nodev,nosuid,size=256m']
            for source, target, ro in mounts:
                args += ['--mount', 'type=bind,src=' + source + ',dst=' + target + (',readonly' if ro else '')]
            command = ['/driver.py', '--repo', '/src', '--candidate', r['candidate_sha'],
                       '--assets', '/assets', '--output', '/out', '--evidence', '/evidence/build',
                       '--manifest', '/inputs.json']
            args += ['--entrypoint', '/usr/bin/python3', r['image_id'], *command]
            attempted = True
            created = docker.call(args)
            receipt['container_id'] = created.stdout.strip()
            info = inspect(docker, name)
            atomic(evidence / 'inspect-before-start.json', info)
            check_profile(info, r['image_id'], lease.nonce)
            actual = {(m['Source'], m['Destination'], m['RW']) for m in info.get('Mounts', []) if m['Type'] == 'bind'}
            if (actual != {(s, t, not ro) for s, t, ro in mounts} or
                    any(m['Type'] != 'bind' for m in info.get('Mounts', [])) or
                    info['HostConfig'].get('Tmpfs') != {'/tmp': 'rw,nodev,nosuid,size=256m'}):
                raise RuntimeError('actual mount binding mismatch')
            if (info['Config'].get('Entrypoint') != ['/usr/bin/python3'] or
                    info['Config'].get('Cmd') != command or
                    info['Config'].get('User') != '%d:%d' % (os.getuid(), os.getgid())):
                raise RuntimeError('actual driver command mismatch')
            docker.call(['start', name])
            result = docker.call(['wait', name], timeout=r['timeout'])
            receipt['exit_code'] = int(result.stdout.strip())
            if receipt['exit_code'] != 0:
                raise RuntimeError('offline driver failed')
            build = json.loads((evidence / 'build' / 'receipt.json').read_text())
            if build.get('status') != 'PASS' or build.get('candidate_sha') != r['candidate_sha']:
                raise RuntimeError('missing successful driver receipt')
            for artifact in ('bzImage', 'ihk.ko', 'ihk-smp-x86_64.ko', 'mcctrl.ko', 'SHA256SUMS'):
                p = regular(evidence / 'build' / 'native-rust-build-evidence' / artifact)
                if p.stat().st_size == 0:
                    raise RuntimeError('empty build artifact')
            receipt['status'] = 'PASS'
        except BaseException as exc:
            receipt['error'] = str(exc)
        finally:
            if self.signals:
                self.signals.cleaning = True
            if attempted:
                try:
                    terminal = retire(docker, name, lease.nonce)
                    atomic(evidence / 'inspect-terminal.json', terminal)
                    receipt['retired'] = True
                except BaseException as exc:
                    receipt['status'] = 'FAIL'
                    receipt['retirement_error'] = str(exc)
                try:
                    logs = docker.call(['logs', name])
                    (evidence / 'container.log').write_text(logs.stdout + logs.stderr)
                    if receipt['status'] == 'PASS' and receipt['retired']:
                        docker.call(['rm', name])
                except BaseException as exc:
                    receipt['status'] = 'FAIL'
                    receipt['capture_error'] = str(exc)
            else:
                receipt['retired'] = True
            if getattr(docker, 'client_retirement_unproven', False):
                receipt.update(status='FAIL', retired=False, client_retirement_unproven=True)
            try:
                for binding in self.measurement.get('memory_allocation_bindings', []):
                    _revalidate_allocation_binding(binding)
            except BaseException as exc:
                receipt.update(status='FAIL', allocation_revalidation_error=str(exc))
            receipt['outputs'] = inventory(Path(r['output_root']))
            receipt['evidence'] = inventory(evidence)
            if self.signals and self.signals.requested is not None:
                receipt.update(status='FAIL', interrupted_signal=self.signals.requested)
            atomic(evidence / 'receipt.json', receipt)
            if receipt['retired']:
                lease.release()
        return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('request', type=Path)
    args = parser.parse_args()
    with CliSignals() as signals:
        result = BuildOwner(json.loads(args.request.read_text()), signals=signals).run()
    print(json.dumps(result))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
