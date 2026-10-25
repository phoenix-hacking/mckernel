pub static mut job_profile_lock: McsLockNode = McsLockNode {
    locked: 0,
    next: null_mut(),
    irqsave: 0,
};

pub static mut job_profile_events: *mut ProfileEvent = null_mut();

pub static mut job_nr_processes: CInt = -1;

pub static mut job_nr_processes_left: CInt = -1;

pub static mut job_elapsed_ts: CULong = 0;
