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


const _: () = {
    use core::mem::{align_of, offset_of, size_of};
    assert!(size_of::<Ddebug>() == 32);
    assert!(align_of::<Ddebug>() == 8);
    assert!(offset_of!(Ddebug, file) == 0);
    assert!(offset_of!(Ddebug, func) == 8);
    assert!(offset_of!(Ddebug, fmt) == 16);
    assert!(offset_of!(Ddebug, line_flags) == 24);
};
