"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read only the focused object and two linked HOST fixtures. No executable runs here.
"""
import importlib.util
import json
from pathlib import Path
import re
import sys

H = Path(__file__).resolve().parent
P = H.parent
spec = importlib.util.spec_from_file_location('fixed_line13_elf', P / 'check_thirteen_storage.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def map_entries(path):
    text = Path(path).read_text().split('Linker script and memory map', 1)[1]
    text = text.split('Cross Reference Table', 1)[0]
    entries, pending = [], None
    for line in text.splitlines():
        m = re.match(r'^\s+(\.[^\s]+)\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.+?)\s*$', line)
        if m:
            entries.append((m[1], int(m[2], 16), int(m[3], 16), m[4]))
            pending = None
            continue
        m = re.match(r'^\s+(\.[^\s]+)\s*$', line)
        if m:
            pending = m[1]
            continue
        m = re.match(r'^\s+(0x[0-9a-f]+)\s+(0x[0-9a-f]+)\s+(.+?)\s*$', line)
        if pending and m:
            entries.append((pending, int(m[1], 16), int(m[2], 16), m[3]))
            pending = None
    return entries


def main():
    obj, eight_exe, eight_map, five_exe, five_map, report = map(Path, sys.argv[1:])
    binding = json.loads((P / 'SOURCE-IMPLEMENTATION-AND-ACTUAL13-ABI.json').read_text())
    rust = module.Elf(obj)
    eight, five = module.Elf(eight_exe), module.Elf(five_exe)
    entries = {'eight': map_entries(eight_map), 'five': map_entries(five_map)}
    eight_names = {'process_mckfd_free_bridge', 'process_policy_free_bridge',
                   'process_optional_free_bridge', 'process_alloc_bridge',
                   'process_free_vm_bridge', 'process_range_kfree_bridge',
                   'process_add_range_alloc_bridge', 'process_add_range_free_bridge'}
    rows = []
    for row in binding['data_records']:
        storage = rust.readonly_int(row['name'], row['value'])
        name = row['Rust_consumer']['name']
        if name == 'free_pages':
            name = 'fixture_invoke_free_range_pages'
        label = 'eight' if name in eight_names else 'five'
        linked = eight if label == 'eight' else five
        definitions = [s for s in rust.definitions(name) if s['kind'] == 2]
        final_definitions = [s for s in linked.definitions(name) if s['kind'] == 2]
        assert len(definitions) == len(final_definitions) == 1, ('missing actual consumer', name)
        source, final = definitions[0], final_definitions[0]
        assert source['bind'] == final['bind'] == 1
        section = rust.sections[source['ndx']]['name']
        matches = [entry for entry in entries[label]
                   if entry[0] == section and entry[2] > 0 and entry[3] == str(obj)]
        assert len(matches) == 1, ('missing exact Rust input section', name, section, matches)
        assert final['value'] == matches[0][1] + source['value'], ('consumer masked by C', name)
        rows.append(dict(storage=storage, actual_consumer=name, fixture=label,
                         object_section=section, final_address=hex(final['value']),
                         exact_Rust_provider=True))
    Path(report).write_text(json.dumps(dict(scope=__doc__.splitlines()[0],
        status='PASS_13_READONLY_SIGNED_INT4_OBJECTS_AND_13_EXACT_RUST_CONSUMER_ORIGINS',
        rows=rows, object=module.ref(obj), eight_fixture=module.ref(eight_exe),
        five_fixture=module.ref(five_exe), production_or_native_credit=False,
        retirement_acceptance=False), indent=2) + '\n')
    print(json.dumps(dict(status='PASS_HOST_READONLY13_AND_EXACT_CONSUMER13', records=13)))


if __name__ == '__main__':
    main()
