#!/usr/bin/env python3
"""Bounded read-only observer for seven immutable historical build leases.

Source-only: privileged execution needs an independent release. No mutation,
arbitrary pathname, external command, credential access, or lease retirement.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

ROOT = Path('/home/holden/mckernel-work/scratch')
EVIDENCE = Path('/home/holden/mckernel/docs/verification')
BOOT = 'c733d83b-a5ae-4f91-9ce6-9f8ccf119afd'
EVIDENCE_BINDINGS = {
 '675': ('stability-native-exact-retirement-runtime-success-20260929-1.json', 'cdb1eabf257940fbfd91e86accde5bbab342e47b2568261462ed9da06b9f842c'),
 '704': ('stability-native-exact-retirement-704f6654-failure-20260929-1.json', '1e63a02eb9b29f1ec3ec0a4142543ca523720e19c0676f6a30048c3f1b34d7e0'),
 '76': ('evidence/stability-native-exact-candidate-retirement-postflight-76ae20b5-1.release.json', 'aba167b8ac6cf3167e6946f30197c079e2d6df534ebb28c06f2c75934096522d'),
 'f5': ('evidence/stability-native-exact-candidate-retirement-success-5386f60c-20260929-1.json', '7af1a1575f3c584c16fd3d8cc8e7f5a9d6de2f52e3509f3e4e3ed1d633b1766f'),
}
# name suffix, inode, bytes, SHA256, PID, starttime, retained evidence key.
LEASES = (
 ('67589154-1', 31470, 426, 'ac3d18953da2871ae6e9702143ba05a98abbb3412d512cc65eaa480517772f34', 3871619, '89921507', '675'),
 ('704f6654-1', 31474, 426, '482bdf30e7320693c338832695932fdf1be261ed081de225e4cbdaf7e4c2c123', 3912447, '90493097', '704'),
 ('76ae20b5-1', 31509, 426, 'a68867c85058eac82013575427851b4cc2ec38b310e8572e399fa5107166d8a2', 4194054, '93880605', '76'),
 ('76ae20b5-disk-1', 31510, 431, 'b25bd68e9b03249c57b8538e7192ef01b1acc6e0f686c81b79f55076efff31dd', 4194054, '93880605', '76'),
 ('76ae20b5-disk-retirement-1', 31512, 442, '4716843b04b58a4c8004ab4381197b9a78ba2179fdeb11f1a63b52dda3ea4b9f', 4194054, '93880605', '76'),
 ('76ae20b5-disk-validation-2', 31511, 442, '027b4db20d377c5b9f7e7c0eb999452e40fa3ef110e191db68713efcdaf83e88', 4194054, '93880605', '76'),
 ('f5d8d914-1', 31487, 426, '30477fdce5425bb6e1a76b801e21542062eb99d8c7ec6d7333f8b31dda3e29e5', 4061014, '92686869', 'f5'),
)

class Refusal(ValueError): pass

def _read(path, immutable=False):
    """Descriptor-relative NOFOLLOW, NOATIME bounded stable regular read."""
    path = Path(path)
    fds = []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fds.append(fd)
        for part in path.parts[1:-1]:
            if part in ('.', '..'): raise Refusal('invalid path')
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            fds.append(fd)
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME, dir_fd=fd)
        fds.append(fd)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 1 << 20:
            raise Refusal('unbounded or nonunique file')
        if immutable:
            flags = struct.unpack('I', fcntl.ioctl(fd, 0x80086601, struct.pack('I', 0)))[0]
            if not flags & 0x10: raise Refusal('lease is not immutable')
        data = b''
        while len(data) <= before.st_size:
            block = os.read(fd, min(65536, before.st_size + 1 - len(data)))
            if not block: break
            data += block
        after = os.fstat(fd)
        if before != after or len(data) != before.st_size:
            raise Refusal('file changed while observed')
        return data, before
    finally:
        for fd in reversed(fds): os.close(fd)

def observe():
    if os.geteuid() != 0: raise Refusal('privileged read-only observer required')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != BOOT:
        raise Refusal('retained boot identity differs; fresh review required')
    for relative, expected in EVIDENCE_BINDINGS.values():
        data, _ = _read(EVIDENCE / relative)
        if hashlib.sha256(data).hexdigest() != expected: raise Refusal('retirement evidence changed')
    rows = []
    for suffix, inode, size, expected, pid, start, evidence in LEASES:
        path = ROOT / ('native-exact-build-lease-' + suffix + '.json')
        data, meta = _read(path, immutable=True)
        if ((meta.st_dev, meta.st_ino, meta.st_size, meta.st_mode, meta.st_uid, meta.st_gid)
                != (1831, inode, size, stat.S_IFREG | 0o600, 0, 0) or
                hashlib.sha256(data).hexdigest() != expected):
            raise Refusal('historical lease binding changed')
        # The exact retained bytes bind the tombstone schema, state, owner and
        # release. Never accept self-declared retired:true from an unknown file.
        try:
            current = Path('/proc').joinpath(str(pid), 'stat').read_text()
        except FileNotFoundError:
            current = None
        if current is not None and current.rsplit(')', 1)[1].split()[19] == start:
            raise Refusal('historical owner is live')
        rows.append({'path': str(path), 'sha256': expected, 'device': meta.st_dev,
                     'inode': inode, 'size': size, 'pid': pid, 'starttime': start,
                     'evidence_sha256': EVIDENCE_BINDINGS[evidence][1]})
    return {'schema': 'mckernel.historical-lease-observation.v1', 'boot_id': BOOT,
            'status': 'PASS_READ_ONLY', 'leases': rows}

def main():
    import sys
    if len(sys.argv) != 1: raise Refusal('observer accepts no arguments')
    print(json.dumps(observe(), sort_keys=True))
    return 0

if __name__ == '__main__': raise SystemExit(main())
