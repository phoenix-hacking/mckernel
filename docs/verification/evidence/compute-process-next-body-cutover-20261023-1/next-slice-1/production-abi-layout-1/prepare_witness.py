# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Real-header/type witness only; exact GCC14 whole-TU/default link remains OPEN.
from pathlib import Path
import hashlib,json,re,shutil
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel');B=P.parent
C9=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-9/default-image-preparation-1/source-materialization-attempt-1/materialized-source')
OLD=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/idle-orchestration-1/actual-body-attempt-3/commands.json')
BUILD=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/output/build')
BASESRC=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/source-materialization-1/materialized-source')
S=P/'source';S.mkdir(exist_ok=False)
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def fun(s,mark):
 a=s.index(mark);b=s.index('{',a);i=b+1;n=1
 while n:
  if s[i]=='{':n+=1
  elif s[i]=='}':n-=1
  i+=1
 return s[a:i]
def block(s,mark):
 x=fun(s,mark);return x+';'
process=R/'kernel/process.c';sched=B/'fullcrate-preparation-1/source/kernel/rust/sched_helpers.rs';abi=B/'fullcrate-preparation-1/source/kernel/rust/abi.rs'
c=process.read_text();rs=sched.read_text();assert pin(abi)['sha256']==pin(C9/'kernel/rust/abi.rs')['sha256']==pin(R/'kernel/rust/abi.rs')['sha256']
shutil.copyfile(process,S/'actual_process_reference.c');shutil.copyfile(abi,S/'actual_abi.rs');shutil.copyfile(sched,S/'actual_sched_reference.rs')
spin=block(c,'static const struct sched_runqueue_offsets process_sched_runqueue_offsets')
timer=block(c,'PROCESS_SCHED_PUBLIC_BRIDGE const struct timer_runtime_offsets process_timer_runtime_offsets')
parse=lambda t:re.findall(r'\.(\w+)\s*=\s*__builtin_offsetof\(struct\s+(\w+),\s*(\w+)\)',t,re.S)
spinfields=parse(spin);timerfields=parse(timer);assert len(spinfields)==26 and len(timerfields)==15
T={'thread':'Thread','cpu_local_var':'CpuLocalVar','process':'Process','sig_common':'SigCommon','timer':'Timer'}
rows=[]
def add(label,ce,re):rows.append(dict(label=label,C=ce,Rust=re))
add('sizeof.pointer','sizeof(void *)','core::mem::size_of::<*mut core::ffi::c_void>()')
add('sizeof.Culong','sizeof(unsigned long)','core::mem::size_of::<CULong>()')
add('sizeof.Cint','sizeof(int)','core::mem::size_of::<CInt>()')
for ct,rt in T.items():
 add('sizeof.'+rt,'sizeof(struct '+ct+')','core::mem::size_of::<'+rt+'>()')
 add('align.'+rt,'_Alignof(struct '+ct+')','core::mem::align_of::<'+rt+'>()')
add('CpuLocalVar.current','__builtin_offsetof(struct cpu_local_var,current)','offset_of!(CpuLocalVar,current)')
for field,ct,member in spinfields:add('spin.'+field,'__builtin_offsetof(struct '+ct+','+member+')','ACTUAL_SPIN.'+field)
for field,ct,member in timerfields:add('timer.'+field,'__builtin_offsetof(struct '+ct+','+member+')','offset_of!('+T[ct]+','+member+')')
for ct,rt,fields in [('sched_runqueue_offsets','SchedRunqueueOffsets',spinfields),('timer_runtime_offsets','TimerRuntimeOffsets',timerfields)]:
 add('descriptor.sizeof.'+rt,'sizeof(struct '+ct+')','core::mem::size_of::<'+rt+'>()');add('descriptor.align.'+rt,'_Alignof(struct '+ct+')','core::mem::align_of::<'+rt+'>()')
 for field,_,_ in fields:add('descriptor.'+rt+'.'+field,'__builtin_offsetof(struct '+ct+','+field+')','offset_of!('+rt+','+field+')')
