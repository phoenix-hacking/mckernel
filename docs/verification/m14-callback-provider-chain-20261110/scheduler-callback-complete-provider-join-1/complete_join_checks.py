"""Finite current122 + qualified callback targets and backend data; preparation pending data gate, no producer replay."""
from pathlib import Path
import hashlib,importlib.util,json,sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualified(q):
    item=q['qualified_current_helpers'];assert sha(item['path'])==item['sha256']
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('qualified_current_real_owner_data_helpers',item['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    helpers,base,reader=module.qualified(q)
    return module,helpers,base,reader


def qualification(q):
    assert q['qualification_state']=='ACTUAL_TARGET_AND_BACKEND_DATA_GATES_PASS'
    prior=json.loads(Path(q['base_result']).read_text())
    assert prior['status']=='PASS_CURRENT117_PLUS_GENUINE_CALLBACK_PUBLICATION_PARTIAL'
    assert prior['actual_joined_object_sha256']==q['object_inputs'][0]['sha256']
    assert prior['actual_postjoin_called'] and prior['all3_direct_waits_joined']
    assert len(q['actual_new_qualifications'])==2
    for index,proof in enumerate(q['actual_new_qualifications'],1):
        for key in ('gate','execution','capture'):
            item=proof[key];assert item['sha256'] and sha(item['path'])==item['sha256']
        gate=json.loads(Path(proof['gate']['path']).read_text())
        assert gate['status']==proof['exact_gate_status'] and gate['object_sha256']==q['object_inputs'][index]['sha256']
        execution=json.loads(Path(proof['execution']['path']).read_text())
        for key,value in proof['exact_execution_fields'].items():assert execution[key]==value


def publication_slots(image):
    for name,size in [('x86_cpu_x2apic_mode',4),('lapic_write',8),('lapic_read',8),('lapic_icr_write',8),('lapic_wait_icr_idle',8),('x86_issue_ipi',8)]:
        owner=image.defined[name];assert image.kind(owner)=='B' and owner['size']==size
    return dict(six_original_preboot_BSS_owners_retained=True,no_publisher_store_or_target_function_executed=True)


def lower_alias(image):
    a,b=(image.defined[name] for name in ('wrmsr','x86_write_msr_bridge'))
    assert a['type']==b['type']==2 and a['bind']==b['bind']==1
    assert (a['section'],a['value'],a['size'])==(b['section'],b['value'],b['size']) and a['size']==15
    assert image.defined['ihk_mc_mb']['size']==4 and image.defined['x86_cpu_pause_bridge']['size']==12
    slot=image.defined['lapic_read'];assert slot['size']==8 and image.kind(slot)=='B'
    return dict(names=['wrmsr','x86_write_msr_bridge'],physical_ranges=1,bytes=15,source_names_not_rewritten=True)


def prejoin(q):
    assert q['status']=='READY_CURRENT122_PLUS_TARGET_AND_BACKEND_DATA_JOIN3_PENDING_REVIEW_ROOT_ADMISSION'
    for path,digest in q['inputs'].items():assert sha(path)==digest,path
    qualification(q);module,helpers,base,reader=qualified(q);assert len(q['object_inputs'])==3
    originals=[reader.Image(item['path']) for item in q['object_inputs']];owners=set();imports=set();private=set()
    for item,image in zip(q['object_inputs'],originals):
        assert sha(item['path'])==item['sha256'];base.check_nm(reader,image,item['actual_nm'])
        assert set(image.defined)==set(item['actual_definitions']) and image.undefined==set(item['actual_U'])
        for name,expected in item['actual_definitions'].items():assert dict(kind=image.kind(image.defined[name]),size=image.defined[name]['size'])==expected
        assert not owners&set(image.defined),'Duplicate strong source/partition owner';owners|=set(image.defined);imports|=image.undefined
        names={s['name'] for s in image.symbols if s['bind']==0 and s['section']!=0 and s['type'] in (1,2)}
        assert not private&names,'Private-name overlap requires concrete source review';private|=names
    old=originals[0];assert len(old.defined)==122
    assert old.defined['cpu_pause']['size']==3 and old.kind(old.defined['cpu_pause'])=='T'
    lower_alias(old)
    publication_slots(old)
    for name in ('apic_read','apic_write','x2apic_read','x2apic_write','rdmsr'):assert originals[1].kind(originals[1].defined[name])=='T'
    assert originals[1].undefined=={'lapic_vp','wrmsr','x86_local_apic_base_msr'}
    assert originals[2].undefined==set()
    for name in ('lapic_vp','x86_local_apic_base_msr'):assert name in originals[2].defined
    assert originals[2].kind(originals[2].defined['lapic_vp'])=='B' and originals[2].defined['lapic_vp']['size']==8
    assert originals[2].kind(originals[2].defined['x86_local_apic_base_msr'])=='R' and originals[2].symbol_bytes(originals[2].defined['x86_local_apic_base_msr'])==bytes.fromhex('00080000')
    for name,size in q['old2LOCAL_helpers'].items():assert base.local(old,name)['size']==size
    singleton=helpers.private_object(old,q['original_LOCAL_KMSG_LOCK']);assert singleton['size']==4 and old.kind(singleton)=='B';module.alias(old,q['delay_alias'])
    # Existing real save/restore providers must be reused, never duplicated or
    # replaced by HOST/fake callbacks. Exact bytes remain in the passed base.
    assert old.kind(old.defined['cpu_disable_interrupt_save'])=='T' and old.kind(old.defined['cpu_restore_interrupt'])=='T'
    prospective=imports-owners;assert prospective==set(q['actual_prospective_U'])
    return dict(status='PASS_CALLED_CURRENT122_TARGET_BACKEND_DATA_PREJOIN',predicate_called_before_ld_r=True,
                actual_inputs=[dict(path=item['path'],sha256=item['sha256']) for item in q['object_inputs']],duplicate_strong_owners=[],
                actual_global_union=len(owners),actual_remaining_genuine_U=sorted(prospective),old_real_save_restore_owners_reused=True,
                actual_provider_gates_consumed_without_producer_readback_or_gate_reexecution=True)


def cstring_target(image,relocation):
    index,at,_=image.pointer_target(relocation,1);raw=image.contents(image.sections[index]);return raw[at:raw.index(0,at)+1]


def postjoin(q):
    qualification(q);module,helpers,base,reader=qualified(q);originals=[reader.Image(item['path']) for item in q['object_inputs']]
    joined=reader.Image(q['joined_object']);alias=lower_alias(joined);slots=publication_slots(joined);capture=module.retain_capture(q,joined);base.check_nm(reader,joined,q['joined_nm']);assert Path(q['joined_elf']).read_bytes()
    owners=set().union(*(set(image.defined) for image in originals));imports=set().union(*(image.undefined for image in originals))-owners
    assert set(joined.defined)==owners and joined.undefined==imports==set(q['actual_prospective_U'])
    ownership,relocations={},{};private_functions=set();private_data=set()
    for original in originals:
        for name,before in original.defined.items():
            after=joined.defined[name];ownership[name]=base.compare_owner(original,before,joined,after)
            a,b=helpers.owner_relocations(base,original,before),helpers.owner_relocations(base,joined,after);assert a==b,('Source relocation changed',name);relocations[name]=b
        for before in original.symbols:
            if before['bind']!=0 or before['section']==0 or before['type'] not in (1,2):continue
            name=before['name']
            if before['type']==2:
                assert name not in private_functions;private_functions.add(name);after=base.local(joined,name)
            else:
                assert name not in private_data;private_data.add(name);after=helpers.private_object(joined,name)
            ownership[name]=base.compare_owner(original,before,joined,after)
            a,b=helpers.owner_relocations(base,original,before),helpers.owner_relocations(base,joined,after);assert a==b;relocations[name]=b
    assert {s['name'] for s in joined.symbols if s['bind']==0 and s['section']!=0 and s['type']==2}==private_functions
    assert {s['name'] for s in joined.symbols if s['bind']==0 and s['section']!=0 and s['type']==1}==private_data
    assert len([s for s in joined.symbols if s['type']==1 and s['section']!=0 and 'KMSG_LOCK' in s['name']])==1
    singleton=helpers.private_object(joined,q['original_LOCAL_KMSG_LOCK']);assert singleton['size']==4 and singleton['bind']==0;module.alias(joined,q['delay_alias'])
    readonly=[]
    for original in originals:
        for before in original.sections:
            if not before['size'] or not before['flags']&2 or before['flags']&5 or before['name']=='.eh_frame':continue
            matches=[s for s in joined.sections if s['name']==before['name']];assert len(matches)==1;after=matches[0]
            assert before['type']==after['type']==1 and before['flags']==after['flags'] and after['align']>=before['align'];raw,actual=original.contents(before),joined.contents(after)
            if before['flags']&0x20:
                at=0
                while at<len(raw):
                    end=raw.index(0,at)+1;assert raw[at:end] in actual;at=end
                readonly.append(dict(name=before['name'],original_NUL_contents_retained=True,original_bytes=len(raw)))
            else:
                assert raw==actual
                a=sorted((r['offset'],r['type'],helpers.reference(base,original,r)) for r in original.relocations if r['section']==before['index'])
                b=sorted((r['offset'],r['type'],helpers.reference(base,joined,r)) for r in joined.relocations if r['section']==after['index']);assert a==b
                readonly.append(dict(name=before['name'],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),actual_source_relocations=b))
    verbose_inputs=[s for image in originals for s in image.sections if s['name']=='__verbose'];verbose=[s for s in joined.sections if s['name']=='__verbose'];assert len(verbose)==1;verbose=verbose[0]
    assert all(s['type']==1 and s['flags']==0x200003 and s['align']==8 for s in verbose_inputs)
    assert verbose['type']==1 and verbose['flags']==0x200003 and verbose['align']==8 and verbose['size']==sum(s['size'] for s in verbose_inputs)
    debug=module.data_fields(q,joined);old=originals[0];before=old.defined['x86_interrupt_log_debug'];after=joined.defined[before['name']]
    a,b=old.symbol_bytes(before),joined.symbol_bytes(after);assert len(a)==len(b)==32 and a==b
    before_relocs={r['offset']-before['value']:r for r in old.relocations if r['section']==before['section'] and before['value']<=r['offset']<before['value']+32}
    after_relocs={r['offset']-after['value']:r for r in joined.relocations if r['section']==after['section'] and after['value']<=r['offset']<after['value']+32};assert set(before_relocs)==set(after_relocs)
    for at in (0,8):assert cstring_target(old,before_relocs[at])==cstring_target(joined,after_relocs[at])
    assert old.defined['x86_issue_ipi']['size']==joined.defined['x86_issue_ipi']['size']==8
    return dict(status='PASS_CURRENT122_PLUS_GENUINE_TARGETS_AND_BACKEND_DATA_PARTIAL',joined_sha256=capture['object_sha256'],global_strong=len(joined.defined),
                global_T=sum(joined.kind(s)=='T' for s in joined.defined.values()),global_data=sum(joined.kind(s)!='T' for s in joined.defined.values()),
                actual_remaining_genuine_U=sorted(joined.undefined),all_source_owners_preserved=ownership,normalized_source_relocations=relocations,actual_source_readonly=readonly,
                retained_debug18=debug,real_IPI32descriptor_and8Bslot_retained=True,actual_lower_alias=alias,publication_slot_boundaries=slots,no_publisher_or_target_function_run=True,one_privateKMSG_twoformatterhelpers_and_delayalias_preserved=True,
                no_compiler_provider_readback_gate_function_hardware_IRQ_native_default_or_score_claim=True)
