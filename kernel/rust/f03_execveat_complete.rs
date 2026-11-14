// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Complete ordinary-profile exec orchestration. All process, VM, transport,
//! scheduler and allocation providers below are the existing real Rust owners.
#[cfg(not(all(target_arch = "x86_64", native_linux_irq_work_v6_12, enable_profile,
    f03_do_syscall_outer_candidate, f03_perf_owner_protocol)))]
compile_error!("complete exec requires its paired ordinary x86/Linux6.12 provider cohort");

use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, copy_nonoverlapping, null, null_mut, read_volatile};
use crate::abi::{CInt, CLong, CULong, Process, ProcessVm, ProgramImageSection,
    ProgramLoadDesc, SigInfo, SizeT, SyscallRequest, Thread, VmRegions, X86UserContext};
use crate::debug::{kprintf, Ddebug};
use crate::syscall_policy as policy;

const SYS_EXECVE: CULong = 59;
const SIGKILL: CInt = 9;
const RANGE_ATTRIBUTES: CULong = 0x8000_0000_0002_0002;
const IHK_MC_AP_NOWAIT: CULong = 2;
const SOURCE_FILE: *const i8 = concat!(env!("MCKERNEL_DO_SYSCALL_C_FILE"), "\0").as_ptr().cast();
const DEBUG_FLAGS: u32 = match env!("MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS").as_bytes() {
    b"0" => 0,
    b"1" => 1,
    _ => panic!("exec DDEBUG default must match the genuine C source"),
};
const fn debug_record(line: u32) -> Ddebug {
    Ddebug { file: SOURCE_FILE, func: b"do_execveat\0".as_ptr().cast(),
        fmt: null(), line_flags: line | (DEBUG_FLAGS << 24) }
}
// Selected C #line7179 at baseline physical7652: physical line minus474.
// Existing helper allocation/release origins remain their explicit7142/7285/7288/7290.
#[used]
#[link_section = "__verbose"]
static mut EXEC_DEBUG: [Ddebug; 3] = [
    debug_record(7600), debug_record(7606), debug_record(7727),
];

unsafe extern "C" {
    fn ihk_mc_get_processor_id() -> CInt;
    fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;
    fn clear_host_pte(address: CULong, length: SizeT, holding_lock: CInt) -> CLong;
    fn do_kill(thread: *mut Thread, pid: CInt, tid: CInt, signal: CInt,
        info: *mut SigInfo, ptracecont: CInt) -> CULong;
}

unsafe fn debug_enabled(index: usize) -> bool {
    read_volatile(addr_of!(EXEC_DEBUG[index].line_flags)) >> 24 != 0
}

// Keep the two original error diagnostics and tracked temporary allocations.
// strlen/copy errors intentionally retain their existing diagnostic-only use.
unsafe fn report_flatten_error(filename: *const i8, argv: bool) {
    let len = crate::x86_memory_helpers::strlen_user(filename);
    let allocation_line = if argv { 7623 } else { 7640 };
    let release_line = if argv { 7628 } else { 7645 };
    let name = crate::mem_helpers::kmalloc_tracked(
        len.wrapping_add(1), IHK_MC_AP_NOWAIT, SOURCE_FILE.cast_mut(), allocation_line,
    ).cast::<i8>();
    if !name.is_null() {
        let _ = crate::x86_memory_helpers::strcpy_from_user(name, filename);
    }
    let printable: *const i8 = if name.is_null() { b"\0".as_ptr().cast() } else { name };
    if argv {
        kprintf(b"ERROR: no argv for executable: %s?\n\0".as_ptr().cast(), printable);
    } else {
        kprintf(b"ERROR: no envp for executable: %s?\n\0".as_ptr().cast(), printable);
    }
    if !name.is_null() {
        crate::mem_helpers::kfree_tracked(name.cast(), SOURCE_FILE.cast_mut(), release_line);
    }
}

// Each irreversible failure enables preemption before reading the thread's live
// process/PID/TID and issuing the genuine kill; the cached entry proc is not used.
unsafe fn kill_after_unmap(thread: *mut Thread) {
    crate::cls::preempt_enable();
    let _ = do_kill(thread, (*(*thread).proc).pid, (*thread).tid, SIGKILL, null_mut(), 0);
}

