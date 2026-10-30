// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Approved defined contract: event 4 logs the result's low 32 bits as unsigned hex.
    use crate::abi::CInt;
    use crate::debug::Ddebug;
    use core::ptr::addr_of;

    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    static mut f03_ptrace_wakeup_log_debug_v1: [Ddebug; 1] = [Ddebug {
        file: b"/src/kernel/syscall.c\0".as_ptr().cast(),
        func: b"ptrace_wakeup_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(), line_flags: 24429,
    }];

    /// Emit the event-4 diagnostic under the proposed defined hexadecimal ABI.
    ///
    /// # Safety
    /// The original C caller's logging/CPU context must remain valid. The review
    /// must bind the static ddebug identity and the logger's callable ABI.
    #[no_mangle]
    pub unsafe extern "C" fn ptrace_wakeup_log_bridge(event: CInt, value: CInt, result: CInt) {
        if event == 4 {
            // SAFETY: The original writable ddebug flag is read before emission;
            // passing u32 gives `%x` its defined unsigned-int variadic domain.
            unsafe {
                if core::ptr::read_volatile(addr_of!(f03_ptrace_wakeup_log_debug_v1[0].line_flags)) >> 24 != 0 {
                    super::kprintf(c"ptrace_wakeup_sig,pid=%d,data=%08x\n".as_ptr(),
                        value, result as u32);
                }
            }
        }
    }

const _: unsafe extern "C" fn(CInt, CInt, CInt) = ptrace_wakeup_log_bridge;
