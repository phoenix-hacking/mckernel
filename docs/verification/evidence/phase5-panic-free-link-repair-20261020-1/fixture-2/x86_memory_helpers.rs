use crate::abi::{CInt,CULong,SizeT,ProcessVm};use core::ffi::c_void;use core::ptr::{read_volatile,write_volatile};
// Explicit fixture physical/page-fault/log callbacks, not native MM evidence.
pub unsafe fn virt_to_phys(p:*mut c_void)->u64{p as u64}


const EINVAL: i32 = 22;

const EFAULT: i32 = 14;

const PAGE_MASK: CULong = !(PTL1_SIZE - 1);

const PTL1_SHIFT: i32 = 12;

const PTL1_SIZE: CULong = 1 << PTL1_SHIFT;

const PTATTR_ACTIVE: CULong = 0x01;

const PF_WRITE: CULong = 1 << 1;

const PF_USER: CULong = 1 << 2;

const PF_PATCH: CULong = 1 << 29;

const PF_POPULATE: CULong = 1 << 30;

const X86_USER_COPY_READ: CInt = 0;

const X86_USER_COPY_WRITE: CInt = 1;

const X86_USER_COPY_LOG_RANGE: CInt = 1;

const X86_USER_COPY_LOG_PF: CInt = 2;

const X86_USER_COPY_LOG_VTOP: CInt = 3;

const X86_USER_COPY_LOG_EXTERNAL: CInt = 4;

const X86_USER_COPY_LOG_PATCH_START: CInt = 5;

const X86_USER_COPY_LOG_PATCH_RANGE: CInt = 6;

const X86_USER_COPY_LOG_PATCH_PF: CInt = 7;

const X86_USER_COPY_LOG_PATCH_VTOP: CInt = 8;

const X86_USER_COPY_LOG_PATCH_DONE: CInt = 9;

type X86UserPageFaultFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CULong) -> CInt;

type X86UserVtopFn = unsafe extern "C" fn(*mut c_void, *const c_void, *mut CULong) -> CInt;

type X86UserIsMemoryFn = unsafe extern "C" fn(CULong, CULong) -> CInt;

type X86UserMapFn = unsafe extern "C" fn(CULong, CInt, CULong) -> *mut c_void;

type X86UserUnmapFn = unsafe extern "C" fn(*mut c_void, CInt);

type X86UserPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;

type X86UserLogFn = unsafe extern "C" fn(CInt, *mut c_void, CULong, CULong, CInt);

unsafe fn x86_user_copy_bytes(dst: *mut u8, src: *const u8, size: usize) {
    let mut i = 0usize;

    while i < size {
        let byte = unsafe { read_volatile(src.add(i)) };
        unsafe {
            write_volatile(dst.add(i), byte);
        }
        i += 1;
    }
}

fn x86_user_range_valid(uaddr: CULong, size: SizeT, user_start: CULong, user_end: CULong) -> bool {
    let size = size as CULong;

    !(uaddr < user_start || user_end <= uaddr || user_end.wrapping_sub(uaddr) < size)
}

pub unsafe extern "C" fn x86_verify_process_vm_result(
    vm: *mut c_void,
    uaddr: CULong,
    size: SizeT,
    user_start: CULong,
    user_end: CULong,
    reason: CULong,
    page_fault_fn: Option<X86UserPageFaultFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    if !x86_user_range_valid(uaddr, size, user_start, user_end) {
        if let Some(log) = log_fn {
            unsafe {
                log(X86_USER_COPY_LOG_RANGE, vm, uaddr, size as CULong, -EFAULT);
            }
        }
        return -EFAULT;
    }

    let Some(page_fault) = page_fault_fn else {
        return -EFAULT;
    };

    let uend = uaddr.wrapping_add(size as CULong);
    let mut addr = uaddr & PAGE_MASK;

    while addr < uend {
        if addr == 0 {
            return -EINVAL;
        }

        let error = unsafe { page_fault(vm, addr as *mut c_void, reason) };
        if error != 0 {
            if let Some(log) = log_fn {
                unsafe {
                    log(X86_USER_COPY_LOG_PF, vm, addr, reason, error);
                }
            }
            return error;
        }

        addr = addr.wrapping_add(PTL1_SIZE);
    }

    0
}

