"""Exact two-input string-provider join; reuse qualified readers/owner comparison."""
from pathlib import Path
import hashlib
import importlib.util
import json

def helpers(q):
 p=Path(q['qualified_join_helpers']['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==q['qualified_join_helpers']['sha256'];spec=importlib.util.spec_from_file_location('qualified_kprintf_join_helpers',p);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h);return h,h.reader(q)

def prejoin(q):
 h,m=helpers(q)
 for item in q['object_inputs']:assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
 new,old=[m.Image(item['path']) for item in q['object_inputs']];h.check_nm(m,new,q['actual_new_nm']);h.check_nm(m,old,q['actual_prior_nm']);e=q['expected'];core=json.loads(Path(q['actual_core_check']).read_text())
 assert core['object_sha256']==q['object_inputs'][0]['sha256'] and core['direct_indirect_self_cross_helper_calls']==0 and core['text_relocations']==[] and core['genuine_U']==[]
 assert set(new.defined)=={'memset','strnlen'} and new.undefined==set()
 for name,size in e['new2_T'].items():assert new.kind(new.defined[name])=='T' and new.defined[name]['size']==size
 assert set(old.defined)==set(e['prior42_owners']) and old.undefined==set(e['prior23_U'])
 for name,fields in e['prior42_owners'].items():assert old.kind(old.defined[name])==fields['kind'] and old.defined[name]['size']==fields['bytes']
 assert not(set(new.defined)&set(old.defined)) and {'memset','strnlen'}<=old.undefined
 for name,size in e['prior_two_private_helpers'].items():assert h.local(old,name)['size']==size
 prospective=(old.undefined|new.undefined)-(set(old.defined)|set(new.defined));assert prospective==set(e['joined21_U']) and len(prospective)==21
 return {'status':'PASS_CALLED_PREJOIN_EXACT_TWO_REAL_STRING_ROOTS_AND_CURRENT_42_OWNER_COHORT','new_global_T':2,'new_U':[],'prior_strong':42,'duplicate_strong_owners':[],'only_resolved':['memset','strnlen'],'prospective44_strong_21_genuine_U':True,'existing_core_no_call_qualification_reused':True,'no_compile_or_runtime':True}

def postjoin(q):
 h,m=helpers(q);new,old=[m.Image(item['path']) for item in q['object_inputs']];joined=m.Image(q['joined_object']);h.check_nm(m,joined,q['joined_nm']);expected=set(old.defined)|set(new.defined);assert len(expected)==44 and set(joined.defined)==expected and joined.undefined==set(q['expected']['joined21_U'])
 assert sum(joined.kind(s)=='T' for s in joined.defined.values())==35
 owners={};relocs={}
 for original in (old,new):
  for name,before in original.defined.items():
   after=joined.defined[name];owners[name]=h.compare_owner(original,before,joined,after);a=h.function_relocations(original,before);b=h.function_relocations(joined,after);assert a==b,('relocationschanged',name);relocs[name]=b
 for name in q['expected']['prior_two_private_helpers']:
  before,after=h.local(old,name),h.local(joined,name);owners[name]=h.compare_owner(old,before,joined,after);assert h.function_relocations(old,before)==h.function_relocations(joined,after),name
 tables={}
 for name in q['expected']['prior_jump_table_sections']:
  a=[s for s in old.sections if s['name']==name];b=[s for s in joined.sections if s['name']==name];assert len(a)==len(b)==1;a,b=a[0],b[0];assert a['type']==b['type']==1 and not b['flags']&5 and old.contents(a)==joined.contents(b)
  first=sorted((r['offset'],r['type'],h.reference(old,r)) for r in old.relocations if r['section']==a['index']);second=sorted((r['offset'],r['type'],h.reference(joined,r)) for r in joined.relocations if r['section']==b['index']);assert first==second;tables[name]={'bytes':a['size'],'relocations':len(first)}
 return {'status':'PASS_CALLED_STRING_PROVIDER_UNIQUE_PARTIAL_JOIN','strong_definitions':44,'global_T':35,'global_data':9,'genuine_U':sorted(joined.undefined),'only_resolved':['memset','strnlen'],'all42prior_and2new_owners_sizes_bytes_preserved':True,'all_prior_relocations_private_helpers_jump_tables_preserved':True,'owner_byte_evidence':owners,'actual_source_relocations':relocs,'source_tables':tables,'no_initialized_HOST_or_function_native_runtime_claim':True}
