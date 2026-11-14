#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only configure-probe verifier; caller must supply actual make status and
fresh, exclusively owned outputs. No Kbuild, subprocess or privileged operation.
"""
import argparse
import pathlib
import re
import struct
import sys

class ProbeError(ValueError):
    pass

def require(ok, why):
    if not ok:
        raise ProbeError(why)

def blob(path, maximum):
    p = pathlib.Path(path)
    require(p.is_file(), 'required probe input missing')
    require(p.stat().st_size <= maximum, 'probe input exceeds bound')
    data = p.read_bytes()
    require(len(data) <= maximum, 'probe input exceeds bound')
    return data

def section(data, entry, what):
    offset, size = entry[4], entry[5]
    require(offset <= len(data) and size <= len(data)-offset, what+' out of bounds')
    return data[offset:offset+size]

def cstring(data, offset):
    require(offset < len(data), 'symbol name offset out of bounds')
    end = data.find(b'\0', offset)
    require(end >= 0, 'unterminated symbol name')
    return data[offset:end]

def map_value(module):
    require(len(module) >= 64, 'truncated ELF header')
    ident = module[:16]
    require(ident[:4] == b'\x7fELF' and ident[4:7] == b'\x02\x01\x01', 'expected ELF64 little-endian version 1')
    e = struct.unpack_from('<HHIQQQIHHHHHH', module, 16)
    etype, machine, version, _, _, shoff, _, ehsize, _, _, shentsize, shnum, _ = e
    require((etype, machine, version, ehsize, shentsize) == (1, 62, 1, 64, 64), 'expected x86_64 relocatable ELF')
    require(0 < shnum <= 8192 and shoff <= len(module) and shnum * 64 <= len(module)-shoff, 'section table out of bounds')
    sections = [struct.unpack_from('<IIQQQQIIQQ', module, shoff + i*64) for i in range(shnum)]
    candidates = []
    for symtab in sections:
        if symtab[1] != 2:
            continue
        require(symtab[9] == 24 and symtab[5] % 24 == 0 and symtab[6] < shnum, 'invalid symbol table')
        strings = sections[symtab[6]]
        require(strings[1] == 3, 'symbol strings are not a string table')
        names = section(module, strings, 'string table')
        symbols = section(module, symtab, 'symbol table')
        for i in range(0, len(symbols), 24):
            name, info, _, index, value, size = struct.unpack_from('<IBBHQQ', symbols, i)
            if cstring(names, name) != b'MAP_KERNEL_START':
                continue
            candidates.append((info, index, value, size))
    require(len(candidates) == 1, 'expected exactly one MAP_KERNEL_START symbol')
    info, index, value, size = candidates[0]
    require(info >> 4 == 1 and info & 15 == 1 and 0 < index < shnum and size == 8, 'unexpected MAP_KERNEL_START symbol definition')
    target = sections[index]
    require(target[1] == 1 and target[2] & 3 == 3, 'MAP_KERNEL_START must be in writable allocated bytes')
    data = section(module, target, 'symbol section')
    require(value <= len(data) and 8 <= len(data)-value, 'MAP_KERNEL_START bytes out of bounds')
    return struct.unpack_from('<Q', data, value)[0]

def verify(make_status, module_path, release_path, uts_path, uname_r, expected):
    require(make_status == '0', 'Kbuild make did not succeed')
    require(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+[-A-Za-z0-9._+]*', uname_r) is not None, 'invalid explicit UNAME_R')
    require(re.fullmatch(r'0x[0-9a-fA-F]{16}', expected) is not None, 'expected map must be explicit 16-digit hexadecimal')
    release = blob(release_path, 4096).decode('ascii')
    uts = blob(uts_path, 4096).decode('ascii')
    require(release in (uname_r, uname_r + '\n'), 'kernel.release and explicit UNAME_R differ')
    matches = re.findall(r'^\s*#\s*define\s+UTS_RELEASE\s+"([^"\n]+)"\s*$', uts, re.M)
    require(matches == [uname_r], 'UTS_RELEASE and explicit UNAME_R differ')
    value = map_value(blob(module_path, 16 * 1024 * 1024))
    require(value == int(expected,16), 'MAP_KERNEL_START does not match expected value')
    return f'0x{value:016x}'

def main():
    a=argparse.ArgumentParser(description=__doc__)
    for name in ('make-status','module','kernel-release','uts-release-header','uname-r','expected-map'):
        a.add_argument('--'+name, required=True)
    x=a.parse_args()
    try:
        print(verify(x.make_status,x.module,x.kernel_release,x.uts_release_header,x.uname_r,x.expected_map))
    except (ProbeError, OSError, UnicodeError, struct.error) as error:
        print('configure probe rejected: '+str(error), file=sys.stderr)
        return 1
    return 0
if __name__=='__main__':
    raise SystemExit(main())
