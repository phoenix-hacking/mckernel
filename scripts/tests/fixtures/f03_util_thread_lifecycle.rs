#![feature(c_variadic)]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// This fixture executes the real new body and unchanged initializer with the real
// Rust ABI declarations. Observation providers below are HOST test doubles only.

#[path = "@ABI@"]
mod abi;
#[path = "@PROVIDERS@"]
mod uti_data_providers;
#[path = "@BODY@"]
mod f03_util_thread;

use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of, addr_of_mut};
use std::alloc::{alloc, dealloc, Layout};
use std::ffi::CStr;
use std::sync::Mutex;

use abi::{CInt, CLong, CULong, CpuLocalVar, Process, Thread, UtiAttr, UtiCtx, UtiInfo, UtiKattr};

#[derive(Debug, PartialEq)]
enum Event {
    Current,
    Allocate(usize, i32),
    Physical(usize),
    Save,
    Submit,
    Joined,
    Profile,
    Free(usize, i32),
    Exit(i32),
    Terminate(i32, i32),
    Log(String),
}

struct State {
    thread: usize,
    process: usize,
    local: usize,
    allocation_call: usize,
    fail_allocation: usize,
    allocations: Vec<(usize, Layout)>,
    events: Vec<Event>,
    result: i64,
    cpu_calls: usize,
    attr: Option<Vec<u8>>,
    completed: bool,
    protect_exit: bool,
}

static STATE: Mutex<State> = Mutex::new(State {
    thread: 0, process: 0, local: 0, allocation_call: 0, fail_allocation: 0,
    allocations: Vec::new(), events: Vec::new(), result: 0, cpu_calls: 0,
    attr: None, completed: false, protect_exit: false,
});

#[no_mangle]
static mut idle_halt: CInt = -11;
#[no_mangle]
static mut uti_desc: CULong = 0x1020_3040_5060_7080;
const REFILL_TID: CInt = -77;
const PHYSICAL_XOR: u64 = 0x0100_0000_0000_0000;

fn physical(pointer: usize) -> u64 { pointer as u64 ^ PHYSICAL_XOR }
fn virtual_address(address: u64) -> usize { (address ^ PHYSICAL_XOR) as usize }

unsafe extern "C" {
    fn mmap(address: *mut c_void, size: usize, protection: i32, flags: i32,
            fd: i32, offset: i64) -> *mut c_void;
    fn mprotect(address: *mut c_void, size: usize, protection: i32) -> i32;
    fn munmap(address: *mut c_void, size: usize) -> i32;
}

fn page_span(size: usize) -> usize { (size + 4095) & !4095 }
struct Region { pointer: *mut c_void, bytes: usize }
impl Region {
    fn new<T>() -> Self {
        let bytes = page_span(size_of::<T>());
        let pointer = unsafe { mmap(core::ptr::null_mut(), bytes, 3, 0x22, -1, 0) };
        assert_ne!(pointer as usize, usize::MAX);
        assert_eq!(pointer as usize % align_of::<T>(), 0);
        Self { pointer, bytes }
    }
    fn readable(&self) {
        assert_eq!(unsafe { mprotect(self.pointer, self.bytes, 3) }, 0);
    }
}
impl Drop for Region {
    fn drop(&mut self) { assert_eq!(unsafe { munmap(self.pointer, self.bytes) }, 0); }
}

