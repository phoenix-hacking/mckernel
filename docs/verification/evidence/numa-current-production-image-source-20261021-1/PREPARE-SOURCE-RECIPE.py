"""Static bounded derivative preparation; never imports candidate validators."""
from pathlib import Path
import ast,copy,hashlib,json,shutil
R=Path(__file__).resolve().parent;S=R/'source-materialization-1';S.mkdir()
P=Path('/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1')
C=P/'owned-fork-pin-successor-1/coupled-current-pin-correction-1';CONTROL=C/'control-successor-1'
N=Path('/home/holden/mckernel-work/host-preparation/numa-current-whole-consumer-compile-preparation-20261021-1')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)}
def canonical(d):return (json.dumps(d,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def digest(d):return hashlib.sha256(canonical(d)).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,d):
 with p.open('x') as f:f.write(canonical(d).decode())
old=load(P/'thin-inputs.json');m=copy.deepcopy(old);n=load(N/'source-manifest.json');by={r['relative']:r for r in n['rows']}
rels=['kernel/syscall.c','kernel/rust/sched_helpers.rs','kernel/rust/syscall_policy.rs'];overlays=[]
for rel in rels:
 row=by[rel];src=N/'materialized-source'/rel;assert ref(src)['sha256']==row['sha256'] and src.stat().st_size==row['bytes']
 dst=R/'source-overlays'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 assert m['repository_files'][rel]==m['materialized_repository_files'][rel]
 overlays.append({'relative':rel,'predecessor_sha256':m['materialized_repository_files'][rel],'input':ref(dst),'accepted_current160_source':{'path':str(src),'bytes':row['bytes'],'sha256':row['sha256']}})
 m['repository_files'][rel]=m['materialized_repository_files'][rel]=row['sha256']
patch={'scope':SCOPE,'predecessor_manifest':ref(P/'thin-inputs.json'),'base_source':str(P/'source-materialization-1/materialized-source'),'base_actual_source_acceptance':ref(P/'independent-review-1/actual6959-source-and-identity-acceptance.json'),'overlays':overlays,'retained_production_CMake':m['materialized_repository_files']['kernel/CMakeLists.txt'],'retained_owned_fork_default':'OFF; existing opt-in image profile remains separate from default activation','raw_production_lib':m['materialized_repository_files']['kernel/rust/lib.rs'],'production_config':'CMake-generated; do not copy compiler-only .compiler-generated/config.h or FAM lib suffix','accepted_current160_manifest':ref(N/'source-manifest.json'),'actual_current160_acceptance':ref(N/'independent-review-1/actual-materialization-acceptance.json')}
save(R/'EXACT-THREE-PRODUCTION-OVERLAY-RECIPE.json',patch)
derivation={'base_manifest_sha256':sha(P/'thin-inputs.json'),'repository_files':m['repository_files'],'gitlinks':m['gitlinks'],'ihk_overlay':m['ihk_overlay'],'patch_sha256':digest(patch)}
m['source_derivative_sha256']=digest(derivation)
materialization={k:m[k] for k in ['source_derivative_sha256','materialized_repository_files','materialized_modes','retained_ihk_git_metadata','omitted_repository_files','omitted_main_git_metadata','materialized_kinds','materialized_symlinks']};m['materialization_sha256']=digest(materialization)
m['lineage']['numa_scheduler_current_three_overlay']={'parent':ref(P/'thin-inputs.json'),'patch':ref(R/'EXACT-THREE-PRODUCTION-OVERLAY-RECIPE.json'),'current160':ref(N/'source-manifest.json'),'scope':SCOPE+' Exact successor of accepted four-overlay image6959 with three coherent scheduler/NUMA replacements; all6956 other entries unchanged. Source/build/link/native outcomes unbound.'}
save(R/'thin-inputs.json',m);oldcanonical=digest(old);newcanonical=digest(m)
for name in ['thin_source_contract.py','native_rust_exact_build_offline.py']:
 text=(P/name).read_text();assert text.count(oldcanonical)==1;(R/name).write_text(text.replace(oldcanonical,newcanonical))
driver=(C/'native_rust_exact_mckernel_image_offline.py').read_text();tree=ast.parse(driver);changes=[]
for node in tree.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['OWNED_FORK_CURRENT_SOURCE_PINS','AFFINITY_SOURCE_PINS'] for t in node.targets):
  segment=ast.get_source_segment(driver,node);updated=segment
  for rel in rels:
   oldsha=old['materialized_repository_files'][rel];assert segment.count(oldsha)==1;updated=updated.replace(oldsha,m['materialized_repository_files'][rel])
  changes.append((node.lineno,node.end_lineno,updated))
