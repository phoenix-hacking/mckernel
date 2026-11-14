// SOURCE-ONLY TEST HARNESS DRAFT. Root alone compiles/runs retained copies.
// Includes the exact reviewed native methods; concrete stubs below supply only
// clocks, owner records, locks, context and user-copy adapters. No guest memory,
// actual kernel owner/lifetime, native stack or runtime acceptance is simulated.
#![allow(dead_code)]
extern crate self as kernel;
use std::sync::atomic::{AtomicBool, AtomicI64, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, MutexGuard};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Error(i32);
impl Error { pub fn to_errno(self) -> i32 { self.0 } }
type Result<T = ()> = std::result::Result<T, Error>;
const EIO: Error = Error(-5);
const EAGAIN: Error = Error(-11);
const EINVAL: Error = Error(-22);
const EBUSY: Error = Error(-16);
const ENODEV: Error = Error(-19);
fn errno(value: i32) -> Error { Error(value) }
pub mod error {
    pub fn to_result(value: i32) -> crate::Result {
        if value < 0 { Err(crate::Error(value)) } else { Ok(()) }
    }
}
static CLOCK_NS: AtomicI64 = AtomicI64::new(35_100_000_000);
static PRODUCTION_GUARDS: AtomicUsize = AtomicUsize::new(0);
static OBSERVE_FAIL: AtomicBool = AtomicBool::new(false);
static OBSERVE_ADVANCE_TO: AtomicI64 = AtomicI64::new(0);
static COPYIN_FAIL: AtomicBool = AtomicBool::new(false);
static COPYOUT_FAIL: AtomicBool = AtomicBool::new(false);
static COPYOUT_CALLS: AtomicU64 = AtomicU64::new(0);
static STABILITY_FAULT_BARRIERS: AtomicU64 = AtomicU64::new(0);
static USER_BYTES: Mutex<[u8; 256]> = Mutex::new([0; 256]);
static NATIVE_LOGS: Mutex<Vec<String>> = Mutex::new(Vec::new());
pub mod bindings {
    pub unsafe fn ktime_get() -> i64 { crate::CLOCK_NS.load(crate::Ordering::Acquire) }
}
#[macro_export]
macro_rules! pr_info { ($($value:tt)*) => { $crate::native_log(format_args!($($value)*)) }; }
#[macro_export]
macro_rules! pr_err { ($($value:tt)*) => { $crate::native_log(format_args!($($value)*)) }; }
fn native_log(value: std::fmt::Arguments<'_>) {
    assert_eq!(PRODUCTION_GUARDS.load(Ordering::Acquire), 0, "native printk under production guard");
    let text = value.to_string();
    assert!(text.len() <= 4096, "unexpected overlong native line");
    let mut records = NATIVE_LOGS.lock().unwrap();
    assert!(records.len() < 128, "unexpected native log count");
    print!("{}", text);
    records.push(text);
}

