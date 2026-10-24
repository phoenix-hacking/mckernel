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