mod cls {
    use super::*;
    pub unsafe extern "C" fn get_this_cpu_local_var() -> *mut CpuLocalVar {
        let mut state = STATE.lock().unwrap();
        state.events.push(Event::Current);
        state.local as *mut CpuLocalVar
    }
}
mod x86_local {
    use super::*;
    pub unsafe extern "C" fn ihk_mc_get_processor_id() -> CInt {
        let mut state = STATE.lock().unwrap();
        state.cpu_calls += 1;
        // Distinct values prove the actual fresh second lookup is consumed.
        if state.cpu_calls == 1 { 3 } else { 7 }
    }
}
mod x86_memory_helpers {
    use super::*;
    pub unsafe extern "C" fn virt_to_phys(pointer: *mut c_void) -> CULong {
        STATE.lock().unwrap().events.push(Event::Physical(pointer as usize));
        physical(pointer as usize)
    }
}
mod futex {
    use super::*;
    pub unsafe extern "C" fn get_futex_queues() -> *mut abi::FutexHashBucket {
        0x5566_0000usize as *mut abi::FutexHashBucket
    }
}
mod mem_helpers {
    use super::*;
    pub unsafe extern "C" fn kmalloc_tracked(
        size: CInt, flags: CULong, file: *mut i8, line: CInt,
    ) -> *mut c_void {
        assert_eq!(flags, 2);
        assert_eq!(unsafe { CStr::from_ptr(file) }.to_bytes(), b"/src/kernel/syscall.c");
        let mut state = STATE.lock().unwrap();
        state.allocation_call += 1;
        let call = state.allocation_call;
        assert_eq!((size as usize, line),
                   if call == 1 { (4096, 28314) } else { (160, 28323) });
        state.events.push(Event::Allocate(size as usize, line));
        if call == state.fail_allocation { return core::ptr::null_mut(); }
        let layout = Layout::from_size_align(size as usize, 64).unwrap();
        let pointer = unsafe { alloc(layout) };
        assert!(!pointer.is_null());
        // Defined poison lets the observer detect any extra write/zeroing of the
        // original host-owned slots or padding without reading undefined bytes.
        unsafe { pointer.write_bytes(0xa5, size as usize) };
        state.allocations.push((pointer as usize, layout));
        pointer.cast()
    }
    pub unsafe extern "C" fn kfree_tracked(pointer: *mut c_void, file: *mut i8, line: CInt) {
        assert_eq!(unsafe { CStr::from_ptr(file) }.to_bytes(), b"/src/kernel/syscall.c");
        let mut state = STATE.lock().unwrap();
        state.events.push(Event::Free(pointer as usize, line));
        if pointer.is_null() { return; }
        if state.completed {
            // Refill must already be copied while the actual source allocation
            // is alive. No fixture context/refill value is supplied by the body.
            let thread = state.thread as *const Thread;
            assert_eq!(unsafe { addr_of!((*thread).uti_refill_tid).read() }, REFILL_TID);
        }
        let position = state.allocations.iter().position(|row| row.0 == pointer as usize)
            .expect("free must release exactly one owned allocation");
        let (_, layout) = state.allocations.remove(position);
        unsafe { dealloc(pointer.cast(), layout) };
    }
}
mod syscall_policy {
    use super::*;
    pub unsafe extern "C" fn save_uctx(pointer: *mut c_void, regs: *mut abi::X86UserContext) {
        assert!(regs.is_null());
        let mut state = STATE.lock().unwrap();
        assert_eq!(state.allocations[0].0, pointer as usize);
        state.events.push(Event::Save);
        unsafe { pointer.cast::<i32>().write(0) };
    }
    @PROXY_RESULT@
    pub unsafe extern "C" fn util_show_syscall_profile() -> CInt {
        let mut state = STATE.lock().unwrap();
        let thread = state.thread as *const Thread;
        assert_eq!(unsafe { addr_of!((*thread).uti_state).read() }, 3);
        assert_eq!(state.allocations.len(), 2);
        state.events.push(Event::Profile);
        0
    }
    pub unsafe extern "C" fn f03_do_exit_supported_v2(code: CInt) {
        let mut state = STATE.lock().unwrap();
        assert!(state.allocations.is_empty());
        let process = state.process as *const Process;
        assert_eq!(unsafe { addr_of!((*process).nohost).read() },
                   if state.result == -512 { 1 } else { 0 });
        state.events.push(Event::Exit(code));
        drop(state);
        protect_released_owners();
    }
    unsafe extern "C" {
        #[link_name = "util_thread"]
        fn f03_util_thread_entry(argument: *mut UtiAttr) -> CInt;
    }
    @BRIDGE@
}
mod f03_terminate {
    use super::*;
    pub unsafe extern "C" fn terminate(status: CInt, signal: CInt) {
        let mut state = STATE.lock().unwrap();
        assert!(state.allocations.is_empty());
        let process = state.process as *const Process;
        assert_eq!(unsafe { addr_of!((*process).nohost).read() }, 1);
        state.events.push(Event::Terminate(status, signal));
        drop(state);
        protect_released_owners();
    }
}

