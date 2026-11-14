// SPDX-License-Identifier: GPL-2.0-only
//! Disposable Linux module checking the actual guest-produced irq_work objects.
//! Boot inputs, guest CPU/interrupt state and transport are explicitly mocked.
//! Linux owns actual IRQ dispatch and BUSY release through irq_work_queue.
//! The remote selection instead publishes into Linux's real raised queue and
//! sends its actual APIC interrupt to a different CPU.
#![allow(dead_code)]
// Imported McKernel code follows its own crate's lint policy. This fixture
// compiles those exact bodies without claiming Linux unsafe-review coverage.
#![allow(unsafe_op_in_unsafe_fn, missing_docs, unreachable_pub)]

use core::ffi::c_void;
use core::ptr::null_mut;
use core::sync::atomic::{AtomicBool, AtomicI32, AtomicPtr, AtomicU32, AtomicU64, Ordering};
use kernel::prelude::*;

#[path = "../../../kernel/rust/llist.rs"]
mod llist;
#[path = "../../../kernel/rust/smp_ikc.rs"]
mod smp_ikc;

mod abi {
    pub type CInt = i32;
    pub type CULong = u64;
}
mod spinlock_helpers {
    #[repr(C)]
    pub struct IhkSpinlock(core::sync::atomic::AtomicU32);
}
mod x86_local {
    pub unsafe fn ihk_mc_get_processor_id() -> i32 {
        super::CPU.load(core::sync::atomic::Ordering::Relaxed)
    }
}

module! {
    type: IrqWorkVerification,
    name: "mckernel_irq_work_verify",
    license: "GPL v2",
}

#[repr(C, align(64))]
struct Storage([u8; 128]);
#[repr(C, align(8))]
struct BootPrefix([u8; 4304]);
static mut STORAGE: Storage = Storage([0xa5; 128]);
static mut PREFIX: BootPrefix = BootPrefix([0; 4304]);
static QUEUE: AtomicPtr<llist::LListNode> = AtomicPtr::new(null_mut());
static ALLOCATIONS: AtomicU32 = AtomicU32::new(0);
static ALLOCATE_FAILS: AtomicBool = AtomicBool::new(true);
static CALLBACKS: AtomicU32 = AtomicU32::new(0);
static CPU: AtomicI32 = AtomicI32::new(0);
static MOCK_IRQ_FLAGS: AtomicU64 = AtomicU64::new(0x202);
static SAVES: AtomicU32 = AtomicU32::new(0);
static RESTORES: AtomicU32 = AtomicU32::new(0);
#[cfg(native_linux_irq_work_remote_queue)]
static TARGET_CPU: AtomicI32 = AtomicI32::new(-1);
#[cfg(native_linux_irq_work_remote_queue)]
static REMOTE_CALLBACKS: [AtomicU32; 4] = [const { AtomicU32::new(0) }; 4];
#[cfg(native_linux_irq_work_remote_queue)]
static mut TARGET_MASK: kernel::bindings::cpumask =
    // SAFETY: cpumask contains only an unsigned-long array.
    unsafe { core::mem::MaybeUninit::zeroed().assume_init() };

#[no_mangle]
static mut boot_param: *mut c_void = null_mut();
#[no_mangle]
static mut num_processors: i32 = 2;

// Exact Linux 6.12 signature, separately checked by the header witness. The
// pointed object is the production guest's 64-byte slot with a 32-byte header.
unsafe extern "C" {
    fn irq_work_queue(work: *mut c_void) -> bool;
}

#[cfg(native_linux_irq_work_remote_queue)]
unsafe extern "C" {
    // The per-CPU address is formed only under the CPU read guard below.
    static mut raised_list: c_void;
    fn per_cpu_ptr_to_phys(address: *mut c_void) -> u64;
    fn irq_work_sync(work: *mut c_void);
    // This exported static-call trampoline is the entry used by Linux's
    // __apic_send_IPI_mask. The exact C witness checks the function signature.
    #[link_name = "__SCT__apic_call_send_IPI_mask"]
    fn send_ipi_mask(mask: *const c_void, vector: i32);
}

