//! Changed memory-host/offload composition; explicit HOST-only lower effects.
#![feature(c_variadic)]
#![deny(warnings)]

use core::{ffi::c_void, mem::{align_of, offset_of, size_of}, ptr::addr_of_mut};
use std::{alloc::{alloc_zeroed, dealloc, handle_alloc_error, Layout}, cell::RefCell};
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
#[path = "production_slices.rs"]
mod syscall_policy;
#[path = "production_setters.rs"]
mod x86_cpu_helpers;
// Written only as a byte-identical copy of the independently reviewed correction.
mod production_memory_provider;
use abi::{CInt, CLong, CULong, CpuLocalVar, Process, ProcessVm, SizeT, SyscallRequest, Thread};

const ADDR: u64 = 0x7fff_2345_6000;
const LEN: usize = 8192;
const WIDE: i64 = 0x1_0000_0005;

struct Slot<T>(*mut T);
impl<T> Slot<T> {
    fn new() -> Self {
        let layout = Layout::new::<T>();
        assert!(layout.size() > 0);
        let pointer = unsafe { alloc_zeroed(layout).cast::<T>() };
        if pointer.is_null() { handle_alloc_error(layout); }
        Self(pointer)
    }
}
impl<T> Drop for Slot<T> {
    fn drop(&mut self) { unsafe { dealloc(self.0.cast(), Layout::new::<T>()) }; }
}

struct Model {
    cpu: usize,
    vm: usize,
    number: CInt,
    args: [u64; 3],
    result: CLong,
    expected_flag: CInt,
    error_log: Option<(CLong, CInt)>,
    remove_error: CInt,
    ro_freed: CInt,
    events: Vec<&'static str>,
    requests: Vec<String>,
    forward_flags: Vec<CInt>,
    error_rows: Vec<String>,
    cpu_calls: usize,
}
thread_local! {
    static MODEL: RefCell<Model> = const { RefCell::new(Model {
        cpu: 0, vm: 0, number: 0, args: [0; 3], result: 0, expected_flag: 17,
        error_log: None, remove_error: 0, ro_freed: 0, events: Vec::new(),
        requests: Vec::new(), forward_flags: Vec::new(), error_rows: Vec::new(), cpu_calls: 0,
    }) };
}
fn flag(model: &Model) -> i32 {
    assert_ne!(model.vm, 0);
    unsafe { (*(model.vm as *const ProcessVm)).is_memory_range_lock_taken }
}
mod cls {
    pub unsafe extern "C" fn get_this_cpu_local_var() -> *mut super::CpuLocalVar {
        super::MODEL.with(|m| {
            let pointer = m.borrow().cpu;
            assert_ne!(pointer, 0);
            pointer as *mut super::CpuLocalVar
        })
    }
}
// Explicit test-only CPU effect; no HOST kernel GS/IRQ/current-thread access.
mod x86_local {
    pub unsafe extern "C" fn ihk_mc_get_processor_id() -> super::CInt {
        super::MODEL.with(|m| {
            let mut model = m.borrow_mut();
            model.events.push("cpu");
            model.cpu_calls += 1;
        });
        6
    }
}

// Real C-variadic call convention; only the diagnostic sink is test-only.
// It checks the complete literal and full-width signed long after flag restore.
mod debug {
    pub unsafe extern "C" fn kprintf(format: *const i8, mut arguments: ...) -> super::CInt {
        let literal = unsafe { std::ffi::CStr::from_ptr(format).to_bytes_with_nul() };
        assert_eq!(literal, b"clear_host_pte failed. %ld\n\0");
        let error = unsafe { arguments.arg::<super::CLong>() };
        super::MODEL.with(|m| {
            let mut model = m.borrow_mut();
            let observed_flag = super::flag(&model);
            assert_eq!(model.error_log, Some((error, observed_flag)));
            model.events.push("error-log");
            model.error_rows.push(format!("{{\"error\":{error},\"flag\":{observed_flag}}}"));
        });
        0
    }
}