/// Execute both host phases and the original irreversible exec transaction.
///
/// # Safety
/// The original syscall-entry contract keeps ctx, current Thread, its entry VM
/// and Process alive throughout all synchronous providers and the final switch.
/// User pointers remain opaque until the real admission/string providers use
/// them. Descriptor is exactly four owned pages; flattened buffers are distinct
/// owned allocations. No new process/thread reference is acquired or released.
/// The real transport retains request/reply TID, status, wait/schedule and cleanup
/// ordering. No callback may retain the stack request or copied ptrace context.
#[inline(never)]
unsafe extern "C" fn do_execveat(ctx: *mut X86UserContext, dirfd: CInt,
    filename: *const i8, argv: *mut *mut i8, envp: *mut *mut i8, flags: CInt,
) -> CInt {
    let thread = (*crate::cls::get_this_cpu_local_var()).current;
    let vm = (*thread).vm;
    let proc = (*thread).proc;
    let mut execve_ctx = MaybeUninit::<X86UserContext>::uninit();
    copy_nonoverlapping(ctx.cast::<u8>(), execve_ctx.as_mut_ptr().cast(),
        size_of::<X86UserContext>());
    let mut error = policy::f03_execveat_filename_admission_v1(vm, filename.cast());
    if error != 0 { return error; }
    let desc = policy::f03_execveat_allocate_descriptor_v1(SOURCE_FILE, 7142, &mut error)
        .cast::<ProgramLoadDesc>();
    if desc.is_null() { return error; }
    let mut argv_flat: *mut i8 = null_mut();
    let mut envp_flat: *mut i8 = null_mut();

    // Define every transport byte, including the previously unspecified args5.
    // Host phase1 consumes args0..4, phase2 args0..2. Keep the original single
    // request lifetime and phase2 reuse of args3/4, rather than clearing between
    // calls. This source repair does not assert parity for indeterminate bytes.
    let mut request = SyscallRequest { rtid: 0, ttid: 0, valid: 0,
        number: SYS_EXECVE, args: [0; 6] };
    request.args[0] = 1;
    request.args[1] = dirfd as CULong;
    request.args[2] = filename as CULong;
    request.args[3] = crate::x86_memory_helpers::virt_to_phys(desc.cast());
    request.args[4] = flags as CULong;
    let mut ret = do_syscall(addr_of_mut!(request), ihk_mc_get_processor_id());
    if ret != 0 {
        if debug_enabled(0) {
            // Preserve the original C long vararg, including its historical %d.
            kprintf(b"execve(): ERROR: host failed to load elf header, errno: %d\n\0"
                .as_ptr().cast(), ret);
        }
        ret = ret.wrapping_neg();
    } else {
        if debug_enabled(1) {
            kprintf(b"execve(): ELF desc received, num sections: %d\n\0"
                .as_ptr().cast(), (*desc).num_sections);
        }
        if (*desc).args_len != 0 {
            let bytes = size_of::<ProgramLoadDesc>().wrapping_add(
                size_of::<ProgramImageSection>().wrapping_mul((*desc).num_sections as usize));
            (*desc).args = desc.cast::<u8>().wrapping_add(bytes).cast();
        }
        let argv_flat_len = crate::string::flatten_strings_from_user(
            (*desc).args, argv, &mut argv_flat);
        if argv_flat_len < 0 {
            report_flatten_error(filename, true);
            ret = argv_flat_len as CLong;
        } else {
            (*desc).args = null_mut();
            (*desc).args_len = 0;
            let envp_flat_len = crate::string::flatten_strings_from_user(
                null_mut(), envp, &mut envp_flat);
            if envp_flat_len < 0 {
                report_flatten_error(filename, false);
                ret = envp_flat_len as CLong;
            } else {
                policy::f03_munmap_all_current_v1();
                policy::f03_execveat_install_user_context_v1(thread, vm, (*desc).entry);
                ret = crate::host_helpers::prepare_process_ranges_args_envs(
                    thread, desc, desc, RANGE_ATTRIBUTES,
                    argv_flat, argv_flat_len, envp_flat, envp_flat_len,
                ) as CLong;
                if ret != 0 {
                    kprintf(b"execve(): ERROR: preparing ranges, args, envs, stack, ret: %d\n\0"
                        .as_ptr().cast(), ret);
                    kill_after_unmap(thread);
                } else {
                    let _ = clear_host_pte((*vm).region.user_start,
                        (*vm).region.user_end.wrapping_sub((*vm).region.user_start), 0);
                    request.number = SYS_EXECVE;
                    request.args[0] = 2;
                    request.args[1] = crate::x86_memory_helpers::virt_to_phys(desc.cast());
                    request.args[2] = (size_of::<ProgramLoadDesc>() as CULong).wrapping_add(
                        (size_of::<ProgramImageSection>() as CULong)
                            .wrapping_mul((*desc).num_sections as CULong));
                    ret = do_syscall(addr_of_mut!(request), ihk_mc_get_processor_id());
                    if ret != 0 {
                        kill_after_unmap(thread);
                    } else {
                        policy::exec_reset_signal_state_current_v1(thread);
                        error = policy::f03_execveat_ptrace_report_v1(thread, execve_ctx.as_mut_ptr());
                        if error != 0 {
                            kprintf(b"execve(): ERROR: ptrace_report_exec()\n\0".as_ptr().cast());
                        }
                        if debug_enabled(2) {
                            kprintf(b"execve(): switching to new process\n\0".as_ptr().cast());
                        }
                        (*proc).execed = 1;
                        ret = 0;
                    }
                }
            }
        }
    }
    policy::f03_execveat_release_temporaries_v1(envp_flat.cast(), argv_flat.cast(),
        desc.cast(), SOURCE_FILE, 7285, 7288, 7290);
    // The original C entry returns int, including narrowing the long finish result.
    policy::f03_execveat_finish_switch_v1(thread, ret) as CInt
}

