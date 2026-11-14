#[no_mangle]
pub unsafe extern "C" fn act_execve(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    pathbuf: *mut u8,
    main_loop_ret: *mut c_long,
) -> c_int {
    let phase = unsafe { (*w).sr.args[0] };

    match phase {
        1 => unsafe {
            act_execve_phase1(w, fd, cpu, pathbuf);
            0
        },
        2 => {
            let ret = unsafe { act_execve_phase2(w, fd, cpu) };
            if ret != 0 {
                if !main_loop_ret.is_null() {
                    unsafe {
                        *main_loop_ret = ret;
                    }
                }
                // Exec has already destroyed the old userspace. A worker-only
                // return is insufficient: join_all_threads discards td.ret.
                // Match the existing act_exit command-server/process cleanup
                // sequence and retain a failing process status. No success RET
                // is published for this incomplete image.
                unsafe {
                    mcexec_exit_cmd_servers_bridge();
                    mcexec_exit_process_bridge(1);
                }
                1 // Existing void bridge ABI; real bridge exits the process.
            } else {
                0
            }
        }
        _ => unsafe {
            mcexec_execve_invalid_phase_bridge();
            0
        },
    }
}
