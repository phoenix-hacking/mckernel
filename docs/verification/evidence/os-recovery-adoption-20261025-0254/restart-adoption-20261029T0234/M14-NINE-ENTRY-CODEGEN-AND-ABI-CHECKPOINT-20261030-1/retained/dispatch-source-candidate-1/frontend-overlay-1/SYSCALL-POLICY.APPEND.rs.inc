
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Seven private frontend bodies; existing public provider/modules remain intact.
#[cfg(all(m14_private_frontend, not(target_arch = "x86_64")))]
compile_error!("private M14 frontend requires its selected x86_64 ABI");
#[cfg(all(m14_private_frontend, not(enable_profile)))]
compile_error!("private do_syscall frontend requires its reviewed profile provider");
#[cfg(all(m14_private_frontend, any(enable_tofu, enable_fugaku_hacks)))]
compile_error!("private do_syscall frontend excludes optional ToFu/Fugaku paths");
#[cfg(m14_private_frontend)]
#[path = "m14_private_do_syscall.rs"]
mod m14_private_do_syscall;
#[cfg(m14_private_frontend)]
#[path = "m14_private_util_thread.rs"]
mod m14_private_util_thread;
#[cfg(m14_private_frontend)]
#[path = "m14_private_request_constructors.rs"]
mod m14_private_request_constructors;
