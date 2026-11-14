"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reuse frozen ready sources and exact existing fixed-five adapters; private only.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel');Q=E/'qualified-sync-processvm-next-default-source-1';F=E/'f02-source38-next-current-integration-source-1';S=E/'qualified-cohort-next-static-source-1';B=E/'ROOT-NEXT10-DEFAULT-BUILD-ADMISSION-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
def auth(x):
 p=Path(x['path']);assert ref(p)==x;return p
assert ref(Q/'READY.SOURCE-ONLY.json')['sha256']=='adb270c23ee3a8ea2c61bd92fdcc5931c550191d931c8fe40f637af72bacf9de'
assert ref(F/'ACTUAL-HOST13-HANDOFF.json')['sha256']=='603fa11cc81f891d98bbd55e9448f513d9707e70d2bed2186f27b91e4f56be6c'
host=read(F/'ACTUAL-HOST13-HANDOFF.json');implementation=read(auth(host['implementation']));assert host['tested']['total_comparisons']==292 and host['tested']['readonly_CInt4_min_align4_initial_values']==13
plan=read(Q/'COHERENT-SOURCE-PLAN.NOT-GRANTED.json');pre=copy.deepcopy(plan['preimages']);post={}
for row in implementation['preimages']:
 p=auth(row);pre[str(p.relative_to(R))]=row
for rel,row in plan['preimages'].items():assert ref(R/rel)==row
for rel,row in plan['postimages'].items():
 p=D/'candidate'/rel;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_bytes(auth(row).read_bytes());p.chmod(0o400);post[rel]=ref(p)
for row in host['candidate_postimages']:
 src=auth(row);rel=str(src.relative_to(F/'candidate'));p=D/'candidate'/rel;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_bytes(src.read_bytes());p.chmod(0o400);post[rel]=ref(p)
for rel,row in post.items():
 p=D/'patches'/(rel.replace('/','__')+'.patch');p.parent.mkdir(mode=0o700,exist_ok=True);old=(R/rel).read_text() if (R/rel).exists() else '';p.write_text(''.join(difflib.unified_diff(old.splitlines(True),Path(row['path']).read_text().splitlines(True),fromfile=rel if old else '/dev/null',tofile=rel)))
# Materialize the exact already-prepared fixed-five source adapters, not an
# extension of or weakening to the active fixed-four runner.
tools={}
for name in ['run_build_only.py','build_only_worker.py']:
 editpath=S/(name+'.edits.json');edits=read(editpath);source=auth(edits['baseline']).read_text()
 for change in edits['edits']:
  assert source.count(change['before'])==1;source=source.replace(change['before'],change['after'],1)
 ast.parse(source);(D/name).write_text(source);tools[name]=dict(materialized=ref(D/name),existing_exact_adapter=ref(editpath),baseline=edits['baseline'])
for name in ['hold_and_run_build_only.py','publish_approved_ready.py','capture_and_bind_resource.py']:
 (D/name).write_bytes((B/name).read_bytes());tools[name]=dict(materialized=ref(D/name),byteexact_parent=ref(B/name))
P=read(Q/'PROFILE.SOURCE-ONLY.json');oldmap=read(auth(P['inputs']['source_directory_exports'][0]['manifest']));snapshot=D/'rust-subtree';snapshot.mkdir(mode=0o700);rows={}
for old in oldmap['files']:
 source=auth(old['snapshot']);target=snapshot/old['relative'];target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(source.read_bytes());target.chmod(0o400);rows[old['relative']]=dict(old,predecessor_snapshot=old['snapshot'],snapshot=ref(target))
short='process_helpers.rs';target=snapshot/short;target.chmod(0o600);target.write_bytes((D/'candidate/kernel/rust'/short).read_bytes());target.chmod(0o400);rows[short].update(snapshot=ref(target),qualified_origin=post['kernel/rust/process_helpers.rs'],kind='actual HOST13 qualified unchanged storage fragment')
manifest=dict(oldmap,export_root=str(snapshot),files=[rows[n] for n in sorted(rows)],predecessor_manifest=P['inputs']['source_directory_exports'][0]['manifest'],changed_predecessor_files=['process_helpers.rs'],changed_from_accepted_NEXT10=['syscall_policy.rs','process_helpers.rs'],new_leaf_files_from_accepted_NEXT10=['f06_process_vm_entry.rs'],total_bytes=sum(r['snapshot']['bytes'] for r in rows.values()));save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',manifest)
P.update(status='STATIC_SYNC_PROCESSVM_HOST13_FIXED_FIVE_COMMANDS_NOT_GRANTED',runtime_authority=None,request_sha256=None,native_custody_clearance=None)
P['inputs']['source_directory_exports'][0].update(host_path=str(snapshot),manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))
for row in P['inputs']['postimages']:
 rel=row['relative']
 if rel in post:row.update(postimage=post[rel],postimage_mode=0o400)
