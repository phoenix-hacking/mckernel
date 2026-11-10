"""Actual5T target/RDMSR source, ABI, owner, code and relocation gate; no loader."""
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
    assert review['decision'] == 'GO_EXACT_FIVE_T_SOURCE_AND_ONE_LITERAL_COMPILE_PROPOSAL_ONLY_SUBJECT_TO_FRESH_ROOT_ADMISSION'
    assert review['request']['path'] == q['source_request'] and review['request']['sha256'] == sha(q['source_request'])
    source = json.loads(Path(q['source_manifest']).read_text())
    assert sha(source['actual_abi']['path']) == source['actual_abi']['sha256']
    assert source['new_data_or_constants'] == [] and source['runtime_private_helpers'] == []
    produced = json.loads(Path(q['producer_result']).read_text())
    assert produced['status'] == 'PASS_FIRST_FIVE_TARGET_AND_RDMSR_PRODUCER'
    assert produced['joined'] and produced['returncode'] == 0 and produced['exact_retained_diagnostics'] and produced['CPU6_released']
    assert (produced['object_path'], produced['object_sha256'], produced['object_bytes']) == (q['compiled_input']['path'], q['compiled_input']['sha256'], q['compiled_input']['bytes'])
    prior = json.loads(Path(q['retained_actual_capture']).read_text())
    assert prior['status'] == 'ACTUAL_EMISSION_CAPTURE_ONLY_NOT_OWNER_GATE_OR_RUNTIME_PASS'
    assert prior['object_sha256'] == q['compiled_input']['sha256']
    item = q['qualified_ELF_reader']
    assert sha(item['path']) == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_storage_ELF_for_callback_target5', item['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    sections = []
    for section in image.sections:
        row = dict(section)
        if section['type'] == 8:
            row['NOBITS_declaration_only'] = True
        elif section['flags'] & 2:
            content = image.contents(section)
            row.update(actual_file_bytes_hex=content.hex(), actual_file_bytes_sha256=hashlib.sha256(content).hexdigest())
        sections.append(row)
    capture = dict(status='ACTUAL_NEW_CAPTURE_BEFORE_OWNER_ASSERTIONS_NOT_PASS', object_sha256=hashlib.sha256(image.raw).hexdigest(),
                   object_bytes=len(image.raw), symbols=image.symbols, sections=sections, relocations=image.relocations,
                   genuine_U=sorted(image.undefined), no_loader_or_runtime=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(capture, stream, indent=2)
        stream.write('\n')
    assert capture['object_sha256'] == q['compiled_input']['sha256'] and capture['object_bytes'] == q['compiled_input']['bytes']
    assert image.symbols == prior['symbols'] and image.relocations == prior['relocations'] and image.defined == prior['defined']
    assert image.undefined == set(prior['undefined'])
    assert Path(q['actual_elf']).read_bytes(), 'Retain actual newly admitted GNU ELF readback'
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert set(definitions) == set(image.defined) and imports == image.undefined
    contract = json.loads(Path(q['source_emission_contract']).read_text())
    assert set(image.defined) == set(source['functions']) == set(contract['functions']) and len(image.defined) == 5
    assert image.undefined == set(contract['actual_genuine_U']) == {'lapic_vp', 'wrmsr', 'x86_local_apic_base_msr'}
    assert 'mapped_local_apic' not in image.undefined, 'Preserve original link_name direction; never invent reverse alias'
    assert all(s['type'] == 2 and s['bind'] == 1 and s['other'] & 3 == 0 for s in image.defined.values())
    assert not [s for s in image.symbols if s['bind'] == 0 and s['section'] != 0 and s['type'] in (1,2)], 'Unexpected emitted private owner requires concrete review'
    assert not [s for s in image.sections if s['size'] and s['flags'] & 3 == 3], 'No new writable storage is selected'
    functions, function_sections = {}, set()
    for name, fact in contract['functions'].items():
        symbol = image.defined[name]
        assert symbol == fact['symbol'] and image.kind(symbol) == 'T'
        section = image.sections[symbol['section']]
        assert {k:section[k] for k in fact['section']} == fact['section']
        assert symbol['value'] == 0 and section['size'] == symbol['size'] > 0
        assert definitions[name] == dict(kind='T', size=symbol['size'])
        content = image.symbol_bytes(symbol)
        assert content.hex() == fact['actual_code_hex'] and hashlib.sha256(content).hexdigest() == fact['actual_code_sha256']
        relocs = [r for r in image.relocations if r['section'] == symbol['section']]
        summary = [dict(offset=r['offset'], type=r['type'], target=r['symbol']['name'], target_bind=r['symbol']['bind'],
                        target_section=r['symbol']['section'], addend=r['addend']) for r in relocs]
        assert summary == fact['actual_source_relocations'], 'Preserve actual source data binding, signed-offset/MMIO and WRMSR boundary'
        functions[name] = dict(symbol=symbol, section=dict(section), actual_code_hex=content.hex(),
                               actual_code_sha256=hashlib.sha256(content).hexdigest(), actual_source_relocations=summary)
        function_sections.add(symbol['section'])
    assert len(function_sections) == 5
    frames = [s for s in image.sections if s['name'] == '.eh_frame']
    assert len(frames) == 1
    frame = frames[0]
    fact = contract['actual_unwind']
    assert {k:frame[k] for k in fact['section']} == fact['section']
    content = image.contents(frame)
    assert content.hex() == fact['actual_code_hex'] and hashlib.sha256(content).hexdigest() == fact['actual_code_sha256']
    relocs = [r for r in image.relocations if r['section'] == frame['index']]
    summary = [dict(offset=r['offset'], type=r['type'], target_section_name=image.sections[r['symbol']['section']]['name'],
                    target_bind=r['symbol']['bind'], target_type=r['symbol']['type'], target_value=r['symbol']['value'], addend=r['addend']) for r in relocs]
    assert summary == fact['source_relocations'] and {r['symbol']['section'] for r in relocs} == function_sections
    assert {s['index'] for s in image.sections if s['size'] and s['flags'] & 2} == function_sections | {frame['index']}
    assert len(image.relocations) == contract['actual_relocation_counts']['total']
    assert sum(r['section'] in function_sections for r in image.relocations) == contract['actual_relocation_counts']['function']
    assert len(relocs) == contract['actual_relocation_counts']['unwind']
    assert all(r['section'] in function_sections | {frame['index']} for r in image.relocations)
    return dict(status='PASS_CALLED_ACTUAL_FIVE_CALLBACK_TARGET_RDMSR_SOURCE_OWNER_CONTENT_RELOCATION_GATE',
                object_sha256=capture['object_sha256'], object_bytes=capture['object_bytes'], actual_global_T=5,
                actual_new_data=[], actual_private_FUNC_OBJECT=[], actual_genuine_U=sorted(image.undefined),
                actual_functions=functions, actual_unwind=dict(section=dict(frame), source_relocations=summary),
                source_MMIO_volatile_signed_offset_RDMSR_asm_and_casts_unchanged=True,
                actual_original_link_name_lapic_vp=True, public_RDMSR_and_inlined_x2_read_preserved=True,
                WRMSR_genuine_U_no_owner_copy_or_alias=True, actual_source_observations=contract['actual_source_code_observations'],
                actual_new_capture=q['actual_metadata_capture'], retained_raw_capture_immutable=True,
                future_current_join_unbound=True, no_MMIO_MSR_function_fixture_publication_hardware_native_or_runtime_execution=True)
