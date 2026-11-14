# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,ast
P=Path(__file__).resolve().parent;F=P/'fixture';O=P/'leaf-output-1';R=Path('/home/holden/mckernel')
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def fn(s,mark):
 a=s.index(mark);b=s.index('{',a);i=b+1;n=1
 while n:n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
c=(P/'source/kernel/process.c').read_text();old=(R/'kernel/process.c').read_text()
# The exact private default selection and fallback are extracted, not copied
# into a second implementation. This is a focused selected-fragment consumer.
frag='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Extracted selection only; NOT full process TU. Logging is a fixture primitive. */
#include <process.h>
#include <sched_helpers.h>
#include <cls.h>
#include <cpulocal.h>
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
#define PROCESS_SCHED_PUBLIC_BRIDGE
#else
#define PROCESS_SCHED_PUBLIC_BRIDGE static
#endif
#define dkprintf(...) ((void)0)
unsigned long process_spin_lock_bridge(unsigned long);
void process_spin_unlock_bridge(unsigned long,unsigned long);
void process_sched_noirq_lock_bridge(unsigned long);
void process_sched_noirq_unlock_bridge(unsigned long);
void process_sched_waitq_init_bridge(unsigned long);
void process_sched_waitq_prepare_bridge(unsigned long,unsigned long,int);
void process_sched_waitq_finish_bridge(unsigned long,unsigned long);
int process_sched_vector_bridge(int);
void process_sched_interrupt_bridge(int,int);
void process_sched_schedule_bridge(void);
'''
req=fn(c,'struct migrate_request {')+';';offs=fn(c,'static const struct sched_migrate_offsets process_sched_migrate_offsets =')+';'
frag+='#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+req+'\n'+offs+'\n#endif\n'+fn(c,'PROCESS_SCHED_PUBLIC_BRIDGE void process_sched_migrate_log_bridge(')+'\n#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+fn(c,'void sched_request_migrate(')+'\n#endif\n'
(F/'selected-fragment.c').write_text(frag)
recipe0=Path('/home/holden/mckernel-work/host-preparation/compute-process-next-body-cutover-20261023-1/next-slice-1/production-abi-layout-1/EXACT-LAYOUT-WITNESS-RECIPE.GRANTED.json');r0=json.loads(recipe0.read_text());cflags=r0['C_argv'][1:r0['C_argv'].index('-c')];gcc='/usr/bin/gcc-9';rust='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
rflags=['--edition=2021','--crate-type=lib','--emit=obj','-C','panic=abort','-C','opt-level=2','-C','codegen-units=1','-C','relocation-model=static']
for cfg in ['native_linux_irq_work_v6_12','enable_profile','enable_perf','enable_rusage']:rflags+=['--cfg',cfg]
cmds=[dict(name='00-actual-Rust',argv=[rust,*rflags,str(F/'actual.rs'),'-o',str(O/'actual.o')]),dict(name='01-real-header-original-C-fixture',argv=[gcc,*cflags,'-Werror','-c',str(F/'fixture.c'),'-o',str(O/'fixture.o')]),dict(name='02-host-fixture-link',argv=[gcc,'-std=gnu11','-Wall','-Wextra','-Werror','-O2','-fno-pie','-no-pie',str(F/'main.c'),str(O/'fixture.o'),str(O/'actual.o'),'-o',str(O/'equivalence')]),dict(name='03-functional-mocked-callback-fixture',argv=[str(O/'equivalence')]),dict(name='04-selected-PUBLIC-C-fragment',argv=[gcc,*cflags,'-Werror','-c',str(F/'selected-fragment.c'),'-o',str(O/'public.o')]),dict(name='05-fallback-C-fragment',argv=[gcc,*[x for x in cflags if x!='-DMCKERNEL_RUST_PROCESS_HELPERS'],'-Werror','-c',str(F/'selected-fragment.c'),'-o',str(O/'fallback.o')])]
for name in ['actual','public','fallback']:
 for tool,args in [('nm',['-g']),('readelf',['--wide','--relocs'])]:cmds.append(dict(name=name+'-'+tool,argv=['/usr/bin/'+tool,*args,str(O/(name+'.o'))]))
source={str(x.relative_to(P)):pin(x) for x in [*F.iterdir(),P/'PRIVATE-PRODUCTION.patch',P/'SOURCE-BINDINGS.json',P/'source/kernel/process.c',P/'source/kernel/rust/sched_helpers.rs'] if x.is_file()}
# Validate all retained header/config inputs now; no compiler is run.
for row in r0['actual_header_config_closure'].values():assert pin(Path(row['path']))==row
for x in cmds:
 for arg in x['argv']:assert isinstance(arg,str)
b=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='NOT_EXECUTED_AWAIT_ROOT_CPU0_GRANT',profile=dict(CPU=0,jobs=1,AS_bytes=2<<30,CPU_seconds=60,wall_seconds=120,retirement_seconds=6,FSIZE_bytes=32<<20,NOFILE=256,core=0,RUST_MIN_STACK=2097152),profile_authority='Existing Rust1.92/GCC9 leaf plus accepted GCC9 idle/current-header fixture flags; CPU0 requested only, no grant yet',header_profile=pin(recipe0),tools={x:pin(Path(x)) for x in [rust,gcc,'/usr/bin/nm','/usr/bin/readelf']},source_files=source,actual_header_config_closure=r0['actual_header_config_closure'],commands=cmds,tests=dict(original_C_actual_Rust_pairs=37500,actual_existing_body_pairs=6250,full_callback_pairs=3125,negative_null_thread_pairs=3125,ignored_return_pairs=31250,layout_words=18,real_types='C actual selected headers/config; entire actual Rust abi.rs plus exact existing waitq entry/type/initializer extracts; no model structs',callback_invariants=['target CPU getter before current getter before processor ID','locked entry initialized before body call','migq lock before runq lock; target notified before migq unlock','schedule invoked after unlock; removes publication before return','finish detaches wait entry before stack objects expire','same/cross CPU branch; CPU flags preserved; ignored body return']),expectations=dict(actual=['T sched_request_migrate','T leaf_sched_request_migrate_body_result','U process_sched_migrate_log_bridge'],PUBLIC_C=['no T sched_request_migrate','T process_sched_migrate_log_bridge','no process_sched_migrate_offsets'],fallback_C=['T sched_request_migrate','U sched_request_migrate_body_result']),default_consumer=dict(current_C_declaration='kernel/include/process.h:892',actual_caller='kernel/syscall.c:24895 sched_request_migrate_bridge',actual_Rust_caller='kernel/rust/syscall_policy.rs:12141 passes existing sched_request_migrate_bridge to sched_setaffinity_body_result',next_production='same exact78input nightly1.95 fullcrate profile with new private two postimages, separately granted; then real GCC14 whole process TU/defaultlink and native migration sequence',canonical_changed=False),qualifiers='Leaf/selected fragment only; whole process C TU/defaultkernel/defaultlink/native OPEN; migration completion is a mocked semantic boundary, not production scheduler proof')
(P/'EXACT-NEXT-LEAF-RECIPE.NOT-EXECUTED.json').write_text(json.dumps(b,indent=2)+'\n')
(P/'READINESS.md').write_text('''Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private next-slice-2 replaces the remaining selected sched_request_migrate wrapper with a Rust export calling the existing sched_request_migrate_body_result. Exact C fallback remains. Existing typed SchedMigrateRequest and waitq::WaitqEntry use MaybeUninit stack storage; no new repr(C) layout. The existing migrate-log C callback gains existing PUBLIC linkage only.

