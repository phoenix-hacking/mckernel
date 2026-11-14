// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code,private_interfaces,non_snake_case)]
use core::ffi::c_void;
use core::ptr::{read_volatile,write_volatile,addr_of,addr_of_mut,null_mut};
type CInt=i32;type CLong=i64;type CULong=u64;type SizeT=u64;
const EFAULT:CInt=14;const EINVAL:CInt=22;const ENOMEM:CInt=12;
const PAGE_SIZE:CULong=4096;
const PTATTR_ACTIVE:CULong=1;const PTATTR_USER:CULong=4;
const PTATTR_NO_EXECUTE:CULong=0x8000000000000000;const PTATTR_UNCACHABLE:CULong=0x10000;
extern "C" {
 fn arch_vdso_state_bridge(v:*mut *mut ArchVdso,s:*mut *mut SizeT,o:*mut *mut isize);
 fn fixture_setup()->CInt;
 fn fixture_phys(p:*mut c_void)->CULong;
 fn kprintf(p:*const i8,...)->CInt;
}
#[repr(C)]
pub struct ArchVdso {
    busy: CLong,
    vdso_npages: CInt,
    vvar_is_global: i8,
    hpet_is_global: i8,
    pvti_is_global: i8,
    padding: i8,
    vdso_physlist: [CLong; 2],
    vvar_virt: *mut c_void,
    vvar_phys: CLong,
    hpet_virt: *mut c_void,
    hpet_phys: CLong,
    pvti_virt: *mut c_void,
    pvti_phys: CLong,
    vgtod_virt: *mut c_void,
}
mod debug {
#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
}
unsafe fn arch_vdso_state() -> Result<(*mut ArchVdso, *mut SizeT, *mut isize), CInt> {
    let mut vdso: *mut ArchVdso = null_mut();
    let mut container_size: *mut SizeT = null_mut();
    let mut vdso_offset: *mut isize = null_mut();

    arch_vdso_state_bridge(
        addr_of_mut!(vdso),
        addr_of_mut!(container_size),
        addr_of_mut!(vdso_offset),
    );
    if vdso.is_null() || container_size.is_null() || vdso_offset.is_null() {
        return Err(-EFAULT);
    }
    Ok((vdso, container_size, vdso_offset))
}
// Only provider adapters below are fixture controlled; exact production bodies follow.
mod x86_cpu_helpers {
 use super::*;
 type X86GetIntFn=unsafe extern "C" fn()->CInt;
 type X86AllocAlignedPagesNodeFn=unsafe extern "C" fn(CInt,CInt,CULong,CInt,CInt,CULong,*mut i8,CInt)->*mut c_void;
 type X86CpuLogFn=unsafe extern "C" fn(CInt);
 #[no_mangle]
pub unsafe extern "C" fn x86_arch_setup_pvclock_body_result(
    pvti_slot: *mut *mut c_void,
    pvti_npages_slot: *mut CInt,
    num_processors: CInt,
    pvti_entry_size: usize,
    page_size: CULong,
    page_p2align: CInt,
    alloc_flag: CULong,
    pg_kernel: CInt,
    file: *mut i8,
    line: CInt,
    available_fn: Option<X86GetIntFn>,
    alloc_fn: Option<X86AllocAlignedPagesNodeFn>,
    log_fn: Option<X86CpuLogFn>,
) -> CInt {
    if pvti_slot.is_null()
        || pvti_npages_slot.is_null()
        || num_processors < 0
        || pvti_entry_size == 0
        || page_size == 0
    {
        return -EINVAL;
    }
    let Some(available) = available_fn else {
        return -EINVAL;
    };
    let Some(alloc) = alloc_fn else {
        return -EINVAL;
    };

    if let Some(log) = log_fn {
        unsafe {
            log(6);
        }
    }
    if unsafe { available() } == 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(7);
            }
        }
        return 0;
    }

    let page_size_usize = page_size as usize;
    if page_size_usize as CULong != page_size {
        return -EINVAL;
    }
    let size = match (num_processors as usize).checked_mul(pvti_entry_size) {
        Some(size) => size,
        None => return -EINVAL,
    };
    let rounded = match size.checked_add(page_size_usize - 1) {
        Some(value) => value,
        None => return -EINVAL,
    };
    let npages = rounded / page_size_usize;
    if npages > CInt::MAX as usize {
        return -EINVAL;
    }
    unsafe {
        write_volatile(pvti_npages_slot, npages as CInt);
    }

    let pages = unsafe {
        alloc(
            npages as CInt,
            page_p2align,
            alloc_flag,
            -1,
            pg_kernel,
            CULong::MAX,
            file,
            line,
        )
    };
    unsafe {
        write_volatile(pvti_slot, pages);
    }
    if pages.is_null() {
        if let Some(log) = log_fn {
            unsafe {
                log(8);
            }
        }
        return -ENOMEM;
    }

    if let Some(zero_len) = page_size_usize.checked_mul(npages) {
        unsafe {
            core::ptr::write_bytes(pages.cast::<u8>(), 0, zero_len);
        }
    } else {
        return -EINVAL;
    }

    if let Some(log) = log_fn {
        unsafe {
            log(9);
        }
    }
    0
}
 pub unsafe extern "C" fn arch_setup_pvclock()->CInt { unsafe {fixture_setup()} }
}
mod x86_memory_helpers {
 use super::*;
 type X86AddrLogFn=unsafe extern "C" fn(CInt,CULong);
 const X86_ADDR_LOG_KERNEL:CInt=1;const X86_ADDR_LOG_STRAIGHT:CInt=2;
 extern "C" { fn x86_pt_set_page_bridge(pt:*mut c_void,virt:CULong,phys:CULong,attr:CULong)->CInt; }
 #[no_mangle]
pub unsafe extern "C" fn x86_virt_to_phys_body_result(
    va: CULong,
    map_kernel_start: CULong,
    kernel_phys_base: CULong,
    linux_page_offset_base: CULong,
    map_fixed_start: CULong,
    map_st_start: CULong,
    log_fn: Option<X86AddrLogFn>,
) -> CULong {
    if va >= map_kernel_start {
        if let Some(log) = log_fn {
            unsafe {
                log(X86_ADDR_LOG_KERNEL, va);
            }
        }
        return va
            .wrapping_sub(map_kernel_start)
            .wrapping_add(kernel_phys_base);
    }
    if va >= linux_page_offset_base {
        return va.wrapping_sub(linux_page_offset_base);
    }
    if va >= map_fixed_start {
        return va.wrapping_sub(map_fixed_start);
    }

    if let Some(log) = log_fn {
        unsafe {
            log(X86_ADDR_LOG_STRAIGHT, va);
        }
    }
    va.wrapping_sub(map_st_start)
}
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_set_page(
    pt: *mut c_void,
    virt: *mut c_void,
    phys: CULong,
    attr: CULong,
) -> CInt {
    unsafe { x86_pt_set_page_bridge(pt, virt as CULong, phys, attr | PTATTR_ACTIVE) }
}
 pub unsafe extern "C" fn virt_to_phys(p:*mut c_void)->CULong { unsafe {fixture_phys(p)} }
}
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06 source-only next slice: complete global VDSO mapping orchestration.
// Root removes the old extern declaration of vdso_map_global_pages before merge.
// Existing ArchVdso/state bridge, Rust memory/CPU providers and Ddebug ABI reused.
extern "C" {
    #[link_name = "pvti"]
    static mut ARCH_VDSO_GLOBAL_PVTI: *mut c_void;
    #[link_name = "pvti_npages"]
    static mut ARCH_VDSO_GLOBAL_PVTI_NPAGES: CInt;
}

