"""Exact current80 + qualified timer/vector + qualified CPU/IPI join; no producer replay."""
from pathlib import Path
import hashlib,importlib.util,json,sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualified(q):
    item=q['qualified_current_join_helpers'];assert sha(item['path'])==item['sha256']
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('qualified_current80_owner_data_helpers',item['path']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    helpers,base,reader=module.qualified(q)
    return module,helpers,base,reader


def qualification(q):
    proof=q['actual_qualification']
    base=json.loads(Path(proof['base_result']).read_text())
    assert base['status']=='PASS_ACTUAL_CURRENT76_PLUS_PRIMITIVE3_AND_DEBUG18_PARTIAL'
    assert base['actual_joined_object_sha256']==q['object_inputs'][0]['sha256']
    assert base['actual_postjoin_called'] and base['all3_direct_waits_joined']
    timer=json.loads(Path(proof['timer_corrected_gate']).read_text());correction=json.loads(Path(proof['timer_correction_result']).read_text())
    assert correction['status']=='PASS_CALLED_ONCE_RETAINED_TIMER_OBJECT_AND_READBACKS_PREDICATE_ONLY_CORRECTION'
    assert correction['actual_object_gate_status']=='PASS_CALLED_ACTUAL_TIMER_VECTOR3_SOURCE_OBJECT_GATE'
    assert correction['new_Popen']==0 and correction['compiler_readback_link_replayed'] is False
    assert timer['status']==correction['actual_object_gate_status']
    assert timer['object_sha256']==correction['actual_object_sha256']==q['object_inputs'][1]['sha256']
    cpu=json.loads(Path(proof['cpu_gate']).read_text());execution=json.loads(Path(proof['cpu_execution']).read_text())
    assert execution['status']=='PASS_ACTUAL_TWO_CPU_IPI_METADATA_READS_AND_CALLED_OBJECT_GATE'
    assert execution['object_gate_called'] and execution['all_started_children_joined']
    assert cpu['status']=='PASS_CALLED_FINITE_CPU_IPI_SOURCE_OBJECT_GATE'
    assert cpu['object_sha256']==execution['compiled_input']['sha256']==q['object_inputs'][2]['sha256']
    assert cpu['real_num_processors_is_U_not_defined']
    return timer,cpu


def prejoin(q):
    assert q['status']=='READY_EXACT_CURRENT80_TIMER_CPU_THREE_OBJECT_JOIN_PENDING_CONCRETE_REVIEW_ROOT_ADMISSION'
    for path,digest in q['inputs'].items():assert sha(path)==digest,path
    timer,cpu=qualification(q);module,helpers,base,reader=qualified(q)
    originals=[reader.Image(item['path']) for item in q['object_inputs']]
    owners=set();imports=set();private=set()
    for item,image in zip(q['object_inputs'],originals):
        assert sha(item['path'])==item['sha256'];base.check_nm(reader,image,item['actual_nm'])
        assert set(image.defined)==set(item['actual_definitions']) and image.undefined==set(item['actual_U'])
        for name,expected in item['actual_definitions'].items():assert dict(kind=image.kind(image.defined[name]),size=image.defined[name]['size'])==expected
        assert not owners&set(image.defined),'Duplicate strong source owner'
        owners|=set(image.defined);imports|=image.undefined
        names={s['name'] for s in image.symbols if s['bind']==0 and s['section']!=0 and s['type'] in (1,2)}
        assert not private&names,'Duplicate private owner name needs concrete normalization review';private|=names
    old,new_timer,new_cpu=originals
    assert len(old.defined)==80 and set(new_timer.defined)==set(timer['actual3T']) and set(new_cpu.defined)==set(cpu['actual3T'])
    assert new_timer.undefined==set(timer['genuine7U']) and new_cpu.undefined==set(cpu['genuine4U'])
    for image in (new_timer,new_cpu):assert not[s for s in image.sections if s['flags']&3==3 and s['size']]
    assert old.kind(old.defined['num_processors'])=='D'
    assert old.defined['num_processors']['size']==4 and 'num_processors' in new_cpu.undefined
    for name,size in q['old2LOCAL_helpers'].items():assert base.local(old,name)['size']==size
    singleton=helpers.private_object(old,q['original_LOCAL_KMSG_LOCK']);assert singleton['size']==4 and old.kind(singleton)=='B'
    module.alias(old,q['delay_alias'])
    prospective=imports-owners;assert prospective==set(q['actual_prospective_U'])
    return dict(status='PASS_CALLED_EXACT_THREE_BACKEND_OPERAND_PREJOIN',predicate_called_before_ld_r=True,
                actual_inputs=[dict(path=item['path'],sha256=item['sha256']) for item in q['object_inputs']],
                prior_global=80,actual_new_timer_T=len(new_timer.defined),actual_new_CPU_T=len(new_cpu.defined),
                actual_global_union=len(owners),actual_prospective_genuine_U=sorted(prospective),duplicate_strong_owners=[],
                qualified_corrected_timer_and_CPU_proofs_consumed_without_gate_or_readback_replay=True,
                actual_num_processors_import_binds_existing_original_D4=True)


def postjoin(q):
    qualification(q);module,helpers,base,reader=qualified(q)
    originals=[reader.Image(item['path']) for item in q['object_inputs']];joined=reader.Image(q['joined_object']);capture=module.retain_capture(q,joined)
    base.check_nm(reader,joined,q['joined_nm']);assert Path(q['joined_elf']).read_bytes()
    owners=set().union(*(set(image.defined) for image in originals));imports=set().union(*(image.undefined for image in originals))-owners
    assert set(joined.defined)==owners and joined.undefined==imports==set(q['actual_prospective_U'])
    evidence,relocations={},{};private_functions=set();private_data=set()
    for original in originals:
        for name,before in original.defined.items():
            after=joined.defined[name];evidence[name]=base.compare_owner(original,before,joined,after)
            a,b=helpers.owner_relocations(base,original,before),helpers.owner_relocations(base,joined,after);assert a==b,('Source relocation changed',name);relocations[name]=b
        for before in original.symbols:
            if before['bind']!=0 or before['section']==0 or before['type'] not in (1,2):continue
            name=before['name']
            if before['type']==2:
                assert name not in private_functions;private_functions.add(name);after=base.local(joined,name)
            else:
                assert name not in private_data;private_data.add(name);after=helpers.private_object(joined,name)
            evidence[name]=base.compare_owner(original,before,joined,after)
            a,b=helpers.owner_relocations(base,original,before),helpers.owner_relocations(base,joined,after);assert a==b,('Private relocation changed',name);relocations[name]=b
    assert {s['name'] for s in joined.symbols if s['bind']==0 and s['section']!=0 and s['type']==2}==private_functions
    assert {s['name'] for s in joined.symbols if s['bind']==0 and s['section']!=0 and s['type']==1}==private_data
    assert len([s for s in joined.symbols if s['type']==1 and s['section']!=0 and 'KMSG_LOCK' in s['name']])==1
    singleton=helpers.private_object(joined,q['original_LOCAL_KMSG_LOCK']);assert singleton['bind']==0 and singleton['size']==4
    module.alias(joined,q['delay_alias']);readonly=[]
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
    old_verbose=[s for s in originals[0].sections if s['name']=='__verbose'];new_verbose=[s for s in joined.sections if s['name']=='__verbose'];assert len(old_verbose)==len(new_verbose)==1
    before,after=old_verbose[0],new_verbose[0];assert before['type']==after['type']==1 and before['flags']==after['flags']==0x200003 and before['align']==after['align']==8 and before['size']==after['size']
    debug=module.data_fields(q,joined)
    return dict(status='PASS_ACTUAL_CURRENT80_PLUS_TIMER_VECTOR_AND_CPU_IPI_PARTIAL',joined_sha256=capture['object_sha256'],
                global_strong=len(joined.defined),global_T=sum(joined.kind(s)=='T' for s in joined.defined.values()),
                global_data=sum(joined.kind(s)!='T' for s in joined.defined.values()),actual_remaining_genuine_U=sorted(joined.undefined),
                all_source_owners_preserved=evidence,normalized_source_relocations=relocations,actual_source_readonly=readonly,retained_debug18=debug,
                actual_joined_metadata=q['joined_capture'],two_formatter_helpers_one_private_KMSG_delay_alias_logger_table_and_real_data_preserved=True,
                no_compile_provider_metadata_replay_function_hardware_IRQ_native_default_Cretirement_or_score_claim=True)
