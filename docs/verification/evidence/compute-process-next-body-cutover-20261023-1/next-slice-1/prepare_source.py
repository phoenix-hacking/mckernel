# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,difflib
R=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;S=P/'source';F=P/'fixture';F.mkdir(exist_ok=True)
def function(s,mark):
 a=s.index(mark);b=s.index('{',a);i=b+1;n=1
 while n:
  if s[i]=='{':n+=1
  elif s[i]=='}':n-=1
  i+=1
 return s[a:i]
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
c=(R/'kernel/process.c').read_text();rs=(R/'kernel/rust/sched_helpers.rs').read_text();h=(R/'kernel/rust/tests/run_equivalence.sh').read_text();hdr=(R/'kernel/include/sched_helpers.h').read_text()
whole=function(c,'void spin_sleep_or_schedule(void)');assert whole.count('#ifdef MCKERNEL_RUST_PROCESS_HELPERS')==1
prefix,branches=whole.split('#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n',1);selected,fallback=branches.split('#else\n',1);assert fallback.endswith('#endif\n}')
fallback=fallback[:-len('#endif\n}')];original=prefix+selected+'}';reference=prefix+fallback+'}'
write(P/'ORIGINAL-SELECTED-C.c',original+'\n');write(P/'ORIGINAL-FALLBACK-C.c',reference+'\n')
newc=c.replace(whole,'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+reference+'\n#endif',1)
# Existing shared ABI constructor provides exactly the same immutable offsets;
# no additional C data/provider body is introduced.
extra='''    static mut idle_halt: CInt;
    fn process_sched_irq_restore_bridge(irqstate: CULong);
    fn process_sched_zero_free_bridge();
    fn process_sched_pause_bridge();
    fn process_sched_has_signal_bridge(thread_addr: usize) -> CInt;
'''
newrs=rs.replace('unsafe extern "C" {\n','unsafe extern "C" {\n'+extra,1)
wrapper='''/// Current-CPU spin-sleep boundary; preserve the existing timer/scheduler body.
///
/// # Safety
/// A wait/futex queue is already installed and the current thread's spin_sleep
/// marker is set before testing its wait condition. The caller preserves the
/// original current-CPU/IRQ lifetime contract. The existing shared ABI supplies
/// current and the stack-local immutable offset table; the body does not retain
/// either the table or callback pointers. No lock or pointer ownership transfers.
#[no_mangle]
pub unsafe extern "C" fn spin_sleep_or_schedule() {
    let thread = unsafe { (*get_this_cpu_local_var()).current };
    let cpu = unsafe { get_this_cpu_local_var() };
    // The live LWK ihk/ikc/include/ikc/ihk.h maps ihk_ikc_get_processor_id
    // directly to ihk_mc_get_processor_id.
    let current_cpu_id = unsafe { ihk_mc_get_processor_id() };
    let halt = unsafe { core::ptr::read(core::ptr::addr_of!(idle_halt)) };
    let offsets = sched_runqueue_offsets();
    let _ = unsafe {
        sched_spin_sleep_or_schedule_body_result(
            thread as usize, cpu as usize, current_cpu_id, halt,
            CPU_FLAG_NEED_RESCHED, &offsets,
            Some(process_sched_irq_save_bridge),
            Some(process_sched_irq_restore_bridge),
            Some(sched_process_spin_lock_bridge),
            Some(sched_process_spin_unlock_bridge),
            Some(sched_process_noirq_lock_bridge),
            Some(sched_process_noirq_unlock_bridge),
            Some(process_sched_schedule_bridge),
            Some(process_sched_zero_free_bridge),
            Some(process_sched_pause_bridge),
            Some(process_sched_has_signal_bridge),
            Some(process_sched_runq_log_bridge),
        )
    };
}

'''
a='#[no_mangle]\npub unsafe extern "C" fn sched_spin_sleep_or_schedule_body_result(';assert newrs.count(a)==1;newrs=newrs.replace(a,wrapper+a,1)
oldstub='__attribute__((weak)) void spin_sleep_or_schedule(void) {}';assert h.count(oldstub)==1
newh=h.replace(oldstub,'/* spin_sleep_or_schedule is supplied by the actual Rust scheduler object. */',1)
oldU="grep -Eq 'U spin_sleep_or_schedule' \"${tmpdir}/out/rust.undefined\"";assert newh.count(oldU)==1
newh=newh.replace(oldU,"grep -Eq ' T spin_sleep_or_schedule$' \"${tmpdir}/out/rust.global\"\n! grep -Eq 'U spin_sleep_or_schedule$' \"${tmpdir}/out/rust.undefined\"",1);assert newh.count('-eq 597')==1;newh=newh.replace('-eq 597','-eq 596',1)
changes={'kernel/process.c':newc,'kernel/rust/sched_helpers.rs':newrs,'kernel/rust/tests/run_equivalence.sh':newh};patch=''
for rel,new in changes.items():
 write(S/rel,new);patch+=''.join(difflib.unified_diff((R/rel).read_text().splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel,n=4))
write(P/'PRIVATE-PRODUCTION.patch',patch)
# Fixtures model only host state layout. The actual existing Rust offset builder,
# adapters, pending-signal helper and timer/scheduler body are extracted unchanged.
rstruct='#[repr(C)]\n'+function(rs,'pub struct SchedRunqueueOffsets')+'\n';cstruct=function(hdr,'struct sched_runqueue_offsets')+';\n'
write(F/'runqueue-offsets.h',cstruct);write(F/'original.c',original.replace('void spin_sleep_or_schedule(', 'void original_spin_sleep_or_schedule(',1)+'\n')
alias='''#![no_std]
use core::ptr::{read_volatile,write_volatile};
use core::mem::offset_of;
type CInt=i32; type CULong=u64;
#[repr(C)] pub struct List { pub next:*mut List, pub prev:*mut List }
#[repr(C)] pub struct Thread {
 pub cpu_id:i32,pub tid:i32,pub status:i32,pub spin_sleep_lock:u64,pub spin_sleep:i32,
 pub sched_list:List,pub sigpending:List,pub sigcommon:*mut SigCommon,pub proc:*mut Process,pub mod_clone:i32,
}
#[repr(C)] pub struct SigCommon { pub sigpending:List }
#[repr(C)] pub struct Process { pub pid:i32,pub status:i32,pub update_lock:u64,pub clone_count:i32 }
#[repr(C)] pub struct CpuLocalVar {
 pub runq_lock:u64,pub runq_irqstate:u64,pub current:*mut Thread,pub prevpid:i32,pub runq:List,
 pub runq_len:usize,pub runq_reserved:i32,pub flags:u32,pub status:i32,pub in_interrupt:i32,pub nr_ctx_switches:u64,
}
'''
for key in ['type SchedMigrateSpinLockFn =','type SchedMigrateSpinUnlockFn =','type SchedMigrateNoirqLockFn =','type SchedMigrateNoirqUnlockFn =','type SchedMigrateVoidFn =','type SchedRunqLogFn =','type SchedRunqIrqSaveFn =','type SchedRunqIrqRestoreFn =','type SchedRunqHasSignalFn =','const EINVAL:','const CPU_FLAG_NEED_RESCHED:','const SCHED_RUNQ_LOG_IDLE_HALT:','const SCHED_RUNQ_LOG_LOST_WAKEUP:','const SCHED_RUNQ_LOG_SPIN_WOKEN:','const SCHED_RUNQ_LOG_SLEEP_WOKEN:']:
 i=rs.index(key);alias+=rs[i:rs.index(';',i)+1]+'\n'
extern='''unsafe extern "C" {
 fn get_this_cpu_local_var()->*mut CpuLocalVar;
 fn ihk_mc_get_processor_id()->CInt;
 fn process_sched_irq_save_bridge()->CULong;
 fn process_sched_schedule_bridge();
 fn process_sched_runq_log_bridge(event:CInt,arg0:usize,arg1:usize,arg2:CInt,arg3:CInt);
 #[link_name="process_spin_lock_bridge"] fn process_spin_lock_bridge_c(p:CULong)->CULong;
 #[link_name="process_spin_unlock_bridge"] fn process_spin_unlock_bridge_c(p:CULong,s:CULong);
 #[link_name="process_sched_noirq_lock_bridge"] fn process_sched_noirq_lock_bridge_c(p:CULong);
 #[link_name="process_sched_noirq_unlock_bridge"] fn process_sched_noirq_unlock_bridge_c(p:CULong);
'''+extra+''' fn sched_spin_sleep_or_schedule_body_result(thread:usize,cpu:usize,id:CInt,halt:CInt,need:u32,
 offsets:*const SchedRunqueueOffsets,irq:Option<SchedRunqIrqSaveFn>,restore:Option<SchedRunqIrqRestoreFn>,
 lock:Option<SchedMigrateSpinLockFn>,unlock:Option<SchedMigrateSpinUnlockFn>,nl:Option<SchedMigrateNoirqLockFn>,nu:Option<SchedMigrateNoirqUnlockFn>,
 schedule:Option<SchedMigrateVoidFn>,zero:Option<SchedMigrateVoidFn>,pause:Option<SchedMigrateVoidFn>,signal:Option<SchedRunqHasSignalFn>,log:Option<SchedRunqLogFn>)->CInt;
}\n'''
leaf=alias+rstruct+extern+wrapper
for name,mark in [('sched_runqueue_offsets','fn '),('sched_process_spin_lock_bridge','unsafe extern "C" fn '),('sched_process_spin_unlock_bridge','unsafe extern "C" fn '),('sched_process_noirq_lock_bridge','unsafe extern "C" fn '),('sched_process_noirq_unlock_bridge','unsafe extern "C" fn '),('list_next','unsafe fn '),('list_empty_addr','unsafe fn '),('sched_thread_has_pending_signal','unsafe fn ')]:leaf+=function(rs,mark+name)+'\n'
leaf+='#[no_mangle]\n'+function(rs,'pub unsafe extern "C" fn sched_spin_sleep_or_schedule_body_result').replace('fn sched_spin_sleep_or_schedule_body_result(', 'fn leaf_spin_sleep_or_schedule_body_result(',1)+'\n'
futex=(R/'kernel/rust/futex.rs').read_text()
leaf+='#[no_mangle]\n'+function(futex,'unsafe extern \"C\" fn futex_wait_schedule_direct_bridge')+'\n'
write(F/'actual.rs',leaf)
write(F/'abi.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <sched_helpers.h>
void spin_sleep_or_schedule(void); /* exact process.h:886 declaration */
_Static_assert(sizeof(unsigned long)==8 && sizeof(int)==4,"LP64 callback ABI");
_Static_assert(sizeof(struct sched_runqueue_offsets)==26*8,"existing26offsets");
_Static_assert(__builtin_types_compatible_p(__typeof__(&spin_sleep_or_schedule),void (*)(void)),"public ABI");
''')
bind=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_SOURCE_PREPARED',source_inputs={rel:pin(R/rel) for rel in changes},outputs={rel:pin(S/rel) for rel in changes},patch=pin(P/'PRIVATE-PRODUCTION.patch'),original_selected_C=pin(P/'ORIGINAL-SELECTED-C.c'),original_fallback_C=pin(P/'ORIGINAL-FALLBACK-C.c'),header_inputs={rel:pin(R/rel) for rel in ['kernel/rust/abi.rs','kernel/include/sched_helpers.h','kernel/include/process.h','ihk/ikc/include/ikc/ihk.h','kernel/rust/futex.rs']},implementation='Reuse existing Rust sched_runqueue_offsets/lockadapters/body; no new C/data/provider/layout. Exact C fallback preserved. LWK ihk_ikc CPUid macro resolves to existing ihk_mc CPUid.',callback_identity='Existing Rust lock adapters preserve their established usize/CULong ABI and delegate to the same exported providers. Cstatic descriptor vs Ruststack descriptor identity differs; all26offsetvalues match, synchronous body retains no pointers.',C_argument_order='Cargument evaluation order unspecified. Valid current-CPU getters remain non-mutating; two getters and one CPUid call preserved. Fixture compares calls/count/values and body callback order, not an invented Cargument evaluation order.',whole_C_TU_default_link_native='OPEN')
write(P/'SOURCE-BINDINGS.json',json.dumps(bind,indent=2)+'\n');print(json.dumps(dict(patch=bind['patch'],source=pin(P/'SOURCE-BINDINGS.json'))))