type ArchVdsoGlobalSetupFn = unsafe extern "C" fn() -> CInt;
type ArchVdsoGlobalPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type ArchVdsoGlobalMapFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong) -> CInt;
type ArchVdsoGlobalLogFn = unsafe extern "C" fn(CInt, CInt);

const VDSO_GLOBAL_LOG_ENTER: CInt = 0;
const VDSO_GLOBAL_LOG_VVAR_FAILED: CInt = 1;
const VDSO_GLOBAL_LOG_HPET_FAILED: CInt = 2;
const VDSO_GLOBAL_LOG_SETUP_FAILED: CInt = 3;
const VDSO_GLOBAL_LOG_PVTI_FAILED: CInt = 4;
const VDSO_GLOBAL_LOG_EXIT: CInt = 5;

#[used]
#[link_section = "__verbose"]
static mut VDSO_GLOBAL_ENTER_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"vdso_map_global_pages\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};
#[used]
#[link_section = "__verbose"]
static mut VDSO_GLOBAL_EXIT_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"vdso_map_global_pages\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};

unsafe extern "C" fn arch_vdso_global_log(event: CInt, error: CInt) {
    unsafe {
        match event {
            VDSO_GLOBAL_LOG_ENTER => {
                if read_volatile(addr_of!(VDSO_GLOBAL_ENTER_DEBUG.line_flags)) >> 24 != 0 {
                    kprintf(b"vdso_map_global_pages()\n\0".as_ptr().cast());
                }
            }
            VDSO_GLOBAL_LOG_VVAR_FAILED => {
                kprintf(b"vdso_map_global_pages: mapping vvar failed. %d\n\0".as_ptr().cast(), error);
            }
            VDSO_GLOBAL_LOG_HPET_FAILED => {
                kprintf(b"vdso_map_global_pages: mapping hpet failed. %d\n\0".as_ptr().cast(), error);
            }
            VDSO_GLOBAL_LOG_SETUP_FAILED => {
                kprintf(b"vdso_map_global_pages: arch_setup_pvclock failed. %d\n\0".as_ptr().cast(), error);
            }
            VDSO_GLOBAL_LOG_PVTI_FAILED => {
                kprintf(b"vdso_map_global_pages: mapping pvti failed. %d\n\0".as_ptr().cast(), error);
            }
            VDSO_GLOBAL_LOG_EXIT => {
                if read_volatile(addr_of!(VDSO_GLOBAL_EXIT_DEBUG.line_flags)) >> 24 != 0 {
                    kprintf(b"vdso_map_global_pages(): %d\n\0".as_ptr().cast(), error);
                }
            }
            _ => {}
        }
    }
}