#[cfg(native_linux_irq_work_remote_queue)]
unsafe fn current_linux_cpu() -> u32 {
    // get_current is valid in task and hard-IRQ context. Linux's task_cpu()
    // reads this same field; the callback cannot migrate during the read.
    let task = kernel::bindings::get_current();
    core::ptr::read_volatile(&raw const (*task).thread_info.cpu)
}

#[cfg(native_linux_irq_work_remote_queue)]
unsafe fn linux_queue(cpu: usize) -> *mut c_void {
    let offset = (&raw const kernel::bindings::__per_cpu_offset)
        .cast::<u64>()
        .add(cpu)
        .read();
    // Per-CPU linker offsets may wrap; this is Linux's address-token
    // translation, not an in-bounds Rust pointer offset into the symbol.
    ((&raw mut raised_list) as usize).wrapping_add(offset as usize) as *mut c_void
}

#[cfg(native_linux_irq_work_remote_queue)]
struct CpuReadGuard;

#[cfg(native_linux_irq_work_remote_queue)]
impl Drop for CpuReadGuard {
    fn drop(&mut self) {
        unsafe { kernel::bindings::cpus_read_unlock() };
    }
}

#[cfg(native_linux_irq_work_remote_queue)]
unsafe extern "C" fn drain_barrier(_argument: *mut c_void) {}

#[no_mangle]
unsafe extern "C" fn _kmalloc(size: i32, flags: i32, _file: *mut i8, _line: i32) -> *mut c_void {
    assert_eq!(size, 128);
    assert_eq!(flags, 2);
    assert_eq!(MOCK_IRQ_FLAGS.load(Ordering::Relaxed) & 0x200, 0);
    ALLOCATIONS.fetch_add(1, Ordering::Relaxed);
    if ALLOCATE_FAILS.load(Ordering::Relaxed) {
        return null_mut();
    }
    (&raw mut STORAGE.0).cast()
}

#[no_mangle]
unsafe extern "C" fn cpu_pause() {
    core::hint::spin_loop();
}

#[no_mangle]
unsafe extern "C" fn cpu_disable_interrupt_save() -> u64 {
    SAVES.fetch_add(1, Ordering::Relaxed);
    MOCK_IRQ_FLAGS.fetch_and(!0x200, Ordering::Relaxed)
}

#[no_mangle]
unsafe extern "C" fn cpu_restore_interrupt(flags: u64) {
    RESTORES.fetch_add(1, Ordering::Relaxed);
    MOCK_IRQ_FLAGS.store(flags, Ordering::Relaxed);
}

unsafe fn flags(work: *mut u8) -> u32 {
    AtomicU32::from_ptr(work.add(8).cast()).load(Ordering::Acquire)
}

unsafe extern "C" fn callback(work: *mut smp_ikc::LinuxIrqWork) {
    let bytes = work.cast::<u8>();
    assert_eq!(flags(bytes) & 3, 2); // Linux has cleared PENDING, retaining BUSY.
    #[cfg(not(native_linux_irq_work_remote_queue))]
    assert_eq!(flags(bytes) & 0xf0, 0x20); // Linux's actual claim added its type.
    #[cfg(native_linux_irq_work_remote_queue)]
    {
        // The real McKernel producer bypasses Linux's claim helper; verify
        // the unchanged producer's direct BUSY-only publication separately.
        assert_eq!(flags(bytes) & 0xf0, 0);
        let cpu = current_linux_cpu();
        assert_eq!(cpu, TARGET_CPU.load(Ordering::Acquire) as u32);
        REMOTE_CALLBACKS[cpu as usize].fetch_add(1, Ordering::Relaxed);
    }
    assert_eq!(bytes.add(12).cast::<u32>().read(), 0);
    assert_eq!(bytes.add(24).cast::<u64>().read(), 0); // irqwait initialized.
    for index in 32..64 {
        assert_eq!(bytes.add(index).read(), 0);
    }
    CALLBACKS.fetch_add(1, Ordering::Release);
}

