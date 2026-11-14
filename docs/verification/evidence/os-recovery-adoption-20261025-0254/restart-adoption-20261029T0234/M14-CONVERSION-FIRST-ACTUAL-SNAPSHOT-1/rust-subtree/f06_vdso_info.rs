// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Child of syscall_policy; preserves the selected C vdso_get_vdso_info body.
use super::ArchVdso;
use crate::abi::{CInt, CULong, IkcScdPacket};
use core::ffi::c_void;
use core::mem::{size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, read_volatile, write_bytes, write_volatile};

const GET_VDSO_INFO: CInt = 0xb;
const LOG_ENTER: CInt = 0;
const LOG_PREPARE_FAILED: CInt = 1;
const LOG_SEND_FAILED: CInt = 2;
const LOG_EXIT: CInt = 3;

type Physical = unsafe extern "C" fn(*mut c_void) -> CULong;
type Prepare = unsafe extern "C" fn(*mut IkcScdPacket, CInt, CULong) -> CInt;
type Send = unsafe extern "C" fn(*mut c_void, *mut IkcScdPacket, CInt) -> CInt;
type Pause = unsafe extern "C" fn();
type Log = unsafe extern "C" fn(CInt, CInt);

/// Execute the original reset/request/wait flow with its existing effects.
///
/// # Safety
/// `vdso` is the original live writable 88-byte state allocation; no concurrent
/// setup caller may reset it. `channel` has the original current-CPU lifetime.
/// Send publishes the physical state address to the existing peer. The peer may
/// update that state through the original IKC contract; busy is polled volatile.
/// Callbacks have their original ABI and do not retain the stack packet after
/// send returns. No exclusive Rust reference is formed across a peer/callback.
/// There is deliberately no timeout, extra fence, null policy or error mapping.
/// Only msg and arg of the uninitialized packet are prepared, as in original C.
#[inline]
pub(super) unsafe fn vdso_info_body(
    vdso: *mut ArchVdso,
    channel: *mut c_void,
    physical: Physical,
    prepare: Prepare,
    send: Send,
    pause: Pause,
    log: Log,
) -> CInt {
    // SAFETY: original debug event precedes the complete byte reset.
    unsafe { log(LOG_ENTER, 0) };
    // SAFETY: exact original memset including padding, then busy/pages stores.
    unsafe {
        write_bytes(vdso.cast::<u8>(), 0, size_of::<ArchVdso>());
        write_volatile(addr_of_mut!((*vdso).busy), 1);
        write_volatile(addr_of_mut!((*vdso).vdso_npages), 0);
    }
    let mut packet = MaybeUninit::<IkcScdPacket>::uninit();
    // SAFETY: original helper initializes only the actual sent msg/arg fields.
    let mut error = unsafe {
        prepare(packet.as_mut_ptr(), GET_VDSO_INFO, physical(vdso.cast()))
    };
    if error != 0 {
        unsafe { log(LOG_PREPARE_FAILED, error) };
    } else {
        // SAFETY: unchanged flags0/channel and packet lifetime through send.
        error = unsafe { send(channel, packet.as_mut_ptr(), 0) };
        if error != 0 {
            unsafe { log(LOG_SEND_FAILED, error) };
        } else {
            // SAFETY: exact original volatile completion word; pause retains
            // the existing architecture hint and peer publication semantics.
            while unsafe { read_volatile(addr_of!((*vdso).busy)) } != 0 {
                unsafe { pause() };
            }
        }
    }
    if error != 0 {
        // SAFETY: error path clears only page count, preserving peer bytes.
        unsafe { write_volatile(addr_of_mut!((*vdso).vdso_npages), 0) };
    }
    unsafe { log(LOG_EXIT, error) };
    error
}

#[cfg(not(test))]
unsafe extern "C" fn production_log(event: CInt, error: CInt) {
    use crate::debug::Ddebug;
    #[used]
    #[link_section = "__verbose"]
    static mut ENTER: Ddebug = Ddebug {
        file: concat!(env!("MCKERNEL_F06_RT_SIGRETURN_ORIGIN"), "\0").as_ptr().cast(),
        func: b"vdso_get_vdso_info\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2859,
    };
    #[used]
    #[link_section = "__verbose"]
    static mut EXIT: Ddebug = Ddebug {
        file: concat!(env!("MCKERNEL_F06_RT_SIGRETURN_ORIGIN"), "\0").as_ptr().cast(),
        func: b"vdso_get_vdso_info\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 2887,
    };
    match event {
        LOG_ENTER => {
            if unsafe { read_volatile(addr_of!(ENTER.line_flags)) } >> 24 != 0 {
                unsafe { super::kprintf(b"vdso_get_vdso_info()\n\0".as_ptr().cast()) };
            }
        }
        LOG_PREPARE_FAILED => {
            unsafe { super::kprintf(b"vdso_get_vdso_info: packet prepare failed. %d\n\0".as_ptr().cast(), error) };
        }
        LOG_SEND_FAILED => {
            unsafe { super::kprintf(b"vdso_get_vdso_info: ihk_ikc_send failed. %d\n\0".as_ptr().cast(), error) };
        }
        LOG_EXIT => {
            if unsafe { read_volatile(addr_of!(EXIT.line_flags)) } >> 24 != 0 {
                unsafe { super::kprintf(b"vdso_get_vdso_info(): %d\n\0".as_ptr().cast(), error) };
            }
        }
        _ => {}
    }
}

#[cfg(not(test))]
unsafe extern "C" {
    fn ihk_ikc_send(channel: *mut c_void, packet: *mut IkcScdPacket, flags: CInt) -> CInt;
}

/// Existing public legacy IKC entry, distinct from native_vdso::initialize.
///
/// # Safety
/// Same setup/CPU/IKC lifetime as original C. The existing state bridge returns
/// the persistent C-owned allocation; native Rust's separate initializer remains
/// unchanged and this module introduces no second vdso allocation.
#[cfg(not(test))]
#[no_mangle]
pub unsafe extern "C" fn vdso_get_vdso_info() -> CInt {
    // Original C obtains the current CPU channel before its first debug event.
    let channel = unsafe { (*super::get_this_cpu_local_var()).ikc2linux };
    let mut vdso = core::ptr::null_mut();
    // SAFETY: reviewed state bridge has no effect beyond returning storage.
    unsafe {
        super::arch_vdso_state_bridge(&mut vdso, core::ptr::null_mut(), core::ptr::null_mut());
        vdso_info_body(vdso, channel,
            crate::x86_memory_helpers::virt_to_phys,
            crate::x86_memory_helpers::x86_vdso_packet_prepare_result,
            ihk_ikc_send,
            super::syscall_cpu_pause_bridge,
            production_log)
    }
}
