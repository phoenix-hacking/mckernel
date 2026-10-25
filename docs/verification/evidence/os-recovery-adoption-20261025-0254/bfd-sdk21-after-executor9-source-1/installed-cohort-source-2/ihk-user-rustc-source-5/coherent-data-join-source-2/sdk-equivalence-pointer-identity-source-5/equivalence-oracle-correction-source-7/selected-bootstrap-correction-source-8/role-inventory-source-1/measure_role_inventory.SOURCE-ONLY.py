"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only replacement for the existing measure() inner inventory; no controller.
"""
import hashlib
import json
import os
from pathlib import Path
import stat


def role_inventory(root, role, source_relative=None, complete=False):
    """No-follow finite walk; return source/generated logical and allocated totals.

    Partial clone creation may expose only a subset of declared paths/sizes.
    A completed clone must match the full source set and every file digest.
    No invariant is cached between polls; aliases never extend traversal.
    """
    root = Path(root)
    if not root.exists():
        return dict(source_entries=0, generated_entries=0, logical_bytes=0, allocated_bytes=0)
    base = root.lstat()
    if not stat.S_ISDIR(base.st_mode):
        raise ValueError('role root is not a directory')
    expected = role['rows'] if source_relative is not None else {}
    counts = dict(source_entries=0, generated_entries=0, logical_bytes=0, allocated_bytes=0)
    seen = set()
    pending = [(root, '')]
    while pending:
        path, relative = pending.pop()
        meta = path.lstat()
        if (meta.st_dev, meta.st_uid, meta.st_gid) != (base.st_dev, base.st_uid, base.st_gid):
            raise ValueError('role device/ownership changed')
        is_source = source_relative is not None and (relative == source_relative or relative.startswith(source_relative+'/'))
        pin = None
        if is_source:
            name = relative[len(source_relative):].lstrip('/')
            if name not in expected:
                raise ValueError('undeclared source entry')
            pin = expected[name]
            if complete and stat.S_IMODE(meta.st_mode) != pin['mode']:
                raise ValueError('source mode changed')
            seen.add(name)
            counts['source_entries'] += 1
            if counts['source_entries'] > role['source_entry_limit']:
                raise ValueError('source entry bound')
        elif relative:
            counts['generated_entries'] += 1
            if counts['generated_entries'] > role['generated_entry_limit']:
                raise ValueError('generated entry bound')
        counts['allocated_bytes'] += meta.st_blocks * 512
        if counts['allocated_bytes'] > role['allocated_limit']:
            raise ValueError('allocated byte bound')
        if stat.S_ISLNK(meta.st_mode):
            if pin is None or pin['type'] != 'symlink' or os.readlink(path) != pin['target']:
                raise ValueError('undeclared or changed alias')
            source_root = root/source_relative
            # strict=False permits a declared target not copied yet; complete
            # requires the exact inventoried destination to exist and type-match.
            resolved = path.resolve(strict=complete)
            if resolved != source_root/pin['resolved']:
                raise ValueError('alias target changed or escaped')
            if complete:
                target_mode = resolved.stat().st_mode
                if (pin['target_type'] == 'file') != stat.S_ISREG(target_mode):
                    raise ValueError('alias target type changed')
                if pin['target_type'] == 'directory' and not stat.S_ISDIR(target_mode):
                    raise ValueError('alias directory target type changed')
            counts['logical_bytes'] += meta.st_size
        elif stat.S_ISDIR(meta.st_mode):
            if pin is not None and pin['type'] != 'directory':
                raise ValueError('source directory type changed')
            with os.scandir(path) as entries:
                for child in entries:
                    child_relative = relative+'/'+child.name if relative else child.name
                    pending.append((Path(child.path), child_relative))
                    if len(pending) > role['source_entry_limit'] + role['generated_entry_limit'] + 1:
                        raise ValueError('bounded traversal queue')
        elif stat.S_ISREG(meta.st_mode):
            if meta.st_nlink != 1:
                raise ValueError('unexpected output hardlink')
            if pin is not None:
                if pin['type'] != 'file' or meta.st_size > pin['size'] or (complete and meta.st_size != pin['size']):
                    raise ValueError('source file type/size changed')
                if complete:
                    value = hashlib.sha256()
                    descriptor = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW)
                    with os.fdopen(descriptor, 'rb') as stream:
                        before = os.fstat(stream.fileno())
                        if (before.st_dev, before.st_ino) != (meta.st_dev, meta.st_ino):
                            raise ValueError('source file identity changed')
                        for block in iter(lambda: stream.read(1<<20), b''):
                            value.update(block)
                        after = os.fstat(stream.fileno())
                        fields = ('st_dev','st_ino','st_mode','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns','st_blocks','st_nlink')
                        if any(getattr(before, key) != getattr(after, key) for key in fields):
                            raise ValueError('source file changed during hash')
                    if value.hexdigest() != pin['sha256']:
                        raise ValueError('source file hash changed')
            counts['logical_bytes'] += meta.st_size
        else:
            raise ValueError('special output file')
        if counts['logical_bytes'] > role['logical_limit']:
            raise ValueError('logical byte bound')
    if complete and seen != set(expected):
        raise ValueError('completed source closure incomplete')
    after = root.lstat()
    if (after.st_dev, after.st_ino, after.st_uid, after.st_gid) != (base.st_dev, base.st_ino, base.st_uid, base.st_gid):
        raise ValueError('role root identity changed')
    return counts