#[no_mangle]
unsafe extern "C" fn ihk_mc_ikc_arch_issue_host_ipi(cpu: i32, vector: i32) -> i32 {
    #[cfg(not(native_linux_irq_work_remote_queue))]
    assert_eq!(cpu, 0);
    assert_eq!(vector, 0xf6);
    assert_eq!(MOCK_IRQ_FLAGS.load(Ordering::Relaxed) & 0x200, 0);
    #[cfg(native_linux_irq_work_remote_queue)]
    {
        assert_eq!(cpu, TARGET_CPU.load(Ordering::Relaxed));
        assert_ne!(cpu, current_linux_cpu() as i32);
        // No dequeue/re-enqueue or Linux irq_work_queue call intervenes.
        // Linux must consume the exact work published by the guest producer.
        send_ipi_mask((&raw const TARGET_MASK).cast(), vector);
        return 0;
    }
    #[cfg(not(native_linux_irq_work_remote_queue))]
    {
        let node = llist::llist_del_all((&raw const QUEUE).cast_mut().cast());
        assert!(!node.is_null());
        assert!(llist::llist_next(node).is_null());
        let expected = smp_ikc::per_cpu_irq_work.add(CPU.load(Ordering::Relaxed) as usize);
        assert_eq!(node.cast::<c_void>(), expected.cast::<c_void>());
        assert_eq!(flags(expected.cast()), 2);
        // This is the explicit test transport: hand the very same object to the
        // real Linux engine. It is not proof of cross-kernel APIC delivery.
        assert!(irq_work_queue(expected.cast()));
        0
    }
}

#[no_mangle]
unsafe extern "C" fn ihk_mc_ikc_init_first_local(
    _channel: *mut c_void,
    _handler: *mut c_void,
) -> i32 {
    0
}

unsafe fn write_boot<T>(offset: usize, value: T) {
    (&raw mut PREFIX.0)
        .cast::<u8>()
        .add(offset)
        .cast::<T>()
        .write(value);
}

struct MigrationGuard;
impl Drop for MigrationGuard {
    fn drop(&mut self) {
        unsafe { kernel::bindings::migrate_enable() };
    }
}

