//! Private codegen references only; no exports or runtime wiring.
use crate::abi::{CInt, CLong, CULong, SyscallRequest, UtiAttr};

#[used]
static REF_CRED_UID: unsafe extern "C" fn() = super::f03_credential_snapshot_typecheck::do_setresuid;
#[used]
static REF_CRED_GID: unsafe extern "C" fn() = super::f03_credential_snapshot_typecheck::do_setresgid;
#[used]
static REF_DO_SYSCALL: unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong = super::m14_private_do_syscall::f03_do_syscall_supported_v1;
#[used]
static REF_UTIL_THREAD: unsafe extern "C" fn(*mut UtiAttr) -> CInt = super::m14_private_util_thread::f03_util_thread_whole_v1;
#[used]
static REF_DO_SYSCALL2: unsafe extern "C" fn(CInt, CULong, CULong) -> CLong = super::m14_private_request_constructors::syscall_do_syscall2_bridge;
#[used]
static REF_POLICY_SYSCALL2: unsafe extern "C" fn(CInt, CULong, CULong) -> CLong = super::m14_private_request_constructors::syscall_policy_do_syscall2_bridge;
#[used]
static REF_DO_SYSCALL3: unsafe extern "C" fn(CInt, CULong, CULong, CULong) -> CLong = super::m14_private_request_constructors::syscall_do_syscall3_bridge;
#[used]
static REF_POLICY_SYSCALL3: unsafe extern "C" fn(CInt, CULong, CULong, CULong) -> CLong = super::m14_private_request_constructors::syscall_policy_do_syscall3_bridge;
#[used]
static REF_WAIT4: unsafe extern "C" fn(CInt, CInt) -> CInt = super::m14_private_request_constructors::wait_host_wait4_bridge;
