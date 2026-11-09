"""Four actual timer callback forwarders; qualified ELF reader, no execution loader."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def actual_object_gate(q):
    for path, digest in q['source_bindings'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    for item in q['source_segments']:
        raw = ''.join(Path(item['path']).read_text().splitlines(keepends=True)[item['first_line']-1:item['last_line']]).encode()
        assert hashlib.sha256(raw).hexdigest() == item['segment_sha256'], item
    item = q['qualified_ELF_reader']
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_ELF_reader_for_four_timer_callbacks', item['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    contract = json.loads(Path(q['source_emission_contract']).read_text())
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes(), 'Actual admitted readback must be retained'
    # Save ALL emission before any expected owner/function/relocation assertions.
    sections = []
    for section in image.sections:
        entry = dict(section)
        if section['type'] == 8:
            entry['NOBITS_declaration_only'] = True
        elif section['flags'] & 2:
            raw = image.contents(section)
            entry.update(actual_file_bytes_hex=raw.hex(), actual_file_bytes_sha256=hashlib.sha256(raw).hexdigest())
        sections.append(entry)
    capture = dict(object_sha256=hashlib.sha256(image.raw).hexdigest(), object_bytes=len(image.raw),
                   sections=sections, symbols=image.symbols, relocations=image.relocations,
                   genuine_U=sorted(image.undefined), no_loader_or_runtime=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(capture, stream, indent=2)
        stream.write('\n')
    assert capture['object_sha256'] == q['compiled_input']['sha256'] and capture['object_bytes'] == q['compiled_input']['bytes']
    expected = contract['wrapper_genuine_imports']
    assert set(definitions) == set(image.defined) == set(expected)
    assert imports == image.undefined == set(expected.values())
    functions = [s for s in image.symbols if s['section'] != 0 and s['type'] == 2]
    assert len(functions) == 4 and {s['name'] for s in functions} == set(expected)
    assert not [s for s in image.symbols if s['section'] != 0 and s['type'] == 1], 'No global/private data'
    assert not [s for s in image.sections if s['size'] and s['flags'] & 3 == 3], 'No writable state'
    evidence = {}
    owned_relocation_ids = set()
    for symbol in functions:
        name = symbol['name']
        assert symbol['bind'] == 1 and symbol['other'] & 3 == 0 and symbol['size'] > 0
        assert image.kind(symbol) == 'T' and definitions[name] == dict(kind='T', size=symbol['size'])
        rows = [(index, row) for index, row in enumerate(image.relocations)
                if row['section'] == symbol['section'] and symbol['value'] <= row['offset'] < symbol['value'] + symbol['size']]
        assert len(rows) == 1, ('Exactly one genuine forwarding address relocation', name)
        index, relocation = rows[0]
        target = relocation['symbol']
        assert relocation['type'] == 1 and relocation['addend'] == 0
        assert target['bind'] == 1 and target['section'] == 0 and target['name'] == expected[name]
        assert target['type'] in (0,2) and target['other'] & 3 == 0
        owned_relocation_ids.add(index)
        evidence[name] = dict(bytes=symbol['size'], actual_function_bytes_sha256=hashlib.sha256(image.symbol_bytes(symbol)).hexdigest(),
                              actual_function_bytes_hex=image.symbol_bytes(symbol).hex(), genuine_import=expected[name],
                              exact_actual_address_relocation=relocation,
                              source_ABI=contract['wrapper_ABI'][name])
    for section in image.sections:
        if section['size'] and section['flags'] & 4:
            assert any(s['section'] == section['index'] for s in functions), 'No unowned executable source section'
    unwind = []
    for section in image.sections:
        if not section['size'] or not section['flags'] & 2 or section['flags'] & 5:
            continue
        assert section['name'] == '.eh_frame' and section['type'] == 0x70000001 and section['flags'] == 2 and section['align'] == 8
        targets = []
        for index, row in enumerate(image.relocations):
            if row['section'] != section['index']:
                continue
            assert row['type'] == 24 and row['symbol']['bind'] == 0
            target = row['symbol']
            position = target['value'] + row['addend']
            owners = [s['name'] for s in functions if s['section'] == target['section'] and s['value'] <= position < s['value'] + s['size']]
            assert len(owners) == 1
            targets.append(owners[0])
            owned_relocation_ids.add(index)
        assert len(targets) == 4 and set(targets) == set(expected)
        unwind.append(dict(name=section['name'], bytes=section['size'], selected_function_targets=targets))
    assert len(unwind) == 1
    assert owned_relocation_ids == set(range(len(image.relocations))), 'No unreviewed data/helper relocation'
    return dict(status='PASS_CALLED_ACTUAL_FOUR_TIMER_CALLBACK_FORWARDING_OBJECT_GATE',
                object_sha256=capture['object_sha256'], actual4T={name:image.defined[name]['size'] for name in sorted(image.defined)},
                genuine4U=sorted(image.undefined), exact_function_forwarding=evidence,
                source_owned_unwind=unwind, data_or_private_helpers=[], actual_metadata_capture=q['actual_metadata_capture'],
                future_base_and_join_unbound=True, no_lock_LAPIC_timer_IRQ_scheduling_boot_native_or_function_runtime=True)