callbacks=[('process_timer_spin_lock_bridge','TimerSpinLockFn','unsigned long (*)(unsigned long)'),('process_timer_spin_unlock_bridge','TimerSpinUnlockFn','void (*)(unsigned long,unsigned long)'),('process_timer_lapic_enable_bridge','TimerLapicEnableFn','void (*)(unsigned int)'),('process_timer_lapic_disable_bridge','TimerLapicDisableFn','void (*)(void)'),('process_sched_irq_save_bridge','SchedRunqIrqSaveFn','unsigned long (*)(void)'),('process_sched_irq_restore_bridge','SchedRunqIrqRestoreFn','void (*)(unsigned long)'),('process_spin_lock_bridge','SchedMigrateSpinLockFn','unsigned long (*)(unsigned long)'),('process_spin_unlock_bridge','SchedMigrateSpinUnlockFn','void (*)(unsigned long,unsigned long)'),('process_sched_noirq_lock_bridge','SchedMigrateNoirqLockFn','void (*)(unsigned long)'),('process_sched_noirq_unlock_bridge','SchedMigrateNoirqUnlockFn','void (*)(unsigned long)'),('process_sched_schedule_bridge','SchedMigrateVoidFn','void (*)(void)'),('process_sched_zero_free_bridge','SchedMigrateVoidFn','void (*)(void)'),('process_sched_pause_bridge','SchedMigrateVoidFn','void (*)(void)'),('process_sched_has_signal_bridge','SchedRunqHasSignalFn','int (*)(unsigned long)'),('process_sched_runq_log_bridge','SchedRunqLogFn','void (*)(int,unsigned long,unsigned long,int,int)')]
prototypes=[];positions={}
for name,rt,ctype in callbacks:
 # Exact current C signature from first declaration or definition, no mock body.
 pat=r'(?:PROCESS_SCHED_PUBLIC_BRIDGE\s+)?(?:static\s+)?(?:unsigned long|void|int)\s+'+name+r'\s*\([^;{}]*\)'
 m=re.search(pat,c,re.S);assert m,name
 decl=m.group(0).replace('PROCESS_SCHED_PUBLIC_BRIDGE ','').replace('static ','');prototypes.append(decl+';');positions[name]=c[:m.start()].count('\n')+1
 add('callback.size.'+name,'sizeof(__typeof__(&'+name+'))','core::mem::size_of::<Option<'+rt+'>>()')
 add('callback.align.'+name,'_Alignof(__typeof__(&'+name+'))','core::mem::align_of::<Option<'+rt+'>>()')
C='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual current production C headers/config and source declarations/initializers.
 * GCC9 header-layout scope; this file is NOT the exact GCC14 whole process TU. */
