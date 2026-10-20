use core::arch::asm;
use core::ffi::c_void;
use core::ptr::{write_bytes, write_unaligned};
use core::sync::atomic::{AtomicI32, Ordering};

use crate::abi::{CInt, CULong, SizeT, X86CpuLocalVariables};

const PAGE_SIZE: usize = 4096;
const PAGE_P2ALIGN: CInt = 0;
const IHK_MC_AP_CRITICAL: CULong = 0x000001;
const IHK_MC_PG_KERNEL: CInt = 0;
const LOCALS_SPAN: usize = 4 * PAGE_SIZE;
const MSR_GS_BASE: u32 = 0xc000_0101;

#[no_mangle]
pub static mut locals: *mut X86CpuLocalVariables = core::ptr::null_mut();

#[no_mangle]
pub static mut x86_cpu_local_variables_span: SizeT = LOCALS_SPAN;

static LAST_PROCESSOR_ID: AtomicI32 = AtomicI32::new(-1);
static mut BOOT_CPU_LOCAL: [u8; 456] = [0; 456];

unsafe extern "C" {
    static mut num_processors: CInt;

    fn _ihk_mc_alloc_aligned_pages_node(
        npages: CInt,
        p2align: CInt,
        flag: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
        file: *mut i8,
        line: CInt,
    ) -> *mut c_void;
    fn kprintf(format: *const i8, ...) -> CInt;
}

#[inline(always)]
unsafe fn rdmsr(index: u32) -> CULong {
    let low: u32;
    let high: u32;
    asm!(
        "rdmsr",
        in("ecx") index,
        out("eax") low,
        out("edx") high,
        options(nomem, preserves_flags)
    );
    ((high as CULong) << 32) | low as CULong
}

#[inline(always)]
unsafe fn wrmsr(index: u32, value: CULong) {
    asm!(
        "wrmsr",
        in("ecx") index,
        in("eax") value as u32,
        in("edx") (value >> 32) as u32,
        options(nomem, preserves_flags)
    );
}

#[inline(always)]
unsafe fn set_gs_base(address: *mut c_void) {
    wrmsr(MSR_GS_BASE, address as CULong);
}

#[inline(always)]
unsafe fn alloc_pages(npages: CInt, flag: CULong) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        PAGE_P2ALIGN,
        flag,
        -1,
        IHK_MC_PG_KERNEL,
        CULong::MAX,
        c"x86_local.rs".as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn local_addr(id: CInt) -> *mut X86CpuLocalVariables {
    (locals as *mut u8).add(LOCALS_SPAN.wrapping_mul(id as usize)) as *mut X86CpuLocalVariables
}

#[no_mangle]
pub unsafe extern "C" fn init_processors_local(max_id: CInt) {
    let size = LOCALS_SPAN.wrapping_mul(max_id as usize);
    locals =
        alloc_pages((size / PAGE_SIZE) as CInt, IHK_MC_AP_CRITICAL) as *mut X86CpuLocalVariables;
    write_bytes(locals as *mut u8, 0, size);
    kprintf(c"locals = %p\n".as_ptr().cast(), locals);
}

#[no_mangle]
pub unsafe extern "C" fn get_x86_cpu_local_variable(id: CInt) -> *mut X86CpuLocalVariables {
    local_addr(id)
}

#[no_mangle]
pub unsafe extern "C" fn get_x86_cpu_local_kstack(id: CInt) -> *mut c_void {
    (locals as *mut u8).add(LOCALS_SPAN.wrapping_mul(id.wrapping_add(1) as usize)) as *mut c_void
}

#[no_mangle]
pub unsafe extern "C" fn get_x86_this_cpu_local() -> *mut X86CpuLocalVariables {
    get_x86_cpu_local_variable(ihk_mc_get_processor_id())
}

#[no_mangle]
pub unsafe extern "C" fn get_x86_this_cpu_kstack() -> *mut c_void {
    get_x86_cpu_local_kstack(ihk_mc_get_processor_id())
}

#[no_mangle]
pub unsafe extern "C" fn assign_processor_id() {
    let id = LAST_PROCESSOR_ID
        .fetch_add(1, Ordering::SeqCst)
        .wrapping_add(1);
    let v = get_x86_cpu_local_variable(id);
    set_gs_base(v.cast());
    write_unaligned(v.cast::<CULong>(), id as CULong);
}

#[no_mangle]
pub unsafe extern "C" fn init_boot_processor_local() {
    write_bytes((&raw mut BOOT_CPU_LOCAL).cast::<u8>(), 0xff, 456);
    set_gs_base((&raw mut BOOT_CPU_LOCAL).cast::<c_void>());
}

#[cfg(mckernel_equivalence)]
unsafe extern "C" {
    fn ihk_mc_get_processor_id_equiv() -> CInt;
}

#[cfg(mckernel_equivalence)]
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_get_processor_id() -> CInt {
    ihk_mc_get_processor_id_equiv()
}

#[cfg(not(mckernel_equivalence))]
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_get_processor_id() -> CInt {
    let gs = rdmsr(MSR_GS_BASE) as *mut u8;
    let local_base = locals as *mut u8;
    let local_end = local_base.add(LOCALS_SPAN.wrapping_mul(num_processors as usize));

    if gs < local_base || gs > local_end {
        return -1;
    }

    let id: CInt;
    asm!("mov {0:e}, gs:0", out(reg) id, options(nomem, preserves_flags));
    id
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_get_hardware_processor_id() -> CInt {
    let v = get_x86_this_cpu_local() as *const u8;
    core::ptr::read_unaligned(v.add(8).cast::<CULong>()) as CInt
}
