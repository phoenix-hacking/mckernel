"""One new genuine process-pair object plus retained e1a partial, no runtime calls.

Reuse the qualified ELF reader and owner/relocation normalizers only. This file
does not load or execute a McKernel function or replay an old gate.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module(item, name):
    assert sha(item['path']) == item['sha256'], item['path']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location(name, item['path'])
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def qualified(q):
    reader = module(q['qualified_ELF_reader'], 'process_pair_qualified_ELF')
    owners = module(q['qualified_owner_helpers'], 'process_pair_qualified_owners')
    relocs = module(q['qualified_relocation_helpers'], 'process_pair_qualified_relocations')
    return reader, owners, relocs


def bindings(q):
    for path, digest in q['inputs'].items():
        assert sha(path) == digest, path
    manifest = json.loads(Path(q['source_manifest']).read_text())
    for path, fields in manifest['files'].items():
        assert sha(path) == fields['sha256'] and Path(path).stat().st_size == fields['bytes'], path
    for item in manifest['source_slices']:
        raw = Path(item['source']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['source_sha256'], item['source']
        selected = raw[item['start_byte']:item['end_byte_exclusive']]
        assert len(selected) == item['bytes']
        assert hashlib.sha256(selected).hexdigest() == item['slice_sha256']
        assert selected in Path(item['selected_file']).read_bytes(), item['label']
    assert manifest['expected_global_T'] == q['expected_new_global_T']
    assert manifest['expected_new_data'] == [] and manifest['exact_native_cfg'] == []
    reader, owners, _ = qualified(q)
    old = reader.Image(q['retained_object']['path'])
    owners.check_nm(reader, old, q['retained_object']['actual_nm'])
    saved = json.loads(Path(q['retained_object']['capture']).read_text())
    assert saved['object_sha256'] == q['retained_object']['sha256']
    assert saved['symbols'] == old.symbols
    assert len(old.defined) == 129 and old.undefined == set(q['retained_genuine_U'])
    assert sum(old.kind(s) == 'T' for s in old.defined.values()) == 104
    assert len(old.defined) - 104 == 25
    assert not set(q['expected_new_global_T']) & set(old.defined)
    for name, expected in q['retained_lower_owners'].items():
        value = old.defined[name]
        assert dict(kind=old.kind(value), bytes=value['size']) == expected, name
    return {'status': 'PASS_CURRENT_SOURCE_TYPES_AND_RETAINED_E1A_BINDINGS',
            'actual_retained_object_sha256': sha(q['retained_object']['path']),
            'retained_global_owners': 129, 'retained_genuine_U': sorted(old.undefined),
            'new_source_members_only': q['expected_new_global_T'],
            'actual_source_slice_count': len(manifest['source_slices']),
            'runtime_or_native_or_source_hold_release': False}


def prejoin(q):
    reader, owners, _ = qualified(q)
    old = reader.Image(q['retained_object']['path'])
    new = reader.Image(q['provider_object'])
    owners.check_nm(reader, new, q['provider_nm'])
    assert Path(q['provider_elf']).stat().st_size > 0
    assert set(new.defined) == set(q['expected_new_global_T'])
    for name, value in new.defined.items():
        assert new.kind(value) == 'T' and value['type'] == 2 and value['bind'] == 1 and value['size'] > 0, name
    assert new.undefined == set(q['expected_new_genuine_U'])
    assert not set(old.defined) & set(new.defined), 'Duplicate actual strong owner'
    assert new.undefined <= set(old.defined), 'Every new import needs the retained genuine provider'
    remaining = (new.undefined | old.undefined) - (set(new.defined) | set(old.defined))
    assert remaining == set(q['expected_remaining_genuine_U'])
    assert old.undefined - remaining == {'syscall_find_process_bridge', 'syscall_process_unlock_bridge'}
    return {'status': 'PASS_NEW_GENUINE_PROCESS_PAIR_PREJOIN',
            'called_before_ld_r': True, 'provider_sha256': sha(q['provider_object']),
            'actual_new11': {n: {'kind': new.kind(s), 'bytes': s['size']} for n, s in new.defined.items()},
            'actual_new_genuine_U': sorted(new.undefined), 'duplicate_strong_owners': [],
            'expected_remaining_genuine_U': sorted(remaining),
            'old_or_new_kernel_function_executed': False}


def postjoin(q):
    reader, owners, relocs = qualified(q)
    originals = [reader.Image(q['retained_object']['path']), reader.Image(q['provider_object'])]
    joined = reader.Image(q['joined_object'])
    owners.check_nm(reader, joined, q['joined_nm'])
    assert Path(q['joined_elf']).stat().st_size > 0
    expected = set().union(*(set(x.defined) for x in originals))
    assert set(joined.defined) == expected and len(expected) == 140
    assert joined.undefined == set(q['expected_remaining_genuine_U'])
    assert sum(joined.kind(s) == 'T' for s in joined.defined.values()) == 115
    assert sum(joined.kind(s) != 'T' for s in joined.defined.values()) == 25
    owned, relocations, private = {}, {}, {1: set(), 2: set()}
    for original in originals:
        for name, before in original.defined.items():
            after = joined.defined[name]
            owned[name] = owners.compare_owner(original, before, joined, after)
            first = relocs.owner_relocations(owners, original, before)
            second = relocs.owner_relocations(owners, joined, after)
            assert first == second, ('Actual normalized owner relocations changed', name)
            relocations[name] = second
        for before in original.symbols:
            if before['bind'] != 0 or before['section'] == 0 or before['type'] not in (1, 2):
                continue
            name = before['name']
            assert name not in private[before['type']], ('Private source-name collision', name)
            private[before['type']].add(name)
            after = (owners.local(joined, name) if before['type'] == 2 else relocs.private_object(joined, name))
            owned[name] = owners.compare_owner(original, before, joined, after)
            first = relocs.owner_relocations(owners, original, before)
            second = relocs.owner_relocations(owners, joined, after)
            assert first == second, ('Actual private owner relocation changed', name)
            relocations[name] = second
    for typ in (1, 2):
        assert {s['name'] for s in joined.symbols if s['bind'] == 0 and s['section'] != 0 and s['type'] == typ} == private[typ]
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
                at = 0
                while at < len(raw):
                    end = raw.index(0, at) + 1
                    assert raw[at:end] in actual
                    at = end
                readonly.append({'section': before['name'], 'original_NUL_strings_preserved': True})
            else:
                assert raw == actual
                first = sorted((r['offset'], r['type'], relocs.reference(owners, original, r)) for r in original.relocations if r['section'] == before['index'])
                second = sorted((r['offset'], r['type'], relocs.reference(owners, joined, r)) for r in joined.relocations if r['section'] == after['index'])
                assert first == second
                readonly.append({'section': before['name'], 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()})
    capture = {'object_sha256': sha(q['joined_object']), 'symbols': joined.symbols,
               'sections': joined.sections,
               'relocations': [{k: v for k, v in r.items() if k != 'symbol'} | {'symbol_name': r['symbol']['name']} for r in joined.relocations]}
    return {'status': 'PASS_CURRENT129_PLUS_GENUINE_PROCESS_PAIR11_PARTIAL_NOT_IMAGE_OR_RUNTIME_ACCEPTANCE',
            'joined_sha256': capture['object_sha256'], 'global_strong': 140, 'global_T': 115, 'global_data': 25,
            'actual_remaining_genuine_U': sorted(joined.undefined), 'all_source_owners_preserved': owned,
            'normalized_source_relocations': relocations, 'actual_source_readonly': readonly,
            'new_type_assertions_compiled': True, 'existing_C_header_ABI_evidence_reused_at_unchanged_scope': True,
            'new_C_header_or_native_or_runtime_qualification': False, 'capture': capture}
