"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Compose only frozen LOCAL14/config3 and final14 deltas; propose ordinary HOST checks.
No compiler/CPP/guard/resource query/runtime/source-authority/canonical operation.
"""
import ast,copy,difflib,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent;E=D.parent;ROOT=E.parents[3]
N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717')
L=N/'f02-local14-companion-source-1';F=N/'f02-final14-metadata-source-1'
COMP=E/'m14-f02-local14-config-companions-source-1'
G=E/'m14-f02-verbose32-host-preparation-source-1'
SUFFIX=G/'joint-retain-linker-correction-source-1'
A=E/'ROOT-CURRENT114-GLOBAL32-PERF3-BUILD-ADMISSION-1'
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

def save(n,x):return ref(write(n,json.dumps(x,indent=2)+'\n'))
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
def patch(source,p):
 groups=[];g=None
 for line in p.read_text().splitlines(True):
  if line.startswith('@@ '):
   if g is not None:groups.append(g)
   g=[]
  elif g is not None:assert line[0] in ' +-';g.append(line)
 if g is not None:groups.append(g)
 for g in groups:
  before=''.join(x[1:] for x in g if x[0] in ' -');after=''.join(x[1:] for x in g if x[0] in ' +');source=once(source,before,after)
 return source
assert ref(L/'READY.SOURCE-ONLY.json')['sha256'].startswith('4bb0')
assert ref(F/'READY.SOURCE-ONLY.json')['sha256'].startswith('5d4d')
p=read(A/'PROFILE.SOURCE-ONLY.json');mapping=read(auth(p['inputs']['source_directory_exports'][0]['manifest']));prior={r['relative']:r for r in mapping['files']};assert len(prior)==119
post={r['relative']:r for r in p['inputs']['postimages']}
base={'kernel/CMakeLists.txt':auth(post['kernel/CMakeLists.txt']['postimage']).read_text(),'kernel/process.c':auth(post['kernel/process.c']['postimage']).read_text(),'kernel/rust/process_helpers.rs':auth(prior['process_helpers.rs']['snapshot']).read_text(),'kernel/rust/process_verbose_data.rs':auth(prior['process_verbose_data.rs']['snapshot']).read_text()}
composed={}
for relative,old in base.items():
 leaf=Path(relative).name
 first=patch(old,L/(leaf+'.patch'))
 final=patch(first,F/(leaf+'.patch')) if relative!='kernel/rust/process_verbose_data.rs' else first
 composed[relative]=final
 before=write('preimages/'+relative,old);after=write('candidate/'+relative,final)
 write('patches/'+relative+'.patch',''.join(difflib.unified_diff(old.splitlines(True),final.splitlines(True),fromfile='actual114/'+relative,tofile='privateLOCAL14final14/'+relative)))
# For C and actual Rust consumer/type file, the original frozen conditional proofs apply exactly.
assert composed['kernel/process.c']==(F/'postimage/kernel/process.c').read_text()
assert composed['kernel/rust/process_helpers.rs']==(F/'postimage/kernel/rust/process_helpers.rs').read_text()
assert composed['kernel/rust/process_verbose_data.rs']==(L/'postimage/kernel/rust/process_verbose_data.rs').read_text()
assert (L/'local14_config_storage.REUSED.rs').read_bytes()==(COMP/'local14_config_storage.FRAGMENT.rs').read_bytes()
assert 'unsafe impl<T> Sync for ReadonlyPointerCell<T> {}' in composed['kernel/rust/process_helpers.rs']
assert 'unsafe impl Sync for SchedExitDebug' not in composed['kernel/rust/process_helpers.rs']
assert 'NOT ENABLE_FUGAKU_HACKS' in composed['kernel/CMakeLists.txt']
records=[]
for r in mapping['files']:
 relative='kernel/rust/'+r['relative'];data=composed.get(relative)
 dest=write('rust-subtree/'+r['relative'],data if data is not None else auth(r['snapshot']).read_bytes())
 row=copy.deepcopy(r);row.update(snapshot=ref(dest),predecessor_snapshot=r['snapshot'],kind='frozen LOCAL14/final14 source composition' if data is not None else 'unchanged actual114 source')
 records.append(row)
source_map=copy.deepcopy(mapping);source_map.update(export_root=str(D/'rust-subtree'),files=records,total_bytes=sum(r['snapshot']['bytes'] for r in records),predecessor_manifest=p['inputs']['source_directory_exports'][0]['manifest'],new_leaf_files=[],original_source_mutations=0)
save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',source_map)
save('COMPOSITION-AND-LIMITS.json',dict(scope=SCOPE,runtime_authority=None,status='PRIVATE_DEFAULT_ONLY_ATOMIC_LOCAL14_CONFIG3_FINAL14_SOURCE_PROPOSAL',actual114_source_profile=ref(A/'PROFILE.SOURCE-ONLY.json'),actual114_producer=ref(A/'OUTPUT/work/evidence/producer-contract.json'),frozen_packets=[ref(L/'READY.SOURCE-ONLY.json'),ref(F/'READY.SOURCE-ONLY.json')],retained_companion=[ref(COMP/'SOURCE-READY.json'),ref(COMP/'PARENT-LOCAL14-CONFIG-INTERFACE.json')],applied_patches=[ref(L/(Path(r).name+'.patch')) for r in base]+[ref(F/(Path(r).name+'.patch')) for r in base if r!='kernel/rust/process_verbose_data.rs'],proposed_files=[dict(relative=r,preimage=ref(D/'preimages'/r),candidate=ref(D/'candidate'/r)) for r in composed],source_line_proofs_reused=[ref(L/'STATIC-CHECKS.json'),ref(F/'STATIC-CHECKS.json')],logical_C_proof_scope='Composed process.c and process_helpers.rs byte-identical frozen final14 postimages; local typed descriptor module byte-identical frozenLOCAL14. Reuse16/20known-profile source checks, no CPP/all-profile inference.',owned_counts=dict(Rust_internal_debug_objects=14,debug_slots=14,debug_bytes=448,companion_config_objects=3,companion_config_bytes=384,final_readonly_objects=14,final_readonly_bytes=256),ABI_source='Existing actual ArchMemclear alias, SchedExitDebug pointee and config types; no mirrors or visibility widening. Raw-cell Sync is cell-bits only, not pointee Sync.',selection_limit='Existing option defaultsON. Selected RUSAGE_DEBUG/TIMER_CPU_ID/ARCH_MEMCLEAR reject unless local-companion optionOFF; directFugaku selection rejects and CMake excludesFugaku. Those nondefault supported fallback obligations remain OPEN, not waived.',C_globalization=False,new_runtime_bodies=0,remaining_C_symbol_count=None,whole_file_or_native_acceptance=False,canonical_or_Git_writes=0,all_actual_calls=0))
# Reuse old genuine three-config ABI predicates on the ACTUAL included process TU.
abi=(COMP/'fixture/genuine_three_config_abi.c').read_text();asserts=abi[abi.index('_Static_assert'):]
fixture='/* '+SCOPE+' */\n#include '+json.dumps(str(D/'candidate/kernel/process.c'))+'\n'+asserts
fixture+='\n_Static_assert(sizeof(struct process_init_stack_entry_config)==168 && __alignof__(struct process_init_stack_entry_config)==8,"actual init-stack168B ABI");\n'
write('fixture/genuine_candidate_abi.c',fixture)
# Reuse known exact metadata maps and existing ELF/metadata readers, never generate another ABI framework.
for src,name in [(L/'EXACT-LOCAL14-CONFIG3-MAP.json','EXACT-LOCAL14-CONFIG3-MAP.json'),(F/'EXACT14-TYPES-AND-CONSUMERS.json','EXACT14-TYPES-AND-CONSUMERS.json')]:write(name,src.read_bytes())
# Literal ordinary HOST commands: selected whole Rust, selected actualC+ABI, optionOFF C,
# two partial links (retained LLVM21 GNU_RETAIN profile), fixed CPP controls, object/consumer reader.
oldrecipe=read(G/'COMMAND-RECIPE.NOT-ADMITTED.json')['commands'];selected_old=next(c for c in oldrecipe if 'selected-process' in c['name'] or ('selected' in c['name'] and '/usr/bin/gcc-9'==c['argv'][0]))
cc=selected_old['argv'];stop=cc.index('-c');flags=cc[1:stop]
# Remove old selected filename/flags/local selectors, bind exact new actual included TU.
flags=[v for v in flags if not v.startswith(('-DMCKERNEL_PROCESS_DDEBUG_FILE=','-DMCKERNEL_PROCESS_DDEBUG_FLAGS=')) and v not in ['-DMCKERNEL_RUST_PROCESS_VERBOSE_LOCAL_COMPANIONS']]
if '-DMCKERNEL_RUST_PROCESS_VERBOSE_DATA' not in flags:flags.append('-DMCKERNEL_RUST_PROCESS_VERBOSE_DATA')
flags+=['-DMCKERNEL_PROCESS_DDEBUG_FLAGS=0','-DMCKERNEL_PROCESS_DDEBUG_FILE='+json.dumps(str(D/'candidate/kernel/process.c'))]
OUT=D/'HOST-output-proposed-1';CAP=D/'future-capture-1'
assert not OUT.exists() and not CAP.exists()
rust=copy.deepcopy(p['exact_commands'][0]['argv'])
oldRustTool=next(c['argv'][next(i for i,v in enumerate(c['argv']) if v.endswith('/rustc'))] for c in oldrecipe if any(v.endswith('/rustc') for v in c['argv']))
rust[rust.index('/nightly/bin/rustc')]=oldRustTool
for i,v in enumerate(rust):
 if v.startswith('MCKERNEL_PROCESS_C_FILE='):rust[i]='MCKERNEL_PROCESS_C_FILE='+str(D/'candidate/kernel/process.c')
 if v.startswith('MCKERNEL_PROCESS_DDEBUG_FLAGS='):rust[i]='MCKERNEL_PROCESS_DDEBUG_FLAGS=0'
 if v.startswith('--emit=obj='):rust[i]='--emit=obj='+str(OUT/'rust-selected.o')
 if v=='/src/kernel/rust/lib.rs':rust[i]=str(D/'rust-subtree/lib.rs')
idx=next(i for i,v in enumerate(rust) if v.startswith('--emit=obj='));rust[idx:idx]=['--cfg','process_verbose_local_companions']
# No new runtime C code in ABI wrapper: includes actual candidate and frozen static assertions only.
selected=['/usr/bin/gcc-9']+flags+['-DMCKERNEL_RUST_PROCESS_VERBOSE_LOCAL_COMPANIONS','-c',str(D/'fixture/genuine_candidate_abi.c'),'-o',str(OUT/'selected.o')]
fallback=['/usr/bin/gcc-9']+flags+['-c',str(D/'fixture/genuine_candidate_abi.c'),'-o',str(OUT/'optionOFF.o')]
linker=read(SUFFIX/'PROFILE.NOT-GRANTED.json')['commands'][0]['argv'][:4];assert linker[-1]=='-r' and 'rust-lld' in linker[0]
retained_rust=ref(A/'OUTPUT/work/output/build/kernel/rust/mckernel_rust.o');retained_process=ref(A/'OUTPUT/work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o')
cppbase=['/usr/bin/gcc-9']+flags
control_plan=[]
for feature in ['RUSAGE_DEBUG','TIMER_CPU_ID','ARCH_MEMCLEAR','ENABLE_FUGAKU_HACKS']:
 for selected_mode in [True,False]:
  name=feature+('-selected-reject' if selected_mode else '-optionOFF-fallback')
  argv=cppbase+(['-DMCKERNEL_RUST_PROCESS_VERBOSE_LOCAL_COMPANIONS'] if selected_mode else [])+['-D'+feature,'-E',str(D/'candidate/kernel/process.c'),'-o',str(OUT/(name+'.i'))]
  control_plan.append(dict(name=name,argv=argv,expected_reject=selected_mode,diagnostic='Unqualified final process metadata profile; disable local companions for C fallback' if selected_mode else None))
save('FIXED-CPP-CONTROLS.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,commands=control_plan,limits='These fixed preprocessor controls prove selected rejection and optionOFF preprocessing only. Nondefault C object/link/runtime compatibility remains OPEN. No new all-profile acceptance.'))
commands=[dict(name='00-new-fullRust-local14-final14-consumers',argv=rust),dict(name='01-actual-selected-processTU-and-genuine-configABI',argv=selected),dict(name='02-optionOFF-original-C-config-metadata',argv=fallback),dict(name='03-new-selected-partial-link',argv=linker+[str(OUT/'rust-selected.o'),str(OUT/'selected.o'),'-o',str(OUT/'selected-joint.o')]),dict(name='04-optionOFF-partial-link-retained-actual114Rust',argv=linker+[retained_rust['path'],str(OUT/'optionOFF.o'),'-o',str(OUT/'optionOFF-joint.o')]),dict(name='05-fixed-selected-reject-optionOFF-CPP',argv=['/usr/bin/python3','-B',str(D/'run_fixed_cpp_controls.py'),str(D/'FIXED-CPP-CONTROLS.NOT-GRANTED.json')]),dict(name='06-new-object-config-and-actual-consumer-readback',argv=['/usr/bin/python3','-B',str(D/'qualify_changed_objects.py'),str(OUT)])]
for c in commands:c['purpose']=SCOPE+' '+c['name']
save('EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,commands=commands,retained_actual114_Rust=retained_rust,retained_actual114_process=retained_process,passed_GLOBAL32_prefix_replayed=False,execution_authority=None))
# Ordinary CPU6 profile reused from GLOBAL32 corrected suffix, resource controls untouched.
host=read(SUFFIX/'PROFILE.NOT-GRANTED.json');host.update(task_id='F02-LOCAL14-CONFIG3-FINAL14-DEFAULT-HOST-PROPOSAL',status='SOURCE_PROFILE_NOT_GRANTED',capture_root=str(CAP),LOCAL14_selected=True,production_acceptance=False)
host['commands']=[dict(id=c['name'],argv=c['argv'],purpose=c['purpose']) for c in commands]
host['leaves']=[dict(name='F02local14final14changed',first=0,last=6,plan=ref(D/'EXACT-SEVEN-COMMAND-HOST-PROPOSAL.NOT-GRANTED.json'),output=str(OUT),expected_stdout='F02 LOCAL14+FINAL14 HOST boundary PASS\n')]
# New controls reuse the original4GiB envelope; full source compiler is the only new Rust object.
host['host_growth_reserve_bytes']=4294967296
host['internal_and_capture_bound_bytes']=dict(outer_capture_max=7*2*67108864,CPP_internal_capture_max=8*2*67108864,positive_objects_and_partial_links_max=5*67108864,metadata_reserve=134217728,compiler_temp_reserve=2*67108864,total=2617245696,headroom_to_4GiB=1677721600)
host['scope_limit']='Default0/localON only, selected nondefault rejection and optionOFF_CPP explicit. No source integration/wholefile/native/allprofile credit.'
# The fixed helper sources are written by the following adjacent source preparation.
save('PROFILE.PENDING-HELPER-CLOSURE.NOT-GRANTED.json',host)
save('REUSED-EVIDENCE-AND-OPEN-PREDICATES.json',dict(scope=SCOPE,runtime_authority=None,LOCAL14_SOURCE=ref(L/'READY.SOURCE-ONLY.json'),FINAL14_SOURCE=ref(F/'READY.SOURCE-ONLY.json'),GLOBAL32_existing_profile=ref(SUFFIX/'PROFILE.NOT-GRANTED.json'),old_GLOBAL32_passed_tests_to_replay=0,existing_ELF_reader=ref(E/'f02-source38-next-current-integration-source-1/check_thirteen_storage.py'),existing_registry_reader=ref(G/'qualify_metadata.py'),retained_actual114_Rust=retained_rust,retained_actual114_process=retained_process,required_new_compiler_scope=['genuine actual-C three config384B and init-stack168B ABI','full new Rust private types/readonly cell/default config compilation','LOCAL14 ELFLOCAL14 internal vs originalC14, exact config14pointers/scalars/callbacks','14metadata256B exact unique readonly owners/6filenames/NULL/timer/4lines/nineinitcallbacks','actual compiled current consumer refs/folded forms and registry GNU_RETAIN/2496B/78slots','selected unsupported3macro rejection, explicit optionOFF_CPP and Fugaku exclusion'],actual_folded_consumer_missing_relocation_policy='Record OPEN and preserve actual objects; independent exact compiled instruction/dataflow proof is required, never infer accepted consumer from missing relocation.',nondefault_supported_fallback_obligation='DefaultON rejection is a real visible compatibility limitation. OptionOFF CPP success alone is not allvariant object/link/native support. No silent waiver.',remaining_C_symbol_total=None,default_source_not_adopted=True,all_actual_calls=0))
print(json.dumps(dict(decision='COMPOSITION_AND_HOST_COMMANDS_PREPARED_HELPER_CLOSURE_PENDING',files=4,Rust_files=119,HOST_commands=7,actual_calls=0)))
