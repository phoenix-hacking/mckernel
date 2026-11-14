// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod f03_util_register_desc_logger_v1 {
    use core::ptr::{addr_of,read_volatile};
    use crate::{abi::{CInt,CULong},debug::Ddebug};
    unsafe extern "C" {static mut f03_util_register_desc_debug_v1:[Ddebug;1];}

    /// Keep the original registration diagnostic without changing registration.
    ///
    /// # Safety
    /// The original debug record remains initialized and live under its existing
    /// update contract. Arguments are copied scalar values; this function does
    /// not resolve the current thread or dereference the descriptor address.
    #[no_mangle]
    pub unsafe extern "C" fn syscall_util_register_desc_log_bridge(tid:CInt,descriptor:CULong) {
        let record=addr_of!(f03_util_register_desc_debug_v1).cast::<Ddebug>();
        // SAFETY: One genuine record, preserving any-nonzero8-bit flag gating.
        let enabled=unsafe{read_volatile(addr_of!((*record).line_flags))>>24!=0};
        if enabled {
            // SAFETY: Exact original function text/format and promoted-int plus
            // unsigned-long varargs. The original logger result is ignored.
            unsafe{super::kprintf(b"%s: tid=%d,uti_desc=%lx\n\0".as_ptr().cast(),
                b"sys_util_register_desc\0".as_ptr().cast::<i8>(),tid,descriptor);}
        }
    }

    #[no_mangle]
    pub static F03_UTIL_DESC_LOG_ABI:[CULong;10]=[
        (core::mem::size_of::<Ddebug>()) as CULong,
        (core::mem::align_of::<Ddebug>()) as CULong,
        (core::mem::offset_of!(Ddebug,file)) as CULong,
        (core::mem::offset_of!(Ddebug,func)) as CULong,
        (core::mem::offset_of!(Ddebug,fmt)) as CULong,
        (core::mem::offset_of!(Ddebug,line_flags)) as CULong,
        (core::mem::size_of::<CInt>()) as CULong,
        (core::mem::size_of::<CULong>()) as CULong,
        (core::mem::size_of::<unsafe extern "C" fn(CInt,CULong)>()) as CULong,
        (1) as CULong
    ];
}
