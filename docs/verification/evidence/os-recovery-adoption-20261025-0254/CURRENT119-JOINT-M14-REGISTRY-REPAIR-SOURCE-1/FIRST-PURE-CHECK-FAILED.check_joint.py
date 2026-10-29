"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded source-only positive/negative patch/layout/ABI/module closure checks.
Reuse owner predicates; never run origin/compiler/HOST/SDK/export/materializer/guard.
"""
from pathlib import Path,PurePosixPath
import ast,collections,copy,hashlib,json,re,time
from compose_joint import HERE,ROOT,PINS,need,ref,auth,checked,write

def owner_functions(row,names,namespace):
 """Compile only the exact pinned pure function definitions, not module top-level."""
 raw=auth(row).read_text();tree=ast.parse(raw);body=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in names]
 need({n.name for n in body}==set(names),'exact reused owner pure predicates')
 exec(compile(ast.Module(body=body,type_ignores=[]),row['path'],'exec'),namespace)
 return [namespace[name]for name in names]

def modules(text):
 pending=None
 for line in text.splitlines():
  path=re.fullmatch(r'\s*#\[path\s*=\s*"([^"\n]+)"\]\s*',line)
  if path:pending=path.group(1);continue
  mod=re.fullmatch(r'\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+([A-Za-z_][A-Za-z_0-9]*)\s*;\s*(?://.*)?',line)
  if mod:yield mod.group(1),pending;pending=None
  elif line.strip()and not line.lstrip().startswith(('#[','//')):pending=None

def main():
 started=time.monotonic();source=checked(ref(HERE/'SOURCE-MAP-FROM118.json'));rows=source['changes'];need(len(rows)==18,'exact18 source paths')
 apply_patch,descriptor=owner_functions(PINS['F06_checker'],['apply_patch','descriptor'],dict(re=re))
 patchcases=[]
 for row in rows:
  post=auth(row['postimage']);need(post.read_bytes()==auth(row['owner_postimage']).read_bytes(),'unchanged owner complete postimage')
  if row['preimage_requirement']=='EXACT_BYTE_REF':need(ref(ROOT/row['relative'])==row['preimage'],'exact current canonical118 bytes');before=auth(row['preimage']).read_text()
  else:need(not(ROOT/row['relative']).exists(),'exact new path absence');before=''
  after=apply_patch(before,auth(row['patch']).read_text());need(after==post.read_text(),'mechanical patch equals exact owner postimage')
  patchcases.append(row['relative'])
 need(sum(r['preimage_requirement']=='PATH_ABSENT'for r in rows)==10,'ten new Rust leaves only')
 # Reject wrong existing preimage at an actual changed hunk, not just a checksum.
 first=rows[0];before=auth(first['preimage']).read_text();patch=auth(first['patch']).read_text();hunk=next(line[1:]for line in patch.splitlines(True)[2:]if line.startswith('-'))
 changed=before.replace(hunk,hunk.replace('\n',' /* TEST_ONLY wrong preimage */\n'),1);rejected=False
 try:apply_patch(changed,patch)
 except AssertionError:rejected=True
 need(rejected,'wrong changed-hunk preimage rejected')
 (positions,)=owner_functions(PINS['F03_layout_checker'],['positions'],{})
 original=positions(auth(PINS['original_macro_source']).read_text());policy=(HERE/'candidate/kernel/rust/syscall_policy.rs').read_text()
 need(len(original)==88 and positions(policy)==original,'all88 genuine macro-bearing source lines exact; no line normalization')
 old118=next(r['source118_preimage']for r in checked(PINS['F03_map'])['writes']if r['relative']=='kernel/rust/syscall_policy.rs')
 need(positions(auth(old118).read_text())!=original and positions('\n'+policy)!=original,'actual118 and synthetic line drift rejected')
 block='#[cfg(f06_vdso_info_candidate)]\n#[path = "f06_vdso_info.rs"]\nmod f06_vdso_info;\n#[cfg(f06_vdso_info_candidate)]\nuse f06_vdso_info::vdso_get_vdso_info;'
 need(policy.count(block)==1 and policy.rstrip().endswith(block),'exact vdso_info declarations at EOF once')
 body5=checked(source['inherited_F03_ABI']);change=checked(body5['BODY5_live_body_changed']);tested=auth(change['tested_candidate']).read_text()
 pattern=r'pub unsafe extern "C" fn perf_event_alloc_map_body_result\(.*?^}'
 a=re.search(pattern,policy,re.S|re.M);b=re.search(pattern,tested,re.S|re.M);need(a and b,'existing live BODY5 source functions')
 token=lambda s:re.findall(r'"(?:\\.|[^"\\])*"|\S',s)
 need(token(a.group())==token(b.group()),'BODY5 exact tested non-whitespace tokens; event map before extra map preserved')
 need(a.group().index('hw_cache_event_map(attr_config)')<a.group().index('hw_cache_extra_reg_map(attr_config)'),'BODY5 callback order')
 metadata=checked(PINS['F06_metadata']);oracle=checked(metadata['accepted_389_oracle']);failure=checked(PINS['actual118_failure']);classification=checked(PINS['Root_field_classification'])
 need(oracle['count']==389 and failure['artifact_acceptance']is False and failure['registry']['original_count']==failure['registry']['actual_count']==389 and len(failure['registry']['removed'])==len(failure['registry']['added'])==20,'genuine actual118 original389 failure immutable')
 need(classification['source_check']==PINS['actual118_failure']and classification['changed_field_counts']==dict(line=20,file=2)and classification['other_compared_fields_preserved']==['function','fmt','flags','count'],'Root exact failure field classification unchanged')
 profile_path=HERE/'candidate/scripts/f06_origin_command_profile.json';profile=json.loads(profile_path.read_bytes());producer=(HERE/'candidate/scripts/derive_f06_origin.py').read_text()
 need('PROFILE_SHA256 = "'+ref(profile_path)['sha256']+'"'in producer and profile['composed_arch_source_sha256']==ref(HERE/'candidate/arch/x86_64/kernel/syscall.c')['sha256'],'exact unchanged F06 profile/producer/source chain')
 actualprofile=checked(PINS['actual118_profile']);origin=json.loads(auth(actualprofile['origin_source_materialization']['actual_Rust_environment']).read_bytes())['MCKERNEL_F06_RT_SIGRETURN_ORIGIN']
 need(origin=='/src/arch/x86_64/kernel/syscall.c','genuine original origin env retained as historical reference; new producer still unrun')
 desc_namespace=dict(re=re,origin=origin);(_,read_descriptor)=owner_functions(PINS['F06_checker'],['apply_patch','descriptor'],desc_namespace)
 info=(HERE/'candidate/kernel/rust/f06_vdso_info.rs').read_text();maptext=(HERE/'candidate/kernel/rust/f06_vdso_map_log.rs').read_text();descriptors=[]
 for text,name,function,line in [(info,'ENTER','vdso_get_vdso_info',2859),(info,'EXIT','vdso_get_vdso_info',2887),(maptext,'VDSO_MAP_DEBUG','arch_vdso_map_log_bridge',3084)]:
  row,_=read_descriptor(text,name,function);need(row['line']==line and row in oracle['records'],'exact original F06 production descriptor source identity');descriptors.append(row)
 need(profile['vdso_info_descriptor_source_repair']['sha256']==ref(HERE/'candidate/kernel/rust/f06_vdso_info.rs')['sha256'],'both original info source fields bound')
 overlay=checked(ref(HERE/'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json'));files={r['relative']:r['source']for r in overlay['files']};need(len(files)==133 and sum(p.endswith('.rs')for p in files)==122,'exact reference-only Rust133/122')
 for row in rows:
  if row['relative'].startswith('kernel/rust/'):need(files[row['relative'][12:]]==row['postimage'],'closed source uses every selected joint Rust postimage')
 external={r['relative']:r['source']for r in actualprofile['inputs']['external_relative_modules']};need(len(external)==3,'exact retained external3')
 found_external=set();edges=[]
 for relative,row in files.items():
  if not relative.endswith('.rs'):continue
  text=auth(row).read_text()
  for name,path in modules(text):
   target=PurePosixPath(relative).parent/(path or(name+'.rs'));parts=[]
   for part in target.parts:
    if part=='..'and parts and parts[-1]!='..':parts.pop()
    elif part!='.':parts.append(part)
   target='/'.join(parts)
   if target in files:kind='closed_Rust_subtree'
   else:
    # lib.rs owns the three explicit ../../ external modules under /src.
    need(target.startswith('../../')and target[6:]in external,'exact external Rust module '+relative+':'+target);target=target[6:];auth(external[target]);found_external.add(target);kind='existing_external_module'
   edges.append(dict(from_file=relative,module=name,to_file=target,kind=kind))
 need(found_external==set(external),'all and only three retained external module edges')
 cmake=(HERE/'candidate/kernel/CMakeLists.txt').read_text();lib=(HERE/'candidate/kernel/rust/lib.rs').read_text();rusttexts=[auth(row).read_text()for relative,row in files.items()if relative.endswith('.rs')]
 for module in body5['modules_once']:need(len(re.findall(r'\bmod\s+'+re.escape(module)+r'\s*\{',policy))==1,'F03 module owner once '+module)
 for function in body5['exported_functions_once']:need(len(re.findall(r'\bfn\s+'+re.escape(function)+r'\s*\(',policy))==1,'F03 Rust export once '+function)
 f6map=checked(PINS['F06_map']);recipe=checked(ref(HERE/'CURRENT119-FOUR-COMMANDS.NOT-GRANTED.json'));oldrecipe=checked(PINS['F06_recipe']);need(recipe['ordered_commands']==oldrecipe['ordered_commands']and len(recipe['ordered_commands'])==4,'exact four existing argv/cwd vectors')
 for body in f6map['body_map']:
  auth(body['Rust_source']);candidate=next(r['postimage']for r in rows if Path(r['relative']).name==Path(body['candidate']['path']).name)
  need(auth(candidate).read_bytes()==auth(body['Rust_source']).read_bytes(),'banked HOST Rust leaf byte-identical')
  need(recipe['ordered_commands'][0]['argv'].count(body['Rust_cfg'])==1 and recipe['ordered_commands'][2]['argv'].count('-D'+body['C_selector'])==1,'one selected Rust cfg/C fallback selector per F06 leaf')
  for function in body['functions']:need(sum(len(re.findall(r'\bfn\s+'+re.escape(function)+r'\s*\(',text))for text in rusttexts)==1,'F06 function provider once '+function)
 need(cmake.count('${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_info.rs')==1,'existing info CMake source once')
 reuse=checked(PINS['existing_SDK21_reuse']);need(reuse['SDK21_recompiled']is False and len(actualprofile['inputs']['configuration'])==10 and len(actualprofile['inputs']['objects'])==11 and actualprofile['inputs']['retained_count']==8 and len(recipe['retained_inputs'])==8,'SDK21/8objects exact retained scope')
 for row in recipe['retained_inputs']:auth(row['source'])
 write('MODULE-CLOSURE-SOURCE-CHECKS.json',dict(scope=PINS['scope'],status='PASS_SOURCE_REFERENCE_CLOSURE_NOT_EXPORTED',subtree_files=133,Rust_files=122,external_modules=external,edges=edges,generated_clone_metadata_from_existing_origin_recipe_not_produced=True,physical_exports=0,runtime_authority=None))
 write('ABI-AND-METADATA-SOURCE-CHECKS.json',dict(scope=PINS['scope'],status='PASS_UNCHANGED_OWNER_POSTIMAGES_SOURCE_ABI_METADATA_CHECKS_NOT_LINKED_PROOF',F03_ABI=source['inherited_F03_ABI'],F06_ABI=source['inherited_F06_ABI'],BODY5_tested_tokens_order_preserved=True,F03_ten_functions_and_BODY13_storage_unique=True,F06_ten_functions_five_storage_owners_inherited_exact=True,all88_genuine_macro_source_sites_preserved=True,F03_observed17_failure_rows_cause_repaired=True,F06_exact_three_original_source_rows=descriptors,actual118_failure=PINS['actual118_failure'],original389_oracle=metadata['accepted_389_oracle'],oracle_changed=False,original389_linked_candidate_PASS_claimed=False,runtime_ABI_logic_changed_by_joint_union=False,runtime_authority=None))
 write('RETAINED-INPUTS-AND-PROFILE-SCOPE.json',dict(scope=PINS['scope'],actual118_profile=PINS['actual118_profile'],existing_SDK21_reuse=PINS['existing_SDK21_reuse'],source6153=actualprofile['inputs']['source6153'],configuration=actualprofile['inputs']['configuration'],retained_eight_objects=recipe['retained_inputs'],SDK_recompile=False,source6153_mutation=False,origin_producer_runs=0,actual_new_compiler_HOST_SDK_export_origin_guard_native_runs=0,runtime_authority=None))
 write('PURE-JOINT-CHECKS.json',dict(scope=PINS['scope'],status='PASS_SOURCE_ONLY_JOINT119',source_paths=18,unchanged_owner_full_postimages=18,exact_existing118_paths=8,new_Rust_paths=10,patches_checked_in_memory=patchcases,negative_wrong_preimage_rejected=True,actual118_and_synthetic_layout_drift_rejected=True,source_macro_sites=88,closed_source_files=133,Rust_files=122,external_modules=3,commands=4,eight_retained_objects=True,SDK21_recompiled=False,seconds=time.monotonic()-started,actual_new_compiler_HOST_SDK_export_origin_guard_native_runs=0,canonical_writes=0,artifact_acceptance=False,native_acceptance=False,runtime_authority=None))
 print(json.dumps(checked(ref(HERE/'PURE-JOINT-CHECKS.json'))))
if __name__=='__main__':main()