fn protect_released_owners() {
    let state = STATE.lock().unwrap();
    if state.protect_exit {
        // Real HOST VM protection detects any Thread/Process access after the
        // original void provider could have released both owners and returned.
        assert_eq!(unsafe { mprotect(state.thread as *mut c_void,
                                    page_span(size_of::<Thread>()), 0) }, 0);
        assert_eq!(unsafe { mprotect(state.process as *mut c_void,
                                    page_span(size_of::<Process>()), 0) }, 0);
    }
}

mod debug {
    use super::*;
    @DDEBUG@
    pub unsafe extern "C" fn kprintf(format: *const i8, mut arguments: ...) -> CInt {
        let format = unsafe { CStr::from_ptr(format) }.to_str().unwrap();
        let function = unsafe { CStr::from_ptr(arguments.arg::<*const i8>()) };
        assert_eq!(function.to_bytes(), b"util_thread");
        let state = STATE.lock().unwrap();
        match format {
            "%s: returned from do_syscall,tid=%d,rc=%lx\n" |
            "%s: exit_group, tid=%d,rc=%lx\n" => {
                assert_eq!(unsafe { arguments.arg::<CInt>() }, 123);
                assert_eq!(unsafe { arguments.arg::<CLong>() }, state.result);
            }
            "%s: mcexec worker tid=%d\n" => {
                assert_eq!(unsafe { arguments.arg::<CInt>() }, REFILL_TID);
            }
            "%s: exit or killed by signal, pid=%d,tid=%d,rc=%lx\n" |
            "%s: release_handler,pid=%d,tid=%d,rc=%lx\n" => {
                assert_eq!(unsafe { arguments.arg::<CInt>() }, 321);
                assert_eq!(unsafe { arguments.arg::<CInt>() }, 123);
                assert_eq!(unsafe { arguments.arg::<CLong>() }, state.result);
            }
            "%s: ERROR: do_syscall() failed (%ld)\n" => {
                assert_eq!(unsafe { arguments.arg::<CLong>() }, state.result);
            }
            other => panic!("unexpected original diagnostic: {other}"),
        }
        drop(state);
        STATE.lock().unwrap().events.push(Event::Log(format.into()));
        0
    }
}

