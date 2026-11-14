#!/usr/bin/env python3
"""Fail-closed archival of an accidental synthetic scratch18 v1 transaction.

This is deliberately separate from the real cleanup helper.  It only archives
the two fixed, byte-bound transaction records; it never interprets them as a
live cleanup request.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import stat

ROOT = Path('/home/holden/mckernel-work/scratch')
DEVICE = 1831
UID = GID = 1000
PLAN = ROOT / 'native-exact-scratch18-interrupt-cleanup.plan.json'
JOURNAL = ROOT / 'native-exact-scratch18-interrupt-cleanup.journal.jsonl'
PLAN_ARCHIVE = ROOT / 'native-exact-scratch18-interrupt-cleanup.plan.json.synthetic-v1.archive'
JOURNAL_ARCHIVE = ROOT / 'native-exact-scratch18-interrupt-cleanup.journal.jsonl.synthetic-v1.archive'
PLAN_SENTINEL = ROOT / 'native-exact-scratch18-interrupt-cleanup.plan.json.synthetic-v1.sentinel'
JOURNAL_SENTINEL = ROOT / 'native-exact-scratch18-interrupt-cleanup.journal.jsonl.synthetic-v1.sentinel'
PLAN_RECORD = ('b12ca96f9464f5488a243d7de4ea1ecf0132efccf911ddc52a0807c9b9274c88', 90737, 169)
JOURNAL_RECORD = ('b1eb871a3b2fc6beba2af00500e15df7fb4f4191b228800eeb819f6a3e7c94cb', 90738, 1251)
ARCHIVES = ((PLAN, PLAN_ARCHIVE, PLAN_RECORD), (JOURNAL, JOURNAL_ARCHIVE, JOURNAL_RECORD))
TMP_RECORDS = ('/tmp/tmp8aj5goke/attempt', '/tmp/tmp8aj5goke/lease', '/tmp/tmp8aj5goke/shared')
EVENTS = (
    ('before', 0, '', '6f0a8f7654ccbacbc1f6e6ee0951356e2534dd0e76587cd76c27cc0fe90c682f'),
    ('after', 0, '6f0a8f7654ccbacbc1f6e6ee0951356e2534dd0e76587cd76c27cc0fe90c682f', 'be31420e038e64600b94a9b9454f002985f52260cf0d502a99531586a10b0738'),
    ('before', 1, 'be31420e038e64600b94a9b9454f002985f52260cf0d502a99531586a10b0738', 'b13ca730078081b7fb09fcbbec2c516a25356e7bfab3360f73d22e6c0b767a2c'),
    ('after', 1, 'b13ca730078081b7fb09fcbbec2c516a25356e7bfab3360f73d22e6c0b767a2c', 'e19b716fd233248c22539a184622be6ad77d3247b66c63301fc13bece7138bd2'),
    ('before', 2, 'e19b716fd233248c22539a184622be6ad77d3247b66c63301fc13bece7138bd2', '03e05296c84ae7beeebe8ddb087b95e24c481fdaefbac1a32bfd206bc8c7c934'),
    ('after', 2, '03e05296c84ae7beeebe8ddb087b95e24c481fdaefbac1a32bfd206bc8c7c934', '205c8b0be894ea584ff4813782bb1b1a90b710675257adb154026b1d7ce86a92'),
    ('complete', 3, '205c8b0be894ea584ff4813782bb1b1a90b710675257adb154026b1d7ce86a92', '6344d13cd963d373afeb745266ccb0a8069ae51cddacd7cbcd5ab223d669a79b'),
)

class Refusal(ValueError):
    pass

def digest(data):
    return hashlib.sha256(data).hexdigest()

def _open_root():
    if not ROOT.is_absolute() or '..' in ROOT.parts:
        raise Refusal('noncanonical-root')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in ROOT.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
    except BaseException:
        os.close(fd); raise
    st = os.fstat(fd)
    if st.st_dev != DEVICE or stat.S_IMODE(st.st_mode) != 0o700 or (st.st_uid, st.st_gid) != (UID, GID):
        os.close(fd); raise Refusal('root-binding')
    return fd

def _read(fd, path, expected):
    name = path.name
    f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=fd)
    try:
        before = os.fstat(f)
        if (not stat.S_ISREG(before.st_mode) or before.st_dev != DEVICE or before.st_ino != expected[1] or
            before.st_size != expected[2] or before.st_nlink != 1 or stat.S_IMODE(before.st_mode) != 0o600 or
            (before.st_uid, before.st_gid) != (UID, GID)):
            raise Refusal('record-identity:' + name)
        data = os.read(f, expected[2] + 1)
        after = os.fstat(f)
        # Reading may advance atime (including after an exchange changes ctime
        # and makes relatime eligible). Bind every mutation-sensitive field,
        # including nanosecond mtime/ctime, to the snapshot taken AFTER rename.
        # Only access time is excluded; content still has its exact byte hash.
        stable = lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_uid,
                             st.st_gid, st.st_nlink, st.st_size,
                             st.st_mtime_ns, st.st_ctime_ns)
        if len(data) != expected[2] or digest(data) != expected[0] or stable(before) != stable(after):
            raise Refusal('record-mutated:' + name)
        return data
    finally:
        os.close(f)

def _validate_tmp_ancestry():
    rootfd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        tmpfd = os.open('tmp', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=rootfd)
        try:
            st = os.fstat(tmpfd)
            if not stat.S_ISDIR(st.st_mode) or (st.st_uid, st.st_gid) != (0, 0) or stat.S_IMODE(st.st_mode) != 0o1777:
                raise Refusal('tmp-ancestry')
            try:
                os.stat('tmp8aj5goke', dir_fd=tmpfd, follow_symlinks=False)
            except FileNotFoundError:
                return
            raise Refusal('synthetic-source-present')
        finally:
            os.close(tmpfd)
    finally:
        os.close(rootfd)

def _validate_contents(plan, journal):
    try:
        obj = json.loads(plan.decode('utf-8'))
    except (ValueError, UnicodeError) as exc:
        raise Refusal('plan-json') from exc
    if obj != {'device': 66306, 'records': list(TMP_RECORDS), 'schema': 'native-exact-scratch18-interrupt-cleanup-v1'}:
        raise Refusal('synthetic-plan-binding')
    _validate_tmp_ancestry()
    rows = []
    for line in journal.splitlines():
        try: row = json.loads(line.decode('utf-8'))
        except (ValueError, UnicodeError) as exc: raise Refusal('journal-json') from exc
        if set(row) != {'event','hash','index','previous'}: raise Refusal('journal-fields')
        rows.append(row)
    if len(rows) != len(EVENTS): raise Refusal('journal-length')
    for row, expected in zip(rows, EVENTS):
        if (row.get('event'), row.get('index'), row.get('previous'), row.get('hash')) != expected:
            raise Refusal('journal-chain')

def _rename_noreplace(fd, source, destination):
    libc = ctypes.CDLL(None, use_errno=True)
    fn = getattr(libc, 'renameat2', None)
    if fn is None: raise Refusal('renameat2-unavailable')
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    fn.restype = ctypes.c_int
    if fn(fd, os.fsencode(source), fd, os.fsencode(destination), 1):
        error = ctypes.get_errno(); raise OSError(error, os.strerror(error))

def _exchange(fd, left, right):
    libc = ctypes.CDLL(None, use_errno=True); fn = getattr(libc, 'renameat2', None)
    if fn is None: raise Refusal('renameat2-unavailable')
    fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    fn.restype = ctypes.c_int
    if fn(fd, os.fsencode(left), fd, os.fsencode(right), 2):
        error = ctypes.get_errno(); raise OSError(error, os.strerror(error))

def _stat(fd, path):
    try:
        return os.stat(path.name, dir_fd=fd, follow_symlinks=False)
    except FileNotFoundError:
        return None

def _marker(fd, path):
    """Return an open, empty owned marker; caller owns its descriptor.

    Original immutable records do not bind marker inodes across invocations.
    On resume we adopt only this narrowly checked shape, then retain the opened
    inode through every rename. No directory or foreign object is ever deleted.
    """
    marker = os.open(path.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    try:
        st = os.fstat(marker)
        if (st.st_dev != DEVICE or stat.S_IMODE(st.st_mode) != 0o700 or
            (st.st_uid, st.st_gid) != (UID, GID) or st.st_nlink != 2 or os.listdir(marker)):
            raise Refusal('sentinel-identity:' + path.name)
        _same(fd, path, marker)
        return marker
    except BaseException:
        os.close(marker); raise

def _same(fd, path, marker):
    observed, expected = _stat(fd, path), os.fstat(marker)
    if observed is None or (observed.st_dev, observed.st_ino, observed.st_mode) != (expected.st_dev, expected.st_ino, expected.st_mode):
        raise Refusal('sentinel-replaced:' + path.name)

def _retained(sentinel):
    return sentinel.with_name(sentinel.name + '.archive')

def _state(fd, source, archive, sentinel, expected):
    retained = _retained(sentinel)
    entries = [_stat(fd, p) for p in (source, sentinel, archive, retained)]
    shape = tuple('absent' if st is None else 'dir' if stat.S_ISDIR(st.st_mode)
                  else 'file' if stat.S_ISREG(st.st_mode) else 'other' for st in entries)
    shapes = (
        ('file', 'absent', 'absent', 'absent'),
        ('file', 'dir', 'absent', 'absent'),
        ('dir', 'file', 'absent', 'absent'),
        ('dir', 'absent', 'file', 'absent'),
        ('absent', 'absent', 'file', 'dir'),
    )
    if shape not in shapes:
        raise Refusal('illegal-record-state:' + source.name)
    stage = shapes.index(shape)
    data = _read(fd, (source, source, sentinel, archive, archive)[stage], expected)
    if stage:
        marker = _marker(fd, (None, sentinel, source, source, retained)[stage])
        os.close(marker)
    return stage, data

def _states(fd):
    records = ((PLAN, PLAN_ARCHIVE, PLAN_SENTINEL, PLAN_RECORD),
               (JOURNAL, JOURNAL_ARCHIVE, JOURNAL_SENTINEL, JOURNAL_RECORD))
    states = [_state(fd, *record) for record in records]
    # Plan must be completely retained before any journal mutation.
    if states[0][0] != 4 and states[1][0] != 0:
        raise Refusal('out-of-order-prefix')
    _validate_contents(states[0][1], states[1][1])
    return records, states

def _sentinel_capture(fd, source, archive, sentinel, expected):
    stage, _ = _state(fd, source, archive, sentinel, expected)
    if stage == 4:
        return
    if stage == 0:
        os.mkdir(sentinel.name, 0o700, dir_fd=fd)
        os.fsync(fd)
        stage = 1
    marker = _marker(fd, sentinel if stage == 1 else source)
    try:
        if stage == 1:
            _same(fd, sentinel, marker)
            _exchange(fd, source.name, sentinel.name)
            os.fsync(fd)
            _same(fd, source, marker)
            stage = 2
        if stage == 2:
            # Replacements captured by exchange stay at sentinel on refusal.
            _read(fd, sentinel, expected)
            _rename_noreplace(fd, sentinel.name, archive.name)
            os.fsync(fd)
            _read(fd, archive, expected)
        _same(fd, source, marker)
        _rename_noreplace(fd, source.name, _retained(sentinel).name)
        os.fsync(fd)
        _same(fd, _retained(sentinel), marker)
    finally:
        os.close(marker)

def validate():
    return recover(False)

def recover(execute=False):
    fd = _open_root()
    try:
        records, states = _states(fd)
        terminal = all(stage == 4 for stage, _ in states)
        if not execute:
            return {'status': 'PASS_VALIDATE_ONLY', 'terminal': terminal}
        if terminal:
            return {'status': 'PASS_TERMINAL_REPLAY', 'terminal': True}
        for record in records:
            _sentinel_capture(fd, *record)
        _, final = _states(fd)
        if not all(stage == 4 for stage, _ in final):
            raise Refusal('incomplete')
        return {'status': 'PASS_EXECUTED', 'terminal': True}
    finally:
        os.close(fd)

def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--execute', action='store_true')
    try: print(json.dumps(recover(parser.parse_args().execute), sort_keys=True))
    except (Refusal, OSError) as exc: parser.exit(1, 'REFUSED: ' + str(exc) + '\n')

if __name__ == '__main__': main()
