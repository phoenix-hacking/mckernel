"""Exact18 original mutable debug records: actual ELF metadata only, no loader."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def actual_object_gate(q):
    for path, digest in q['source_bindings'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    for item in q['source_segments']:
        lines = Path(item['path']).read_text().splitlines(keepends=True)
        raw = ''.join(lines[item['first_line']-1:item['last_line']]).encode()
        assert hashlib.sha256(raw).hexdigest() == item['segment_sha256'], item
    item = q['qualified_ELF_reader']
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_ELF_reader_for_scheduler_debug18', item['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    contract = json.loads(Path(q['source_emission_contract']).read_text())
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes(), 'Actual admitted ELF readback must be retained'
    # Preserve every emitted owner, section, relocation and allocated byte BEFORE assertions.
    sections = []
    for section in image.sections:
        entry = dict(section)
        if section['type'] == 8:
            entry['NOBITS_declaration_only'] = True
        elif section['flags'] & 2:
            raw = image.contents(section)
            entry['actual_file_bytes_hex'] = raw.hex()
            entry['actual_file_bytes_sha256'] = hashlib.sha256(raw).hexdigest()
        sections.append(entry)
    capture = dict(object_sha256=hashlib.sha256(image.raw).hexdigest(), object_bytes=len(image.raw),
                   symbols=image.symbols, sections=sections, relocations=image.relocations,
                   genuine_U=sorted(image.undefined), no_loader_or_runtime=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(capture, stream, indent=2)
        stream.write('\n')
    assert capture['object_sha256'] == q['compiled_input']['sha256']
    assert capture['object_bytes'] == q['compiled_input']['bytes']
    assert set(definitions) == set(image.defined) and imports == image.undefined
    assert contract['flags'] == 1 and len(contract['records']) == 18
    name = contract['name']
    assert set(image.defined) == {name} and not image.undefined, 'Exactly one actual global data owner, zero U'
    symbol = image.defined[name]
    assert symbol['bind'] == 1 and symbol['type'] == 1 and symbol['other'] & 3 == 0
    assert image.kind(symbol) == 'D' and symbol['size'] == 576
    assert definitions[name] == dict(kind='D', size=576)
    section = image.sections[symbol['section']]
    assert section['name'] == '__verbose' and section['type'] == 1
    # Exact observed WRITE|ALLOC|GNU_RETAIN, retaining original #[used] emission.
    assert section['flags'] == 0x200003 and section['align'] == 8
    assert symbol['value'] == 0 and section['size'] == 576
    assert not [s for s in image.symbols if s['section'] != 0 and s['type'] == 2], 'No public/private emitted functions'
    assert not [s for s in image.sections if s['size'] and s['flags'] & 4], 'No executable allocated content'
    assert [s['index'] for s in image.sections if s['size'] and s['flags'] & 3 == 3] == [section['index']], 'No unrelated writable state'
    raw = image.symbol_bytes(symbol)
    expected_offsets = {index * 32 + field for index in range(18) for field in (0,8)}
    assert len(image.relocations) == 36
    assert all(r['section'] == section['index'] and r['type'] == 1 for r in image.relocations)
    assert {r['offset'] for r in image.relocations} == expected_offsets
    by_offset = {r['offset']: r for r in image.relocations}
    assert len(by_offset) == 36
    records = []
    readonly_targets = {}
    for index, expected in enumerate(contract['records']):
        base = index * 32
        assert raw[base+16:base+24] == bytes(8), 'Original fmt pointer must remain NULL'
        line_flags = int.from_bytes(raw[base+24:base+28], 'little')
        assert line_flags == expected['line'] | (1 << 24)
        targets = {}
        for field, field_offset, content in [('file',0,contract['file_nul_hex']), ('func',8,expected['function_nul_hex'])]:
            relocation = by_offset[base+field_offset]
            target = reader.Image.pointer_target(image, relocation, len(bytes.fromhex(content)))
            assert target[2] == bytes.fromhex(content), (index, field, 'Exact original NUL string')
            target_section = image.sections[target[0]]
            assert target_section['flags'] & 2 and not target_section['flags'] & 5
            assert relocation['symbol']['bind'] == 0, 'Genuine new object-owned readonly string, no external provider'
            targets[field] = dict(section_index=target[0], offset=target[1], bytes_hex=target[2].hex(), relocation=relocation)
            readonly_targets.setdefault(target[0], []).append(dict(record=index, field=field, offset=target[1]))
        records.append(dict(index=index, line=expected['line'], flags=1, line_flags=line_flags,
                            fmt_null=True, targets=targets, actual_record_bytes_hex=raw[base:base+32].hex(),
                            actual_trailing_ABI_padding_hex=raw[base+28:base+32].hex()))
    literals = [bytes.fromhex(value) for value in contract['source_nul_literals_hex']]
    readonly = {}
    for candidate in image.sections:
        if not candidate['size'] or not candidate['flags'] & 2 or candidate['flags'] & 5:
            continue
        assert candidate['type'] == 1 and candidate['index'] in readonly_targets, 'No unrelated/unreferenced readonly emission'
        value = image.contents(candidate)
        assert value.endswith(b'\0')
        at = 0
        strings = []
        while at < len(value):
            end = value.index(0, at) + 1
            part = value[at:end]
            matches = [literal.hex() for literal in literals if literal.endswith(part)]
            assert matches, ('Unreviewed readonly bytes', candidate['name'], at, part.hex())
            strings.append(dict(offset=at, bytes_hex=part.hex(), source_literal_or_suffix_hex=matches))
            at = end
        readonly[candidate['index']] = dict(section=dict(candidate), actual_strings=strings, actual_field_targets=readonly_targets[candidate['index']])
    private_data = []
    for candidate in image.symbols:
        if candidate['section'] == 0 or candidate['type'] != 1 or candidate['name'] == name:
            continue
        assert candidate['bind'] == 0 and candidate['section'] in readonly
        assert candidate['value'] + candidate['size'] <= image.sections[candidate['section']]['size']
        private_data.append(dict(symbol=candidate, actual_bytes_sha256=hashlib.sha256(image.symbol_bytes(candidate)).hexdigest()))
    return dict(status='PASS_CALLED_EXACT18_SCHEDULER_DEBUG_DATA_OBJECT_GATE',
                object_sha256=capture['object_sha256'], global_OBJECT=dict(name=name, bytes=576, alignment=8, section='__verbose', mutable=True),
                actual_T=0, genuine_U=[], actual_records=records, pointer_field_relocations=36,
                readonly_source_evidence=list(readonly.values()), actual_private_readonly_symbols=private_data,
                all_actual_metadata_retained=q['actual_metadata_capture'], no_padding_value_or_unique_pool_count_claim=True,
                future_base_and_join_unbound=True, no_function_registry_init_logging_IRQ_scheduling_native_runtime=True)
