"""Finite scheduler object and exact aaaf join; reuse qualified owner/ELF machinery."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def qualified(q):
    item = q['qualified_lock_relocation_helpers']
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('scheduler_qualified_lock_owner_helpers', item['path'])
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    base = helpers.helpers(q)
    return helpers, base, base.reader(q)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source(q):
    for path, digest in q['source_bindings'].items():
        assert sha(path) == digest, path
    manifest = json.loads(Path(q['source_manifest']).read_text())
    assert sha(q['source_unit']) == q['source_unit_sha256']
    return manifest


def alias(image, names):
    values = {(image.defined[name]['section'], image.defined[name]['value'], image.defined[name]['size']) for name in names}
    assert len(values) == 1


def actual_private_source_name(symbol, q):
    # Only three exact original source names in this exact crate/module path.
    marker = '_' + str(len(q['crate_name'])) + q['crate_name'] + '13sched_helpers'
    matches = [name for name in q['source_private_functions']
               if symbol['name'].startswith('_RN') and marker in symbol['name']
               and symbol['name'].endswith(str(len(name)) + name)]
    assert len(matches) == 1, ('Unreviewed compiler private FUNC: STOP before join', symbol['name'])
    return matches[0]


def object_gate(q):
    source(q)
    helpers, base, reader = qualified(q)
    new = reader.Image(q['new_object'])
    base.check_nm(reader, new, q['actual_new_nm'])
    assert Path(q['actual_new_elf']).read_bytes(), 'Actual ELF readback absent'
    assert set(new.defined) == set(q['expected_new3T']), 'Unreviewed global owner'
    assert new.undefined == set(q['expected_new11U']), ('Unexpected source/intrinsic import: STOP before link', sorted(new.undefined))
    for name in q['expected_new3T']:
        owner = new.defined[name]
        assert owner['bind'] == 1 and owner['type'] == 2 and owner['other'] & 3 == 0
        assert new.kind(owner) == 'T' and owner['size'] > 0
    assert not [section for section in new.sections if section['flags'] & 3 == 3 and section['size']], 'Writable allocated data is not in source partition'
    private_constants = []
    for owner in new.symbols:
        if owner['type'] != 1 or owner['section'] == 0:
            continue
        section = new.sections[owner['section']]
        assert owner['bind'] == 0 and owner['name'] and owner['other'] & 3 == 0
        assert owner['value'] == 0 and owner['size'] == section['size'] == 208
        assert section['type'] == 1 and section['flags'] & 2 and not section['flags'] & 5, 'Only local readonly original offset constructor owner is eligible'
        private_constants.append(dict(name=owner['name'], bytes=owner['size'], section=section['name'], sha256=sha_symbol(new, owner)))
    private = {}
    for owner in new.symbols:
        if owner['bind'] != 0 or owner['type'] != 2 or owner['section'] == 0:
            continue
        name = actual_private_source_name(owner, q)
        assert name not in private and owner['size'] > 0 and owner['other'] & 3 == 0
        relocations = helpers.owner_relocations(base, new, owner)
        target = q['private_adapter_imports'].get(name)
        if target:
            globals_ = [row[2] for row in relocations if row[2][0] == 'global']
            assert globals_ == [('global', target, 0)], ('Actual source adapter import binding', name, globals_)
        private[name] = dict(symbol=owner['name'], bytes=owner['size'], sha256=sha_symbol(new, owner), relocations=relocations)
    readonly = []
    table_bytes = None
    for section in new.sections:
        if not section['size'] or not section['flags'] & 2 or section['flags'] & 5:
            continue
        if section['name'] == '.eh_frame':
            # Exact inherited freestanding profile emits native unwind metadata.
            assert section['type'] == 0x70000001 and section['flags'] == 2 and section['align'] == 8
            refs = [helpers.reference(base, new, row) for row in new.relocations if row['section'] == section['index']]
            assert refs and all(row[0] == 'code' or row[0] == 'global' and row[1] in q['expected_new3T'] and row[2] == 0 for row in refs)
            readonly.append(dict(kind='retained_profile_native_unwind', name=section['name'], bytes=section['size'], source_code_references=refs))
            continue
        # No source strings/statics are selected. Only the original 26-usize
        # offset constructor can emit file-backed constants in this cut.
        assert section['type'] == 1 and section['size'] == 208 and section['align'] >= 8, ('Unreviewed readonly emission: STOP before join', section['name'], section['size'])
        assert not [row for row in new.relocations if row['section'] == section['index']], 'Offset values are integers, not provider addresses'
        payload = new.contents(section)
        if table_bytes is None:
            table_bytes = payload
        assert payload == table_bytes, 'One original offset constructor must produce one value'
        incoming = [row for row in new.relocations if row['symbol']['section'] == section['index']]
        assert incoming, 'Unbound readonly data'
        source_owners = []
        for row in incoming:
            target = row['symbol']['value'] + row['addend']
            assert row['type'] == 1 and 0 <= target < 208, 'Exact large-code-model source constant reference'
            owners = [owner for owner in new.symbols if owner['type'] == 2 and owner['section'] == row['section']
                      and owner['value'] <= row['offset'] < owner['value'] + owner['size']]
            assert len(owners) == 1
            owner = owners[0]
            label = owner['name'] if owner['bind'] == 1 else actual_private_source_name(owner, q)
            assert label in ('__sched_wakeup_thread', 'sched_wakeup_thread', 'sched_runqueue_offsets'), 'Offset constant source-owner relationship'
            source_owners.append(label)
        readonly.append(dict(kind='actual_source_26_offset_constructor', name=section['name'], bytes=208,
                             source_function='sched_runqueue_offsets', source_ABI_sha256=q['source_bindings'][q['actual_ABI']],
                             sha256=hashlib.sha256(payload).hexdigest(), actual26usize=[int.from_bytes(payload[i:i+8], 'little') for i in range(0, 208, 8)],
                             incoming_source_owners=source_owners,
                             claim='Actual immutable source/compiler constructor ownership, not a new independent numeric ABI or native qualification'))
    return dict(status='PASS_CALLED_ACTUAL_SCHEDULER_OBJECT_GATE', object_sha256=sha(q['new_object']),
                global3T={name: new.defined[name]['size'] for name in sorted(new.defined)}, genuine11U=sorted(new.undefined),
                source_private_functions=private, source_private_offset_objects=private_constants, source_readonly_sections=readonly,
                no_writable_data_or_unreviewed_intrinsics=True)


def sha_symbol(image, owner):
    return hashlib.sha256(image.symbol_bytes(owner)).hexdigest()


def prejoin(q):
    decision = object_gate(q)
    helpers, base, reader = qualified(q)
    assert sha(q['prior_object']) == q['prior_object_sha256']
    new, old = reader.Image(q['new_object']), reader.Image(q['prior_object'])
    base.check_nm(reader, old, q['actual_prior_nm'])
    expected = q['expected']
    assert set(old.defined) == set(expected['prior63']) and old.undefined == set(expected['prior13U'])
    for name, fields in expected['prior63'].items():
        owner = old.defined[name]
        assert {'kind': old.kind(owner), 'size': owner['size']} == fields, name
    assert not (set(new.defined) & set(old.defined)), 'Duplicate strong owners'
    assert 'sched_wakeup_thread' in old.undefined and old.kind(old.defined['ihk_mc_get_processor_id']) == 'T'
    singleton = helpers.private_object(old, expected['original_LOCAL_KMSG_LOCK'])
    assert old.kind(singleton) == 'B' and singleton['size'] == 4
    for name, size in expected['old2LOCAL_helpers'].items():
        assert base.local(old, name)['size'] == size
    alias(old, expected['delay_alias'])
    prospective = (new.undefined | old.undefined) - (set(new.defined) | set(old.defined))
    assert prospective == set(expected['joined22U']) and len(prospective) == 22
    assert len(set(new.defined) | set(old.defined)) == 66
    return dict(status='PASS_CALLED_PREJOIN_ONLY_NEW_SCHEDULER_PLUS_AAAF', actual_object_gate=decision,
                prior_sha256=sha(q['prior_object']), duplicate_strong_owners=[], prospective66globals55T11data22U=True,
                predicate_called_before_ld_r=True, no_function_or_hardware_execution=True)


def postjoin(q):
    helpers, base, reader = qualified(q)
    new, old, joined = reader.Image(q['new_object']), reader.Image(q['prior_object']), reader.Image(q['joined_object'])
    base.check_nm(reader, joined, q['joined_nm'])
    assert Path(q['joined_elf']).read_bytes()
    assert set(joined.defined) == set(new.defined) | set(old.defined) and len(joined.defined) == 66
    assert joined.undefined == set(q['expected']['joined22U']) and len(joined.undefined) == 22
    assert sum(joined.kind(owner) == 'T' for owner in joined.defined.values()) == 55
    ownership, relocations = {}, {}
    for original in (old, new):
        for name, before in original.defined.items():
            after = joined.defined[name]
            ownership[name] = base.compare_owner(original, before, joined, after)
            first, second = helpers.owner_relocations(base, original, before), helpers.owner_relocations(base, joined, after)
            assert first == second, ('Source-owner relocation binding changed', name)
            relocations[name] = second
    for original in (old, new):
        for before in original.symbols:
            if before['bind'] != 0 or before['type'] != 2 or before['section'] == 0:
                continue
            after = base.local(joined, before['name'])
            ownership[before['name']] = base.compare_owner(original, before, joined, after)
            first, second = helpers.owner_relocations(base, original, before), helpers.owner_relocations(base, joined, after)
            assert first == second
            relocations[before['name']] = second
    for before in new.symbols:
        if before['bind'] == 0 and before['type'] == 1 and before['section'] != 0:
            after = helpers.private_object(joined, before['name'])
            ownership[before['name']] = base.compare_owner(new, before, joined, after)
            assert helpers.owner_relocations(base, new, before) == helpers.owner_relocations(base, joined, after)
    singleton_name = q['expected']['original_LOCAL_KMSG_LOCK']
    before, after = helpers.private_object(old, singleton_name), helpers.private_object(joined, singleton_name)
    ownership[singleton_name] = base.compare_owner(old, before, joined, after)
    assert after['bind'] == 0 and after['size'] == 4
    assert len([owner for owner in joined.symbols if owner['type'] == 1 and owner['section'] != 0 and 'KMSG_LOCK' in owner['name']]) == 1
    tables = {}
    for original, names in [(old, q['expected']['old_source_owned_tables']),
                            (new, [section['name'] for section in new.sections if section['type'] == 1 and section['size'] and section['flags'] & 2 and not section['flags'] & 5])]:
        for name in names:
            first = [section for section in original.sections if section['name'] == name]
            second = [section for section in joined.sections if section['name'] == name]
            assert len(first) == len(second) == 1
            first, second = first[0], second[0]
            assert first['type'] == second['type'] == 1 and first['flags'] == second['flags'] and second['align'] >= first['align']
            assert original.contents(first) == joined.contents(second)
            a = sorted((row['offset'], row['type'], helpers.reference(base, original, row)) for row in original.relocations if row['section'] == first['index'])
            b = sorted((row['offset'], row['type'], helpers.reference(base, joined, row)) for row in joined.relocations if row['section'] == second['index'])
            assert a == b
            tables[name] = dict(bytes=first['size'], sha256=hashlib.sha256(original.contents(first)).hexdigest(), source_owned_relocations=a)
    alias(joined, q['expected']['delay_alias'])
    return dict(status='PASS_CALLED_SCHEDULER_AAAF_PARTIAL_JOIN', global_strong=66, global_T=55, global_data=11,
                genuine_remaining_U=sorted(joined.undefined), exact_global_and_private_owner_bytes_sizes_visibility_alignments=ownership,
                actual_source_relocations=relocations, source_readonly_tables=tables,
                one_private_LOCAL_KMSG_LOCK_preserved=True, delay_alias_preserved=True,
                no_scheduling_lock_IRQ_boot_function_native_runtime_or_acceptance_claim=True)
