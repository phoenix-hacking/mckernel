"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only gate for one current timer descriptor and its actual HOST consumer.
"""
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys

P = Path(__file__).resolve().parent
HELPER = P.parent / 'f02-source38-next-current-integration-source-1/check_thirteen_storage.py'
spec = importlib.util.spec_from_file_location('accepted_fixed_f02_elf', HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def table(elf):
    definitions = elf.definitions('process_timer_runtime_offsets')
    assert len(definitions) == 1, (elf.path, 'not one allocated timer descriptor')
    symbol = definitions[0]
    section = elf.sections[symbol['ndx']]
    assert symbol['kind'] == 1 and symbol['bind'] == 1 and symbol['size'] == 120
    assert section['flags'] & 2 and not section['flags'] & (1 | 4)
    assert section['align'] >= 8 and symbol['value'] % 8 == 0
    start = section['off'] + symbol['value'] - section['addr']
    data = elf.data[start:start + 120]
    for relocations in elf.sections:
        if relocations['type'] != 4 or relocations['info'] != symbol['ndx']:
            continue
        for offset in range(0, relocations['size'], relocations['entsize']):
            address, _, _ = struct.unpack_from('<QQq', elf.data, relocations['off'] + offset)
            assert not symbol['value'] <= address < symbol['value'] + 120, 'Offset words must not hide pointer relocations'
    return dict(symbol=symbol, section=section['name'], section_flags=section['flags'],
                bytes_hex=data.hex(), words=list(struct.unpack('<15Q', data)))


def map_entries(path):
    text = Path(path).read_text().split('Linker script and memory map', 1)[1]
    text = text.split('Cross Reference Table', 1)[0]
    result, pending = [], None
    for line in text.splitlines():
        m = re.match(r'^\s+(\.[^\s]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.+?)\s*$', line)
        if m:
            result.append((m[1], int(m[2], 16), int(m[3], 16), m[4]))
            pending = None
            continue
        m = re.match(r'^\s+(\.[^\s]+)\s*$', line)
        if m:
            pending = m[1]
            continue
        m = re.match(r'^\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.+?)\s*$', line)
        if pending and m:
            result.append((pending, int(m[1], 16), int(m[2], 16), m[3]))
            pending = None
    return result


def origin(source, final, entries, name):
    old, new = source.definitions(name), final.definitions(name)
    assert len(old) == len(new) == 1, name
    original, linked = old[0], new[0]
    section = source.sections[original['ndx']]['name']
    matches = [row for row in entries if row[0] == section and row[2] > 0
               and row[3] == str(source.path)]
    assert len(matches) == 1, (name, section, matches)
    assert linked['value'] == matches[0][1] + original['value'], ('Wrong final provider', name)
    return dict(name=name, object_section=section, final_address=hex(linked['value']),
                exact_Rust_provider=True)


def main():
    rust_path, fallback_path, selected_path, executable_path, map_path, output_path = map(Path, sys.argv[1:])
    manifest = json.loads((P / 'SOURCE-IMPLEMENTATION-AND-CURRENT120B-ABI.json').read_text())
    baseline = manifest['current71_C_object']
    assert module.ref(baseline['path']) == baseline
    old, rust, fallback, selected, final = map(module.Elf,
        (baseline['path'], rust_path, fallback_path, selected_path, executable_path))
    records = {label: table(elf) for label, elf in
               [('current055c', old), ('focused_Rust', rust), ('fallback_C', fallback), ('HOST_final', final)]}
    assert all(row['bytes_hex'] == manifest['actual_current_table']['bytes_hex']
               for row in records.values())
    assert not selected.definitions('process_timer_runtime_offsets'), 'Selected C still owns descriptor'
    entries = map_entries(map_path)
    origins = [origin(rust, final, entries, name)
               for name in ['process_timer_runtime_offsets', 'set_timer', 'leaf_timer_set_timer_body_result']]
    Path(output_path).write_text(json.dumps(dict(scope=__doc__.splitlines()[0],
        status='PASS_TIMER120_CURRENT_BYTES_READONLY_SELECTED_FALLBACK_AND_EXACT_RUST_ORIGINS',
        tables=records, final_origins=origins, selected_C_owner_absent=True,
        current_C_baseline=baseline, Rust=module.ref(rust_path),
        fallback=module.ref(fallback_path), selected=module.ref(selected_path),
        executable=module.ref(executable_path), production_or_native_credit=False,
        GNU_RETAIN_verbose_scope='Unchanged; no descriptor or retention waiver',
        file_retirement=False), indent=2) + '\n')
    print(json.dumps(dict(status='PASS_TIMER120_READONLY15WORDS_AND_REAL_CONSUMER_ORIGINS',
                          data_objects=1, offset_words=15)))


if __name__ == '__main__':
    main()
