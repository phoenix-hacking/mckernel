use crate::abi::{CInt, CULong};

const EINVAL: CInt = 22;

const RLIMIT_CPU: CInt = 0;
const RLIMIT_FSIZE: CInt = 1;
const RLIMIT_DATA: CInt = 2;
const RLIMIT_STACK: CInt = 3;
const RLIMIT_CORE: CInt = 4;
const RLIMIT_RSS: CInt = 5;
const RLIMIT_NPROC: CInt = 6;
const RLIMIT_NOFILE: CInt = 7;
const RLIMIT_MEMLOCK: CInt = 8;
const RLIMIT_AS: CInt = 9;
const RLIMIT_LOCKS: CInt = 10;
const RLIMIT_SIGPENDING: CInt = 11;
const RLIMIT_MSGQUEUE: CInt = 12;
const RLIMIT_NICE: CInt = 13;
const RLIMIT_RTPRIO: CInt = 14;
const RLIMIT_RTTIME: CInt = 15;
const RLIMIT_NLIMITS: CInt = 16;

const MCK_RLIMIT_AS: CInt = 0;
const MCK_RLIMIT_CORE: CInt = 1;
const MCK_RLIMIT_CPU: CInt = 2;
const MCK_RLIMIT_DATA: CInt = 3;
const MCK_RLIMIT_FSIZE: CInt = 4;
const MCK_RLIMIT_LOCKS: CInt = 5;
const MCK_RLIMIT_MEMLOCK: CInt = 6;
const MCK_RLIMIT_MSGQUEUE: CInt = 7;
const MCK_RLIMIT_NICE: CInt = 8;
const MCK_RLIMIT_NOFILE: CInt = 9;
const MCK_RLIMIT_NPROC: CInt = 10;
const MCK_RLIMIT_RSS: CInt = 11;
const MCK_RLIMIT_RTPRIO: CInt = 12;
const MCK_RLIMIT_RTTIME: CInt = 13;
const MCK_RLIMIT_SIGPENDING: CInt = 14;
const MCK_RLIMIT_STACK: CInt = 15;

#[no_mangle]
pub extern "C" fn prlimit_validate_resource(resource: CInt) -> CInt {
    if !(0..RLIMIT_NLIMITS).contains(&resource) {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn prlimit_validate_new_limit(rlim_cur: CULong, rlim_max: CULong) -> CInt {
    if rlim_cur > rlim_max {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn prlimit_linux_update_needed(resource: CInt) -> CInt {
    matches!(
        resource,
        RLIMIT_FSIZE | RLIMIT_NOFILE | RLIMIT_LOCKS | RLIMIT_MSGQUEUE
    ) as CInt
}

#[no_mangle]
pub extern "C" fn prlimit_to_mckernel_resource(resource: CInt) -> CInt {
    match resource {
        RLIMIT_AS => MCK_RLIMIT_AS,
        RLIMIT_CORE => MCK_RLIMIT_CORE,
        RLIMIT_CPU => MCK_RLIMIT_CPU,
        RLIMIT_DATA => MCK_RLIMIT_DATA,
        RLIMIT_FSIZE => MCK_RLIMIT_FSIZE,
        RLIMIT_LOCKS => MCK_RLIMIT_LOCKS,
        RLIMIT_MEMLOCK => MCK_RLIMIT_MEMLOCK,
        RLIMIT_MSGQUEUE => MCK_RLIMIT_MSGQUEUE,
        RLIMIT_NICE => MCK_RLIMIT_NICE,
        RLIMIT_NOFILE => MCK_RLIMIT_NOFILE,
        RLIMIT_NPROC => MCK_RLIMIT_NPROC,
        RLIMIT_RSS => MCK_RLIMIT_RSS,
        RLIMIT_RTPRIO => MCK_RLIMIT_RTPRIO,
        RLIMIT_RTTIME => MCK_RLIMIT_RTTIME,
        RLIMIT_SIGPENDING => MCK_RLIMIT_SIGPENDING,
        RLIMIT_STACK => MCK_RLIMIT_STACK,
        _ => -1,
    }
}
