//! Functional McKernel OS/apps and Rust migration only; no security testing.
//! Private-header and original-source-only contracts; never public ABI claims.
use core::ffi::{c_char, c_int};

const _: unsafe extern "C" fn(c_int) -> c_int = super::accepted_cpu_memory::ihklib_device_open;
const _: unsafe extern "C" fn(c_int) -> c_int = super::ihklib_mcstat::ihklib_os_open;
const _: unsafe extern "C" fn(c_int, *mut c_char, isize, *const c_char) -> c_int = super::ihklib_mcstat_memory::ihklib_os_query_mem_sysfs;
const _: unsafe extern "C" fn(*mut c_char) -> c_int = super::ihklib_cli_parsers::cpu_str2count;
const _: unsafe extern "C" fn(*mut c_char, c_int, *mut super::ihklib_cli_parsers::CpuReq) -> c_int = super::ihklib_cli_parsers::cpu_str2req;
const _: unsafe extern "C" fn(*mut super::ihklib_cli_parsers::CpuReq) -> *mut c_char = super::ihklib_cli_parsers::cpu_req2str;
const _: unsafe extern "C" fn(*mut c_char) -> c_int = super::ihklib_cli_parsers::mem_str2count;
const _: unsafe extern "C" fn(*mut c_char, *mut super::ihklib_cli_parsers::MemReq) -> c_int = super::ihklib_cli_parsers::mem_str2req;
const _: unsafe extern "C" fn(*mut super::ihklib_cli_parsers::MemReq) -> *mut c_char = super::ihklib_cli_parsers::mem_req2str;
const _: unsafe extern "C" fn(*mut c_char) -> c_int = super::ihklib_ikc::ikc_str2count;
const _: unsafe extern "C" fn(*mut c_char, c_int, *mut super::ihklib_ikc::IhkIkcReq) -> c_int = super::ihklib_ikc::ikc_str2req;
const _: unsafe extern "C" fn(*mut super::ihklib_ikc::IhkIkcReq) -> *mut c_char = super::ihklib_ikc::ikc_req2str;
const _: unsafe extern "C" fn(c_int, *mut c_char, *mut c_char) -> c_int = super::raw_strings::_ihk_reserve_cpu_str;
const _: unsafe extern "C" fn(c_int, *mut c_char, *mut c_char) -> c_int = super::raw_strings::_ihk_reserve_mem_str;
const _: unsafe extern "C" fn(c_int, *mut c_char, *mut c_char) -> c_int = super::raw_strings::_ihk_os_assign_cpu_str;
const _: unsafe extern "C" fn(c_int, *mut c_char, *mut c_char) -> c_int = super::raw_strings::_ihk_os_set_ikc_map_str;
const _: unsafe extern "C" fn(*const c_char, c_int, *mut *mut *mut c_char, *mut *mut *mut c_char) -> c_int = super::environment::parse_env;
const _: unsafe extern "C" fn() -> () = super::configuration_report::dump_reserve_mem_conf;

// Check actual definitions without reading or mutating existing ABI storage.
const _: *mut super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf = core::ptr::addr_of_mut!(super::runtime_state::reserve_mem_conf);
const _: *mut [*const c_char; 2] = core::ptr::addr_of_mut!(super::legacy_data::ihklib_os_query_mem_type_str);
const _: *mut c_int = core::ptr::addr_of_mut!(super::legacy_data::__argc);
const _: *mut *mut *mut c_char = core::ptr::addr_of_mut!(super::legacy_data::__argv);
const _: *mut [super::legacy_data::NamespaceFile; 8] = core::ptr::addr_of_mut!(super::legacy_data::namespace_files);

const _: () = {
    assert!(core::mem::size_of::<super::ihklib_ikc::IhkIkcReq>() == 24);
    assert!(core::mem::align_of::<super::ihklib_ikc::IhkIkcReq>() == 8);
    assert!(core::mem::offset_of!(super::ihklib_ikc::IhkIkcReq, src_cpus) == 0);
    assert!(core::mem::offset_of!(super::ihklib_ikc::IhkIkcReq, dst_cpus) == 8);
    assert!(core::mem::offset_of!(super::ihklib_ikc::IhkIkcReq, num_cpus) == 16);
};
const _: fn(&super::ihklib_ikc::IhkIkcReq) = |value| {
    let _: &*mut c_int = &value.src_cpus;
    let _: &*mut c_int = &value.dst_cpus;
    let _: &c_int = &value.num_cpus;
};

const _: () = {
    assert!(core::mem::size_of::<super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf>() == 24);
    assert!(core::mem::align_of::<super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf>() == 4);
    assert!(core::mem::offset_of!(super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf, balanced_enable) == 0);
    assert!(core::mem::offset_of!(super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf, balanced_best_effort) == 4);
    assert!(core::mem::offset_of!(super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf, balanced_variance_limit) == 8);
    assert!(core::mem::offset_of!(super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf, min_chunk_size) == 12);
    assert!(core::mem::offset_of!(super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf, max_size_ratio_all) == 16);
    assert!(core::mem::offset_of!(super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf, timeout) == 20);
};
const _: fn(&super::accepted_cpu_memory::ihklib_memory_os::ReserveMemConf) = |value| {
    let _: &c_int = &value.balanced_enable;
    let _: &c_int = &value.balanced_best_effort;
    let _: &c_int = &value.balanced_variance_limit;
    let _: &c_int = &value.min_chunk_size;
    let _: &c_int = &value.max_size_ratio_all;
    let _: &c_int = &value.timeout;
};

const _: () = {
    assert!(core::mem::size_of::<super::legacy_data::NamespaceFile>() == 24);
    assert!(core::mem::align_of::<super::legacy_data::NamespaceFile>() == 8);
    assert!(core::mem::offset_of!(super::legacy_data::NamespaceFile, nstype) == 0);
    assert!(core::mem::offset_of!(super::legacy_data::NamespaceFile, name) == 8);
    assert!(core::mem::offset_of!(super::legacy_data::NamespaceFile, fd) == 16);
};
const _: fn(&super::legacy_data::NamespaceFile) = |value| {
    let _: &c_int = &value.nstype;
    let _: &*const c_char = &value.name;
    let _: &c_int = &value.fd;
};
