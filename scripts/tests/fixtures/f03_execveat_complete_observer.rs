// Functional HOST observer only. Test doubles below never supply a kernel image.
#![allow(dead_code, unused_imports, unsafe_op_in_unsafe_fn)]
#[path = "@ABI@"] mod abi;
#[path = "@MODULE@"] mod candidate;
use abi::*;
use core::ffi::c_void;
use core::mem::{align_of, size_of};
use core::ptr::{addr_of_mut, null_mut, write_bytes};
use std::cell::RefCell;

mod debug {
    #[repr(C)]
    pub struct Ddebug { pub file: *const i8, pub func: *const i8,
        pub fmt: *const i8, pub line_flags: u32 }
    unsafe extern "C" {
        #[link_name = "printf"]
        pub fn kprintf(format: *const i8, ...) -> crate::abi::CInt;
    }
}
#[derive(Clone, Debug)]
struct Case {
    name: &'static str, admission: i32, allocation: bool, phase1: i64,
    argv: i32, envp: i32, ranges: i32, pte: i64, phase2: i64, ptrace: i32,
    shebang: bool, diagnostic_allocation: bool, error_output: bool, change_process: bool,
}
impl Case {
    fn success(name: &'static str) -> Self {
        Self { name, admission: 0, allocation: true, phase1: 0,
            argv: 24, envp: 16, ranges: 0, pte: 0, phase2: 0, ptrace: 0,
            shebang: false, diagnostic_allocation: true, error_output: false,
            change_process: false }
    }
}
struct State {
    case: Case, events: Vec<&'static str>, cpu: *mut CpuLocalVar, thread: *mut Thread,
    proc: *mut Process, other_proc: *mut Process, vm: *mut ProcessVm,
    desc: *mut ProgramLoadDesc, ctx: *mut X86UserContext,
    argv: *mut *mut i8, envp: *mut *mut i8, filename: *const i8,
    argv_flat: *mut i8, envp_flat: *mut i8, diagnostic: *mut i8,
    argv_live: bool, envp_live: bool, descriptor_live: bool, diagnostic_live: bool,
    unmapped: bool, preempt_disabled: bool, cpu_calls: usize, host_calls: usize,
    phys_calls: usize, request: usize, original_context: Vec<u8>,
}
thread_local! { static STATE: RefCell<Option<State>> = const { RefCell::new(None) }; }
fn observe<T>(f: impl FnOnce(&mut State) -> T) -> T {
    STATE.with(|s| f(s.borrow_mut().as_mut().unwrap()))
}
mod cls {
    use super::*;
    pub unsafe fn get_this_cpu_local_var() -> *mut CpuLocalVar { observe(|s| s.cpu) }
    pub unsafe fn preempt_enable() { observe(|s| {
        assert!(s.unmapped && s.preempt_disabled); s.preempt_disabled = false;
        s.events.push("enable");
    }); }
}
mod mem_helpers {
    use super::*;
    pub unsafe fn kmalloc_tracked(bytes: CInt, flags: CULong, file: *mut i8, line: CInt)
        -> *mut c_void {
        observe(|s| {
            assert!(!s.unmapped); assert_eq!(bytes, 6); assert_eq!(flags, 2);
            assert!(!file.is_null()); assert_eq!(line, if s.case.argv < 0 { 7623 } else { 7640 });
            s.events.push("diag_alloc");
            s.diagnostic_live = s.case.diagnostic_allocation;
            if s.diagnostic_live { s.diagnostic.cast() } else { null_mut() }
        })
    }
    pub unsafe fn kfree_tracked(ptr: *mut c_void, file: *mut i8, line: CInt) {
        observe(|s| {
            assert_eq!(ptr, s.diagnostic.cast()); assert!(s.diagnostic_live);
            assert!(!file.is_null()); assert_eq!(line, if s.case.argv < 0 { 7628 } else { 7645 });
            s.diagnostic_live = false; write_bytes(s.diagnostic, 0xcc, 16);
            s.events.push("diag_free");
        });
    }
}
mod x86_memory_helpers {
    use super::*;
    pub unsafe extern "C" fn virt_to_phys(ptr: *mut c_void) -> CULong {
        observe(|s| {
            assert!(s.descriptor_live); assert_eq!(ptr, s.desc.cast());
            s.phys_calls += 1; s.events.push(if s.phys_calls == 1 { "phys1" } else { "phys2" });
            0x1234_0000
        })
    }
    pub unsafe fn strlen_user(filename: *const i8) -> CInt {
        observe(|s| { assert!(!s.unmapped); assert_eq!(filename, s.filename);
            s.events.push("strlen"); 5 })
    }
    pub unsafe fn strcpy_from_user(destination: *mut i8, filename: *const i8) -> CInt {
        observe(|s| {
            assert!(!s.unmapped && s.diagnostic_live); assert_eq!(filename, s.filename);
            assert_eq!(destination, s.diagnostic);
            core::ptr::copy_nonoverlapping(filename, destination, 6); s.events.push("copy"); 0
        })
    }
}
mod string {
    use super::*;
    pub unsafe fn flatten_strings_from_user(pre: *mut i8, input: *mut *mut i8,
        flat: *mut *mut i8) -> CInt {
        observe(|s| {
            assert!(!s.unmapped && s.descriptor_live);
            if input == s.argv {
                let expected = if s.case.shebang {
                    s.desc.cast::<u8>().add(size_of::<ProgramLoadDesc>() + 2 * size_of::<ProgramImageSection>()).cast()
                } else { null_mut() };
                assert_eq!(pre, expected); s.events.push("argv");
                s.argv_live = s.case.argv >= 0 || s.case.error_output;
                if s.argv_live { flat.write(s.argv_flat); }
                s.case.argv
            } else {
                assert_eq!(input, s.envp); assert!(pre.is_null());
                assert!((*s.desc).args.is_null()); assert_eq!((*s.desc).args_len, 0);
                assert!(s.argv_live); s.events.push("envp");
                s.envp_live = s.case.envp >= 0 || s.case.error_output;
                if s.envp_live { flat.write(s.envp_flat); }
                s.case.envp
            }
        })
    }
}
mod host_helpers {
    use super::*;
    pub unsafe fn prepare_process_ranges_args_envs(thread: *mut Thread,
        desc: *mut ProgramLoadDesc, same: *mut ProgramLoadDesc, attributes: CULong,
        argv: *mut i8, argv_len: CInt, envp: *mut i8, envp_len: CInt) -> CInt {
        observe(|s| {
            assert!(s.unmapped && s.preempt_disabled && s.descriptor_live);
            assert_eq!(thread, s.thread); assert_eq!((desc, same), (s.desc, s.desc));
            assert_eq!(attributes, 0x8000_0000_0002_0002);
            assert_eq!((argv, argv_len), (s.argv_flat, s.case.argv));
            assert_eq!((envp, envp_len), (s.envp_flat, s.case.envp));
            assert!(s.argv_live && s.envp_live); s.events.push("ranges");
            if s.case.change_process { (*thread).proc = s.other_proc; }
            s.case.ranges
        })
    }
}
mod syscall_policy {
    use super::*;
    pub unsafe fn f03_execveat_filename_admission_v1(vm: *mut ProcessVm,
        filename: *const c_void) -> CInt {
        observe(|s| {
            assert_eq!(vm, s.vm); assert_eq!(filename, s.filename.cast());
            // The entry must already have copied the complete original context.
            write_bytes(s.ctx.cast::<u8>(), 0x5a, size_of::<X86UserContext>());
            s.events.push("admit"); s.case.admission
        })
    }
    pub unsafe fn f03_execveat_allocate_descriptor_v1(file: *const i8, line: CInt,
        error: *mut CInt) -> *mut c_void {
        observe(|s| {
            assert!(!file.is_null()); assert_eq!(line, 7142); s.events.push("alloc");
            if !s.case.allocation { error.write(-12); return null_mut(); }
            s.descriptor_live = true; (*s.desc).num_sections = 2;
            (*s.desc).entry = 0x40_1000;
            if s.case.shebang { (*s.desc).args_len = 32; }
            s.desc.cast()
        })
    }
    pub unsafe fn f03_munmap_all_current_v1() {
        observe(|s| { assert!(!s.unmapped && s.argv_live && s.envp_live);
            s.unmapped = true; s.events.push("unmap"); });
    }
    pub unsafe fn f03_execveat_install_user_context_v1(thread: *mut Thread,
        vm: *mut ProcessVm, entry: CULong) {
        observe(|s| {
            assert!(s.unmapped && !s.preempt_disabled);
            assert_eq!((thread, vm, entry), (s.thread, s.vm, 0x40_1000));
            s.preempt_disabled = true; s.events.push("install");
        });
    }
    pub unsafe fn exec_reset_signal_state_current_v1(thread: *mut Thread) {
        observe(|s| {
            assert_eq!(thread, s.thread); assert!(s.preempt_disabled);
            assert_eq!(s.host_calls, 2); assert!(s.descriptor_live);
            s.events.push("reset");
        });
    }
    pub unsafe fn f03_execveat_ptrace_report_v1(thread: *mut Thread,
        ctx: *mut X86UserContext) -> CInt {
        observe(|s| {
            assert_eq!(thread, s.thread); assert_ne!(ctx, s.ctx);
            assert_eq!(ctx as usize % align_of::<X86UserContext>(), 0);
            assert_eq!(core::slice::from_raw_parts(ctx.cast::<u8>(), size_of::<X86UserContext>()),
                s.original_context.as_slice());
            assert_eq!((*s.proc).execed, 0); s.events.push("ptrace"); s.case.ptrace
        })
    }
    pub unsafe fn f03_execveat_release_temporaries_v1(envp: *mut c_void,
        argv: *mut c_void, desc: *mut c_void, file: *const i8,
        envp_line: CInt, argv_line: CInt, desc_line: CInt) {
        observe(|s| {
            assert!(!file.is_null()); assert_eq!((envp_line, argv_line, desc_line), (7285, 7288, 7290));
            if !envp.is_null() {
                assert_eq!(envp, s.envp_flat.cast()); assert!(s.envp_live);
                s.envp_live = false; write_bytes(s.envp_flat, 0xcc, 64); s.events.push("release_envp");
            } else { assert!(!s.envp_live); }
            if !argv.is_null() {
                assert_eq!(argv, s.argv_flat.cast()); assert!(s.argv_live);
                s.argv_live = false; write_bytes(s.argv_flat, 0xcc, 64); s.events.push("release_argv");
            } else { assert!(!s.argv_live); }
            assert_eq!(desc, s.desc.cast()); assert!(s.descriptor_live);
            s.descriptor_live = false; write_bytes(s.desc.cast::<u8>(), 0xcc, 4 * 4096);
            s.events.push("release_desc");
        });
    }
    pub unsafe fn f03_execveat_finish_switch_v1(thread: *mut Thread, result: CLong) -> CLong {
        observe(|s| {
            assert_eq!(thread, s.thread); assert!(!s.descriptor_live && !s.argv_live && !s.envp_live);
            if result == 0 {
                assert!(s.preempt_disabled); assert_eq!((*s.proc).execed, 1);
                assert_eq!((*s.other_proc).execed, 0);
                s.events.push("finish_zero"); -14 // Existing nonreturning-switch fallback.
            } else {
                assert!(!s.preempt_disabled); assert_eq!((*s.proc).execed, 0);
                s.events.push("finish_error"); result
            }
        })
    }
}
#[no_mangle]
unsafe extern "C" fn ihk_mc_get_processor_id() -> CInt {
    observe(|s| { s.cpu_calls += 1; s.events.push(if s.cpu_calls == 1 { "cpu1" } else { "cpu2" }); 7 })
}
#[no_mangle]
unsafe extern "C" fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong {
    let (phase, expected, result) = observe(|s| {
        assert_eq!(cpu, 7); assert!(s.descriptor_live);
        assert_eq!(request as usize % align_of::<SyscallRequest>(), 0);
        s.host_calls += 1;
        assert_eq!((*request).number, 59);
        if s.host_calls == 1 {
            s.request = request as usize; assert!(!s.unmapped);
            assert_eq!(((*request).rtid, (*request).ttid, (*request).valid), (0, 0, 0));
            s.events.push("host1");
            (1, [1, (-100i32) as u64, s.filename as u64, 0x1234_0000, 0x1000, 0], s.case.phase1)
        } else {
            assert_eq!(s.request, request as usize); assert!(s.unmapped && s.preempt_disabled);
            assert_eq!(((*request).rtid, (*request).ttid, (*request).valid), (-91, 812, 1));
            s.events.push("host2");
            (2, [2, 0x1234_0000, (size_of::<ProgramLoadDesc>() + 2 * size_of::<ProgramImageSection>()) as u64,
                0x1234_0000, 0x1000, 0], s.case.phase2)
        }
    });
    // Genuine stack request stays alive while a synchronous observer reads on
    // another thread. It is joined before publication of provider mutations.
    let address = request as usize;
    std::thread::spawn(move || {
        std::thread::yield_now();
        let request = address as *const SyscallRequest;
        unsafe { assert_eq!((*request).args, expected); }
    }).join().unwrap();
    if phase == 1 { (*request).rtid = -91; (*request).ttid = 812; (*request).valid = 1; }
    result
}
#[no_mangle]
unsafe extern "C" fn clear_host_pte(start: CULong, length: SizeT, holding: CInt) -> CLong {
    observe(|s| {
        assert!(s.unmapped && s.preempt_disabled && s.descriptor_live);
        assert_eq!((start, length, holding), (0x1000, 0x9000, 0));
        s.events.push("pte"); s.case.pte
    })
}
#[no_mangle]
unsafe extern "C" fn do_kill(thread: *mut Thread, pid: CInt, tid: CInt,
    signal: CInt, info: *mut SigInfo, cont: CInt) -> CULong {
    observe(|s| {
        assert!(s.unmapped && !s.preempt_disabled && s.descriptor_live);
        assert_eq!((thread, tid, signal, cont), (s.thread, 301, 9, 0)); assert!(info.is_null());
        assert_eq!(pid, if s.case.change_process { 202 } else { 101 });
        s.events.push("kill"); 0
    })
}
unsafe fn storage<T>() -> *mut T {
    let p = std::alloc::alloc_zeroed(std::alloc::Layout::new::<T>()).cast::<T>();
    assert!(!p.is_null()); p
}
unsafe fn discard<T>(ptr: *mut T) { std::alloc::dealloc(ptr.cast(), std::alloc::Layout::new::<T>()); }
unsafe fn run(case: Case, expected: &[&str], expected_result: i32) {
    let cpu = storage::<CpuLocalVar>(); let thread = storage::<Thread>();
    let proc = storage::<Process>(); let other_proc = storage::<Process>();
    let vm = storage::<ProcessVm>(); let ctx = storage::<X86UserContext>();
    let layout = std::alloc::Layout::from_size_align(4 * 4096, 4096).unwrap();
    let desc = std::alloc::alloc_zeroed(layout).cast::<ProgramLoadDesc>(); assert!(!desc.is_null());
    let argv_flat = storage::<[i8; 64]>().cast::<i8>(); let envp_flat = storage::<[i8; 64]>().cast::<i8>();
    let diagnostic = storage::<[i8; 16]>().cast::<i8>();
    let filename = b"/exec\0".as_ptr().cast::<i8>();
    let mut argv = [filename.cast_mut(), null_mut()]; let mut envp = [filename.cast_mut(), null_mut()];
    (*cpu).current = thread; (*thread).proc = proc; (*thread).vm = vm; (*thread).tid = 301;
    (*proc).pid = 101; (*other_proc).pid = 202;
    (*vm).region.user_start = 0x1000; (*vm).region.user_end = 0xa000;
    write_bytes(ctx.cast::<u8>(), 0xa5, size_of::<X86UserContext>());
    let original_context = core::slice::from_raw_parts(ctx.cast::<u8>(), size_of::<X86UserContext>()).to_vec();
    let name = case.name;
    STATE.with(|s| *s.borrow_mut() = Some(State { case, events: Vec::new(), cpu, thread,
        proc, other_proc, vm, desc, ctx, argv: argv.as_mut_ptr(), envp: envp.as_mut_ptr(), filename,
        argv_flat, envp_flat, diagnostic, argv_live: false, envp_live: false, descriptor_live: false,
        diagnostic_live: false, unmapped: false, preempt_disabled: false, cpu_calls: 0,
        host_calls: 0, phys_calls: 0, request: 0, original_context }));
    let result = candidate::syscall_execveat_bridge(ctx.cast(), -100, filename.cast(),
        argv.as_mut_ptr().cast(), envp.as_mut_ptr().cast(), 0x1000);
    let s = STATE.with(|s| s.borrow_mut().take().unwrap());
    assert_eq!(result, expected_result, "{name}");
    assert_eq!(s.events, expected, "{name}");
    assert!(!s.argv_live && !s.envp_live && !s.descriptor_live && !s.diagnostic_live, "{name}");
    discard(cpu); discard(thread); discard(proc); discard(other_proc); discard(vm); discard(ctx);
    std::alloc::dealloc(desc.cast(), layout);
    discard(argv_flat.cast::<[i8; 64]>()); discard(envp_flat.cast::<[i8; 64]>());
    discard(diagnostic.cast::<[i8; 16]>());
}
fn main() { unsafe {
    let success = ["admit", "alloc", "phys1", "cpu1", "host1", "argv", "envp", "unmap", "install",
        "ranges", "pte", "phys2", "cpu2", "host2", "reset", "ptrace", "release_envp", "release_argv",
        "release_desc", "finish_zero"];
    let phase1 = ["admit", "alloc", "phys1", "cpu1", "host1", "release_desc", "finish_error"];
    let range_error = ["admit", "alloc", "phys1", "cpu1", "host1", "argv", "envp", "unmap", "install",
        "ranges", "enable", "kill", "release_envp", "release_argv", "release_desc", "finish_error"];
    let phase2 = ["admit", "alloc", "phys1", "cpu1", "host1", "argv", "envp", "unmap", "install",
        "ranges", "pte", "phys2", "cpu2", "host2", "enable", "kill", "release_envp", "release_argv",
        "release_desc", "finish_error"];
    let mut cases = 0;
    let mut c = Case::success("admission"); c.admission = -14; run(c, &["admit"], -14); cases += 1;
    let mut c = Case::success("descriptor"); c.allocation = false; run(c, &["admit", "alloc"], -12); cases += 1;
    for result in [2i64, -17, 1 << 32, (1 << 32) + 7] {
        let mut c = Case::success("phase1-result"); c.phase1 = result;
        run(c, &phase1, result.wrapping_neg() as i32); cases += 1;
    }
    for argv_error in [true, false] { for diagnostic_allocation in [true, false] {
    for error_output in [true, false] {
        let mut c = Case::success("flatten-error"); c.diagnostic_allocation = diagnostic_allocation;
        c.error_output = error_output;
        if argv_error { c.argv = -7; } else { c.envp = -12; }
        let mut expected = vec!["admit", "alloc", "phys1", "cpu1", "host1", "argv"];
        if !argv_error { expected.push("envp"); }
        expected.extend(["strlen", "diag_alloc"]);
        if diagnostic_allocation { expected.extend(["copy", "diag_free"]); }
        if !argv_error && error_output { expected.push("release_envp"); }
        if !argv_error || error_output { expected.push("release_argv"); }
        expected.extend(["release_desc", "finish_error"]);
        run(c, &expected, if argv_error { -7 } else { -12 }); cases += 1;
    }}}
    for change_process in [true, false] {
        let mut c = Case::success("range-error-live-kill-owner"); c.ranges = -12;
        c.change_process = change_process; run(c, &range_error, -12); cases += 1;
    }
    for result in [-5i64, 19, 1 << 32, (1 << 32) + 9] {
        let mut c = Case::success("phase2-result"); c.phase2 = result;
        run(c, &phase2, result as i32); cases += 1;
    }
    for shebang in [false, true] { for ptrace in [0, -3] { for change_process in [false, true] {
        let mut c = Case::success("successful-exec"); c.shebang = shebang; c.ptrace = ptrace;
        c.change_process = change_process; run(c, &success, -14); cases += 1;
    }}}
    let mut c = Case::success("host-pte-error-is-ignored"); c.pte = -22;
    run(c, &success, -14); cases += 1;
    println!("PASS {cases} complete exec cases");
}}
