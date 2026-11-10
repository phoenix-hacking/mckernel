"""Finite actual LAPIC five-function/one-slot object gate; no execution loader."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def actual_object_gate(q):
    for path, digest in q['inputs'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    item = q['qualified_ELF_reader']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_reader_for_lapic', item['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes()
    retained = json.loads(Path(q['retained_actual_capture']).read_text())
    contract = json.loads(Path(q['emission_source_contract']).read_text())
    actual = dict(object_sha256=hashlib.sha256(image.raw).hexdigest(), object_bytes=len(image.raw),
                  symbols=image.symbols, sections=image.sections, relocations=image.relocations,
                  defined=image.defined, undefined=sorted(image.undefined),
                  allocated_file_bytes={s['name']:image.contents(s).hex() for s in image.sections if s['size'] and s['flags'] & 2 and s['type'] != 8},
                  NOBITS_remains_metadata_only=True, function_runtime_executed=False)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(actual, stream, indent=2)
        stream.write('\n')
    assert actual['object_sha256'] == q['compiled_input']['sha256'] == retained['object_sha256']
    assert actual['object_bytes'] == q['compiled_input']['bytes'] == retained['object_bytes']
    assert image.symbols == retained['symbols'] and image.relocations == retained['relocations']
    expected_sections = [{k:v for k,v in s.items() if k not in ('actual_file_bytes_hex', 'NOBITS_declaration_only_not_runtime_initialization')} for s in retained['sections']]
    assert image.sections == expected_sections, 'Exact actual section classification/flags/alignment preserved'
    assert image.defined == retained['defined'] and imports == image.undefined == set() and retained['undefined'] == []
    names = {f['name'] for f in contract['actual_functions']} | {'lapic_write'}
    assert set(image.defined) == set(definitions) == names and len(names) == 6
    owned = [s for s in image.symbols if s['type'] in (1, 2) and s['section'] != 0]
    assert len(owned) == 6 and all(s['bind'] == 1 and s['other'] & 3 == 0 for s in owned), 'No private or duplicate function/data owners'
    function_sections = set()
    for f in contract['actual_functions']:
        symbol = image.defined[f['name']]
        section = image.sections[symbol['section']]
        assert symbol['type'] == 2 and image.kind(symbol) == 'T'
        assert definitions[f['name']] == {'kind':'T', 'size':f['actual_size']}
        assert symbol['size'] == f['actual_size'] and symbol['value'] == f['symbol_value'] == 0
        assert (section['name'], section['type'], section['flags'], section['align'], section['size']) == (f['section'], 1, f['section_flags'], f['section_alignment'], f['actual_size'])
        assert image.symbol_bytes(symbol).hex() == f['code_hex'], f['name']
        assert symbol['section'] not in function_sections, 'Actual five distinct code ranges; no invented alias'
        function_sections.add(symbol['section'])
    slot = image.defined['lapic_write']
    section = image.sections[slot['section']]
    assert (slot['type'], slot['size'], slot['value'], image.kind(slot)) == (1, 8, 0, 'B')
    assert definitions['lapic_write'] == {'kind':'B', 'size':8}
    assert (section['name'], section['type'], section['flags'], section['align'], section['size']) == ('.lbss.lapic_write', 8, 268435459, 8, 8)
    assert not [r for r in image.relocations if r['section'] == slot['section']], 'Original None slot, no fabricated target relocation'
    assert len(image.relocations) == len(contract['actual_relocations']) == 8
    for r, expected in zip(image.relocations, contract['actual_relocations']):
        symbol = r['symbol']
        observed = dict(section=image.sections[r['section']]['name'], offset=r['offset'], type=r['type'], symbol_name=symbol['name'], symbol_section=image.sections[symbol['section']]['name'], symbol_type=symbol['type'], symbol_bind=symbol['bind'], addend=r['addend'])
        assert observed == {k:expected[k] for k in observed}, observed
    allowed = function_sections | {slot['section']}
    for s in image.sections:
        if not s['size'] or not s['flags'] & 2:
            continue
        if s['index'] in allowed:
            continue
        assert (s['name'], s['type'], s['flags'], s['align'], s['size']) == ('.eh_frame', 1, 2, 8, 208), 'No unknown readonly/private/state or intrinsic emission'
        assert image.contents(s).hex() == retained['sections'][s['index']]['actual_file_bytes_hex']
    return dict(status='PASS_CALLED_ACTUAL_LAPIC_FIVE_T_ONE_REAL_NONE_SLOT_ZERO_U_GATE',
                object_sha256=actual['object_sha256'], actual_function_sizes={f['name']:f['actual_size'] for f in contract['actual_functions']},
                slot=dict(name='lapic_write', kind='B', bytes=8, section='.lbss.lapic_write', flags=268435459, alignment=8, NOBITS_declaration_only=True),
                genuine_U=[], private_owners=[], aliases=[], source_bound_relocations=contract['actual_relocations'],
                ordered_source_callbacks_and_actual_inlining_bytes_preserved=True, actual_metadata_capture=q['actual_metadata_capture'],
                standalone_unique_owners_only=True, future_cohort_unique_owner_join_UNBOUND=True,
                preboot_None_never_runtime_target_readiness=True, no_function_boot_hardware_native_execution=True)
