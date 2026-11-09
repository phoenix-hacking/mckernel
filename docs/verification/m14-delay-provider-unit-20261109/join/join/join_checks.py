"""Exact delay+published lock cohort partial join; reuse qualified owner/reloc helpers."""
from pathlib import Path
import hashlib
import importlib.util
import sys


def qualified(request):
    item = request['qualified_lock_relocation_helpers']
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_lock_owner_helpers_for_delay_join', item['path'])
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    base = helpers.helpers(request)
    return helpers, base, base.reader(request)


def alias(image, names):
    values = {(image.defined[name]['section'], image.defined[name]['value'], image.defined[name]['size']) for name in names}
    assert len(values) == 1
    return sorted(names)


def prejoin(request):
    helpers, base, reader = qualified(request)
    for item in request['object_inputs']:
        assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    new, old = [reader.Image(item['path']) for item in request['object_inputs']]
    base.check_nm(reader, new, request['actual_new_nm'])
    base.check_nm(reader, old, request['actual_prior_nm'])
    expected = request['expected']
    for image, definitions in [(new, expected['actual_new3']), (old, expected['actual_prior60'])]:
        assert set(image.defined) == set(definitions)
        for name, fields in definitions.items():
            symbol = image.defined[name]
            assert {'kind': image.kind(symbol), 'size': symbol['size']} == fields, name
    assert new.undefined == set(expected['actual_new1U']) and old.undefined == set(expected['actual_prior14U'])
    assert not (set(new.defined) & set(old.defined)), 'Duplicate strong owner'
    assert not [symbol for symbol in new.symbols if symbol['type'] == 1 and symbol['section'] != 0]
    alias(new, expected['actual_new_compiler_code_alias'])
    singleton = helpers.private_object(old, expected['original_old_LOCAL_KMSG_LOCK']['name'])
    assert singleton['size'] == 4 and old.kind(singleton) == 'B'
    for name, size in expected['retained_old2LOCAL_helpers'].items():
        assert base.local(old, name)['size'] == size
    prospective = (new.undefined | old.undefined) - (set(new.defined) | set(old.defined))
    assert prospective == set(expected['actual_partial13U'])
    assert len(set(new.defined) | set(old.defined)) == 63
    return {'status': 'PASS_CALLED_PREJOIN_EXACT_E9D1_PLUS_346C',
            'predicate_called_before_ld_r': True,
            'actual_new3_global_prior60_global': True,
            'original_private_singleton_and_two_formatter_helpers_retained': True,
            'actual_new_compiler_alias_preserved': expected['actual_new_compiler_code_alias'],
            'duplicate_global_owners': [],
            'cpu_pause_new_U_binds_existing_genuine_T3': True,
            'prospective63global52T11data13genuineU': True,
            'no_function_or_hardware_timing_execution': True}


def postjoin(request):
    helpers, base, reader = qualified(request)
    new, old = [reader.Image(item['path']) for item in request['object_inputs']]
    joined = reader.Image(request['joined_object'])
    base.check_nm(reader, joined, request['joined_nm'])
    assert set(joined.defined) == set(new.defined) | set(old.defined) and len(joined.defined) == 63
    assert joined.undefined == set(request['expected']['actual_partial13U']) and len(joined.undefined) == 13
    assert sum(joined.kind(symbol) == 'T' for symbol in joined.defined.values()) == 52
    ownership, relocations = {}, {}
    for original in (old, new):
        for name, symbol in original.defined.items():
            ownership[name] = base.compare_owner(original, symbol, joined, joined.defined[name])
            before = helpers.owner_relocations(base, original, symbol)
            after = helpers.owner_relocations(base, joined, joined.defined[name])
            assert before == after, ('source owner relocation binding changed', name)
            relocations[name] = after
    for name in request['expected']['retained_old2LOCAL_helpers']:
        before, after = base.local(old, name), base.local(joined, name)
        ownership[name] = base.compare_owner(old, before, joined, after)
        assert helpers.owner_relocations(base, old, before) == helpers.owner_relocations(base, joined, after), name
        relocations[name] = helpers.owner_relocations(base, joined, after)
    name = request['expected']['original_old_LOCAL_KMSG_LOCK']['name']
    before, after = helpers.private_object(old, name), helpers.private_object(joined, name)
    ownership[name] = base.compare_owner(old, before, joined, after)
    assert after['bind'] == 0 and after['size'] == 4
    assert len([symbol for symbol in joined.symbols if symbol['type'] == 1 and symbol['section'] != 0 and 'KMSG_LOCK' in symbol['name']]) == 1
    alias(joined, request['expected']['actual_new_compiler_code_alias'])
    tables = {}
    for name in request['expected']['old_source_owned_jump_tables']:
        first = [section for section in old.sections if section['name'] == name]
        second = [section for section in joined.sections if section['name'] == name]
        assert len(first) == len(second) == 1
        first, second = first[0], second[0]
        assert first['type'] == second['type'] == 1 and not (second['flags'] & 5)
        assert old.contents(first) == joined.contents(second)
        before = sorted((r['offset'], r['type'], helpers.reference(base, old, r)) for r in old.relocations if r['section'] == first['index'])
        after = sorted((r['offset'], r['type'], helpers.reference(base, joined, r)) for r in joined.relocations if r['section'] == second['index'])
        assert before == after
        tables[name] = {'bytes': first['size'], 'source_owned_relocation_entries': len(before)}
    return {'status': 'PASS_CALLED_EXACT_DELAY_LOCK_STRING_PARTIAL_JOIN',
            'global_strong': 63, 'global_T': 52, 'global_data': 11,
            'genuine_remaining_U': sorted(joined.undefined),
            'all60prior_and3new_global_owners_sizes_filebytes_declarations_preserved': True,
            'actual_all_function_and_data_source_relocations_preserved': relocations,
            'old2LOCALformatter_helpers_and_ONELOCALb4KMSG_LOCK_preserved': True,
            'original_LOCAL_singleton': helpers.private_object(joined, request['expected']['original_old_LOCAL_KMSG_LOCK']['name']),
            'actual_new_compiler_alias_preserved': alias(joined, request['expected']['actual_new_compiler_code_alias']),
            'NOBITS_is_declaration_only_not_initialized_HOST_state': True,
            'owner_byte_evidence': ownership, 'source_owned_tables': tables,
            'no_runtime_RDTSC_timing_calibration_boot_or_native_claim': True}
