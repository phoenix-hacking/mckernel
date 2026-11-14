"""Finite actual timer/vector3 object gate; no compiler/link/runtime."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys


def actual_object_gate(q):
    for path, digest in q['source_bindings'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    reader_item = q['qualified_ELF_reader']
    assert hashlib.sha256(Path(reader_item['path']).read_bytes()).hexdigest() == reader_item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_ELF_reader_for_timer_vector', reader_item['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    contract = json.loads(Path(q['source_emission_contract']).read_text())
    relocation_bindings = json.loads(Path(q['relocation_source_bindings']).read_text())
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes()
    sections = []
    for section in image.sections:
        entry = dict(section)
        if section['type'] == 8:
            entry['NOBITS_declaration_only'] = True
        elif section['flags'] & 2:
            entry['actual_file_bytes_hex'] = image.contents(section).hex()
            entry['actual_file_bytes_sha256'] = hashlib.sha256(image.contents(section)).hexdigest()
        sections.append(entry)
    capture = dict(object_sha256=hashlib.sha256(image.raw).hexdigest(), object_bytes=len(image.raw),
                   symbols=image.symbols, sections=sections, relocations=image.relocations,
                   genuine_U=sorted(image.undefined), no_timer_vector_function_execution=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(capture,stream,indent=2)
        stream.write('\n')
    assert capture['object_sha256'] == q['compiled_input']['sha256'] and capture['object_bytes'] == q['compiled_input']['bytes']
    assert set(definitions) == set(image.defined) == set(contract['required3_T'])
    assert imports == image.undefined == set(contract['genuine7_U']), ('Unexpected source/intrinsic import; stop before future link', sorted(image.undefined))
    assert set(contract['all4_timer_callbacks_U']) <= image.undefined
    assert {contract['external_descriptor'], contract['external_mutable_state']} <= image.undefined
    functions = []
    labels = {}
    for symbol in image.symbols:
        if symbol['type'] != 2 or symbol['section'] == 0:
            continue
        if symbol['bind'] == 1:
            assert symbol['name'] in contract['required3_T']
            label = symbol['name']
        else:
            matches = [name for name, pattern in contract['private_helper_patterns'].items() if re.fullmatch(pattern, symbol['name'])]
            assert symbol['bind'] == 0 and len(matches) == 1, ('Unreviewed private/core helper', symbol['name'])
            label = matches[0]
        assert symbol['size'] > 0 and symbol['other'] & 3 == 0 and image.kind(symbol) == 'T'
        labels[symbol['name']] = label
        functions.append(symbol)
    for name,symbol in image.defined.items():
        assert definitions[name] == {'kind':'T','size':symbol['size']}
    assert not [symbol for symbol in image.symbols if symbol['type'] == 1 and symbol['section'] != 0], 'No source data/descriptor/time-sharing instance selected'
    assert not [section for section in image.sections if section['flags'] & 3 == 3 and section['size']], 'No writable allocated source state selected'
    def owners(section,position):
        result = [symbol['name'] for symbol in functions if symbol['section']==section and symbol['value'] <= position < symbol['value']+symbol['size']]
        assert result, 'Actual relocation must belong to selected source function/helper'
        return result
    readonly = []
    for section in image.sections:
        if not section['size'] or not section['flags'] & 2 or section['flags'] & 5:
            continue
        assert section['name']=='.eh_frame' and section['type']==0x70000001 and section['flags']==2 and section['align']==8, ('Unreviewed readonly/offset/callback table; retained actual emission requires review',section['name'],section['size'])
        rows = [row for row in image.relocations if row['section']==section['index']]
        assert rows
        assert rows == [item['actual_relocation'] for item in relocation_bindings['actual_unwind3_PC64_edges']], 'Exact retained source-owned PC64 unwind edges'
        references = []
        for row in rows:
            target = row['symbol']
            references.append(dict(actual_relocation=row,source_functions=owners(target['section'],target['value']+row['addend'])))
        readonly.append(dict(kind='retained_profile_unwind_for_selected_source_only',name=section['name'],bytes=section['size'],actual_source_references=references))
    # One reviewed correction: exact retained R64 edges, including ONLY the
    # actual source-used descriptor members. No arbitrary addends or all-field
    # allowlist; offsets are addresses within the genuine external descriptor.
    descriptor_fields = contract['descriptor_fields_in_original_order']
    assert descriptor_fields == relocation_bindings['full_original15_descriptor_fields']
    exact_by_owner = {}
    for binding in relocation_bindings['actual_set_timer17_R64_edges']:
        member = binding.get('descriptor_member')
        if member is not None:
            index = descriptor_fields.index(member['field_name'])
            assert index == member['ordinal_in_original15']
            assert member['declared_type'] == 'usize' and member['selected_LP64_usize_bytes'] == 8
            assert binding['addend'] == member['member_byte_offset'] == index * 8
            assert binding['target_symbol'] == contract['external_descriptor']
        else:
            assert binding['addend'] == 0 and binding['target_symbol'] in contract['genuine7_U']
        exact_by_owner.setdefault(binding['owner'], []).append((binding['relative_offset'], binding['target_symbol'], binding['symbol_bind'], binding['symbol_type'], binding['symbol_section'], binding['relocation_type'], binding['addend']))
    function_evidence = {}
    public_targets = {}
    for symbol in functions:
        rows = [row for row in image.relocations if row['section']==symbol['section'] and symbol['value'] <= row['offset'] < symbol['value']+symbol['size']]
        targets = [row['symbol']['name'] for row in rows if row['symbol']['bind']==1]
        label = labels[symbol['name']]
        if label=='set_timer':
            assert set(contract['genuine7_U']) <= set(targets), ('Actual CPU/state/offset/four-callback address binding',targets)
            assert set(targets) <= set(contract['genuine7_U']) | {'timer_set_timer_body_result'}
        elif label in ['timer_set_timer_body_result','ihk_mc_get_vector']:
            assert not targets, ('Unexpected direct project provider from source-body/vector',label,targets)
        else:
            assert label in contract['source_private_functions'] and not targets
        actual_edges = [(row['offset']-symbol['value'], row['symbol']['name'], row['symbol']['bind'], row['symbol']['type'], row['symbol']['section'], row['type'], row['addend']) for row in rows]
        assert actual_edges == exact_by_owner.get(label, []), ('Exact actual source-use/member-address relocation binding', label, actual_edges)
        function_evidence[symbol['name']] = dict(source_owner=label,bytes=symbol['size'],bytes_sha256=hashlib.sha256(image.symbol_bytes(symbol)).hexdigest(),actual_source_relocations=rows)
        if symbol['bind']==1:
            public_targets[symbol['name']]=targets
    return dict(status='PASS_CALLED_ACTUAL_TIMER_VECTOR3_SOURCE_OBJECT_GATE', object_sha256=capture['object_sha256'],
                actual3T={name:image.defined[name]['size'] for name in sorted(image.defined)}, genuine7U=sorted(image.undefined),
                all4_timer_callback_addresses_remain_genuine_U=contract['all4_timer_callbacks_U'],
                original_descriptor_and_time_sharing_remain_genuine_U=True, no_data_or_synthetic_offsets_instance=True,
                actual_function_and_private_listhelper_owners=function_evidence, actual_source_unwind=readonly,
                actual_set_timer_CPU_state_descriptor_callback_bindings=public_targets['set_timer'],
                actual_descriptor_member_address_bindings=relocation_bindings,
                actual_metadata_capture=q['actual_metadata_capture'], future_actual_partial_join_unbound=True,
                no_timer_vector_list_lock_IRQ_cpu_native_function_runtime=True)
