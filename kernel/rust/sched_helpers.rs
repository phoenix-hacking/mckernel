use crate::abi::CInt;

const EINVAL: CInt = 22;
const SCHED_NORMAL: CInt = 0;
const SCHED_FIFO: CInt = 1;
const SCHED_RR: CInt = 2;
const SCHED_BATCH: CInt = 3;
const SCHED_IDLE: CInt = 5;
const SCHED_DEADLINE: CInt = 6;
const MAX_USER_RT_PRIO: CInt = 100;

#[no_mangle]
pub extern "C" fn sched_get_priority_max_value(policy: CInt) -> CInt {
    match policy {
        SCHED_FIFO | SCHED_RR => MAX_USER_RT_PRIO - 1,
        SCHED_DEADLINE | SCHED_NORMAL | SCHED_BATCH | SCHED_IDLE => 0,
        _ => -EINVAL,
    }
}

#[no_mangle]
pub extern "C" fn sched_get_priority_min_value(policy: CInt) -> CInt {
    match policy {
        SCHED_FIFO | SCHED_RR => 1,
        SCHED_DEADLINE | SCHED_NORMAL | SCHED_BATCH | SCHED_IDLE => 0,
        _ => -EINVAL,
    }
}