unsafe fn x86_process_vm_copy_impl(
    vm: *mut c_void,
    pt: *mut c_void,
    user_addr: CULong,
    kernel_addr: CULong,
    size: SizeT,
    user_start: CULong,
    user_end: CULong,
    reason: CULong,
    direction: CInt,
    page_fault_fn: Option<X86UserPageFaultFn>,
    vtop_fn: Option<X86UserVtopFn>,
    is_memory_fn: Option<X86UserIsMemoryFn>,
    map_fn: Option<X86UserMapFn>,
    unmap_fn: Option<X86UserUnmapFn>,
    phys_to_virt_fn: Option<X86UserPhysToVirtFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    if (reason & PF_PATCH) != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(
                    X86_USER_COPY_LOG_PATCH_START,
                    vm,
                    user_addr,
                    kernel_addr,
                    size as CInt,
                );
            }
        }
    }

    let verify_error = unsafe {
        x86_verify_process_vm_result(
            vm,
            user_addr,
            size,
            user_start,
            user_end,
            reason,
            page_fault_fn,
            log_fn,
        )
    };
    if verify_error != 0 {
        if (reason & PF_PATCH) != 0 {
            if let Some(log) = log_fn {
                let event = if verify_error == -EFAULT {
                    X86_USER_COPY_LOG_PATCH_RANGE
                } else {
                    X86_USER_COPY_LOG_PATCH_PF
                };
                unsafe {
                    log(event, vm, user_addr, size as CULong, verify_error);
                }
            }
        }
        return verify_error;
    }

    let (Some(vtop), Some(is_memory), Some(map), Some(unmap), Some(phys_to_virt)) =
        (vtop_fn, is_memory_fn, map_fn, unmap_fn, phys_to_virt_fn)
    else {
        return -EFAULT;
    };

    let mut user_cursor = user_addr;
    let mut kernel_cursor = kernel_addr;
    let mut remain = size as CULong;

    while remain > 0 {
        let mut cpsize = PTL1_SIZE - (user_cursor & (PTL1_SIZE - 1));
        if cpsize > remain {
            cpsize = remain;
        }

        let mut pa = 0;
        let error = unsafe { vtop(pt, user_cursor as *const c_void, &mut pa) };
        if error != 0 {
            if let Some(log) = log_fn {
                let event = if (reason & PF_PATCH) != 0 {
                    X86_USER_COPY_LOG_PATCH_VTOP
                } else {
                    X86_USER_COPY_LOG_VTOP
                };
                unsafe {
                    log(event, vm, user_cursor, pa, error);
                }
            }
            return error;
        }

        let is_lwk = unsafe { is_memory(pa, pa.wrapping_add(cpsize)) };
        let va = if is_lwk == 0 {
            if let Some(log) = log_fn {
                unsafe {
                    log(X86_USER_COPY_LOG_EXTERNAL, vm, pa, cpsize, 0);
                }
            }
            unsafe { map(pa, 1, PTATTR_ACTIVE) }
        } else {
            unsafe { phys_to_virt(pa) }
        };

        if va.is_null() {
            return -EFAULT;
        }

        if direction == X86_USER_COPY_READ {
            unsafe {
                x86_user_copy_bytes(kernel_cursor as *mut u8, va as *const u8, cpsize as usize);
            }
        } else {
            unsafe {
                x86_user_copy_bytes(va as *mut u8, kernel_cursor as *const u8, cpsize as usize);
            }
        }

        if is_lwk == 0 {
            unsafe {
                unmap(va, 1);
            }
        }

        user_cursor = user_cursor.wrapping_add(cpsize);
        kernel_cursor = kernel_cursor.wrapping_add(cpsize);
        remain -= cpsize;
    }

    if (reason & PF_PATCH) != 0 {
        if let Some(log) = log_fn {
            unsafe {
                log(X86_USER_COPY_LOG_PATCH_DONE, vm, user_addr, kernel_addr, 0);
            }
        }
    }

    0
}

unsafe fn x86_process_vm_page_table(vm: *mut ProcessVm) -> *mut c_void {
    unsafe { (*(*vm).address_space).page_table }
}

pub unsafe extern "C" fn x86_write_process_vm_public_result(
    vm: *mut ProcessVm,
    udst: *mut c_void,
    ksrc: *const c_void,
    size: SizeT,
    page_fault_fn: Option<X86UserPageFaultFn>,
    vtop_fn: Option<X86UserVtopFn>,
    is_memory_fn: Option<X86UserIsMemoryFn>,
    map_fn: Option<X86UserMapFn>,
    unmap_fn: Option<X86UserUnmapFn>,
    phys_to_virt_fn: Option<X86UserPhysToVirtFn>,
    log_fn: Option<X86UserLogFn>,
) -> CInt {
    let page_table = unsafe { x86_process_vm_page_table(vm) };
    let user_start = unsafe { (*vm).region.user_start };
    let user_end = unsafe { (*vm).region.user_end };

    unsafe {
        x86_process_vm_copy_impl(
            vm.cast(),
            page_table,
            udst as CULong,
            ksrc as CULong,
            size,
            user_start,
            user_end,
            PF_POPULATE | PF_WRITE | PF_USER,
            X86_USER_COPY_WRITE,
            page_fault_fn,
            vtop_fn,
            is_memory_fn,
            map_fn,
            unmap_fn,
            phys_to_virt_fn,
            log_fn,
        )
    }
}

pub unsafe extern "C" fn write_process_vm(
    vm: *mut ProcessVm,
    udst: *mut c_void,
    ksrc: *const c_void,
    size: SizeT,
) -> CInt {
    x86_write_process_vm_public_result(
        vm,
        udst,
        ksrc,
        size,
        Some(x86_user_page_fault_bridge),
        Some(x86_user_vtop_bridge),
        Some(x86_user_is_memory_bridge),
        Some(x86_user_map_bridge),
        Some(x86_user_unmap_bridge),
        Some(x86_user_phys_to_virt_bridge),
        Some(x86_user_copy_log_bridge),
    )
}


unsafe extern "C" fn x86_user_page_fault_bridge(vm:*mut c_void,page:*mut c_void,reason:u64)->i32{crate::phase5_tests::tid_fault(vm,page,reason)}
unsafe extern "C" fn x86_user_vtop_bridge(pt:*mut c_void,address:*const c_void,pa:*mut u64)->i32{crate::phase5_tests::tid_vtop(pt,address,pa)}
unsafe extern "C" fn x86_user_is_memory_bridge(start:u64,end:u64)->i32{crate::phase5_tests::tid_memory(start,end)}
unsafe extern "C" fn x86_user_map_bridge(_:u64,_:i32,_:u64)->*mut c_void{panic!("unexpected external mapping")}
unsafe extern "C" fn x86_user_unmap_bridge(_:*mut c_void,_:i32){panic!("unexpected external unmap")}
unsafe extern "C" fn x86_user_phys_to_virt_bridge(pa:u64)->*mut c_void{pa as *mut c_void}
unsafe extern "C" fn x86_user_copy_log_bridge(_:i32,_:*mut c_void,_:u64,_:u64,_:i32){}