struct Lock<T>(Mutex<T>);
impl<T> Lock<T> {
    fn new(value: T) -> Self { Self(Mutex::new(value)) }
    fn lock(&self) -> Guard<'_, T> {
        let guard = self.0.lock().unwrap();
        PRODUCTION_GUARDS.fetch_add(1, Ordering::AcqRel);
        Guard(guard)
    }
}
struct Guard<'a, T>(MutexGuard<'a, T>);
impl<T> std::ops::Deref for Guard<'_, T> { type Target = T; fn deref(&self) -> &T { &self.0 } }
impl<T> std::ops::DerefMut for Guard<'_, T> { fn deref_mut(&mut self) -> &mut T { &mut self.0 } }
impl<T> Drop for Guard<'_, T> {
    fn drop(&mut self) { assert!(PRODUCTION_GUARDS.fetch_sub(1, Ordering::AcqRel) > 0); }
}
pub mod uaccess {
    pub struct UserSlice { argument: usize, bytes: usize }
    impl UserSlice {
        pub fn new(argument: usize, bytes: usize) -> Self { Self { argument, bytes } }
        pub fn reader(self) -> Self { self }
        pub fn writer(self) -> Self { self }
        pub fn read_slice(&mut self, output: &mut [u8]) -> crate::Result {
            assert_eq!(crate::PRODUCTION_GUARDS.load(crate::Ordering::Acquire), 0);
            if self.argument != 1 || self.bytes != 256 || output.len() != 256
                || crate::COPYIN_FAIL.load(crate::Ordering::Acquire) { return Err(crate::Error(-14)); }
            output.copy_from_slice(&*crate::USER_BYTES.lock().unwrap());
            Ok(())
        }
        pub fn write_slice(&mut self, input: &[u8]) -> crate::Result {
            assert_eq!(crate::PRODUCTION_GUARDS.load(crate::Ordering::Acquire), 0);
            // This probes the actual Permit implementation after native drop.
            let permit = crate::stability_phase::permit().expect("copyout still holds Permit");
            drop(permit);
            crate::COPYOUT_CALLS.fetch_add(1, crate::Ordering::AcqRel);
            if self.argument != 1 || self.bytes != 256 || input.len() != 256
                || crate::COPYOUT_FAIL.load(crate::Ordering::Acquire) { return Err(crate::Error(-14)); }
            crate::USER_BYTES.lock().unwrap().copy_from_slice(input);
            Ok(())
        }
    }
}
mod stability_observer {
    // Exact type declarations extracted from the retained original observer.
    include!("observer-types.rs");
    static SELECTED: std::sync::Mutex<Option<Selection>> = std::sync::Mutex::new(None);
    pub(crate) fn selected() -> Option<Selection> { *SELECTED.lock().unwrap() }
    pub(crate) fn select(key: Selection) -> std::result::Result<Selection, i32> {
        let mut selected = SELECTED.lock().unwrap();
        if selected.is_some() { return Err(-16); }
        *selected = Some(key);
        Ok(key)
    }
}
#[path = "stability_phase.rs"]
mod stability_phase;
#[derive(Clone, Copy)]
struct Token(u64);
impl Token { fn wire(self) -> u64 { self.0 } }
#[derive(Clone, Copy)]
struct Owner { slot: u32, generation: u64 }
impl Owner { fn slot(self) -> u32 { self.slot } fn generation(self) -> u64 { self.generation } }
fn selected_key() -> stability_observer::Selection {
    stability_observer::Selection { os: 0, generation: 7, pid: 1234, cpu: 0, requester: 1235,
        application: 42, worker: 43, delivery: 44, ledger_serial: 45, ledger_index: 2,
        response: 0x2000, response_end: 0x2028 }
}
mod smp_application_syscall {
    use crate::{stability_observer as observer, Token};
    use std::marker::PhantomData;
    type Result<T = ()> = std::result::Result<T, i32>;
    pub(crate) trait ResponseMemory {}
    pub(crate) struct Memory;
    impl ResponseMemory for Memory {}
    pub(crate) struct Delivery { pub(crate) value: observer::Delivery }
    impl Delivery {
        pub(crate) fn serial(&self) -> Token { Token(self.value.serial) }
        pub(crate) fn verification_delivery(&self) -> observer::Delivery {
            assert!(crate::PRODUCTION_GUARDS.load(crate::Ordering::Acquire) > 0);
            self.value
        }
    }
    pub(crate) struct Completion<M> {
        pub(crate) owner: Option<observer::Claim>, pub(crate) state: (bool, bool),
        pub(crate) marker: PhantomData<M>,
    }
    impl<M> Completion<M> {
        pub(crate) fn verification_owner(&self) -> Option<observer::Claim> {
            assert!(crate::PRODUCTION_GUARDS.load(crate::Ordering::Acquire) > 0);
            self.owner
        }
        pub(crate) fn verification_state(&self) -> (bool, bool) { self.state }
    }
    pub(crate) struct Call<M> {
        pub(crate) delivery: Delivery, pub(crate) worker: Option<Token>, pub(crate) response: Option<()>,
        pub(crate) completion: Option<Completion<M>>, pub(crate) cancelled: bool,
        pub(crate) kernel: bool, pub(crate) service: bool, pub(crate) publication_since: Option<u64>,
    }
    pub(crate) struct Mailbox<M: ResponseMemory> {
        pub(crate) calls: Vec<Option<Call<M>>>, pub(crate) closed: bool, pub(crate) quarantined: bool,
    }
    impl Mailbox<Memory> {
        pub(crate) fn new(timer: Option<u64>) -> Self {
            let key = crate::selected_key();
            let claim = observer::Claim { os: key.os, generation: key.generation,
                response: observer::Tag { index: key.ledger_index, serial: Some(key.ledger_serial),
                    physical: key.response, end: key.response_end }, payload: None };
            Self { closed: false, quarantined: false, calls: vec![Some(Call {
                delivery: Delivery { value: observer::Delivery { serial: key.delivery, phase: "returning",
                    phase_worker: Some((key.worker, 2001)), pid: key.pid, cpu: key.cpu,
                    requester: key.requester, target: 1, number: 0, response: key.response,
                    arguments: [0, 0x12345000, 16, 7, 8, 9] } }, worker: Some(Token(key.worker)),
                response: None, completion: Some(Completion { owner: Some(claim), state: (true, true), marker: PhantomData }),
                cancelled: false, kernel: false, service: false, publication_since: timer })] }
        }
    }
    include!("smp_application_syscall.append.rs");
    pub(crate) fn stability_fault_observe() { crate::native_log(format_args!("HARNESS_STUB_FAULT_OBSERVE no_real_send=true\n")); }
}
mod smp_application {
    use crate::{errno, Error, Lock, Owner, Result, Token, EAGAIN, EINVAL, EIO};
    use crate::smp_application_syscall::{Mailbox, Memory};
    use std::sync::atomic::{AtomicI32, Ordering};
    pub(crate) struct Entry {
        pub(crate) token: Token, pub(crate) syscalls: Mailbox<Memory>,
        pub(crate) closed: bool, pub(crate) needs_cleanup: bool, pub(crate) quarantined: bool,
    }
    impl Entry { fn key(&self) -> Token { self.token } }
    pub(crate) struct Remote {
        pub(crate) owner: Owner, pub(crate) transport_error: AtomicI32,
        pub(crate) slots: Lock<Vec<Option<Entry>>>,
    }
    impl Remote {
        pub(crate) fn new(timer: Option<u64>) -> Self {
            Self { owner: Owner { slot: 0, generation: 7 }, transport_error: AtomicI32::new(0),
                slots: Lock::new(vec![Some(Entry { token: Token(42), syscalls: Mailbox::new(timer),
                    closed: false, needs_cleanup: false, quarantined: false })]) }
        }
    }
    include!("smp_application.append.rs");
}
mod memory {
    pub(crate) mod service {
        use crate::{errno, Arc, Error, Owner, Result, EAGAIN, EINVAL, EIO};
        use std::sync::atomic::{AtomicI32, Ordering};
        pub(crate) struct Runtime {
            pub(crate) owner: Owner, pub(crate) error: AtomicI32,
            pub(crate) application: crate::smp_application::Remote,
            pub(crate) planned_timer: Option<u64>,
        }
        #[derive(Clone)]
        pub(crate) struct Started { pub(crate) runtime: Arc<Runtime> }
        impl Runtime {
            pub(crate) fn new(timer: Option<u64>) -> Self {
                Self { owner: Owner { slot: 0, generation: 7 }, error: AtomicI32::new(0),
                    application: crate::smp_application::Remote::new(timer), planned_timer: timer }
            }
            fn verification_observe(&self, phase: crate::stability_observer::Phase) -> Result {
                crate::native_log(format_args!("HARNESS_STUB_OWNER_OBSERVE phase={:?} no_guest=true\n", phase));
                let advance = crate::OBSERVE_ADVANCE_TO.load(Ordering::Acquire);
                if advance != 0 { crate::CLOCK_NS.store(advance, Ordering::Release); }
                if crate::OBSERVE_FAIL.load(Ordering::Acquire) { Err(EIO) } else { Ok(()) }
            }
            pub(crate) fn harness_accepted(&self) { self.verification_accepted_phase(); }
        }
        impl Started {
            pub(crate) fn verification_select_read16(&self, pid: Option<i32>) -> Result<crate::stability_observer::Selection> {
                let key = crate::selected_key();
                if pid != Some(key.pid) { return Err(EINVAL); }
                crate::stability_observer::select(key).map_err(errno)
            }
        }
        include!("smp_service.append.rs");
    }
    use crate::{Lock, Owner, Result, EBUSY, EINVAL, EIO, ENODEV};
    use std::sync::atomic::{AtomicPtr, Ordering};
    pub(crate) struct Context { images: Vec<Option<Image>> }
    struct Image { owner: Owner, boot: Option<Boot> }
    struct Boot { started: bool, prepared: Prepared }
    struct Prepared { continuing: Option<crate::memory::service::Started> }
    static PUBLISHED: AtomicPtr<Lock<Context>> = AtomicPtr::new(std::ptr::null_mut());
    pub(crate) fn install(started: crate::memory::service::Started) {
        let context = Box::new(Lock::new(Context { images: vec![Some(Image {
            owner: Owner { slot: 0, generation: 7 }, boot: Some(Boot { started: true,
                prepared: Prepared { continuing: Some(started) } }) })] }));
        assert!(PUBLISHED.swap(Box::into_raw(context), Ordering::AcqRel).is_null());
    }
    pub(crate) fn finish() {
        let pointer = PUBLISHED.swap(std::ptr::null_mut(), Ordering::AcqRel);
        if !pointer.is_null() {
            // Test-owned context, after all synchronous exact-method calls end.
            unsafe { drop(Box::from_raw(pointer)); }
        }
    }
    include!("smp_memory.append.rs");
}