/// Preserve the original partial-map ownership: stop at the first setup/map
/// error, leave successful prior mappings in place, and never free/rollback.
/// vdso and both global slots must remain live under the original boot/setup
/// exclusion. Callback effects on later state/slots are observed in order.
#[no_mangle]
pub unsafe extern "C" fn vdso_map_global_pages_body_result(
    vdso: *mut ArchVdso,
    pvti_slot: *mut *mut c_void,
    pvti_npages_slot: *mut CInt,
    setup_fn: ArchVdsoGlobalSetupFn,
    phys_fn: ArchVdsoGlobalPhysFn,
    map_fn: ArchVdsoGlobalMapFn,
    log_fn: ArchVdsoGlobalLogFn,
) -> CInt {
    unsafe {
        log_fn(VDSO_GLOBAL_LOG_ENTER, 0);
        let ordinary_attr = PTATTR_ACTIVE | PTATTR_USER | PTATTR_NO_EXECUTE;
        if !read_volatile(addr_of!((*vdso).vvar_virt)).is_null()
            && read_volatile(addr_of!((*vdso).vvar_is_global)) != 0
        {
            let error = map_fn(
                null_mut(),
                read_volatile(addr_of!((*vdso).vvar_virt)),
                read_volatile(addr_of!((*vdso).vvar_phys)) as CULong,
                ordinary_attr,
            );
            if error != 0 {
                log_fn(VDSO_GLOBAL_LOG_VVAR_FAILED, error);
                log_fn(VDSO_GLOBAL_LOG_EXIT, error);
                return error;
            }
        }
        if !read_volatile(addr_of!((*vdso).hpet_virt)).is_null()
            && read_volatile(addr_of!((*vdso).hpet_is_global)) != 0
        {
            let error = map_fn(
                null_mut(),
                read_volatile(addr_of!((*vdso).hpet_virt)),
                read_volatile(addr_of!((*vdso).hpet_phys)) as CULong,
                ordinary_attr | PTATTR_UNCACHABLE,
            );
            if error != 0 {
                log_fn(VDSO_GLOBAL_LOG_HPET_FAILED, error);
                log_fn(VDSO_GLOBAL_LOG_EXIT, error);
                return error;
            }
        }
        if !read_volatile(addr_of!((*vdso).pvti_virt)).is_null()
            && read_volatile(addr_of!((*vdso).pvti_is_global)) != 0
        {
            let error = setup_fn();
            if error != 0 {
                log_fn(VDSO_GLOBAL_LOG_SETUP_FAILED, error);
                log_fn(VDSO_GLOBAL_LOG_EXIT, error);
                return error;
            }
            // PAGE_SIZE is C 1UL<<PAGE_SHIFT. Match its unsigned 64-bit
            // displacement and the old destination-minus/source-plus order.
            let mut i: CInt = 0;
            while i < read_volatile(pvti_npages_slot) {
                let displacement = (i as CULong).wrapping_mul(PAGE_SIZE) as usize;
                let virt = read_volatile(addr_of!((*vdso).pvti_virt))
                    .cast::<u8>().wrapping_sub(displacement).cast::<c_void>();
                let source = read_volatile(pvti_slot)
                    .cast::<u8>().wrapping_add(displacement).cast::<c_void>();
                let phys = phys_fn(source);
                let error = map_fn(null_mut(), virt, phys, ordinary_attr);
                if error != 0 {
                    log_fn(VDSO_GLOBAL_LOG_PVTI_FAILED, error);
                    log_fn(VDSO_GLOBAL_LOG_EXIT, error);
                    return error;
                }
                i += 1;
            }
        }
        log_fn(VDSO_GLOBAL_LOG_EXIT, 0);
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn vdso_map_global_pages() -> CInt {
    // Reuse the existing state-provider contract already used by the selected
    // Rust arch_setup_vdso caller. It returns addresses of stable C data only.
    let (vdso, _, _) = match unsafe { arch_vdso_state() } {
        Ok(state) => state,
        Err(error) => return error,
    };
    unsafe {
        vdso_map_global_pages_body_result(
            vdso,
            addr_of_mut!(ARCH_VDSO_GLOBAL_PVTI),
            addr_of_mut!(ARCH_VDSO_GLOBAL_PVTI_NPAGES),
            crate::x86_cpu_helpers::arch_setup_pvclock,
            crate::x86_memory_helpers::virt_to_phys,
            crate::x86_memory_helpers::ihk_mc_pt_set_page,
            arch_vdso_global_log,
        )
    }
}
