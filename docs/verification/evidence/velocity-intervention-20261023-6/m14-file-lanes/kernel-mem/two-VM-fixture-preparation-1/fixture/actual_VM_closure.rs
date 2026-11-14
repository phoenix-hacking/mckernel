#![no_std]
#![allow(dead_code)]
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong,ProcessVm,AddressSpace};
use core::{ffi::c_void,mem::offset_of,ptr::null_mut};
type MemLookupPteFn=unsafe extern "C" fn(*mut c_void,*mut c_void,CInt,*mut *mut c_void,*mut usize,*mut CInt)->*mut CULong;
type MemPageFaultProcessVmFn=unsafe extern "C" fn(*mut c_void,*mut c_void,CULong)->CInt;
type MemFaultLogFn=unsafe extern "C" fn(*mut c_void);
type MemPhysToNidFn=unsafe extern "C" fn(CULong)->CInt;
const EINVAL:CInt=22;const ENOENT:CInt=2;const PAGE_SIZE:CULong=4096;
const PTATTR_ACTIVE:CULong=1;const PT_PHYSMASK:CULong=((1u64<<52)-1)&!(PAGE_SIZE-1);
const PF_USER:CULong=1<<2;const PF_POPULATE:CULong=1<<30;
unsafe extern "C" {
 fn ihk_mc_pt_lookup_pte(pt:*mut c_void,virt:*mut c_void,pgshift:CInt,basep:*mut *mut c_void,sizep:*mut usize,p2alignp:*mut CInt)->*mut CULong;
 fn page_fault_process_vm(vm:*mut c_void,virt:*mut c_void,reason:CULong)->CInt;
 fn phys_to_nid(phys:CULong)->CInt;
 fn kprintf(format:*const i8,...)->CInt;
}

unsafe fn mem_vm_page_table(
    vm: *mut c_void,
    address_space_offset: CULong,
    page_table_offset: CULong,
) -> *mut c_void {
    if vm.is_null() {
        return null_mut();
    }

    let address_space = *(vm
        .cast::<u8>()
        .add(address_space_offset as usize)
        .cast::<*mut c_void>());
    if address_space.is_null() {
        return null_mut();
    }

    *(address_space
        .cast::<u8>()
        .add(page_table_offset as usize)
        .cast::<*mut c_void>())
}

#[no_mangle]
pub unsafe extern "C" fn mem_lookup_node_body_result(
    vm: *mut c_void,
    addr: *mut c_void,
    address_space_offset: CULong,
    page_table_offset: CULong,
    lookup_pte_fn: Option<MemLookupPteFn>,
    page_fault_fn: Option<MemPageFaultProcessVmFn>,
    phys_to_nid_fn: Option<MemPhysToNidFn>,
) -> CInt {
    let (Some(lookup_pte), Some(page_fault), Some(phys_to_nid_cb)) =
        (lookup_pte_fn, page_fault_fn, phys_to_nid_fn)
    else {
        return -EINVAL;
    };

    let err = page_fault(vm, addr, PF_POPULATE | PF_USER);
    if err != 0 {
        return err;
    }

    let page_table = mem_vm_page_table(vm, address_space_offset, page_table_offset);
    if page_table.is_null() {
        return -ENOENT;
    }

    let ptep = lookup_pte(page_table, addr, 0, null_mut(), null_mut(), null_mut());
    if ptep.is_null() || (*ptep & PTATTR_ACTIVE) == 0 {
        return -ENOENT;
    }

    phys_to_nid_cb(*ptep & PT_PHYSMASK)
}

#[no_mangle]
pub unsafe extern "C" fn mem_pt_lookup_fault_pte_body_result(
    vm: *mut c_void,
    virt: *mut c_void,
    pgshift: CInt,
    basep: *mut *mut c_void,
    sizep: *mut usize,
    p2alignp: *mut CInt,
    address_space_offset: CULong,
    page_table_offset: CULong,
    lookup_pte_fn: Option<MemLookupPteFn>,
    page_fault_fn: Option<MemPageFaultProcessVmFn>,
    log_fn: Option<MemFaultLogFn>,
) -> *mut CULong {
    let (Some(lookup_pte), Some(page_fault)) = (lookup_pte_fn, page_fault_fn) else {
        return null_mut();
    };

    let page_table = mem_vm_page_table(vm, address_space_offset, page_table_offset);
    if page_table.is_null() {
        return null_mut();
    }

    let mut ptep = lookup_pte(page_table, virt, pgshift, basep, sizep, p2alignp);
    if ptep.is_null() || (*ptep & PTATTR_ACTIVE) == 0 {
        page_fault(vm, virt, PF_POPULATE | PF_USER);
        ptep = lookup_pte(page_table, virt, pgshift, basep, sizep, p2alignp);
        if !ptep.is_null() && (*ptep & PTATTR_ACTIVE) != 0 {
            if let Some(log) = log_fn {
                log(virt);
            }
        }
    }

    ptep
}

#[no_mangle]
pub unsafe extern "C" fn lookup_node(vm: *mut ProcessVm, addr: *mut c_void) -> CInt {
    unsafe {
        mem_lookup_node_body_result(
            vm.cast(), addr,
            offset_of!(ProcessVm, address_space) as CULong,
            offset_of!(AddressSpace, page_table) as CULong,
            Some(ihk_mc_pt_lookup_pte), Some(page_fault_process_vm), Some(phys_to_nid),
        )
    }
}

unsafe extern "C" fn mem_lookup_fault_log_bridge(virt: *mut c_void) {
    unsafe {
        kprintf(
            b"%s: successfully faulted 0x%lx\n\0".as_ptr().cast(),
            b"ihk_mc_pt_lookup_fault_pte\0".as_ptr().cast::<i8>(),
            virt as CULong,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_pt_lookup_fault_pte(
    vm: *mut ProcessVm, virt: *mut c_void, pgshift: CInt,
    basep: *mut *mut c_void, sizep: *mut usize, p2alignp: *mut CInt,
) -> *mut CULong {
    unsafe {
        mem_pt_lookup_fault_pte_body_result(
            vm.cast(), virt, pgshift, basep, sizep, p2alignp,
            offset_of!(ProcessVm, address_space) as CULong,
            offset_of!(AddressSpace, page_table) as CULong,
            Some(ihk_mc_pt_lookup_pte), Some(page_fault_process_vm),
            Some(mem_lookup_fault_log_bridge),
        )
    }
}

#[no_mangle]
pub static F01_VM_ACTUAL_LAYOUT:[usize;8]=[
 core::mem::offset_of!(ProcessVm,address_space),core::mem::offset_of!(AddressSpace,page_table),
 core::mem::size_of::<CULong>(),core::mem::size_of::<CInt>(),
 PTATTR_ACTIVE as usize,PT_PHYSMASK as usize,PF_USER as usize,PF_POPULATE as usize,
];
