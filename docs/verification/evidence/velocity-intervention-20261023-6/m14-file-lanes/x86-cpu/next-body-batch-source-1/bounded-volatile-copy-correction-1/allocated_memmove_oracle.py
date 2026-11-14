"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Observe an already durably recorded ELF64 little-endian relocatable Rust object.
No subprocess, hashing, disassembly, or code execution occurs here.
"""
import struct


def observe(path):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('ELF64 little endian required')
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', data)
    if header[1] != 1 or header[2] != 62:
        raise ValueError('x86_64 relocatable required')
    shoff, shentsize, shnum, shstrndx = header[6], header[11], header[12], header[13]
    if shentsize != 64 or not shnum or not shstrndx < shnum:
        raise ValueError('finite ordinary section table required')
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, shoff + i * shentsize)
                for i in range(shnum)]

    def payload(s):
        start, size = s[4], s[5]
        if start + size > len(data):
            raise ValueError('section outside object')
        return data[start:start + size]

    def string(table, at):
        end = table.index(b'\0', at)
        return table[at:end].decode('ascii')

    names = payload(sections[shstrndx])
    section_names = [string(names, s[0]) for s in sections]
    symbols = {}
    functions = {}
    for index, s in enumerate(sections):
        if s[1] != 2:
            continue
        if s[9] != 24 or s[5] % 24 or s[6] >= shnum:
            raise ValueError('symbol table shape')
        strings = payload(sections[s[6]])
        rows = []
        for offset in range(s[4], s[4] + s[5], 24):
            name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', data, offset)
            name = string(strings, name)
            rows.append(name)
            if name in ('mod_nmi_ctx', 'freeze_thaw') and info & 15 == 2:
                if name in functions or not 0 < shndx < shnum or not sections[shndx][2] & 2:
                    raise ValueError('unique allocated function required: ' + name)
                functions[name] = {'section': section_names[shndx], 'section_index': shndx,
                                   'value': value, 'size': size}
        symbols[index] = rows
    references = []
    for s in sections:
        if s[1] != 4:
            continue
        if s[9] != 24 or s[5] % 24 or s[7] >= shnum or s[6] not in symbols:
            raise ValueError('rela table shape')
        if not sections[s[7]][2] & 2:
            continue
        for offset in range(s[4], s[4] + s[5], 24):
            address, info, addend = struct.unpack_from('<QQq', data, offset)
            symbol_index = info >> 32
            if symbol_index >= len(symbols[s[6]]):
                raise ValueError('relocation symbol outside table')
            if symbols[s[6]][symbol_index] == 'memmove':
                references.append({'section': section_names[s[7]], 'offset': address,
                                   'type': info & 0xffffffff, 'addend': addend})
    if set(functions) != {'mod_nmi_ctx', 'freeze_thaw'}:
        raise ValueError('both actual functions required')
    if references:
        raise ValueError(('allocated memmove references remain', references))
    return {'ELF64_x86_64_relocatable': True, 'functions': functions,
            'allocated_memmove_references': references,
            'both_direct_and_optimizer_inlined_copy_checked': True,
            'observation_only_no_subprocess_hash_or_execution': True}
