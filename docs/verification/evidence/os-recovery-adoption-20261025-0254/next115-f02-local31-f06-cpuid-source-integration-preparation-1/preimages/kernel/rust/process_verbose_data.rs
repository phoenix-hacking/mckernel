// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Typed process.c dynamic-debug storage. C selectors and build inputs are paired.
//! The registry owns flag changes; callers continue to use existing raw pointers.
use crate::debug::Ddebug;

const INITIAL_FLAGS: u32 = match env!("MCKERNEL_PROCESS_DDEBUG_FLAGS").as_bytes() {
    b"0" => 0,
    b"1" => 1,
    _ => panic!("process debug flags must match C DDEBUG_DEFAULT (0 or 1)"),
};
const SOURCE_FILE: &[u8] = concat!(env!("MCKERNEL_PROCESS_C_FILE"), "\0").as_bytes();
const _: () = assert!(
    SOURCE_FILE.len() > 1,
    "process C filename must not be empty"
);

// Literal C identities, never Rust file!()/line!(). All original fmt fields are NULL.
macro_rules! record {
    ($function:literal, $line:literal) => {
        Ddebug {
            file: SOURCE_FILE.as_ptr().cast(),
            func: concat!($function, "\0").as_ptr().cast(),
            fmt: core::ptr::null(),
            line_flags: $line | (INITIAL_FLAGS << 24),
        }
    };
}

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_ptrace_traceme_debug: [Ddebug; 3] = [
    record!("process_ptrace_traceme_log_bridge", 236),
    record!("process_ptrace_traceme_log_bridge", 240),
    record!("process_ptrace_traceme_log_bridge", 243),
];

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_create_cpu_debug: Ddebug = record!("process_create_cpu_log_bridge", 276);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_sched_migrate_debug: Ddebug =
    record!("process_sched_migrate_log_bridge", 422);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_remaining_range_debug: [Ddebug; 8] = [
    record!("process_split_range_public_log_bridge", 1689),
    record!("process_split_range_public_log_bridge", 1693),
    record!("process_join_range_log_bridge", 1825),
    record!("process_join_range_log_bridge", 1830),
    record!("process_flush_memory_debug_bridge", 2018),
    record!("process_flush_memory_debug_bridge", 2020),
    record!("process_remove_range_log_bridge", 2050),
    record!("process_remove_range_log_bridge", 2064),
];

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_free_range_body_debug: [Ddebug; 3] = [
    record!("process_free_range_log_bridge", 1947),
    record!("process_free_range_log_bridge", 1955),
    record!("free_process_memory_range", 1964),
];

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_vm_range_insert_debug: Ddebug = record!("vm_range_insert_log_bridge", 2086);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_remaining_range_scheduler_debug: [Ddebug; 18] = [
    record!("process_range_public_log_bridge", 2137),
    record!("process_range_public_log_bridge", 2141),
    record!("process_range_public_log_bridge", 2147),
    record!("process_range_public_log_bridge", 2151),
    record!("process_range_public_log_bridge", 2157),
    record!("process_range_public_log_bridge", 2161),
    record!("process_range_public_log_bridge", 2167),
    record!("process_range_public_log_bridge", 2173),
    record!("process_sched_runq_log_bridge", 4348),
    record!("process_sched_runq_log_bridge", 4357),
    record!("process_sched_runq_log_bridge", 4361),
    record!("process_sched_runq_log_bridge", 4368),
    record!("process_sched_runq_log_bridge", 4374),
    record!("process_sched_runq_log_bridge", 4382),
    record!("process_sched_runq_log_bridge", 4390),
    record!("process_sched_runq_log_bridge", 4398),
    record!("process_sched_runq_log_bridge", 4413),
    record!("process_sched_do_migrate_log_bridge", 489),
];

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_remaining_memory_log_debug: [Ddebug; 5] = [
    record!("process_add_range_log_bridge", 2318),
    record!("process_change_prot_public_log_bridge", 2400),
    record!("process_change_prot_public_log_bridge", 2411),
    record!("process_memset_smp_log_bridge", 2207),
    record!("process_remove_region_log_bridge", 3471),
];

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_remap_one_page_entry_debug: Ddebug = record!("remap_one_page", 2448);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_remap_one_page_rss_debug: Ddebug = record!("remap_one_page", 2470);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_remap_one_page_exit_debug: Ddebug = record!("remap_one_page", 2476);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_sync_one_page_entry_debug: Ddebug = record!("sync_one_page", 2546);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_sync_one_page_exit_debug: Ddebug = record!("sync_one_page", 2574);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_profile_path_debug: Ddebug =
    record!("page_fault_process_memory_range", 2952);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_entry_debug: Ddebug =
    record!("page_fault_process_memory_range", 2959);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_pte_state_debug: Ddebug =
    record!("page_fault_process_memory_range", 3006);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_page_state_debug: Ddebug =
    record!("page_fault_process_memory_range", 3219);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_prepare_bounds_debug: Ddebug =
    record!("page_fault_process_memory_range", 2873);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_cow_rss_add_debug: Ddebug =
    record!("page_fault_process_memory_range", 3071);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_cow_rss_sub_debug: Ddebug =
    record!("page_fault_process_memory_range", 3076);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_set_pte_rss_add_debug: Ddebug =
    record!("page_fault_process_memory_range", 3118);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_set_pte_rss_skip_debug: Ddebug =
    record!("page_fault_process_memory_range", 3121);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_set_pte_attr_debug: Ddebug =
    record!("page_fault_process_memory_range", 3125);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_out_stray_debug: Ddebug =
    record!("page_fault_process_memory_range", 3202);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_out_rss_sub_debug: Ddebug =
    record!("page_fault_process_memory_range", 3206);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_out_return_debug: Ddebug =
    record!("page_fault_process_memory_range", 3210);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_anon_clear_debug: Ddebug =
    record!("page_fault_process_memory_range", 3059);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_anon_map_debug: Ddebug =
    record!("page_fault_process_memory_range", 3067);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_page_fault_cow_copy_debug: Ddebug =
    record!("page_fault_process_memory_range", 3151);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_init_stack_log_size_debug: Ddebug =
    record!("process_init_stack_log_bridge", 3430);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_init_stack_log_ap_user_debug: Ddebug =
    record!("process_init_stack_log_bridge", 3435);

