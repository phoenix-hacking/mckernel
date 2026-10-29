"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Build CURRENT119 source-only DATA input; reads JSON and validator source, never ELF.
"""
from pathlib import Path
import ast,copy,hashlib,json
D=Path(__file__).resolve().parent;READY=D.parent

def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(row):
 p=Path(row['path']);assert p.suffix in ('.json','.py','.md'),('metadata/source only',str(p));assert ref(p)==row;return p

def unit(row,name):
 p=auth(row);raw=p.read_text();tree=ast.parse(raw);nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name];assert len(nodes)==1;node=nodes[0]
 return dict(source=row,name=name,first_line=node.lineno,last_line=node.end_lineno,source_segment_sha256=hashlib.sha256(ast.get_source_segment(raw,node).encode()).hexdigest(),AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),reuse='EXACT_AUTHENTICATED_NODE_NO_OLD_REVIEW_TOPLEVEL')

def build():
 first=read(READY/'ARTIFACT-INPUTS.SOURCE-ONLY.json');profile=read(auth(first['profile_template']));joint=read(auth(first['source_map']));recipe=read(auth(first['recipe']));adoption=read(auth(first['adoption']));export=read(auth(first['export_manifest']));E=Path(first['source_map']['path']).parent.parent
 assert len(adoption['canonical_rows'])==18 and len(export['files'])==133 and sum(r['relative'].endswith('.rs')for r in export['files'])==122
 assert profile['exact_commands']==recipe['ordered_commands'] and profile['inputs']['objects']==first['objects']
 assert len(first['objects'])==11 and sum(r['replace']for r in first['objects'])==3
 old115=read(E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/independent-artifact-review-preparation-1/INDEPENDENT-ACTUAL-CURRENT115-ARTIFACT-ACCEPTANCE.json')
 old116=E/'new-window-guardian-independent-review-20261028-1/CURRENT116-actual-artifact-review-1';functions=[]
 for source,names in [(first['elf_reader'],['_ReuseElf','_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes']),(first['final_reader'],['Final']),(first['registry_reader'],['cstring','registry']),(old115['reader_sources']['review_consumers115.py'],['literal','relocated_function']),(ref(old116/'review_actual116.py'),['own','allocated']),(ref(old116/'seal_checks116.py'),['warnings']),(ref(READY/'check_first_registry119.py'),['compare'])]:
  functions.extend(unit(source,name)for name in names)
 sourcefacts={'joint_source_map':first['source_map'],'source_adoption':first['adoption'],'closed_source_manifest':first['export_manifest'],'exact119_recipe':first['recipe'],'producer_binding':first['source_binding_result'],'source6153_root':profile['inputs']['source6153'],'SDK21_and_toolchain_image':profile['inputs']['image'],'configuration':profile['inputs']['configuration'],'toolchain_manifest':profile['inputs']['toolchain_manifest'],'toolchain_lock_sha256':profile['inputs']['toolchain_lock_sha256'],'canonical_paths':[r['relative']for r in adoption['canonical_rows']],'source_files':133,'Rust_files':122,'external_modules':profile['inputs']['external_relative_modules'],'link_objects':first['objects'],'source_qualified_ABI_and_declared_providers':{'F03':joint['inherited_F03_ABI'],'F06':joint['inherited_F06_ABI']},'source_qualified_body_provenance':{'F03_registry':joint['inherited_F03_registry'],'F03_remaining':joint['inherited_F03_remaining'],'F06_remaining':joint['inherited_F06_remaining']},'actual_linked_provider_count':None,'actual_linked_storage_count':None,'actual_selected_C_function_count':None}
 slots={'actual_root119_profile':None,'worker_result':None,'producer_contract':None,'Rust_object':None,'generic_C_object':None,'arch_C_object':None,'final_image':None,'link_dependency_file':None,'fresh_origin_five_file_binding':None,'actual_postbuild_source_snapshot_binding':None,'producer_stdout_stderr_four_commands':None,'positive_direct_parent_holder_runner_joins':None,'actual_postbuild_current_custody':None,'independent_artifact_review_result':None}
 validation_slots={k:None for k in ['four_command_source_profile_link_inputs','unique_providers_function_instructions_relocations','storage_ABI_layout_constants_provider_relocations','inherited_consumer_table_timer_idle_runqueue','original389_identity_multiset','actual_warning_and_import_disposition']}
 return {'scope':first['scope'],'schema':'mckernel.current119.fullartifact.source-data-adapter.v1','status':'SOURCE_METADATA_READY_ACTUAL_FULL_ARTIFACT_INPUTS_OPEN','weekly_only':{'allowance':'codex','window_minutes':10080,'reset_upper_bound_epoch':1793774133,'stop_used_percent':100,'prepaid_fallback':False,'runtime_grant':None},'source_facts':sourcefacts,'validator_nodes':functions,'historical_validator_scripts_no_top_level_execution':[ref(old116/n)for n in ['review_actual116.py','review_consumers116.py','review_supplement116.py','seal_checks116.py']],'historical_accepted116':ref(old116/'INDEPENDENT-ACTUAL-CURRENT116-ARTIFACT-ACCEPTANCE.json'),'original389':first['original389_oracle'],'retained_failed118':first['retained_failed118'],'actual_postbuild_inputs':slots,'actual_qualification_results':validation_slots,'artifact_acceptance':None,'native_acceptance':None,'whole_file_acceptance':None,'runtime_authority':None,'source_qualification_is_not_actual_provider_fact':True,'direct_old_review_script_execution_allowed':False}

def validate_source_data(data):
 expected=build();assert data==expected,'Exact source-only adapter data drift; actual slots must remain separately supplied, never inferred.'
 assert all(v is None for v in data['actual_postbuild_inputs'].values()) and all(v is None for v in data['actual_qualification_results'].values())
 assert data['source_facts']['actual_linked_provider_count'] is None
 return True

if __name__=='__main__':
 data=build();validate_source_data(data);p=D/'FULL-ARTIFACT-INPUT.TEMPLATE.NOT-AUTHORITY.json'
 with p.open('x') as f:json.dump(data,f,indent=2);f.write('\n')
 print(json.dumps(dict(status=data['status'],output=ref(p),validator_nodes=len(data['validator_nodes']),actual_ELF_reads=0)))
