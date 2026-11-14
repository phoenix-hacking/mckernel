"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private qualified-fragment composition and source proposal; no workload authority.
"""
import ast
import copy
import difflib
import hashlib
import json
import re
from pathlib import Path
D=Path(__file__).resolve().parent
E=D.parent
ROOT=E.parents[3]
A=E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2'
A110=E/'ROOT-CURRENT110-HOST19-BUILD-ADMISSION-1'
P111=E/'current111-counter3-runqueue208-production-preparation-source-1'
F03=E/'m14-f03-event-provider-bridges-next-source-1'
F06=E/'m14-f06-next-supported-body-new12h-1/generated-rust-origin-alternative-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(p.read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(name,raw):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(raw,str):raw=raw.encode()
 if p.exists():assert p.read_bytes()==raw and not p.is_symlink(),name
 else:
  with p.open('xb') as f:f.write(raw)
  p.chmod(0o400)
 return p

def save(name,x):return write(name,json.dumps(x,indent=2)+'\n')
def once(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def apply_literal_patch(source,patch):
 # Exact retained hunks, no offset guessing or subprocess.
 lines=patch.splitlines(keepends=True);groups=[];g=None
 for line in lines:
  if line.startswith('@@ '):
   if g is not None:groups.append(g)
   g=[]
  elif g is not None:
   assert line[0] in ' +-';g.append(line)
 if g is not None:groups.append(g)
 for g in groups:
  before=''.join(l[1:] for l in g if l[0] in ' -')
  after=''.join(l[1:] for l in g if l[0] in ' +')
  source=once(source,before,after)
 return source

old=read(A/'PROFILE.SOURCE-ONLY.json');accept=read(A/'independent-final-consumer-review-1/DEFAULT-ARTIFACT-REVIEW.json')
assert accept['decision']=='PASS_ACTUAL_CURRENT111_DEFAULT_SELECTED_ARTIFACT'
assert ref(A/'PROFILE.SOURCE-ONLY.json')==accept['profile']
assert accept['tuple']['image']['sha256'].startswith('0bbe')
for relative,prefix in {'kernel/syscall.c':'7d303969','kernel/rust/syscall_policy.rs':'c81c6735','kernel/CMakeLists.txt':'1ca3a50f','kernel/process.c':'ccca48c2','kernel/rust/sched_helpers.rs':'c4e6153b'}.items():assert ref(ROOT/relative)['sha256'].startswith(prefix),relative
prior_map_path=Path(old['inputs']['source_directory_exports'][0]['manifest']['path']);prior_map=read(prior_map_path)
prior={r['relative']:r for r in prior_map['files']};assert len(prior)==112
base={r['relative']:Path(r['postimage']['path']).read_text() for r in old['inputs']['postimages']}
base['kernel/rust/syscall_policy.rs']=Path(prior['syscall_policy.rs']['snapshot']['path']).read_text()
composed={}
composed['kernel/syscall.c']=apply_literal_patch(base['kernel/syscall.c'],(F03/'syscall.c.patch').read_text())
composed['kernel/rust/syscall_policy.rs']=apply_literal_patch(base['kernel/rust/syscall_policy.rs'],(F03/'syscall_policy.rs.patch').read_text())+'\n'+(F06/'syscall_policy.rs.fragment').read_text()
composed['arch/x86_64/kernel/syscall.c']=apply_literal_patch(base['arch/x86_64/kernel/syscall.c'],(F06/'syscall.c.diff').read_text())
assert composed['arch/x86_64/kernel/syscall.c']==(F06/'syscall.c').read_text()
composed['kernel/rust/f06_rt_sigreturn_alloc_free.rs']=(F06/'f06_rt_sigreturn_alloc_free.rs').read_text()
cmake=apply_literal_patch(base['kernel/CMakeLists.txt'],(F03/'CMakeLists.txt.proposal.patch').read_text())
fragment=(F06/'ROOT-CMAKE-PROPOSAL.fragment').read_text()
fragment=fragment[:fragment.index('\n# Separately insert')]
fragment='set(MCKERNEL_F06_ORIGIN_PROFILE "${PROJECT_SOURCE_DIR}/scripts/f06_origin_command_profile.json")\n'+fragment
needle='\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_rt_sigreturn_check_signal_candidate")\n'
cmake=once(cmake,needle,needle+''.join('\t\t\t\t'+l+'\n' for l in fragment.splitlines()))
cmake=once(cmake,'\t\t\tMCKERNEL_CPU_C_FILE=${MCKERNEL_CPU_C_FILE}\n','\t\t\tMCKERNEL_CPU_C_FILE=${MCKERNEL_CPU_C_FILE}\n\t\t\t"MCKERNEL_F06_RT_SIGRETURN_ORIGIN=${MCKERNEL_F06_RT_SIGRETURN_ORIGIN}"\n')
composed['kernel/CMakeLists.txt']=cmake
# Minimal producer sequence: wholeRust/kernelC/archC/raw11link. Process is retained.
commands=[copy.deepcopy(old['exact_commands'][0]),copy.deepcopy(old['exact_commands'][2]),copy.deepcopy(read(A110/'PROFILE.SOURCE-ONLY.json')['exact_commands'][3]),copy.deepcopy(old['exact_commands'][3])]
argv=commands[0]['argv'];i=next(i for i,v in enumerate(argv) if v.startswith('--emit=obj='));argv[i:i]=[v for cfg in ['f03_perf_event_provider_bridges_selected_candidate','f06_rt_sigreturn_alloc_candidate','f06_rt_sigreturn_free_candidate'] for v in ['--cfg',cfg]]
argv=commands[1]['argv'];i=next(i for i,v in enumerate(argv) if v.startswith('-I'));argv[i:i]=['-DMCKERNEL_RUST_F03_PERF_EVENT_PROVIDER_BRIDGES']
argv=commands[2]['argv'];i=next(i for i,v in enumerate(argv) if v.startswith('-I'));argv[i:i]=['-DMCKERNEL_RUST_F06_RT_SIGRETURN_ALLOC','-DMCKERNEL_RUST_F06_RT_SIGRETURN_FREE','-I/work/output/build/kernel/rust/f06-origin']
origin=commands[2]['argv'][-1]
assert origin=='/src/arch/x86_64/kernel/syscall.c'
assert not any('prefix-map' in x or x.startswith('@') or '__FILE__' in x or x in ('-include','-imacros') for x in commands[2]['argv'])
assert not re.search(r'^\s*#\s*(?:line\s+)?\d+\s+"',composed['arch/x86_64/kernel/syscall.c'],re.M)
argv=commands[0]['argv'];i=argv.index('/nightly/bin/rustc');argv.insert(i,'MCKERNEL_F06_RT_SIGRETURN_ORIGIN='+origin)
origin_profile=dict(scope=SCOPE,status='SOURCE_ONLY_EXACT_PROPOSED_C_PRODUCER_NOT_AUTHORITY',runtime_authority=None,accepted_CURRENT111=ref(A/'independent-final-consumer-review-1/DEFAULT-ARTIFACT-REVIEW.json'),accepted_CURRENT111_profile=ref(A/'PROFILE.SOURCE-ONLY.json'),arch_predecessor_profile=ref(A110/'PROFILE.SOURCE-ONLY.json'),arch_predecessor_command=read(A110/'PROFILE.SOURCE-ONLY.json')['exact_commands'][3],exact_commands=[commands[2]],composed_arch_source_sha256=hashlib.sha256(composed['arch/x86_64/kernel/syscall.c'].encode()).hexdigest(),new_C_runtime_objects=0)
origin_profile_path=save('candidate/scripts/f06_origin_command_profile.json',origin_profile)
# Rebind the qualified origin producer to the small exact proposed-arch profile.
producer=(F06/'derive_origin.py').read_text()
producer=once(producer,'Support precisely the adopted CURRENT110 SDK profile; reject profile drift.','Support precisely the private CURRENT112 arch-command profile; reject profile drift.')
producer=once(producer,'PROFILE_SHA256 = "64242ef204a7696369462487e5ca17e63f24d1a9d4c9957e43778b643a2fa288"','PROFILE_SHA256 = "'+ref(origin_profile_path)['sha256']+'"')
producer=once(producer,'    source = source_path.read_text()','    if hashlib.sha256(source_path.read_bytes()).hexdigest() != profile["composed_arch_source_sha256"]:\n        raise ValueError("exact proposed architecture source bytes required")\n    source = source_path.read_text()')
composed['scripts/derive_f06_origin.py']=producer
# Source preview only, copied from the accepted HOST producer, never run here.
header=(F06/'ordinary-host-profile-1/future-host-output-1/generated/f06_rt_sigreturn_origin.h').read_text()
assert '#define MCKERNEL_F06_RT_SIGRETURN_ORIGIN '+json.dumps(origin) in header
header_path=write('origin-source-preview/f06_rt_sigreturn_origin.h',header)
save('ORIGIN-DERIVATION.NOT-RUNTIME.json',dict(scope=SCOPE,runtime_authority=None,status='SOURCE_PREVIEW_ONLY_PRODUCER_NOT_EXECUTED',origin_profile=ref(origin_profile_path),source_producer_predecessor=ref(F06/'derive_origin.py'),actual_proposed_C_command=commands[2],origin_utf8=origin,origin_bytes_with_nul=list(origin.encode()+b'\0'),header_source_preview=ref(header_path),header_copied_from_actual_HOST=ref(F06/'ordinary-host-profile-1/future-host-output-1/generated/f06_rt_sigreturn_origin.h'),Rust_environment_argument='MCKERNEL_F06_RT_SIGRETURN_ORIGIN='+origin,Root_materialization_command=['/usr/bin/python3','-B','/src/scripts/derive_f06_origin.py','--profile','/src/scripts/f06_origin_command_profile.json','--source',origin,'--output','/work/output/build/kernel/rust/f06-origin'],actual_producer_invocations=0,actual_materializations=0,limits='Root must materialize/review exact producer output before compile; preview is source data, not new runtime evidence. Four proposed commands are compiler/link only; no configure/SDK replay.'))
# All retained allocator tracking call spellings remain literal, including fallback.
tracking=lambda s: re.findall(r'\b(?:kmalloc_tracked|kfree_tracked)\s*\([^;]*;',s,re.S)
assert tracking(base['arch/x86_64/kernel/syscall.c'])==tracking(composed['arch/x86_64/kernel/syscall.c'])
for relative,text in composed.items():
 if relative.startswith('kernel/rust/'):continue
 write('candidate/'+relative,text)
 before=base.get(relative,'')
 write('patches/'+relative+'.patch',''.join(difflib.unified_diff(before.splitlines(keepends=True),text.splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative)))
rows=[]
for relative in sorted(set(prior)|{'f06_rt_sigreturn_alloc_free.rs'}):
 original=Path(prior[relative]['snapshot']['path']) if relative in prior else F06/'f06_rt_sigreturn_alloc_free.rs'
 text=composed.get('kernel/rust/'+relative,original.read_text())
 dest=write('rust-subtree/'+relative,text)
 rows.append(dict(relative=relative,original=ref(original),snapshot=ref(dest),predecessor_snapshot=prior.get(relative,{}).get('snapshot'),kind='new qualified F06 leaf' if relative not in prior else ('unchanged CURRENT111' if ref(dest)['sha256']==prior[relative]['snapshot']['sha256'] else 'composed qualified F03/F06 successor')))
 if 'kernel/rust/'+relative in composed:
  before=Path(prior[relative]['snapshot']['path']).read_text() if relative in prior else ''
  write('patches/kernel/rust/'+relative+'.patch',''.join(difflib.unified_diff(before.splitlines(keepends=True),text.splitlines(keepends=True),fromfile='a/kernel/rust/'+relative,tofile='b/kernel/rust/'+relative)))
assert len(rows)==113
assert {r['relative'] for r in rows if r['kind']!='unchanged CURRENT111'}=={'syscall_policy.rs','f06_rt_sigreturn_alloc_free.rs'}
source_map=dict(scope=SCOPE,runtime_authority=None,schema='mckernel.exact-kernel-rust-subtree-readonly.v1',base_source_root=old['inputs']['source6153']+'/kernel/rust',export_root=str(D/'rust-subtree'),container_destination='/src/kernel/rust',files=rows,total_bytes=sum(r['snapshot']['bytes'] for r in rows),new_leaf_files=['f06_rt_sigreturn_alloc_free.rs'],no_symlinks=True,no_hardlinks=True,original_source_mutations=0,predecessor_manifest=ref(prior_map_path))
save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',source_map)
profile=copy.deepcopy(old);profile.update(status='CURRENT112_PRIVATE_QUALIFIED_COMPOSITION_NOT_ADOPTED_NOT_RELEASED',runtime_authority=None)
for k in ['request_sha256','native_custody_clearance','actual_nonce','actual_root_adoption','actual_execution_review','actual_resource_authority','actual_output_root','actual_holder']:profile[k]=None
postimages=[]
for row in old['inputs']['postimages']:
 r=copy.deepcopy(row);relative=r['relative']
 dest=write('candidate/'+relative,composed.get(relative,base[relative]));r['postimage']=ref(dest);postimages.append(r)
for relative in ['scripts/derive_f06_origin.py','scripts/f06_origin_command_profile.json']:
 postimages.append(dict(relative=relative,base=None,base_mode=None,postimage=ref(D/'candidate'/relative),postimage_mode=256,container_destination='/src/'+relative,readonly=True))
postimages.append(dict(relative='kernel/rust/f06-origin/f06_rt_sigreturn_origin.h',base=None,base_mode=None,postimage=ref(header_path),postimage_mode=256,container_destination='/work/output/build/kernel/rust/f06-origin/f06_rt_sigreturn_origin.h',readonly=True,source_preview_not_runtime_producer=True))
profile['inputs']['postimages']=postimages
profile['inputs']['source_directory_exports']=[dict(host_path=str(D/'rust-subtree'),container_destination='/src/kernel/rust',readonly=True,manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
profile['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in postimages]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in rows]
outputs={}
for row in read(A/'OUTPUT/work/evidence/producer-contract.json')['commands']:
 out=row['output'];relative=Path(out['path']).relative_to('/work/output/build').as_posix();r=ref(A/'OUTPUT/work/output/build'/relative)
 assert r['sha256']==out['sha256'] and r['bytes']==out['bytes'];outputs[relative]=r
new={'kernel/rust/mckernel_rust.o','kernel/CMakeFiles/mckernel.img.dir/syscall.c.o','kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'}
for row in profile['inputs']['objects']:
 if row['build_relative'] in outputs:
  row['source']=outputs[row['build_relative']];row['retained_archive_member']=row['source']['path']
 row['replace']=row['build_relative'] in new
 row['action']='Rebuild changed CURRENT112 object; prior provenance only' if row['replace'] else 'Retain exact accepted CURRENT111 input; do not recompile'
 assert ref(row['source']['path'])==row['source']
process=next(r for r in profile['inputs']['objects'] if r['build_relative']=='kernel/CMakeFiles/mckernel.img.dir/process.c.o')
assert not process['replace'] and process['source']['sha256'].startswith('a4309')
profile['inputs']['retained_count']=8;profile['inputs']['replaced_count']=3;profile['exact_commands']=commands
contract=profile['producer_contract']
contract.update(source='Accepted CURRENT111 plus qualified F03event2/F06allocfree2+Rustfilename private union; four commands/three fresh objects/eight retained',new_objects=sorted(new),reused_objects=8,process_delta='No processC rebuild; retain actual accepted CURRENT111 processa4309/67C OBJECT records and Rustrunqueue208/idle116/timer120 metadata. Reprove all fresh fullRust/image consumers.',expected_F03_C_functions=64,expected_F06_C_functions=23,expected_total_selected_C_functions=87,expected_current_cohort_Rust_function_exports=52,expected_process_OBJECT_records=67,expected_new_C_function_removals=['perf_event_set_period_bridge','perf_event_update_bridge','arch_rt_sigreturn_alloc_bridge','arch_rt_sigreturn_free_bridge'],expected_new_Rust_data=['F06_RT_SIGRETURN_ORIGIN static UTF8+NUL'],counts_are_unaccepted_expectations=True)
contract['postbuild_required'] += ['Qualified F03event2 independent actualHOST acceptance required before Root source adoption/release; no HOST replay.','Exact proposed archCargv/source-bound origin producer, genuine C TU equality assertion, Rust-owned filename withNUL, original tracking385/391, all unrelated C metadata and no new C filename object.','Reprove all inherited logger/line/timer120/idle116/runqueue208 and current PMU/native pointer providers against actual new fullRust and finalimage; original scripted failures remain.']
profile['reuse_descriptor']=str(D/'FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json')
save('FROZEN-FOUR-COMMAND-EIGHT-INPUT-REUSE.json',dict(scope=SCOPE,runtime_authority=None,accepted_CURRENT111=ref(A/'independent-final-consumer-review-1/DEFAULT-ARTIFACT-REVIEW.json'),configuration=profile['inputs']['configuration'],objects=profile['inputs']['objects'],new_objects=sorted(new),actual_commands=commands,configuration_reuse_not_fresh_configure=True,SDK21_recompiled=False,previous_commands_replayed=False))
save('PROFILE.SOURCE-ONLY.json',profile)
save('EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,commands=commands,source_profile=ref(D/'PROFILE.SOURCE-ONLY.json'),tool_files=read(A/'OUTPUT/plan.json')['tool_files'],producer_contract=contract,actual_nonce=None,actual_output_root=None))
# Reuse existing exact custody/account/resource implementation; adapt compiler-source map only.
runner=(A/'run_build_only.py').read_text()
runner=once(runner,"outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','CMakeFiles/mckernel.img.dir/syscall.c.o','mckernel.img']","outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']")
runner=once(runner,"sources=['/src/kernel/rust/lib.rs','/src/kernel/process.c','/src/kernel/syscall.c']","sources=['/src/kernel/rust/lib.rs','/src/kernel/syscall.c','/src/arch/x86_64/kernel/syscall.c']")
runner=once(runner,"name='current111-build-only-'","name='current112-build-only-'")
tools=[]
for name,text in [('run_build_only.py',runner),('build_only_worker.py',(A/'build_only_worker.py').read_text()),('hold_and_run_build_only.py',(A/'hold_and_run_build_only.py').read_text()),('publish_approved_ready.py',(A/'publish_approved_ready.py').read_text())]:
 ast.parse(text,filename=name);dest=write(name,text)
 diff=write('tool-diffs/'+name+'.diff',''.join(difflib.unified_diff((A/name).read_text().splitlines(keepends=True),text.splitlines(keepends=True),fromfile='CURRENT111/'+name,tofile='CURRENT112/'+name)))
 tools.append(dict(name=name,predecessor=ref(A/name),successor=ref(dest),diff=ref(diff)))
export=copy.deepcopy(read(A/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'));export.update(status='CURRENT112_TEMPLATE_NOT_ACTUAL_AUTHORITY',author=None,decision=None,request_sha256=None)
export['qualified_readonly_files']=[r['source'] for r in profile['inputs']['configuration']]+[r['source'] for r in profile['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in postimages]+[r['snapshot'] for r in rows]
save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
save('COMPOSITION-DERIVATION.json',dict(scope=SCOPE,runtime_authority=None,accepted_CURRENT111=ref(A/'independent-final-consumer-review-1/DEFAULT-ARTIFACT-REVIEW.json'),qualified_F03_source_review=ref(F03/'independent-source-profile-review-1/INDEPENDENT-SOURCE-PROFILE-REVIEW.json'),F03_actual_tool_result=ref(F03/'ordinary-host-profile-1/ROOT-ACTUAL-TOOL-RESULT.json'),F03_independent_actual_HOST_review='PENDING_AT_PREPARATION; Root must bind later exact result',qualified_F06_source_review=ref(F06/'independent-source-review-1/INDEPENDENT-SOURCE-REVIEW.json'),F06_independent_actual_HOST=ref(F06/'ordinary-host-profile-1/independent-profile-review-1/INDEPENDENT-ACTUAL-HOST-ACCEPTANCE.json'),reused_fragments=[ref(F03/x) for x in ['syscall.c.patch','syscall_policy.rs.patch','CMakeLists.txt.proposal.patch']]+[ref(F06/x) for x in ['syscall.c.diff','syscall_policy.rs.fragment','f06_rt_sigreturn_alloc_free.rs','ROOT-CMAKE-PROPOSAL.fragment','derive_origin.py']],closed_Rust_source_count=113,arch_tracking_call_expressions_unchanged=len(tracking(base['arch/x86_64/kernel/syscall.c'])),process_retained=process,changes_excluded=['unrunF03perf3','foregroundLOCK4','F06next4','F02scalar4'],tools=tools,canonical_writes=0,compiler_invocations=0,producer_invocations=0,materializations=0))
save('ROOT-NEXT-STEPS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,owner='/root',required_next=['Finish independent actual F03event2 HOST acceptance (no replay). Independently review this exact private union/CMake/origin-producer adaptation and source tracking.','Root alone adopts exact reviewed canonical files/new Rust leaf/producer+commandprofile. Current canonical sources unchanged by preparation.','Root materializes exact origin header using pinned producer/commandprofile and proposed arch source; bind output byte equality to preview, Rustenv and fullprofile arch command. This preparation never ran that producer.','Fresh current account/source/ownership/ledger/native controls/resource admission, nonce/export/publication and independent execution review before Root grant. Reuse existing oneheavy holder/protocol, no new authority framework.','Four actual commands only: wholeRust, changedkernelC, changedarchC, raw11link. Retain actualCURRENT111processa4309 and other7objects; no SDK/configure/HOST/completedbuild replay.','Rebind exact final qualifiers/currentconsumer supplement to actual tuple: expected64+23=87C/52Rust/process67 are unaccepted expectations. Reprove all inherited metadata and actual filename origin/385/391/fourcallbacks providers.','Preserve failures/prefixes and positive resource-owner/container joins. Native/wholefile/M14/M15 claims require separate matching evidence.'],actual_nonce=None,actual_resource_authority=None,actual_output_root=None,actual_holder=None,actual_root_release=None,fixed_three_clock_cutoffs=old['fixed_three_clock_cutoffs'],controls='Same creditrun7f4af94a83b14cc08f97401f5891d965/57774.852125 cumulative debits; actual holds; oneheavyCPU2-5/12GiB/noswap/512pids/networknone; permanent27:4/scratch21; aggregate7jobs/23259332608B; HOST16GiB/scratch12GiB and larger original floors.',limitations=['SOURCE_ONLY; no producer/materialization/compiler/test/guard/Docker/guest/sudo/cleanup executed.','No actual Root nonce/resource/holder/release/publication fabricated; canonical unchanged.','Original scripted OPEN/FAIL and all prior failures remain authoritative.']))
save('SOURCE-READY.json',dict(scope=SCOPE,status='PRIVATE_QUALIFIED_COMPOSITION_SOURCE_READY_NOT_ADOPTED_NOT_RELEASED',runtime_authority=None,profile=ref(D/'PROFILE.SOURCE-ONLY.json'),closed_Rust_source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),composition=ref(D/'COMPOSITION-DERIVATION.json'),origin_derivation=ref(D/'ORIGIN-DERIVATION.NOT-RUNTIME.json'),next_steps=ref(D/'ROOT-NEXT-STEPS.NOT-AUTHORITY.json'),tools=tools,commands=4,new_objects=3,retained_objects=8,closed_Rust_sources=113,canonical_writes=0,actual_compilers=0,actual_native_apps=0,actual_tests=0,actual_materializations=0,F03_actual_independent_HOST_acceptance='PENDING_ROOT_BINDING'))
print(json.dumps(dict(status='PRIVATE_SOURCE_READY_NOT_ADOPTED_NOT_RELEASED',commands=4,new_objects=3,retained_objects=8,Rust_sources=113,canonical_writes=0,tests_executed=0,profile=ref(D/'PROFILE.SOURCE-ONLY.json'))))