assert len(changes)==2
lines=driver.splitlines(keepends=True)
for a,b,new in reversed(changes):lines[a-1:b]=[new+'\n']
newdriver=''.join(lines);(R/'native_rust_exact_mckernel_image_offline.py').write_text(newdriver)
def algorithms(text):
 t=ast.parse(text);t.body=[n for n in t.body if not(isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id in ['OWNED_FORK_CURRENT_SOURCE_PINS','AFFINITY_SOURCE_PINS'] for x in n.targets))];return ast.dump(t,include_attributes=False)
assert algorithms(driver)==algorithms(newdriver)
owner=(C/'native_rust_exact_mckernel_image_container_owner.py').read_text()
for a,b in [(sha(C/'native_rust_exact_mckernel_image_offline.py'),sha(R/'native_rust_exact_mckernel_image_offline.py')),(sha(P/'native_rust_exact_build_offline.py'),sha(R/'native_rust_exact_build_offline.py')),(str(P/'native_rust_exact_build_offline.py'),str(R/'native_rust_exact_build_offline.py')),(str(C/'full-image-attempt-1/common-exclusion.json'),str(R/'full-image-attempt-1/common-exclusion.json'))]:owner=owner.replace(a,b)
(R/'native_rust_exact_mckernel_image_container_owner.py').write_text(owner)
git=load(P/'gitlink-inputs.json');git['base_manifest_sha256']=sha(R/'thin-inputs.json');save(R/'gitlink-inputs.json',git)
# Preserve original materializer body; only exact input/data namespace assignments change.
mat=(P/'source-materialization-1/materialize_thin.py').read_text();mat=mat.replace(str(P),str(R));t=ast.parse(mat);edits=[]
for node in t.body:
 if isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='OVERLAYS' for x in node.targets):edits.append((node.lineno,node.end_lineno,'OVERLAYS={p:Path(v) for p,v in '+repr({r['relative']:r['input']['path'] for r in overlays})+'.items()}'))
 if isinstance(node,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='BASE_ROOT' for x in node.targets):edits.append((node.lineno,node.end_lineno,'BASE_ROOT='+repr(str(P/'source-materialization-1/materialized-source'))))