struct IrqWorkVerification;
impl kernel::Module for IrqWorkVerification {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        assert!(cfg!(native_linux_irq_work_v6_12));
        // The harness requires non-RT x86 with a real IRQ-work interrupt.
        // Pin the init task to its queue CPU. When it resumes after each
        // callback, that CPU's hardirq tail has finished touching the object.
        #[cfg(native_linux_irq_work_remote_queue)]
        unsafe {
            kernel::bindings::cpus_read_lock()
        };
        #[cfg(native_linux_irq_work_remote_queue)]
        let _topology = CpuReadGuard;
        unsafe { kernel::bindings::migrate_disable() };
        let _migration = MigrationGuard;
        unsafe {
            assert_eq!(smp_ikc::ihk_mc_interrupt_host(0, 0), -22);
            boot_param = (&raw mut PREFIX).cast();
            write_boot(192, (&raw const QUEUE).cast_mut().cast::<c_void>());
            write_boot(4288, callback as *const ());
            write_boot(4296, 0xf6_u32);
            assert_eq!(smp_ikc::ihk_mc_interrupt_host(-1, 0), -22);
            assert_eq!(smp_ikc::ihk_mc_interrupt_host(512, 0), -22);
            assert_eq!(smp_ikc::ihk_mc_interrupt_host(1, 0), -22);
            assert_eq!(ALLOCATIONS.load(Ordering::Relaxed), 0);
            assert_eq!(smp_ikc::ihk_mc_interrupt_host(0, 0), -12);
            assert!(smp_ikc::per_cpu_irq_work.is_null());
            ALLOCATE_FAILS.store(false, Ordering::Relaxed);
            #[cfg(native_linux_irq_work_remote_queue)]
            let initiating_cpu = {
                let cpu_count = (&raw const kernel::bindings::nr_cpu_ids).read();
                assert_eq!(cpu_count, 4);
                let origin = current_linux_cpu();
                assert!(origin < 4);
                for cpu in 0..4 {
                    let queue = linux_queue(cpu);
                    let physical = per_cpu_ptr_to_phys(queue);
                    assert!(physical != 0 && physical % 8 == 0);
                    assert!(physical % 4096 <= 4096 - 8);
                    write_boot(192 + 8 * cpu, queue);
                    pr_info!(
                        "MCKERNEL_IRQ_WORK_REMOTE queue_cpu={} physical={:x}\n",
                        cpu,
                        physical
                    );
                }
                origin
            };
            for sequence in 0..512_u32 {
                CPU.store((sequence % 2) as i32, Ordering::Relaxed);
                #[cfg(not(native_linux_irq_work_remote_queue))]
                assert_eq!(smp_ikc::ihk_mc_interrupt_host(0, 123), 0);
                #[cfg(native_linux_irq_work_remote_queue)]
                {
                    let target = (initiating_cpu + 1 + sequence % 3) % 4;
                    TARGET_CPU.store(target as i32, Ordering::Release);
                    (*(&raw mut TARGET_MASK)).bits[0] = 1 << target;
                    assert_eq!(smp_ikc::ihk_mc_interrupt_host(target as i32, 123), 0);
                }
                let work = smp_ikc::per_cpu_irq_work.add((sequence % 2) as usize);
                let mut remaining = 10_000_000;
                while CALLBACKS.load(Ordering::Acquire) != sequence + 1
                    || flags(work.cast()) & 2 != 0
                {
                    // Never return an init error and free a still-queued
                    // module. A timeout fails the disposable guest instead.
                    assert!(remaining > 0, "Linux IRQ work did not complete");
                    remaining -= 1;
                    core::hint::spin_loop();
                }
                #[cfg(native_linux_irq_work_remote_queue)]
                irq_work_sync(work.cast());
                assert_eq!(MOCK_IRQ_FLAGS.load(Ordering::Relaxed), 0x202);
            }
            assert_eq!(ALLOCATIONS.load(Ordering::Relaxed), 2);
            assert_eq!(
                SAVES.load(Ordering::Relaxed),
                RESTORES.load(Ordering::Relaxed)
            );
            assert!(QUEUE.load(Ordering::Relaxed).is_null());
            for index in 0..2 {
                assert_eq!(flags(smp_ikc::per_cpu_irq_work.add(index).cast()) & 3, 0);
            }
            #[cfg(native_linux_irq_work_remote_queue)]
            for cpu in 0..4 {
                let count = REMOTE_CALLBACKS[cpu].load(Ordering::Acquire);
                if cpu as u32 == initiating_cpu {
                    assert_eq!(count, 0);
                    continue;
                }
                assert!(count == 170 || count == 171);
                assert_eq!(
                    kernel::bindings::smp_call_function_single(
                        cpu as i32,
                        Some(drain_barrier),
                        null_mut(),
                        1
                    ),
                    0
                );
                pr_info!(
                    "MCKERNEL_IRQ_WORK_REMOTE sender={} target={} callbacks={} drained=1\n",
                    initiating_cpu,
                    cpu,
                    count
                );
            }
        }
        #[cfg(native_linux_irq_work_remote_queue)]
        pr_info!("MCKERNEL_IRQ_WORK_REMOTE PASS callbacks=512 targets=3 transport=direct-linux-raised-list-apic mckernel_boot=0\n");
        #[cfg(not(native_linux_irq_work_remote_queue))]
        pr_info!("MCKERNEL_IRQ_WORK_VERIFY PASS callbacks=512 slots=2 allocation_failure=1 pending_busy_cleared=1 transport=local-linux-irq-work mckernel_boot=0\n");
        Ok(Self)
    }
}

impl Drop for IrqWorkVerification {
    fn drop(&mut self) {
        assert_eq!(CALLBACKS.load(Ordering::Acquire), 512);
        pr_info!("MCKERNEL_IRQ_WORK_VERIFY UNLOAD drained=1\n");
    }
}