fn expected_request(number: CInt, args: [u64; 3]) -> [u8; 72] {
    let mut result = [0; 72];
    result[16..24].copy_from_slice(&(number as u64).to_le_bytes());
    for (i, value) in args.iter().enumerate() {
        result[24 + i * 8..32 + i * 8].copy_from_slice(&value.to_le_bytes());
    }
    result
}
// Test-only transport, not an actual selected provider or native reply.
#[no_mangle]
unsafe extern "C" fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong {
    assert_eq!(cpu, 6);
    assert!(!request.is_null());
    assert_eq!(request as usize % align_of::<SyscallRequest>(), 0);
    assert_eq!(size_of::<SyscallRequest>(), 72);
    MODEL.with(|m| {
        let mut model = m.borrow_mut();
        assert!(model.requests.is_empty(), "one synchronous transaction per row");
        let observed_flag = flag(&model);
        assert_eq!(observed_flag, model.expected_flag);
        let mut bytes = [0; 72];
        unsafe { core::ptr::copy_nonoverlapping(request.cast::<u8>(), bytes.as_mut_ptr(), 72) };
        assert_eq!(bytes, expected_request(model.number, model.args));
        model.events.push("forward");
        model.requests.push(bytes.iter().map(|byte| format!("{byte:02x}")).collect());
        model.forward_flags.push(observed_flag);
        // The stack allocation remains valid until this synchronous return.
        unsafe {
            addr_of_mut!((*request).rtid).write(77);
            addr_of_mut!((*request).ttid).write(79);
            assert_eq!((*request).rtid, 77);
            assert_eq!((*request).ttid, 79);
            assert_eq!((*request).valid, 0);
        }
        model.result
    })
}

// Explicit test-only metadata tables with the actual repr(C) callback shapes.
// Changed behavior pointers are genuine full production functions. These are
// not the actual C runtime binding definitions and earn no provider-selection proof.
#[repr(C)]
struct ClearBinding {
    number: CInt,
    forward: Option<unsafe extern "C" fn(CInt, CULong, CULong, CULong) -> CLong>,
    log: Option<unsafe extern "C" fn(CLong)>,
}
#[no_mangle]
static f03_clear_host_pte_binding_v1: ClearBinding = ClearBinding {
    number: 11,
    forward: Some(production_memory_provider::syscall_do_syscall3_bridge),
    log: Some(production_memory_provider::clear_host_pte_log_bridge),
};
#[repr(C)]
struct UnmapBinding {
    begin: Option<unsafe extern "C" fn()>,
    remove: Option<unsafe extern "C" fn(*mut c_void, CULong, CULong, *mut CInt) -> CInt>,
    clear: Option<unsafe extern "C" fn(CULong, SizeT, CInt) -> CLong>,
    set: Option<unsafe extern "C" fn(CULong, SizeT, CInt, CInt) -> CInt>,
    finish: Option<unsafe extern "C" fn()>,
    log: Option<unsafe extern "C" fn(CULong, SizeT, CInt)>,
}
#[no_mangle]
static f03_do_munmap_binding_v1: UnmapBinding = UnmapBinding {
    begin: Some(begin), remove: Some(remove),
    clear: Some(production_memory_provider::do_munmap_clear_host_bridge),
    set: Some(production_memory_provider::do_munmap_set_host_bridge),
    finish: Some(finish), log: Some(unmap_log),
};
unsafe extern "C" fn begin() { MODEL.with(|m| m.borrow_mut().events.push("begin")); }
unsafe extern "C" fn remove(vm: *mut c_void, start: u64, end: u64, ro: *mut i32) -> i32 {
    MODEL.with(|m| {
        let mut model = m.borrow_mut();
        assert_eq!(vm as usize, model.vm);
        assert_eq!((start, end), (ADDR, ADDR + LEN as u64));
        assert!(!ro.is_null());
        unsafe { ro.write(model.ro_freed) };
        model.events.push("remove");
        model.remove_error
    })
}
unsafe extern "C" fn finish() { MODEL.with(|m| m.borrow_mut().events.push("finish")); }
unsafe extern "C" fn unmap_log(addr: u64, len: usize, _result: i32) {
    assert_eq!((addr, len), (ADDR, LEN));
    MODEL.with(|m| m.borrow_mut().events.push("unmap-log"));
}
unsafe extern "C" { fn do_munmap(addr: *mut c_void, len: usize, held: i32) -> i32; }

