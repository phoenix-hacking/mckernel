"""Only actual current engine42f1 + actual bridge33500; no source/provider replay."""
from pathlib import Path
import hashlib,importlib.util,json,sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualified(q):
    item=q['qualified_lock_relocation_helpers'];assert sha(item['path'])==item['sha256']
    sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('bridge_join_qualified_lock_helpers',item['path']);helpers=importlib.util.module_from_spec(spec);spec.loader.exec_module(helpers)
    base=helpers.helpers(q)
    return helpers,base,base.reader(q)


def metadata_pass(q):
    proof=q['required_actual_bridge_metadata']
    assert proof['state']=='ACTUAL_PASS_HASH_BOUND_NOT_PENDING'
    for key in ('execution','object_check','actual_capture'):
        item=proof[key];assert item['sha256'] is not None and sha(item['path'])==item['sha256']
    execution=json.loads(Path(proof['execution']['path']).read_text())
    assert execution['status']=='PASS_ACTUAL_TWO_BRIDGE_METADATA_READS_AND_CALLED_OBJECT_GATE'
    assert execution['object_gate_called'] and execution['all_started_children_joined']
    assert execution['compiled_input']['sha256']==q['new_object_sha256']
    gate=json.loads(Path(proof['object_check']['path']).read_text())
    assert gate['status']=='PASS_CALLED_FINITE_TEN_SCHEDULER_BRIDGE_SOURCE_OBJECT_GATE'
    assert gate['object_sha256']==q['new_object_sha256']
    return gate


def alias(image,names):
    assert len({(image.defined[name]['section'],image.defined[name]['value'],image.defined[name]['size']) for name in names})==1


def prejoin(q):
    assert q['status']=='READY_ACTUAL_METADATA_BOUND_ONLY_THREE_BRIDGE_JOIN_COMMANDS'
    for path,digest in q['inputs'].items():assert sha(path)==digest,path
    gate=metadata_pass(q);helpers,base,reader=qualified(q)
    old,new=reader.Image(q['prior_object']),reader.Image(q['new_object'])
    assert sha(q['prior_object'])==q['prior_object_sha256'] and sha(q['new_object'])==q['new_object_sha256']
    base.check_nm(reader,old,q['actual_prior_nm']);base.check_nm(reader,new,q['actual_new_nm'])
    assert set(old.defined)==set(q['expected_prior66'])
    for name,expected in q['expected_prior66'].items():
        symbol=old.defined[name];assert {'kind':old.kind(symbol),'size':symbol['size']}==expected,name
    assert old.undefined==set(q['actual_prior22U'])
    assert set(new.defined)==set(gate['actual10T']) and new.undefined==set(gate['genuine12U'])
    for name,size in gate['actual10T'].items():assert new.kind(new.defined[name])=='T' and new.defined[name]['size']==size
    assert not(set(old.defined)&set(new.defined)),'Duplicate strong source owner'
    actual_functions={symbol['name']:symbol for symbol in new.symbols if symbol['type']==2 and symbol['section']!=0}
    assert set(actual_functions)==set(gate['function_owners'])
    for name,evidence in gate['function_owners'].items():
        symbol=actual_functions[name];assert symbol['size']==evidence['bytes'] and hashlib.sha256(new.symbol_bytes(symbol)).hexdigest()==evidence['bytes_sha256']
    assert not[section for section in new.sections if section['flags']&3==3 and section['size']]
    singleton=helpers.private_object(old,q['original_LOCAL_KMSG_LOCK']);assert singleton['size']==4 and old.kind(singleton)=='B'
    for name,size in q['old2LOCAL_helpers'].items():assert base.local(old,name)['size']==size
    alias(old,q['delay_alias'])
    prospective=(old.undefined|new.undefined)-(set(old.defined)|set(new.defined))
    return dict(status='PASS_CALLED_EXACT_CURRENT_ENGINE_AND_QUALIFIED_TEN_BRIDGE_PREJOIN',
                old_object_sha256=sha(q['prior_object']),new_object_sha256=sha(q['new_object']),
                old_global_owners=len(old.defined),new_global_owners=len(new.defined),duplicate_strong_owners=[],
                actual_prospective_global_owners=len(set(old.defined)|set(new.defined)),
                actual_prospective_remaining_U=sorted(prospective),new_source_metadata_consumed_without_reexecution=True,
                no_codegen_provider_metadata_function_or_native_replay=True)