mod syscall_offload_entry {
    use super::*;
    pub unsafe extern "C" fn do_syscall(request: *mut abi::SyscallRequest, cpu: CInt) -> CLong {
        assert_eq!(cpu, 7);
        assert_eq!(request as usize % 8, 0);
        let mut state = STATE.lock().unwrap();
        assert_eq!(state.allocations.len(), 2);
        assert_eq!(state.cpu_calls, 2);
        let thread = state.thread as *const Thread;
        assert_eq!(unsafe { addr_of!((*thread).uti_state).read() }, 2);
        state.events.push(Event::Submit);
        // The real transport owns these header stores; the caller supplies all
        // six arguments. Never read the uninitialized header before this point.
        unsafe {
            addr_of_mut!((*request).rtid).write(123);
            addr_of_mut!((*request).ttid).write(123);
            addr_of_mut!((*request).valid).write(0);
        }
        let address = request as usize;
        let result = state.result;
        drop(state);
        std::thread::spawn(move || {
            std::thread::yield_now();
            let request = address as *const abi::SyscallRequest;
            let state = STATE.lock().unwrap();
            let context = state.allocations[0].0 as *mut UtiCtx;
            let info = state.allocations[1].0 as *const UtiInfo;
            let thread = state.thread as *const Thread;
            let local = state.local as *const CpuLocalVar;
            assert_eq!(unsafe { addr_of!((*request).number).read() }, 203);
            let args = unsafe { addr_of!((*request).args).read() };
            assert_eq!(args[0], 0);
            assert_eq!(args[1], physical(context as usize));
            assert_eq!(args[3], info as u64);
            assert_eq!(args[4], 0x1020_3040_5060_7080);
            assert_eq!(args[5], 0);
            match &state.attr {
                None => assert_eq!(args[2], 0),
                Some(expected) => {
                    let attribute = virtual_address(args[2]) as *const UtiKattr;
                    assert_eq!(unsafe { addr_of!((*attribute).parent_cpuid).read() }, -17);
                    assert_eq!(unsafe { std::slice::from_raw_parts(
                        addr_of!((*attribute).attr).cast::<u8>(), size_of::<UtiAttr>()) }, expected);
                }
            }
            unsafe {
                assert_eq!(addr_of!((*info).thread_va).read(), thread as u64);
                assert_eq!(addr_of!((*info).uti_futex_resp_pa).read(), physical(0x1122_0000));
                assert_eq!(addr_of!((*info).ikc2linux_pa).read(), physical(0x3344_0000));
                assert_eq!(addr_of!((*info).tid).read(), 123);
                assert_eq!(addr_of!((*info).cpu).read(), 3);
                assert_eq!(addr_of!((*info).status_pa).read(), physical(addr_of!((*thread).status) as usize));
                assert_eq!(addr_of!((*info).spin_sleep_lock_pa).read(),
                           physical(addr_of!((*thread).spin_sleep_lock) as usize));
                assert_eq!(addr_of!((*info).spin_sleep_pa).read(), physical(addr_of!((*thread).spin_sleep) as usize));
                assert_eq!(addr_of!((*info).vm_pa).read(), physical(0x7788_0000));
                assert_eq!(addr_of!((*info).futex_q_pa).read(), physical(addr_of!((*thread).futex_q) as usize));
                assert_eq!(addr_of!((*info).mc_idle_halt).read(), -11);
                assert_eq!(addr_of!((*info).futex_queue_pa).read(), physical(0x5566_0000));
                assert_eq!(addr_of!((*local).current).read(), thread as *mut Thread);
            }
            // Independent allowed-write mask for all nine host-owned fields and
            // the four-byte alignment gap; no whole initialized value is read.
            for offset in [offset_of!(UtiInfo, uti_futex_resp), offset_of!(UtiInfo, ikc2linux),
                           offset_of!(UtiInfo, status), offset_of!(UtiInfo, spin_sleep_lock),
                           offset_of!(UtiInfo, spin_sleep), offset_of!(UtiInfo, vm),
                           offset_of!(UtiInfo, futex_q), offset_of!(UtiInfo, futex_queue),
                           offset_of!(UtiInfo, os)] {
                let bytes = unsafe { std::slice::from_raw_parts(info.cast::<u8>().add(offset), 8) };
                assert_eq!(bytes, &[0xa5; 8]);
            }
            let gap = offset_of!(UtiInfo, mc_idle_halt) + size_of::<CInt>();
            assert_eq!(unsafe { std::slice::from_raw_parts(info.cast::<u8>().add(gap), 4) }, &[0xa5; 4]);
            assert_eq!(unsafe { context.cast::<u8>().add(4095).read() }, 0xa5);
            unsafe { addr_of_mut!((*context).refill.uti_refill_tid).write(REFILL_TID) };
        }).join().expect("the synchronous peer must finish all borrowed addresses");
        let mut state = STATE.lock().unwrap();
        state.completed = true;
        state.events.push(Event::Joined);
        result
    }
}

