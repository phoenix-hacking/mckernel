#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Future source generation only. This program does not compile or execute a fixture.
Run solely in an admitted light-test profile with a fresh owned output directory.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import os
import stat

ROOT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
BASE = ROOT / 'f06-debug-constants-align32-host-1/src/kernel/rust/xpmem_helpers.rs'
ABI = ROOT / 'f06-debug-constants-align32-host-1/src/kernel/rust/abi.rs'
PATCHED = ROOT / 'attempt-0002/m14-xpmem-tg-publish-order-1/xpmem_helpers.rs'
EXPECTED = {BASE: 'e8c7970b672c724f14da2eb0a12fdbcd11df62f824422a5f8a98da4364328255',
            ABI: 'ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e',
            PATCHED: '8a88864073aec2d288297893da072bc26ba34773405bedb09f7c981a0c398892'}
EXPECTED_SIZES = {BASE: 236058, ABI: 76151, PATCHED: 236199}
TAIL_SIZE = 8750
MAX_BOUND_INPUT_SIZE = 236199

class CustodyError(RuntimeError):
    pass

def _id(st):
    return (st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode))

def _file_state(st):
    return (_id(st), st.st_mode, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns)

def _parts(path):
    p = Path(path)
    if not p.is_absolute() or '..' in p.parts:
        raise CustodyError('path must be absolute with no parent components')
    return p.parts[1:]

class PinnedDir:
    def __init__(self, path):
        self.parts = _parts(path)
        self.fds = []
        self.links = []
    def __enter__(self):
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        try:
            self.fds.append(os.open('/', flags))
            for name in self.parts:
                parent = self.fds[-1]
                fd = os.open(name, flags, dir_fd=parent)
                self.fds.append(fd)
                self.links.append((parent, name, fd))
                if _id(os.stat(name, dir_fd=parent, follow_symlinks=False)) != _id(os.fstat(fd)):
                    raise CustodyError('directory identity changed while opening')
            self.verify()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise
    @property
    def fd(self):
        return self.fds[-1]
    def verify(self):
        for parent, name, child in self.links:
            named = os.stat(name, dir_fd=parent, follow_symlinks=False)
            held = os.fstat(child)
            if not stat.S_ISDIR(named.st_mode) or _id(named) != _id(held):
                raise CustodyError('directory path replaced: ' + name)
    def __exit__(self, _a, _b, _c):
        for fd in reversed(self.fds):
            os.close(fd)
        self.fds.clear()
        self.links.clear()

def read_regular(path, expected_sha, expected_size):
    if type(expected_size) is not int or not 0 <= expected_size <= MAX_BOUND_INPUT_SIZE:
        raise CustodyError('invalid expected input size')
    path = Path(path)
    _parts(path)
    with PinnedDir(path.parent) as parent:
        parent.verify()
        fd = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent.fd)
        try:
            before = os.fstat(fd)
            named = os.stat(path.name, dir_fd=parent.fd, follow_symlinks=False)
            if not stat.S_ISREG(before.st_mode) or _file_state(named) != _file_state(before):
                raise CustodyError('input is not a stable named regular file')
            if before.st_size != expected_size:
                raise CustodyError('input size differs from bound size')
            chunks = []
            remaining = expected_size
            while remaining:
                chunk = os.read(fd, min(131072, remaining))
                if not chunk:
                    raise CustodyError('input ended before bound size')
                chunks.append(chunk)
                remaining -= len(chunk)
            # Detect growth without consuming more than one byte beyond the bound.
            if os.read(fd, 1):
                raise CustodyError('input grew beyond bound size')
            data = b''.join(chunks)
            after = os.fstat(fd)
            named_after = os.stat(path.name, dir_fd=parent.fd, follow_symlinks=False)
            parent.verify()
            if _file_state(before) != _file_state(after) or _file_state(after) != _file_state(named_after):
                raise CustodyError('input changed during read')
            if len(data) != expected_size or after.st_size != expected_size or hashlib.sha256(data).hexdigest() != expected_sha:
                raise CustodyError('input digest or size mismatch')
            return data
        finally:
            os.close(fd)

def create_exclusive(directory, name, data):
    if not name or '/' in name or name in ('.', '..'):
        raise CustodyError('output name must be one component')
    directory.verify()
    fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=directory.fd)
    try:
        initial = os.fstat(fd)
        named = os.stat(name, dir_fd=directory.fd, follow_symlinks=False)
        if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1 or _id(named) != _id(initial):
            raise CustodyError('fresh output inode mismatch')
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0: raise CustodyError('short output write')
            view = view[written:]
        verify_output(directory, name, fd, data)
        return fd
    except BaseException:
        os.close(fd)
        raise

