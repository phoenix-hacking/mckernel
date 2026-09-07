#![allow(dead_code)]

// Compile the complete guest producer and its real intrusive-list operations.
// Only allocation, CPU context, boot inputs and host delivery are test doubles.
#[path = "../../../kernel/rust/smp_ikc.rs"]
#[cfg(not(legacy_c_reference))]
mod smp_ikc;
#[cfg(legacy_c_reference)]
mod smp_ikc {
    #[repr(C, align(8))]
    pub struct LinuxIrqWork([u8; 64]);
    unsafe extern "C" {
        pub static mut per_cpu_irq_work: *mut LinuxIrqWork;
        pub fn ihk_mc_interrupt_host(cpu: i32, vector: i32) -> i32;
    }
}
#[path = "../../../kernel/rust/llist.rs"]
mod llist;

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
        super::CPU.with(|value| value.get())
    }
}

#[cfg(legacy_c_reference)]
#[no_mangle]
unsafe extern "C" fn ihk_mc_get_processor_id() -> i32 {
    x86_local::ihk_mc_get_processor_id()
}

use core::ffi::c_void;
use core::ptr::null_mut;
use core::sync::atomic::{AtomicBool, AtomicPtr, AtomicU32, AtomicU64, AtomicUsize, Ordering};
use std::cell::Cell;

thread_local! {
    static CPU: Cell<i32> = const { Cell::new(0) };
    static INTERRUPTS: Cell<u64> = const { Cell::new(0x202) };
}

#[repr(C, align(64))]
struct Storage([u8; 512 * 64]);
#[repr(C, align(8))]
struct BootPrefix([u8; 4304]);
static mut STORAGE: Storage = Storage([0xa5; 512 * 64]);
static mut PREFIX: BootPrefix = BootPrefix([0; 4304]);
static QUEUE: AtomicPtr<llist::LListNode> = AtomicPtr::new(null_mut());
static ALLOCATIONS: AtomicUsize = AtomicUsize::new(0);
static ALLOCATE_FAILS: AtomicBool = AtomicBool::new(false);
static CALLBACKS: AtomicUsize = AtomicUsize::new(0);
static IPIS: AtomicUsize = AtomicUsize::new(0);
static SAVES: AtomicUsize = AtomicUsize::new(0);
static RESTORES: AtomicUsize = AtomicUsize::new(0);
static IPI_FAILS: AtomicBool = AtomicBool::new(false);
static RELEASE_BUSY_ON_PAUSE: AtomicBool = AtomicBool::new(false);

#[no_mangle]
static mut boot_param: *mut c_void = null_mut();
#[no_mangle]
static mut num_processors: i32 = 2;

// The unchanged legacy producer's variadic logger is irrelevant to this test.
// This ABI-correct x86 leaf ignores all arguments and returns zero.
#[cfg(not(native_linux_irq_work_v6_12))]
core::arch::global_asm!(
    ".text",
    ".globl kprintf",
    ".type kprintf,@function",
    "kprintf:",
    "xor eax,eax",
    "ret",
    ".size kprintf,.-kprintf"
);

#[no_mangle]
unsafe extern "C" fn _kmalloc(size: i32, flags: i32, _file: *mut i8, _line: i32) -> *mut c_void {
    assert_eq!(size, 64 * num_processors);
    assert_eq!(flags, 2);
    #[cfg(native_linux_irq_work_v6_12)]
    INTERRUPTS.with(|value| assert_eq!(value.get() & 0x200, 0));
    ALLOCATIONS.fetch_add(1, Ordering::Relaxed);
    if ALLOCATE_FAILS.load(Ordering::Relaxed) {
        return null_mut();
    }
    // Make an initialization race more likely without changing its body.
    for _ in 0..100 {
        std::thread::yield_now();
    }
    (&raw mut STORAGE.0).cast()
}

#[no_mangle]
unsafe extern "C" fn cpu_pause() {
    if RELEASE_BUSY_ON_PAUSE.swap(false, Ordering::Relaxed) {
        set_flags(smp_ikc::per_cpu_irq_work.cast(), 0);
    }
    std::thread::yield_now();
}

#[no_mangle]
unsafe extern "C" fn cpu_disable_interrupt_save() -> u64 {
    SAVES.fetch_add(1, Ordering::Relaxed);
    INTERRUPTS.with(|value| value.replace(value.get() & !0x200))
}

