# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,difflib
R=Path('/home/holden/mckernel');P=Path(__file__).resolve().parent;F=P/'fixture';S=P/'source'
def fn(s,mark):
 a=s.index(mark);b=s.index('{',a);i=b+1;n=1
 while n:
  n+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
c=(R/'kernel/process.c').read_text();rs=(R/'kernel/rust/sched_helpers.rs').read_text();w=(R/'kernel/rust/waitq.rs').read_text();hdr=(R/'kernel/include/sched_helpers.h').read_text()
original=fn(c,'void sched_request_migrate(int cpu_id, struct thread *thread)')
request=fn(c,'struct migrate_request {')+';'
off=fn(c,'static const struct sched_migrate_offsets process_sched_migrate_offsets =')+';'
newc=c.replace(original,'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+original+'\n#endif',1)
assert newc.count(request+'\n\n'+off)==1
newc=newc.replace(request+'\n\n'+off,'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+request+'\n\n'+off+'\n#endif',1)
oldlog='static void process_sched_migrate_log_bridge(';assert newc.count(oldlog)==1
newc=newc.replace(oldlog,'PROCESS_SCHED_PUBLIC_BRIDGE void process_sched_migrate_log_bridge(',1)
extra='''    fn process_sched_waitq_init_bridge(waitq_addr: usize);
    fn process_sched_waitq_prepare_bridge(waitq_addr: usize, entry_addr: usize, status: CInt);
    fn process_sched_waitq_finish_bridge(waitq_addr: usize, entry_addr: usize);
    fn process_sched_migrate_log_bridge(thread_addr: usize, tid: CInt, cpu_id: CInt);
'''
newrs=rs.replace('unsafe extern "C" {\n','unsafe extern "C" {\n'+extra,1)
wrapper='''/// Publish a stack-local migration request using the existing scheduler body.
///
/// # Safety
/// The caller preserves the existing scheduler/current-CPU contract and supplies
/// a live thread and CPU. As in the C wrapper, schedule completes the request
/// before returning; waitq_finish then detaches the entry before either stack
/// object expires. The body acquires migq_lock before runq_lock and retains it
/// through target notification. Callbacks must not retain the offset table.
#[no_mangle]
pub unsafe extern "C" fn sched_request_migrate(cpu_id: CInt, thread: *mut Thread) {
    let cpu = unsafe { process_sched_cpu_local_bridge(cpu_id) };
    let mut request = MaybeUninit::<SchedMigrateRequest>::uninit();
    let mut entry = MaybeUninit::<crate::waitq::WaitqEntry>::uninit();
    unsafe {
        crate::waitq::waitq_init_locked_entry(
            entry.as_mut_ptr(), (*get_this_cpu_local_var()).current.cast(),
        );
    }
    let current_cpu_id = unsafe { ihk_mc_get_processor_id() };
    let offsets = SchedMigrateOffsets {
        req_list_offset: offset_of!(SchedMigrateRequest, list),
        req_thread_offset: offset_of!(SchedMigrateRequest, thread),
        req_wq_offset: offset_of!(SchedMigrateRequest, wq),
        thread_cpu_id_offset: offset_of!(Thread, cpu_id),
        thread_tid_offset: offset_of!(Thread, tid),
        cpu_migq_lock_offset: offset_of!(CpuLocalVar, migq_lock),
        cpu_migq_offset: offset_of!(CpuLocalVar, migq),
        cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
        cpu_flags_offset: offset_of!(CpuLocalVar, flags),
        cpu_status_offset: offset_of!(CpuLocalVar, status),
    };
    let _ = unsafe {
        sched_request_migrate_body_result(
            cpu_id, cpu, request.as_mut_ptr() as usize, entry.as_mut_ptr() as usize,
            thread as usize, current_cpu_id, 0x4, CPU_FLAG_NEED_RESCHED,
            CPU_FLAG_NEED_MIGRATE, CPU_STATUS_RUNNING, IHK_GV_IKC, &offsets,
            Some(sched_process_spin_lock_bridge),
            Some(sched_process_spin_unlock_bridge),
            Some(sched_process_noirq_lock_bridge),
            Some(sched_process_noirq_unlock_bridge),
            Some(process_sched_waitq_init_bridge),
            Some(process_sched_waitq_prepare_bridge),
            Some(process_sched_waitq_finish_bridge),
            Some(process_sched_vector_bridge), Some(process_sched_interrupt_bridge),
            Some(process_sched_schedule_bridge), Some(process_sched_migrate_log_bridge),
        )
    };
}

'''
# PS_UNINTERRUPTIBLE is 0x4 in the current production process.h; name it explicitly.
wrapper=wrapper.replace('current_cpu_id, 0x4,','current_cpu_id, PS_UNINTERRUPTIBLE,')
newrs=newrs.replace('const PS_RUNNING: CInt = 0x1;','const PS_RUNNING: CInt = 0x1;\nconst PS_UNINTERRUPTIBLE: CInt = 0x4;',1)
marker='#[no_mangle]\npub unsafe extern "C" fn sched_request_migrate_body_result(';assert newrs.count(marker)==1
newrs=newrs.replace(marker,wrapper+marker,1)
changes={'kernel/process.c':newc,'kernel/rust/sched_helpers.rs':newrs};patch=''
for rel,new in changes.items():
 write(S/rel,new);patch+=''.join(difflib.unified_diff((R/rel).read_text().splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel,n=4))
write(P/'PRIVATE-PRODUCTION.patch',patch);write(P/'ORIGINAL-SELECTED-C.c',original+'\n');write(F/'original.c',original.replace('void sched_request_migrate(', 'void original_sched_request_migrate(',1)+'\n');write(F/'c-request-and-offsets.h',request+'\n'+off+'\n')
write(F/'actual_abi.rs',(R/'kernel/rust/abi.rs').read_text())
# Real existing WaitqEntry plus actual initializer; wake callback is a primitive
# external provider and never invoked by this focused wrapper fixture.
wtypes='\n'.join('#[repr(C)]\n'+fn(w,'pub(crate) struct '+n) for n in ['IhkSpinlock','ListHead','WaitqEntry'])
wq='''use core::ffi::c_void; type CUInt=u32; type CInt=i32;
type WaitqFunc=Option<unsafe extern "C" fn(*mut WaitqEntry,CUInt,CInt,*mut c_void)->CInt>;
'''+wtypes+'\nunsafe extern "C" { fn locked_wake_function(entry:*mut WaitqEntry,mode:CUInt,flags:CInt,key:*mut c_void)->CInt; }\n'+fn(w,'unsafe fn init_list_head(')+'\n'+fn(w,'unsafe fn entry_link(')+'\n#[no_mangle]\n'+fn(w,'pub unsafe extern "C" fn waitq_init_locked_entry(')+'\n'
write(F/'actual_waitq_entry.rs',wq)
base='''#![no_std]
#![allow(dead_code)]
#[path="actual_abi.rs"] mod abi;
#[path="actual_waitq_entry.rs"] mod waitq;
use abi::{AbiListHead,CInt,CULong,CpuLocalVar,Thread,Waitq};
use core::mem::{offset_of,MaybeUninit};
use core::ptr::{read_volatile,write_volatile};
const EINVAL:CInt=22; const PS_UNINTERRUPTIBLE:CInt=0x4;
const CPU_FLAG_NEED_RESCHED:u32=1;const CPU_FLAG_NEED_MIGRATE:u32=2;
const CPU_STATUS_RUNNING:CInt=2;const IHK_GV_IKC:CInt=1;
'''
aliases='\n'.join(line for line in rs.splitlines() if line.startswith('type SchedMigrate') and 'Fn =' in line)+'\n'
extern='''unsafe extern "C" {
 fn get_this_cpu_local_var()->*mut CpuLocalVar;
 fn ihk_mc_get_processor_id()->CInt;
 fn process_sched_cpu_local_bridge(cpu_id:CInt)->usize;
 #[link_name="process_spin_lock_bridge"] fn process_spin_lock_bridge_c(lock_addr:CULong)->CULong;
 #[link_name="process_spin_unlock_bridge"] fn process_spin_unlock_bridge_c(lock_addr:CULong,irqstate:CULong);
 #[link_name="process_sched_noirq_lock_bridge"] fn process_sched_noirq_lock_bridge_c(lock_addr:CULong);
 #[link_name="process_sched_noirq_unlock_bridge"] fn process_sched_noirq_unlock_bridge_c(lock_addr:CULong);
 fn process_sched_vector_bridge(vector_key:CInt)->CInt;
 fn process_sched_interrupt_bridge(cpu:CInt,vector:CInt);
 fn process_sched_schedule_bridge();
'''+extra+fn(rs,'pub unsafe extern "C" fn sched_request_migrate_body_result(').split(' {',1)[0].replace('pub unsafe extern "C" fn ',' fn ',1)+';\n}\n'
parts=['#[repr(C)]\n'+fn(rs,'pub struct SchedMigrateOffsets'),'#[repr(C)]\n'+fn(rs,'struct SchedMigrateRequest')]
for n in ['sched_process_spin_lock_bridge','sched_process_spin_unlock_bridge','sched_process_noirq_lock_bridge','sched_process_noirq_unlock_bridge']:
 parts.append(fn(rs,'unsafe extern "C" fn '+n+'('))
parts += [fn(rs,'unsafe fn list_prev_addr('),fn(rs,'unsafe fn list_add_tail_addr(')]
body=fn(rs,'pub unsafe extern "C" fn sched_request_migrate_body_result(').replace('fn sched_request_migrate_body_result(', 'fn leaf_sched_request_migrate_body_result(',1)
write(F/'actual.rs',base+aliases+extern+'\n'.join(parts)+'\n'+wrapper+'#[no_mangle]\n'+body+'\n')
write(F/'main.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stdio.h>
#include <stdlib.h>
void fixture_fail(unsigned line) { fprintf(stderr,"fixture assertion line=%u\\n",line);exit(1); }
unsigned long leaf_fixture_run(void);
int main(void) { unsigned long n=leaf_fixture_run();if(n!=37500)return 2;printf("PASS pairs=%lu actual_body_pairs=6250; real headers/types; mocked callbacks; no target state instructions\\n",n);return 0; }
''')
bindings=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='SOURCE_ONLY_NOT_COMPILED',changes={rel:dict(before=pin(R/rel),after=pin(S/rel)) for rel in changes},references={rel:pin(R/rel) for rel in ['kernel/rust/abi.rs','kernel/rust/waitq.rs','kernel/rust/process_helpers.rs','kernel/include/process.h','kernel/include/waitq.h','kernel/include/sched_helpers.h']},patch=pin(P/'PRIVATE-PRODUCTION.patch'),selected_C_line=c[:c.index(original)].count('\n')+1,existing_Rust_body_line=rs[:rs.index('pub unsafe extern "C" fn sched_request_migrate_body_result(')].count('\n')+1)
write(P/'SOURCE-BINDINGS.json',json.dumps(bindings,indent=2)+'\n')
