"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only postcompiler gate for the fixed thirteen F02 line-storage records.
No executable is run. Missing consumer relocations stay OPEN for exact code review.
"""
import hashlib
import json
from pathlib import Path
import struct
import sys

P = Path(__file__).resolve().parent


class Elf:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        h = struct.unpack_from('<16sHHIQQQIHHHHHH', self.data)
        assert self.data[:6] == b'\x7fELF\x02\x01'
        self.sections = []
        for i in range(h[12]):
            z = struct.unpack_from('<IIQQQQIIQQ', self.data, h[6] + i * h[11])
            self.sections.append(dict(no=z[0], type=z[1], flags=z[2], addr=z[3],
                                      off=z[4], size=z[5], link=z[6], info=z[7],
                                      align=z[8], entsize=z[9]))
        names = self.section_data(h[13])
        for s in self.sections:
            s['name'] = names[s['no']:].split(b'\0')[0].decode()
        self.tables, self.symbols = {}, []
        for index, s in enumerate(self.sections):
            if s['type'] != 2:
                continue
            names = self.section_data(s['link'])
            table = []
            for off in range(0, s['size'], s['entsize']):
                no, info, _, ndx, value, size = struct.unpack_from('<IBBHQQ', self.data, s['off'] + off)
                table.append(dict(name=names[no:].split(b'\0')[0].decode(),
                                  kind=info & 15, bind=info >> 4, ndx=ndx,
                                  value=value, size=size))
            self.tables[index] = table
            self.symbols.extend(table)

    def section_data(self, index):
        s = self.sections[index]
        return self.data[s['off']:s['off'] + s['size']]

    def definitions(self, name):
        return [s for s in self.symbols if s['name'] == name and s['ndx']
                and s['ndx'] < len(self.sections)
                and self.sections[s['ndx']]['flags'] & 2]

    def readonly_int(self, name, expected):
        rows = self.definitions(name)
        assert len(rows) == 1, (self.path, name, 'not one allocated owner')
        symbol = rows[0]
        section = self.sections[symbol['ndx']]
        assert symbol['kind'] == 1 and symbol['bind'] == 1 and symbol['size'] == 4
        assert section['flags'] & 2 and not section['flags'] & (1 | 4)
        assert section['align'] >= 4 and symbol['value'] % 4 == 0
        start = section['off'] + symbol['value'] - section['addr']
        data = self.data[start:start + 4]
        assert int.from_bytes(data, 'little', signed=True) == expected, (name, data.hex())
        return dict(name=name, section=section['name'], section_flags=section['flags'],
                    alignment_minimum=4, bytes_hex=data.hex(), signed_value=expected)

    def allocated_references(self, name):
        rows = []
        for section in self.sections:
            if section['type'] != 4 or not self.sections[section['info']]['flags'] & 2:
                continue
            table = self.tables[section['link']]
            for off in range(0, section['size'], section['entsize']):
                offset, info, addend = struct.unpack_from('<QQq', self.data, section['off'] + off)
                if table[info >> 32]['name'] == name:
                    rows.append(dict(section=self.sections[section['info']]['name'],
                                     offset=offset, relocation_type=info & 0xffffffff,
                                     addend=addend))
        return rows


def ref(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    # Existing baseline path is frozen by the source manifest; all outputs are new.
    changed_path, rust_path, image_path, output_path = map(Path, sys.argv[1:])
    manifest = json.loads((P / 'SOURCE-IMPLEMENTATION-AND-ACTUAL13-ABI.json').read_text())
    baseline_ref = manifest['current_process_object']
    assert ref(baseline_ref['path']) == baseline_ref
    old, changed, rust, image = map(Elf, (baseline_ref['path'], changed_path, rust_path, image_path))
    rows, open_consumers = [], []
    for record in manifest['data_records']:
        name, value = record['name'], record['value']
        prior = old.readonly_int(name, value)
        assert not changed.definitions(name), ('selected C still owns record', name)
        owner = rust.readonly_int(name, value)
        final = image.readonly_int(name, value)
        references = rust.allocated_references(name)
        if not references:
            open_consumers.append(dict(name=name, original_consumer=record['Rust_consumer']['name'],
                                       required='Exact constant-folded argument instruction proof; no blanket inlining waiver'))
        rows.append(dict(name=name, baseline=prior, Rust=owner, final=final,
                         current_Rust_consumer=record['Rust_consumer'],
                         Rust_allocated_relocations=references))
    result = dict(scope=__doc__.splitlines()[0],
                  status='PASS_STORAGE13_CONSUMER_INSTRUCTION_PROOF_OPEN' if open_consumers else 'PASS_STORAGE13_AND_REAL_RUST_RELOCATIONS_PENDING_FINAL_MAP_REVIEW',
                  records=rows, open_consumer_instruction_proofs=open_consumers,
                  baseline=baseline_ref, changed_process=ref(changed_path), Rust=ref(rust_path),
                  final_image=ref(image_path), no_native_execution=True,
                  required_independent_final_checks='Exact image map Rust ownership for13; unchanged71 C metadata/debug/pointer graphs; current default/native tuple.',
                  whole_file_acceptance=False, retirement_acceptance=False)
    Path(output_path).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], records=13, open_consumers=len(open_consumers))))


if __name__ == '__main__':
    main()
