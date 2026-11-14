"""Exact two-object lock/preempt partial join; reuse qualified ELF/owner helpers."""
from pathlib import Path
import hashlib
import importlib.util
import sys


def helpers(request):
    item = request['qualified_owner_helpers']
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_kprintf_owner_helpers_for_lock_join', item['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def private_object(image, name):
    matches = [symbol for symbol in image.symbols if symbol['name'] == name and symbol['bind'] == 0 and symbol['type'] == 1]
    assert len(matches) == 1, name
    return matches[0]


def reference(base, image, relocation):
    symbol = relocation['symbol']
    if symbol['bind'] == 0 and 0 < symbol['section'] < len(image.sections):
        section = image.sections[symbol['section']]
        if section['type'] == 8:
            position = symbol['value'] + relocation['addend']
            owners = [(owner['name'], owner['bind'], owner['size'], owner['other'] & 3, position - owner['value'])
                      for owner in image.symbols if owner['type'] == 1
                      and owner['section'] == symbol['section']
                      and owner['value'] <= position < owner['value'] + owner['size']]
            assert len(owners) == 1, 'Exactly one actual NOBITS data owner required'
            return ('NOBITS_declaration_owner', tuple(owners[0]))
    return base.reference(image, relocation)


def owner_relocations(base, image, symbol):
    return sorted((relocation['offset'] - symbol['value'], relocation['type'], reference(base, image, relocation))
                  for relocation in image.relocations if relocation['section'] == symbol['section']
                  and symbol['value'] <= relocation['offset'] < symbol['value'] + symbol['size'])


def prejoin(request):
    base = helpers(request)
    reader = base.reader(request)
    for item in request['object_inputs']:
        assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    new, old = [reader.Image(item['path']) for item in request['object_inputs']]
    base.check_nm(reader, new, request['actual_new_nm'])
    base.check_nm(reader, old, request['actual_prior_nm'])
    expected = request['expected']
    for image, definitions in [(new, expected['actual_new16']), (old, expected['actual_prior44'])]:
        assert set(image.defined) == set(definitions)
        for name, fields in definitions.items():
            symbol = image.defined[name]
            assert {'kind': image.kind(symbol), 'size': symbol['size']} == fields, name
    assert new.undefined == set(expected['actual_new2U']) and old.undefined == set(expected['actual_prior21U'])
    assert not (set(new.defined) & set(old.defined)), 'Duplicate strong owner'
    singleton = private_object(new, expected['original_new_LOCAL_KMSG_LOCK']['name'])
    assert singleton['size'] == 4 and new.kind(singleton) == 'B'
    assert len([symbol for symbol in new.symbols if symbol['type'] == 1 and symbol['section'] != 0 and 'KMSG_LOCK' in symbol['name']]) == 1
    for name, size in expected['retained_old2LOCAL_helpers'].items():
        assert base.local(old, name)['size'] == size
    prospective = (new.undefined | old.undefined) - (set(new.defined) | set(old.defined))
    assert prospective == set(expected['actual_partial14U'])
    assert len(set(new.defined) | set(old.defined)) == 60
    return {'status': 'PASS_CALLED_PREJOIN_EXACT_82579_PLUS_F6DB',
            'predicate_called_before_ld_r': True,
            'actual_new16_global_prior44_global': True,
            'one_original_KMSG_LOCK_remains_LOCAL': singleton,
            'duplicate_global_owners': [],
            'actual_both_new_CPU_getter_imports_bind_existing_owners': sorted(new.undefined),
            'prospective60global49T11data14genuineU': True,
            'no_runtime_or_native_claim': True}


def postjoin(request):
    base = helpers(request)
    reader = base.reader(request)
    new, old = [reader.Image(item['path']) for item in request['object_inputs']]
    joined = reader.Image(request['joined_object'])
    base.check_nm(reader, joined, request['joined_nm'])
    assert set(joined.defined) == set(new.defined) | set(old.defined) and len(joined.defined) == 60
    assert joined.undefined == set(request['expected']['actual_partial14U']) and len(joined.undefined) == 14
    assert sum(joined.kind(symbol) == 'T' for symbol in joined.defined.values()) == 49
    ownership, relocations = {}, {}
    for original in (old, new):
        for name, symbol in original.defined.items():
            ownership[name] = base.compare_owner(original, symbol, joined, joined.defined[name])
            before = owner_relocations(base, original, symbol)
            after = owner_relocations(base, joined, joined.defined[name])
            assert before == after, ('source owner relocation binding changed', name)
            relocations[name] = after
    for name in request['expected']['retained_old2LOCAL_helpers']:
        before, after = base.local(old, name), base.local(joined, name)
        ownership[name] = base.compare_owner(old, before, joined, after)
        assert owner_relocations(base, old, before) == owner_relocations(base, joined, after), name
        relocations[name] = owner_relocations(base, joined, after)
    name = request['expected']['original_new_LOCAL_KMSG_LOCK']['name']
    before, after = private_object(new, name), private_object(joined, name)
    ownership[name] = base.compare_owner(new, before, joined, after)
    assert after['bind'] == 0 and after['size'] == 4
    assert len([symbol for symbol in joined.symbols if symbol['type'] == 1 and symbol['section'] != 0 and 'KMSG_LOCK' in symbol['name']]) == 1
    tables = {}
    for name in request['expected']['old_source_owned_jump_tables']:
        before = [section for section in old.sections if section['name'] == name]
        after = [section for section in joined.sections if section['name'] == name]
        assert len(before) == len(after) == 1
        before, after = before[0], after[0]
        assert before['type'] == after['type'] == 1 and not (after['flags'] & 5)
        assert old.contents(before) == joined.contents(after)
        first = sorted((r['offset'], r['type'], reference(base, old, r)) for r in old.relocations if r['section'] == before['index'])
        second = sorted((r['offset'], r['type'], reference(base, joined, r)) for r in joined.relocations if r['section'] == after['index'])
        assert first == second
        tables[name] = {'bytes': before['size'], 'source_owned_relocation_entries': len(first)}
    return {'status': 'PASS_CALLED_EXACT_LOCK_PREEMPT_STRING_PARTIAL_JOIN',
            'global_strong': 60, 'global_T': 49, 'global_data': 11,
            'genuine_remaining_U': sorted(joined.undefined),
            'all44prior_and16new_global_owners_sizes_filebytes_declarations_preserved': True,
            'all_actual_global_and_private_function_source_relocations_preserved': relocations,
            'all_old2LOCALformatter_helpers_preserved': True,
            'original_one_LOCAL_KMSG_LOCK4_preserved': private_object(joined, request['expected']['original_new_LOCAL_KMSG_LOCK']['name']),
            'NOBITS_preserved_as_declarations_not_fabricated_initialized_HOST_state': True,
            'owner_byte_evidence': ownership, 'source_owned_tables': tables,
            'no_runtime_boot_GS_preempt_IRQ_or_native_claim': True}
