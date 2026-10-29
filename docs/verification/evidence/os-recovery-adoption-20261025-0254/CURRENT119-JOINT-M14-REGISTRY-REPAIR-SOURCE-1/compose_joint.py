"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact one-time private union of banked F03/F06 postimages; no canonical apply API.
"""
from pathlib import Path
import copy,difflib,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
PINS=json.loads((HERE/'INPUTS.json').read_bytes())
def need(ok,why):
 if not ok:raise ValueError(why)
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(row):need(ref(row['path'])==row,'exact BYTE source');return Path(row['path'])
def checked(row):return json.loads(auth(row).read_bytes())
def write(name,value):(HERE/name).write_text(json.dumps(value,indent=2)+'\n')
def prepare():
 need(not(HERE/'SOURCE-MAP-FROM118.json').exists(),'one-time private preparation; preserve sealed predecessor')
 f3=checked(PINS['F03_map']);f6=checked(PINS['F06_map']);ready3=checked(PINS['F03_ready']);ready6=checked(PINS['F06_ready'])
 need(ready3['source_map']==PINS['F03_map']and ready6['source_map']==PINS['F06_map'],'exact owner ready/map bindings')
 paths3={r['relative']for r in f3['writes']};paths6={r['relative']for r in f6['changes']}
 need(len(paths3)==2 and len(paths6)==16 and not paths3&paths6,'two plus16 disjoint complete postimages')
 for relative,row in f6['all_nine_actual118_preimages'].items():need(ref(ROOT/relative)==row,'actual canonical118 preimage '+relative)
 rows=[]
 for owner,source_rows in [('F03',f3['writes']),('F06',f6['changes'])]:
  for source in source_rows:
   relative=source['relative'];post=auth(source['postimage']);target=HERE/'candidate'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(post.read_bytes())
   if owner=='F03':
    historical=source['source118_preimage'];auth(historical);pre=ref(ROOT/relative);need((pre['bytes'],pre['sha256'])==(historical['bytes'],historical['sha256']),'canonical equals exact historical118 bytes');requirement='EXACT_BYTE_REF'
   else:pre=source['preimage'];requirement=source['preimage_requirement']
   if requirement=='EXACT_BYTE_REF':need(ref(ROOT/relative)==pre,'exact existing118 source');before=auth(pre).read_text()
   else:need(requirement=='PATH_ABSENT'and not(ROOT/relative).exists(),'new Rust path remains absent');before=''
   patch=HERE/'patches-from118'/(relative.replace('/','__')+'.patch');patch.parent.mkdir(exist_ok=True)
   patch.write_text(''.join(difflib.unified_diff(before.splitlines(True),target.read_text().splitlines(True),fromfile='/dev/null'if requirement=='PATH_ABSENT'else'a/'+relative,tofile='b/'+relative)))
   rows.append(dict(owner=owner,relative=relative,preimage_requirement=requirement,preimage=pre,owner_postimage=source['postimage'],postimage=ref(target),patch=ref(patch)))
 need(len(rows)==18 and len({r['relative']for r in rows})==18,'exact18 no duplicate application')
 (HERE/'CURRENT119-CUMULATIVE-FROM118.patch').write_text(''.join(auth(r['patch']).read_text()for r in rows))
 write('SOURCE-MAP-FROM118.json',dict(scope=PINS['scope'],status='PRIVATE_EXACT18PATH_JOINT_F03_BODY3_13_F06_BODY3_12_SOURCE_ONLY',F03_source_ready=PINS['F03_ready'],F06_source_ready=PINS['F06_ready'],actual118_failure=PINS['actual118_failure'],Root_field_classification=PINS['Root_field_classification'],actual118_source_adoption=f6['base118_source_adoption'],all_nine_actual118_preimages=f6['all_nine_actual118_preimages'],changes=rows,inherited_F03_ABI=f3['inherited_body_provider_ABI_ownership'],inherited_F03_registry=f3['inherited_C_metadata_and_debt'],inherited_F03_remaining=f3['inherited_frontier'],inherited_F06_ABI=PINS['F06_ABI'],inherited_F06_body_map=f6['body_map'],inherited_F06_remaining=f6['remaining'],original389_oracle=checked(PINS['F06_metadata'])['accepted_389_oracle'],no_equivalent_ports=True,no_runtime_source_logic_changes_during_joint_union=True,canonical_writes=0,actual_new_compiler_HOST_SDK_export_origin_guard_native_runs=0,runtime_authority=None))
 overlay=checked(PINS['F06_overlay']);files=copy.deepcopy(overlay['files']);changed={Path(r['relative']).name:r for r in rows if r['relative'].startswith('kernel/rust/')}
 for r in files:
  if r['relative']in changed:r.update(source=changed[r['relative']]['postimage'],action='reference_exact_joint119_source_no_export')
 need(len(files)==133 and len({r['relative']for r in files})==133 and sum(r['relative'].endswith('.rs')for r in files)==122,'exact inherited133/122 closure')
 write('RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json',dict(scope=PINS['scope'],status='REFERENCE_ONLY_JOINT119_133_FILES_122_RUST_NOT_EXPORTED',files=files,expected_count=133,expected_rs_count=122,source_map=ref(HERE/'SOURCE-MAP-FROM118.json'),predecessor_F06_overlay=PINS['F06_overlay'],external_module_closure='Existing exact three external Rust modules; bind separately in MODULE-CLOSURE-SOURCE-CHECKS.json',physical_exports_created=0,runtime_authority=None))
 recipe=copy.deepcopy(checked(PINS['F06_recipe']));recipe.update(status='CURRENT119_JOINT_EXACT_FOUR_COMMAND_RECIPE_NOT_GRANTED',source_map=ref(HERE/'SOURCE-MAP-FROM118.json'),source_overlay=ref(HERE/'RUST-CLOSED-SOURCE-OVERLAY.NOT-MATERIALIZED.json'),actual_new_commands=0,actual_source_adoption=None,actual_origin_export_sdk=None,actual_operation_admission=None,runtime_authority=None,native_release=None)
 recipe['joint_F03_source_ready']=PINS['F03_ready'];recipe['joint_F06_source_ready']=PINS['F06_ready'];recipe['Root_prerequisites']=['Keep actual118 failure27e8/a922 and unaccepted image7e5; no unchanged retry.','Existing joint source review covers exact18postimages and original389 predicate, ABI/provider/module/metadata closure.','Root alone adopts exact18paths after preimage check, authenticates new source/profile/origin/closedRust133/122 plus external3 using existing machinery. Existing SDK21 and eight retained objects stay reused; no SDK rebuild/per-body replay.','Root alone binds new ordinary operation/current custody/resource/admission after actual quarantine-owner reconciliation. This packet has no nonce, grant or release.','One admitted exact existing four-command image path; original389 linked multiset/line/staticlayout/ABI then matching-native/file requirements separately.']
 write('CURRENT119-FOUR-COMMANDS.NOT-GRANTED.json',recipe)
 write('ORIGIN-AND-PROFILE-RECIPE.NOT-RUN.json',dict(scope=PINS['scope'],producer=next(r['postimage']for r in rows if r['relative']=='scripts/derive_f06_origin.py'),profile=next(r['postimage']for r in rows if r['relative']=='scripts/f06_origin_command_profile.json'),actual_arch_source=next(r['postimage']for r in rows if r['relative']=='arch/x86_64/kernel/syscall.c'),argv=['python3','-B','/src/scripts/derive_f06_origin.py','--profile','/src/scripts/f06_origin_command_profile.json','--source','/src/arch/x86_64/kernel/syscall.c','--output','/work/output/build/kernel/rust/f06-origin'],generated_files=['f06_rt_sigreturn_origin.h','f06_rt_sigreturn_origin.cmake','f06_clone_cpuid_metadata.rs','rust-environment.json','ORIGIN-BINDING.json'],actual_origin_producer_runs=0,existing_SDK21_reused=True,existing_eight_objects_reused=True,generated_clone_lines_preserved=[898,908],runtime_authority=None))
 write('ORDERED-PATCHES.json',dict(scope=PINS['scope'],baseline='Exact canonical118 byte refs and10 absent Rust paths; never replay old118 producer prefix',order=[r['patch']for r in rows],combined=ref(HERE/'CURRENT119-CUMULATIVE-FROM118.patch'),changed_paths=18,applications_per_path=1,alternative_never_apply_both='Apply18 individual patches OR combined patch; complete postimages are byte-identical alternatives',Root_authority=None,runtime_authority=None))
 print(json.dumps(dict(status='PRIVATE_EXACT18PATH_JOINT_SOURCE_PREPARED',source_map=ref(HERE/'SOURCE-MAP-FROM118.json'),new_compiler_HOST_SDK_export_origin_guard_native_runs=0)))
if __name__=='__main__':prepare()
