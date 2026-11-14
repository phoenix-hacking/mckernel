"""Finite actual two-data source/ELF/initializer/owner gate; no C guard execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def actual_object_gate(q):
    for path, digest in q['inputs'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    contract = json.loads(Path(q['data_source_contract']).read_text())
    unit = Path(q['source_unit']).read_bytes()
    for block in contract['source_blocks']:
        lines = Path(block['source_path']).read_bytes().splitlines(keepends=True)
        raw = b''.join(lines[block['first_line']-1:block['last_line']])
        assert hashlib.sha256(raw).hexdigest() == block['source_sha256'] and raw == block['source_bytes'].encode()
        offset = block['unit_byte_offset']
        assert unit[offset:offset+len(raw)] == raw
    for item in contract['guard_context_evidence']:
        lines = Path(item['path']).read_bytes().splitlines(keepends=True)
        raw = b''.join(lines[item['first_line']-1:item['last_line']])
        assert hashlib.sha256(raw).hexdigest() == item['sha256'] and raw == item['exact_source'].encode(), item['role']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_reader_for_backend_data', q['qualified_ELF_reader']['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes()
    retained = json.loads(Path(q['retained_actual_capture']).read_text())
    actual = dict(object_sha256=hashlib.sha256(image.raw).hexdigest(), object_bytes=len(image.raw), symbols=image.symbols, sections=image.sections,
                  defined=image.defined, undefined=sorted(image.undefined), relocations=image.relocations,
                  allocated_file_bytes={s['name']:image.contents(s).hex() for s in image.sections if s['size'] and s['flags'] & 2 and s['type'] != 8},
                  NOBITS_is_declaration_not_runtime_mapping=True, C_guard_not_processed=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(actual, stream, indent=2)
        stream.write('\n')
    assert actual['object_sha256'] == q['compiled_input']['sha256'] == retained['object_sha256'] and actual['object_bytes'] == retained['object_bytes'] == 896
    assert image.symbols == retained['symbols'] and image.defined == retained['defined']
    expected_sections = [{k:v for k,v in s.items() if k not in ('actual_file_bytes_hex', 'NOBITS_declaration_only_not_runtime_init')} for s in retained['sections']]
    assert image.sections == expected_sections
    assert set(image.defined) == set(definitions) == set(contract['expected_globals']) == {'lapic_vp', 'x86_local_apic_base_msr'}
    assert image.undefined == imports == set() and retained['undefined'] == []
    assert image.relocations == retained['relocations'] == []
    owners = [s for s in image.symbols if s['type'] in (1, 2) and s['section'] != 0]
    assert len(owners) == 2 and all(s['type'] == 1 and s['bind'] == 1 and s['other'] & 3 == 0 for s in owners), 'Only two genuine original dataowners/no private/function/literal'
    allocated = set()
    for name, expected in contract['expected_globals'].items():
        symbol = image.defined[name]
        section = image.sections[symbol['section']]
        assert (symbol['type'], symbol['size'], symbol['value'], symbol['section'], image.kind(symbol)) == (expected['type'], expected['size'], expected['value'], expected['section_index'], expected['kind'])
        assert definitions[name] == {'kind':expected['kind'], 'size':expected['size']}
        assert (section['name'], section['type'], section['flags'], section['align'], section['size']) == (expected['section_name'], expected['section_type'], expected['section_flags'], expected['section_align'], expected['size'])
        allocated.add(section['index'])
    readonly = image.symbol_bytes(image.defined['x86_local_apic_base_msr'])
    assert readonly.hex() == contract['expected_globals']['x86_local_apic_base_msr']['actual_LE_bytes_hex'] and int.from_bytes(readonly, 'little') == int('0x800', 16), 'Original real scalar bytes/type/sourcevalue'
    assert {s['index'] for s in image.sections if s['size'] and s['flags'] & 2} == allocated, 'No extra state/readonly/unwind/code'
    assert 'mapped_local_apic' not in image.defined and 'lapic_virtpage' not in image.defined
    return dict(status='PASS_CALLED_ACTUAL_TWO_ORIGINAL_BACKEND_DATA_CONTENT_OWNER_GATE', object_sha256=actual['object_sha256'],
                T=0, genuine_U=[], relocations=[], private_or_extra_readonly_owners=[],
                data_owners=contract['expected_globals'], lapic_vp_original_NULL_NOBITS_declaration_not_mapping=True,
                actual_immutable_CUInt0x800_bytes='00080000', original_source_alias_direction_preserved=True,
                actual_source_C_macro_owner_staticguard_context_bound=True, C_guard_processing_or_PASS=False,
                original_real_header_object_equality_C_duplicate_owner_and_live_mapping_requirements_OPEN=True,
                future_current_cohort_join_UNBOUND=True, actual_metadata_capture=q['actual_metadata_capture'],
                no_function_boot_slot_mapping_MSR_controller_IRQ_native_execution=True)
