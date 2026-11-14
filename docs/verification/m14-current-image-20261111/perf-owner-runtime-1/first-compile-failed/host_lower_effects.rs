// HOST-only lower primitives for the actual perf ownership runtime fixture.
// ABI: kernel/rust/abi.rs ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e.
// Actual ownership bodies remain the coherent compiler-scheduler cbea/23c297 source.
// No reference/group/lifetime decisions, hardware/IRQ/GS instructions or scenario
// oracle exist here. Common fixture, actual waitq/schedule and all cases are P04's.
use core::cell::{RefCell, UnsafeCell};
use core::ffi::c_void;
use core::mem::{align_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, null_mut};
use std::alloc::{alloc, dealloc, Layout};
use std::collections::{BTreeMap, VecDeque};
use std::ffi::CStr;
use std::sync::{Condvar, Mutex, MutexGuard, OnceLock};
use std::thread::ThreadId;
use crate::abi::{CInt, CLong, CULong, CpuLocalVar, Mckfd, Process,
    SyscallRequest, Thread, X86UserContext};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum LockClass { Process, Registry, State }
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HeldLock {
    pub address: usize,
    pub class: LockClass,
    pub saved_flags: Option<CULong>,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AllocationRecord {
    pub id: u64,
    pub address: usize,
    pub size: usize,
    pub flags: CULong,
    pub file: Vec<u8>,
    pub line: CInt,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Effect {
    Alloc { record: AllocationRecord },
    AllocFailed { size: CInt, flags: CULong, file: Vec<u8>, line: CInt },
    Free { record: AllocationRecord, file: Vec<u8>, line: CInt },
    FreeNull { file: Vec<u8>, line: CInt },
    Lock { lock: HeldLock },
    Unlock { lock: HeldLock },
    HostReply { request: [u8; 72], cpu: CInt, thread: usize, process: usize, result: CLong },
    ForwardClose { number: CInt, arg0: CULong, context: usize, thread: usize,
        process: usize, result: CLong },
    HashFind { pid: CInt, process: usize, node: usize },
    HashUnlock { process: usize, node: usize },
    ProcessRegistered { pid: CInt, process: usize },
    Marker(String),
}
struct Allocation { record: AllocationRecord, layout: Layout }
struct State {
    trace: Vec<Effect>,
    allocations: BTreeMap<usize, Allocation>,
    next_allocation_id: u64,
    fail_next_allocation: bool,
    lock_classes: BTreeMap<usize, LockClass>,
    lock_owners: BTreeMap<usize, ThreadId>,
    host_replies: VecDeque<CLong>,
    forward_replies: VecDeque<CLong>,
    processes: BTreeMap<CInt, usize>,
}
impl Default for State {
    fn default() -> Self {
        Self { trace: Vec::new(), allocations: BTreeMap::new(), next_allocation_id: 1,
            fail_next_allocation: false, lock_classes: BTreeMap::new(),
            lock_owners: BTreeMap::new(), host_replies: VecDeque::new(),
            forward_replies: VecDeque::new(), processes: BTreeMap::new() }
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct HashBorrow { pub process: usize, pub node: usize, saved_flags: CULong }
struct Local { held: Vec<HeldLock>, hash: Vec<HashBorrow>, irq_enabled: bool }
impl Default for Local {
    fn default() -> Self { Self { held: Vec::new(), hash: Vec::new(), irq_enabled: true } }
}
thread_local! {
    static CPU: UnsafeCell<MaybeUninit<CpuLocalVar>> = const { UnsafeCell::new(MaybeUninit::zeroed()) };
    static LOCAL: RefCell<Local> = RefCell::new(Local::default());
}
fn global() -> &'static (Mutex<State>, Condvar) {
    static DATA: OnceLock<(Mutex<State>, Condvar)> = OnceLock::new();
    DATA.get_or_init(|| (Mutex::new(State::default()), Condvar::new()))
}
fn state() -> MutexGuard<'static, State> {
    global().0.lock().unwrap_or_else(|error| error.into_inner())
}
fn trace(effect: Effect) { state().trace.push(effect); }
pub fn snapshot() -> Vec<Effect> { state().trace.clone() }
pub fn live_allocations() -> Vec<AllocationRecord> {
    state().allocations.values().map(|value| value.record.clone()).collect()
}
pub fn held_locks() -> Vec<HeldLock> { LOCAL.with(|local| local.borrow().held.clone()) }
pub fn hash_borrows_held() -> Vec<HashBorrow> { LOCAL.with(|local| local.borrow().hash.clone()) }
pub fn irq_enabled() -> bool { LOCAL.with(|local| local.borrow().irq_enabled) }
pub fn marker(name: &str) { trace(Effect::Marker(name.to_owned())); }

/// Reset only observation scripts/trace. Never free a live allocation, clear a
/// production registry, reset an allocation ID, or mutate an ownership body.
pub fn reset_trace() {
    assert_effects_unlocked("reset_trace");
    let mut state = state();
    state.trace.clear(); state.host_replies.clear(); state.forward_replies.clear();
    state.fail_next_allocation = false;
}
pub fn set_host_replies(replies: &[CLong]) {
    assert_effects_unlocked("set_host_replies");
    state().host_replies = replies.iter().copied().collect();
}
pub fn set_forward_replies(replies: &[CLong]) {
    assert_effects_unlocked("set_forward_replies");
    state().forward_replies = replies.iter().copied().collect();
}
pub fn fail_next_allocation() {
    assert_effects_unlocked("fail_next_allocation"); state().fail_next_allocation = true;
}
pub fn assert_effects_unlocked(operation: &str) {
    LOCAL.with(|local| {
        let local = local.borrow();
        assert!(local.held.is_empty(), "{operation} under tracked P/R/S exclusion: {:?}", local.held);
        assert!(local.hash.is_empty(), "{operation} under raw hash-reader borrow");
    });
}
pub fn register_lock(lock: *mut crate::abi::IhkSpinlock, class: LockClass) {
    assert_effects_unlocked("register_lock");
    assert!(!lock.is_null());
    let mut state = state();
    assert!(!state.lock_owners.contains_key(&(lock as usize)), "reclassifying a held lock");
    state.lock_classes.insert(lock as usize, class);
}
pub fn register_p_lock(lock: *mut crate::abi::IhkSpinlock) { register_lock(lock, LockClass::Process); }

pub unsafe fn set_current(thread: *mut Thread) {
    assert_effects_unlocked("set_current");
    CPU.with(|cpu| unsafe { addr_of_mut!((*(*cpu.get()).as_mut_ptr()).current).write(thread) });
}
unsafe fn cpu_local() -> *mut CpuLocalVar { CPU.with(|cpu| unsafe { (*cpu.get()).as_mut_ptr() }) }
fn current_route() -> (usize, usize) {
    let cpu = unsafe { cpu_local() };
    let thread = unsafe { addr_of!((*cpu).current).read() };
    let process = if thread.is_null() { null_mut() } else { unsafe { addr_of!((*thread).proc).read() } };
    (thread as usize, process as usize)
}
pub(crate) mod cls {
    pub unsafe extern "C" fn get_this_cpu_local_var() -> *mut crate::abi::CpuLocalVar {
        unsafe { super::cpu_local() }
    }
}
pub(crate) mod x86_local {
    pub unsafe extern "C" fn ihk_mc_get_processor_id() -> crate::abi::CInt { 0 }
}

unsafe fn origin(file: *mut i8) -> Vec<u8> {
    assert!(!file.is_null(), "tracked allocator origin absent");
    let bytes = unsafe { CStr::from_ptr(file) }.to_bytes();
    assert!(bytes.len() <= 4096, "tracked allocator origin bound");
    bytes.to_vec()
}
fn allocation_alignment() -> usize {
    [align_of::<Thread>(), align_of::<Process>(), align_of::<CpuLocalVar>(),
        align_of::<X86UserContext>(), align_of::<Mckfd>(), align_of::<usize>()]
        .into_iter().max().unwrap()
}
pub(crate) mod mem_helpers {
    use super::*;
    pub unsafe extern "C" fn kmalloc_tracked(size: CInt, flags: CULong,
        file: *mut i8, line: CInt) -> *mut c_void {
        assert_effects_unlocked("kmalloc_tracked");
        let file = unsafe { origin(file) };
        assert!(size > 0, "unsupported nonpositive production allocation");
        let mut state = state();
        if core::mem::take(&mut state.fail_next_allocation) {
            state.trace.push(Effect::AllocFailed { size, flags, file, line });
            return null_mut();
        }
        let layout = Layout::from_size_align(size as usize, allocation_alignment()).unwrap();
        let pointer = unsafe { alloc(layout) };
        if pointer.is_null() {
            state.trace.push(Effect::AllocFailed { size, flags, file, line });
            return null_mut();
        }
        // Deterministic arbitrary nonzero allocator contents: missing genuine
        // production initialization is not hidden by a zeroed dummy object.
        unsafe { pointer.write_bytes(0xa5, size as usize) };
        let id = state.next_allocation_id;
        state.next_allocation_id = id.checked_add(1).expect("lower allocation ID overflow");
        let record = AllocationRecord { id, address: pointer as usize, size: size as usize,
            flags, file, line };
        assert!(state.allocations.insert(pointer as usize,
            Allocation { record: record.clone(), layout }).is_none());
        state.trace.push(Effect::Alloc { record });
        pointer.cast()
    }
    pub unsafe extern "C" fn kfree_tracked(pointer: *mut c_void, file: *mut i8, line: CInt) {
        assert_effects_unlocked("kfree_tracked");
        let file = unsafe { origin(file) };
        let mut state = state();
        if pointer.is_null() { state.trace.push(Effect::FreeNull { file, line }); return; }
        let allocation = state.allocations.remove(&(pointer as usize))
            .expect("foreign or already-freed production allocation");
        state.trace.push(Effect::Free { record: allocation.record, file, line });
        unsafe { dealloc(pointer.cast(), allocation.layout) };
    }
}

fn take_lock(lock: *mut crate::abi::IhkSpinlock, irqsave: bool) -> CULong {
    assert!(!lock.is_null());
    assert_eq!((lock as usize) % align_of::<crate::abi::IhkSpinlock>(), 0);
    let address = lock as usize;
    let thread = std::thread::current().id();
    let mut state = state();
    let class = *state.lock_classes.get(&address).unwrap_or(&LockClass::Registry);
    LOCAL.with(|local| {
        let local = local.borrow();
        assert!(!local.held.iter().any(|held| held.address == address), "recursive kernel lock");
        match class {
            LockClass::Process | LockClass::State => assert!(local.held.is_empty(), "P/S lock nesting"),
            LockClass::Registry => assert!(local.held.len() <= 1 &&
                local.held.iter().all(|held| held.class == LockClass::Process), "R lock order"),
        }
    });
    while let Some(owner) = state.lock_owners.get(&address) {
        assert_ne!(*owner, thread, "recursive kernel primitive lock");
        state = global().1.wait(state).unwrap_or_else(|error| error.into_inner());
    }
    state.lock_owners.insert(address, thread);
    let held = LOCAL.with(|local| {
        let mut local = local.borrow_mut();
        let flags = if local.irq_enabled { 0x200 } else { 0 };
        if irqsave { local.irq_enabled = false; }
        let held = HeldLock { address, class, saved_flags: irqsave.then_some(flags) };
        local.held.push(held.clone()); held
    });
    let flags = held.saved_flags.unwrap_or(0);
    state.trace.push(Effect::Lock { lock: held });
    flags
}
fn release_lock(lock: *mut crate::abi::IhkSpinlock, flags: Option<CULong>) {
    assert!(!lock.is_null());
    let address = lock as usize;
    let held = LOCAL.with(|local| {
        let mut local = local.borrow_mut();
        let held = local.held.last().expect("unlock without owned primitive lock");
        assert_eq!(held.address, address, "non-LIFO primitive unlock");
        assert_eq!(held.saved_flags, flags, "IRQsave/restore flags differ");
        let held = local.held.pop().unwrap();
        if let Some(flags) = flags { local.irq_enabled = flags & 0x200 != 0; }
        held
    });
    let mut state = state();
    assert_eq!(state.lock_owners.remove(&address), Some(std::thread::current().id()), "foreign primitive unlock");
    state.trace.push(Effect::Unlock { lock: held });
    drop(state); global().1.notify_all();
}
pub(crate) mod spinlock_helpers {
    pub use crate::abi::IhkSpinlock;
    use crate::abi::CULong;
    pub unsafe extern "C" fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong {
        super::take_lock(lock, true)
    }
    pub unsafe extern "C" fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong) {
        super::release_lock(lock, Some(flags));
    }
    pub unsafe extern "C" fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock) {
        super::take_lock(lock, false);
    }
    pub unsafe extern "C" fn __ihk_mc_spinlock_unlock_noirq(lock: *mut IhkSpinlock) {
        super::release_lock(lock, None);
    }
}

