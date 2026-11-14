"""Finite actual lower-IPI ELF/ASM/alias/slot owner gate; no code execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def actual_object_gate(q):
    for path, digest in q['inputs'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    spec = importlib.util.spec_from_file_location('qualified_reader_for_ipi_lower', q['qualified_ELF_reader']['path'])
    sys.dont_write_bytecode = True
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes()
    retained = json.loads(Path(q['retained_actual_capture']).read_text())
    c = json.loads(Path(q['emission_source_contract']).read_text())
    actual = dict(object_sha256=hashlib.sha256(image.raw).hexdigest(), object_bytes=len(image.raw), symbols=image.symbols,
                  sections=image.sections, relocations=image.relocations, defined=image.defined, undefined=sorted(image.undefined),
                  allocated_file_bytes={s['name']:image.contents(s).hex() for s in image.sections if s['size'] and s['flags'] & 2 and s['type'] != 8},
                  saved_disassembly_sha256=hashlib.sha256(Path(q['saved_disassembly']).read_bytes()).hexdigest(),
                  NOBITS_is_metadata_only=True, no_function_hardware_runtime=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(actual, stream, indent=2)
        stream.write('\n')
    assert actual['object_sha256'] == q['compiled_input']['sha256'] == retained['object_sha256'] and actual['object_bytes'] == retained['object_bytes'] == 1712
    assert image.symbols == retained['symbols'] and image.relocations == retained['relocations'] == c['relocations']
    expected_sections = [{k:v for k,v in s.items() if k not in ('actual_file_bytes_hex', 'NOBITS_declaration_only_not_runtime_initialization')} for s in retained['sections']]
    assert image.sections == expected_sections and image.defined == retained['defined']
    expected_names = {'ihk_mc_mb', 'wrmsr', 'x86_cpu_pause_bridge', 'x86_write_msr_bridge', 'lapic_read'}
    assert set(definitions) == set(image.defined) == expected_names and imports == image.undefined == {'cpu_pause'}
    assert sorted(image.undefined) == retained['undefined'] == c['genuine_U']
    owners = [s for s in image.symbols if s['type'] in (1, 2) and s['section'] != 0]
    assert len(owners) == 5 and all(s['bind'] == 1 and s['other'] & 3 == 0 for s in owners), 'No unknown private/function/data owner'
    actual_ranges = set()
    for item in c['physical_code_ranges']:
        section = image.sections[item['index']]
        assert (section['name'], section['type'], section['flags'], section['align'], section['size']) == (item['section'], 1, item['flags'], item['align'], item['size'])
        assert image.contents(section).hex() == item['code_hex'], 'Actual MFENCE/WRMSR/ECX-EAX-EDX/tailcall lowering matches source-bound retainedbytes'
        for name in item['names']:
            symbol = image.defined[name]
            assert (symbol['type'], symbol['section'], symbol['value'], symbol['size'], image.kind(symbol)) == (2, item['index'], 0, item['size'], 'T')
            assert definitions[name] == {'kind':'T', 'size':item['size']}
            actual_ranges.add((symbol['section'], symbol['value'], symbol['size']))
    a = image.defined['wrmsr']
    b = image.defined['x86_write_msr_bridge']
    assert (a['section'], a['value'], a['size']) == (b['section'], b['value'], b['size']) == (4, 0, 15)
    assert len(actual_ranges) == 3, 'Four source exportnames, exactlythree physicalranges/three unwindrefs'
    slot = image.defined['lapic_read']
    s = image.sections[slot['section']]
    assert (slot['type'], slot['size'], slot['value'], image.kind(slot)) == (1, 8, 0, 'B') and definitions['lapic_read'] == {'kind':'B', 'size':8}
    assert (s['name'], s['type'], s['flags'], s['align'], s['size']) == ('.lbss.lapic_read', 8, 268435459, 8, 8)
    assert not [r for r in image.relocations if r['section'] == slot['section']], 'Original None slot has no target relocation'
    assert len(image.relocations) == 4
    allowed = {3, 4, 5, slot['section']}
    for section in image.sections:
        if not section['size'] or not section['flags'] & 2 or section['index'] in allowed:
            continue
        assert (section['name'], section['type'], section['flags'], section['align'], section['size']) == ('.eh_frame', 1879048193, 2, 8, 120)
        assert image.contents(section).hex() == c['allocated_unwind']['bytes']
    dis = c['saved_disassembly']
    assert actual['saved_disassembly_sha256'] == dis['sha256'] and Path(q['saved_disassembly']).read_text() == dis['exact_retained_text']
    for item in c['physical_code_ranges']:
        for instruction in item['instructions']:
            assert instruction in dis['exact_retained_text'], instruction
    return dict(status='PASS_CALLED_ACTUAL_IPI_LOWER_FOUR_T_ONE_READ_SLOT_ONE_REAL_U_ASM_ALIAS_GATE', object_sha256=actual['object_sha256'],
                actual_global_T=4, actual_global_B=dict(name='lapic_read', bytes=8, section='.lbss.lapic_read', NOBITS_declaration_only=True),
                actual_alias=c['alias_group'], physical_code_ranges=3, genuine_U=['cpu_pause'], private_owners=[],
                actual_source_asm_memory_effects_preserved=True, actual_wrmsr_ECX_EAX_EDX_and_barrier_tailcall_bytes_bound=True,
                actual_relocations=image.relocations, saved_disassembly_reused_not_replayed=True,
                actual_metadata_capture=q['actual_metadata_capture'], future_cohort_unique_owner_join_UNBOUND=True,
                preboot_None_not_runtime_target_readiness=True, no_function_barrier_MSR_IRQ_boot_native_execution=True)