lines=mat.splitlines(keepends=True)
for a,b,new in reversed(edits):lines[a-1:b]=[new+'\n']
(S/'materialize_thin.py').write_text(''.join(lines))
# Existing real whole-validator check adapted only for namespace and exact pins/map rows.
check=(C/'check_whole_actual_source_validators.py').read_text();check=check.replace('O=R.parent.parent','O=R\nOLD=Path('+repr(str(C))+')')
check=check.replace("assert sha(O/'native_rust_exact_mckernel_image_offline.py')=='319790fd648ea82c7ef3adc129cc9cc329c08ea23beed105fdfeeb6770f09d9a'", "assert sha(OLD/'native_rust_exact_mckernel_image_offline.py')=="+repr(sha(C/'native_rust_exact_mckernel_image_offline.py')))
check=check.replace('0407c1d87fe85fbcda7f23872f3f47fe64c238f7ef6cc0c6e4f21fd63253fd4d',sha(R/'native_rust_exact_build_offline.py')).replace('c269f7387b0937368fd2da53a837d49699c4f3a311b22b80fd0966dcb948a986',sha(R/'native_rust_exact_mckernel_image_offline.py'))
check=check.replace("old=whole_module('_retained_full_actual_image_driver',O/", "old=whole_module('_retained_full_actual_image_driver',OLD/")
# Dict row ordering differs in owned and affinity maps; compare exact changed key sets.
check=check.replace("assert [k for k in a if a[k]!=b[k]]==['kernel/syscall.c','kernel/rust/syscall_policy.rs']", "assert {k for k in a if a[k]!=b[k]}=="+repr(set(rels)))
check=check.replace("'source_or_scheduler_changes':False", "'source_and_scheduler_changes':"+repr(rels))
check=check.replace("assert sha(OLD/'native_rust_exact_mckernel_image_offline.py')=='"+sha(R/'native_rust_exact_mckernel_image_offline.py')+"'","assert sha(OLD/'native_rust_exact_mckernel_image_offline.py')=='"+sha(C/'native_rust_exact_mckernel_image_offline.py')+"'")
(R/'check_whole_actual_source_validators.py').write_text(check)
# Small exact request delta avoids duplicating accepted26MiB control inventory; it is not executable request/release.
qpath=CONTROL/'image-request.json';q=load(qpath)
setfields={'source_manifest':str(R/'thin-inputs.json'),'source_manifest_sha256':sha(R/'thin-inputs.json'),'source_derivative_sha256':m['source_derivative_sha256'],'materialization_sha256':m['materialization_sha256'],'provenance_path':str(R/'native_rust_exact_build_offline.py'),'provenance_sha256':sha(R/'native_rust_exact_build_offline.py'),'driver_path':str(R/'native_rust_exact_mckernel_image_offline.py'),'driver_sha256':sha(R/'native_rust_exact_mckernel_image_offline.py'),'gitlink_manifest':str(R/'gitlink-inputs.json'),'gitlink_manifest_sha256':sha(R/'gitlink-inputs.json'),'source_root':str(S/'materialized-source'),'source_identity':None,'disk_identity':None,'backup_identity':None}
for key in ['attempt_root','evidence_root','output_root','owner_evidence_root','work_root','lease_path','common_exclusion_path']:
 value=q[key];setfields[key]=value.replace(str(CONTROL),str(R/'heavy-execution-preparation-1')).replace(str(C),str(R))