struct Case {
    id: &'static str,
    kind: u8,
    number: i32,
    args: [u64; 3],
    provider_result: i64,
    result: i64,
    held: i32,
    forward_flag: i32,
    final_flag: i32,
    error_log: Option<(i64, i32)>,
    remove_error: i32,
    ro_freed: i32,
    straight: bool,
    events: &'static [&'static str],
}
const CASES: [Case; 9] = [
    Case { id: "direct3-setitimer-high-arg2", kind: 0, number: 38, args: [0x8000_0000_0000_0001, 0x7fff_1234_5000, 0xffff_eeee_dddd_cccc], provider_result: -14, result: -14, held: 0, forward_flag: 17, final_flag: 17, error_log: None, remove_error: 0, ro_freed: 0, straight: false, events: &["cpu", "forward"] },
    Case { id: "policy3-signed-number-return", kind: 1, number: -1, args: [u64::MAX, 0x8000_0000_0000_0000, 0xfedc_ba98_7654_3210], provider_result: i64::MIN + 7, result: i64::MIN + 7, held: 0, forward_flag: 17, final_flag: 17, error_log: None, remove_error: 0, ro_freed: 0, straight: false, events: &["cpu", "forward"] },
    Case { id: "clear-unheld-wide-nonzero-log", kind: 2, number: 11, args: [ADDR, LEN as u64, 0], provider_result: WIDE, result: WIDE, held: 0, forward_flag: 17, final_flag: 17, error_log: Some((WIDE, 17)), remove_error: 0, ro_freed: 0, straight: false, events: &["cpu", "cpu", "forward", "error-log"] },
    Case { id: "clear-held-success-quiet", kind: 2, number: 11, args: [ADDR, LEN as u64, 0], provider_result: 0, result: 0, held: 1, forward_flag: 6, final_flag: -1, error_log: None, remove_error: 0, ro_freed: 0, straight: false, events: &["cpu", "cpu", "forward"] },
    Case { id: "set-unheld-error-quiet", kind: 3, number: 11, args: [ADDR, LEN as u64, 0], provider_result: -14, result: -14, held: 0, forward_flag: 17, final_flag: 17, error_log: None, remove_error: 0, ro_freed: 0, straight: false, events: &["cpu", "cpu", "forward"] },
    Case { id: "unmap-remove-error-precedence", kind: 4, number: 11, args: [ADDR, LEN as u64, 0], provider_result: -14, result: -12, held: 1, forward_flag: 6, final_flag: -1, error_log: Some((-14, -1)), remove_error: -12, ro_freed: 0, straight: false, events: &["begin", "remove", "cpu", "cpu", "forward", "error-log", "finish", "unmap-log"] },
    Case { id: "unmap-clear-error-result", kind: 4, number: 11, args: [ADDR, LEN as u64, 0], provider_result: -14, result: -14, held: 0, forward_flag: 17, final_flag: 17, error_log: Some((-14, 17)), remove_error: 0, ro_freed: 0, straight: false, events: &["begin", "remove", "cpu", "cpu", "forward", "error-log", "finish", "unmap-log"] },
    Case { id: "unmap-ro-set-wide-int-quiet", kind: 4, number: 11, args: [ADDR, LEN as u64, 0], provider_result: WIDE, result: 5, held: 1, forward_flag: 6, final_flag: -1, error_log: None, remove_error: 0, ro_freed: 1, straight: false, events: &["begin", "remove", "cpu", "cpu", "forward", "finish", "unmap-log"] },
    Case { id: "unmap-straight-suppresses-host", kind: 4, number: 11, args: [ADDR, LEN as u64, 0], provider_result: -14, result: 0, held: 1, forward_flag: 6, final_flag: 17, error_log: None, remove_error: 0, ro_freed: 0, straight: true, events: &["begin", "remove", "finish", "unmap-log"] },
];