Actual default consumer: syscall_policy.rs sys_sched_setaffinity -> existing sched_request_migrate_bridge in syscall.c -> process.h sched_request_migrate -> proposed Rust export. The request is removed by the existing migration-completion protocol before schedule returns; waitq_finish detaches entry before stack lifetime ends, identical to the C wrapper assumption. Body behavior and lock/IRQ operations are unchanged. Independent source/ABI review and production execution remain required.

Focused fixture uses original C wrapper bytes, actual private Rust wrapper, actual existing Rust migration body and exact existing wait-entry initializer. Actual header/config C types are paired with actual whole abi.rs and existing waitq.rs entry types. Primitive lock/interrupt/schedule/waitq callbacks are explicitly mocked; the schedule fixture consumes the publication before returning. No target IRQ/XSAVE/host-state instructions, kernel, guest, root or Docker execution.

37500 original-C/actual-Rust pairs are proposed:3125 normal existing-body callback sequences,3125 null-thread error pairs,31250 ignored-return boundary pairs. Eighteen real layout words cover10offsets/request size+alignment/6wait-entry words. Selected PUBLIC and fallback fragments are compiled separately with real headers. Whole process TU/defaultlink/native remain OPEN. Compiler has not run. Canonical/candidate9 inputs are unchanged. Leaf profile requests CPU0 onejob2GiBAS/60CPU/120wall+6/32MiBFSIZE/NOFILE256/core0, Rust1.92/GCC9/CGU1/2MiBstack; exact commands and hashes are in EXACT-NEXT-LEAF-RECIPE.NOT-EXECUTED.json.
''')
print(json.dumps(dict(recipe=pin(P/'EXACT-NEXT-LEAF-RECIPE.NOT-EXECUTED.json'),patch=pin(P/'PRIVATE-PRODUCTION.patch'),source_bindings=pin(P/'SOURCE-BINDINGS.json'),commands=len(cmds))))
