"""Exact current publisher ELF/ABI/six-store/target-owner gate; no execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def actual_object_gate(q):
    for path, digest in q['inputs'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    for item in q['source_segment_bindings']:
        lines = Path(item['path']).read_bytes().splitlines(keepends=True)
        raw = b''.join(lines[item['first_line']-1:item['last_line']])
        assert hashlib.sha256(raw).hexdigest() == item['segment_sha256'], item['role']
    d = q['exact_diagnostic_reconciliation']
    assert Path(d['stdout_path']).read_bytes() == b''
    stderr = Path(d['stderr_path']).read_bytes()
    assert len(stderr) == 910 and hashlib.sha256(stderr).hexdigest() == d['stderr_sha256']
    reconciliation = json.loads(Path(d['Root_reconciliation_RESULT']).read_text())
    assert reconciliation['status'] == 'PASS_EXACT_RETAINED_PRODUCER_DIAGNOSTIC_RECONCILIATION_ONLY_AND_CAPTURED_ACTUAL_ELF'
    assert reconciliation['object_sha256'] == q['compiled_input']['sha256'] and reconciliation['compiler_replayed'] is False and reconciliation['old_failed_receipt_preserved'] is True
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_reader_for_six_store_publisher', q['qualified_ELF_reader']['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes()
    retained = json.loads(Path(q['retained_actual_capture']).read_text())
    c = json.loads(Path(q['emission_source_contract']).read_text())
    actual = dict(object_sha256=hashlib.sha256(image.raw).hexdigest(), object_bytes=len(image.raw), symbols=image.symbols, sections=image.sections,
                  defined=image.defined, undefined=sorted(image.undefined), relocations=image.relocations,
                  allocated_file_bytes={s['name']:image.contents(s).hex() for s in image.sections if s['size'] and s['flags'] & 2 and s['type'] != 8},
                  diagnostic_stderr_sha256=hashlib.sha256(stderr).hexdigest(), NOBITS_declaration_not_live_state=True, no_store_or_target_execution=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(actual, stream, indent=2)
        stream.write('\n')
    assert actual['object_sha256'] == retained['object_sha256'] == q['compiled_input']['sha256'] and actual['object_bytes'] == retained['object_bytes'] == 2616
    assert image.symbols == retained['symbols'] and image.defined == retained['defined'] and image.relocations == retained['relocations'] == c['all_actual_relocations']
    expected_sections = [{k:v for k,v in s.items() if k not in ('actual_file_bytes_hex', 'NOBITS_declaration_only_not_runtime_initialization')} for s in retained['sections']]
    assert image.sections == expected_sections
    assert set(image.defined) == set(definitions) == {'x2apic_wait_icr_idle', 'x86_lapic_bsp_select_bridge', 'x86_cpu_x2apic_mode', 'lapic_icr_write', 'lapic_wait_icr_idle'}
    assert imports == image.undefined == set(c['actual_genuine_U']) and sorted(image.undefined) == retained['undefined'] and len(imports) == 12
    owners = [s for s in image.symbols if s['type'] in (1, 2) and s['section'] != 0]
    assert len(owners) == 5 and all(s['bind'] == 1 and s['other'] & 3 == 0 for s in owners), 'No extra private/function/storage owner'
    for name, f in c['actual_function_bytes'].items():
        sym = image.defined[name]
        section = image.sections[sym['section']]
        assert (sym['type'], sym['section'], sym['value'], sym['size'], image.kind(sym)) == (2, f['section'], 0, f['size'], 'T')
        assert definitions[name] == {'kind':'T', 'size':f['size']}
        assert (section['name'], section['type'], section['flags'], section['align'], section['size']) == ('.ltext.'+name, 1, 268435462, 16, f['size'])
        assert image.symbol_bytes(sym).hex() == f['code_hex'], name
    for name, data in c['original_new_NOBITS_owners'].items():
        sym = image.defined[name]
        section = image.sections[sym['section']]
        assert (sym['type'], sym['value'], sym['size'], image.kind(sym)) == (1, 0, data['size'], 'B')
        assert definitions[name] == {'kind':'B', 'size':data['size']}
        assert (section['name'], section['type'], section['flags'], section['align'], section['size']) == ('.lbss.'+name, 8, 268435459, data['align'], data['size'])
        assert not [r for r in image.relocations if r['section'] == sym['section']], 'Original0/None storage has no target relocations'
    raw = image.symbol_bytes(image.defined['x86_lapic_bsp_select_bridge'])
    mode = c['zero_nonzero_mode']
    assert raw[mode['offset']:mode['offset']+len(bytes.fromhex(mode['hex']))].hex() == mode['hex']
    code_relocs = {r['offset']:r for r in image.relocations if r['section'] == 4}
    assert len(code_relocs) == 16
    for selection in c['target_selections']:
        for field, offset_field in [('x2_target','x2_reloc_offset'), ('apic_target','apic_reloc_offset')]:
            r = code_relocs[selection[offset_field]]
            assert r['type'] == 1 and r['addend'] == 0 and r['symbol']['name'] == selection[field]
        offset = selection['select_offset']
        expected = bytes.fromhex(selection['select_hex'])
        assert raw[offset:offset+len(expected)] == expected, 'Exact originalzero/nonzero CMOV targetchoice'
    assert [x['slot'] for x in c['ordered_six_stores']] == ['x86_cpu_x2apic_mode','lapic_write','lapic_read','lapic_icr_write','lapic_wait_icr_idle','x86_issue_ipi']
    assert [x['store_offset'] for x in c['ordered_six_stores']] == [137,149,162,175,188,201]
    for store in c['ordered_six_stores']:
        r = code_relocs[store['address_reloc_offset']]
        assert r['type'] == 1 and r['addend'] == 0 and r['symbol']['name'] == store['slot']
        offset = store['store_offset']
        expected = bytes.fromhex(store['store_hex'])
        assert raw[offset:offset+len(expected)] == expected
    assert raw[-1:] == b'\xc3' and len(image.relocations) == 18
    allowed = {image.defined[name]['section'] for name in image.defined}
    for section in image.sections:
        if not section['size'] or not section['flags'] & 2 or section['index'] in allowed:
            continue
        assert (section['name'], section['type'], section['flags'], section['align'], section['size']) == ('.eh_frame', 1879048193, 2, 8, 88)
        assert image.contents(section).hex() == c['allocated_unwind']['bytes']
    return dict(status='PASS_CALLED_ACTUAL_PUBLISHER_TWO_T_THREE_B_TWELVE_REAL_U_SIX_STORE_ADDRESS_GATE', object_sha256=actual['object_sha256'],
                T_sizes={'x86_lapic_bsp_select_bridge':205,'x2apic_wait_icr_idle':1}, B_sizes={'x86_cpu_x2apic_mode':4,'lapic_icr_write':8,'lapic_wait_icr_idle':8},
                genuine_U=sorted(image.undefined), actual_original_zero_nonzero_targets_and_six_ordered_stores=c['ordered_six_stores'],
                target_relocations_and_choices=c['target_selections'], physical_unwind_references=2, private_owners=[], aliases=[],
                exact_two_warning_source_specific_reconciliation_only=True, actual_metadata_capture=q['actual_metadata_capture'],
                preboot0_None_storage_not_live_state=True, future_current_cohort_collision_join_UNBOUND=True,
                no_store_observation_target_controller_boot_IRQ_function_or_native_execution=True)
