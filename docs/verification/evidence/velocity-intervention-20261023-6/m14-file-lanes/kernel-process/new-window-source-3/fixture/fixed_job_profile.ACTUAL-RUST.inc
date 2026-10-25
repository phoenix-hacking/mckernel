#[no_mangle]
pub unsafe extern "C" fn profile_accumulate_and_print_job_events(proc: *mut Process) -> CInt {
    let mut node = McsLockNode {
        locked: 0,
        next: null_mut(),
        irqsave: 0,
    };
    mcs_lock_lock(&raw mut job_profile_lock, &raw mut node);

    if job_nr_processes == -1 {
        job_nr_processes = (*proc).nr_processes;
        job_nr_processes_left = (*proc).nr_processes;
        job_elapsed_ts = 0;
    }
    job_nr_processes_left -= 1;

    if job_profile_events.is_null() {
        job_profile_events = _kmalloc(
            (size_of::<ProfileEvent>() * PROFILE_EVENT_MAX) as CInt,
            IHK_MC_AP_NOWAIT,
            file_ptr(),
            line!() as CInt,
        )
        .cast::<ProfileEvent>();
        if job_profile_events.is_null() {
            kprintf(
                JOB_ALLOC_ERR_FMT.as_ptr().cast(),
                PROFILE_ACC_JOB_NAME.as_ptr(),
            );
            // Release the same acquisition and restore its saved IRQ state.
            mcs_lock_unlock(&raw mut job_profile_lock, &raw mut node);
            return -ENOMEM;
        }
        zero_events(job_profile_events);
    }

    let proc_events = profile_events((*proc).profile_events);
    let mut i = 0usize;
    while i < PROFILE_EVENT_MAX {
        let src = proc_events.add(i);
        if (*src).tsc != 0 {
            let dst = job_profile_events.add(i);
            (*dst).tsc = (*dst).tsc.wrapping_add((*src).tsc);
            (*dst).cnt = (*dst).cnt.wrapping_add((*src).cnt);
            (*src).tsc = 0;
            (*src).cnt = 0;
        }
        i += 1;
    }

    job_elapsed_ts = job_elapsed_ts.wrapping_add((*proc).profile_elapsed_ts);
    if job_nr_processes_left == 0 {
        print_profile_events(
            job_profile_events,
            JOB_HDR_FMT.as_ptr().cast(),
            JOB_LABEL.as_ptr(),
            job_nr_processes,
            job_elapsed_ts,
        );
        job_nr_processes = -1;
        job_nr_processes_left = -1;
        job_elapsed_ts = 0;
        zero_events(job_profile_events);
    }

    mcs_lock_unlock(&raw mut job_profile_lock, &raw mut node);
    0
}