def verify_output(directory, name, fd, expected):
    directory.verify()
    before = os.fstat(fd)
    named = os.stat(name, dir_fd=directory.fd, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or _file_state(named) != _file_state(before):
        raise CustodyError('output inode replaced or aliased')
    if before.st_size != len(expected):
        raise CustodyError('output size differs from expected')
    chunks = []
    offset = 0
    while offset < len(expected):
        chunk = os.pread(fd, min(131072, len(expected) - offset), offset)
        if not chunk:
            raise CustodyError('output ended before expected size')
        chunks.append(chunk)
        offset += len(chunk)
    if os.pread(fd, 1, offset):
        raise CustodyError('output grew beyond expected size')
    after = os.fstat(fd)
    named_after = os.stat(name, dir_fd=directory.fd, follow_symlinks=False)
    directory.verify()
    if _file_state(before) != _file_state(after) or _file_state(after) != _file_state(named_after):
        raise CustodyError('output changed during validation')
    if b''.join(chunks) != expected:
        raise CustodyError('output bytes mismatch')


def read_bound(path):
    return read_regular(path, EXPECTED[path], EXPECTED_SIZES[path]).decode('utf-8')

def one_line(source, pattern):
    matches = list(re.finditer(pattern, source, re.MULTILINE))
    if len(matches) != 1:
        raise RuntimeError('expected exactly one match: ' + pattern)
    return matches[0].group(0)

def braced(source, marker, attributes=False):
    if source.count(marker) != 1:
        raise RuntimeError('expected exactly one marker: ' + marker)
    pos = source.index(marker)
    start = source.rfind('#[repr(', 0, pos) if attributes else pos
    if start < 0:
        raise RuntimeError('missing repr: ' + marker)
    open_pos = source.index('{', pos)
    depth = 0
    for i in range(open_pos, len(source)):
        if source[i] == '{': depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0: return source[start:i + 1]
    raise RuntimeError('unclosed body: ' + marker)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path,
                        help='fresh existing private directory for generated sources')
    args = parser.parse_args()
    out = args.output
    original, patched, abi = read_bound(BASE), read_bound(PATCHED), read_bound(ABI)
    definition_markers = ['unsafe fn field_ptr<T>', 'fn ptr_is_err',
                          'pub extern "C" fn xpmem_tg_hashtable_index_result',
                          'pub struct XpmemOpenTgOffsets']
    defs = []
    for marker in definition_markers:
        old = braced(original, marker, marker.startswith('pub struct '))
        new = braced(patched, marker, marker.startswith('pub struct '))
        if old != new:
            raise RuntimeError('shared production definition differs: ' + marker)
        defs.append(old)
    for name in ('XpmemAllocFn', 'XpmemAtomicSetFn', 'XpmemTgRefFn', 'XpmemRwlockFn',
                 'XpmemObjectVoidFn', 'XpmemListAddTailFn'):
        pattern = r'^type ' + name + r' = [^\n]+;$'
        old = one_line(original, pattern)
        if old != one_line(patched, pattern): raise RuntimeError('callback ABI differs: ' + name)
        defs.append(old)
    for name in ('EINVAL', 'ENOMEM', 'XPMEM_AP_HASHTABLE_SIZE', 'XPMEM_TG_HASHTABLE_SIZE'):
        pattern = r'^const ' + name + r': [^\n]+;$'
        old = one_line(original, pattern)
        if old != one_line(patched, pattern): raise RuntimeError('constant differs: ' + name)
        defs.append(old)
    for name in ('CInt', 'SizeT'):
        defs.append(one_line(abi, r'^pub type ' + name + r' = [^\n]+;$'))
    for name in ('AbiListHead', 'IhkAtomic', 'IhkSpinlock', 'McsRwlockLock',
                 'XpmemHashlist', 'XpmemThreadGroupPrefix', 'XpmemPartitionPrefix'):
        defs.append(braced(abi, 'pub struct ' + name + ' {', True))
    marker = 'pub unsafe extern "C" fn xpmem_open_tg_body_result('
    bodies = [braced(original, marker), braced(patched, marker)]
    if bodies[0] == bodies[1]: raise RuntimeError('original and candidate bodies unexpectedly equal')
    harness_path = Path(__file__).absolute().parent / 'fixture-tail.rs'
    harness_bytes = read_regular(harness_path, '7d0ae66207d453e452c03c6bc789b6880042db6530264d304a695c51e82dc9a2', TAIL_SIZE)
    harness_sha = hashlib.sha256(harness_bytes).hexdigest()
    if harness_sha != '7d0ae66207d453e452c03c6bc789b6880042db6530264d304a695c51e82dc9a2':
        raise RuntimeError('fixture-tail digest mismatch')
    harness = harness_bytes.decode('utf-8')
    source = ('#![allow(dead_code)]\nuse std::ffi::c_void;\nuse std::ptr::write_bytes;\n'
              + '#[repr(C)] pub struct Thread { _opaque: [u8; 0] }\n'
              + '#[repr(C)] pub struct ProcessVm { _opaque: [u8; 0] }\n'
              + '\n\n'.join(defs) + '\nmod original { use super::*;\n' + bodies[0] + '\n}\n'
              + 'mod patched { use super::*;\n' + bodies[1] + '\n}\n' + harness)
    bindings = {'sources': {str(k): {'sha256': v, 'size': EXPECTED_SIZES[k]} for k, v in EXPECTED.items()},
                'original_body_sha256': hashlib.sha256(bodies[0].encode()).hexdigest(),
                'patched_body_sha256': hashlib.sha256(bodies[1].encode()).hexdigest(),
                'generated_source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'fixture_tail_sha256': harness_sha,
                'fixture_tail_size': TAIL_SIZE,
                'scope': 'actual body; mocked providers; no kernel lifetime or runtime claim'}
    source_bytes = source.encode('utf-8')
    binding_bytes = (json.dumps(bindings, indent=2) + '\n').encode('utf-8')
    with PinnedDir(out) as directory:
        held = []
        try:
            held.append(('fixture.rs', create_exclusive(directory, 'fixture.rs', source_bytes), source_bytes))
            held.append(('BODY-BINDINGS.json', create_exclusive(directory, 'BODY-BINDINGS.json', binding_bytes), binding_bytes))
            for name, fd, data in held:
                verify_output(directory, name, fd, data)
            directory.verify()
        finally:
            for _, fd, _ in held:
                os.close(fd)

if __name__ == '__main__': main()
