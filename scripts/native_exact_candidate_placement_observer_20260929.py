#!/usr/bin/env python3
"""Read-only disk placement and Git identity; backup is metadata, not a worktree."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

ENV = dict(PATH='/usr/bin:/bin', HOME='/nonexistent', LANG='C', LC_ALL='C', TZ='UTC',
           GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
           GIT_NO_REPLACE_OBJECTS='1', GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='file')
OVERLAY_FILE = 'test/ihklib/whitebox/src/driver/mckernel/syscall.c'


def git(repo, *args, metadata=False):
    command = ['/usr/bin/git', '--git-dir=' + str(repo)] if metadata else ['/usr/bin/git', '-C', str(repo)]
    result = subprocess.run(command + ['-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false'] + list(args),
                            env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace'))
    return result.stdout


def mounts(text=None):
    result = []
    for line in (Path('/proc/self/mountinfo').read_text() if text is None else text).splitlines():
        left, right = line.split(' - ', 1)
        fields, tail = left.split(), right.split()
        if len(fields) < 6 or len(tail) < 3:
            raise RuntimeError('malformed mount row')
        name = re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), fields[4])
        result.append((Path(name), tail[0]))
    if not result:
        raise RuntimeError('empty mount table')
    return result


def safe_path(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise RuntimeError('noncanonical path')
    for ancestor in [path] + list(path.parents):
        if ancestor.is_symlink():
            raise RuntimeError('symlink path component: ' + str(ancestor))
    return path


def placement(scratch, roots, table=None, host_device=None):
    scratch = safe_path(scratch)
    table = mounts() if table is None else table
    entries = [item for item in table if item[0] == scratch]
    device = scratch.stat().st_dev
    if len(entries) != 1 or entries[0][1] not in ('ext4', 'xfs'):
        raise RuntimeError('scratch is not an exact disk-backed ext4/xfs mount')
    if device == (Path('/').stat().st_dev if host_device is None else host_device):
        raise RuntimeError('scratch is not distinct from host')
    for root in roots:
        root = safe_path(root)
        if root.parent != scratch:
            raise RuntimeError('root is not an immediate scratch child')
        if any(mp == root or root in mp.parents for mp, _ in table):
            raise RuntimeError('nested mount under allocation root')
        if root.exists() and (not root.is_dir() or root.stat().st_dev != device):
            raise RuntimeError('allocation root escaped scratch')
    return device, entries[0][1]


def allocation(root, device, exclude=None):
    """Count lstat blocks, including directories/symlinks, without following links."""
    total = 0
    def failed(error):
        raise error
    for base, directories, files in os.walk(str(root), followlinks=False, onerror=failed):
        base = Path(base)
        if exclude is not None and base == exclude:
            directories[:] = []
            continue
        for path in [base] + [base / n for n in files] + [base / n for n in directories if (base / n).is_symlink()]:
            info = path.lstat()
            if info.st_dev != device:
                raise RuntimeError('allocation escaped scratch device')
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)):
                raise RuntimeError('special allocation entry')
            total += info.st_blocks * 512
    return total


def committed_gitlinks(repo, sha):
    """Read names, modes and object IDs from the pinned tree, never live index."""
    links = {}
    for row in git(repo, 'ls-tree', '-r', '-z', sha).split(b'\0'):
        if not row:
            continue
        metadata, sep, name = row.partition(b'\t')
        fields = metadata.split()
        if not sep or len(fields) != 3:
            raise RuntimeError('malformed committed tree row')
        mode, kind, oid = fields
        if mode == b'160000':
            if kind != b'commit' or not re.fullmatch(rb'[0-9a-f]{40}', oid):
                raise RuntimeError('malformed committed gitlink')
            links[os.fsdecode(name)] = (mode, oid)
    return links


def tracked(repo, source, device, expected_links):
    count = 0
    observed_links = {}
    for row in git(repo, 'ls-files', '-s', '-z').split(b'\0'):
        if not row:
            continue
        metadata, sep, name = row.partition(b'\t')
        fields = metadata.split()
        if (not sep or len(fields) != 3 or fields[2] != b'0' or
                not re.fullmatch(rb'[0-9a-f]{40}', fields[1])):
            raise RuntimeError('malformed index row')
        name = os.fsdecode(name)
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise RuntimeError('unsafe tracked name')
        path, mode = repo / name, fields[0]
        safe_path(path.parent)
        if mode == b'160000':
            identity = (mode, fields[1])
            if expected_links.get(name) != identity:
                raise RuntimeError('unexpected or mismatched indexed gitlink')
            observed_links[name] = identity
            # The accepted clean conversion preserves empty directories for
            # optional gitlinks. They need no .git or nested checkout; only IHK
            # is materialized and independently checked by this packet.
            safe_path(path)
            info = path.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_dev != device:
                raise RuntimeError('gitlink directory type or placement differs')
            continue
        info = path.lstat()
        if info.st_dev != device:
            raise RuntimeError('tracked entry escaped scratch')
        if mode == b'120000':
            if not stat.S_ISLNK(info.st_mode):
                raise RuntimeError('tracked symlink changed type')
            continue
        if mode not in (b'100644', b'100755') or not stat.S_ISREG(info.st_mode):
            raise RuntimeError('tracked regular changed type')
        if bool(info.st_mode & 0o111) != (mode == b'100755'):
            raise RuntimeError('tracked executable mode differs')
        count += 1
        original = source / name
        if os.path.lexists(str(original)):
            other = original.lstat()
            if (info.st_dev, info.st_ino) == (other.st_dev, other.st_ino):
                raise RuntimeError('tracked inode shared with source')
    if observed_links != expected_links:
        raise RuntimeError('indexed gitlink set or mode differs from source commit')
    if not count:
        raise RuntimeError('empty tracked file set')
    return count


def observe(candidate, backup, source, scratch, main_sha, ihk_sha, phase,
            overlay_sha=None, result_sha=None, table=None, host_device=None):
    c, b, s, scratch = map(Path, (candidate, backup, source, scratch))
    device, filesystem = placement(scratch, (c, b), table, host_device)
    if c == b or c == s or c in s.parents or s in c.parents:
        raise RuntimeError('overlapping roots')
    for repo, sha in ((c, main_sha), (c / 'ihk', ihk_sha)):
        safe_path(repo)
        if git(repo, 'rev-parse', 'HEAD').strip().decode() != sha:
            raise RuntimeError('candidate HEAD mismatch')
    main_links = committed_gitlinks(s, main_sha)
    if (main_links.get('ihk') != (b'160000', ihk_sha.encode()) or
            committed_gitlinks(c, main_sha) != main_links):
        raise RuntimeError('committed gitlink mismatch')
    main_count = tracked(c, s, device, main_links)
    if git(c, 'status', '--porcelain=1', '--untracked-files=all', '--ignore-submodules=dirty', '-z'):
        raise RuntimeError('main candidate dirty')
    nested_status = git(c / 'ihk', 'status', '--porcelain=1', '--untracked-files=all', '-z')
    if phase == 'clean':
        if os.path.lexists(str(b)) or nested_status:
            raise RuntimeError('pre-conversion backup exists or IHK is dirty')
        backup_bytes = 0
    elif phase == 'overlay':
        if nested_status != (' M ' + OVERLAY_FILE + '\0').encode():
            raise RuntimeError('IHK overlay status mismatch')
        if hashlib.sha256(git(c / 'ihk', 'diff', '--binary')).hexdigest() != overlay_sha:
            raise RuntimeError('IHK overlay diff mismatch')
        if hashlib.sha256((c / 'ihk' / OVERLAY_FILE).read_bytes()).hexdigest() != result_sha:
            raise RuntimeError('IHK overlay result mismatch')
        if sorted(p.name for p in b.iterdir()) != ['ihk.git', 'main.git']:
            raise RuntimeError('metadata backup shape differs')
        for name, sha in (('main.git', main_sha), ('ihk.git', ihk_sha)):
            safe_path(b / name)
            if git(b / name, 'rev-parse', 'HEAD', metadata=True).strip().decode() != sha:
                raise RuntimeError('backup HEAD mismatch')
        backup_bytes = allocation(b, device)
    else:
        raise RuntimeError('invalid phase')
    ihk_count = tracked(c / 'ihk', s / 'ihk', device,
                        committed_gitlinks(c / 'ihk', ihk_sha))
    main_bytes = allocation(c, device, exclude=c / 'ihk')
    ihk_bytes = allocation(c / 'ihk', device)
    if table is None:
        placement(scratch, (c, b))
    return dict(status='PASS_PLACEMENT', phase=phase, filesystem=filesystem, device=device,
                main_tracked_files=main_count, ihk_tracked_files=ihk_count,
                main_gitlinks={name: {'mode': mode.decode(), 'object_id': oid.decode()}
                               for name, (mode, oid) in main_links.items()},
                main_allocated_bytes=main_bytes, ihk_allocated_bytes=ihk_bytes,
                backup_allocated_bytes=backup_bytes,
                candidate_allocated_bytes=main_bytes + ihk_bytes, memory_backed_bytes=0)


def self_test():
    assert mounts('1 0 1:1 / /a\\040b rw - ext4 /dev/x rw') == [(Path('/a b'), 'ext4')]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / 'x').write_bytes(b'payload')
        assert allocation(root, root.stat().st_dev) >= (root / 'x').stat().st_blocks * 512
    print('SELF_TEST PASS')


def main():
    parser = argparse.ArgumentParser()
    for name in ('candidate', 'backup', 'source', 'scratch'):
        parser.add_argument('--' + name, type=Path)
    for name in ('main-sha', 'ihk-sha', 'overlay-sha', 'result-sha'):
        parser.add_argument('--' + name)
    parser.add_argument('--phase', choices=('clean', 'overlay'))
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if None in (args.candidate, args.backup, args.source, args.scratch, args.main_sha, args.ihk_sha, args.phase):
        parser.error('all identity, placement and phase arguments are required')
    print(json.dumps(observe(args.candidate, args.backup, args.source, args.scratch,
                             args.main_sha, args.ihk_sha, args.phase,
                             args.overlay_sha, args.result_sha), sort_keys=True))


if __name__ == '__main__':
    main()
