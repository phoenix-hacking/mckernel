// Controlled HOST boundary test only: no real CPU/GS/offload/wait/native provider.
use core::mem::{align_of, offset_of, size_of};
use std::fmt::Write as _;
use std::sync::Mutex;
#[path = "/home/holden/mckernel/kernel/rust/abi.rs"]
mod abi;
use abi::{CInt, CLong, SyscallRequest};
#[path = "/home/holden/mckernel-work/m14-blocker-resolution-20261110/wait-host-provider-1/candidate/kernel/rust/f03_wait_host_provider.rs"]
mod actual_wait_provider;

struct State {
    active: bool, phase: u8, cpu: CInt, reply: CLong,
    cpu_calls: usize, syscall_calls: usize, sent_cpu: Option<CInt>,
    snapshot: Option<[u8; 72]>, events: Vec<&'static str>, writable: bool,
}
static STATE: Mutex<State> = Mutex::new(State {
    active: false, phase: 0, cpu: 0, reply: 0, cpu_calls: 0, syscall_calls: 0,
    sent_cpu: None, snapshot: None, events: Vec::new(), writable: false,
});
// These two modules are explicitly controlled test effects. The entire genuine
// candidate is included unchanged above; no production function is substituted.
mod x86_local {
    pub unsafe extern "C" fn ihk_mc_get_processor_id() -> crate::abi::CInt {
        let mut s = crate::STATE.lock().unwrap();
        assert!(s.active); assert_eq!(s.phase, 0);
        s.phase = 1; s.cpu_calls += 1; s.events.push("cpu"); s.cpu
    }
}
mod syscall_offload_entry {
    pub unsafe extern "C" fn do_syscall(
        request: *mut crate::abi::SyscallRequest, cpu: crate::abi::CInt,
    ) -> crate::abi::CLong {
        let mut s = crate::STATE.lock().unwrap();
        assert!(s.active); assert_eq!(s.phase, 1);
        assert!(!request.is_null());
        assert_eq!((request as usize) % core::mem::align_of::<crate::abi::SyscallRequest>(), 0);
        s.syscall_calls += 1; assert_eq!(s.syscall_calls, 1);
        assert_eq!(cpu, s.cpu); s.sent_cpu = Some(cpu); s.events.push("send");
        let mut snapshot = [0u8; 72];
        // Source/const guards prove a fully initialized72B field-complete object.
        unsafe { core::ptr::copy_nonoverlapping(request.cast::<u8>(), snapshot.as_mut_ptr(), 72) };
        s.snapshot = Some(snapshot);
        // Mutate only while the actual local request is synchronously borrowed.
        // Retain copied bytes only; no pointer/numeric address escapes this call.
        unsafe {
            core::ptr::addr_of_mut!((*request).rtid).write(-77);
            core::ptr::addr_of_mut!((*request).ttid).write(88);
            core::ptr::addr_of_mut!((*request).valid).write(0x1122334455667788);
            core::ptr::addr_of_mut!((*request).number).write(999);
            core::ptr::addr_of_mut!((*request).args).write([0x55aa; 6]);
            assert_eq!(core::ptr::addr_of!((*request).valid).read(), 0x1122334455667788);
            assert_eq!(core::ptr::addr_of!((*request).args).read(), [0x55aa; 6]);
        }
        s.writable = true; s.phase = 2; s.events.push("send-return"); s.reply
    }
}
const _: unsafe extern "C" fn(CInt, CInt) -> CInt =
    actual_wait_provider::wait_host_wait4_bridge;
const _: () = {
    assert!(size_of::<CInt>() == 4 && size_of::<CLong>() == 8);
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(offset_of!(SyscallRequest, rtid) == 0 && offset_of!(SyscallRequest, ttid) == 4);
    assert!(offset_of!(SyscallRequest, valid) == 8 && offset_of!(SyscallRequest, number) == 16);
    assert!(offset_of!(SyscallRequest, args) == 24);
};
struct Case { id: &'static str, pid: CInt, options: CInt, cpu: CInt, reply: CLong }
fn main() {
    let cases = [
        Case { id: "pid-one-success", pid: 1, options: 0, cpu: 0, reply: 1 },
        Case { id: "max-pid-option-bit-error", pid: 2147483647, options: 16777216, cpu: 6, reply: -10 },
        Case { id: "min-pid-sign-options-interrupted", pid: -2147483648, options: -2147483648, cpu: 7, reply: -4 },
        Case { id: "negative-pid-all-option-bits", pid: -1, options: -1, cpu: 6, reply: 0 },
        Case { id: "wide-positive-return-narrows", pid: 123, options: 16777218, cpu: 0, reply: 4294967297 },
        Case { id: "wide-negative-return-narrows", pid: 456, options: 2, cpu: 7, reply: -4294967297 },
    ];
    print!("{{\"status\":\"PASS\",\"scope\":\"new-whole-wait-host-provider-with-explicit-controlled-lower-effects\",\"case_count\":6,\"cases\":[");
    for (index, c) in cases.iter().enumerate() {
        {
            let mut s = STATE.lock().unwrap();
            assert!(!s.active);
            *s = State { active: true, phase: 0, cpu: c.cpu, reply: c.reply,
                cpu_calls: 0, syscall_calls: 0, sent_cpu: None, snapshot: None,
                events: Vec::new(), writable: false };
        }
        let ret = unsafe { actual_wait_provider::wait_host_wait4_bridge(c.pid, c.options) };
        let mut s = STATE.lock().unwrap();
        assert!(s.active); s.active = false;
        assert_eq!(s.phase, 2); assert_eq!(s.cpu_calls, 1); assert_eq!(s.syscall_calls, 1);
        assert_eq!(s.events, ["cpu", "send", "send-return"]);
        assert!(s.writable);
        let observed = s.snapshot.expect("synchronous snapshot");
        let mut hex = String::with_capacity(144);
        for byte in observed { write!(&mut hex, "{byte:02x}").unwrap(); }
        if index != 0 { print!(","); }
        print!("{{\"id\":\"{}\",\"pid\":{},\"options\":{},\"configured_cpu\":{},\"cpu_lookups\":{},\"sent_cpu\":{},\"syscall_calls\":{},\"request_hex\":\"{}\",\"reply\":{},\"return\":{},\"events\":[\"cpu\",\"send\",\"send-return\"],\"natural_alignment\":true,\"writable_during_callback\":{},\"snapshot_within_call_only\":true}}",
            c.id, c.pid, c.options, c.cpu, s.cpu_calls, s.sent_cpu.unwrap(),
            s.syscall_calls, hex, c.reply, ret, s.writable);
    }
    println!("],\"actual_CPU_or_do_syscall_or_waitid_executed\":false,\"native_execution\":false,\"original_acceptance\":false}}");
}