#[no_mangle]
unsafe extern "C" fn cpu_restore_interrupt(flags: u64) {
    RESTORES.fetch_add(1, Ordering::Relaxed);
    INTERRUPTS.with(|value| value.set(flags));
}

unsafe fn flags(work: *mut u8) -> u64 {
    #[cfg(native_linux_irq_work_v6_12)]
    {
        AtomicU32::from_ptr(work.add(8).cast()).load(Ordering::Acquire) as u64
    }
    #[cfg(not(native_linux_irq_work_v6_12))]
    {
        AtomicU64::from_ptr(work.cast()).load(Ordering::Acquire)
    }
}

unsafe fn set_flags(work: *mut u8, value: u64) {
    #[cfg(native_linux_irq_work_v6_12)]
    {
        AtomicU32::from_ptr(work.add(8).cast()).store(value as u32, Ordering::Release);
    }
    #[cfg(not(native_linux_irq_work_v6_12))]
    {
        AtomicU64::from_ptr(work.cast()).store(value, Ordering::Release);
    }
}

unsafe extern "C" fn callback(work: *mut smp_ikc::LinuxIrqWork) {
    let bytes = work.cast::<u8>();
    assert_eq!(flags(bytes), 2);
    #[cfg(native_linux_irq_work_v6_12)]
    {
        assert!(core::slice::from_raw_parts(bytes.add(12), 4)
            .iter()
            .all(|b| *b == 0));
        assert!(core::slice::from_raw_parts(bytes.add(24), 40)
            .iter()
            .all(|b| *b == 0));
    }
    CALLBACKS.fetch_add(1, Ordering::Relaxed);
}

#[no_mangle]
unsafe extern "C" fn ihk_mc_ikc_arch_issue_host_ipi(cpu: i32, vector: i32) -> i32 {
    assert!(cpu == 0 || cpu == 511);
    assert_eq!(vector, 0xf6);
    #[cfg(native_linux_irq_work_v6_12)]
    INTERRUPTS.with(|value| assert_eq!(value.get() & 0x200, 0));
    IPIS.fetch_add(1, Ordering::Relaxed);
    let mut node = llist::llist_del_all((&raw const QUEUE).cast_mut().cast());
    while !node.is_null() {
        let next = llist::llist_next(node);
        let bytes = node.cast::<u8>();
        #[cfg(not(native_linux_irq_work_v6_12))]
        let bytes = bytes.sub(8);
        let offset = bytes as usize - (&raw const STORAGE.0) as usize;
        assert_eq!(offset % 64, 0);
        assert!(offset < num_processors as usize * 64);
        let actual: unsafe extern "C" fn(*mut smp_ikc::LinuxIrqWork) = bytes
            .add(16)
            .cast::<unsafe extern "C" fn(*mut smp_ikc::LinuxIrqWork)>()
            .read();
        assert_eq!(actual as usize, callback as *const () as usize);
        actual(bytes.cast());
        set_flags(bytes, 0);
        node = next;
    }
    if IPI_FAILS.load(Ordering::Relaxed) {
        -5
    } else {
        0
    }
}

#[no_mangle]
unsafe extern "C" fn ihk_mc_ikc_init_first_local(
    _channel: *mut c_void,
    _handler: *mut c_void,
) -> i32 {
    37
}

unsafe fn write_boot<T>(offset: usize, value: T) {
    (&raw mut PREFIX.0)
        .cast::<u8>()
        .add(offset)
        .cast::<T>()
        .write(value);
}

unsafe fn setup() {
    boot_param = (&raw mut PREFIX).cast();
    write_boot(192, (&raw const QUEUE).cast_mut().cast::<c_void>());
    write_boot(
        192 + 511 * 8,
        (&raw const QUEUE).cast_mut().cast::<c_void>(),
    );
    write_boot(4288, callback as *const ());
    write_boot(4296, 0xf6_u32);
}

unsafe fn send(cpu: i32) -> i32 {
    let before = INTERRUPTS.with(|value| value.get());
    let result = smp_ikc::ihk_mc_interrupt_host(cpu, 123);
    INTERRUPTS.with(|value| assert_eq!(value.get(), before));
    result
}

