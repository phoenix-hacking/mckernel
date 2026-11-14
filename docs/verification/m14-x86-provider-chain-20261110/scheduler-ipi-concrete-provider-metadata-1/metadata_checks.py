"""Exact real IPI7 object/source/ABI/owner/content/relocation gate; no loader."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def actual_object_gate(q):
    for path, digest in q['inputs'].items():
        assert sha(path) == digest, path
    review = json.loads(Path(q['source_review']).read_text())
    assert review['decision'] == 'GO_EXACT_SEVEN_FUNCTIONS_TWO_FIXED_DATA_SOURCE_AND_ONE_COMPILE_PROPOSAL_ONLY_SUBJECT_TO_FRESH_ROOT_ADMISSION'
    assert review['request']['path'] == q['source_request']
    assert review['request']['sha256'] == sha(q['source_request'])
    source = json.loads(Path(q['source_manifest']).read_text())
    assert source['actual_abi']['sha256'] == sha(source['actual_abi']['path'])
    produced = json.loads(Path(q['producer_result']).read_text())
    assert produced['status'] == 'PASS_NEXT_FIVE_OBJECT_JOIN_AND_TWO_FIRST_LAPIC_IPI_PRODUCERS'
    assert produced['all_direct_waits_joined'] and produced['CPU6_released']
    rows = [row for row in produced['steps'] if row['label'] == 'concrete-ipi-producer']
    assert len(rows) == 1
    row = rows[0]
    assert row['kind'] == 'compiler' and row['joined'] and row['returncode'] == 0 and row['exact_retained_diagnostics']
    assert (row['object_path'], row['object_sha256'], row['object_bytes']) == (q['compiled_input']['path'], q['compiled_input']['sha256'], q['compiled_input']['bytes'])
    prior = json.loads(Path(q['retained_actual_capture']).read_text())
    assert prior['status'] == 'ACTUAL_EMITTED_METADATA_CAPTURE_ONLY_NOT_OWNERSHIP_GATE_PASS'
    assert prior['object_sha256'] == q['compiled_input']['sha256']
    ref = q['qualified_ELF_reader']
    assert sha(ref['path']) == ref['sha256'] == prior['qualified_reader_sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_storage_ELF_reader_for_concrete_IPI7', ref['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    sections = []
    for section in image.sections:
        entry = dict(section)
        if section['type'] == 8:
            entry['NOBITS_declaration_only'] = True
        elif section['flags'] & 2:
            raw = image.contents(section)
            entry.update(actual_file_bytes_hex=raw.hex(), actual_file_bytes_sha256=hashlib.sha256(raw).hexdigest())
        sections.append(entry)
    capture = dict(status='ACTUAL_CAPTURE_BEFORE_OWNER_GATE_ASSERTIONS_NOT_GO', object_sha256=hashlib.sha256(image.raw).hexdigest(),
                   object_bytes=len(image.raw), symbols=image.symbols, sections=sections, relocations=image.relocations,
                   genuine_U=sorted(image.undefined), no_loader_or_runtime=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(capture, stream, indent=2)
        stream.write('\n')
    assert capture['object_sha256'] == q['compiled_input']['sha256'] and capture['object_bytes'] == q['compiled_input']['bytes']
    assert image.symbols == prior['symbols'] and image.relocations == prior['relocations']
    assert image.defined == prior['defined'] and image.undefined == set(prior['undefined'])
    assert Path(q['actual_elf']).read_bytes(), 'Actual new admitted GNU ELF readback must be retained'
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert set(definitions) == set(image.defined) and imports == image.undefined
    contract = json.loads(Path(q['source_emission_contract']).read_text())
    expected_T, expected_R = set(contract['functions']), set(contract['data'])
    assert expected_T == set(source['exact_functions']) and len(expected_T) == 7
    assert expected_R == {item['name'] for item in source['fixed_data']} and len(expected_R) == 2
    assert set(image.defined) == expected_T | expected_R and len(image.defined) == 9
    assert image.undefined == set(source['genuine_U']) == set(contract['actual_genuine_U']) and len(image.undefined) == 7
    assert 'x86_cpu_pause_bridge' in image.undefined and 'cpu_pause' not in image.undefined
    assert not [s for s in image.symbols if s['bind'] == 0 and s['section'] != 0 and s['type'] in (1, 2)], 'Unexpected emitted private owner; stop for concrete review'
    assert not [s for s in image.sections if s['size'] and s['flags'] & 3 == 3], 'No writable source storage selected'
    owners, function_sections, data_sections = {}, set(), set()
    for name, fields in contract['functions'].items():
        symbol = image.defined[name]
        assert symbol == fields['symbol']
        section = image.sections[symbol['section']]
        assert {k:section[k] for k in fields['section']} == fields['section']
        assert symbol['bind'] == 1 and symbol['type'] == 2 and symbol['other'] & 3 == 0 and image.kind(symbol) == 'T'
        assert symbol['value'] == 0 and section['size'] == symbol['size'] > 0
        assert definitions[name] == dict(kind='T', size=symbol['size'])
        raw = image.symbol_bytes(symbol)
        assert hashlib.sha256(raw).hexdigest() == fields['actual_bytes_sha256']
        relocs = [r for r in image.relocations if r['section'] == symbol['section']]
        summary = [dict(offset=r['offset'], type=r['type'], target=r['symbol']['name'], target_bind=r['symbol']['bind'],
                        target_section=r['symbol']['section'], addend=r['addend']) for r in relocs]
        assert summary == fields['source_global_relocations'], 'Preserve actual source inlining/constant folding/global targets'
        assert all(r['type'] == 1 and r['symbol']['bind'] == 1 and r['symbol']['section'] == 0
                   and r['symbol']['name'] in image.undefined and r['addend'] == 0 for r in relocs)
        function_sections.add(symbol['section'])
        owners[name] = dict(kind='T', bytes=symbol['size'], actual_bytes_hex=raw.hex(), actual_bytes_sha256=hashlib.sha256(raw).hexdigest(),
                            actual_source_global_relocations=summary)
    assert len(function_sections) == 7
    for name, fields in contract['data'].items():
        symbol = image.defined[name]
        assert symbol == fields['symbol']
        section = image.sections[symbol['section']]
        assert {k:section[k] for k in fields['section']} == fields['section']
        assert symbol['bind'] == 1 and symbol['type'] == 1 and symbol['other'] & 3 == 0 and image.kind(symbol) == 'R'
        assert definitions[name] == dict(kind='R', size=symbol['size'])
        assert symbol['value'] == 0 and section['size'] == symbol['size']
        raw = image.symbol_bytes(symbol)
        assert raw.hex() == fields['actual_bytes_hex'] == contract['source_data_values'][name]['bytes_hex']
        assert not [r for r in image.relocations if r['section'] == symbol['section']], 'Original immutable scalar/array have no pointer target relocation'
        if name == 'x86_ipi_icr_id_shift':
            assert len(raw) == 4 and section['align'] == 4 and int.from_bytes(raw, 'little', signed=True) == 24
        else:
            assert name == 'x86_icr_geometry' and len(raw) == 32 and section['align'] == 8
            assert [int.from_bytes(raw[i:i+8], 'little') for i in range(0,32,8)] == [0x830,0x310,0x300,0x1000]
        data_sections.add(symbol['section'])
        owners[name] = dict(kind='R', bytes=symbol['size'], alignment=section['align'], exact_source_contents_hex=raw.hex(), immutable=True)
    assert len(data_sections) == 2
    frames = [s for s in image.sections if s['name'] == '.eh_frame']
    assert len(frames) == 1
    frame = frames[0]
    expected_frame = contract['actual_unwind']
    assert {k:frame[k] for k in expected_frame['section']} == expected_frame['section']
    assert hashlib.sha256(image.contents(frame)).hexdigest() == expected_frame['actual_bytes_sha256']
    frame_relocs = [r for r in image.relocations if r['section'] == frame['index']]
    summary = [dict(offset=r['offset'], type=r['type'], target_section_name=image.sections[r['symbol']['section']]['name'],
                    target_bind=r['symbol']['bind'], target_symbol_type=r['symbol']['type'], target_value=r['symbol']['value'], addend=r['addend']) for r in frame_relocs]
    assert summary == expected_frame['relocations'] and len(frame_relocs) == 7
    assert {r['symbol']['section'] for r in frame_relocs} == function_sections
    assert all(r['type'] == 24 and r['symbol']['bind'] == 0 and r['symbol']['type'] == 3 and r['addend'] == 0 for r in frame_relocs)
    assert {s['index'] for s in image.sections if s['size'] and s['flags'] & 2} == function_sections | data_sections | {frame['index']}
    assert len(image.relocations) == 20 and sum(r['section'] in function_sections for r in image.relocations) == 13
    assert all(r['section'] in function_sections | {frame['index']} for r in image.relocations)
    return dict(status='PASS_CALLED_ACTUAL_CONCRETE_IPI7_TWO_GENUINE_FIXED_RO_OWNERS',
                object_sha256=capture['object_sha256'], object_bytes=capture['object_bytes'], actual_global_T=7,
                actual_global_R=2, actual_genuine_U=sorted(image.undefined), actual_source_owners=owners,
                actual_unwind=dict(section=dict(frame), source_relocations=summary), actual_private_FUNC_OBJECT=[],
                immutable_geometry_and_shift_exact=True, legitimate_source_constant_folding_and_entry_inlining_preserved=True,
                no_cpu_pause_alias_or_backend_slot_owner=True, new_capture=q['actual_metadata_capture'],
                future_current_join_unbound=True, no_runtime_hardware_IRQ_APIC_MSR_callback_publication_or_native_acceptance=True)
