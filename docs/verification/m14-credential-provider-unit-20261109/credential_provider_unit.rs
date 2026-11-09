#![no_std]
// Actual current credential getter partition only; no provider implementations.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
use abi::{CInt, CLong, CULong, SizeT, SyscallRequest};
use core::ffi::c_void;
use core::mem::MaybeUninit;
use core::ptr::{null_mut, write};

const EINVAL: CInt = 22;
const EFAULT: CInt = 14;
const PAGE_SIZE: CULong = 1 << 12;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);
const SYS_SETFSUID: CInt = 122;

type SyscallRequestCallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;
type SyscallVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type SyscallGetcredFn = unsafe extern "C" fn(*mut CInt) -> *mut CInt;
type SyscallGetCpuFn = unsafe extern "C" fn() -> CInt;

unsafe extern "C" {
    fn syscall_virt_to_phys_bridge(addr: *mut c_void) -> CULong;
    fn syscall_get_processor_id_bridge() -> CInt;
    fn syscall_do_syscall_request_bridge(
        request: *mut SyscallRequest,
        cpu: CInt,
    ) -> CLong;
}

#[no_mangle]
pub unsafe extern "C" fn getcred_body_result(
    raw_buf: *mut CInt,
    page_mask: CULong,
    syscall_nr: CInt,
    virt_to_phys_fn: Option<SyscallVirtToPhysFn>,
    processor_id_fn: Option<SyscallGetCpuFn>,
    do_syscall_fn: Option<SyscallRequestCallFn>,
) -> *mut CInt {
    if raw_buf.is_null() {
        return null_mut();
    }
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return null_mut();
    };
    let Some(processor_id) = processor_id_fn else {
        return null_mut();
    };
    let Some(do_syscall) = do_syscall_fn else {
        return null_mut();
    };

    // The existing caller supplies sixteen writable CInt slots. Initialize
    // both possible eight-int spans; only a successful genuine producer grants
    // permission to consume the selected span. Zero fill is not completion proof.
    core::ptr::write_bytes(raw_buf, 0, 16);
    let alternate_buf = raw_buf.add(8);
    let selected_buf = if ((raw_buf as CULong) ^ (alternate_buf as CULong)) & page_mask != 0 {
        alternate_buf
    } else {
        raw_buf
    };

    let mut request = MaybeUninit::<SyscallRequest>::zeroed();
    let requestp = request.as_mut_ptr();
    (*requestp).number = syscall_nr as CULong;
    (*requestp).args[0] = virt_to_phys(selected_buf.cast::<c_void>());
    (*requestp).args[1] = 1;
    if do_syscall(requestp, processor_id()) != 0 {
        // A failed/partial response is not a credential snapshot. The existing
        // refresh helper checks NULL before reading scratch or writing fields.
        return null_mut();
    }

    selected_buf
}

#[no_mangle]
pub unsafe extern "C" fn syscall_refresh_cred_fields_body_result(
    thread: *mut c_void,
    scratch: *mut CInt,
    thread_proc_offset: SizeT,
    field0_offset: SizeT,
    field1_offset: SizeT,
    field2_offset: SizeT,
    field3_offset: SizeT,
    value0_index: SizeT,
    value1_index: SizeT,
    value2_index: SizeT,
    value3_index: SizeT,
    getcred_fn: Option<SyscallGetcredFn>,
) -> CInt {
    if thread.is_null() || scratch.is_null() {
        return -EFAULT;
    }
    let Some(getcred) = getcred_fn else {
        return -EINVAL;
    };
    let values = getcred(scratch);
    if values.is_null() {
        return -EFAULT;
    }

    let proc = *(thread
        .cast::<u8>()
        .add(thread_proc_offset)
        .cast::<*mut c_void>());
    if proc.is_null() {
        return -EFAULT;
    }
    let proc_bytes = proc.cast::<u8>();
    write(
        proc_bytes.add(field0_offset).cast::<CInt>(),
        *values.add(value0_index),
    );
    write(
        proc_bytes.add(field1_offset).cast::<CInt>(),
        *values.add(value1_index),
    );
    write(
        proc_bytes.add(field2_offset).cast::<CInt>(),
        *values.add(value2_index),
    );
    write(
        proc_bytes.add(field3_offset).cast::<CInt>(),
        *values.add(value3_index),
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn getcred(raw_buf: *mut CInt) -> *mut CInt {
    // SAFETY: Reuse the exact existing selected algorithm, including its full
    // zeroed request and page-span choice. Scratch is initialized before the
    // synchronous call and nonzero completion returns no snapshot. The three
    // existing adapters resolve to genuine mapping/CPU/do_syscall.
    unsafe {
        getcred_body_result(
            raw_buf, PAGE_MASK, SYS_SETFSUID,
            Some(syscall_virt_to_phys_bridge), Some(syscall_get_processor_id_bridge),
            Some(syscall_do_syscall_request_bridge),
        )
    }
}
