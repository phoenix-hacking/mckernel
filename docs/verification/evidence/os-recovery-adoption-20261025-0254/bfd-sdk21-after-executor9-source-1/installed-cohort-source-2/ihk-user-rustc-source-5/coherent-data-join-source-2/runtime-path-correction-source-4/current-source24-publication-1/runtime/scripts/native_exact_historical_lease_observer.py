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
import uuid

ROOT = Path('/home/holden/mckernel-work/scratch')
EVIDENCE = Path('/home/holden/mckernel/docs/verification')
# Original retirement identities remain historical evidence, not mount authority.
HISTORICAL_BOOT = 'c733d83b-a5ae-4f91-9ce6-9f8ccf119afd'
HISTORICAL_DEVICE = 1831
# This single reviewed generation must refuse every later boot/remount until reviewed.
CURRENT_BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
CURRENT_DEVICE = 1828
FILESYSTEM_UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
BLOCK_DEVICE = Path('/dev/loop36')
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

def _directory(path):
    fds = []
    try:
        fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        fds.append(fd)
        chain = [_directory_identity(os.fstat(fd))]
        for part in path.parts[1:]:
            if part in ('.', '..'): raise Refusal('invalid directory path')
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            fds.append(fd)
            chain.append(_directory_identity(os.fstat(fd)))
        for parent in fds[:-1]: os.close(parent)
        return fd, chain
    except BaseException:
        for fd in reversed(fds): os.close(fd)
        raise

def _directory_identity(meta):
    return (meta.st_dev, meta.st_ino, meta.st_mode, meta.st_uid, meta.st_gid)

def _block_identity(meta):
    return (meta.st_dev, meta.st_ino, meta.st_rdev, meta.st_mode,
            meta.st_uid, meta.st_gid, meta.st_nlink)

class ScratchBinding:
    """Pin current mount and fixed backing block descriptor across all observations."""
    def __enter__(self):
        self.root_fd = self.block_parent = self.block_fd = None
        try:
            self.root_fd, self.root_chain = _directory(ROOT)
            self.root_identity = _directory_identity(os.fstat(self.root_fd))
            if self.root_identity != (CURRENT_DEVICE, 2, stat.S_IFDIR | 0o700, 1000, 1000):
                raise Refusal('current scratch root binding differs')
            self.block_parent, self.block_chain = _directory(BLOCK_DEVICE.parent)
            self.block_fd = os.open(BLOCK_DEVICE.name, os.O_RDONLY | os.O_NOFOLLOW |
                                    os.O_NONBLOCK | os.O_CLOEXEC | os.O_NOATIME, dir_fd=self.block_parent)
            meta = os.fstat(self.block_fd)
            if (not stat.S_ISBLK(meta.st_mode) or meta.st_rdev != CURRENT_DEVICE or
                    meta.st_uid != 0 or meta.st_nlink != 1):
                raise Refusal('current backing block binding differs')
            self.block_identity = _block_identity(meta)
            self.check()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def check(self):
        if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != CURRENT_BOOT:
            raise Refusal('current boot identity differs; fresh review required')
        if _directory_identity(os.fstat(self.root_fd)) != self.root_identity:
            raise Refusal('current scratch root identity changed')
        for path, expected in ((ROOT, self.root_chain), (BLOCK_DEVICE.parent, self.block_chain)):
            fd, chain = _directory(path)
            os.close(fd)
            if chain != expected: raise Refusal('current mount ancestry changed')
        if (_block_identity(os.fstat(self.block_fd)) != self.block_identity or
                _block_identity(os.stat(BLOCK_DEVICE.name, dir_fd=self.block_parent,
                                        follow_symlinks=False)) != self.block_identity):
            raise Refusal('current backing block identity changed')
        # ext4's primary superblock starts at byte 1024; only this fixed bounded
        # region is read. Its UUID authenticates the same rdev as scratch st_dev.
        data = os.pread(self.block_fd, 1024, 1024)
        if (len(data) != 1024 or data[0x38:0x3a] != b'\x53\xef' or
                str(uuid.UUID(bytes=data[0x68:0x78])) != FILESYSTEM_UUID):
            raise Refusal('current ext4 filesystem UUID proof differs')
        if (_block_identity(os.fstat(self.block_fd)) != self.block_identity or
                Path('/proc/sys/kernel/random/boot_id').read_text().strip() != CURRENT_BOOT):
            raise Refusal('current mount or boot changed during UUID read')

    def __exit__(self, *args):
        for name in ('block_fd', 'block_parent', 'root_fd'):
            fd = getattr(self, name, None)
            if fd is not None:
                os.close(fd)
                setattr(self, name, None)

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
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NOATIME | os.O_CLOEXEC, dir_fd=fd)
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
        if immutable and struct.unpack('I', fcntl.ioctl(fd, 0x80086601, struct.pack('I', 0)))[0] != flags:
            raise Refusal('immutable lease flags changed while observed')
        current = os.stat(path.name, dir_fd=fds[-2], follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino):
            raise Refusal('file pathname changed while observed')
        return data, before
    finally:
        for fd in reversed(fds): os.close(fd)

def observe():
    if os.geteuid() != 0: raise Refusal('privileged read-only observer required')
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != CURRENT_BOOT:
        raise Refusal('current boot identity differs; fresh review required')
    with ScratchBinding() as binding:
        result = _observe_leases()
        binding.check()
        return result

def _observe_leases():
    for relative, expected in EVIDENCE_BINDINGS.values():
        data, _ = _read(EVIDENCE / relative)
        if hashlib.sha256(data).hexdigest() != expected: raise Refusal('retirement evidence changed')
    rows = []
    for suffix, inode, size, expected, pid, start, evidence in LEASES:
        path = ROOT / ('native-exact-build-lease-' + suffix + '.json')
        data, meta = _read(path, immutable=True)
        if ((meta.st_dev, meta.st_ino, meta.st_size, meta.st_mode, meta.st_uid, meta.st_gid)
                != (CURRENT_DEVICE, inode, size, stat.S_IFREG | 0o600, 0, 0) or
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
    return {'schema': 'mckernel.historical-lease-observation.v1', 'boot_id': CURRENT_BOOT,
            'status': 'PASS_READ_ONLY', 'leases': rows,
            'authority': {'historical_boot_id': HISTORICAL_BOOT,
                          'historical_device': HISTORICAL_DEVICE,
                          'current_device': CURRENT_DEVICE, 'filesystem_uuid': FILESYSTEM_UUID,
                          'block_device': str(BLOCK_DEVICE),
                          'uuid_proof': 'ext4-primary-superblock-pread-1024-at-1024'}}

def main():
    import sys
    if len(sys.argv) != 1: raise Refusal('observer accepts no arguments')
    print(json.dumps(observe(), sort_keys=True))
    return 0

if __name__ == '__main__': raise SystemExit(main())