#[no_mangle]
#[used]
#[link_section = "__verbose"]
pub static mut process_schedule_switch_debug: Ddebug = record!("schedule", 4684);

// Not selected by CMake. Enable only with Rust companion configs and paired C
// suppression of their original descriptors. Rust visibility does not export ELF
// locals; linkage="internal" keeps their original names local to this object.
#[cfg(process_verbose_local_companions)]
compile_error!("C-local debug storage requires coordinated companion config migration");

#[cfg(process_verbose_local_companions)]
pub(crate) mod local {
    use super::{Ddebug, INITIAL_FLAGS, SOURCE_FILE};

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_clone_vm_debug: Ddebug = record!("clone_thread", 1098);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_clone_ranges_debug: Ddebug = record!("clone_thread", 1118);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_clone_ranges_ok_debug: Ddebug = record!("clone_thread", 1176);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_clone_sigcommon_debug: Ddebug = record!("clone_thread", 1193);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_clone_sigshared_debug: Ddebug = record!("clone_thread", 1208);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_copy_pte_found_debug: Ddebug = record!("copy_user_pte", 1460);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_copy_pte_size_debug: Ddebug = record!("copy_user_pte", 1461);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_copy_pte_allocated_debug: Ddebug = record!("copy_user_pte", 1471);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_copy_pte_zeroed_debug: Ddebug = record!("copy_user_pte", 1494);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_copy_pte_copied_debug: Ddebug = record!("copy_user_pte", 1496);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_copy_pte_installed_debug: Ddebug = record!("copy_user_pte", 1514);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_extend_region_exists_debug: Ddebug =
        record!("extend_process_region", 3394);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_extend_region_alloc_debug: Ddebug =
        record!("extend_process_region", 3411);

    #[no_mangle]
    #[used]
    #[link_section = "__verbose"]
    #[linkage = "internal"]
    pub(crate) static mut process_extend_region_success_debug: Ddebug =
        record!("extend_process_region", 3428);
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};
    assert!(size_of::<Ddebug>() == 32);
    assert!(align_of::<Ddebug>() == 8);
    assert!(offset_of!(Ddebug, file) == 0);
    assert!(offset_of!(Ddebug, func) == 8);
    assert!(offset_of!(Ddebug, fmt) == 16);
    assert!(offset_of!(Ddebug, line_flags) == 24);
};