save(R/'SOURCE-UNBOUND-REQUEST-DELTA-PROPOSAL.json',{'scope':SCOPE,'status':'DATA_ONLY_NOT_EXECUTABLE_REQUEST','accepted_request_basis':ref(qpath),'set_fields':setfields,'native_fork_owned_transaction':q['native_fork_owned_transaction'],'selector_note':'Preserve accepted opt-in diagnostic build flag True; production CMake default remains OFF. No default activation claim.','required_mount_updates':'Root mechanically derives src/provenance/driver/manifest/gitlink/work mounts and path_dirs from exact set_fields; preserve all accepted toolchain/backups/profile inventory rows. Fresh identities/admission/publication/release remain unbound.','actual_source':None,'compiler_acceptance':None,'latest_physical':None,'runtime':None})
commands={name:['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=1073741824','--cpu=30','--fsize=33554432','--nofile=256','--core=0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(path)] for name,path in [('materialize',S/'materialize_thin.py'),('whole_real_source_validators',R/'check_whole_actual_source_validators.py')]}
save(R/'ORDINARY-MATERIALIZATION-AND-VALIDATOR-PROPOSAL.json',{'scope':SCOPE,'status':'UNBOUND_NOT_EXECUTED','commands':commands,'ordering':'Independent changed-boundary review and fresh root ordinary grant; existing exact materialization first, actual6959/49symlink source acceptance; then existing whole real owned/affinity source-gate check with absent compile_commands boundary. No fake ELF/build database.','profile':{'cpu':6,'jobs':1,'AS_bytes':1073741824,'CPU_seconds_each':30,'wall_seconds_each':35,'FSIZE_bytes':33554432,'nofile':256,'core':0,'network':False,'root':False},'storage_admission':'Root fresh measured whole120MiB source growth plus exact threefile delta, journal/capture/control and emergency reserve; preserve host16GiB/scratch12GiB floors and scratch UUID/noresize. Existing materializer per-file floor is not aggregate admission. Preparation current packet <32MiB; actual source copy is separately granted future work.','actual_outputs':None,'source_identity':None,'grant':None,'source6959_acceptance':None,'compiler_acceptance':None,'latest_physical':None,'runtime':None})
guard=CONTROL/'native_exact_current_optin_image_guard.py'
save(R/'FUTURE-GUARD-AND-LINK-BINDING-DELTA.json',{'scope':SCOPE,'status':'UNBOUND_FUTURE_AUTHORITY_REQUIRED','guard_basis':ref(guard),'guard_auth_literal_substitutions':{old['source_derivative_sha256']:m['source_derivative_sha256'],old['materialization_sha256']:m['materialization_sha256']},'required_genuine_new_refs':['actual source materialization/inode acceptance','runtime binding acceptance and source-bound request basis','current independent execution review','source/control fetched publication','latest actual positive physical retirement','fresh root snapshot/resource/ownership/service/included100%/noAPI admission and release'],'production_link_observation':['unique setscheduler_body_result and syscall_vm_range_policy_search_body_result definitions in actual production Rust object and final image','unique corresponding selected production C imports before actual link','no unresolved helper in final image; exact config/defaultOFF and opt-in selection retained','existing settid/fork/constructor/ABI/FAM/panic-refusal/nine-artifact real-mcexec route remains required'],'actual_physical':None,'compiler_acceptance':None,'runtime':None})
receipt={'scope':SCOPE,'status':'ONE_COHERENT_THREE_OVERLAY_CURRENT_IMAGE_SOURCE_RECIPE_ONLY','production_basis':ref(P/'thin-inputs.json'),'accepted_current_route_request':ref(qpath),'manifest':ref(R/'thin-inputs.json'),'planned_source_derivative':m['source_derivative_sha256'],'planned_materialization':m['materialization_sha256'],'canonical_manifest_sha256':newcanonical,'changed_production_rows':overlays,'unchanged_materialized_entries':len(m['materialized_modes'])-3,'total_entries':len(m['materialized_modes']),'symlinks_retained':len(m['materialized_symlinks']),'driver_only_two_source_pin_map_changes':{k:rels for k in ['OWNED_FORK_CURRENT_SOURCE_PINS','AFFINITY_SOURCE_PINS']},'driver_algorithms_AST_identical':True,'contract_and_embedded_runtime_only_canonical_literal_changed':True,'materializer_original_algorithm_retained':True,'CMake_retained':m['materialized_repository_files']['kernel/CMakeLists.txt'],'owned_fork_source_default':'OFF','retained_raw2012B_lib':m['materialized_repository_files']['kernel/rust/lib.rs'],'ABI_assertions_and_config_generation_unchanged':True,'preserved_failure_history':'Original precompiler ownedpin refusal77f94 and bounded coupled correction; original fullimage/panicLD/auth/stale metadata/source attempts all retained. This new source candidate has zero execution attempts. Carry family history; one failed candidate plus one bounded correction, then focused expert.','actual_source_materialization':None,'latest_physical':None,'compiler_acceptance':None,'runtime':None,'next':'Focused changed three-source/coherent coupled pin/contract review, fresh ordinary source grant, existing materializer then actual source acceptance and whole real source validators. Root separately derives final existing request/release; no heavy execution authority.'}
save(R/'PREPARATION-RECEIPT.json',receipt)
print(json.dumps({'receipt':ref(R/'PREPARATION-RECEIPT.json'),'manifest':ref(R/'thin-inputs.json'),'driver':ref(R/'native_rust_exact_mckernel_image_offline.py'),'planned_canonical':newcanonical}))