def postjoin(q):
    gate=metadata_pass(q);helpers,base,reader=qualified(q)
    old,new,joined=reader.Image(q['prior_object']),reader.Image(q['new_object']),reader.Image(q['joined_object'])
    base.check_nm(reader,joined,q['joined_nm']);assert Path(q['joined_elf']).read_bytes()
    expected=set(old.defined)|set(new.defined);prospective=(old.undefined|new.undefined)-expected
    assert set(joined.defined)==expected and joined.undefined==prospective
    ownership,relocations={},{}
    for original in (old,new):
        for name,before in original.defined.items():
            after=joined.defined[name];ownership[name]=base.compare_owner(original,before,joined,after)
            a,b=helpers.owner_relocations(base,original,before),helpers.owner_relocations(base,joined,after);assert a==b,('Source relocation changed',name);relocations[name]=b
        for before in original.symbols:
            if before['bind']==0 and before['type']==2 and before['section']!=0:
                after=base.local(joined,before['name']);ownership[before['name']]=base.compare_owner(original,before,joined,after)
                a,b=helpers.owner_relocations(base,original,before),helpers.owner_relocations(base,joined,after);assert a==b;relocations[before['name']]=b
    for record in gate['source_private_readonly_data']:
        before=record['symbol'];after=helpers.private_object(joined,before['name']);ownership[before['name']]=base.compare_owner(new,before,joined,after)
        assert helpers.owner_relocations(base,new,before)==helpers.owner_relocations(base,joined,after)
    name=q['original_LOCAL_KMSG_LOCK'];before,after=helpers.private_object(old,name),helpers.private_object(joined,name)
    ownership[name]=base.compare_owner(old,before,joined,after);assert after['bind']==0 and after['size']==4
    assert len([symbol for symbol in joined.symbols if symbol['type']==1 and symbol['section']!=0 and 'KMSG_LOCK' in symbol['name']])==1
    alias(joined,q['delay_alias']);tables={}
    actual_new_tables=[record['name'] for record in gate['exact_source_readonly_sections'] if record['kind']=='compiler_switch_table_owned_only_by_complete_source_logger']
    for original,names in [(old,q['old_source_owned_tables']),(new,actual_new_tables)]:
        for name in names:
            before=[section for section in original.sections if section['name']==name];after=[section for section in joined.sections if section['name']==name];assert len(before)==len(after)==1;before,after=before[0],after[0]
            assert before['type']==after['type']==1 and before['flags']==after['flags'] and after['align']>=before['align'];assert original.contents(before)==joined.contents(after)
            a=sorted((row['offset'],row['type'],helpers.reference(base,original,row)) for row in original.relocations if row['section']==before['index'])
            b=sorted((row['offset'],row['type'],helpers.reference(base,joined,row)) for row in joined.relocations if row['section']==after['index']);assert a==b
            tables[name]=dict(bytes=before['size'],sha256=hashlib.sha256(original.contents(before)).hexdigest(),actual_source_relocations=b)
    strings={}
    for record in gate['exact_source_readonly_sections']:
        if record['kind']!='exact_original_logger_format_label_strings':continue
        section=[section for section in joined.sections if section['name']==record['name']];assert len(section)==1;section=section[0];assert section['type']==1 and section['flags']&0x20 and not section['flags']&5;raw=joined.contents(section)
        for literal in record['source_literals']:assert bytes.fromhex(literal['bytes_hex']) in raw
        strings[record['name']]=dict(all_original_NUL_strings_or_merged_suffixes_retained=True,actual_function_relocation_string_targets_preserved=True)
    return dict(status='PASS_ACTUAL_CURRENT_ENGINE_PLUS_TEN_GENUINE_BRIDGE_PARTIAL',global_strong=len(joined.defined),
                global_T=sum(joined.kind(symbol)=='T' for symbol in joined.defined.values()),
                global_data=sum(joined.kind(symbol)!='T' for symbol in joined.defined.values()),
                actual_remaining_genuine_U=sorted(joined.undefined),all_old66_and_actual_new_owners_preserved=ownership,
                actual_global_and_private_source_relocations=relocations,actual_source_tables=tables,actual_logger_strings=strings,
                one_original_LOCAL_KMSG_LOCK_and_delay_alias_preserved=True,
                no_function_logging_state_lock_timer_IRQ_boot_native_default_or_score_claim=True)
