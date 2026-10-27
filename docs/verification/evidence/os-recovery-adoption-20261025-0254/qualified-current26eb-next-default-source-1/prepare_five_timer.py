"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind actual-qualified timer120 to six qualified functions using unchanged fixed-five.
"""
from pathlib import Path
import copy,difflib,hashlib,json
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel');B=E/'ROOT-SYNC-PROCESSVM-HOST13-FIVE-BUILD-ADMISSION-1';F=E/'f02-timer-layout-storage-next-current-source-1';HOST=E/'f02-timer-layout-provider-link-repair-source-1/ACTUAL-HOST-PASS-HANDOFF.json'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(p.read_text())
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
assert ref(HOST)['sha256']=='1dd58c83dfb36d073c6c185be97ad2caa4786fc182f616b9d85a96e691f68b73';host=read(HOST);assert host['all_children_joined'] and host['all_streams_closed'] and host['CPU6']=='FREE'
history=D/'unexecuted-four-tuple-history-1';history.mkdir(mode=0o700)
for name in ['PROFILE.SOURCE-ONLY.json','INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json','run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py','capture_and_bind_resource.py','FOUR-TUPLE-SPECIALIZATION.SOURCE-ONLY.json','EXACT-FOUR-TUPLE-SPECIALIZATION.diff','CURRENT055C-REUSE-COMPATIBILITY.SOURCE-ONLY.json']:
 p=D/name
 if p.exists():(history/name).write_bytes(p.read_bytes())
(history/'UNEXECUTED.json').write_text(json.dumps(dict(scope=__doc__.splitlines()[0],status='UNEXECUTED_FOUR_SPECIALIZATION_SUPERSEDED_BY_ACTUAL_QUALIFIED_TIMER_FIVE_SCOPE',executions=0,compiler_grants=0,original_snapshot_and_manifest_preserved=True),indent=2)+'\n')
six=read(D/'SIX-FUNCTION-SOURCE-UNION.NOT-GRANTED.json');plan=copy.deepcopy(six);implementation=read(F/'SOURCE-IMPLEMENTATION-AND-CURRENT120B-ABI.json')
for row in implementation['preimages']:
 p=Path(row['path']);assert ref(p)==row
for row in read(F/'SOURCE-ONLY-RESULT.json')['postimages']:
 p=Path(row['path']);assert ref(p)==row;rel=str(p.relative_to(F/'candidate'));target=D/'candidate'/rel;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(p.read_bytes());target.chmod(0o400);plan['postimages'][rel]=ref(target);plan['preimages'][rel]=ref(R/rel);patch=D/'patches'/(rel.replace('/','__')+'.patch');patch.write_text(''.join(difflib.unified_diff((R/rel).read_text().splitlines(True),target.read_text().splitlines(True),fromfile=rel,tofile=rel)))
P=read(B/'PROFILE.SOURCE-ONLY.json');oldexport=P['inputs']['source_directory_exports'][0];oldmap=read(Path(oldexport['manifest']['path']));snapshot=D/'rust-subtree-five-timer';snapshot.mkdir(mode=0o700);rows={}
for old in oldmap['files']:
 src=Path(old['snapshot']['path']);assert ref(src)==old['snapshot'];target=snapshot/old['relative'];target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(src.read_bytes());target.chmod(0o400);rows[old['relative']]=dict(old,predecessor_snapshot=old['snapshot'],snapshot=ref(target))
for rel in ['kernel/rust/syscall_policy.rs','kernel/rust/process_helpers.rs']+six['new_module_paths']:
 p=snapshot/rel.removeprefix('kernel/rust/')
 if p.exists():p.chmod(0o600)
 p.write_bytes((D/'candidate'/rel).read_bytes());p.chmod(0o400);short=rel.removeprefix('kernel/rust/');rows[short]=dict(rows.get(short,{}),relative=short,snapshot=ref(p),qualified_origin=ref(D/'candidate'/rel),kind='Actual HOST-qualified six-function and timer120 source union')
manifest=dict(oldmap,export_root=str(snapshot),files=[rows[k] for k in sorted(rows)],predecessor_manifest=oldexport['manifest'],new_leaf_files=[Path(s).name for s in six['new_module_paths']],changed_predecessor_files=['syscall_policy.rs','process_helpers.rs'],total_bytes=sum(r['snapshot']['bytes'] for r in rows.values()));save('RUST-SUBTREE-CLOSED-SOURCE-MAP.FIVE.json',manifest)
P.update(status='STATIC_ACTUAL_HOST_SIX_FUNCTION_TIMER120_FIXED_FIVE_NOT_GRANTED',runtime_authority=None,request_sha256=None,native_custody_clearance=None)
P['inputs']['source_directory_exports']=[dict(oldexport,host_path=str(snapshot),manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.FIVE.json'))]
for row in P['inputs']['postimages']:
 if row['relative'] in plan['postimages']:row.update(postimage=plan['postimages'][row['relative']],postimage_mode=0o400)
for row in P['inputs']['objects']:
 if row['replace']:
  path=B/'OUTPUT/work/output/build'/row['build_relative'];row.update(source=ref(path),retained_archive_member=str(path),action='Genuine new six-function/timer object; exact accepted26eb predecessor provenance')
for index,flags in [(0,six['new_Rust_cfgs']),(2,six['new_C_defines']['kernel']),(3,six['new_C_defines']['arch'])]:
 argv=P['exact_commands'][index]['argv'];pos=next(i for i,a in enumerate(argv) if a.startswith('--emit=obj=')) if index==0 else next(i for i,a in enumerate(argv) if a.startswith('-I'));argv[pos:pos]=[t for cfg in flags for t in ['--cfg',cfg]] if index==0 else ['-D'+s for s in flags]
P['unchanged_completed_process_prefix']['Root_decision']='RECOMPILE_CHANGED_PROCESS_SOURCE_ACTUAL_TIMER120_HOST_QUALIFIED';P['producer_contract'].update(source='Accepted26eb plus exact qualified six bridge selectors and actual-qualified timer120 storage; fixed-five/four-new/seven-prefix',reused_objects=7,process_delta='NEW process source1dc76b89 and Rusthelper439ffb1e: actual-qualified timer120 C OBJECT migration; process71→70 metadata, zero C functions');P['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in P['inputs']['postimages']]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in manifest['files']];P['reuse_descriptor']=str(D/'FROZEN-FIVE-COMMAND-SEVEN-INPUT-REUSE.json');save('PROFILE.SOURCE-ONLY.json',P)
reuse=read(Path(read(B/'PROFILE.SOURCE-ONLY.json')['reuse_descriptor']));reuse.update(schema='mckernel.current26eb.six-functions-timer120-five-command-seven-prefix.v1',objects=P['inputs']['objects'],postimages=P['inputs']['postimages'],source_directory_exports=P['inputs']['source_directory_exports'],runtime_authority=None,future_nonce=None,future_pid=None);reuse['commands']['exact_five_literal_argv']=P['exact_commands'];reuse['commands']['new_objects']=P['producer_contract']['new_objects'];save('FROZEN-FIVE-COMMAND-SEVEN-INPUT-REUSE.json',reuse)
export=read(B/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json');export.update(author=None,decision=None,status='STATIC_109_SEVEN_PREFIX_FIVE_COMMAND_EXPORT_NOT_AUTHORITY',request_sha256=None,runtime_authority=None);export['qualified_readonly_files']=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['snapshot'] for r in manifest['files']];save('INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json',export)
for name in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py','capture_and_bind_resource.py']:(D/name).write_bytes((B/name).read_bytes())
assert ref(D/'run_build_only.py')['sha256']=='25d3b8ccbf7430eda6b3e063ed440355b48ec6f85d5838a6be6d26f276e1d9f6';assert ref(D/'build_only_worker.py')['sha256']=='8512307cfe59593444ac70d5f5ba6631bff50b60ce7153bc16c93a090b7c30ab'
plan.update(status='COHERENT_ACTUAL_HOST_SIX_FUNCTION_AND_TIMER120_SOURCE_PROFILE_READY_NOT_EXECUTED',timer_included=True,timer_actual_result=ref(HOST),timer_implementation=ref(F/'SOURCE-IMPLEMENTATION-AND-CURRENT120B-ABI.json'),source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.FIVE.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),commands=5,new_objects=4,retained_C_inputs=7,closed_Rust_files=len(rows),expected_C_process_OBJECTs=dict(before=71,after=70,only_removed='process_timer_runtime_offsets'),timer_new_data_objects=1,timer_bytes=120,timer_genuine_ABI_words=15,new_Rust_function_exports=4,carried_Rust_function_exports=35,total_expected_function_exports=39,expected_new_Rust_import_removals=six['expected_new_Rust_import_removals']+['process_timer_runtime_offsets'],four_specialization_executed=False,actual_request_sha256=None,actual_Root_admission=None,actual_nonce=None,actual_resource_authority=None,actual_execution_release=None)
save('COHERENT-NEXT-DEFAULT-SOURCE-PLAN.NOT-GRANTED.json',plan);print(json.dumps(dict(status=plan['status'],postimages=len(plan['postimages']),Rust_files=len(rows),commands=5,retained_C=7,Cfunctions=[72,28],process_metadata=70,function_exports=39,timer_data_objects=1)))