P['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in P['inputs']['postimages']]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in manifest['files']]
process=copy.deepcopy(read(F/'EXACT-NEXT-THREE-COMPILER-COMMANDS.NOT-ADMITTED.json')['commands'][1]);process['new_output']='/work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o';P['exact_commands'].insert(1,process)
for row in P['inputs']['objects']:
 if row['link_token']=='CMakeFiles/mckernel.img.dir/process.c.o':
  row.update(replace=True,action='new process object for exact actual HOST13 qualified data source; b816 baseline provenance only');row.pop('matching_source_sha256',None);row.pop('matching_exact_process_argv_unchanged',None)
P['inputs'].update(retained_count=7,replaced_count=4);P['unchanged_completed_process_prefix']['Root_decision']='RECOMPILE_CHANGED_PROCESS_SOURCE_ACTUAL_HOST13_QUALIFIED';P['producer_contract']['new_objects'].insert(1,'kernel/CMakeFiles/mckernel.img.dir/process.c.o');P['producer_contract'].update(reused_objects=7,process_delta='NEW SOURCE: exact HOST13 readonly CInt storage selection; no repeated old process compile; 84 C OBJECTs expected71, same zero C FUNCs',source='Accepted F42 plus ready qualified sync/processVM and actual HOST13 data; four new objects, seven unchanged C prefixes, same11 rawld')
P['reuse_descriptor']=str(D/'FROZEN-FIVE-STAGE-SEVEN-OBJECT-REUSE-INPUTS.json');save('PROFILE.SOURCE-ONLY.json',P)
reuse=read(Path(read(Q/'PROFILE.SOURCE-ONLY.json')['reuse_descriptor']));reuse.update(schema='mckernel.sync-processvm-host13-fixed-five-seven-prefix-reuse.v1',objects=P['inputs']['objects'],postimages=P['inputs']['postimages'],source_directory_exports=P['inputs']['source_directory_exports'],runtime_authority=None,future_nonce=None,future_pid=None);reuse['commands'].pop('exact_four_literal_argv',None);reuse['commands']['exact_five_literal_argv']=P['exact_commands'];reuse['commands']['new_objects']=P['producer_contract']['new_objects'];save('FROZEN-FIVE-STAGE-SEVEN-OBJECT-REUSE-INPUTS.json',reuse)
export=read(Q/'INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json');export['qualified_readonly_files']=[r['source'] for r in P['inputs']['configuration']]+[r['source'] for r in P['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in P['inputs']['postimages']]+[r['snapshot'] for r in manifest['files']];save('INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json',export)
combined=dict(plan,status='PRIVATE_COMBINED_SYNC_PROCESSVM_HOST13_FIVE_STAGE_SOURCE_NOT_ADMITTED',preimages=pre,postimages=post,ready_four_command_source=ref(Q/'READY.SOURCE-ONLY.json'),actual_HOST13=ref(F/'ACTUAL-HOST13-HANDOFF.json'),HOST13_implementation=host['implementation'],prior_four_command_packet_unchanged=True,existing_fixed_five_tools=tools,commands=5,new_objects=4,retained_C_inputs=7,closed_Rust_files=106,new_data_providers=13,new_function_exports=2,expected_C_OBJECT_counts=dict(process_before=84,process_after=71),expected_C_FUNC_counts=dict(process=0,kernel_before=76,kernel_after=75,arch_before=45,arch_after=31),Source38_GNU_RETAIN_hold='OPEN_UNCHANGED_NO_OLD_GRAPH_IMPORT',actual_Root_admission=None,actual_request_sha256=None,actual_nonce=None,actual_resource_authority=None,independent_execution_release=None,default_acceptance=False,native_acceptance=False,whole_file_retirement=False);save('COHERENT-COMBINED-SOURCE-PLAN.NOT-GRANTED.json',combined)
print(json.dumps(dict(status=combined['status'],source_postimages=len(post),closed_Rust_files=106,commands=5,retained_C_inputs=7,exact_existing_five_API_materialized=True)))
