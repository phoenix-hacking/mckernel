//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
mod abi;
use abi::{CInt,CULong,ProcessVm,VmRange};use core::ffi::c_void;
use core::mem::{size_of,align_of,offset_of};
const EFAULT:CInt=14;const ENOMEM:CInt=12;
extern "C" {fn kprintf(format:*const i8,...)->CInt;}
mod rbtree {include!("rbtree.inc");}
mod lock_helpers {include!("lock.inc");}
mod process_helpers {include!("process.inc");}
mod string {include!("string.inc");}
mod mem_helpers {include!("mem.inc");}
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
/// # Safety
/// vm and its memory_range_lock/range tree retain the original current-thread
/// ownership contract. The range pointer is used only under the same reader lock;
/// no reference or range ownership escapes. filename is converted to address only.
#[no_mangle]
pub unsafe extern "C" fn f03_execveat_filename_admission_v1(
    vm: *mut ProcessVm, filename: *const c_void,
) -> CInt {
    let lock = addr_of_mut!((*vm).memory_range_lock)
        .cast::<crate::lock_helpers::IhkRwSpinlock>();
    crate::lock_helpers::ihk_rwspinlock_read_lock_noirq(lock);
    let start = filename as CULong;
    let range = crate::process_helpers::lookup_process_memory_range(
        vm, start, start.wrapping_add(1),
    );
    if range.is_null() || ((*range).flag & 0x0001_0000) == 0 {
        crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(lock);
        kprintf(c"execve(): ERROR: filename is bad address\n".as_ptr().cast());
        return -EFAULT;
    }
    crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(lock);
    0
}
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
/// # Safety
/// file is the original static C source string; source_line identifies the bound
/// allocation origin. error points to the live C local, written only on failure.
/// Genuine tracked allocator owns initialization; on success the caller receives
/// exactly four owned kernel pages, all zeroed before return. No context/request
/// fields are touched and no ownership escapes on allocation failure.
#[no_mangle]
pub unsafe extern "C" fn f03_execveat_allocate_descriptor_v1(
    file: *const i8, source_line: CInt, error: *mut CInt,
) -> *mut c_void {
    let descriptor = crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
        4, 0, 0x000002, -1, 0, CULong::MAX, file.cast_mut(), source_line,
    );
    if descriptor.is_null() {
        kprintf(c"execve(): ERROR: allocating program descriptor\n".as_ptr().cast());
        core::ptr::write(error, -ENOMEM);
        return descriptor;
    }
    crate::string::memset(descriptor, 0, 4 * 4096);
    descriptor
}

#[no_mangle] pub unsafe extern "C" fn f03_admission_descriptor_layout(out:*mut usize)->usize {
 let v=[size_of::<ProcessVm>(),align_of::<ProcessVm>(),offset_of!(ProcessVm,memory_range_lock),offset_of!(ProcessVm,vm_range_tree),offset_of!(ProcessVm,range_cache),offset_of!(ProcessVm,range_cache_ind),size_of::<VmRange>(),align_of::<VmRange>(),offset_of!(VmRange,vm_rb_node),offset_of!(VmRange,start),offset_of!(VmRange,end),offset_of!(VmRange,flag),size_of::<abi::IhkRwSpinlock>(),size_of::<abi::IhkSpinlock>(),size_of::<abi::IhkAtomic>(),size_of::<abi::AbiListHead>()];core::ptr::copy_nonoverlapping(v.as_ptr(),out,v.len());v.len()
}