fn main() {
    assert_eq!((size_of::<ClearBinding>(), align_of::<ClearBinding>()), (24, 8));
    assert_eq!((offset_of!(ClearBinding, forward), offset_of!(ClearBinding, log)), (8, 16));
    assert_eq!((size_of::<UnmapBinding>(), align_of::<UnmapBinding>()), (48, 8));
    assert_eq!((offset_of!(UnmapBinding, clear), offset_of!(UnmapBinding, set)), (16, 24));
    let cpu = Slot::<CpuLocalVar>::new();
    let thread = Slot::<Thread>::new();
    let vm = Slot::<ProcessVm>::new();
    let process = Slot::<Process>::new();
    unsafe {
        addr_of_mut!((*cpu.0).current).write(thread.0);
        addr_of_mut!((*thread.0).vm).write(vm.0);
        addr_of_mut!((*thread.0).proc).write(process.0);
    }
    let mut rows = Vec::new();
    for case in CASES {
        unsafe {
            addr_of_mut!((*vm.0).is_memory_range_lock_taken).write(17);
            addr_of_mut!((*process.0).straight_va).write(if case.straight { ADDR as *mut c_void } else { core::ptr::null_mut() });
            addr_of_mut!((*process.0).straight_len).write(LEN);
        }
        MODEL.with(|m| *m.borrow_mut() = Model {
            cpu: cpu.0 as usize, vm: vm.0 as usize, number: case.number, args: case.args,
            result: case.provider_result, expected_flag: case.forward_flag,
            error_log: case.error_log, remove_error: case.remove_error, ro_freed: case.ro_freed,
            events: Vec::new(), requests: Vec::new(), forward_flags: Vec::new(), error_rows: Vec::new(), cpu_calls: 0,
        });
        let result = unsafe { match case.kind {
            0 => production_memory_provider::syscall_do_syscall3_bridge(case.number, case.args[0], case.args[1], case.args[2]),
            1 => production_memory_provider::syscall_policy_do_syscall3_bridge(case.number, case.args[0], case.args[1], case.args[2]),
            2 => production_memory_provider::do_munmap_clear_host_bridge(ADDR, LEN, case.held),
            3 => production_memory_provider::do_munmap_set_host_bridge(ADDR, LEN, 5, case.held) as i64,
            4 => do_munmap(ADDR as *mut c_void, LEN, case.held) as i64,
            _ => unreachable!(),
        }};
        MODEL.with(|m| {
            let model = m.borrow();
            assert_eq!(result, case.result, "{}", case.id);
            assert_eq!(flag(&model), case.final_flag, "{}", case.id);
            assert_eq!(model.events, case.events, "{}", case.id);
            assert_eq!(model.error_rows.len(), usize::from(case.error_log.is_some()));
            assert_eq!(model.requests.len(), usize::from(!case.straight));
            let quoted_events = model.events.iter().map(|e| format!("\"{e}\"")).collect::<Vec<_>>().join(",");
            let quoted_requests = model.requests.iter().map(|e| format!("\"{e}\"")).collect::<Vec<_>>().join(",");
            let flags = model.forward_flags.iter().map(i32::to_string).collect::<Vec<_>>().join(",");
            rows.push(format!("{{\"id\":\"{}\",\"return\":{},\"final_flag\":{},\"cpu_lookups\":{},\"forward_flags\":[{}],\"requests\":[{}],\"error_logs\":[{}],\"events\":[{}]}}", case.id, result, flag(&model), model.cpu_calls, flags, quoted_requests, model.error_rows.join(","), quoted_events));
        });
    }
    MODEL.with(|m| { let mut model = m.borrow_mut(); model.cpu = 0; model.vm = 0; });
    println!("{{\"status\":\"PASS\",\"scope\":\"corrected-memory-host-production-composition-with-explicit-test-only-effects\",\"case_count\":9,\"kernel_runtime\":false,\"native_execution\":false,\"actual_provider_binding\":false,\"cases\":[{}]}}", rows.join(","));
}
