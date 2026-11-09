"""Exact passed IPI/logger + local/accessor/real None slot objects; metadata only."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualified(q):
    item = q['qualified_ELF_reader']
    assert sha(item['path']) == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_storage_reader_for_ipi_local', item['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    return reader


def provenance(q, item):
    for path, digest in item['source_bindings'].items():
        assert sha(path) == digest, path
    review = json.loads(Path(item['source_review']).read_text())
    assert review['decision'] == item['source_review_decision']
    assert review['request']['path'] == item['source_request']
    assert review['request']['sha256'] == sha(item['source_request'])
    result = json.loads(Path(q['producer_result']).read_text())
    assert result['status'] == 'PASS_BOUNDED_CALLBACK_LAUNCH_CORRECTION_AND_TWO_NEW_SOURCE_PRODUCERS'
    assert result['all_direct_waits_joined'] and result['cpu6_released']
    matches = [row for row in result['commands'] if row['label'] == item['producer_label']]
    assert len(matches) == 1
    row = matches[0]
    assert row['joined'] and row['returncode'] == 0 and row['exact_retained_diagnostics']
    assert (row['object_path'], row['object_sha256'], row['object_bytes']) == (item['path'], item['sha256'], item['bytes'])


def capture(q, key):
    item = q['objects'][key]
    provenance(q, item)
    reader = qualified(q)
    image = reader.Image(item['path'])
    sections = []
    for section in image.sections:
        entry = dict(section)
        if section['type'] == 8:
            entry['NOBITS_declaration_only'] = True
        elif section['flags'] & 2:
            raw = image.contents(section)
            entry.update(actual_file_bytes_hex=raw.hex(), actual_file_bytes_sha256=hashlib.sha256(raw).hexdigest())
        sections.append(entry)
    evidence = dict(object_sha256=hashlib.sha256(image.raw).hexdigest(), object_bytes=len(image.raw),
                    symbols=image.symbols, sections=sections, relocations=image.relocations,
                    genuine_U=sorted(image.undefined), no_loader_or_runtime=True)
    with Path(item['capture']).open('x') as stream:
        json.dump(evidence, stream, indent=2)
        stream.write('\n')
    assert evidence['object_sha256'] == item['sha256'] and evidence['object_bytes'] == item['bytes']
    definitions, imports = reader.parse_nm(Path(item['actual_nm']).read_text())
    assert Path(item['actual_elf']).read_bytes(), 'Retain actual admitted ELF readback'
    assert set(definitions) == set(image.defined) and imports == image.undefined
    assert image.undefined == set(item['expected_U'])
    assert set(image.defined) == set(item['expected_T']) | {item['expected_data_name']}
    for name, fields in definitions.items():
        symbol = image.defined[name]
        assert fields == dict(kind=image.kind(symbol), size=symbol['size'])
        assert symbol['bind'] == 1 and symbol['other'] & 3 == 0
    private = [s for s in image.symbols if s['bind'] == 0 and s['section'] != 0 and s['type'] in (1, 2)]
    assert not private, 'Unexpected emitted private function/object requires concrete review; no wildcard'
    return item, reader, image, evidence


def functions(image, names):
    result = {}
    sections = set()
    for name in names:
        symbol = image.defined[name]
        section = image.sections[symbol['section']]
        assert symbol['type'] == 2 and image.kind(symbol) == 'T' and symbol['size'] > 0
        assert section['name'] == '.ltext.' + name and section['type'] == 1
        assert section['flags'] == 0x10000006 and section['align'] == 16
        assert symbol['value'] == 0 and section['size'] == symbol['size']
        assert symbol['section'] not in sections
        sections.add(symbol['section'])
        relocs = [r for r in image.relocations if r['section'] == symbol['section']]
        assert all(0 <= r['offset'] < symbol['size'] and r['type'] == 1 for r in relocs)
        raw = image.symbol_bytes(symbol)
        result[name] = dict(symbol=symbol, section=dict(section), actual_bytes_hex=raw.hex(),
                            actual_bytes_sha256=hashlib.sha256(raw).hexdigest(), actual_relocations=relocs)
    emitted = {s['section'] for s in image.symbols if s['section'] != 0 and s['type'] == 2}
    assert emitted == sections
    executable = {s['index'] for s in image.sections if s['size'] and s['flags'] & 4}
    assert executable == sections
    return result, sections


def unwind(image, function_sections):
    sections = [s for s in image.sections if s['name'] == '.eh_frame']
    assert len(sections) == 1
    section = sections[0]
    assert section['type'] == 0x70000001 and section['flags'] == 2 and section['align'] == 8 and section['size'] > 0
    relocs = [r for r in image.relocations if r['section'] == section['index']]
    assert len(relocs) == len(function_sections)
    assert all(r['type'] == 24 and r['symbol']['bind'] == 0 and r['symbol']['type'] == 3
               and r['symbol']['section'] in function_sections and r['symbol']['value'] + r['addend'] == 0 for r in relocs)
    assert {r['symbol']['section'] for r in relocs} == function_sections
    return dict(section=dict(section), actual_bytes_sha256=hashlib.sha256(image.contents(section)).hexdigest(), actual_relocations=relocs)


def strings(image, contract):
    expected = [bytes.fromhex(x) for x in contract['all_source_literals_hex']]
    sections = [s for s in image.sections if s['name'] == '.lrodata.str1.1']
    assert len(sections) == 1
    section = sections[0]
    assert section['type'] == 1 and section['flags'] == 0x10000032 and section['align'] == 1 and section['entry_size'] == 1
    raw = image.contents(section)
    assert raw and raw.endswith(b'\0')
    assert all(value in raw for value in expected), 'Every original source NUL string must remain present, pooling permitted'
    at = 0
    parts = []
    while at < len(raw):
        end = raw.index(0, at) + 1
        part = raw[at:end]
        source = [value.hex() for value in expected if value.endswith(part)]
        assert source, 'Unknown readonly string bytes require concrete source review'
        parts.append(dict(offset=at, bytes_hex=part.hex(), source_literal_or_suffix_hex=source))
        at = end
    assert not [r for r in image.relocations if r['section'] == section['index']]
    return section, dict(section=dict(section), actual_bytes_hex=raw.hex(), actual_strings=parts,
                         no_unique_physical_pool_count_assumption=True)


def actual_ipi_object_gate(q):
    item, reader, image, evidence = capture(q, 'ipi')
    contract = json.loads(Path(q['source_contract']).read_text())['ipi']
    funcs, function_sections = functions(image, item['expected_T'])
    name = item['expected_data_name']
    data = image.defined[name]
    section = image.sections[data['section']]
    assert data['type'] == 1 and image.kind(data) == 'D' and data['size'] == 32 and data['value'] == 0
    assert section['name'] == '__verbose' and section['type'] == 1 and section['flags'] == 0x200003
    assert section['align'] == 8 and section['size'] == 32
    raw = image.symbol_bytes(data)
    assert raw[16:24] == bytes(8) and int.from_bytes(raw[24:28], 'little') == 3140
    relocs = [r for r in image.relocations if r['section'] == section['index']]
    assert len(relocs) == 2 and {r['offset'] for r in relocs} == {0, 8} and all(r['type'] == 1 for r in relocs)
    by_offset = {r['offset']: r for r in relocs}
    fields = {}
    for field, offset, expected_hex in [('file', 0, contract['filename_hex']), ('func', 8, contract['descriptor_function_hex'])]:
        rel = by_offset[offset]
        target = image.pointer_target(rel, len(bytes.fromhex(expected_hex)))
        assert rel['symbol']['bind'] == 0 and target[2] == bytes.fromhex(expected_hex)
        target_section = image.sections[target[0]]
        assert target_section['name'] == '.lrodata.str1.1' and target_section['flags'] == 0x10000032
        fields[field] = dict(target_section=target[0], target_offset=target[1], exact_NUL_contents_hex=target[2].hex(), relocation=rel)
    readonly, literal_evidence = strings(image, contract)
    code_refs = {}
    for function, allowed_globals in [('x86_issue_ipi_bridge', {'x86_issue_ipi'}),
                                      ('x86_interrupt_log_bridge', {'x86_interrupt_log_debug', 'kprintf', 'ihk_mc_get_processor_id'})]:
        globals_seen = set()
        literal_targets = []
        for rel in funcs[function]['actual_relocations']:
            symbol = rel['symbol']
            if symbol['bind'] == 1:
                assert symbol['name'] in allowed_globals and rel['addend'] == 0
                globals_seen.add(symbol['name'])
            else:
                assert function == 'x86_interrupt_log_bridge' and symbol['bind'] == 0
                assert symbol['section'] == readonly['index']
                pos = symbol['value'] + rel['addend']
                assert 0 <= pos < readonly['size']
                value = image.contents(readonly)
                end = value.index(0, pos) + 1
                actual = value[pos:end]
                assert actual.hex() in contract['logger_literals_hex']
                literal_targets.append(dict(offset=rel['offset'], exact_NUL_contents_hex=actual.hex()))
        assert globals_seen == allowed_globals, 'Complete live logger/real slot references must remain; no initial-disabled assumption'
        code_refs[function] = dict(actual_source_globals=sorted(globals_seen), actual_literal_targets=literal_targets)
    assert {x['exact_NUL_contents_hex'] for x in code_refs['x86_interrupt_log_bridge']['actual_literal_targets']} == set(contract['logger_literals_hex'])
    eh = unwind(image, function_sections)
    allowed_alloc = function_sections | {section['index'], readonly['index'], eh['section']['index']}
    assert {s['index'] for s in image.sections if s['size'] and s['flags'] & 2} == allowed_alloc
    accounted = function_sections | {section['index'], eh['section']['index']}
    assert all(r['section'] in accounted for r in image.relocations), 'Unknown relocation source requires concrete review'
    return dict(status='PASS_CALLED_ACTUAL_IPI_LOGGER_TWO_T_AND_GENUINE32_DESCRIPTOR',
                object_sha256=evidence['object_sha256'], actual_T=sorted(item['expected_T']), genuine_U=sorted(image.undefined),
                actual_data=dict(name=name, bytes=32, alignment=8, section='__verbose', exact_flags='0x200003', line_flags=3140,
                                 fmt_NULL=True, field_relocations=fields, actual_padding_hex=raw[28:32].hex()),
                actual_function_evidence=funcs, actual_code_source_references=code_refs, actual_source_readonly=literal_evidence,
                actual_unwind=eh, capture=item['capture'], source_volatile_guard_late_getter_casts_unchanged=True,
                no_callback_slot_owner_init_target_call_or_logger_runtime=True,
                actual_private_FUNC_OBJECT=[], source_config_scope_only=True)


def actual_local_slot_object_gate(q):
    item, reader, image, evidence = capture(q, 'local')
    funcs, function_sections = functions(image, item['expected_T'])
    name = item['expected_data_name']
    slot = image.defined[name]
    section = image.sections[slot['section']]
    assert slot['type'] == 1 and image.kind(slot) == 'B' and slot['size'] == 8 and slot['value'] == 0
    assert section['name'] == '.bss.x86_issue_ipi' and section['type'] == 8 and section['flags'] == 3
    assert section['align'] == 8 and section['size'] == 8
    assert not [r for r in image.relocations if r['section'] == section['index']], 'Original None slot has no target relocation'
    name = 'get_x86_cpu_local_variable'
    relocs = funcs[name]['actual_relocations']
    assert len(relocs) == 1
    rel = relocs[0]
    assert rel['symbol']['bind'] == 1 and rel['symbol']['name'] == 'locals' and rel['symbol']['section'] == 0 and rel['addend'] == 0
    assert 'locals' not in image.defined
    eh = unwind(image, function_sections)
    allowed_alloc = function_sections | {section['index'], eh['section']['index']}
    assert {s['index'] for s in image.sections if s['size'] and s['flags'] & 2} == allowed_alloc
    accounted = function_sections | {eh['section']['index']}
    assert all(r['section'] in accounted for r in image.relocations)
    return dict(status='PASS_CALLED_ACTUAL_LOCAL_ACCESSOR_AND_ORIGINAL_NONE_SLOT',
                object_sha256=evidence['object_sha256'], actual_T=['get_x86_cpu_local_variable'], genuine_U=['locals'],
                actual_slot=dict(name=item['expected_data_name'], bytes=8, alignment=8, section='.bss.x86_issue_ipi',
                                 NOBITS_declaration_only=True, target_relocations=0, original_None_preboot_only=True),
                actual_function_evidence=funcs, actual_unwind=eh, capture=item['capture'], actual_private_FUNC_OBJECT=[],
                original_inline_local_addr_inlined_no_other_owner=True,
                no_locals_redefinition_fake_mapping_or_runtime_callback_readiness=True,
                no_function_slot_read_call_init_publication_CPUlocal_hardware_or_native_execution=True)