unsafe fn invalid_inputs() {
    let original = boot_param;
    boot_param = null_mut();
    assert_eq!(send(0), -22);
    boot_param = original;
    for cpu in [-1, 512, i32::MAX] {
        assert_eq!(send(cpu), -22);
    }
    assert_eq!(send(1), -22); // No owned raised-list address.
    for count in [-1, 0, 513, i32::MAX] {
        num_processors = count;
        assert_eq!(send(0), -22);
    }
    num_processors = 2;
    for cpu in [-1, 2, i32::MAX] {
        CPU.with(|value| value.set(cpu));
        assert_eq!(send(0), -22);
    }
    CPU.with(|value| value.set(0));
    write_boot(4288, core::ptr::null::<()>());
    assert_eq!(send(0), -22);
    write_boot(4288, callback as *const ());
    assert_eq!(ALLOCATIONS.load(Ordering::Relaxed), 0);
    assert_eq!(IPIS.load(Ordering::Relaxed), 0);
    assert!(smp_ikc::per_cpu_irq_work.is_null());
}

fn main() {
    let concurrent = std::env::args().any(|argument| argument == "concurrent");
    unsafe {
        setup();
    }
    if concurrent {
        assert!(cfg!(native_linux_irq_work_v6_12));
        let barrier = std::sync::Arc::new(std::sync::Barrier::new(2));
        let threads: Vec<_> = (0..2)
            .map(|cpu| {
                let barrier = barrier.clone();
                std::thread::spawn(move || {
                    CPU.with(|value| value.set(cpu));
                    barrier.wait();
                    for _ in 0..4096 {
                        assert_eq!(unsafe { send(0) }, 0);
                    }
                })
            })
            .collect();
        for thread in threads {
            thread.join().unwrap();
        }
        assert_eq!(ALLOCATIONS.load(Ordering::Relaxed), 1);
        assert_eq!(CALLBACKS.load(Ordering::Relaxed), 8192);
        println!("PASS native-concurrent one-allocation callbacks=8192");
    } else {
        #[cfg(native_linux_irq_work_v6_12)]
        unsafe {
            invalid_inputs();
        }
        ALLOCATE_FAILS.store(true, Ordering::Relaxed);
        assert_eq!(unsafe { send(0) }, -12);
        assert!(unsafe { smp_ikc::per_cpu_irq_work.is_null() });
        ALLOCATE_FAILS.store(false, Ordering::Relaxed);
        for _ in 0..512 {
            for cpu in 0..2 {
                CPU.with(|value| value.set(cpu));
                assert_eq!(unsafe { send(if cpu == 0 { 0 } else { 511 }) }, 0);
            }
        }
        assert_eq!(ALLOCATIONS.load(Ordering::Relaxed), 2);
        assert_eq!(CALLBACKS.load(Ordering::Relaxed), 1024);
        CPU.with(|value| value.set(0));
        unsafe {
            set_flags(smp_ikc::per_cpu_irq_work.cast(), 2);
        }
        RELEASE_BUSY_ON_PAUSE.store(true, Ordering::Relaxed);
        assert_eq!(unsafe { send(0) }, 0);
        assert!(!RELEASE_BUSY_ON_PAUSE.load(Ordering::Relaxed));
        INTERRUPTS.with(|value| value.set(0x2));
        assert_eq!(unsafe { send(0) }, 0); // Retain already-disabled IRQ state.
        IPI_FAILS.store(true, Ordering::Relaxed);
        assert_eq!(
            unsafe { send(0) },
            if cfg!(native_linux_irq_work_v6_12) {
                -5
            } else {
                0
            }
        );
        #[cfg(native_linux_irq_work_v6_12)]
        unsafe {
            num_processors = 1;
            assert_eq!(send(0), -22); // Do not silently reuse an array of another size.
            num_processors = 2;
        }
        assert_eq!(CALLBACKS.load(Ordering::Relaxed), 1027);
        println!("PASS boundary allocation-failure-retry repeated-reuse busy-wait irq-restore ipi-result callbacks=1027 native={}", cfg!(native_linux_irq_work_v6_12));
    }
    assert_eq!(
        SAVES.load(Ordering::Relaxed),
        RESTORES.load(Ordering::Relaxed)
    );
    assert!(QUEUE.load(Ordering::Relaxed).is_null());
    unsafe {
        for cpu in 0..2 {
            assert_eq!(flags(smp_ikc::per_cpu_irq_work.add(cpu).cast()), 0);
        }
    }
}
