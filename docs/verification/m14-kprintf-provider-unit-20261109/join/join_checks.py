"""Exact two-input kprintf join checks; reuse the qualified storage ELF reader.

No ELF loader/new parser, source provider, compiler or runtime execution here.
NOBITS is checked as a declaration, never fabricated as initialized HOST bytes.
"""
from pathlib import Path
import hashlib
import importlib.util
import sys


def reader(request):
    path = Path(request['qualified_ELF_reader']['path'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == request['qualified_ELF_reader']['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_storage_reader_for_kprintf_join', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local(image, name):
    matches = [s for s in image.symbols if s['name'] == name and s['bind'] == 0 and s['type'] == 2]
    assert len(matches) == 1, name
    return matches[0]


def check_nm(module, image, path):
    definitions, imports = module.parse_nm(Path(path).read_text())
    assert set(definitions) == set(image.defined) and imports == image.undefined
    for name, fields in definitions.items():
        symbol = image.defined[name]
        assert fields == {'kind': image.kind(symbol), 'size': symbol['size']}, name


def compare_owner(original, before, joined, after):
    assert (before['bind'], before['type'], before['size'], before['other'] & 3) == \
           (after['bind'], after['type'], after['size'], after['other'] & 3), before['name']
    assert original.kind(before) == joined.kind(after), before['name']
    first, second = original.sections[before['section']], joined.sections[after['section']]
    assert first['type'] == second['type'] and first['flags'] == second['flags']
    assert second['align'] >= first['align']
    if first['type'] == 8:
        assert after['value'] + after['size'] <= second['size']
        return {'kind': 'B', 'bytes': before['size'], 'NOBITS_declaration_preserved': True}
    actual = original.symbol_bytes(before)
    assert actual == joined.symbol_bytes(after), before['name']
    return {'kind': original.kind(before), 'bytes': before['size'],
            'exact_bytes_sha256': hashlib.sha256(actual).hexdigest()}


def reference(image, relocation):
    symbol = relocation['symbol']
    if symbol['bind'] == 1:
        return ('global', symbol['name'], relocation['addend'])
    assert 0 < symbol['section'] < len(image.sections)
    section = image.sections[symbol['section']]
    position = symbol['value'] + relocation['addend']
    assert 0 <= position < section['size']
    if section['flags'] & 4:
        owners = sorted((s['name'], position - s['value']) for s in image.symbols
                        if s['type'] == 2 and s['section'] == symbol['section']
                        and s['value'] <= position < s['value'] + s['size'])
        assert owners
        return ('code', tuple(owners))
    assert section['type'] == 1 and not section['flags'] & 1
    raw = image.contents(section)
    if section['name'] == '.lrodata.str1.1':
        end = raw.index(0, position)
        return ('literal_string', raw[position:end + 1].hex())
    return ('readonly', section['name'], position, section['size'], hashlib.sha256(raw).hexdigest())


def function_relocations(image, symbol):
    return sorted((r['offset'] - symbol['value'], r['type'], reference(image, r))
                  for r in image.relocations if r['section'] == symbol['section']
                  and symbol['value'] <= r['offset'] < symbol['value'] + symbol['size'])


def prejoin(request):
    module = reader(request)
    for item in request['object_inputs']:
        assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    new, old = [module.Image(item['path']) for item in request['object_inputs']]
    check_nm(module, new, request['actual_new_nm'])
    check_nm(module, old, request['actual_prior_nm'])
    expected = request['expected']
    assert set(new.defined) == set(expected['new11_global_T']) and len(new.defined) == 11
    for name, size in expected['new11_global_T'].items():
        symbol = new.defined[name]
        assert new.kind(symbol) == 'T' and symbol['size'] == size
    assert new.undefined == set(expected['actual_new12_U'])
    assert set(old.defined) == set(expected['prior31_global_owners']) and len(old.defined) == 31
    for name, fields in expected['prior31_global_owners'].items():
        symbol = old.defined[name]
        assert old.kind(symbol) == fields['kind'] and symbol['size'] == fields['bytes']
    assert old.undefined == set(expected['actual_prior13_U'])
    assert not (set(new.defined) & set(old.defined)), 'Duplicate strong owner'
    for name, size in expected['two_source_private_local_helpers'].items():
        assert local(new, name)['size'] == size
    assert len(set(new.defined) | set(old.defined)) == 42
    prospective = (new.undefined | old.undefined) - (set(new.defined) | set(old.defined))
    assert prospective == set(expected['partial23_U'])
    return {'status': 'PASS_CALLED_PREJOIN_EXACT_ACTUAL_TWO_INPUT_OWNERS',
            'predicate_called_before_ld_r': True, 'new_global_T': 11, 'prior_global_owners': 31,
            'duplicate_strong_owners': [], 'two_source_owned_helpers_local': True,
            'prospective42_strong_23_genuine_U': True, 'no_compile_or_runtime': True}


def postjoin(request):
    module = reader(request)
    new, old = [module.Image(item['path']) for item in request['object_inputs']]
    joined = module.Image(request['joined_object'])
    check_nm(module, joined, request['joined_nm'])
    expected = set(old.defined) | set(new.defined)
    assert len(expected) == 42 and set(joined.defined) == expected
    assert joined.undefined == set(request['expected']['partial23_U']) and len(joined.undefined) == 23
    assert sum(joined.kind(s) == 'T' for s in joined.defined.values()) == 33
    ownership, relocs = {}, {}
    for original in (old, new):
        for name, symbol in original.defined.items():
            ownership[name] = compare_owner(original, symbol, joined, joined.defined[name])
            before = function_relocations(original, symbol)
            after = function_relocations(joined, joined.defined[name])
            assert before == after, ('relocation source binding changed', name)
            relocs[name] = after
    for name in request['expected']['two_source_private_local_helpers']:
        before, after = local(new, name), local(joined, name)
        ownership[name] = compare_owner(new, before, joined, after)
        assert function_relocations(new, before) == function_relocations(joined, after), name
        relocs[name] = function_relocations(joined, after)
    # These two actual compiler tables have unique source-owned section names.
    tables = {}
    for name in request['expected']['source_owned_jump_table_sections']:
        before = [s for s in new.sections if s['name'] == name]
        after = [s for s in joined.sections if s['name'] == name]
        assert len(before) == len(after) == 1
        before, after = before[0], after[0]
        assert before['type'] == after['type'] == 1 and not (after['flags'] & 5)
        assert new.contents(before) == joined.contents(after)
        first = sorted((r['offset'], r['type'], reference(new, r)) for r in new.relocations if r['section'] == before['index'])
        second = sorted((r['offset'], r['type'], reference(joined, r)) for r in joined.relocations if r['section'] == after['index'])
        assert first == second
        tables[name] = {'bytes': before['size'], 'source_owned_relocation_entries': len(first)}
    assert any(r[2] == ('global', 'kprintf', 0) for r in relocs['x86_addr_log_bridge'])
    assert any(r[2] == ('global', 'ihk_mc_get_processor_id', 0) for r in relocs['kprintf'])
    return {'status': 'PASS_CALLED_EXACT_KPRINTF_PARTIAL_JOIN',
            'global_strong': 42, 'global_T': 33, 'global_data': 9,
            'genuine_remaining_U': sorted(joined.undefined),
            'all31_prior_sizes_and_exact_file_backed_bytes_preserved': True,
            'NOBITS_preserved_as_declarations_not_fabricated_HOST_bytes': True,
            'all11_new_C_function_bytes_and_two_local_helpers_preserved': True,
            'actual_source_owner_relocation_bindings': relocs,
            'source_owned_jump_tables': tables, 'owner_byte_evidence': ownership,
            'cross_input_kprintf_and_CPU_edges_resolved': True,
            'memset_kernel_provider_stays_U': 'memset' in joined.undefined,
            'no_runtime_boot_lock_IRQ_or_native_claim': True}
