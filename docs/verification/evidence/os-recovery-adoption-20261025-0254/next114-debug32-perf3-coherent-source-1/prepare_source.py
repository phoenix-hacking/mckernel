"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Selective qualified GLOBAL32+perf3 union, source-only; no operational calls.
"""
import ast,copy,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;E=D.parent
B=E/'newdebug32-next114-source/actual113-three-command-reuse-source-1'
PERF=E/'m14-f03-perf-provider-next3-source-1'
KPROD=E/'ROOT-CURRENT112-EVENT2-ALLOC2-BUILD-ADMISSION-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return write(n,json.dumps(x,indent=2)+'\n')
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
base_review=B/'independent-source-profile-review-1/INDEPENDENT-SOURCE-PROFILE-REVIEW.json'
perf_review=PERF/'ordinary-host-profile-1/independent-actual-review-1/FINAL-REVIEW.json'
assert ref(base_review)['sha256']=='10d980d9a96c4df46ad9abe7762195c6162205ab640c2d5e77d0e7f2b0095ebe'
assert ref(perf_review)['sha256']=='4af93d3013c136a3dc9db8df2652959adc45c9d6814f137cc502feba476d87b3'
old=read(B/'PROFILE.SOURCE-ONLY.json');assert ref(B/'PROFILE.SOURCE-ONLY.json')['sha256'].startswith('a73')
accepted=old['predecessor_CURRENT113_actual_acceptance'];auth(accepted);assert accepted['sha256'].startswith('02c1001e')
oldmap_path=auth(old['inputs']['source_directory_exports'][0]['manifest']);oldmap=read(oldmap_path);prior={r['relative']:r for r in oldmap['files']};assert len(prior)==119
post={r['relative']:r for r in old['inputs']['postimages']}
kernel=auth(post['kernel/syscall.c']['postimage']).read_text()
callbacks=['perf_counter_extra_set_bridge','perf_counter_init_raw_bridge','perf_event_atomic64_read_bridge']
for name in callbacks:
 kernel=once(kernel,(PERF/(name+'.original.C.inc')).read_text(),(PERF/(name+'.paired-selector.C.inc')).read_text())
policy=auth(prior['syscall_policy.rs']['snapshot']).read_text()
fragment=(PERF/'selected-bridges.Rust.inc').read_text()
assert policy.count('fn perf_counter_extra_set_bridge(')==0 and policy.count('fn perf_counter_init_raw_bridge(')==0
policy=policy+'\n'+fragment
assert policy.count('fn syscall_atomic64_read_bridge(')==1
cmake=auth(post['kernel/CMakeLists.txt']['postimage']).read_text()
needle='\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_counter_control_bridges_selected_candidate")\n'
cmake=once(cmake,needle,needle+'\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_provider_next3_bridges_selected_candidate")\n')
flags='MCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES;MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES;MCKERNEL_RUST_F03_PERF_EVENT_PROVIDER_BRIDGES'
cmake=once(cmake,'COMPILE_DEFINITIONS "'+flags+'"','COMPILE_DEFINITIONS "'+flags+';MCKERNEL_RUST_F03_PERF_PROVIDER_NEXT3_BRIDGES"')
changes={'kernel/syscall.c':kernel,'kernel/CMakeLists.txt':cmake}
for relative,text in changes.items():
 before=auth(post[relative]['postimage']).read_text();write('candidate/'+relative,text)
 write('patches/'+relative+'.patch',''.join(difflib.unified_diff(before.splitlines(keepends=True),text.splitlines(keepends=True),fromfile='GLOBAL32/'+relative,tofile='GLOBAL32-perf3/'+relative)))
write('patches/kernel/rust/syscall_policy.rs.patch',''.join(difflib.unified_diff(auth(prior['syscall_policy.rs']['snapshot']).read_text().splitlines(keepends=True),policy.splitlines(keepends=True),fromfile='GLOBAL32/kernel/rust/syscall_policy.rs',tofile='GLOBAL32-perf3/kernel/rust/syscall_policy.rs')))
rows=[]
for r in oldmap['files']:
 snapshot=write('rust-subtree/'+r['relative'],policy if r['relative']=='syscall_policy.rs' else auth(r['snapshot']).read_bytes())
 row=copy.deepcopy(r);row.update(snapshot=ref(snapshot),predecessor_snapshot=r['snapshot'],kind='qualified perf3 append-only two Rust wrappers' if r['relative']=='syscall_policy.rs' else 'unchanged reviewed GLOBAL32 cohort')
 rows.append(row)
assert len(rows)==119 and {r['relative'] for r in rows if r['snapshot']['sha256']!=r['predecessor_snapshot']['sha256']}=={'syscall_policy.rs'}
newmap=copy.deepcopy(oldmap);newmap.update(export_root=str(D/'rust-subtree'),files=rows,total_bytes=sum(r['snapshot']['bytes'] for r in rows),new_leaf_files=[],predecessor_manifest=ref(oldmap_path),original_source_mutations=0)
save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',newmap)
p=copy.deepcopy(old);p.update(status='NEXT114_TYPED_GLOBAL32_AND_PERF3_PRIVATE_COHERENT_SOURCE_ONLY_NOT_ADOPTED_NOT_RELEASED',runtime_authority=None)
for key in ['request_sha256','native_custody_clearance','actual_nonce','actual_root_adoption','actual_execution_review','actual_resource_authority','actual_output_root','actual_holder','actual_source_publication']:p[key]=None
postimages=[]
for r in old['inputs']['postimages']:
 row=copy.deepcopy(r)
 if row['relative'] in changes:row['postimage']=ref(D/'candidate'/row['relative'])
 postimages.append(row)
p['inputs']['postimages']=postimages
p['inputs']['source_directory_exports']=[dict(host_path=str(D/'rust-subtree'),container_destination='/src/kernel/rust',readonly=True,manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
p['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in postimages]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in rows]
kcommand=copy.deepcopy(read(KPROD/'PROFILE.SOURCE-ONLY.json')['exact_commands'][1]);assert kcommand['stage']=='selected kernel syscall object'
argv=kcommand['argv'];idx=next(i for i,v in enumerate(argv) if v.startswith('-I'));argv[idx:idx]=['-DMCKERNEL_RUST_F03_PERF_PROVIDER_NEXT3_BRIDGES']
commands=[copy.deepcopy(old['exact_commands'][0]),kcommand,copy.deepcopy(old['exact_commands'][1]),copy.deepcopy(old['exact_commands'][2])]
argv=commands[0]['argv'];idx=next(i for i,v in enumerate(argv) if v.startswith('--emit=obj='));argv[idx:idx]=['--cfg','f03_perf_provider_next3_bridges_selected_candidate']
assert commands[2]==old['exact_commands'][1] and commands[3]==old['exact_commands'][2]
assert [v for v in commands[0]['argv'] if v.startswith('MCKERNEL_')]==[v for v in old['exact_commands'][0]['argv'] if v.startswith('MCKERNEL_')]
p['exact_commands']=commands
for row in p['inputs']['objects']:
 if row['build_relative']=='kernel/CMakeFiles/mckernel.img.dir/syscall.c.o':row['replace']=True;row['action']='Rebuild changed perf3 kernelC; actual accepted retained predecessor provenance only'
assert sum(not r['replace'] for r in p['inputs']['objects'])==8
arch=next(r for r in p['inputs']['objects'] if r['build_relative'].endswith('/arch/x86_64/kernel/syscall.c.o'))
assert arch['replace'] is False and arch['source']['sha256'].startswith('da1e0f3a')
p['inputs']['retained_count']=8;p['inputs']['replaced_count']=3
origin=p['origin_source_materialization'];assert origin['actual_producer_receipt']['sha256'].startswith('2c419c64')
for k in ['actual_producer_receipt','actual_generated_header','actual_origin_binding','actual_Rust_environment','actual_CMake_origin']:auth(origin[k])
assert next(r['postimage'] for r in postimages if r['relative']=='arch/x86_64/kernel/syscall.c')==post['arch/x86_64/kernel/syscall.c']['postimage']
p['source_preparation_current_context']=dict(runtime_authority=None,status='FUTURE_ROOT40_CURRENT_BINDING_REQUIRED_NOT_ADMISSION',current_nonce_ledger=None,current_native_custody_clearance=None,predecessor_accepted_CURRENT113=accepted)
p['qualified_perf3_actual_HOST']=ref(perf_review)
contract=p['producer_contract'];contract.update(source='Reviewed typedGLOBAL32 sourcefa334/profilea73/10d980 + independently HOST-qualifiedperf3 4af93 over actual accepted11302c100; source-only next114 union',new_objects=[r['build_relative'] for r in p['inputs']['objects'] if r['replace']],reused_objects=8,expected_F03_C_functions=61,expected_F06_C_functions=19,expected_total_selected_C_functions=80,expected_current_cohort_Rust_function_exports=58,expected_process_OBJECT_records=31,expected_new_C_function_removals=callbacks,counts_are_unaccepted_expectations=True)
contract['postbuild_required']=[v.replace('nine unchanged retained','eight unchanged retained').replace('nine retained','eight retained').replace('two fresh','three fresh').replace('two-object','three-object') for v in contract['postbuild_required']]
contract['postbuild_required'] += ['Actual fullRust/kernelC/processC producer binding and exact eight retained inputs including accepted113archda1e; no arch compile/configure/SDK/origin producer replay.', 'TypedGLOBAL32 actual ownership32GLOBAL/64Cstrslots/2048B, original selected metadata/default0/env/fileline and14LOCAL/configs/4scalar/timer/idle/runqueue obligations retained source-exact.', 'New perf3 C callbacks absent: unique new Rust extra_set/init_raw definitions with exact CInt/CULong→u32 narrowing; atomic callback aliases existing syscall_atomic64_read_bridge, no duplicate body.', 'Preserve original prefix/HOST/compiler/source failures and oracles; any actual elision/import/string/line delta needs exact source-bound disposition, not count normalization.']
p['reuse_descriptor']=str(D/'FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json')
save('FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json',dict(scope=SCOPE,runtime_authority=None,predecessor=ref(Path(old['reuse_descriptor'])),accepted_CURRENT113=accepted,reviewed_GLOBAL32=ref(base_review),qualified_perf3=ref(perf_review),configuration=p['inputs']['configuration'],objects=p['inputs']['objects'],new_objects=contract['new_objects'],actual_commands=commands,source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),genuine_origin_reused=origin['actual_producer_receipt'],arch_compile_replayed=False,producer_replayed=False,SDK21_recompiled=False))
save('PROFILE.SOURCE-ONLY.json',p)
plan=read(B/'EXACT-THREE-COMMAND-PROPOSAL.NOT-GRANTED.json');plan.update(commands=commands,source_profile=ref(D/'PROFILE.SOURCE-ONLY.json'),producer_contract=contract);save('EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json',plan)
export=read(B/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json');export.update(status='NEXT114_GLOBAL32_PERF3_EXPORT_TEMPLATE_NOT_AUTHORITY',author=None,decision=None,request_sha256=None)
export['qualified_readonly_files']=[r['source'] for r in p['inputs']['configuration']]+[r['source'] for r in p['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in postimages]+[r['snapshot'] for r in rows];save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
runner=(B/'run_build_only.py').read_text()
for a,b in [
 ('matching nine-object/two-replacement reuse descriptor','matching eight-object/three-replacement reuse descriptor'),
 ("outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','mckernel.img']","outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/process.c.o','mckernel.img']"),
 ("sources=['/src/kernel/rust/lib.rs','/src/kernel/process.c']","sources=['/src/kernel/rust/lib.rs','/src/kernel/syscall.c','/src/kernel/process.c']"),
 ("len(commands)==3,'exact three selected successor commands'","len(commands)==4,'exact four selected successor commands'"),
 ('both changed compiler source paths','all three changed compiler source paths'),
 ("==9 and sum(r['replace'] for r in profile['inputs']['objects'])==2,'nine accepted retained and two new objects'","==8 and sum(r['replace'] for r in profile['inputs']['objects'])==3,'eight accepted retained and three new objects'"),
 ("set(outputs[:2]),'exact two selected replacement object paths'","set(outputs[:3]),'exact three selected replacement object paths'"),
 ("elif i==1:require(argv[0]","elif i<3:require(argv[0]"),
 ]:runner=once(runner,a,b)
worker=(B/'build_only_worker.py').read_text()
worker=once(worker,"len(plan['commands'])==3,'exact three selected build commands'","len(plan['commands'])==4,'exact four selected build commands'")
worker=once(worker,'ACTUAL_BUILD_ONLY_THREE_COMMAND_PRODUCER','ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER')
tools=[]
for n,text in [('run_build_only.py',runner),('build_only_worker.py',worker)]+[(n,(B/n).read_text()) for n in ['hold_and_run_build_only.py','publish_approved_ready.py']]:
 ast.parse(text,filename=n);dest=write(n,text);delta=write('helper-diffs/'+n+'.diff',''.join(difflib.unified_diff((B/n).read_text().splitlines(keepends=True),text.splitlines(keepends=True),fromfile='GLOBAL32/'+n,tofile='GLOBAL32-perf3/'+n)));tools.append(dict(name=n,predecessor=ref(B/n),successor=ref(dest),diff=ref(delta)))
save('SELECTIVE-COMPOSITION-PROOF.json',dict(scope=SCOPE,runtime_authority=None,reviewed_GLOBAL32_source_ready=ref(B/'SOURCE-READY.json'),reviewed_GLOBAL32_profile=ref(B/'PROFILE.SOURCE-ONLY.json'),GLOBAL32_review=ref(base_review),perf3_actual_full_HOST=ref(perf_review),accepted_CURRENT113=accepted,exact_paired_fragments=[ref(PERF/(n+s)) for n in callbacks for s in ['.original.C.inc','.paired-selector.C.inc']],two_Rust_wrappers=ref(PERF/'selected-bridges.Rust.inc'),existing_atomic_body_count=1,new_Rust_leaf_files=0,closed_Rust_files=119,changed_Rust_files=['syscall_policy.rs'],changed_postimages=['kernel/syscall.c','kernel/CMakeLists.txt'],unchanged_GLOBAL32_process=post['kernel/process.c']['postimage'],unchanged_process_command=True,unchanged_env_bindings=True,original_fallback_bodies_preserved=True,retained_actual113arch=arch,genuine_origin_reused=origin['actual_producer_receipt'],actual_origin_replayed=False,actual_compilers=0,canonical_or_Git_writes=0,app_stream_or_oracle_mutations=0))
save('ROOT-NEXT-STEPS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,steps=['Independent selective union source/profile review; preserve GLOBAL32fa334/profilea73/10d98 and perf3HOST4af93/failures unchanged.', 'Root alone adopts exact union kernelC/policy/CMake alongside reviewedGLOBAL32cohort; no repeated Rust implementation.', 'Bind actualRoot40-or-later current account/source/ownership/adoption/publication/materializer/resource/nonce/holder/independentPASS/release; all remain absent here.', 'Run four proposed commands only: fullRust/kernelC/processC/raw11link. Eight retained inputs include accepted113archda1e; preserve exact genuine113origin2c419 with no archC/producer replay.', 'Validate actual selected counts/data/consumer bytes and inherited/global32/default0/env/fileline/fallback contracts; expected80C/58Rust/process31 are candidates only. Native/whole-file/M14/M15 stay OPEN without matching proof.'],actual_current_ledger=None,actual_Root_adoption=None,actual_materializer=None,actual_resource_authority=None,actual_nonce=None,actual_holder=None,actual_output_root=None,actual_execution_review=None,actual_release=None,fixed_three_clock_cutoffs=p['fixed_three_clock_cutoffs'],controls='Sameaccount/cumulativecredits/realholds, CPU2-5/12GiB/noswap/512pids/networknone oneheavy/permanent27:4/scratch21,7jobs/original floors unchanged.',all_actual_calls=0))
save('SOURCE-READY.json',dict(scope=SCOPE,status='NEXT114_GLOBAL32_PERF3_SELECTIVE_PRIVATE_COHERENT_SOURCE_READY_NOT_RELEASED',runtime_authority=None,profile=ref(D/'PROFILE.SOURCE-ONLY.json'),source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),composition=ref(D/'SELECTIVE-COMPOSITION-PROOF.json'),next_steps=ref(D/'ROOT-NEXT-STEPS.NOT-AUTHORITY.json'),tools=tools,commands=4,new_objects=3,retained_objects=8,Rust_sources=119,changed_Rust_files=1,added_Rust_functions=2,reused_atomic_aliases=1,expected_new_C_function_removals=3,expected_new_C_data_removals=32,expected_C_functions=80,expected_Rust_function_exports=58,expected_process_C_OBJECTs=31,counts_are_candidate_only=True,all_actual_calls=0,canonical_or_Git_writes=0))
print(json.dumps(dict(decision='SOURCE_READY_NOT_RELEASED',ready=ref(D/'SOURCE-READY.json'),profile=ref(D/'PROFILE.SOURCE-ONLY.json'),commands=4,new_objects=3,retained_objects=8,Rust_sources=119)))
