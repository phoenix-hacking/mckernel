// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Fragment for the future actual fixture crate; no driver/argv/second queue.
// Requires actual abi.rs, c_void/CInt/CLong/CULong/X86UserContext, EINVAL/EFAULT/EBADF,
// unchanged actual AT_FDCWD/AT_EMPTY_PATH/AT_SYMLINK_NOFOLLOW constants.
mod x86_cpu_helpers {
    use crate::abi::{CInt,CULong,X86UserContext};
    use core::ptr::read_volatile;
    include!("x86_syscall_read.UNCHANGED-RUST.inc");
    include!("ihk_mc_syscall_arg0.UNCHANGED-RUST.inc");
    include!("ihk_mc_syscall_arg1.UNCHANGED-RUST.inc");
    include!("ihk_mc_syscall_arg2.UNCHANGED-RUST.inc");
    include!("ihk_mc_syscall_arg3.UNCHANGED-RUST.inc");
    include!("ihk_mc_syscall_arg4.UNCHANGED-RUST.inc");
}
include!("ExecveatFn.EXACT-RUST.inc");
include!("execveat_policy_result.UNCHANGED-RUST.inc");
include!("execveat_body_result.UNCHANGED-RUST.inc");
include!("execve_body_result.UNCHANGED-RUST.inc");
include!("../exec_entries.RUST-FRAGMENT.rs.inc");
