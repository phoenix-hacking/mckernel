"""Finite five-object current/provider composition; every qualification must be actual."""
from pathlib import Path
import hashlib,importlib.util,json,sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualified(q):
    item=q['qualified_current_helpers'];assert sha(item['path'])==item['sha256']
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('qualified_real_current_owner_data_helpers',item['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    helpers,base,reader=module.qualified(q)
    return module,helpers,base,reader


def qualification(q):
    base=json.loads(Path(q['base_result']).read_text())
    assert base['status']=='PASS_ACTUAL_CURRENT80_PLUS_TIMER_VECTOR_AND_CPU_IPI_PARTIAL'
    assert base['actual_joined_object_sha256']==q['object_inputs'][0]['sha256']
    assert base['actual_postjoin_called'] and base['all3_direct_waits_joined']
    roles=('timer_callbacks','IPI_logger_descriptor','local_getter_slot','timer_data_Linux6_12')
    for index,role in enumerate(roles,1):
        proof=q['actual_qualification'][role]
        assert proof['state']=='ACTUAL_PASS_FROZEN_NOT_PENDING'
        gate=json.loads(Path(proof['gate']['path']).read_text())
        assert sha(proof['gate']['path'])==proof['gate']['sha256']
        assert gate['status']==proof['exact_gate_status']
        assert gate[proof['object_sha256_key']]==q['object_inputs'][index]['sha256']
        for item in proof['actual_pass_receipts']:
            assert sha(item['path'])==item['sha256'];receipt=json.loads(Path(item['path']).read_text())
            for key,value in item['exact_required_fields'].items():assert receipt[key]==value,(role,key)
    assert q['timer_data_source_profile']['scope']=='ONLY_the_two_timer_data_object'
    assert q['timer_data_source_profile']['actual_cfg_flags']
    assert q['timer_data_source_profile']['source_profile_reviewed'] is True


def prejoin(q):
    assert q['status']=='READY_ONLY_FIVE_MATCHING_QUALIFIED_OBJECTS_JOIN3_PENDING_REVIEW_ROOT_ADMISSION'
    for path,digest in q['inputs'].items():assert sha(path)==digest,path
    qualification(q);module,helpers,base,reader=qualified(q)
    assert len(q['object_inputs'])==5
    originals=[reader.Image(item['path']) for item in q['object_inputs']]
    owners=set();imports=set();private=set();verbose=[]
    for item,image in zip(q['object_inputs'],originals):
        assert sha(item['path'])==item['sha256'];base.check_nm(reader,image,item['actual_nm'])
        assert set(image.defined)==set(item['actual_definitions']) and image.undefined==set(item['actual_U'])
        for name,expected in item['actual_definitions'].items():assert dict(kind=image.kind(image.defined[name]),size=image.defined[name]['size'])==expected,name
        assert not owners&set(image.defined),'Strong source/partition owner collision before ld-r';owners|=set(image.defined);imports|=image.undefined
        names={s['name'] for s in image.symbols if s['bind']==0 and s['section']!=0 and s['type'] in (1,2)}
        assert not private&names,'Private name collision needs concrete source normalization review';private|=names
        sections=[s for s in image.sections if s['name']=='__verbose'];assert len(sections)<=1
        if sections:
            section=sections[0];assert section['type']==1 and section['flags']==0x200003 and section['align']==8
            verbose.append(dict(role=item['role'],bytes=section['size'],retained_flags='0x200003',align=8))
    old=originals[0]
    assert len(old.defined)==86
    for name,size in q['old2LOCAL_helpers'].items():assert base.local(old,name)['size']==size
    singleton=helpers.private_object(old,q['original_LOCAL_KMSG_LOCK']);assert singleton['size']==4 and old.kind(singleton)=='B'
    module.alias(old,q['delay_alias'])
    # This source partition adds exactly its real single descriptor, not replicas.
    ipi=originals[2];descriptors=[s for s in ipi.symbols if s['type']==1 and s['section']!=0 and ipi.sections[s['section']]['name']=='__verbose']
    assert len(descriptors)==1 and descriptors[0]['size']==32
    getter=originals[3];slots=[s for s in getter.symbols if s['type']==1 and s['section']!=0]
    assert len(slots)==1 and slots[0]['size']==8
    prospective=imports-owners;assert prospective==set(q['actual_prospective_U'])
    return dict(status='PASS_CALLED_FIVE_MATCHING_CURRENT_AND_PROVIDER_PREJOIN',actual_inputs=[dict(path=item['path'],sha256=item['sha256']) for item in q['object_inputs']],
                duplicate_strong_owners=[],actual_global_union=len(owners),actual_remaining_genuine_U=sorted(prospective),
                actual_verbose_inputs=verbose,new_real_IPI_descriptor_name=descriptors[0]['name'],new_real_local_slot_name=slots[0]['name'],
                source_cfg_Linux6_12_applies_ONLY_two_timer_data_object=True,
                actual_qualifications_consumed_without_producer_metadata_gate_reexecution=True)


def cstring_target(image,relocation):
    section_index,position,_=image.pointer_target(relocation,1);section=image.sections[section_index];raw=image.contents(section);end=raw.index(0,position)+1
    return raw[position:end]


def postjoin(q):
    qualification(q);module,helpers,base,reader=qualified(q);originals=[reader.Image(item['path']) for item in q['object_inputs']]
    joined=reader.Image(q['joined_object']);capture=module.retain_capture(q,joined);base.check_nm(reader,joined,q['joined_nm']);assert Path(q['joined_elf']).read_bytes()
    owners=set().union(*(set(image.defined) for image in originals));imports=set().union(*(image.undefined for image in originals))-owners
    assert set(joined.defined)==owners and joined.undefined==imports==set(q['actual_prospective_U'])
    ownership,relocations={},{};private_functions=set();private_data=set()
    for original in originals:
        for name,before in original.defined.items():
            after=joined.defined[name];ownership[name]=base.compare_owner(original,before,joined,after)
            first,second=helpers.owner_relocations(base,original,before),helpers.owner_relocations(base,joined,after);assert first==second,('Source owner relocation changed',name);relocations[name]=second
        for before in original.symbols:
            if before['bind']!=0 or before['section']==0 or before['type'] not in (1,2):continue
            name=before['name']
            if before['type']==2:
                assert name not in private_functions;private_functions.add(name);after=base.local(joined,name)
            else:
                assert name not in private_data;private_data.add(name);after=helpers.private_object(joined,name)
            ownership[name]=base.compare_owner(original,before,joined,after)
            first,second=helpers.owner_relocations(base,original,before),helpers.owner_relocations(base,joined,after);assert first==second;relocations[name]=second
    assert {s['name'] for s in joined.symbols if s['bind']==0 and s['section']!=0 and s['type']==2}==private_functions
    assert {s['name'] for s in joined.symbols if s['bind']==0 and s['section']!=0 and s['type']==1}==private_data
    assert len([s for s in joined.symbols if s['type']==1 and s['section']!=0 and 'KMSG_LOCK' in s['name']])==1
    singleton=helpers.private_object(joined,q['original_LOCAL_KMSG_LOCK']);assert singleton['size']==4 and singleton['bind']==0;module.alias(joined,q['delay_alias'])
    readonly=[]
    for original in originals:
        for before in original.sections:
            if not before['size'] or not before['flags']&2 or before['flags']&5 or before['name']=='.eh_frame':continue
            matches=[s for s in joined.sections if s['name']==before['name']];assert len(matches)==1;after=matches[0]
            assert before['type']==after['type']==1 and before['flags']==after['flags'] and after['align']>=before['align']
            raw,actual=original.contents(before),joined.contents(after)
            if before['flags']&0x20:
                at=0
                while at<len(raw):
                    end=raw.index(0,at)+1;assert raw[at:end] in actual;at=end
                readonly.append(dict(name=before['name'],exact_original_NUL_contents_retained=True,original_bytes=len(raw)))
            else:
                assert raw==actual
                a=sorted((r['offset'],r['type'],helpers.reference(base,original,r)) for r in original.relocations if r['section']==before['index'])
                b=sorted((r['offset'],r['type'],helpers.reference(base,joined,r)) for r in joined.relocations if r['section']==after['index']);assert a==b
                readonly.append(dict(name=before['name'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),actual_source_relocations=b))
    verbose_inputs=[s for image in originals for s in image.sections if s['name']=='__verbose'];verbose=[s for s in joined.sections if s['name']=='__verbose'];assert len(verbose)==1;verbose=verbose[0]
    assert all(s['type']==1 and s['flags']==0x200003 and s['align']==8 for s in verbose_inputs)
    assert verbose['type']==1 and verbose['flags']==0x200003 and verbose['align']==8 and verbose['size']==sum(s['size'] for s in verbose_inputs)
    old_debug=module.data_fields(q,joined)
    ipi=originals[2];descriptor=[s for s in ipi.symbols if s['type']==1 and s['section']!=0 and ipi.sections[s['section']]['name']=='__verbose'];assert len(descriptor)==1;before=descriptor[0]
    after=joined.defined[before['name']] if before['bind']==1 else helpers.private_object(joined,before['name'])
    a,b=ipi.symbol_bytes(before),joined.symbol_bytes(after);assert len(a)==len(b)==32 and a==b
    old_relocs={r['offset']-before['value']:r for r in ipi.relocations if r['section']==before['section'] and before['value']<=r['offset']<before['value']+32}
    new_relocs={r['offset']-after['value']:r for r in joined.relocations if r['section']==after['section'] and after['value']<=r['offset']<after['value']+32}
    assert set(old_relocs)==set(new_relocs)
    targets={}
    for offset in (0,8):
        assert offset in old_relocs and old_relocs[offset]['type']==new_relocs[offset]['type']==1
        original=cstring_target(ipi,old_relocs[offset]);assert original==cstring_target(joined,new_relocs[offset]);targets[str(offset)]=original.hex()
    descriptor_fields=dict(name=before['name'],size=32,original_line_flags=int.from_bytes(a[24:28],'little'),retained_fmt_raw_bytes=a[16:24].hex(),exact_file_function_NUL_targets=targets,retained_trailing_ABI_padding=a[28:32].hex())
    return dict(status='PASS_FIVE_MATCHING_CURRENT_AND_GENUINE_NEXT_PROVIDER_PARTIAL',joined_sha256=capture['object_sha256'],global_strong=len(joined.defined),
                global_T=sum(joined.kind(s)=='T' for s in joined.defined.values()),global_data=sum(joined.kind(s)!='T' for s in joined.defined.values()),
                actual_remaining_genuine_U=sorted(joined.undefined),all_source_owners_preserved=ownership,normalized_source_relocations=relocations,actual_source_readonly=readonly,
                retained_debug18=old_debug,new_real_IPI_descriptor=descriptor_fields,actual_retained_verbose_bytes=verbose['size'],real8Bslot_owned_not_fabricated=True,
                source_Linux6_12_cfg_ONLY_two_timer_data_object=True,no_compiler_metadata_function_hardware_IRQ_native_default_Cretirement_or_score_claim=True)
