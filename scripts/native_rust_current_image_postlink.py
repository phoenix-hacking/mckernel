#!/usr/bin/env python3
"""Diagnostic linked-image admission, never a runtime or ownership release.

Inputs are trusted build outputs, but accidental concurrent edits/replacements
are rejected. Open descriptors and revalidation are not a hostile-writer lock.
The executable's interpreter/shared libraries are environment prerequisites;
the explicitly selected binutils executables themselves are hash-bound here.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import struct
import subprocess
import sys
import time
import uuid

MAX_OUTPUT = 2 * 1024 * 1024
MAX_DISASSEMBLY = 64 * 1024 * 1024
MAX_INPUT = 512 * 1024 * 1024
TOOL_TIMEOUT = 30
ENV = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}
BASE = 0xfffffffffe800000
LIMIT = BASE + 8 * 1024 * 1024
NOTE_TYPE = 0x4d434b01
NOTE_NAME = b'MCKERNEL\0'
NOTE_DESC = struct.pack('<IIII', 4, 0x00060c00, 7616, 1)
EH = struct.Struct('<16sHHIQQQIHHHHHH')
PH = struct.Struct('<IIQQQQQQ')


def open_path(path, label, directory=False):
    """Walk every component without following symlinks, including parents."""
    p = Path(path)
    if not p.is_absolute() or '..' in p.parts or any(c.isspace() for c in str(p)):
        raise ValueError(f'{label} path must be absolute and unambiguous')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, part in enumerate(p.parts[1:]):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if directory or index < len(p.parts) - 2:
                flags |= os.O_DIRECTORY
            new = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = new
        return fd
    except BaseException:
        os.close(fd)
        raise


def identity(st):
    return st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def read_all(fd, size):
    parts = []
    offset = 0
    while offset < size:
        chunk = os.pread(fd, min(1024 * 1024, size - offset), offset)
        if not chunk:
            raise ValueError('input short read')
        parts.append(chunk)
        offset += len(chunk)
    return b''.join(parts)


class Snapshot:
    def __init__(self, path, label):
        self.path, self.label = Path(path), label
        self.fd = open_path(path, label)
        try:
            st = os.fstat(self.fd)
            if not stat.S_ISREG(st.st_mode):
                raise ValueError(f'{label} is not a regular file')
            if st.st_size > MAX_INPUT:
                raise ValueError(f'{label} exceeds input bound')
            self.before = identity(st)
            self.data = read_all(self.fd, st.st_size)
            self.digest = hashlib.sha256(self.data).hexdigest()
            self.verify()
        except BaseException:
            self.close()
            raise

    def verify(self):
        try:
            current = open_path(self.path, self.label)
        except OSError as exc:
            raise ValueError(f'{self.label} path changed during admission') from exc
        try:
            if identity(os.fstat(current)) != self.before or identity(os.fstat(self.fd)) != self.before:
                raise ValueError(f'{self.label} changed during admission')
            if read_all(self.fd, self.before[2]) != self.data:
                raise ValueError(f'{self.label} bytes changed during admission')
            if identity(os.fstat(self.fd)) != self.before:
                raise ValueError(f'{self.label} changed during admission')
        finally:
            os.close(current)

    def binding(self):
        return {'path': str(self.path), 'sha256': self.digest,
                'device': self.before[0], 'inode': self.before[1], 'bytes': self.before[2]}

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


def parse_elf(data):
    if len(data) < 64:
        raise ValueError('truncated ELF header')
    ident, typ, machine, version, entry, phoff, _, flags, ehsize, phentsz, phnum, *_ = EH.unpack_from(data)
    if ident[:7] != b'\x7fELF\x02\x01\x01' or typ != 2 or machine != 62 or version != 1 or flags != 0 or ehsize != 64 or phentsz != 56:
        raise ValueError('ELF version/flags/header mismatch')
    if not phnum or phnum > 64 or phoff < 64 or phoff + phnum * 56 > 4096 or phoff + phnum * 56 > len(data):
        raise ValueError('program headers exceed loader bounds')
    headers = [PH.unpack_from(data, phoff + i * 56) for i in range(phnum)]
    loads, notes = [], []
    for kind, fl, off, va, _, fs, ms, align in headers:
        if kind == 4:
            # Loader bounds the note length, not its location in the image.
            if fs > 4096 or off + fs > len(data):
                raise ValueError('note exceeds loader bounds')
            blob, pos = data[off:off + fs], 0
            while pos < len(blob):
                if len(blob) - pos < 12:
                    raise ValueError('malformed note tail')
                ns, ds, nt = struct.unpack_from('<III', blob, pos)
                pos += 12
                ne = pos + ns
                de = (ne + 3) & ~3
                dend = de + ds
                nxt = (dend + 3) & ~3
                if nxt > len(blob) or ne > len(blob):
                    raise ValueError('malformed note')
                if blob[pos:ne] == NOTE_NAME and nt == NOTE_TYPE:
                    notes.append(blob[de:dend])
                pos = nxt
            continue
        if kind in (0, 6, 0x6474e551, 0x6474e552):
            continue
        if kind != 1:
            raise ValueError('unsupported program header')
        if fl & ~7 or ms == 0 or fs > ms or off + fs > len(data):
            raise ValueError('invalid PT_LOAD')
        if align > 1 and (align & (align - 1) or va % align != off % align):
            raise ValueError('invalid PT_LOAD alignment')
        if va < BASE or va + ms > LIMIT:
            raise ValueError('PT_LOAD outside loader window')
        loads.append((va, va + ms, fs, fl))
    for a, b in zip(sorted(loads), sorted(loads)[1:]):
        if a[1] > b[0]:
            raise ValueError('overlapping PT_LOAD spans')
    if len(notes) != 1 or notes[0] != NOTE_DESC:
        raise ValueError('expected MCKERNEL boot note mismatch')
    if not any(a <= entry < a + fs and fl & 1 for a, _, fs, fl in loads):
        raise ValueError('entry outside executable file-backed PT_LOAD')
    return {'entry': entry, 'program_headers': phnum, 'pt_loads': len(loads),
            'note': list(struct.unpack('<IIII', notes[0]))}


def run_tool(snap, args, target, limit=MAX_OUTPUT):
    snap.verify()
    target.verify()
    argv = [f'/proc/self/fd/{snap.fd}', *args, f'/proc/self/fd/{target.fd}']
    out = {'stdout': bytearray(), 'stderr': bytearray()}
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         pass_fds=(snap.fd, target.fd), env=ENV, start_new_session=True)
    deadline = time.monotonic() + TOOL_TIMEOUT
    try:
        with selectors.DefaultSelector() as sel:
            for name in out:
                sel.register(getattr(p, name), selectors.EVENT_READ, name)
            while sel.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ValueError('tool timeout')
                for key, _ in sel.select(min(remaining, 0.1)):
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        sel.unregister(key.fileobj)
                        continue
                    if len(out[key.data]) + len(chunk) > limit:
                        raise ValueError(f'tool {key.data} output exceeds bound')
                    out[key.data].extend(chunk)
            try:
                status = p.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as exc:
                raise ValueError('tool timeout') from exc
            if status:
                raise ValueError(f'tool returned nonzero: {snap.path}: {status}')
    finally:
        # Kill the entire owned group even if its leader exited while a child
        # retained a pipe. Always reap our direct child on success and failure.
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.wait()
        p.stdout.close()
        p.stderr.close()
    snap.verify()
    target.verify()
    return {'stdout': bytes(out['stdout']).decode('utf-8', 'strict'),
            'stderr': bytes(out['stderr']).decode('utf-8', 'strict'),
            'argv': argv, 'environment': dict(ENV), 'executable': snap.binding(),
            'target': target.binding(), 'exit_status': status, 'limit_bytes': limit,
            'timeout_seconds': TOOL_TIMEOUT}


def check_disassembly(text):
    count = 0
    for line in text.splitlines():
        # --no-show-raw-insn makes instruction boundaries independent of widths.
        match = re.match(r'^\s*[0-9a-fA-F]+:\s+(.+)$', line)
        if not match:
            continue
        # GNU objdump's AT&T output puts symbolic annotations after '#'.
        # A referenced symbol named xmm0 is not a register operand.
        instruction = match.group(1).split('#', 1)[0]
        instruction = re.sub(r'<[^>]*>', '', instruction)
        words = instruction.lower().split()
        while words and (words[0] in ('lock', 'rep', 'repe', 'repz', 'repne', 'repnz',
                                      'data16', 'addr32', 'cs', 'ds', 'es', 'fs', 'gs', 'ss')
                         or words[0].startswith('rex')):
            words.pop(0)
        if not words or not re.fullmatch(r'[a-z][a-z0-9_.]*', words[0]):
            raise ValueError('Rust object disassembly has undecoded instruction')
        count += 1
        mnemonic, operands = words[0], ' '.join(words[1:])
        scalar_p = mnemonic.startswith(('push', 'pop', 'prefetch')) or mnemonic in ('pause', 'pext', 'pdep', 'ptwrite', 'ptwritel', 'ptwriteq', 'pconfig')
        if (mnemonic.startswith('f') or mnemonic.startswith('v') and mnemonic not in ('verr', 'verw')
                or mnemonic.startswith('p') and not scalar_p
                or mnemonic.startswith(('xsave', 'xrstor', 'ldmxcsr', 'stmxcsr', 'kadd', 'kand', 'kmov', 'knot', 'kor', 'kshift', 'ktest', 'kunpck', 'kxnor', 'kxor'))
                or mnemonic in ('emms', 'wait')
                or re.search(r'%(?:xmm|ymm|zmm|mm|k)[0-9]+\b|%st\b', operands)
                or re.search(r'\b(?:xmm|ymm|zmm|mm)[0-9]+\b', operands)):
            raise ValueError(f'Rust object contains forbidden vector/x87/MMX instruction: {mnemonic}')
    if not count:
        raise ValueError('Rust object disassembly has no instructions')
    return count


def check_relocations(text):
    # -rW traverses all relocation sections, including dynamic relocations
    # omitted by objdump -r. Require GNU readelf's explicit empty result;
    # empty, unrecognized or partially decoded output cannot prove absence.
    if text.strip() == 'There are no relocations in this file.':
        return
    if (re.search(r"Relocation section .+ contains [1-9][0-9]* entr", text)
            or re.search(r'^\s*[0-9a-fA-F]+\s+[0-9a-fA-F]+\s+R_', text, re.M)):
        raise ValueError('linked image has relocations')
    raise ValueError('unrecognized linked image relocation listing')


def output_evidence(result, abbreviated=False):
    result = dict(result)
    for stream in ('stdout', 'stderr'):
        raw = result[stream].encode('utf-8')
        result[stream + '_sha256'] = hashlib.sha256(raw).hexdigest()
        result[stream + '_bytes'] = len(raw)
        if abbreviated:
            result[stream] = result[stream][:4096]
            result[stream + '_truncated'] = len(raw) > 4096
    return result


def build_report(image, link_map, rust_object, source_commit, readelf, nm, objdump, output=None):
    with ExitStack() as stack:
        snaps = []
        for path, label in zip((image, link_map, rust_object, readelf, nm, objdump),
                               ('image', 'link map', 'Rust object', 'readelf', 'nm', 'objdump')):
            snap = Snapshot(path, label)
            stack.callback(snap.close)
            snaps.append(snap)
        def verify():
            for snap in snaps:
                snap.verify()
        if not re.fullmatch(r'[0-9a-fA-F]{40}', source_commit):
            raise ValueError('source commit must be 40 hex characters')
        elf = parse_elf(snaps[0].data)
        verify()
        ro = run_tool(snaps[3], ['-l', '-n'], snaps[0])
        allrel = run_tool(snaps[3], ['-rW'], snaps[0])
        check_relocations(allrel['stdout'])
        undefined = run_tool(snaps[4], ['-u'], snaps[0])
        # Query undefined symbols explicitly: weak w/v are undefined too,
        # whereas lowercase u in the full listing denotes GNU unique binding.
        if undefined['stdout'].strip():
            raise ValueError('linked image has unresolved symbols')
        no = run_tool(snaps[4], ['-an'], snaps[0])
        starts = re.findall(r'^\s*([0-9a-fA-F]+)\s+\w\s+arch_start\s*$', no['stdout'], re.M)
        if len(starts) != 1 or int(starts[0], 16) != elf['entry']:
            raise ValueError('nm arch_start does not match ELF entry')
        rel = run_tool(snaps[5], ['-r'], snaps[0])
        dis = run_tool(snaps[5], ['-d', '--no-show-raw-insn'], snaps[2], MAX_DISASSEMBLY)
        if re.search(r'(^|\n)\s*[0-9a-fA-F]+\s+\S+', rel['stdout']):
            raise ValueError('linked image has relocations')
        count = check_disassembly(dis['stdout'])
        verify()
        report = {'schema': 'mckernel-current-image-postlink-admission-v2',
                  'admission': 'diagnostic-only', 'runtime': False, 'application': False,
                  'production': False, 'source_commit': source_commit.lower(),
                  'image': snaps[0].binding(), 'link_map': snaps[1].binding(),
                  'rust_object': snaps[2].binding(), 'elf': elf,
                  'tools': {'readelf': snaps[3].binding(), 'nm': snaps[4].binding(),
                            'objdump': snaps[5].binding(), 'outputs': {
                                'readelf': output_evidence(ro), 'nm': output_evidence(no),
                                'all_relocations': output_evidence(allrel),
                                'undefined_symbols': output_evidence(undefined),
                                'relocations': output_evidence(rel),
                                'disassembly': output_evidence(dis, True)},
                            'disassembled_instructions': count},
                  'ownership': {'status': 'mandatory-outstanding',
                                'helper': 'scripts/mckernel_linked_text_ownership.py', 'claim': False}}
        verify()
        if output is not None:
            publish(output, report, verify)
        return report


def publish(path, report, verify=lambda: None):
    p = Path(path)
    if not p.is_absolute() or '..' in p.parts or any(c.isspace() for c in str(p)):
        raise ValueError('output must be absolute and unambiguous')
    dfd = open_path(p.parent, 'output parent', directory=True)
    parent_identity = identity(os.fstat(dfd))[:2]
    tmp = f'.{p.name}.tmp-{uuid.uuid4().hex}'
    fd, created = -1, False
    def parent_check():
        try:
            other = open_path(p.parent, 'output parent', directory=True)
        except OSError as exc:
            raise ValueError('output parent changed during publication') from exc
        try:
            if identity(os.fstat(other))[:2] != parent_identity:
                raise ValueError('output parent changed during publication')
        finally:
            os.close(other)
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644, dir_fd=dfd)
        created = True
        data = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode()
        pos = 0
        while pos < len(data):
            n = os.write(fd, data[pos:])
            if n <= 0:
                raise OSError('short report write')
            pos += n
        os.fsync(fd)
        os.close(fd)
        fd = -1
        verify()
        parent_check()
        os.link(tmp, p.name, src_dir_fd=dfd, dst_dir_fd=dfd, follow_symlinks=False)
        os.unlink(tmp, dir_fd=dfd)
        created = False
        # Failure here is reported as failure even though the complete final
        # file exists. Do not remove a possibly externally consumed report.
        try:
            os.fsync(dfd)
        except OSError as exc:
            raise OSError(f'report final file is complete but directory durability is unconfirmed: {exc}') from exc
        parent_check()
        verify()
    finally:
        if fd >= 0:
            os.close(fd)
        if created:
            os.unlink(tmp, dir_fd=dfd)
        os.close(dfd)


def main(argv=None):
    ap = argparse.ArgumentParser()
    for name in ('image', 'link-map', 'rust-object', 'source-commit', 'readelf', 'nm', 'objdump', 'output'):
        ap.add_argument('--' + name, required=True)
    a = ap.parse_args(argv)
    try:
        build_report(a.image, a.link_map, a.rust_object, a.source_commit,
                     a.readelf, a.nm, a.objdump, a.output)
    except (OSError, ValueError) as exc:
        print('error: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
