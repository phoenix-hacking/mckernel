"""Functional OS trace metadata extraction; no security testing.

Read only the named ELF64 relocatable object's actual constant/relocation bytes.
"""
import struct


def observe(path, expected_lines, expected_filename):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('expected actual little-endian ELF64')
    if struct.unpack_from('<HH', data, 16) != (1, 62):
        raise ValueError('expected actual x86_64 relocatable object')
    offset = struct.unpack_from('<Q', data, 40)[0]
    stride, count, names_index = struct.unpack_from('<HHH', data, 58)
    if stride != 64 or count == 0:
        raise ValueError('ordinary ELF64 section table required')
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + index*stride)
                for index in range(count)]

    def section_bytes(index):
        section = sections[index]
        return data[section[4]:section[4]+section[5]]

    def string(blob, index):
        end = blob.index(b'\0', index)
        return blob[index:end]

    names = section_bytes(names_index)
    section_name = lambda index: string(names, sections[index][0]).decode()
    table_index = next(index for index, row in enumerate(sections) if row[1] == 2)
    table = sections[table_index]
    symbols = [struct.unpack_from('<IBBHQQ', data, at)
               for at in range(table[4], table[4]+table[5], table[9])]
    symbol_names = section_bytes(table[6])

    def symbol(name):
        found = [row for row in symbols if string(symbol_names, row[0]).decode() == name]
        if len(found) != 1 or found[0][3] == 0:
            raise ValueError('one defined metadata symbol required: ' + name)
        return found[0]

    observed = {}
    for provider, expected in expected_lines.items():
        name = provider + '_source_line'
        row = symbol(name)
        if row[5] != 4 or sections[row[3]][2] & 1:
            raise ValueError('line metadata must be four actual readonly bytes: ' + name)
        raw = section_bytes(row[3])[row[4]:row[4]+4]
        if raw != struct.pack('<i', expected):
            raise ValueError('original trace-line bytes changed: ' + name)
        observed[name] = dict(value=expected, bytes_hex=raw.hex(),
                              section=section_name(row[3]), section_flags=sections[row[3]][2])

    name = 'process_tracked_allocator_source_file'
    row = symbol(name)
    if row[5] != 8:
        raise ValueError('actual file metadata must have pointer width8')
    relocations = []
    for section in sections:
        if section[1] != 4 or section[7] != row[3]:
            continue
        for at in range(section[4], section[4]+section[5], section[9]):
            target, info, addend = struct.unpack_from('<QQq', data, at)
            if target == row[4]:
                relocations.append((info >> 32, info & 0xffffffff, addend))
    if len(relocations) != 1 or relocations[0][1] != 1:
        raise ValueError('one exact R_X86_64_64 source-file relocation required')
    referenced, kind, addend = relocations[0]
    target = symbols[referenced]
    file_bytes = string(section_bytes(target[3]), target[4]+addend) + b'\0'
    if file_bytes != expected_filename.encode() + b'\0':
        raise ValueError('actual original __FILE__ bytes changed')
    pointer_section = section_name(row[3])
    if sections[row[3]][2] & 1 and not pointer_section.startswith('.data.rel.ro'):
        raise ValueError('source file pointer lacks readonly/relocation-readonly section')
    observed[name] = dict(file_bytes_hex=file_bytes.hex(), file=expected_filename,
                          pointer_section=pointer_section, section_flags=sections[row[3]][2],
                          target_section=section_name(target[3]), relocation_type=kind,
                          raw_pointer_bytes=section_bytes(row[3])[row[4]:row[4]+8].hex(),
                          final_image_readonly_mapping_proven=False)
    return observed
