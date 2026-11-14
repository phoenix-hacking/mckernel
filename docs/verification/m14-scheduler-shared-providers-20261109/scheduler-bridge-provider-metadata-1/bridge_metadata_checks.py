"""Finite actual ten-bridge metadata/source-owner gate; qualified ELF reader only."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys


def actual_object_gate(q):
    for path, digest in q['source_bindings'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    item = q['qualified_ELF_reader']
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_ELF_reader_for_ten_scheduler_bridges', item['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    contract = json.loads(Path(q['source_emission_contract']).read_text())
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes(), 'Actual admitted ELF readback must be retained'
    # Keep ALL actual metadata, including unexpected owners, before source checks.
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
    assert set(definitions) == set(image.defined) and imports == image.undefined
    assert set(image.defined) == set(contract['required10_C_exports']), 'Unreviewed global owner: stop before future link'
    assert image.undefined == set(contract['genuine12_U']), ('Unreviewed source/intrinsic U: stop before future link', sorted(image.undefined))
    functions = []
    for symbol in image.symbols:
        if symbol['section'] == 0 or symbol['type'] != 2:
            continue
        if symbol['bind'] == 1:
            assert symbol['name'] in contract['required10_C_exports']
        else:
            # The compiler disambiguator varies; the complete source path and
            # sole helper identifier are exact, not wildcard source ownership.
            assert symbol['bind'] == 0 and re.fullmatch(contract['source_private_helper_raw_v0_pattern'], symbol['name']), ('Unreviewed private/core FUNC', symbol['name'])
        assert symbol['size'] > 0 and symbol['other'] & 3 == 0 and image.kind(symbol) == 'T'
        functions.append(symbol)
    for name, symbol in image.defined.items():
        assert definitions[name] == {'kind': 'T', 'size': symbol['size']}
    assert not [section for section in image.sections if section['flags'] & 3 == 3 and section['size']], 'No writable source state selected'
    def code_owners(section, offset):
        names = sorted(symbol['name'] for symbol in functions if symbol['section'] == section and symbol['value'] <= offset < symbol['value'] + symbol['size'])
        assert names, 'Actual code relocation must belong to selected public/helper source'
        return names
    def owner_label(name):
        return name if name in contract['required10_C_exports'] else contract['source_private_helper']
    literals = [bytes.fromhex(value) for value in contract['source_string_literals_hex']]
    def source_string(value):
        matches = [literal.hex() for literal in literals if literal.endswith(value)]
        assert matches, ('Unreviewed literal bytes', value.hex())
        return matches
    readonly = {}
    for section in image.sections:
        if not section['size'] or not section['flags'] & 2 or section['flags'] & 5:
            continue
        raw = image.contents(section)
        relocs = [row for row in image.relocations if row['section'] == section['index']]
        incoming = [row for row in image.relocations if row['symbol']['section'] == section['index']]
        evidence = dict(name=section['name'], bytes=section['size'], sha256=hashlib.sha256(raw).hexdigest())
        if section['name'] == '.eh_frame':
            assert section['type'] == 0x70000001 and section['flags'] == 2 and section['align'] == 8
            targets = []
            for row in relocs:
                symbol = row['symbol']
                assert 0 < symbol['section'] < len(image.sections)
                targets.append(code_owners(symbol['section'], symbol['value'] + row['addend']))
            assert targets
            evidence.update(kind='retained_profile_unwind_for_exact_source_functions', targets=targets)
        elif section['type'] == 1 and section['flags'] & 0x20:
            assert section['entry_size'] == 1 and not relocs and raw.endswith(b'\0')
            source_literals = []
            position = 0
            while position < len(raw):
                end = raw.index(0, position) + 1
                value = raw[position:end]
                source_literals.append(dict(offset=position, bytes_hex=value.hex(), exact_source_literal_or_merged_suffix=source_string(value)))
                position = end
            assert incoming, 'No unbound readonly string storage'
            sources = []
            for row in incoming:
                assert row['type'] == 1
                position = row['symbol']['value'] + row['addend']
                assert 0 <= position < len(raw)
                end = raw.index(0, position) + 1
                source_string(raw[position:end])
                owners = code_owners(row['section'], row['offset'])
                assert all(owner_label(name) == contract['logger'] for name in owners)
                sources.append(dict(source_functions=owners, actual_string_offset=position))
            evidence.update(kind='exact_original_logger_format_label_strings', source_literals=source_literals, incoming_source_functions=sources)
        elif section['type'] == 1 and relocs:
            # Selected switch lowering may emit ONLY a complete array of
            # native pointers back into this one full 11-event logger body.
            assert section['size'] % 8 == 0 and len(relocs) == section['size'] // 8 and raw == bytes(len(raw))
            assert sorted(row['offset'] for row in relocs) == list(range(0, section['size'], 8))
            targets = []
            for row in relocs:
                assert row['type'] == 1
                symbol = row['symbol']
                owners = code_owners(symbol['section'], symbol['value'] + row['addend'])
                assert owners == [contract['logger']]
                targets.append(dict(source_functions=owners, source_code_offset=symbol['value'] + row['addend'], actual_table_offset=row['offset']))
            assert incoming
            for row in incoming:
                assert row['type'] == 1
                owners = code_owners(row['section'], row['offset'])
                assert owners == [contract['logger']]
            evidence.update(kind='compiler_switch_table_owned_only_by_complete_source_logger', targets=targets)
        else:
            raise AssertionError(('Unreviewed readonly/private emission: retain and stop before future link', section['name'], section['size']))
        readonly[section['index']] = evidence
    private_data = []
    for symbol in image.symbols:
        if symbol['section'] == 0 or symbol['type'] != 1:
            continue
        assert symbol['bind'] == 0 and symbol['section'] in readonly
        section = image.sections[symbol['section']]
        assert symbol['value'] + symbol['size'] <= section['size']
        assert readonly[symbol['section']]['kind'] != 'retained_profile_unwind_for_exact_source_functions'
        private_data.append(dict(symbol=symbol, source_readonly_evidence=readonly[symbol['section']], bytes_sha256=hashlib.sha256(image.symbol_bytes(symbol)).hexdigest()))
    function_evidence = {}
    for symbol in functions:
        rows = [row for row in image.relocations if row['section'] == symbol['section'] and symbol['value'] <= row['offset'] < symbol['value'] + symbol['size']]
        global_targets = [row['symbol']['name'] for row in rows if row['symbol']['bind'] == 1]
        label = owner_label(symbol['name'])
        if label in contract['source_wrapper_imports']:
            assert global_targets == [contract['source_wrapper_imports'][label]], ('Wrapper genuine callee binding', label, global_targets)
        elif label == 'enabled':
            assert global_targets == [contract['real_external_metadata_array']]
        else:
            assert label == contract['logger'] and {'kprintf', 'ihk_mc_get_processor_id'} <= set(global_targets)
            assert set(global_targets) <= {'kprintf', 'ihk_mc_get_processor_id', contract['real_external_metadata_array']}
        function_evidence[symbol['name']] = dict(bytes=symbol['size'], bytes_sha256=hashlib.sha256(image.symbol_bytes(symbol)).hexdigest(), source_owner=label, actual_relocations=rows)
    return dict(status='PASS_CALLED_FINITE_TEN_SCHEDULER_BRIDGE_SOURCE_OBJECT_GATE',
                object_sha256=capture['object_sha256'], actual10T={name:image.defined[name]['size'] for name in sorted(image.defined)},
                genuine12U=sorted(image.undefined), function_owners=function_evidence,
                exact_source_readonly_sections=list(readonly.values()), source_private_readonly_data=private_data,
                actual_external18_Ddebug_array_is_U_not_defined=contract['real_external_metadata_array'] in image.undefined,
                all_actual_metadata_retained=q['actual_metadata_capture'], future_engine_partial_and_join_unbound=True,
                no_function_logging_selector_lock_timer_IRQ_native_runtime=True)
