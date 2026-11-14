"""One exact current76 + genuine3primitive + genuine18record data partial join."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualified(q):
    item = q['qualified_lock_relocation_helpers']
    assert sha(item['path']) == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_lock_owner_helpers_for_debug18_join', item['path'])
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    base = helpers.helpers(q)
    return helpers, base, base.reader(q)


def source_qualified(q):
    proof = q['actual_qualification']
    prior = json.loads(Path(proof['base_result']).read_text())
    assert prior['status'] == 'PASS_ACTUAL_CURRENT_ENGINE_PLUS_ONLY_QUALIFIED_TEN_BRIDGES'
    assert prior['actual_joined_object_sha256'] == q['object_inputs'][0]['sha256']
    assert prior['actual_postjoin_called'] and prior['all3_direct_waits_joined']
    primitive = json.loads(Path(proof['primitive_gate']).read_text())
    execution = json.loads(Path(proof['primitive_execution']).read_text())
    assert primitive['status'] == 'PASS_CALLED_ACTUAL_THREE_PRIMITIVES_ATOMIC_AND_DELEGATE_METADATA'
    assert primitive['object_sha256'] == q['object_inputs'][1]['sha256']
    assert execution['object_gate_called'] and execution['all_started_children_joined']
    data = json.loads(Path(proof['data_gate']).read_text())
    correction = json.loads(Path(proof['data_root_result']).read_text())
    assert data['status'] == 'PASS_CALLED_EXACT18_SCHEDULER_DEBUG_DATA_OBJECT_GATE'
    assert data['object_sha256'] == q['object_inputs'][2]['sha256']
    assert correction['status'] == 'PASS_ONE_CORRECTED_GATE_CALL_ON_RETAINED_ACTUAL_DATA'
    assert correction['actual_gate_called'] and correction['all_q_input_hashes_verified']
    assert correction['compiler_GNUmetadata_link_or_runtime_commands'] == 0
    assert len(data['actual_records']) == 18 and data['pointer_field_relocations'] == 36
    return primitive, data


def images(q, reader):
    return [reader.Image(item['path']) for item in q['object_inputs']]


def alias(image, names):
    assert len({(image.defined[name]['section'], image.defined[name]['value'], image.defined[name]['size']) for name in names}) == 1


def prejoin(q):
    assert q['status'] == 'READY_EXACT_THREE_OPERAND_CURRENT76_PRIMITIVE3_DEBUG18_JOIN_PENDING_REVIEW_ROOT_ADMISSION'
    for path, digest in q['inputs'].items():
        assert sha(path) == digest, path
    primitive, data = source_qualified(q)
    helpers, base, reader = qualified(q)
    originals = images(q, reader)
    owners = set()
    imports = set()
    for item, image in zip(q['object_inputs'], originals):
        assert sha(item['path']) == item['sha256']
        base.check_nm(reader, image, item['actual_nm'])
        assert set(image.defined) == set(item['actual_definitions'])
        assert image.undefined == set(item['actual_U'])
        for name, fields in item['actual_definitions'].items():
            symbol = image.defined[name]
            assert dict(kind=image.kind(symbol), size=symbol['size']) == fields
        assert not (owners & set(image.defined)), 'Duplicate strong source owner before ld-r'
        owners |= set(image.defined)
        imports |= image.undefined
    old, atomic, descriptors = originals
    assert len(old.defined) == 76 and len(atomic.defined) == 3 and len(descriptors.defined) == 1
    assert set(atomic.defined) == set(primitive['actual3T'])
    assert set(descriptors.defined) == {data['global_OBJECT']['name']}
    assert len(owners) == 80
    prospective = imports - owners
    assert prospective == set(q['actual_prospective_U']) and len(prospective) == 15
    assert sum(image.kind(symbol) == 'T' for image in originals for symbol in image.defined.values()) == 68
    for name, size in q['old2LOCAL_helpers'].items():
        assert base.local(old, name)['size'] == size
    singleton = helpers.private_object(old, q['original_LOCAL_KMSG_LOCK'])
    assert singleton['size'] == 4 and old.kind(singleton) == 'B'
    alias(old, q['delay_alias'])
    # Both original selected descriptors and the new exact array carry the SAME
    # retained writable section flag set. No merge flag union/waiver is selected.
    for image in (old, descriptors):
        sections = [section for section in image.sections if section['name'] == '__verbose']
        assert len(sections) == 1
        assert sections[0]['type'] == 1 and sections[0]['flags'] == 0x200003 and sections[0]['align'] == 8
    return dict(status='PASS_CALLED_EXACT_THREE_OPERAND_NO_COLLISION_PREJOIN', predicate_called_before_ld_r=True,
                actual_inputs=[dict(path=item['path'], sha256=item['sha256']) for item in q['object_inputs']],
                prior_global=76, primitive_global_T=3, new_global_data=1, actual_global_union=80,
                actual_prospective_T=68, actual_prospective_data=12, actual_prospective_genuine_U=sorted(prospective),
                duplicate_strong_owners=[], exact_input_verbose_flags='0x200003',
                qualified_metadata_consumed_without_gate_or_GNU_readback_replay=True)


def retain_capture(q, image):
    sections = []
    for section in image.sections:
        item = dict(section)
        if section['type'] == 8:
            item['NOBITS_declaration_only'] = True
        elif section['flags'] & 2:
            raw = image.contents(section)
            item.update(actual_file_bytes_hex=raw.hex(), actual_file_bytes_sha256=hashlib.sha256(raw).hexdigest())
        sections.append(item)
    capture = dict(object_sha256=sha(q['joined_object']), symbols=image.symbols, sections=sections,
                   relocations=image.relocations, genuine_U=sorted(image.undefined), no_loader_or_runtime=True)
    with Path(q['joined_capture']).open('x') as stream:
        json.dump(capture, stream, indent=2)
        stream.write('\n')
    return capture


def data_fields(q, joined):
    contract = json.loads(Path(q['debug18_source_contract']).read_text())
    name = contract['name']
    symbol = joined.defined[name]
    section = joined.sections[symbol['section']]
    assert symbol['type'] == 1 and symbol['bind'] == 1 and symbol['other'] & 3 == 0 and symbol['size'] == 576
    assert section['name'] == '__verbose' and section['type'] == 1 and section['flags'] == 0x200003
    assert section['align'] == 8 and symbol['value'] % 8 == 0
    raw = joined.symbol_bytes(symbol)
    relocs = [r for r in joined.relocations if r['section'] == symbol['section'] and symbol['value'] <= r['offset'] < symbol['value'] + 576]
    assert len(relocs) == 36 and all(r['type'] == 1 for r in relocs)
    by_offset = {r['offset'] - symbol['value']: r for r in relocs}
    assert set(by_offset) == {32*i + field for i in range(18) for field in (0,8)}
    rows = []
    for index, record in enumerate(contract['records']):
        at = index * 32
        assert raw[at+16:at+24] == bytes(8)
        value = int.from_bytes(raw[at+24:at+28], 'little')
        assert value == record['line'] | (1 << 24)
        targets = {}
        for field, offset, value_hex in [('file',0,contract['file_nul_hex']),('func',8,record['function_nul_hex'])]:
            relocation = by_offset[at+offset]
            target = joined.pointer_target(relocation, len(bytes.fromhex(value_hex)))
            assert target[2] == bytes.fromhex(value_hex)
            target_section = joined.sections[target[0]]
            assert target_section['flags'] & 2 and not target_section['flags'] & 5
            assert relocation['symbol']['bind'] == 0
            targets[field] = dict(actual_section=target[0], actual_offset=target[1], exact_NUL_contents_hex=target[2].hex())
        rows.append(dict(index=index, actual_line_flags=value, fmt_NULL=True, targets=targets,
                         actual_trailing_ABI_padding_hex=raw[at+28:at+32].hex()))
    return dict(name=name, records=rows, field_relocations=36, flags='0x200003', no_pool_count_or_padding_value_assumption=True)


def postjoin(q):
    primitive, data = source_qualified(q)
    helpers, base, reader = qualified(q)
    originals = images(q, reader)
    joined = reader.Image(q['joined_object'])
    capture = retain_capture(q, joined)
    base.check_nm(reader, joined, q['joined_nm'])
    assert Path(q['joined_elf']).read_bytes()
    expected = set().union(*(set(image.defined) for image in originals))
    prospective = set().union(*(image.undefined for image in originals)) - expected
    assert set(joined.defined) == expected and len(expected) == 80
    assert joined.undefined == prospective == set(q['actual_prospective_U']) and len(prospective) == 15
    assert sum(joined.kind(s) == 'T' for s in joined.defined.values()) == 68
    assert sum(joined.kind(s) != 'T' for s in joined.defined.values()) == 12
    ownership, relocations = {}, {}
    private_functions = set()
    private_data = set()
    for original in originals:
        for name, before in original.defined.items():
            after = joined.defined[name]
            ownership[name] = base.compare_owner(original, before, joined, after)
            first = helpers.owner_relocations(base, original, before)
            second = helpers.owner_relocations(base, joined, after)
            assert first == second, ('Source relocation changed', name)
            relocations[name] = second
        for before in original.symbols:
            if before['bind'] != 0 or before['section'] == 0 or before['type'] not in (1,2):
                continue
            name = before['name']
            if before['type'] == 2:
                assert name not in private_functions
                private_functions.add(name)
                after = base.local(joined, name)
            else:
                assert name not in private_data
                private_data.add(name)
                after = helpers.private_object(joined, name)
            ownership[name] = base.compare_owner(original, before, joined, after)
            first = helpers.owner_relocations(base, original, before)
            second = helpers.owner_relocations(base, joined, after)
            assert first == second, ('Private source relocation changed', name)
            relocations[name] = second
    assert {s['name'] for s in joined.symbols if s['bind'] == 0 and s['section'] != 0 and s['type'] == 2} == private_functions
    assert {s['name'] for s in joined.symbols if s['bind'] == 0 and s['section'] != 0 and s['type'] == 1} == private_data
    assert len([s for s in joined.symbols if s['type'] == 1 and s['section'] != 0 and 'KMSG_LOCK' in s['name']]) == 1
    singleton = helpers.private_object(joined, q['original_LOCAL_KMSG_LOCK'])
    assert singleton['bind'] == 0 and singleton['size'] == 4
    alias(joined, q['delay_alias'])
    # Preserve every actual non-unwind readonly section. String pooling may move
    # suffixes; field/function normalized relocation checks preserve each target.
    readonly = []
    for original in originals:
        for before in original.sections:
            if not before['size'] or not before['flags'] & 2 or before['flags'] & 5 or before['name'] == '.eh_frame':
                continue
            matches = [s for s in joined.sections if s['name'] == before['name']]
            assert len(matches) == 1
            after = matches[0]
            assert before['type'] == after['type'] == 1 and before['flags'] == after['flags'] and after['align'] >= before['align']
            raw, actual = original.contents(before), joined.contents(after)
            if before['flags'] & 0x20:
                position = 0
                while position < len(raw):
                    end = raw.index(0, position) + 1
                    assert raw[position:end] in actual
                    position = end
                readonly.append(dict(name=before['name'], exact_original_NUL_contents_retained=True, original_bytes=len(raw)))
            else:
                assert raw == actual
                first = sorted((r['offset'], r['type'], helpers.reference(base, original, r)) for r in original.relocations if r['section'] == before['index'])
                second = sorted((r['offset'], r['type'], helpers.reference(base, joined, r)) for r in joined.relocations if r['section'] == after['index'])
                assert first == second
                readonly.append(dict(name=before['name'], bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), actual_source_relocations=second))
    old_verbose = [s for s in originals[0].sections if s['name'] == '__verbose'][0]
    new_verbose = [s for s in originals[2].sections if s['name'] == '__verbose'][0]
    output_verbose = [s for s in joined.sections if s['name'] == '__verbose']
    assert len(output_verbose) == 1
    output_verbose = output_verbose[0]
    assert output_verbose['flags'] == old_verbose['flags'] == new_verbose['flags'] == 0x200003
    assert output_verbose['type'] == 1 and output_verbose['align'] == 8
    assert output_verbose['size'] == old_verbose['size'] + new_verbose['size'] == 640
    debug = data_fields(q, joined)
    return dict(status='PASS_ACTUAL_CURRENT76_PLUS_PRIMITIVE3_AND_DEBUG18_PARTIAL',
                joined_sha256=capture['object_sha256'], global_strong=80, global_T=68, global_data=12,
                actual_remaining_genuine_U=sorted(joined.undefined), all_source_owners_preserved=ownership,
                normalized_source_relocations=relocations, actual_source_readonly=readonly, new_debug18=debug,
                two_formatter_helpers_one_private_KMSG_delay_alias_and_logger88B_table_preserved=True,
                actual_joined_metadata=q['joined_capture'], source_flags_and_fullC_guard_boundary_unchanged=True,
                no_compiler_metadata_replay_function_boot_IRQ_scheduling_native_default_Cretirement_or_score_claim=True)
