"""Finite actual CPU/IPI object gate, never an IRQ/function execution or ELF loader."""
from pathlib import Path
import hashlib,importlib.util,json,re,sys


def actual_object_gate(q):
    for path,digest in q['source_bindings'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest,path
    item=q['qualified_ELF_reader'];assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('qualified_CPU_IPI_ELF_reader',item['path']);reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    image=reader.Image(q['compiled_input']['path']);definitions,imports=reader.parse_nm(Path(q['actual_nm']).read_text());assert Path(q['actual_elf']).read_bytes()
    sections=[]
    for section in image.sections:
        entry=dict(section)
        if section['type']==8:entry['NOBITS_declaration_only']=True
        elif section['flags']&2:
            raw=image.contents(section);entry.update(actual_file_bytes_hex=raw.hex(),actual_file_bytes_sha256=hashlib.sha256(raw).hexdigest())
        sections.append(entry)
    capture=dict(object_sha256=hashlib.sha256(image.raw).hexdigest(),object_bytes=len(image.raw),symbols=image.symbols,sections=sections,relocations=image.relocations,genuine_U=sorted(image.undefined),no_runtime_or_native=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:json.dump(capture,stream,indent=2);stream.write('\n')
    assert capture['object_sha256']==q['compiled_input']['sha256']
    assert set(definitions)==set(image.defined) and imports==image.undefined
    assert set(image.defined)==set(q['expected3T']) and image.undefined==set(q['expected4U']),('Unexpected owner/import: STOP before future join',sorted(image.defined),sorted(image.undefined))
    assert not[section for section in image.sections if section['flags']&3==3 and section['size']], 'No source-owned writable data selected'
    assert not[symbol for symbol in image.symbols if symbol['type']==1 and symbol['section']!=0], 'No source data/readonly object selected'
    source_manifest=json.loads(Path(q['source_manifest']).read_text());unit=Path(q['source_unit']).read_text();abi=Path(q['actual_ABI']).read_text()
    packed=[record['source_bytes'] for record in source_manifest['source_blocks'] if record['name']=='X86CpuLocalVariables'];assert len(packed)==1 and packed[0] in abi
    assert packed[0].startswith('#[repr(C, packed)]\npub struct X86CpuLocalVariables {\n    pub processor_id: CULong,\n    pub apic_id: CULong,\n')
    assert 'pub type CULong = u64;\n' in abi and 'pub type CInt = i32;\n' in abi
    assert 'size_of::<CULong>() as CULong,' in unit and 'pub static mut num_processors: CInt;' in unit
    assert 'pub static mut num_processors: CInt =' not in unit
    functions=[];private=[];relocations={};referenced_imports=set()
    for symbol in image.symbols:
        if symbol['type']!=2 or symbol['section']==0:continue
        assert symbol['size']>0 and symbol['other']&3==0 and image.kind(symbol)=='T'
        if symbol['bind']==1:assert symbol['name'] in q['expected3T']
        else:
            assert symbol['bind']==0 and re.fullmatch(q['source_private_raw_v0_pattern'],symbol['name']),('Unexpected private/core helper',symbol['name']);private.append(symbol['name'])
        rows=[row for row in image.relocations if row['section']==symbol['section'] and symbol['value']<=row['offset']<symbol['value']+symbol['size']]
        targets=[row['symbol']['name'] for row in rows if row['symbol']['bind']==1]
        referenced_imports.update(name for name in targets if name in q['expected4U'])
        if symbol['bind']==0:assert targets==['get_x86_cpu_local_variable'],'Exact original typed getter adapter edge'
        elif symbol['name']=='x86_get_interrupt_id_result':assert not targets,'Original callback-driven volatile helper has no genuine global provider call'
        elif symbol['name']=='x86_interrupt_cpu_result':assert set(targets)<= {'x86_get_interrupt_id_result'},'Original callbacks remain dynamic input interfaces'
        else:
            assert 'num_processors' in targets,'Actual mutable processor-count import reference must remain'
            assert set(targets)<=set(q['expected4U'])|{'x86_interrupt_cpu_result','x86_get_interrupt_id_result'}
        functions.append(symbol);relocations[symbol['name']]=dict(bytes=symbol['size'],sha256=hashlib.sha256(image.symbol_bytes(symbol)).hexdigest(),actual_source_relocations=rows)
    assert len(private)<=1 and referenced_imports==set(q['expected4U'])
    readonly=[]
    for section in image.sections:
        if not section['size'] or not section['flags']&2 or section['flags']&5:continue
        assert section['name']=='.eh_frame' and section['type']==0x70000001 and section['flags']==2 and section['align']==8,('Unexpected readonly emission: retain and STOP',section['name'])
        targets=[]
        for row in image.relocations:
            if row['section']!=section['index']:continue
            target=row['symbol'];position=target['value']+row['addend'];owners=[owner['name'] for owner in functions if owner['section']==target['section'] and owner['value']<=position<owner['value']+owner['size']];assert owners,'Native unwind must reference exact selected code owner';targets.append(owners)
        assert targets;readonly.append(dict(name=section['name'],bytes=section['size'],sha256=hashlib.sha256(image.contents(section)).hexdigest(),kind='retained_profile_native_unwind_for_actual_source_functions',targets=targets))
    return dict(status='PASS_CALLED_FINITE_CPU_IPI_SOURCE_OBJECT_GATE',object_sha256=capture['object_sha256'],actual3T={name:image.defined[name]['size'] for name in sorted(image.defined)},genuine4U=sorted(image.undefined),actual_private_adapter_names=private,function_owners=relocations,source_readonly_sections=readonly,real_num_processors_is_U_not_defined=True,packed_ABI_APIC_offset8='Actual repr(C,packed) first2CULong fields, CULong=u64 and unchanged original size_of expression; source/type binding only, no runtime/register-layout substitute',all_actual_metadata_retained=q['actual_metadata_capture'],future_current80_or_later_partial_unbound=True,no_getter_IPI_logger_body_slot_storage_hardware_function_or_native_execution=True)
