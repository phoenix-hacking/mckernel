"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare exact production sources/commands only; no compiler/test/CPU reservation.
"""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;B=P.parent;S=P/'source';O=P/'output-1'
OLD=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-4/m14-process-next/production-consumer-preparation-1/coherent-current78-refresh-1')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def main():
 S.mkdir();previous=OLD/'ACTUAL-PRODUCTION-WHOLE-JOIN.json';assert pin(previous)['sha256']=='11a772d7dc46b8d35cf9ddfad585409403245414ebfd58bf3521345464d6b764'
 oldrpath=OLD/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json';oldcpath=OLD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-EXECUTED.json';oldr=json.loads(oldrpath.read_text());oldc=json.loads(oldcpath.read_text())
 assert len(oldr['source_inputs'])==78 and len(oldr['argv'])==48
 assert pin(ROOT/'kernel/rust/process_helpers.rs')['sha256']=='3f2c3dc03445147addee47d77e3ad2b31207fb3bfaa591ad99b6d0d9c897932e'
 assert pin(ROOT/'kernel/process.c')['sha256']=='64af918855ea361bd850d6ad7480d304634c28814e04127fe3dec8c013f21044'
 assert pin(B/'candidate/process_helpers.rs')['sha256']=='17c927e656d0c8f3107bb21cfffd76bf5a4bc95002b8bd34cb00294d13fb2eb8'
 assert pin(B/'candidate/process.c')['sha256']=='08c238a08066a6eda5f346bbd6e6f87333bd505d8d598276dc9c52cd43568a45'
 expected_current={'kernel/rust/mem_helpers.rs':'4635a252332cd369e36384f04a414e2b4c2d79726a4f95caafcf1d3ed1a56b4d','kernel/rust/syscall_policy.rs':'f1f7866c0f2ccc8e1b0024dfb632ec7359dd2a0a4bcd8e22deb957d48ef6d770','kernel/rust/x86_memory_helpers.rs':'2994b6fe46feb6d0f6dd1390cd4a4efc550f8dfee66c067e506eba16b00029d7'}
 inputs={};current_changes={};private_changes=[]
 for key,row in sorted(oldr['source_inputs'].items()):
  canonical=ROOT/key;current=pin(canonical)
  if current['sha256']!=row['private']['sha256']:current_changes[key]=dict(accepted_before=row['private'],canonical=current)
  src=B/'candidate/process_helpers.rs' if key=='kernel/rust/process_helpers.rs' else canonical
  dst=S/key;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);private=pin(dst)
  if private['sha256']!=row['private']['sha256']:private_changes.append(key)
  inputs[key]=dict(accepted_before=row['private'],canonical_before=current,private=private,modified_target=key=='kernel/rust/process_helpers.rs')
 assert set(current_changes)==set(expected_current)
 for key,sha in expected_current.items():assert current_changes[key]['canonical']['sha256']==sha
 assert inputs['kernel/rust/x86_cpu_helpers.rs']['canonical_before']['sha256']=='a6e7465d7924755c97e5d72919a97c2985aacd35cf9db417c4ee981b4d5d071a'
 assert set(private_changes)==set(expected_current)|{'kernel/rust/process_helpers.rs'}
 identity_rows=[[key,row['private']['sha256'],row['private']['bytes']] for key,row in inputs.items()];identity=hashlib.sha256(json.dumps(identity_rows,separators=(',',':')).encode()).hexdigest()
 argv=oldr['argv'][:];argv[46]='--emit=obj='+str(O/'mckernel_rust.o');argv[47]=str(S/'kernel/rust/lib.rs');assert [i for i,(a,b) in enumerate(zip(argv,oldr['argv'])) if a!=b]==[46,47]
 assert pin(Path(argv[6]))['sha256']=='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09'
 nmfile=OLD/'actual-production-capture-1/01-current78-Rust-symbols/stdout';nmrows=[line.split() for line in nmfile.read_text().splitlines() if line.split()]
 oldU={row[-1] for row in nmrows if row[-2]=='U'};oldT={row[-1] for row in nmrows if row[-2]=='T'}
 addedT={'remote_flush_tlb_cpumask','arch_ptrace','syscall_signalfd_publish_bridge','x86_clear_range_l4_body','vm_range_insert_log_bridge'}
 removedU={'syscall_signalfd_publish_bridge','vm_range_insert_log_bridge'};addedU={'process_vm_range_insert_debug','x86_clear_range_l3_callback'}
 assert removedU<=oldU and not addedU&oldU and not addedT&oldT
 assert {'kprintf','memset'}<=oldT
 assert {'syscall_alloc_bridge','syscall_mckfd_lock_bridge','syscall_mckfd_unlock_bridge'}<=oldU
 rust=dict(scope=SCOPE,status='PREPARED_NOT_GRANTED_NOT_EXECUTED',source_count=78,source_inputs=inputs,source_identity=identity,source_identity_rows=identity_rows,accepted_prior_whole_join=pin(previous),accepted_prior_Rust_recipe=pin(oldrpath),accepted_prior_Rust_symbols=pin(nmfile),accepted_prior_object_not_rehashed=json.loads(previous.read_text())['objects']['Rust'],canonical_refresh=current_changes,private_changed_from_accepted_11a=private_changes,only_private_override_from_current='kernel/rust/process_helpers.rs',argv=argv,argv_changed_indices=[46,47],compiler_sha256='70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09',cfg_count=4,CGU=1,closure_external_modules=2,profile=oldr['profile'],expected_T_delta=dict(removed=[],added=sorted(addedT),before=len(oldT),after=len(oldT|addedT)),expected_U_delta=dict(removed=sorted(removedU),added=sorted(addedU),before=len(oldU),after=len((oldU-removedU)|addedU)),symbol_delta_source_basis=['mem_helpers: new scalar remote_flush_tlb_cpumask entry (no old U for it)','syscall_policy: former U syscall_signalfd_publish_bridge now T, plus new arch_ptrace T','x86_memory_helpers: new x86_clear_range_l4_body T and retained C data callback x86_clear_range_l3_callback U','Private process_helpers: former U vm_range_insert_log_bridge now T and process_vm_range_insert_debug U','Existing kprintf/memset and allocator/lock provider references already present; no guessed extra exports/imports'],target_callback='vm_range_insert_log_bridge',target_selector='process_vm_range_insert_debug',existing_logger='kprintf one T in same full Rust object',source_closure_stop='Any changed canonical preimage requires root reconciliation before execution; preserve this sealed cohort.')
 write(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json',rust)
 # Same accepted complete selected GCC9 TU profile; change only source/output paths.
 oldS=OLD/'source';flags=oldc['selected_C_argv'][1:-4]
 flags=[token.replace(str(oldS),str(S)) for token in flags]
 dst=S/'kernel/process.c';shutil.copy2(B/'candidate/process.c',dst)
 headers={};canonical_headers={}
 for key,row in oldc['canonical_headers'].items():
  src=ROOT/key;now=pin(src);assert now['sha256']==row['sha256'],key
  target=S/key;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
  headers[str(target)]=pin(target);canonical_headers[key]=now
 for name,row in oldc['headers'].items():
  if not str(name).startswith(str(oldS)+'/'):headers[name]=row
 assert len(headers)==73
 abi=P/'actual-process-debug-header-ABI.c';abi.write_text('''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <process_helpers.h>
#include <ihk/debug.h>
extern void vm_range_insert_log_bridge(int,struct process_vm *,struct vm_range *,struct vm_range *);
extern struct ddebug process_vm_range_insert_debug;
_Static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8 && sizeof(int)==4 && (char)-1<0,"supported LP64 signed-char ABI");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8,"actual Ddebug ABI proven by prior1101 fixture");
_Static_assert(__builtin_offsetof(struct ddebug,fmt)==2*sizeof(void *),"descriptor pointer fields");
_Static_assert(__builtin_types_compatible_p(__typeof__(&vm_range_insert_log_bridge),process_vm_range_insert_log_fn_t),"unchanged full callback signature");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),int (*)(const char *,...)),"existing exact variadic provider");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct vm_range *)0)->flag),unsigned long),"keep original UL flag varargs even for %x");
''')
 gcc='/usr/bin/gcc-9';cargv=[gcc,*flags,'-o',str(O/'process.c.o'),'-c',str(dst)]
 commands=[('00-current78-production-Rust-compile',argv),('01-current78-Rust-symbols',['/usr/bin/nm','-g',str(O/'mckernel_rust.o')]),('02-current78-Rust-ELF',['/usr/bin/readelf','-Ws',str(O/'mckernel_rust.o')]),('03-current78-Rust-relocations',['/usr/bin/readelf','-rW',str(O/'mckernel_rust.o')]),('04-actual-debug-header-ABI',[gcc,*flags,'-fsyntax-only',str(abi)]),('05-selected-complete-process-preprocess',[gcc,*flags,'-E',str(dst)]),('06-selected-complete-process-TU',cargv),('07-selected-process-symbols',['/usr/bin/nm','-a','-S',str(O/'process.c.o')]),('08-selected-process-relocations',['/usr/bin/readelf','-rW',str(O/'process.c.o')]),('09-selected-process-ELF',['/usr/bin/readelf','-SWs',str(O/'process.c.o')]),('10-selected-C-verbose-data',['/usr/bin/readelf','-x','__verbose',str(O/'process.c.o')]),('11-process-fullRust-partial-link',['/usr/bin/ld','-r',str(O/'process.c.o'),str(O/'mckernel_rust.o'),'-o',str(O/'process-rust-partial.o')]),('12-process-fullRust-partial-symbols',['/usr/bin/nm','-a','-S',str(O/'process-rust-partial.o')]),('13-process-fullRust-partial-relocations',['/usr/bin/readelf','-rW',str(O/'process-rust-partial.o')])]
 crecipe=dict(scope=SCOPE,status='PREPARED_NOT_GRANTED_NOT_EXECUTED',accepted_prior_complete_C_profile=pin(oldcpath),accepted_prior_whole_join=pin(previous),selected_C_argv=cargv,private_source=pin(dst),canonical_preimage=pin(ROOT/'kernel/process.c'),headers=headers,canonical_headers=canonical_headers,ABI_witness=pin(abi),commands=[dict(name=name,argv=cmd,cwd=str(O),purpose=SCOPE+' '+name+'; ordinary completeGCC9/current78 proof only, exact defaultGCC14/native remainopen.') for name,cmd in commands],tools={tool:pin(Path(tool)) for tool in (gcc,'/usr/bin/nm','/usr/bin/readelf','/usr/bin/ld',argv[0],argv[6])},profile=oldr['profile'],expected_C_symbols=dict(vm_range_insert='one U unchanged, two real add/split caller relocations',vm_range_insert_log_bridge='NO C symbol, neither T nor U; actual consumer now within Rust',process_vm_range_insert_debug='one global OBJECT32B in __verbose, declarative data',vm_range_insert_dump_bridge='existing C T debt retained'),expected_partial=dict(vm_range_insert='one Rust T',vm_range_insert_log_bridge='one Rust T',kprintf='one existing Rust T',process_vm_range_insert_debug='one C OBJECT32B',vm_range_insert_dump_bridge='one existing C T debt'),debug_metadata=dict(file='actual C __FILE__',func='vm_range_insert_log_bridge',fmt='NULL',line=2086,default_flags='DDEBUG_DEFAULT unchanged, supported profile0',layout='actual debug::Ddebug typed ABI and prior1101 packing proof, not guessed offsets'),expected_function_relocations=dict(function='vm_range_insert_log_bridge',existing_logger='kprintf',selector='process_vm_range_insert_debug',format_and_CULong_ABI='prior1101 actualbody retained'),observer_note='C callback NO symbol is source-derived; do not incorrectly require a C U after callback body retirement. Other fulltree/wholeTU U names remain explicit; no two-U oracle.',compiler_difference='Same accepted ordinary GCC9 profile, not exact GCC14 default kernel link.')
 write(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-EXECUTED.json',crecipe)
 accepted_leaf=B/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json';assert pin(accepted_leaf)['sha256']=='bebe72021c410cddfd8c67dfc086c365d51641e074aca04f87f5450405509316'
 ready=dict(scope=SCOPE,status='CURRENT78_COMPLETE_PROCESS_PRODUCTION_SOURCE_READY_NO_GRANT',Rust_recipe=pin(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json'),C_recipe=pin(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-EXECUTED.json'),source_identity=identity,source_count=78,C_headers=73,canonical_refresh_exact=list(current_changes),private_target_override='process_helpers17c927 over canonical3f2c; C08c238 over64af',accepted_prior_actual_leaf=pin(accepted_leaf),expected_T_delta=rust['expected_T_delta'],expected_U_delta=rust['expected_U_delta'],prepared_commands=14,profile=oldr['profile'],reused_actualbody_comparisons=1101,reused_actual_commands=13,compiler_jobs=0,CPU_reservations=0,canonical_or_frozen15_mutations=0,execution_prerequisites=['Independent leaf/source/ABI acceptance and exact root ordinary grant','Fresh shared19GiB/7job/floors/fullgrowth checks and prior CPU owner wholejoin','All current78 and73header bindings still match; otherwise stop and ask root for exact coherent successor','Durable compiler objects before observers; first unexpected result stops, no self retry'],preserved_prior_process_entry_observer_failure_and_correction=True,remaining_C_debt=['Declarative dynamic selector data','vm_range_insert_dump_bridge/dump_tree/optional dtree','Other process.c compute bodies'],whole_area_file_default_image_native='OPEN')
 write(P/'PRODUCTION-CONSUMER-READY.json',ready)
 mirror=ROOT/'docs/verification/evidence/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1';shutil.copytree(P,mirror,dirs_exist_ok=True)
 print(json.dumps(dict(scope=SCOPE,ready=pin(P/'PRODUCTION-CONSUMER-READY.json'),Rust_recipe=ready['Rust_recipe'],C_recipe=ready['C_recipe'],identity=identity,T_delta=rust['expected_T_delta'],U_delta=rust['expected_U_delta'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
