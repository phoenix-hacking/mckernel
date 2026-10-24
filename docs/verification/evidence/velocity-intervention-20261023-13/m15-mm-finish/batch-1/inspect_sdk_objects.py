#!/usr/bin/env python3
"""Read actual inert pinned-SDK objects; no compilation or child execution.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This narrow checker is additional evidence, never a replacement for objtool,
independent source/codegen review, actual module links or native observations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


class Elf:
    def __init__(self, path):
        self.path = Path(path)
        self.raw = self.path.read_bytes()
        if self.raw[:6] != b'\x7fELF\x02\x01':
            raise ValueError('expected ELF64 little-endian: ' + str(path))
        header = struct.unpack_from('<16sHHIQQQIHHHHHH', self.raw)
        if header[1:3] != (1, 62):
            raise ValueError('expected inert ET_REL/EM_X86_64 object')
        self.sections = [struct.unpack_from('<IIQQQQIIQQ', self.raw,
                         header[6] + i * header[11]) for i in range(header[12])]
        names = self.payload(header[13])
        self.names = [self.string(names, section[0]) for section in self.sections]

    @staticmethod
    def string(data, offset):
        return data[offset:data.index(0, offset)].decode()

    def payload(self, index):
        section = self.sections[index]
        return self.raw[section[4]:section[4] + section[5]]

    def symbols(self, index):
        section = self.sections[index]
        names = self.payload(section[6])
        result = []
        for at in range(0, section[5], section[9]):
            name, info, other, target, value, size = struct.unpack_from(
                '<IBBHQQ', self.payload(index), at)
            result.append(dict(name=self.string(names, name), section=target,
                               value=value, size=size, info=info))
        return result

    def symbol_bytes(self, name):
        matches = []
        for index, section in enumerate(self.sections):
            if section[1] == 2:
                matches.extend(symbol for symbol in self.symbols(index)
                               if symbol['name'] == name and symbol['section'])
        if len(matches) != 1:
            raise ValueError('expected unique defined symbol: ' + name)
        symbol = matches[0]
        return self.payload(symbol['section'])[
            symbol['value']:symbol['value'] + symbol['size']]

    def relocations(self, target_name):
        target = self.names.index(target_name)
        result = []
        for index, section in enumerate(self.sections):
            if section[1] != 4 or section[7] != target:
                continue
            symbols = self.symbols(section[6])
            for at in range(0, section[5], section[9]):
                offset, info, addend = struct.unpack_from('<QQq', self.payload(index), at)
                result.append(dict(offset=offset, type=info & 0xffffffff,
                                   symbol=symbols[info >> 32], addend=addend))
        return result

    def relocation_target(self, relocation):
        symbol = relocation['symbol']
        if not 0 < symbol['section'] < len(self.sections):
            raise ValueError('relocation needs a defined ordinary section')
        return (symbol['section'], symbol['value'] + relocation['addend'])

    def annotation_target(self, section_name, expected_type):
        index = self.names.index(section_name)
        data = self.payload(index)
        if len(data) != 8 or struct.unpack_from('<I', data, 4)[0] != expected_type:
            raise ValueError('wrong singleton annotation: ' + section_name)
        relocations = self.relocations(section_name)
        if len(relocations) != 1 or relocations[0]['offset'] != 0 or relocations[0]['type'] != 2:
            raise ValueError('wrong annotation relocation: ' + section_name)
        return self.relocation_target(relocations[0])


def warning_object(elf):
    data = elf.payload(elf.names.index('__bug_table'))
    if len(data) != 12:
        raise ValueError('expected one 12-byte relative verbose bug_entry')
    source_line, flags = struct.unpack_from('<HH', data, 8)
    if not source_line or flags != 0x901:
        raise ValueError('warning must be non-ONCE BUGFLAG_WARNING/TAINT_WARN')
    relocations = sorted(elf.relocations('__bug_table'), key=lambda r: r['offset'])
    if [(r['offset'], r['type']) for r in relocations] != [(0, 2), (4, 2)]:
        raise ValueError('expected PC32 bug-address/file relocations')
    instruction = elf.relocation_target(relocations[0])
    section, offset = instruction
    if elf.payload(section)[offset:offset + 2] != b'\x0f\x0b':
        raise ValueError('bug entry must point at the actual two-byte UD2')
    file_section, file_offset = elf.relocation_target(relocations[1])
    source_file = elf.string(elf.payload(file_section), file_offset)
    if not source_file.endswith('m15_mm_write_warning.S'):
        raise ValueError('unexpected warning source attribution')
    if elf.annotation_target('.discard.annotate_insn', 8) != instruction:
        raise ValueError('REACHABLE annotation does not point to warning UD2')
    if elf.annotation_target('.discard.annotate_data', 1) != (elf.names.index('__bug_table'), 0):
        raise ValueError('special-data annotation does not point to bug entry')
    body = elf.symbol_bytes('m15_mmap_write_lock_warning')
    if not body.startswith(b'\xf3\x0f\x1e\xfa'):
        raise ValueError('exact IBT pin requires ENDBR64 at warning entry')
    thunk = [r for r in elf.relocations(elf.names[section])
             if r['symbol']['name'] == '__x86_return_thunk']
    if not thunk:
        raise ValueError('exact RETHUNK pin requires the Linux return thunk')
    return dict(source_file=source_file, source_line=source_line, flags=flags,
                ud2_offset=offset, bug_entry_bytes=len(data),
                warning_reachable=True, special_data=True,
                endbr64=True, linux_return_thunk=True)


def words(elf, name, count):
    data = elf.symbol_bytes(name)
    if len(data) != count * 8:
        raise ValueError('wrong layout vector width: ' + name)
    return list(struct.unpack('<' + 'Q' * count, data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--c-layout', required=True, type=Path)
    parser.add_argument('--rust-layout', required=True, type=Path)
    parser.add_argument('--warning-object', required=True, type=Path)
    args = parser.parse_args()
    c, rust, warning = [Elf(path) for path in
                        (args.c_layout, args.rust_layout, args.warning_object)]
    c_mm, rust_mm = words(c, 'm15_c_mm_layout', 23), words(rust, 'm15_rust_mm_layout', 23)
    c_warn = words(c, 'm15_c_warning_layout', 12)
    rust_warn = words(rust, 'm15_rust_warning_layout', 12)
    if c_mm != rust_mm or c_warn != rust_warn:
        raise ValueError('actual C/Rust pinned-SDK layout mismatch')
    if c_mm[19] != 8 or c_warn[0:3] != [1, 8, 8] or c_warn[5:] != [12, 0, 4, 8, 10, 1, 0x901]:
        raise ValueError('actual layout differs from exact gate/warning ASM preconditions')
    result = dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
                  status='PASS_INERT_LAYOUT_AND_WARNING_OBJECT_READBACK_ONLY',
                  layout_words=c_mm, warning_layout_words=c_warn,
                  warning=warning_object(warning),
                  inputs=[dict(path=str(elf.path), sha256=hashlib.sha256(elf.raw).hexdigest())
                          for elf in (c, rust, warning)],
                  actual_objtool_module_native_acceptance=False)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