#include <process.h>
#include <sched_helpers.h>
#include <cls.h>
#include <cpulocal.h>
#include <ihk/monitor.h>
#include <string.h>
#include <timer.h>
#define PROCESS_SCHED_PUBLIC_BRIDGE
'''+ '\n'.join(prototypes)+'\n'+spin+'\n'+timer+'\n'
for name,rt,ctype in callbacks:C+='_Static_assert(__builtin_types_compatible_p(__typeof__(&'+name+'),'+ctype+'),"'+name+' actual callback ABI");\n'
C+='''_Static_assert(__builtin_types_compatible_p(__typeof__(((struct cpu_local_var*)0)->current),struct thread*),"actual current pointer type");
_Static_assert(__builtin_types_compatible_p(__typeof__(&set_timer),void(*)(int)),"set_timer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&spin_sleep_or_schedule),void(*)(void)),"spin_sleep ABI");
const unsigned long *const M14_C_SPIN = (const unsigned long *)&process_sched_runqueue_offsets;
const unsigned long *const M14_C_TIMER = (const unsigned long *)&process_timer_runtime_offsets;
'''
C+='const unsigned long M14_C_LAYOUT['+str(len(rows))+'] = {\n'+',\n'.join(' '+r['C'] for r in rows)+'\n};\n';(S/'actual_header_layout.c').write_text(C)
RUST='''#![no_std]
#![allow(dead_code)]
use core::mem::offset_of;
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong,Thread,CpuLocalVar,Process,SigCommon,Timer};
'''
for name in ['SchedRunqueueOffsets','TimerRuntimeOffsets']:RUST+='#[repr(C)]\n'+fun(rs,'pub struct '+name)+'\n'
for typename in sorted({r[1] for r in callbacks}):
 a=rs.index('type '+typename+' =');RUST+=rs[a:rs.index(';',a)+1]+'\n'
constructor=fun(rs,'fn sched_runqueue_offsets() -> SchedRunqueueOffsets')
RUST+=constructor.replace('fn sched_runqueue_offsets()', 'const fn actual_spin_offsets()',1)+'\nconst ACTUAL_SPIN:SchedRunqueueOffsets=actual_spin_offsets();\n'
RUST+='#[no_mangle]\npub static M14_RUST_LAYOUT:[usize;'+str(len(rows))+']=[\n'+',\n'.join(' '+r['Rust'] for r in rows)+'\n];\n'
RUST+='#[no_mangle]\npub static M14_RUST_SPIN:[usize;26]=['+','.join('ACTUAL_SPIN.'+f for f,_,_ in spinfields)+'];\n'
RUST+='#[no_mangle]\npub static M14_RUST_TIMER:[usize;15]=['+','.join('offset_of!('+T[t]+','+m+')' for _,t,m in timerfields)+'];\n'
(S/'actual_rust_layout.rs').write_text(RUST)
prior_rows=json.loads(OLD.read_text());oldargv=next(row['argv'] for row in prior_rows if row['label']=='default-idle-consumer-object');argv=oldargv[:];pathdeltas=[]
for i,a in enumerate(argv):
 before=a
 if a.startswith('-I'):
  path=a[2:]
  if path.endswith('/idle-orchestration-1/postimage/kernel/include'):a='-I'+str(C9/'kernel/include')
  elif path.startswith(str(BASESRC)):a='-I'+str(C9/Path(path).relative_to(BASESRC))
 argv[i]=a
 if a!=before:pathdeltas.append(dict(index=i,before=before,after=a))
argv[argv.index('-c')+1]=str(S/'actual_header_layout.c');argv[argv.index('-o')+1]=str(P/'output-1/c-layout.o')
# The accepted old full-process dependency set is a finite superset of these headers.
dep=BUILD/'kernel/CMakeFiles/mckernel.img.dir/process.c.o.d';deps=dep.read_text().split(':',1)[1].replace('\\\n',' ').split();headers={}
for name in sorted(set(deps)):
 if name=='/src/kernel/process.c':continue
 path=C9/Path(name).relative_to('/src') if name.startswith('/src/') else BUILD/Path(name).relative_to('/work/output/build') if name.startswith('/work/output/build/') else Path(name)
 assert path.is_file(),path;headers[str(path)]=pin(path)
assert str(BUILD/'config.h') in headers
fullrecipe=json.loads((B/'EXACT-PRODUCTION-RUST-RECIPE.GRANTED.json').read_text());rargv=fullrecipe['argv'][:]
rargv[rargv.index('--crate-name')+1]='m14_actual_layout'
rargv[-2]='--emit=obj='+str(P/'output-1/rust-layout.o');rargv[-1]=str(S/'actual_rust_layout.rs')
recipe=dict(scope=fullrecipe['scope'],status='GRANTED_REAL_HEADER_GCC9_LAYOUT_WITNESS_ONLY_NOT_EXECUTED',compiler_scope='C: accepted ordinary GCC9 realheaderfixture profile, NOT exact productionGCC14wholeTU. Rust: exact productionpinnednightly1.95 flags/4cfg sharedtypes, standalone datatype witness, NOT fullcrate.',C_argv=argv,Rust_argv=rargv,data_observer='ELF64 named OBJECT metadata arrays only; no linked/target/kernel execution',accepted_GCC9_command=pin(OLD),accepted_GCC9_label='default-idle-consumer-object',explicit_header_path_deltas=pathdeltas,C_compiler_expected_sha256='6cb2d84ccd9fd3485d4e47ba032e626be65692601c38fad46866a6b565f3100f',Rust_compiler_expected_sha256=fullrecipe['compiler_sha256'],profile='CPU6onejob AS2GiB CPU60 wall120+6 FSIZE32MiB NOFILE256 core0 CGU1stack2MiB; accepted990+handlers; MemAvailable19GiB andHOST/scratchfloors+fullgap',source_files={str(f.relative_to(P)):pin(f) for f in S.iterdir() if f.is_file()},actual_header_config_closure=headers,accepted_fullprocess_dependency_descriptor=pin(dep),source_positions=dict(current_process=pin(process),actual_Rust_abi=pin(abi),actual_Rust_sched=pin(sched),spin_C_initializer_line=c[:c.index('static const struct sched_runqueue_offsets process_sched_runqueue_offsets')].count('\n')+1,timer_C_initializer_line=c[:c.index('PROCESS_SCHED_PUBLIC_BRIDGE const struct timer_runtime_offsets process_timer_runtime_offsets')].count('\n')+1,spin_Rust_constructor_line=rs[:rs.index('fn sched_runqueue_offsets()')].count('\n')+1,callback_C_signature_lines=positions),witness_rows=rows,actual_offsets=dict(spin=26,timer=15),no_models=True,Rust_constructor_witness_change='Only const qualification/name for compile-time data emission; complete existing constructor body unchanged and sourcebound. Actualabi.rs copied whole; both descriptor types/typealiases exact extracts.',exact_GCC14_whole_C_TU_defaultlink_native='OPEN')
(P/'EXACT-LAYOUT-WITNESS-RECIPE.GRANTED.json').write_text(json.dumps(recipe,indent=2)+'\n');print(json.dumps(dict(recipe=pin(P/'EXACT-LAYOUT-WITNESS-RECIPE.GRANTED.json'),actual_header_files=len(headers),rows=len(rows))))
