// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete selected VDSO setup event logger; retain existing kprintf implementation.
use crate::abi::CInt;

const GET_INFO_FAILED: CInt = 1;
const LOCAL_GETTIME_DISABLED: CInt = 2;
const VDSO_DISABLED: CInt = 3;
const MAP_GLOBAL_FAILED: CInt = 4;

unsafe extern "C" {
    fn kprintf(format: *const i8, ...) -> CInt;
}

/// Preserve exact original event selection, message bytes and int32 arguments.
/// All format pointers name immutable static NUL-terminated bytes; the two %d
/// arguments have the genuine promoted C int type. Existing kprintf retains its
/// synchronization and output ownership. Its result is ignored exactly as C.
#[no_mangle]
pub extern "C" fn arch_vdso_setup_log_bridge(event: CInt, error: CInt) {
    // SAFETY: static format lifetimes and exact C variadic int32 argument ABI.
    unsafe {
        match event {
            GET_INFO_FAILED => {
                kprintf(b"arch_setup_vdso: vdso_get_vdso_info failed. %d\n\0".as_ptr().cast(), error);
            }
            LOCAL_GETTIME_DISABLED => {
                kprintf(b"x86 local gettime disabled: host vgtod data unavailable\n\0".as_ptr().cast());
            }
            VDSO_DISABLED => {
                kprintf(b"vdso disabled: host vgtod data unavailable\n\0".as_ptr().cast());
            }
            MAP_GLOBAL_FAILED => {
                kprintf(b"arch_setup_vdso: vdso_map_global_pages failed. %d\n\0".as_ptr().cast(), error);
            }
            _ => {}
        }
    }
}