fn run(result: i64, attr: bool, failure: usize, protect_exit: bool, bridge: bool) {
    let thread_region = Region::new::<Thread>();
    let process_region = Region::new::<Process>();
    let local_region = Region::new::<CpuLocalVar>();
    let thread = thread_region.pointer.cast::<Thread>();
    let process = process_region.pointer.cast::<Process>();
    let local = local_region.pointer.cast::<CpuLocalVar>();
    unsafe {
        addr_of_mut!((*thread).proc).write(process);
        addr_of_mut!((*thread).tid).write(123);
        addr_of_mut!((*thread).parent_cpuid).write(-17);
        addr_of_mut!((*thread).vm).write(0x7788_0000usize as *mut abi::ProcessVm);
        addr_of_mut!((*process).pid).write(321);
        addr_of_mut!((*local).current).write(thread);
        addr_of_mut!((*local).uti_futex_resp).write(0x1122_0000usize as *mut c_void);
        addr_of_mut!((*local).ikc2linux).write(0x3344_0000usize as _);
    }
    let mut argument = UtiAttr { numa_set: [0x8899_aabb_ccdd_eeff; abi::UTI_NUMA_SET_WORDS],
                                 flags: 0xfedc_ba98_7654_3210 };
    let argument_pointer = if attr { addr_of_mut!(argument) } else { core::ptr::null_mut() };
    {
        let mut state = STATE.lock().unwrap();
        assert!(state.allocations.is_empty());
        state.thread = thread as usize;
        state.process = process as usize;
        state.local = local as usize;
        state.allocation_call = 0;
        state.fail_allocation = failure;
        state.events.clear();
        state.result = result;
        state.cpu_calls = 0;
        state.attr = if attr { Some(unsafe { std::slice::from_raw_parts(
            addr_of!(argument).cast::<u8>(), size_of::<UtiAttr>()) }.to_vec()) } else { None };
        state.completed = false;
        state.protect_exit = protect_exit;
    }
    let actual = if bridge {
        unsafe { syscall_policy::syscall_util_thread_bridge(argument_pointer.cast()) }
    } else {
        unsafe { f03_util_thread::util_thread(argument_pointer) as CLong }
    };
    thread_region.readable();
    process_region.readable();
    assert_eq!(actual, if failure != 0 { -12 } else { result as i32 as i64 });
    let state = STATE.lock().unwrap();
    assert!(state.allocations.is_empty());
    let frees: Vec<_> = state.events.iter().filter_map(|event| match event {
        Event::Free(pointer, line) => Some((*pointer, *line)), _ => None,
    }).collect();
    if failure != 0 {
        assert_eq!(unsafe { addr_of!((*thread).uti_state).read() }, 1);
        assert_eq!(frees.len(), 2);
        assert_eq!((frees[0].1, frees[1].1), (28397, 28398));
        assert_eq!(frees[0].0 == 0, failure == 1);
        assert_eq!(frees[1].0, 0);
        assert!(!state.events.contains(&Event::Submit));
        assert!(!state.events.contains(&Event::Profile));
    } else {
        assert_eq!(unsafe { addr_of!((*thread).uti_state).read() }, 3);
        assert_eq!(unsafe { addr_of!((*thread).uti_refill_tid).read() }, REFILL_TID);
        assert_eq!(frees.len(), 4);
        assert_ne!(frees[0].0, 0);
        assert_ne!(frees[1].0, 0);
        assert_eq!((frees[0].1, frees[1].1), (28371, 28374));
        assert_eq!(&frees[2..], &[(0, 28397), (0, 28398)]);
        assert_eq!(state.events.iter().filter(|e| **e == Event::Current).count(), 4);
        assert_eq!(state.cpu_calls, 2);
        let joined = state.events.iter().position(|e| *e == Event::Joined).unwrap();
        let profiled = state.events.iter().position(|e| *e == Event::Profile).unwrap();
        let released = state.events.iter().position(|e| matches!(e, Event::Free(_, 28371))).unwrap();
        assert!(joined < profiled && profiled < released);
        let exits: Vec<_> = state.events.iter().filter(|e|
            matches!(e, Event::Exit(_) | Event::Terminate(_, _))).collect();
        if result >= 0 && result & 0x1_0000_0000 != 0 {
            assert_eq!(exits, vec![&Event::Terminate(((result >> 8) & 255) as i32,
                                                  (result & 255) as i32)]);
        } else if result >= 0 || result == -512 {
            assert_eq!(exits, vec![&Event::Exit(result as i32)]);
        } else {
            assert!(exits.is_empty());
            assert_eq!(unsafe { addr_of!((*process).nohost).read() }, 0);
        }
    }
}

#[test]
fn both_allocation_failures_preserve_prologue_and_ordered_null_cleanup() {
    for failure in [1, 2] { run(0, false, failure, false, false); }
}
#[test]
fn normal_and_group_exits_preserve_status_bits_and_allow_void_provider_return() {
    for result in [0, 9, 0x7f00, 0x1_0000_0000, 0x1_0000_7f09, 0x7fff_ffff] {
        run(result, false, 0, true, false);
    }
}
#[test]
fn proxy_death_alone_sets_nohost_and_other_negative_errors_return_unchanged() {
    for result in [-512, -1, -12, -513, i32::MIN as i64, -0x1_0000_0001] {
        run(result, false, 0, result == -512, false);
    }
}
#[test]
fn attributes_keep_full_bitmap_flags_signed_parent_and_borrowed_stack_lifetime() {
    for result in [-5, -512, 0, 0x1_0000_0309] { run(result, true, 0, true, false); }
}
#[test]
fn actual_bridge_sign_extends_the_original_int_return_including_truncation() {
    for result in [-1, -512, -0x1_0000_0001, 0x8000_0000, 0xffff_ffff] {
        run(result, true, 0, true, true);
    }
}
