"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private already-HOST-qualified union only. No runtime/materialization/compiler.
"""
import ast,copy,difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;E=D.parent;ROOT=E.parents[3]
U=E/'current112-ready-f06-event2-coherent-source-1'
B=U/'actual-origin-bound-source-1'
A111=E/'ROOT-CURRENT111-COUNTER3-RUNQUEUE208-BUILD-ADMISSION-2'
F06=E/'m14-f06-clone-ptrace-provider-next4-source-1'
F02=E/'m14-f02-scalar-metadata-next4-source-1'
LOCK=E/'m14-f03-lock4-host-preparation-source-1'
FG=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/foreground-f03-lock4-source-1')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(p.read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def write(name,b):
 p=D/name;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b and not p.is_symlink(),name
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(name,x):return write(name,json.dumps(x,indent=2)+'\n')
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def patch(source,pp):
 lines=pp.read_text().splitlines(keepends=True);groups=[];g=None
 for line in lines:
  if line.startswith('@@ '):
   if g is not None:groups.append(g)
   g=[]
  elif g is not None:assert line[0] in ' +-';g.append(line)
 if g is not None:groups.append(g)
 for g in groups:
  a=''.join(l[1:] for l in g if l[0] in ' -');b=''.join(l[1:] for l in g if l[0] in ' +');source=once(source,a,b)
 return source
host_refs=[]
for path,digest in [(F06/'ordinary-host-composition-profile-1/independent-review-1/INDEPENDENT-ACTUAL-HOST-COMPOSITION-ACCEPTANCE.json','a8a98914228d43438d2bf52efb602a35391aaf10a94346cb986052aff314b6e3'),(F02/'independent-source-profile-review-1/INDEPENDENT-ACTUAL-HOST-ACCEPTANCE.json','735c748a9894056a71231128677cab10990edbc0fbeb13f9ce5c62c70372bcf2'),(LOCK/'independent-source-profile-review-1/INDEPENDENT-ACTUAL-HOST-ACCEPTANCE.json','461b133eea0306a3ebb317ffbe1228404883a43bc8f890606494335b9f949d52')]:
 assert ref(path)['sha256']==digest;assert read(path)['decision'].startswith('PASS');host_refs.append(ref(path))
old=read(B/'PROFILE.SOURCE-ONLY.json');adoption_path=U/'root-source-adoption-1/ROOT-SOURCE-ADOPTION.json';adoption=read(adoption_path)
for r in adoption['files']:auth(r['canonical']);auth(r['private_source'])
map_path=Path(old['inputs']['source_directory_exports'][0]['manifest']['path']);oldmap=read(map_path);prior={r['relative']:r for r in oldmap['files']};assert len(prior)==113
base={r['relative']:auth(r['postimage']).read_text() for r in old['inputs']['postimages']}
for name in ['syscall_policy.rs','process_helpers.rs']:base['kernel/rust/'+name]=auth(prior[name]['snapshot']).read_text()
composed={}
composed['kernel/syscall.c']=patch(base['kernel/syscall.c'],FG/'syscall.c.patch')
composed['kernel/rust/syscall_policy.rs']=patch(base['kernel/rust/syscall_policy.rs'],FG/'syscall_policy.rs.patch')+'\n'+(F06/'syscall_policy.rs.fragment').read_text()
composed['arch/x86_64/kernel/syscall.c']=patch(base['arch/x86_64/kernel/syscall.c'],F06/'syscall.c.diff')
composed['kernel/process.c']=patch(base['kernel/process.c'],F02/'process.c.diff')
composed['kernel/rust/process_helpers.rs']=patch(base['kernel/rust/process_helpers.rs'],F02/'process_helpers.rs.diff')
leaves=['f06_clone_reader_lock.rs','f06_clone_reader_unlock.rs','f06_ptrace_find_thread.rs','f06_ptrace_thread_unlock.rs','f06_clone_ptrace_provider_abi.rs']
for name in leaves:composed['kernel/rust/'+name]=(F06/name).read_text()
fragment=(F06/'ROOT-CMAKE-PROPOSAL.fragment').read_text()
needle='\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_rt_sigreturn_check_signal_candidate")\n'
composed['kernel/CMakeLists.txt']=once(base['kernel/CMakeLists.txt'],needle,needle+''.join('\t\t\t\t'+s+'\n' for s in fragment.splitlines()))
# No new LOCK4 or scalar selector: reuse actual existing paired configurations.
commands=copy.deepcopy(old['exact_commands'])
commands.insert(1,copy.deepcopy(read(A111/'PROFILE.SOURCE-ONLY.json')['exact_commands'][1]))
newcfg=['f06_clone_reader_lock_candidate','f06_clone_reader_unlock_candidate','f06_ptrace_find_thread_candidate','f06_ptrace_thread_unlock_candidate']
argv=commands[0]['argv'];idx=next(i for i,v in enumerate(argv) if v.startswith('--emit=obj='));argv[idx:idx]=[v for cfg in newcfg for v in ['--cfg',cfg]]
argv=commands[3]['argv'];idx=next(i for i,v in enumerate(argv) if v.startswith('-I'));argv[idx:idx]=['-D'+v for v in ['MCKERNEL_RUST_F06_CLONE_READER_LOCK','MCKERNEL_RUST_F06_CLONE_READER_UNLOCK','MCKERNEL_RUST_F06_PTRACE_FIND_THREAD','MCKERNEL_RUST_F06_PTRACE_THREAD_UNLOCK']]
assert commands[2]==old['exact_commands'][1] and commands[4]==old['exact_commands'][3]
origin=commands[3]['argv'][-1];assert origin=='/src/arch/x86_64/kernel/syscall.c'
origin_profile=copy.deepcopy(read(U/'candidate/scripts/f06_origin_command_profile.json'))
origin_profile.update(status='CURRENT113_EXACT_PROPOSED_C_PRODUCER_SOURCE_ONLY_NOT_AUTHORITY',predecessor_CURRENT112_source_adoption=ref(adoption_path),predecessor_CURRENT112_origin_context=ref(U/'oci-origin-bind-correction-source-1/ROOT-ACTUAL-ORIGIN-PRODUCER-RESULT.json'),exact_commands=[commands[3]],composed_arch_source_sha256=hashlib.sha256(composed['arch/x86_64/kernel/syscall.c'].encode()).hexdigest())
origin_path=save('candidate/scripts/f06_origin_command_profile.json',origin_profile)
old_producer=(U/'candidate/scripts/derive_f06_origin.py').read_text()
producer=once(old_producer,'Support precisely the private CURRENT112 arch-command profile; reject profile drift.','Support precisely the private CURRENT113 arch-command profile; reject profile drift.')
producer=once(producer,'PROFILE_SHA256 = "'+ref(U/'candidate/scripts/f06_origin_command_profile.json')['sha256']+'"','PROFILE_SHA256 = "'+ref(origin_path)['sha256']+'"')
composed['scripts/derive_f06_origin.py']=producer
assert not re.search(r'^\s*#\s*(?:line\s+)?\d+\s+"',composed['arch/x86_64/kernel/syscall.c'],re.M)
tracking=lambda s:re.findall(r'\b(?:kmalloc_tracked|kfree_tracked)\s*\([^;]*;',s,re.S)
assert tracking(base['arch/x86_64/kernel/syscall.c'])==tracking(composed['arch/x86_64/kernel/syscall.c'])
for relative,text in composed.items():
 if not relative.startswith('kernel/rust/'):write('candidate/'+relative,text)
 before=base.get(relative,'')
 write('patches/'+relative+'.patch',''.join(difflib.unified_diff(before.splitlines(keepends=True),text.splitlines(keepends=True),fromfile='a/'+relative,tofile='b/'+relative)))
rows=[]
for relative in sorted(set(prior)|set(leaves)):
 original=Path(prior[relative]['snapshot']['path']) if relative in prior else F06/relative
 snapshot=write('rust-subtree/'+relative,composed.get('kernel/rust/'+relative,original.read_text()))
 rows.append(dict(relative=relative,original=ref(original),snapshot=ref(snapshot),predecessor_snapshot=prior.get(relative,{}).get('snapshot'),kind='new qualified F06 leaf' if relative not in prior else ('unchanged adopted CURRENT112 source' if ref(snapshot)['sha256']==prior[relative]['snapshot']['sha256'] else 'qualified LOCK4/scalar4 private composition')))
assert len(rows)==118
source_map=dict(scope=SCOPE,runtime_authority=None,schema='mckernel.exact-kernel-rust-subtree-readonly.v1',base_source_root=old['inputs']['source6153']+'/kernel/rust',export_root=str(D/'rust-subtree'),container_destination='/src/kernel/rust',files=rows,total_bytes=sum(r['snapshot']['bytes'] for r in rows),new_leaf_files=leaves,no_symlinks=True,no_hardlinks=True,original_source_mutations=0,predecessor_manifest=ref(map_path))
save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',source_map)
profile=copy.deepcopy(old);profile.update(status='CURRENT113_QUALIFIED_PRIVATE_LOCK4_NEXT4_SCALAR4_UNION_NOT_ADOPTED_NOT_RELEASED',runtime_authority=None)
for key in ['request_sha256','native_custody_clearance','actual_nonce','actual_root_adoption','actual_execution_review','actual_resource_authority','actual_output_root','actual_holder']:profile[key]=None
postimages=[]
for r in old['inputs']['postimages']:
 row=copy.deepcopy(r);relative=row['relative']
 if relative=='kernel/rust/f06-origin/f06_rt_sigreturn_origin.h':
  preview=write('origin-source-preview/f06_rt_sigreturn_origin.h',Path(row['postimage']['path']).read_bytes());row['postimage']=ref(preview);row.pop('actual_origin_producer_receipt',None);row['source_preview_not_runtime_producer']=True
 else:row['postimage']=ref(write('candidate/'+relative,composed.get(relative,base[relative])))
 postimages.append(row)
profile['inputs']['postimages']=postimages
profile['inputs']['source_directory_exports']=[dict(host_path=str(D/'rust-subtree'),container_destination='/src/kernel/rust',readonly=True,manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
profile['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in postimages]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in rows]
for r in profile['inputs']['objects']:
 if r['build_relative']=='kernel/CMakeFiles/mckernel.img.dir/process.c.o':r['replace']=True;r['action']='Rebuild changed CURRENT113 scalar4 processC; actualCURRENT111object provenance only'
assert sum(r['replace'] for r in profile['inputs']['objects'])==4
profile['inputs']['retained_count']=7;profile['inputs']['replaced_count']=4;profile['exact_commands']=commands
profile['predecessor_CURRENT112_source_adoption']=ref(adoption_path)
profile['qualified_HOST_new_slices']=host_refs
profile['origin_source_materialization']=dict(scope=SCOPE,runtime_authority=None,status='CURRENT113_NEW_ORIGIN_PRODUCER_REQUIRED_NOT_EXECUTED',source_only=True,actual_producer_receipt=None,actual_generated_header=None,actual_origin_binding=None,actual_Rust_environment=None,actual_CMake_origin=None,canonical_adoption_inputs=[dict(relative='scripts/derive_f06_origin.py',postimage=ref(D/'candidate/scripts/derive_f06_origin.py')),dict(relative='scripts/f06_origin_command_profile.json',postimage=ref(origin_path))],compiler_OCI_mounts_for_helpers=0,predecessor_actual112_receipt_historical_only=ref(U/'oci-origin-bind-correction-source-1/ROOT-ACTUAL-ORIGIN-PRODUCER-RESULT.json'))
contract=profile['producer_contract'];contract.update(source='Exact Root-adopted CURRENT112 source plus independently HOST-qualified LOCK4/F06cloneptrace4/F02scalar4 private union; no CURRENT112 or CURRENT113 build acceptance inferred',new_objects=[r['build_relative'] for r in profile['inputs']['objects'] if r['replace']],reused_objects=7,process_delta='Rebuild processC for four signed C-int scalar owners: process_init_stack_user_category/page_fault_anon_clear_profile_event/memset_smp_fast_word_pattern/dump_tree_enabled; expected67->63C OBJECTs. Preserve accepted111runqueue208 and inherited timer120/idle116/logger/FILELINE.',expected_F03_C_functions=60,expected_F06_C_functions=19,expected_total_selected_C_functions=79,expected_current_cohort_Rust_function_exports=58,expected_process_OBJECT_records=63,expected_new_C_function_removals=['ptrace_report_clone_noirq_lock_bridge','ptrace_report_clone_noirq_unlock_bridge','ptrace_wakeup_update_lock_bridge','ptrace_wakeup_update_unlock_bridge','arch_clone_reader_lock_bridge','arch_clone_reader_unlock_bridge','arch_ptrace_find_thread_bridge','arch_ptrace_thread_unlock_bridge'],expected_new_Rust_data=['process_init_stack_user_category','process_page_fault_anon_clear_profile_event','process_memset_smp_fast_word_pattern','process_dump_tree_enabled'],counts_are_unaccepted_expectations=True)
contract['postbuild_required']=[s.replace('three-object','four-object').replace('eight unchanged retained objects and three new objects','seven unchanged retained objects and four new objects').replace('retained actual CURRENT111 processa4309 remains unchanged','new processC must prove scalar4 ownership and all inherited process ABI/data').replace('unchanged retained actual CURRENT111 processa4309; no fresh processC is produced','new scalar4 processC with exact runqueue208 external ownership') for s in contract['postbuild_required']]
contract['postbuild_required'] += ['Fresh actual CURRENT113 origin producer bound to changed architecture source and proposed archargv; original112origin is historical only. Preserve exact actual filename/Rustenv/385/391 and all unrelated tracking.', 'Prove new LOCK4 four C callbacks absent with two reused noirq Rust exports plus two new wakeup exports. HOST mock parity is not new rawtrace/MCS/IRQ/native evidence.', 'Prove new F06cloneptrace4 unique actual Rust providers and typed ABI/selected+fallback behavior without widening lock/node/thread ownership assumptions.', 'Prove four new scalar Rust owners are each4B signed CInt/align4/readonly values1,4002(ifprofile),1,0 and actual C consumers; unsupported C macro configs must keep original compileassert rejection.']
profile['reuse_descriptor']=str(D/'FROZEN-FIVE-COMMAND-SEVEN-INPUT-REUSE.json')
save('FROZEN-FIVE-COMMAND-SEVEN-INPUT-REUSE.json',dict(scope=SCOPE,runtime_authority=None,predecessor_source_profile=ref(B/'PROFILE.SOURCE-ONLY.json'),predecessor_source_adoption=ref(adoption_path),actual_accepted_artifact='CURRENT111 remains accepted; CURRENT112 source adopted/origin generated but not built',configuration=profile['inputs']['configuration'],objects=profile['inputs']['objects'],new_objects=contract['new_objects'],actual_commands=commands,SDK21_recompiled=False,configuration_reuse_not_fresh_configure=True,previous_commands_replayed=False))
save('PROFILE.SOURCE-ONLY.json',profile)
plan=read(B/'EXACT-FOUR-COMMAND-PROPOSAL.NOT-GRANTED.json');plan.update(commands=commands,source_profile=ref(D/'PROFILE.SOURCE-ONLY.json'),producer_contract=contract)
save('EXACT-FIVE-COMMAND-PROPOSAL.NOT-GRANTED.json',plan)
# Existing five-command producer with OCI header precreation retained.
runner=(B/'run_build_only.py').read_text()
for a,b in [
 ("outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']","outputs=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o','mckernel.img']"),
 ("sources=['/src/kernel/rust/lib.rs','/src/kernel/syscall.c','/src/arch/x86_64/kernel/syscall.c']","sources=['/src/kernel/rust/lib.rs','/src/kernel/process.c','/src/kernel/syscall.c','/src/arch/x86_64/kernel/syscall.c']"),
 ('matching eight-object/three-replacement reuse descriptor','matching seven-object/four-replacement reuse descriptor'),
 ("len(commands)==4,'exact four selected successor commands'","len(commands)==5,'exact five selected successor commands'"),
 ('all three changed compiler source paths','all four changed compiler source paths'),
 ("==8 and sum(r['replace'] for r in profile['inputs']['objects'])==3,'eight accepted retained and three new objects'","==7 and sum(r['replace'] for r in profile['inputs']['objects'])==4,'seven accepted retained and four new objects'"),
 ("set(outputs[:3]),'exact three selected replacement object paths'","set(outputs[:4]),'exact four selected replacement object paths'"),
 ("elif i<3:require(argv[0]","elif i<4:require(argv[0]"),
 ("name='current112-build-only-'","name='current113-build-only-'"),
]:runner=once(runner,a,b)
worker=(B/'build_only_worker.py').read_text();worker=once(worker,"len(plan['commands'])==4,'exact four selected build commands'","len(plan['commands'])==5,'exact five selected build commands'");worker=once(worker,'ACTUAL_BUILD_ONLY_FOUR_COMMAND_PRODUCER','ACTUAL_BUILD_ONLY_FIVE_COMMAND_PRODUCER')
tools=[]
for name,text in [('run_build_only.py',runner),('build_only_worker.py',worker)]+[(n,(B/n).read_text()) for n in ['hold_and_run_build_only.py','publish_approved_ready.py']]:
 ast.parse(text,filename=name);out=write(name,text);delta=write('tool-diffs/'+name+'.diff',''.join(difflib.unified_diff((B/name).read_text().splitlines(keepends=True),text.splitlines(keepends=True),fromfile='CURRENT112/'+name,tofile='CURRENT113/'+name)));tools.append(dict(name=name,predecessor=ref(B/name),successor=ref(out),diff=ref(delta)))
ast.parse(producer,filename='derive_f06_origin.py')
export=read(B/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json');export.update(status='CURRENT113_SOURCE_EXPORT_TEMPLATE_NOT_AUTHORITY',author=None,decision=None,request_sha256=None)
export.pop('actual_origin_producer_receipt',None);export.pop('actual_origin_context',None)
export['qualified_readonly_files']=[r['source'] for r in profile['inputs']['configuration']]+[r['source'] for r in profile['inputs']['objects'] if not r['replace']]+[r['postimage'] for r in postimages]+[r['snapshot'] for r in rows]
save('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export)
output=D/'ROOT-CURRENT113-ORIGIN-PRODUCER-OUTPUT-1';assert not output.exists()
save('NEW-ORIGIN-PRODUCER.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,status='FRESH_CURRENT113_SOURCE_PRODUCER_REQUIRED_NOT_EXECUTED',cwd=str(ROOT),argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'candidate/scripts/derive_f06_origin.py'),'--profile',str(origin_path),'--source',str(D/'candidate/arch/x86_64/kernel/syscall.c'),'--output',str(output)],producer=ref(D/'candidate/scripts/derive_f06_origin.py'),origin_command_profile=ref(origin_path),proposed_arch_command=commands[3],architecture_source=ref(D/'candidate/arch/x86_64/kernel/syscall.c'),expected_origin_utf8=origin,expected_origin_with_nul=list(origin.encode()+b'\0'),header_source_preview=next(r['postimage'] for r in postimages if r.get('source_preview_not_runtime_producer')),actual_producer_receipt=None,actual_generated_header=None,actual_invocations=0,Root_obligation='Fresh Root-authorized exact source producer, genuine header/env/binding receipt and additive profile/export/cohort rebind before any113build release. Do not reuse actual112producer result for changed source/argv. No /src/scripts OCI helper binds; canonical CMake/script/profile adoption stays separately required.'))
save('COMPOSITION-DERIVATION.json',dict(scope=SCOPE,runtime_authority=None,base_exact112Root_adoption=ref(adoption_path),accepted_current_artifact=ref(A111/'independent-final-consumer-review-1/DEFAULT-ARTIFACT-REVIEW.json'),actual_HOST_acceptances=host_refs,source_fragments=[ref(FG/n) for n in ['syscall.c.patch','syscall_policy.rs.patch']]+[ref(F06/n) for n in ['syscall.c.diff','syscall_policy.rs.fragment','ROOT-CMAKE-PROPOSAL.fragment']+leaves]+[ref(F02/n) for n in ['process.c.diff','process_helpers.rs.diff']],LOCK4_new_Rust_exports=2,LOCK4_reused_Rust_exports=2,new_F06_Rust_exports=4,new_F02_scalar_Rust_OBJECTs=4,new_C_runtime_objects=0,closed_Rust_sources=118,arch_tracked_call_expressions_unchanged=len(tracking(base['arch/x86_64/kernel/syscall.c'])),changed_sources=sorted(composed),original112files_modified=0,canonical_writes=0,actual_producer=0,actual_compilers=0,actual_materializations=0,limits=['Exact source composition only; no current113compiler/default/native acceptance.','HOST mock controls do not prove new actual rawtrace/MCS/IRQ semantics.','NativeRoot4 entry has priority;112 remains ready and must not wait for this union.']))
save('ROOT-NEXT-STEPS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,owner='/root',next_steps=['Independently review exact private union and HOST proof scopes before Root canonical adoption; no re-port/replay.', 'Root/nativeRoot4 retains priority. Current112 remains untouched and ready; this union never blocks native or112.', 'Bind fresh actual113origin producer/header/env/source+archargv and rebind profile/export/cohort before fresh compiler admission;112receipt is historical only.', 'Root source adoption/publication/currentaccount/source/nativeownership/resource/nonce/output/holder/independentexecutionreview+grant are required; use existing oneheavy protocol, no new framework.', 'Five actual commands proposed: wholeRust/processC/kernelC/archC/raw11link; four changed objects and seven exact retained inputs, no SDK/configure/HOST replay.', 'Exact new tuple must reprove inherited112/111ABI/metadata/currentconsumer obligations, all new LOCK4/F06next4/scalar4 boundaries and all original OPEN/FAIL. Counts60+19=79C/58Rust/process63 are unaccepted expectations.'],actual_nonce=None,actual_resource_authority=None,actual_output_root=None,actual_holder=None,actual_release=None,fixed_three_clock_cutoffs=profile['fixed_three_clock_cutoffs'],controls='Same7fcreditrun/57774.852125 cumulative debits and realholds; CPU2-5/12GiB/noswap/512pids/networknone oneheavy/permanent27:4/scratch21;7aggregatejobs/23259332608B and originalfreefloors.',actual_native_or_compiler=0))
save('SOURCE-READY.json',dict(scope=SCOPE,status='PRIVATE_CURRENT113_QUALIFIED_UNION_SOURCE_READY_NOT_ADOPTED_NOT_RELEASED',runtime_authority=None,profile=ref(D/'PROFILE.SOURCE-ONLY.json'),source_map=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),composition=ref(D/'COMPOSITION-DERIVATION.json'),new_origin_producer=ref(D/'NEW-ORIGIN-PRODUCER.NOT-GRANTED.json'),next_steps=ref(D/'ROOT-NEXT-STEPS.NOT-AUTHORITY.json'),tools=tools,commands=5,new_objects=4,retained_objects=7,closed_Rust_sources=118,current112_modified=False,canonical_writes=0,actual_compilers=0,actual_materializations=0))
print(json.dumps(dict(status='PRIVATE_SOURCE_READY_NOT_RELEASED',profile=ref(D/'PROFILE.SOURCE-ONLY.json'),ready=ref(D/'SOURCE-READY.json'),Rust_sources=118,commands=5,new_objects=4,retained_objects=7)))
