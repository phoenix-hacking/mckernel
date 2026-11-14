// Functional OS/apps and Rust migration only; no security testing.
// Layout only, not a fabricated IKC implementation/provider.
#[repr(C)]
struct IhkIkcReq {src_cpus:*mut core::ffi::c_int,dst_cpus:*mut core::ffi::c_int,num_cpus:core::ffi::c_int}
const _:()={assert!(core::mem::size_of::<IhkIkcReq>()==24);assert!(core::mem::offset_of!(IhkIkcReq,num_cpus)==16);};
// ikc_str2count/ikc_str2req/ikc_req2str and ENABLE_MEMDUMP ihk_os_makedumpfile
// remain genuine C exports in current partial library. No dummy functions are defined.
