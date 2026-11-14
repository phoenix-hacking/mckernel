#[repr(C)]
pub struct SchedIdleOffsets {
    pub cpu_runq_lock_offset: usize,
    pub cpu_runq_irqstate_offset: usize,
    pub cpu_current_offset: usize,
    pub cpu_flags_offset: usize,
    pub cpu_status_offset: usize,
    pub cpu_runq_offset: usize,
    pub thread_sched_list_offset: usize,
    pub thread_status_offset: usize,
    pub monitor_status_offset: usize,
    pub monitor_counter_offset: usize,
}

#[repr(C)]
pub struct SchedIdleValues {
    pub cpu_running: CInt,
    pub cpu_idle: CInt,
    pub cpu_reserved: CInt,
    pub thread_running: CInt,
    pub thread_stopped: CInt,
    pub thread_interruptible: CInt,
    pub need_migrate: u32,
    pub monitor_idle: CInt,
    pub monitor_kernel: CInt,
}

#[repr(C)]
pub struct SchedIdleCallbacks {
    pub current_cpu: unsafe extern "C" fn() -> usize,
    pub lock: unsafe extern "C" fn(usize) -> CULong,
    pub unlock: unsafe extern "C" fn(usize, CULong),
    pub enable_interrupt: unsafe extern "C" fn(),
    pub disable_interrupt: unsafe extern "C" fn(),
    pub schedule: unsafe extern "C" fn(),
    pub migrate: unsafe extern "C" fn(),
    pub consolidate: unsafe extern "C" fn(),
    pub zero_free: unsafe extern "C" fn(),
    pub safe_halt: unsafe extern "C" fn(),
}

#[no_mangle]
pub unsafe extern "C" fn sched_idle_current_cpu_bridge() -> usize {
    unsafe { process_sched_cpu_local_bridge(ihk_mc_get_processor_id()) }
}

unsafe fn sched_idle_write_current_status(
    offsets: &SchedIdleOffsets,
    callbacks: &SchedIdleCallbacks,
    status: CInt,
) {
    let current_cpu = unsafe { (callbacks.current_cpu)() };
    let thread = unsafe {
        read_volatile(current_cpu.wrapping_add(offsets.cpu_current_offset) as *const usize)
    };
    unsafe {
        write_volatile(thread.wrapping_add(offsets.thread_status_offset) as *mut CInt, status);
    }
}

/// Release the initial idle runqueue handoff, then enable interrupts.
///
/// # Safety
/// CPU fields, all descriptor tables, and non-null callbacks have the original
/// idle() lifetimes/ABI. The current CPU owns the inherited runqueue lock with
/// its saved irqstate. Descriptors remain immutable; mutable kernel objects are
/// accessed only through raw pointers. No pointer ownership is transferred.
#[no_mangle]
pub unsafe extern "C" fn sched_idle_begin_body_result(
    cpu_addr: usize,
    offsets: *const SchedIdleOffsets,
    values: *const SchedIdleValues,
    callbacks: *const SchedIdleCallbacks,
) {
    let (offsets, values, callbacks) = unsafe { (&*offsets, &*values, &*callbacks) };
    let current_cpu = unsafe { (callbacks.current_cpu)() };
    let irqstate = unsafe {
        read_volatile(current_cpu.wrapping_add(offsets.cpu_runq_irqstate_offset) as *const CULong)
    };
    unsafe { (callbacks.unlock)(current_cpu.wrapping_add(offsets.cpu_runq_lock_offset), irqstate) };
    let status_addr = cpu_addr.wrapping_add(offsets.cpu_status_offset) as *mut CInt;
    if unsafe { read_volatile(status_addr) } == values.cpu_running {
        unsafe { write_volatile(status_addr, values.cpu_idle) };
    }
    unsafe { (callbacks.enable_interrupt)() };
}