fn put64(bytes: &mut [u8; 256], offset: usize, value: u64) {
    bytes[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}
fn word64(bytes: &[u8; 256], offset: usize) -> u64 {
    u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap())
}
fn request_bytes(operation: u32, sequence: u64) -> [u8; 256] {
    let mut bytes = [0; 256];
    for (offset, value) in [(0, 2u32), (4, operation), (8, 0), (12, 1234)] {
        bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
    }
    for (offset, value) in [(16, 7), (24, sequence), (32, 0x0102030405060708), (40, 0x1112131415161718)] {
        put64(&mut bytes, offset, value);
    }
    if operation != 1 { put64(&mut bytes, 48, 44); put64(&mut bytes, 56, 45); }
    if operation == 8 {
        put64(&mut bytes, 64, 2); put64(&mut bytes, 72, 2);
        for index in 0..32 { bytes[80 + index] = index as u8; }
    }
    bytes
}
fn raw_ioctl(input: [u8; 256]) -> (Result<isize>, [u8; 256]) {
    *USER_BYTES.lock().unwrap() = input;
    print!("HARNESS_IOCTL_INPUT hex=");
    for byte in input { print!("{:02x}", byte); }
    println!();
    let result = memory::verification_phase_ioctl(1, false);
    let output = *USER_BYTES.lock().unwrap();
    print!("HARNESS_IOCTL_OUTPUT result={:?} hex=", result);
    for byte in output { print!("{:02x}", byte); }
    println!();
    (result, output)
}
fn invoke(operation: u32, sequence: u64, expected: i32, snapshot: u64) -> [u8; 256] {
    let input = request_bytes(operation, sequence);
    let (result, output) = raw_ioctl(input);
    let actual = match result { Ok(0) => 0, Ok(value) => panic!("unexpected positive ioctl result {}", value), Err(error) => error.to_errno() };
    assert_eq!(actual, expected);
    assert_eq!(&output[..64], &input[..64]);
    assert_eq!(word64(&output, 64), snapshot);
    assert_eq!(word64(&output, 72) as i64, expected as i64);
    assert_eq!(word64(&output, 200), sequence);
    assert!(word64(&output, 240) <= word64(&output, 248));
    for (offset, value) in [(80, 42), (88, 43), (96, 44), (104, 45), (112, 2), (120, 0x2000), (128, 0x2028), (152, 7)] {
        assert_eq!(word64(&output, offset), value);
    }
    output
}
fn fixture(timer: Option<u64>) -> Arc<memory::service::Runtime> {
    assert_eq!(stability_phase::COMMAND, 0xc100f502);
    assert_eq!(stability_phase::VERSION, 2);
    let runtime = Arc::new(memory::service::Runtime::new(timer));
    // Initial selected request is still Delivered, before any Completion.
    { let mut slots=runtime.application.slots.lock(); let call=slots[0].as_mut().unwrap().syscalls.calls[0].as_mut().unwrap();
      call.completion=None; call.response=Some(()); call.delivery.value.phase="delivered"; call.publication_since=None; }
    memory::install(memory::service::Started { runtime: runtime.clone() });
    let output = invoke(1, 1, 0, 1);
    assert_eq!(word64(&output, 160), 1);
    runtime
}
fn mark_prepared(runtime: &memory::service::Runtime) {
    // Concrete stub for unchanged Completion::prepare and ordinary timer scan.
    // The subject helper must copy this supplied timer; it may never initialize it.
    let mut slots = runtime.application.slots.lock();
    slots[0].as_mut().unwrap().syscalls = smp_application_syscall::Mailbox::new(runtime.planned_timer);
    stability_phase::accepted_selected();
}
fn accepted(runtime: &memory::service::Runtime) {
    mark_prepared(runtime);
    runtime.harness_accepted();
}
fn held(runtime: &memory::service::Runtime) {
    accepted(runtime);
    assert_eq!(stability_phase::stage(), 5);
    assert_eq!(stability_phase::timer(), Some(35));
    assert_eq!(stability_phase::accepted_sequence(), 2);
    assert_eq!(PRODUCTION_GUARDS.load(Ordering::Acquire), 0);
}
fn read_errno(bytes: &[u8; 256]) -> i32 {
    match stability_phase::Request::read(bytes) { Ok(_) => 0, Err(error) => error }
}
fn actual_send_gate() -> std::result::Result<(), i32> {
    assert!(PRODUCTION_GUARDS.load(Ordering::Acquire) > 0);
    include!("send-gate.rs");
    Ok(())
}
fn rejected_snapshot(value: stability_observer::Phase) {
    let _permit=stability_phase::permit().unwrap();
    assert_eq!(stability_phase::snapshot_begin(value),Err(-116));
}
fn case(name: &str) {
    match name {
        "decode" => {
            let base = request_bytes(1, 1);
            assert_eq!(read_errno(&base), 0);
            for version in [0u32, 1, 3, u32::MAX] {
                let mut bytes = base; bytes[..4].copy_from_slice(&version.to_le_bytes());
                assert_eq!(read_errno(&bytes), -22); println!("VECTOR version={} errno=-22", version);
            }
            for operation in [0u32, 9, u32::MAX] {
                let mut bytes = base; bytes[4..8].copy_from_slice(&operation.to_le_bytes());
                assert_eq!(read_errno(&bytes), -22); println!("VECTOR operation={} errno=-22", operation);
            }
            for offset in 64..256 {
                let mut bytes = base; bytes[offset] = 1; assert_eq!(read_errno(&bytes), -22);
                println!("VECTOR nonrelease_reserved_offset={} byte=1 errno=-22", offset);
            }
            for (offset, value) in [(8, 64u32), (12, 0), (12, u32::MAX)] {
                let mut bytes = base; bytes[offset..offset+4].copy_from_slice(&value.to_le_bytes());
                assert_eq!(read_errno(&bytes), -22);
            }
            for offset in [16, 24] { let mut bytes=base; put64(&mut bytes,offset,0); assert_eq!(read_errno(&bytes),-22); }
            let mut bytes=base; bytes[32..48].fill(0); assert_eq!(read_errno(&bytes),-22);
            let wrong_ops = if stability_phase::MODE == 2 { [4u32,5] } else { [2u32,3] };
            for operation in wrong_ops { assert_eq!(read_errno(&request_bytes(operation,2)),-22); }
        }
        "release_decode" => {
            let base=request_bytes(8,2); let request=stability_phase::Request::read(&base).unwrap();
            assert_eq!(request.ack,[0x0706050403020100,0x0f0e0d0c0b0a0908,0x1716151413121110,0x1f1e1d1c1b1a1918]);
            for offset in [64,72] { for value in [0,1,3,u64::MAX] { let mut bytes=base;put64(&mut bytes,offset,value);assert_eq!(read_errno(&bytes),-22); } }
            let mut bytes=base;bytes[80..112].fill(0);assert_eq!(read_errno(&bytes),-22);
            for offset in 112..256 { let mut bytes=base;bytes[offset]=1;assert_eq!(read_errno(&bytes),-22);println!("VECTOR release_reserved_offset={} byte=1 errno=-22",offset); }
        }
        "identity_sequence" => {
            let _runtime=fixture(Some(35));
            let valid=request_bytes(6,2);
            let permit=stability_phase::permit().unwrap();
            for offset in [8,12,16,24,32,40,48,56] {
                let mut changed=valid;changed[offset]^=1;
                let parsed=stability_phase::Request::read(&changed).unwrap();
                assert_eq!(parsed.validate(),Err(-116));println!("VECTOR stale_offset={} errno=-116",offset);
            }
            let input=request_bytes(1,2);assert_eq!(stability_phase::Request::read(&input).unwrap().validate(),Err(-16));
            drop(permit);
            invoke(6,2,0,0);
            let (result,output)=raw_ioctl(valid);assert_eq!(result,Err(Error(-116)));assert_eq!(output,valid);
        }
        "pending_poll" => {
            let runtime=fixture(None);
            {let mut slots=runtime.application.slots.lock();slots[0].as_mut().unwrap().syscalls.calls[0].as_mut().unwrap().completion=None;}
            let output=invoke(7,2,-11,0);assert_eq!(word64(&output,160),1);assert_eq!(word64(&output,216),0);
            invoke(7,3,-11,0);assert_eq!(stability_phase::stage(),1);
        }
        "timer_none" => {
            let runtime=fixture(None);accepted(&runtime);
            assert_eq!(stability_phase::stage(),2);assert_eq!(stability_phase::timer(),None);
            invoke(7,2,-11,0);
            {let mut slots=runtime.application.slots.lock();slots[0].as_mut().unwrap().syscalls.calls[0].as_mut().unwrap().publication_since=Some(35);}
            runtime.harness_accepted();assert_eq!(stability_phase::stage(),5);invoke(7,3,0,2);
        }
        "timer_zero" => {
            CLOCK_NS.store(100_000_000,Ordering::Release);let runtime=fixture(Some(0));accepted(&runtime);
            assert_eq!(stability_phase::stage(),5);let output=invoke(7,2,0,2);
            assert_eq!(word64(&output,208),0);assert_eq!(word64(&output,216),1);
        }
        "deadline" => {
            assert_eq!(stability_phase::deadline(35),Ok(40_000_000_000));
            assert_eq!(stability_phase::deadline(u64::MAX),Err(-75));
            assert_eq!(stability_phase::deadline(u64::MAX/1_000_000_000),Err(-75));
            CLOCK_NS.store(39_999_999_999,Ordering::Release);assert_eq!(stability_phase::check_deadline(35,false),Ok(()));
            CLOCK_NS.store(40_000_000_000,Ordering::Release);assert_eq!(stability_phase::check_deadline(35,false),Err(-110));
            CLOCK_NS.store(37_999_999_999,Ordering::Release);assert_eq!(stability_phase::check_deadline(35,true),Ok(()));
            CLOCK_NS.store(38_000_000_000,Ordering::Release);assert_eq!(stability_phase::check_deadline(35,true),if stability_phase::MODE==3 {Err(-110)} else {Ok(())});
        }
        "held_release" => {
            let runtime=fixture(Some(35));held(&runtime);let ready=invoke(7,2,0,2);
            assert_eq!(word64(&ready,160),5);assert_eq!(word64(&ready,216),1);
            let output=invoke(8,3,0,2);assert_eq!(word64(&output,160),3);assert_eq!(word64(&output,208),35);
            {let _slots=runtime.application.slots.lock();assert_eq!(actual_send_gate(),Ok(()));}
            invoke(7,4,-116,0);
        }
        "barrier_freeze" => {
            let runtime=fixture(Some(35));
            mark_prepared(&runtime);
            {let _slots=runtime.application.slots.lock();
             for _ in 0..3 {assert_eq!(actual_send_gate(),Err(-11));}}
            let permit=stability_phase::permit().unwrap();
            assert_eq!(runtime.application.verification_begin_accepted_hold(selected_key(),&runtime.error).unwrap(),Some(35));
            {let _slots=runtime.application.slots.lock();for _ in 0..4 {assert_eq!(actual_send_gate(),Err(-11));}}
            drop(permit);
            let output=invoke(6,2,0,0);assert_eq!(word64(&output,192),3);assert_eq!(word64(&output,232),4);assert_eq!(word64(&output,160),4);
            assert_eq!(STABILITY_FAULT_BARRIERS.load(Ordering::Acquire),3);
        }
        "hold_cap" => {
            let runtime=fixture(Some(35));held(&runtime);
            {let _slots=runtime.application.slots.lock();for _ in 0..1_000_000 {assert_eq!(actual_send_gate(),Err(-11));}}
            assert_eq!(stability_phase::invalid_errno(),0);
            {let _slots=runtime.application.slots.lock();assert_eq!(actual_send_gate(),Err(-11));}
            assert_eq!(stability_phase::invalid_errno(),-75);
            let output=invoke(6,2,0,0);assert_eq!(word64(&output,232),1_000_000);assert_eq!(word64(&output,208),35);
        }
        "repeat_accepted" => {
            let runtime=fixture(Some(35));held(&runtime);let count=NATIVE_LOGS.lock().unwrap().len();
            runtime.harness_accepted();assert_eq!(NATIVE_LOGS.lock().unwrap().len(),count);
            rejected_snapshot(stability_observer::Phase::AcceptedReturn);
        }
        "snapshot_failure" => {
            let runtime=fixture(Some(35));OBSERVE_FAIL.store(true,Ordering::Release);accepted(&runtime);
            assert_eq!(stability_phase::stage(),4);assert_eq!(stability_phase::invalid_errno(),-5);
            assert!(!NATIVE_LOGS.lock().unwrap().iter().any(|line|line.contains("STABILITY_HOLD_READY")));
        }
        "snapshot_deadline" => {
            let runtime=fixture(Some(35));OBSERVE_ADVANCE_TO.store(40_000_000_000,Ordering::Release);accepted(&runtime);
            assert_eq!(stability_phase::stage(),4);assert_eq!(stability_phase::invalid_errno(),-110);
        }
        "timer_recheck" => {
            let runtime=fixture(Some(35));mark_prepared(&runtime);
            let _permit=stability_phase::permit().unwrap();
            runtime.application.verification_begin_accepted_hold(selected_key(),&runtime.error).unwrap();
            {let mut slots=runtime.application.slots.lock();slots[0].as_mut().unwrap().syscalls.calls[0].as_mut().unwrap().publication_since=Some(36);}
            assert_eq!(runtime.application.verification_commit_accepted_hold(selected_key(),&runtime.error,35,2),Err(Error(-116)));
            assert_eq!(stability_phase::stage(),4);assert_eq!(stability_phase::timer(),Some(35));
        }
        "release_duplicate" => {
            let runtime=fixture(Some(35));held(&runtime);invoke(8,2,0,2);invoke(8,3,-116,0);
            assert_eq!(stability_phase::stage(),3);assert_eq!(stability_phase::invalid_errno(),-116);
        }
        "release_failed_once" => {
            let runtime=fixture(Some(35));held(&runtime);runtime.error.store(-5,Ordering::Release);
            invoke(8,2,-5,0);runtime.error.store(0,Ordering::Release);invoke(8,3,-116,0);
            assert_eq!(stability_phase::stage(),5);
        }
        "release_expired" => {
            let runtime=fixture(Some(35));held(&runtime);CLOCK_NS.store(40_000_000_000,Ordering::Release);
            invoke(8,2,-110,0);assert_eq!(stability_phase::stage(),5);
        }
        "released_invalid" => {
            let runtime=fixture(Some(35));held(&runtime);invoke(8,2,0,2);stability_phase::invalid(-75);
            let _slots=runtime.application.slots.lock();assert_eq!(actual_send_gate(),Ok(()));
        }
        "copyout_ambiguity" => {
            let runtime=fixture(Some(35));held(&runtime);let request=request_bytes(8,2);COPYOUT_FAIL.store(true,Ordering::Release);
            let (result,output)=raw_ioctl(request);assert_eq!(result,Err(Error(-14)));assert_eq!(output,request);
            assert_eq!(stability_phase::stage(),3);COPYOUT_FAIL.store(false,Ordering::Release);
            let (replay,unchanged)=raw_ioctl(request);assert_eq!(replay,Err(Error(-116)));assert_eq!(unchanged,request);
            invoke(6,3,0,0);
        }
        "permit_busy" => {
            let runtime=fixture(Some(35));held(&runtime);let before=COPYOUT_CALLS.load(Ordering::Acquire);
            let permit=stability_phase::permit().unwrap();let request=request_bytes(8,2);
            let (result,output)=raw_ioctl(request);assert_eq!(result,Err(Error(-11)));assert_eq!(output,request);
            assert_eq!(COPYOUT_CALLS.load(Ordering::Acquire),before);drop(permit);invoke(7,2,0,2);
        }
        "copyin_failure" => {
            let _runtime=fixture(Some(35));COPYIN_FAIL.store(true,Ordering::Release);let request=request_bytes(6,2);
            let (result,output)=raw_ioctl(request);assert_eq!(result,Err(Error(-14)));assert_eq!(output,request);
            COPYIN_FAIL.store(false,Ordering::Release);invoke(6,2,0,0);
        }
        "local_health" => {
            let runtime=fixture(Some(35));held(&runtime);
            let _permit=stability_phase::permit().unwrap();
            for field in 0..5 {
                {let mut slots=runtime.application.slots.lock();let entry=slots[0].as_mut().unwrap();
                 match field {0=>entry.closed=true,1=>entry.needs_cleanup=true,2=>entry.quarantined=true,3=>entry.syscalls.closed=true,_=>entry.syscalls.quarantined=true}}
                assert!(runtime.application.verification_held_status(selected_key(),&runtime.error).is_err());
                {let mut slots=runtime.application.slots.lock();let entry=slots[0].as_mut().unwrap();entry.closed=false;entry.needs_cleanup=false;entry.quarantined=false;entry.syscalls.closed=false;entry.syscalls.quarantined=false;}
                assert!(runtime.application.verification_held_status(selected_key(),&runtime.error).is_ok());
                println!("VECTOR local_health_field={} rejected_then_restored=true",field);
            }
        }
        "claim_recheck" => {
            let runtime=fixture(Some(35));held(&runtime);
            let _permit=stability_phase::permit().unwrap();
            for field in 0..16 {
                {let mut slots=runtime.application.slots.lock();let entry=slots[0].as_mut().unwrap();
                 let call=entry.syscalls.calls[0].as_mut().unwrap();
                 match field {
                    0=>call.worker=Some(Token(99)),1=>call.delivery.value.pid+=1,2=>call.delivery.value.cpu+=1,
                    3=>call.delivery.value.requester+=1,4=>call.delivery.value.response+=8,5=>call.delivery.value.number=1,
                    6=>call.delivery.value.arguments[0]=1,7=>call.delivery.value.arguments[2]=15,
                    8=>call.completion.as_mut().unwrap().owner.as_mut().unwrap().os=1,
                    9=>call.completion.as_mut().unwrap().owner.as_mut().unwrap().generation+=1,
                    10=>call.completion.as_mut().unwrap().owner.as_mut().unwrap().response.serial=Some(99),
                    11=>call.completion.as_mut().unwrap().owner.as_mut().unwrap().response.index+=1,
                    12=>call.completion.as_mut().unwrap().owner.as_mut().unwrap().response.physical+=8,
                    13=>call.completion.as_mut().unwrap().owner.as_mut().unwrap().response.end+=8,
                    14=>call.completion.as_mut().unwrap().state=(true,false),_=>call.cancelled=true,
                 }}
                assert!(runtime.application.verification_held_status(selected_key(),&runtime.error).is_err());
                {let mut slots=runtime.application.slots.lock();slots[0].as_mut().unwrap().syscalls=smp_application_syscall::Mailbox::new(Some(35));}
                assert!(runtime.application.verification_held_status(selected_key(),&runtime.error).is_ok());
                println!("VECTOR claim_field={} rejected_then_restored=true",field);
            }
        }
        "phase_order" => {
            let runtime=fixture(Some(35));held(&runtime);
            rejected_snapshot(stability_observer::Phase::BlockedRead);
            rejected_snapshot(stability_observer::Phase::TerminalPlusFive);
            invoke(8,2,0,2);
            let wrong=if stability_phase::MODE==2 {stability_observer::Phase::Recovery} else {stability_observer::Phase::Terminal};
            rejected_snapshot(wrong);
        }
        _ => panic!("unknown independently declared case: {}",name),
    }
}
fn main() {
    let arguments:Vec<String>=std::env::args().collect();
    assert_eq!(arguments.len(),2,"one case per fresh process; no native static reset");
    println!("HARNESS_BEGIN mode={} case={} scope=controlled_native_interfaces_only acceptance=false",stability_phase::MODE,arguments[1]);
    case(&arguments[1]);
    assert_eq!(PRODUCTION_GUARDS.load(Ordering::Acquire),0);
    memory::finish();
    println!("HARNESS_CASE_PASS mode={} case={} application_acceptance=false",stability_phase::MODE,arguments[1]);
}