pub unsafe extern "C" fn host_reply(request: *mut SyscallRequest, cpu: CInt) -> CLong {
    assert_effects_unlocked("host_reply");
    assert!(!request.is_null());
    let (thread, process) = current_route();
    assert!(thread != 0 && process != 0, "host request lacks actual current Thread/Process");
    let mut bytes = [0u8; 72];
    unsafe { core::ptr::copy_nonoverlapping(request.cast::<u8>(), bytes.as_mut_ptr(), bytes.len()) };
    let mut state = state();
    let result = state.host_replies.pop_front().expect("host reply script exhausted; no dummy success");
    state.trace.push(Effect::HostReply { request: bytes, cpu, thread, process, result });
    result
}
pub unsafe extern "C" fn forward_close(number: CInt, context: *mut c_void) -> CLong {
    assert_effects_unlocked("forward_close");
    assert_eq!(number, 3, "forward_close is the genuine __NR_close lower endpoint");
    assert!(!context.is_null());
    let arg0 = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg0(context.cast::<X86UserContext>()) };
    let (thread, process) = current_route();
    assert!(thread != 0 && process != 0, "forward close lacks actual current Thread/Process");
    let mut state = state();
    let result = state.forward_replies.pop_front().expect("forward-close script exhausted; no dummy success");
    state.trace.push(Effect::ForwardClose { number, arg0, context: context as usize, thread, process, result });
    result
}

