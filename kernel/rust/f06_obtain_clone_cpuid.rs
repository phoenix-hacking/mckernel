// Functional OS only; no security testing. Qualified banked body, genuine origin bindings only.
use crate::abi::{CInt,CpuSet,SizeT};
use core::mem::size_of;
use core::ptr::{addr_of,addr_of_mut,read_volatile,write_volatile};
use core::sync::atomic::{AtomicU64,Ordering};
use super::kprintf;
include!(env!("MCKERNEL_F06_CLONE_CPUID_METADATA_RS"));
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: full clone-CPU reservation selection. Existing locking, affinity and
// CPU-local providers are reused without adding references or changing policy.
unsafe extern "C" {
    #[link_name = "runq_reservation_lock"]
    static mut F06_CLONE_RUNQ_RESERVATION_LOCK: crate::abi::IhkSpinlock;
}
const F06_CLONE_CPU_STATUS_RESERVED: CInt = 3; // actual cls.h CPU_STATUS_RESERVED
#[used]
#[link_section = "__verbose"]
static mut F06_CLONE_CPU_SAMPLE_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(env!("MCKERNEL_F06_RT_SIGRETURN_ORIGIN"), "\0").as_ptr().cast(), func: b"obtain_clone_cpuid\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: F06_CLONE_CPU_SAMPLE_LINE_FLAGS,
};
#[used]
#[link_section = "__verbose"]
static mut F06_CLONE_CPU_CHOICE_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(env!("MCKERNEL_F06_RT_SIGRETURN_ORIGIN"), "\0").as_ptr().cast(), func: b"obtain_clone_cpuid\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: F06_CLONE_CPU_CHOICE_LINE_FLAGS,
};

/// Reserve one selected CPU under the exact existing global/runqueue lock order.
/// CPU-local objects and cpu_set are live under the original boot/clone contract.
/// The legacy use_last policy can return -1 without a tie, and can retain an old
/// tie after a new minimum; both behaviors are deliberately preserved here.
#[no_mangle]
pub unsafe extern "C" fn obtain_clone_cpuid(cpu_set: *mut CpuSet, use_last: CInt) -> CInt {
    unsafe {
        let mut min_queue_len: CInt = -1;
        let mut min_cpu: CInt = -1;
        let mut uti_cpu: CInt = -1;
        let mut cpu: CInt = 0;
        let reservation = addr_of_mut!(F06_CLONE_RUNQ_RESERVATION_LOCK).cast();
        let irqstate = crate::spinlock_helpers::__ihk_mc_spinlock_lock(reservation);
        while cpu < read_volatile(addr_of!(crate::ap::num_processors)) {
            if crate::affinity::CPU_ISSET(cpu as SizeT, cpu_set) != 0 {
                let v = crate::cls::get_cpu_local_var(cpu);
                let lock = addr_of_mut!((*v).runq_lock).cast();
                crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(lock);
                if read_volatile(addr_of!(F06_CLONE_CPU_SAMPLE_DEBUG.line_flags)) >> 24 != 0 {
                    // Original %d formatting observes low CInt bits of SizeT
                    // arguments. Preserve the actual unsigned-width varargs.
                    kprintf(b"%s: cpu=%d,runq_len=%d,runq_reserved=%d\n\0".as_ptr().cast(),
                        b"obtain_clone_cpuid\0".as_ptr().cast::<i8>(), cpu,
                        read_volatile(addr_of!((*v).runq_len)), read_volatile(addr_of!((*v).runq_reserved)));
                }
                // C adds two unsigned size_t values, then converts the selected
                // sum to int. Subsequent int comparisons convert back to size_t.
                // Keep wrapping arithmetic and truncation, including -1 sentinel.
                if min_queue_len == -1
                    || read_volatile(addr_of!((*v).runq_len))
                        .wrapping_add(read_volatile(addr_of!((*v).runq_reserved))) < min_queue_len as SizeT
                {
                    min_queue_len = read_volatile(addr_of!((*v).runq_len))
                        .wrapping_add(read_volatile(addr_of!((*v).runq_reserved))) as CInt;
                    min_cpu = cpu;
                }
                if min_cpu != cpu
                    && read_volatile(addr_of!((*v).runq_len))
                        .wrapping_add(read_volatile(addr_of!((*v).runq_reserved))) == min_queue_len as SizeT
                {
                    uti_cpu = cpu;
                }
                if read_volatile(addr_of!(F06_CLONE_CPU_CHOICE_DEBUG.line_flags)) >> 24 != 0 {
                    kprintf(b"%s: cpu=%d,runq_len=%d,runq_reserved=%d,min_cpu=%d,uti_cpu=%d\n\0".as_ptr().cast(),
                        b"obtain_clone_cpuid\0".as_ptr().cast::<i8>(), cpu,
                        read_volatile(addr_of!((*v).runq_len)), read_volatile(addr_of!((*v).runq_reserved)), min_cpu, uti_cpu);
                }
                crate::spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(lock);
            }
            cpu = cpu.wrapping_add(1);
        }
        if use_last != 0 { min_cpu = uti_cpu; }
        if min_cpu != -1 {
            if read_volatile(addr_of!((*crate::cls::get_cpu_local_var(min_cpu)).status)) != F06_CLONE_CPU_STATUS_RESERVED {
                write_volatile(addr_of_mut!((*crate::cls::get_cpu_local_var(min_cpu)).status), F06_CLONE_CPU_STATUS_RESERVED);
            }
            let slot = addr_of_mut!((*crate::cls::get_cpu_local_var(min_cpu)).runq_reserved);
            // Original __sync_fetch_and_add(size_t*,1) is a full-barrier 64-bit
            // atomic increment on supported x86 LP64. No extra owner is created.
            const _: () = assert!(size_of::<SizeT>() == size_of::<AtomicU64>());
            (&*slot.cast::<AtomicU64>()).fetch_add(1, Ordering::SeqCst);
        }
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock(reservation, irqstate);
        min_cpu
    }
}
