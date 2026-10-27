"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixed F01 link gate: each unchanged fixture extern must resolve to Rust bytes.
This program reads ELF/map files; it never runs either executable.
"""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

P = Path(__file__).resolve().parent


class Elf:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        header = struct.unpack_from('<16sHHIQQQIHHHHHH', self.data)
        assert self.data[:6] == b'\x7fELF\x02\x01'
        self.sections = []
        for index in range(header[12]):
            z = struct.unpack_from('<IIQQQQIIQQ', self.data,
                                   header[6] + index * header[11])
            self.sections.append(dict(nameoff=z[0], type=z[1], off=z[4],
                                      size=z[5], link=z[6], entsize=z[9]))
        names = self.section_bytes(header[13])
        for section in self.sections:
            section['name'] = names[section['nameoff']:].split(b'\0')[0].decode()
        self.symbols = []
        for section in self.sections:
            if section['type'] != 2:
                continue
            names = self.section_bytes(section['link'])
            for offset in range(0, section['size'], section['entsize']):
                no, info, _, ndx, value, size = struct.unpack_from(
                    '<IBBHQQ', self.data, section['off'] + offset)
                self.symbols.append(dict(name=names[no:].split(b'\0')[0].decode(),
                                         type=info & 15, bind=info >> 4,
                                         ndx=ndx, value=value, size=size))

    def section_bytes(self, index):
        section = self.sections[index]
        return self.data[section['off']:section['off'] + section['size']]

    def functions(self):
        return {s['name']: s for s in self.symbols if s['type'] == 2 and s['ndx']}


def ref(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    obj, exe, mapfile, output = map(Path, sys.argv[1:])
    binding = json.loads((P / 'PROVIDER-SOURCE-BINDING.json').read_text())
    names = binding['root_memory_externs'] + ['hash_64', 'hash_32', 'hash_long', 'hash_ptr']
    assert len(names) == len(set(names)) == 77
    source, final = Elf(obj), Elf(exe)
    sf, ff = source.functions(), final.functions()
    text = mapfile.read_text().split('Linker script and memory map', 1)[1]
    text = text.split('Cross Reference Table', 1)[0]
    entries, pending = [], None
    for line in text.splitlines():
        match = re.match(r'^\s+(\.[^\s]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.+?)\s*$', line)
        if match:
            entries.append((match[1], int(match[2], 16), int(match[3], 16), match[4]))
            pending = None
            continue
        match = re.match(r'^\s+(\.[^\s]+)\s*$', line)
        if match:
            pending = match[1]
            continue
        match = re.match(r'^\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.+?)\s*$', line)
        if pending and match:
            entries.append((pending, int(match[1], 16), int(match[2], 16), match[3]))
            pending = None
    rows = []
    for name in sorted(names):
        assert name in sf and name in ff, ('missing tested definition', name)
        original, linked = sf[name], ff[name]
        assert original['bind'] == linked['bind'] == 1, ('tested symbol is not strong', name)
        section = source.sections[original['ndx']]['name']
        matches = [entry for entry in entries
                   if entry[0] == section and entry[2] > 0 and entry[3] == str(obj)]
        assert len(matches) == 1, ('missing/ambiguous Rust input section', name, matches)
        _, base, size, _ = matches[0]
        assert linked['value'] == base + original['value'], ('tested definition masked', name)
        assert original['value'] + original['size'] <= size, ('symbol outside input section', name)
        original_section = source.sections[original['ndx']]
        final_section = final.sections[linked['ndx']]
        start = original_section['off'] + original['value']
        source_bytes = source.data[start:start + original['size']]
        # Relocations may alter final bytes; section+symbol address, not byte equality,
        # binds the selected provider at this host link.
        rows.append(dict(name=name, input_section=section, input_section_size=size,
                         object_value=original['value'], linked_value=hex(linked['value']),
                         object_symbol_sha256=hashlib.sha256(source_bytes).hexdigest(),
                         exact_Rust_input_origin=True))
    Path(output).write_text(json.dumps(dict(
        scope=__doc__.splitlines()[0], status='PASS_ALL_77_TESTED_EXTERNS_FROM_EXACT_RUST_PROVIDER',
        functions=rows, object=ref(obj), executable=ref(exe), map=ref(mapfile),
        source_binding=ref(P / 'PROVIDER-SOURCE-BINDING.json'),
        fixture=binding['unchanged_fixture'], no_new_mocks=True,
        production_or_native_credit=False, whole_file_acceptance=False), indent=2) + '\n')
    print(json.dumps(dict(status='PASS_EXACT_TESTED_RUST_ORIGINS', functions=len(rows))))


if __name__ == '__main__':
    main()
