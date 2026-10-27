"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private next3 C selections, two new Rust wrappers and exact existing atomic reuse.
Only source copies, bounded diffs and an unrun mock recipe are written here.
"""
from pathlib import Path
import difflib,hashlib,json,re
D=Path(__file__).resolve().parent;E=D.parent;ROOT=E.parents[3]
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
DEFINE='MCKERNEL_RUST_F03_PERF_PROVIDER_NEXT3_BRIDGES';CFG='f03_perf_provider_next3_bridges_selected_candidate'
def ref(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(name,value):
 path=D/name;path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x') as stream:stream.write(value if isinstance(value,str) else json.dumps(value,indent=2)+'\n')
def rows(text):
 logical=1;filename='same-translation-unit';result=[]
 for physical,line in enumerate(text.splitlines(),1):
  m=re.match(r'#line\s+(\d+)(?:\s+"([^"]+)")?',line)
  if m:logical=int(m[1]);filename=m[2] or filename;continue
  result.append(dict(physical=physical,logical=logical,filename=filename,text=line));logical+=1
 return result
names=['kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt','kernel/rust/abi.rs','kernel/rust/x86_perfctr.rs','kernel/rust/atomic_helpers.rs','lib/include/ihk/perfctr.h','arch/x86_64/kernel/include/ihk/atomic.h','CMakeLists.txt']
base={name:(ROOT/name).read_text() for name in names}
assert DEFINE not in base['kernel/syscall.c'] and CFG not in base['kernel/rust/syscall_policy.rs']
assert 'pub type CInt = i32;' in base['kernel/rust/abi.rs'] and 'pub type CLong = i64;' in base['kernel/rust/abi.rs'] and 'pub type CULong = u64;' in base['kernel/rust/abi.rs']
assert 'pub unsafe extern "C" fn ihk_mc_perfctr_init_raw(counter: CInt, code: u32, mode: CInt) -> CInt {' in base['kernel/rust/x86_perfctr.rs']
assert 'int ihk_mc_perfctr_init_raw(int counter, unsigned int code, int mode);' in base['lib/include/ihk/perfctr.h']
assert 'if (BUILD_TARGET STREQUAL "smp-arm64")\n\tset(POSTK_DEBUG_DEFINES ' in base['CMakeLists.txt']
marker='#[no_mangle]\npub unsafe extern "C" fn syscall_atomic64_read_bridge('
policy=base['kernel/rust/syscall_policy.rs'];assert policy.count(marker)==1
start=policy.index(marker);brace=policy.index('{',start);depth=1;end=brace+1
while depth:
 if policy[end]=='{':depth+=1
 if policy[end]=='}':depth-=1
 end+=1
atomic=policy[start:end]+'\n'
assert 'crate::atomic_helpers::ihk_atomic64_read(value.cast())' in atomic
assert 'pub unsafe extern "C" fn ihk_atomic64_read(v: *const IhkAtomic64) -> CLong {\n    (*v).counter64.load(Ordering::SeqCst)\n}' in base['kernel/rust/atomic_helpers.rs']
write('retained-syscall-atomic64-read-bridge.Rust.inc',atomic)
write('retained-abi-types.Rust.inc','pub type CInt = i32;\npub type CLong = i64;\npub type CULong = u64;\n')
write('EXACT-PREIMAGES.json',{name:ref(ROOT/name) for name in names})
specs=[('perf_counter_extra_set_bridge','int','void *event','return ihk_mc_perfctr_set_extra((struct mc_perf_event *)event);'),
 ('perf_counter_init_raw_bridge','int','int counter_id, unsigned long hw_config, int mode','return ihk_mc_perfctr_init_raw(counter_id, hw_config, mode);'),
 ('perf_event_atomic64_read_bridge','long','void *value','return ihk_atomic64_read((ihk_atomic64_t *)value);')]
original=base['kernel/syscall.c'];candidate=original;mapping=rows(original);slices=[]
for name,ret,args,body in specs:
 assert 'fn '+name+'(' not in policy,'assigned C body already has Rust implementation'
 old='static '+ret+'\n'+name+'('+args+')\n{\n\t'+body+'\n}\n'
 assert candidate.count(old)==1,(name,'exact original C body required')
 physical=original[:original.index(old)].count('\n')+1;first=next(r['logical'] for r in mapping if r['physical']==physical);after=first+len(old.splitlines())
 declaration='extern '+ret+' '+name+'('+args+');\n'
 if name=='perf_counter_init_raw_bridge':
  declaration+='_Static_assert(sizeof(unsigned long)==8 && sizeof(unsigned int)==4, "supported Rust perf init code narrowing ABI");\n'
  declaration+='_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_mc_perfctr_init_raw), int (*)(int,unsigned int,int)), "selected x86 Rust provider requires original u32 code ABI");\n'
 if name=='perf_event_atomic64_read_bridge':
  declaration='extern long syscall_atomic64_read_bridge(void *value);\n#define perf_event_atomic64_read_bridge syscall_atomic64_read_bridge\n'
  declaration+='_Static_assert(sizeof(ihk_atomic64_t)==8 && __alignof__(ihk_atomic64_t)==8 && __builtin_offsetof(ihk_atomic64_t,counter64)==0, "existing atomic64 provider layout ABI");\n'
  declaration+='_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_atomic64_read), long (*)(const ihk_atomic64_t *)), "existing atomic64 read provider C ABI");\n'
 selector='#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined('+DEFINE+')\n'+declaration+'#else\n#line '+str(first)+'\n'+old+'#endif\n#line '+str(after)+'\n'
 candidate=candidate.replace(old,selector,1)
 write(name+'.original.C.inc',old);write(name+'.paired-selector.C.inc',selector)
 slices.append(dict(name=name,original=old,selector=selector,physical_first=physical,logical_first=first,logical_after=after,
  selected_Rust_symbol='syscall_atomic64_read_bridge' if name=='perf_event_atomic64_read_bridge' else name))
write('SOURCE-SLICES.json',slices);write('original.C.inc','\n'.join(r['original'] for r in slices));write('paired-selectors.C.inc','\n'.join(r['selector'] for r in slices))
rust=policy+(D/'selected-bridges.Rust.inc').read_text();cm=base['kernel/CMakeLists.txt']
anchor='\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_counter_control_bridges_selected_candidate")\n';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "'+CFG+'")\n',1)
anchor='MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES';assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+';'+DEFINE,1)
for name,text,patch in [('kernel/syscall.c',candidate,'syscall.c.patch'),('kernel/rust/syscall_policy.rs',rust,'syscall_policy.rs.patch'),('kernel/CMakeLists.txt',cm,'CMakeLists.txt.proposal.patch')]:
 write('preimages/'+name,base[name]);write('candidate/'+name,text)
 write(patch,''.join(difflib.unified_diff(base[name].splitlines(keepends=True),text.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name)))
line_items=lambda text:[(r['text'],r['logical'],r['filename']) for r in rows(text) if '__FILE__' in r['text'] or '__LINE__' in r['text']]
assert line_items(original)==line_items(candidate)
reverse=candidate
for row in slices:reverse=reverse.replace(row['selector'],row['original'],1)
assert reverse==original and rust.removesuffix((D/'selected-bridges.Rust.inc').read_text())==policy
assert rust[start:end]+'\n'==atomic,'existing atomic Rust body unchanged in production postimage'
stack=[];gates=[]
for line in cm.splitlines():
 s=line.strip()
 if re.match(r'^if\s*\(',s,re.I):stack.append(s)
 if CFG in s or (DEFINE in s and 'COMPILE_DEFINITIONS' in s):
  assert 'if (ENABLE_PERF)' in stack and 'if (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)' in stack and 'if (MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12")' in stack
  gates.append(dict(line=s,ancestor_conditions=stack.copy()))
 if re.match(r'^endif\s*\(',s,re.I):stack.pop()
assert not stack and len(gates)==2
write('SOURCE-CHECKS.json',dict(scope=SCOPE,status='PASS_PRIVATE_NEXT3_SOURCE_COMPOSITION_ONLY',C_bodies=3,new_Rust_wrapper_bodies=2,existing_Rust_atomic_bridge_reused=1,
 exact_atomic_reuse_sha256=hashlib.sha256(atomic.encode()).hexdigest(),atomic_memory_order_provider_unchanged='SeqCst',
 raw_init_conversion='hw_config: CULong as u32 reproduces genuine x86 unsigned-long to unsigned-int C conversion',
 raw_init_unsupported_variant='Selected genuine C provider-type assertion fails rather than accepting POSTK_DEBUG_TEMP_FIX_29 uint64-code ABI. Original C fallback retains the original header-dependent behavior.',
 reverse_deltas_restore_entire_preimages=True,all_FILE_LINE_logical_identities_preserved=len(line_items(original)),paired_CMake_gates=gates,canonical_writes=0,compiler_commands=0,fixture_runs=0))
OUT=D/'future-host-output-1';RUST=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc');CC=Path('/usr/bin/cc');assert not OUT.exists()
commands=[]
def cmd(id,argv,expected):commands.append(dict(id=id,argv=[str(a) for a in argv],cwd=str(D),purpose=SCOPE+' '+id,expected=expected,timeout_seconds=30,stdout_limit_bytes=16384,stderr_limit_bytes=16384,requires_fresh_Root_ordinary_grant=True))
cmd('rust-host-object',[RUST,'--edition=2021','--crate-name','f03_perf_next3_fixture','--crate-type','lib','--emit=obj','-C','panic=abort','-C','opt-level=2','--cfg','enable_perf','--cfg',CFG,D/'lib.fixture.rs','-o',OUT/'providers.o'],'exit0;two new wrappers plus exact existing Rust atomic forwarding body; ABI16')
flags=['-std=c11','-Wall','-Wextra','-Werror','-O2']
for id,macros,out in [('selected-witness',['MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',DEFINE],'selected.o'),('fallback-none-witness',[],'fallback-none.o'),('fallback-helper-witness',['MCKERNEL_RUST_SYSCALL_POLICY_HELPERS'],'fallback-helper.o'),('fallback-callback-witness',[DEFINE],'fallback-callback.o')]:
 cmd(id,[CC,*flags,*['-D'+m for m in macros],'-c',D/'selector-witness.c','-o',OUT/out],'exit0; selected3 or allthree original C fallback definitions; typed callback/provider ABI')
cmd('host-parity-link',[CC,*flags,D/'driver.c',OUT/'selected.o',OUT/'providers.o','-o',OUT/'parity'],'exit0; inert mocked providers only, no actual PMU or atomic load')
stdout='PASS perf-next3 872 C/Rust pairs; 1744 exact provider traces; ABI16; selected3; reused atomic bridge\n'
cmd('host-parity-run',[OUT/'parity'],'exit0; stdout exactly '+stdout)
source_names=['lib.fixture.rs','selected-bridges.Rust.inc','retained-abi-types.Rust.inc','retained-syscall-atomic64-read-bridge.Rust.inc','selector-witness.c','paired-selectors.C.inc','driver.c','original.C.inc']
write('FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json',dict(scope=SCOPE,status='SOURCE_ONLY_NEXT3_HOST_RECIPE_UNRUN_NOT_GRANTED',runtime_authority=None,sequential=True,compiler_jobs=1,commands=commands,
 future_output_root=str(OUT),output_root_created=False,expected_stdout=stdout,source_inputs=[ref(D/n) for n in source_names],tool_refs=dict(stable_Rust=ref(RUST),C_compiler=ref(CC)),
 expected_C_Rust_pairs=872,expected_single_call_traces=1744,expected_ABI_words=16,selected_callbacks=3,new_Rust_wrappers=2,reused_existing_Rust_bridge=1,
 requires='Fresh exact Root ordinary account/source/ownership/resource grant; old nonces and releases remain consumed.',actual_compiler_commands=0,actual_runtime_tests=0))
print(json.dumps(dict(status='PRIVATE_PERF_NEXT3_SOURCE_READY',C_bodies=3,new_Rust_wrappers=2,reused_atomic_bridge=1,FILE_LINE_identities=len(line_items(original)),mock_recipe_commands=7,mock_recipe_unrun=True,canonical_writes=0)))
