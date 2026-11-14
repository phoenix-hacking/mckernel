#![allow(dead_code,non_camel_case_types)]
type c_int=i32;type c_long=i64;type c_ulong=u64;use std::ffi::c_void;
const PATH_MAX:usize=4096;const EINTR:i32=4;const MCEXEC_UP_WAIT_SYSCALL:c_ulong=0x30a02903;
struct McexecThreadData{cpu:c_int,remote_tid:c_int}
struct McexecSyscallRequest{rtid:i32,ttid:i32,valid:i32,number:c_ulong,args:[c_ulong;6]}
struct McexecSyscallWaitDesc{cpu:c_ulong,sr:McexecSyscallRequest,pid:i32}
unsafe fn getpid()->i32{255}static mut ERRNO:i32=22;unsafe fn __errno_location()->*mut i32{&raw mut ERRNO}
unsafe fn ioctl(_:i32,_:u64,_:u64)->i32{-1}
unsafe fn act_main_loop_iteration(_:&McexecSyscallWaitDesc,_:i32,_:*mut McexecThreadData,_:*mut u8,_:*mut u8,_:*mut i64,_:i32)->i32{panic!("failed WAIT cannot dispatch")}
unsafe fn mcexec_main_loop_timeout_bridge(){}unsafe fn mcexec_exit_cmd_servers_bridge(){}
unsafe fn mcexec_exit_process_bridge(status:i32){std::process::exit(status)}
pub unsafe extern "C" fn act_main_loop_body(
    my_thread: *mut McexecThreadData,
    fd: c_int,
    is_child: c_int,
) -> c_int {
    let cpu = unsafe { (*my_thread).cpu };
    let mut w = McexecSyscallWaitDesc {
        cpu: cpu as c_ulong,
        sr: McexecSyscallRequest {
            rtid: 0,
            ttid: 0,
            valid: 0,
            number: 0,
            args: [0; 6],
        },
        pid: unsafe { getpid() },
    };
    let mut pathbuf = [0u8; PATH_MAX];
    let mut tmpbuf = [0u8; PATH_MAX];

    loop {
        let wait_ret = unsafe {
            ioctl(
                fd,
                MCEXEC_UP_WAIT_SYSCALL,
                (&mut w as *mut McexecSyscallWaitDesc) as c_ulong,
            )
        };

        if wait_ret == 0 {
            let mut main_loop_ret: c_long = 0;
            let should_return = unsafe {
                act_main_loop_iteration(
                    &w,
                    fd,
                    my_thread,
                    pathbuf.as_mut_ptr(),
                    tmpbuf.as_mut_ptr(),
                    &mut main_loop_ret,
                    is_child,
                )
            };
            if should_return != 0 {
                return main_loop_ret as c_int;
            }

            unsafe {
                (*my_thread).remote_tid = -1;
            }
            continue;
        }

        if wait_ret == -1 && unsafe { *__errno_location() } == EINTR {
            continue;
        }

        break;
    }

    unsafe {
        mcexec_main_loop_timeout_bridge();
        // A terminal WAIT failure otherwise disappears when the joining main
        // discards this worker return and exits zero. Preserve the existing
        // fatal launcher exit path; retained kernel ownership stays retained.
        mcexec_exit_cmd_servers_bridge();
        mcexec_exit_process_bridge(1);
    }
    1
}
fn main(){let mut td=McexecThreadData{cpu:0,remote_tid:0};let _=unsafe{act_main_loop_body(&mut td,3,0)};std::process::exit(0)}