/// Controlled raw hash lookup only. A registered refcount0 Process is returned
/// just like any other pointer: only the actual ownership body can reject it.
pub unsafe fn register_process(pid: CInt, process: *mut Process) {
    assert_effects_unlocked("register_process"); assert!(pid > 0 && !process.is_null());
    let mut state = state(); state.processes.insert(pid, process as usize);
    state.trace.push(Effect::ProcessRegistered { pid, process: process as usize });
}
pub unsafe extern "C" fn find_process(pid: CInt, node: *mut c_void) -> *mut c_void {
    assert_effects_unlocked("find_process"); assert!(!node.is_null());
    let mut state = state(); let process = *state.processes.get(&pid).unwrap_or(&0);
    if process != 0 {
        LOCAL.with(|local| {
            let mut local = local.borrow_mut();
            let saved_flags = if local.irq_enabled { 0x200 } else { 0 };
            local.irq_enabled = false;
            local.hash.push(HashBorrow { process, node: node as usize, saved_flags });
        });
    }
    state.trace.push(Effect::HashFind { pid, process, node: node as usize });
    process as *mut c_void
}
pub unsafe extern "C" fn unlock_process(process: *mut c_void, node: *mut c_void) {
    assert!(!process.is_null() && !node.is_null());
    assert!(held_locks().is_empty(), "hash unlock under P/R/S");
    LOCAL.with(|local| {
        let mut local = local.borrow_mut();
        let held = local.hash.pop().expect("hash unlock without original borrow");
        assert_eq!((held.process, held.node), (process as usize, node as usize), "hash identity/unlock mismatch");
        local.irq_enabled = held.saved_flags & 0x200 != 0;
    });
    trace(Effect::HashUnlock { process: process as usize, node: node as usize });
}

// Actual types/callback ABIs; these checks do not implement an ownership body.
const _: () = {
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(size_of::<crate::abi::IhkSpinlock>() == 4 && align_of::<crate::abi::IhkSpinlock>() == 4);
};
