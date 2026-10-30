// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private, unselected source proposal; see CONTRACT.md. Request providers are
// intentionally unresolved until the two-phase protocol has a real owner.
#[cfg(f03_execveat_whole_candidate)]
mod f03_execveat_whole_v1 {
    use core::ffi::c_void;
    use core::mem::{size_of, MaybeUninit};
    use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile};
    use crate::abi::{CInt, CLong, CULong, ProgramImageSection, ProgramLoadDesc,
                     SyscallRequest, Thread, X86UserContext};
    use super::{f03_execveat_allocate_descriptor_v1, f03_execveat_filename_admission_v1,
        f03_execveat_release_temporaries_v1, f03_munmap_all_current_v1,
        f03_execveat_install_user_context_v1, f03_execveat_ptrace_report_v1,
        f03_execveat_finish_switch_v1, exec_reset_signal_state_current_v1, do_syscall};
    use crate::debug::Ddebug;

    #[repr(C)]
    struct Origins {
        file: *const i8,
        filename_argv_alloc_line: CInt,
        filename_argv_free_line: CInt,
        filename_envp_alloc_line: CInt,
        filename_envp_free_line: CInt,
        ranges_attr: CULong,
        sigkill: CInt,
    }
    unsafe extern "C" {
        static f03_execveat_origins_v1: Origins;
        static mut f03_execveat_debug_v1: [Ddebug; 3];
        fn kprintf(format: *const i8, ...) -> CInt;
        #[link_name = "preempt_enable"] fn exec_preempt_enable();
        #[link_name = "do_kill"] fn exec_kill(thread: *mut Thread, pid: CInt,
            tid: CInt, sig: CInt, info: *mut c_void, ptracecont: CInt) -> CULong;
    }
    macro_rules! debug {
        ($index:expr, $fmt:expr $(, $arg:expr)* $(,)?) => {{
            if unsafe { read_volatile(addr_of!(f03_execveat_debug_v1[$index].line_flags)) } >> 24 != 0 {
                unsafe { kprintf($fmt.as_ptr().cast() $(, $arg)*); }
            }
        }};
    }
    unsafe fn failed_strings(filename: *const i8, argv: bool) {
        let n = crate::x86_memory_helpers::strlen_user(filename);
        let o = &f03_execveat_origins_v1;
        let (alloc_line, free_line) = if argv {
            (o.filename_argv_alloc_line, o.filename_argv_free_line)
        } else { (o.filename_envp_alloc_line, o.filename_envp_free_line) };
        let name = crate::mem_helpers::kmalloc_tracked(n.wrapping_add(1), 2,
            o.file.cast_mut(), alloc_line).cast::<i8>();
        if !name.is_null() { let _ = crate::x86_memory_helpers::strcpy_from_user(name, filename); }
        if argv { kprintf(c"ERROR: no argv for executable: %s?\n".as_ptr(),
            if name.is_null() { c"".as_ptr() } else { name }); }
        else { kprintf(c"ERROR: no envp for executable: %s?\n".as_ptr(),
            if name.is_null() { c"".as_ptr() } else { name }); }
        if !name.is_null() { crate::mem_helpers::kfree_tracked(name.cast(), o.file.cast_mut(), free_line); }
    }
    /// # Safety
    /// The current thread/VM/context and syscall input remain live; filename and
    /// vector access use the actual usercopy providers. The host supplies a valid,
    /// bounded descriptor and pre-strings. The approved declared-arity writes
    /// rely on the real offload helpers to initialize their own ID/valid fields.
    /// Temporary buffers remain owned until both synchronous host requests and
    /// range preparation complete. Exec teardown exclusivity, signal/ptrace and
    /// runq switch owners must satisfy their actual existing provider contracts.
    #[export_name = "do_execveat"]
    pub unsafe extern "C" fn do_execveat(ctx: *mut X86UserContext, dirfd: CInt,
        filename: *const i8, argv: *mut *mut i8, envp: *mut *mut i8, flags: CInt) -> CInt {
        let thread = (*crate::cls::get_this_cpu_local_var()).current;
        let vm = (*thread).vm;
        let process = (*thread).proc;
        let mut exec_ctx = MaybeUninit::<X86UserContext>::uninit();
        core::ptr::copy_nonoverlapping(ctx.cast::<u8>(), exec_ctx.as_mut_ptr().cast::<u8>(), size_of::<X86UserContext>());
        let admission = f03_execveat_filename_admission_v1(vm, filename.cast());
        if admission != 0 { return admission; }
        let mut error: CInt = 0;
        let o = &f03_execveat_origins_v1;
        let desc = f03_execveat_allocate_descriptor_v1(o.file, 7142, addr_of_mut!(error)).cast::<ProgramLoadDesc>();
        if desc.is_null() { return error; }
        let mut argv_flat: *mut i8 = null_mut();
        let mut envp_flat: *mut i8 = null_mut();
        let mut request = MaybeUninit::<SyscallRequest>::uninit();
        let ret: CLong = 'transaction: {
            let pa = crate::x86_memory_helpers::virt_to_phys(desc.cast());
            // Root-approved exec-specific arity: no whole-request reference or
            // blanket zeroing. Offload owns rtid, ttid and valid initialization.
            let request_ptr = request.as_mut_ptr();
            core::ptr::write(addr_of_mut!((*request_ptr).number), 59);
            core::ptr::write(addr_of_mut!((*request_ptr).args[0]), 1);
            core::ptr::write(addr_of_mut!((*request_ptr).args[1]), dirfd as CLong as CULong);
            core::ptr::write(addr_of_mut!((*request_ptr).args[2]), filename as CULong);
            core::ptr::write(addr_of_mut!((*request_ptr).args[3]), pa);
            core::ptr::write(addr_of_mut!((*request_ptr).args[4]), flags as CLong as CULong);
            core::ptr::write(addr_of_mut!((*request_ptr).args[5]), 0);
            let mut ret = do_syscall(request.as_mut_ptr(), crate::x86_local::ihk_mc_get_processor_id());
            if ret != 0 {
                debug!(0, b"execve(): ERROR: host failed to load elf header, errno: %ld\n\0", ret);
                break 'transaction ret.wrapping_neg();
            }
            debug!(1, b"execve(): ELF desc received, num sections: %d\n\0", (*desc).num_sections);
            if (*desc).args_len != 0 {
                let offset = size_of::<ProgramLoadDesc>().wrapping_add(
                    size_of::<ProgramImageSection>().wrapping_mul((*desc).num_sections as usize));
                (*desc).args = desc.cast::<u8>().wrapping_add(offset).cast();
            }
            let argv_len = crate::string::flatten_strings_from_user((*desc).args, argv, addr_of_mut!(argv_flat));
            if argv_len < 0 { failed_strings(filename, true); break 'transaction argv_len as CLong; }
            (*desc).args = null_mut(); (*desc).args_len = 0;
            let envp_len = crate::string::flatten_strings_from_user(null_mut(), envp, addr_of_mut!(envp_flat));
            if envp_len < 0 { failed_strings(filename, false); break 'transaction envp_len as CLong; }
            f03_munmap_all_current_v1();
            f03_execveat_install_user_context_v1(thread, vm, (*desc).entry);
            ret = crate::host_helpers::prepare_process_ranges_args_envs(thread, desc, desc,
                o.ranges_attr, argv_flat, argv_len, envp_flat, envp_len) as CLong;
            if ret != 0 {
                kprintf(c"execve(): ERROR: preparing ranges, args, envs, stack, ret: %ld\n".as_ptr(), ret);
                exec_preempt_enable();
                let _ = exec_kill(thread, (*(*thread).proc).pid, (*thread).tid, o.sigkill, null_mut(), 0);
                break 'transaction ret;
            }
            let _ = super::clear_host_pte((*vm).region.user_start,
                (*vm).region.user_end.wrapping_sub((*vm).region.user_start), 0);
            let desc_bytes = size_of::<ProgramLoadDesc>().wrapping_add(
                size_of::<ProgramImageSection>().wrapping_mul((*desc).num_sections as usize));
            // Preserve initialized args3..5 exactly as left by phase one.
            // Caller/transport must prove the preceding request is no longer borrowed.
            core::ptr::write(addr_of_mut!((*request_ptr).number), 59);
            core::ptr::write(addr_of_mut!((*request_ptr).args[0]), 2);
            core::ptr::write(addr_of_mut!((*request_ptr).args[1]),
                crate::x86_memory_helpers::virt_to_phys(desc.cast()));
            core::ptr::write(addr_of_mut!((*request_ptr).args[2]), desc_bytes as CULong);
            ret = do_syscall(request.as_mut_ptr(), crate::x86_local::ihk_mc_get_processor_id());
            if ret != 0 {
                exec_preempt_enable();
                let _ = exec_kill(thread, (*(*thread).proc).pid, (*thread).tid, o.sigkill, null_mut(), 0);
                break 'transaction ret;
            }
            exec_reset_signal_state_current_v1(thread);
            if f03_execveat_ptrace_report_v1(thread, exec_ctx.as_mut_ptr()) != 0 {
                kprintf(c"execve(): ERROR: ptrace_report_exec()\n".as_ptr());
            }
            debug!(2, b"execve(): switching to new process\n\0");
            (*process).execed = 1;
            0
        };
        f03_execveat_release_temporaries_v1(envp_flat.cast(), argv_flat.cast(), desc.cast(),
            o.file, 7285, 7288, 7290);
        f03_execveat_finish_switch_v1(thread, ret) as CInt
    }
    #[no_mangle]
    #[used]
    pub static f03_execveat_Rust_ABI_v1: [CULong; 32] = [
        size_of::<Thread>() as CULong, core::mem::align_of::<Thread>() as CULong,
        core::mem::offset_of!(Thread, vm) as CULong, core::mem::offset_of!(Thread, proc) as CULong,
        core::mem::offset_of!(Thread, tid) as CULong,
        size_of::<crate::abi::ProcessVm>() as CULong,
        core::mem::offset_of!(crate::abi::ProcessVm, region) as CULong,
        core::mem::offset_of!(crate::abi::VmRegions, user_start) as CULong,
        core::mem::offset_of!(crate::abi::VmRegions, user_end) as CULong,
        core::mem::offset_of!(crate::abi::Process, pid) as CULong,
        core::mem::offset_of!(crate::abi::Process, execed) as CULong,
        size_of::<ProgramLoadDesc>() as CULong, core::mem::align_of::<ProgramLoadDesc>() as CULong,
        core::mem::offset_of!(ProgramLoadDesc, num_sections) as CULong,
        core::mem::offset_of!(ProgramLoadDesc, entry) as CULong,
        core::mem::offset_of!(ProgramLoadDesc, args) as CULong,
        core::mem::offset_of!(ProgramLoadDesc, args_len) as CULong,
        size_of::<ProgramImageSection>() as CULong, size_of::<X86UserContext>() as CULong,
        size_of::<SyscallRequest>() as CULong, core::mem::align_of::<SyscallRequest>() as CULong,
        core::mem::offset_of!(SyscallRequest, number) as CULong,
        core::mem::offset_of!(SyscallRequest, args) as CULong,
        size_of::<Origins>() as CULong, core::mem::align_of::<Origins>() as CULong,
        core::mem::offset_of!(Origins, file) as CULong,
        core::mem::offset_of!(Origins, filename_argv_alloc_line) as CULong,
        core::mem::offset_of!(Origins, filename_argv_free_line) as CULong,
        core::mem::offset_of!(Origins, filename_envp_alloc_line) as CULong,
        core::mem::offset_of!(Origins, filename_envp_free_line) as CULong,
        core::mem::offset_of!(Origins, ranges_attr) as CULong,
        core::mem::offset_of!(Origins, sigkill) as CULong,
    ];
}