/// Preserve the exact existing sys_execve/sys_execveat callback ABI.
///
/// # Safety
/// Same entry, provider and ownership contract as do_execveat above; this bridge
/// adds only the original context cast and returns its C-int result unchanged.
#[no_mangle]
pub unsafe extern "C" fn syscall_execveat_bridge(ctx: *mut c_void, dirfd: CInt,
    filename: *const c_void, argv: *mut *mut c_void, envp: *mut *mut c_void, flags: CInt,
) -> CInt {
    do_execveat(ctx.cast(), dirfd, filename.cast(), argv.cast(), envp.cast(), flags)
}

const _: unsafe extern "C" fn(*mut c_void, CInt, *const c_void,
    *mut *mut c_void, *mut *mut c_void, CInt) -> CInt = syscall_execveat_bridge;
const _: unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong = do_syscall;
const _: unsafe extern "C" fn(CULong, SizeT, CInt) -> CLong = clear_host_pte;
const _: unsafe extern "C" fn(*mut Thread, CInt, CInt, CInt, *mut SigInfo, CInt) -> CULong = do_kill;

// Paired genuine C/Rust layout readback: source/caller/provider qualification
// compares these arrays from actual affected objects, not a surrogate layout.
#[no_mangle]
#[used]
pub static f03_execveat_complete_rust_abi_words: [CULong; 35] = [
    size_of::<CInt>() as CULong, align_of::<CInt>() as CULong,
    size_of::<CLong>() as CULong, align_of::<CLong>() as CULong,
    size_of::<SyscallRequest>() as CULong, align_of::<SyscallRequest>() as CULong,
    offset_of!(SyscallRequest, number) as CULong, offset_of!(SyscallRequest, args) as CULong,
    size_of::<X86UserContext>() as CULong, align_of::<X86UserContext>() as CULong,
    size_of::<ProgramLoadDesc>() as CULong, align_of::<ProgramLoadDesc>() as CULong,
    size_of::<ProgramImageSection>() as CULong, align_of::<ProgramImageSection>() as CULong,
    offset_of!(ProgramLoadDesc, num_sections) as CULong,
    offset_of!(ProgramLoadDesc, args) as CULong,
    offset_of!(ProgramLoadDesc, args_len) as CULong,
    offset_of!(ProgramLoadDesc, entry) as CULong,
    offset_of!(Thread, vm) as CULong, offset_of!(Thread, proc) as CULong,
    offset_of!(Thread, tid) as CULong, offset_of!(Process, pid) as CULong,
    offset_of!(Process, execed) as CULong, offset_of!(ProcessVm, region) as CULong,
    offset_of!(VmRegions, user_start) as CULong, offset_of!(VmRegions, user_end) as CULong,
    SYS_EXECVE, SIGKILL as CULong, RANGE_ATTRIBUTES,
    4096, 0, 2, 0, 4, 32,
];
const _: () = {
    assert!(size_of::<CInt>() == 4 && size_of::<CLong>() == 8);
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
};
