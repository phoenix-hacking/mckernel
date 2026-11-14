"""Finite two-data actual object/content gate; reuse qualified ELF machinery."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def actual_object_gate(q):
    for path,digest in q['source_bindings'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    item=q['qualified_ELF_reader']
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('qualified_ELF_reader_for_timer_two_data',item['path'])
    reader=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image=reader.Image(q['compiled_input']['path'])
    definitions,imports=reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes()
    source=json.loads(Path(q['offset_source_contract']).read_text())
    capture=dict(object_sha256=hashlib.sha256(image.raw).hexdigest(),object_bytes=len(image.raw),
                 symbols=image.symbols,sections=image.sections,relocations=image.relocations,
                 all_allocated_file_bytes={section['name']:image.contents(section).hex() for section in image.sections if section['size'] and section['flags']&2 and section['type']!=8},no_runtime_initialization_claim=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(capture,stream,indent=2)
        stream.write('\n')
    assert capture['object_sha256']==q['compiled_input']['sha256'] and capture['object_bytes']==q['compiled_input']['bytes']
    assert set(definitions)==set(image.defined)=={'time_sharing','process_timer_runtime_offsets'} and imports==image.undefined==set()
    assert not [symbol for symbol in image.symbols if symbol['type']==2 and symbol['section']!=0], 'No public/private function owner selected'
    objects=[symbol for symbol in image.symbols if symbol['type']==1 and symbol['section']!=0]
    assert len(objects)==2 and all(symbol['bind']==1 and symbol['other']&3==0 for symbol in objects), 'Exactly two genuine globaldataowners; no extra state/private literals'
    sizes={'time_sharing':('D',4,4),'process_timer_runtime_offsets':('R',120,8)}
    for name,(kind,size,align) in sizes.items():
        symbol=image.defined[name]
        section=image.sections[symbol['section']]
        assert image.kind(symbol)==kind and symbol['size']==size and symbol['type']==1
        assert definitions[name]=={'kind':kind,'size':size}
        assert section['type']==1 and section['flags']&2 and not section['flags']&4
        assert bool(section['flags']&1)==(kind=='D')
        assert section['align']>=align and symbol['value']%align==0 and symbol['value']+size<=section['size']
    assert image.symbol_bytes(image.defined['time_sharing'])==b'\x01\x00\x00\x00', 'Actual original plain CInt1'
    assert not image.relocations, 'Only integer offset values selected; no synthetic provider pointers or dependencies'
    actual_fields=[]
    raw=image.symbol_bytes(image.defined['process_timer_runtime_offsets'])
    assert len(source['slots'])==15
    for index,slot in enumerate(source['slots']):
        assert slot['ordinal']==index and slot['descriptor_member_byte_offset']==index*8
        actual=int.from_bytes(raw[index*8:index*8+8],'little')
        assert actual==slot['expected_actual_compiled_value'], ('Actual source-derived descriptor field',slot['descriptor_field'],actual,slot['source_expression'])
        actual_fields.append(dict(slot,actual_ELF_value=actual,actual_LE_bytes=raw[index*8:index*8+8].hex()))
    # No extra unowned allocated data, readonly constants or synthetic storage.
    for section in image.sections:
        if not section['size'] or not section['flags']&2:
            continue
        assert section['type']==1 and not section['flags']&4
        intervals=sorted((symbol['value'],symbol['value']+symbol['size']) for symbol in objects if symbol['section']==section['index'])
        assert intervals and intervals[0][0]==0 and intervals[-1][1]==section['size']
        assert all(a[1]==b[0] for a,b in zip(intervals,intervals[1:])), 'No uncovered extra allocated state'
    return dict(status='PASS_CALLED_ACTUAL_TWO_TIMER_DATA_SOURCE_CONTENT_UNIQUE_OWNERS',object_sha256=capture['object_sha256'],
                data_owners={name:{'kind':sizes[name][0],'bytes':image.defined[name]['size'],'section':image.sections[image.defined[name]['section']]['name']} for name in sizes},
                original_time_sharing_plain_CInt1=True,actual15_descriptor_offsets_bound_to_real_source=actual_fields,
                function_T=0,genuine_U=[],private_data_or_extra_readonly=[],unique_two_original_data_owners_only=True,
                declared_cfg_and_intended_linux612_Rust_profile_only=True,
                full_C_guard_duplicate_ownership_native_lifecycle_remain_pending=True,
                actual_metadata_capture=q['actual_metadata_capture'],no_function_boot_runtime_or_native_acceptance=True)
