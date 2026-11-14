//! Functional McKernel OS/apps and Rust migration only; no security testing.
//! Remaining actual public exports: compile-time types only, no runtime provider.
use core::ffi::{c_char, c_int, c_long, c_ulong, c_void};

// The actual selected C enum is compatible with unsigned int.
// Use its scalar representation without restricting existing caller values.
type IhkLogLevel = core::ffi::c_uint;

const _: unsafe extern "C" fn(c_int, *mut c_int, c_int) -> c_int = super::accepted_cpu_memory::ihk_reserve_cpu;
const _: unsafe extern "C" fn(c_int, *const c_char, c_int) -> c_int = super::environment::ihk_reserve_cpu_str;
const _: unsafe extern "C" fn(c_int) -> c_int = super::accepted_cpu_memory::ihk_get_num_reserved_cpus;
const _: unsafe extern "C" fn(c_int, *mut c_int, c_int) -> c_int = super::accepted_cpu_memory::ihk_query_cpu;
const _: unsafe extern "C" fn(c_int, *mut c_int, c_int) -> c_int = super::accepted_cpu_memory::ihk_release_cpu;
const _: unsafe extern "C" fn(c_int, c_int, *mut c_void) -> c_int = super::runtime_state::ihk_reserve_mem_conf;
const _: unsafe extern "C" fn(c_int, *const c_char, c_int) -> c_int = super::environment::ihk_reserve_mem_conf_str;
const _: unsafe extern "C" fn(c_int, *const c_char, c_int) -> c_int = super::environment::ihk_reserve_mem_str;
const _: unsafe extern "C" fn(c_int) -> c_int = super::accepted_cpu_memory::ihklib_memory_os::ihk_get_num_reserved_mem_chunks;
const _: unsafe extern "C" fn(c_int) -> c_int = super::os_instances::ihk_create_os;
const _: unsafe extern "C" fn(c_int) -> c_int = super::accepted_cpu_memory::ihklib_memory_os::ihk_get_num_os_instances;
const _: unsafe extern "C" fn(c_int, *mut c_int, c_int) -> c_int = super::accepted_cpu_memory::ihklib_memory_os::ihk_get_os_instances;
const _: unsafe extern "C" fn(c_int, c_int) -> c_int = super::os_instances::ihk_destroy_os;
const _: unsafe extern "C" fn(c_int, *mut c_int, c_int) -> c_int = super::os_cpu::ihk_os_assign_cpu;
const _: unsafe extern "C" fn(c_int, *const c_char, c_int) -> c_int = super::environment::ihk_os_assign_cpu_str;
const _: unsafe extern "C" fn(c_int) -> c_int = super::os_cpu::ihk_os_get_num_assigned_cpus;
const _: unsafe extern "C" fn(c_int, *mut c_int, c_int) -> c_int = super::os_cpu::ihk_os_query_cpu;
const _: unsafe extern "C" fn(c_int, *mut c_int, c_int) -> c_int = super::os_cpu::ihk_os_release_cpu;
const _: unsafe extern "C" fn(c_int, *const c_char, c_int) -> c_int = super::environment::ihk_os_set_ikc_map_str;
const _: unsafe extern "C" fn(c_int) -> c_int = super::accepted_cpu_memory::ihklib_memory_os::ihk_os_get_num_assigned_mem_chunks;
const _: unsafe extern "C" fn(c_int, c_int) -> c_int = super::owned_eventfd::ihk_os_get_eventfd;
const _: unsafe extern "C" fn(c_int, *mut c_char) -> c_int = super::os_load_boot::ihk_os_load;
const _: unsafe extern "C" fn(c_int, *mut c_char) -> c_int = super::os_kargs::ihk_os_kargs;
const _: unsafe extern "C" fn(c_int, *const c_char, c_int, *const c_char) -> c_int = super::environment::ihk_os_kargs_str;
const _: unsafe extern "C" fn(c_int, *mut c_int, *const c_char, c_int, *const c_char, *const c_char, *mut c_char) -> c_int = super::create_os_environment::ihk_create_os_str;
const _: unsafe extern "C" fn(c_int) -> c_int = super::os_load_boot::ihk_os_boot;
const _: unsafe extern "C" fn(c_int) -> c_int = super::shutdown_freeze::ihk_os_shutdown;
const _: unsafe extern "C" fn(c_int) -> c_int = super::ihklib_status_kmsg::ihk_os_get_status;
const _: unsafe extern "C" fn(c_int) -> c_int = super::kmsg_control::ihk_os_get_kmsg_size;
const _: unsafe extern "C" fn(c_int, *mut c_char, isize) -> c_int = super::ihklib_status_kmsg::ihk_os_kmsg;
const _: unsafe extern "C" fn(c_int) -> c_int = super::kmsg_control::ihk_os_clear_kmsg;
const _: unsafe extern "C" fn(c_int) -> c_int = super::ihklib_mcstat::ihk_os_get_num_numa_nodes;
const _: unsafe extern "C" fn(c_int, *mut c_ulong, c_int) -> c_int = super::ihklib_mcstat_memory::ihk_os_query_free_mem;
const _: unsafe extern "C" fn(c_int, *mut c_ulong, c_int) -> c_int = super::ihklib_mcstat_memory::ihk_os_query_total_mem;
const _: unsafe extern "C" fn(c_int) -> c_int = super::perf_pages::ihk_os_get_num_pagesizes;
const _: unsafe extern "C" fn(c_int, *mut c_long, c_int) -> c_int = super::perf_pages::ihk_os_get_pagesizes;
// ihk_perf_event_attr is intentionally opaque here: Rust forwards this
// pointer unchanged and never constructs, copies or dereferences the bitfields.
const _: unsafe extern "C" fn(c_int, *mut c_void, c_int) -> c_int = super::perf_pages::ihk_os_setperfevent;
const _: unsafe extern "C" fn(c_int, c_int) -> c_int = super::perf_pages::ihk_os_perfctl;
const _: unsafe extern "C" fn(c_int, *mut c_ulong, c_int) -> c_int = super::perf_pages::ihk_os_getperfevent;
const _: unsafe extern "C" fn(*mut c_ulong, c_int) -> c_int = super::shutdown_freeze::ihk_os_freeze;
const _: unsafe extern "C" fn(*mut c_ulong, c_int) -> c_int = super::shutdown_freeze::ihk_os_thaw;
const _: unsafe extern "C" fn(c_int, *mut c_char, c_int, c_int) -> c_int = super::dump_correctness::ihk_os_makedumpfile;
const _: unsafe extern "C" fn(IhkLogLevel) -> c_int = super::runtime_state::ihk_set_loglevel;

// Bind the actual externally writable public data definition, with no read/write.
const _: *mut c_int = core::ptr::addr_of_mut!(super::runtime_state::loglevel);