/// Execute exactly one existing idle-loop iteration in its original order.
///
/// # Safety
/// Same valid immutable descriptor and CPU/monitor/current-thread lifetimes as
/// sched_idle_begin_body_result. Scheduler/migration/IRQ callbacks implement the
/// original primitive contracts. Current-thread lookup is repeated after each
/// schedule/halt boundary. The captured CPU and monitor remain valid throughout;
/// the queue scan is performed only while the supplied runqueue lock is held.
#[no_mangle]
pub unsafe extern "C" fn sched_idle_iteration_body_result(
    cpu_addr: usize,
    monitor_addr: usize,
    offsets: *const SchedIdleOffsets,
    values: *const SchedIdleValues,
    callbacks: *const SchedIdleCallbacks,
) {
    let (offsets, values, callbacks) = unsafe { (&*offsets, &*values, &*callbacks) };
    unsafe {
        sched_idle_write_current_status(offsets, callbacks, values.thread_stopped);
        (callbacks.schedule)();
        sched_idle_write_current_status(offsets, callbacks, values.thread_running);
        (callbacks.disable_interrupt)();
    }
    let flags_addr = cpu_addr.wrapping_add(offsets.cpu_flags_offset) as *mut u32;
    if unsafe { read_volatile(flags_addr) } & values.need_migrate != 0 {
        unsafe { (callbacks.migrate)() };
        // Migration can change flags: clear only the requested bit in its NEW value.
        let flags = unsafe { read_volatile(flags_addr) };
        unsafe { write_volatile(flags_addr, flags & !values.need_migrate) };
    }
    let status_addr = cpu_addr.wrapping_add(offsets.cpu_status_offset) as *mut CInt;
    let status = unsafe { read_volatile(status_addr) };
    if status == values.cpu_idle || status == values.cpu_reserved {
        let lock_addr = cpu_addr.wrapping_add(offsets.cpu_runq_lock_offset);
        let irqstate = unsafe { (callbacks.lock)(lock_addr) };
        if unsafe {
            sched_idle_runqueue_has_running_result(
                cpu_addr.wrapping_add(offsets.cpu_runq_offset),
                offsets.thread_sched_list_offset,
                offsets.thread_status_offset,
                values.thread_running,
            )
        } != 0 {
            unsafe { write_volatile(status_addr, values.cpu_running) };
        }
        unsafe { (callbacks.unlock)(lock_addr, irqstate) };
    }
    // Unlock/migration can affect CPU status: decide from a fresh observation.
    let status = unsafe { read_volatile(status_addr) };
    if status == values.cpu_idle || status == values.cpu_reserved {
        unsafe {
            (callbacks.consolidate)();
            (callbacks.zero_free)();
            write_volatile(monitor_addr.wrapping_add(offsets.monitor_status_offset) as *mut CInt,
                           values.monitor_idle);
            sched_idle_write_current_status(offsets, callbacks, values.thread_interruptible);
            (callbacks.safe_halt)();
            write_volatile(monitor_addr.wrapping_add(offsets.monitor_status_offset) as *mut CInt,
                           values.monitor_kernel);
        }
        let counter = monitor_addr.wrapping_add(offsets.monitor_counter_offset) as *mut CULong;
        unsafe {
            write_volatile(counter, read_volatile(counter).wrapping_add(1));
            sched_idle_write_current_status(offsets, callbacks, values.thread_running);
        }
    } else {
        unsafe { (callbacks.enable_interrupt)() };
    }
}

/// Own the existing infinite idle control loop; no callback/data is retained.
///
/// # Safety
/// All begin/iteration preconditions hold for the complete lifetime of idle().
#[no_mangle]
pub unsafe extern "C" fn sched_idle_loop_body_result(
    cpu_addr: usize,
    monitor_addr: usize,
    offsets: *const SchedIdleOffsets,
    values: *const SchedIdleValues,
    callbacks: *const SchedIdleCallbacks,
) -> ! {
    unsafe { sched_idle_begin_body_result(cpu_addr, offsets, values, callbacks) };
    loop {
        unsafe { sched_idle_iteration_body_result(cpu_addr, monitor_addr, offsets, values, callbacks) };
    }
}

