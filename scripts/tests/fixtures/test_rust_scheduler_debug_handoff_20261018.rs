// REAL_SCHED_ABI
use abi::Thread;
use std::alloc::{alloc_zeroed, dealloc, Layout};
use std::ptr::{null_mut, write_bytes};
use std::sync::Mutex;

struct State {
    buffers: [usize; 2],
    next: usize,
    mutation: usize,
    hardware: [u64; 8],
    trace: Vec<(u8, usize, [u64; 8])>,
}
static STATE: Mutex<State> = Mutex::new(State {
    buffers: [0; 2], next: 0, mutation: 0, hardware: [0; 8], trace: Vec::new(),
});
extern "C" {
    fn reference(prev: *mut Thread, next: *mut Thread);
    fn consumer(prev: *mut Thread, next: *mut Thread);
    fn sched_schedule_debug_handoff(prev: *mut Thread, next: *mut Thread);
}
fn buffer_id(s: &State, p: *mut u64) -> usize {
    if p.is_null() { 0 } else if p as usize == s.buffers[0] { 1 }
    else { assert_eq!(p as usize, s.buffers[1]); 2 }
}
#[no_mangle]
unsafe extern "C" fn save_debugreg(p: *mut u64) {
    let mut s = STATE.lock().unwrap();
    let id = buffer_id(&s, p);
    let hw = s.hardware;
    s.trace.push((1, id, hw));
    for i in 0..8 { p.add(i).write(if i == 4 || i == 5 { 0 } else { hw[i] }); }
    if s.mutation != 0 {
        let next = s.next as *mut Thread;
        (*next).ptrace_debugreg = match s.mutation {
            1 => null_mut(), 2 => s.buffers[0] as *mut u64,
            3 => s.buffers[1] as *mut u64, _ => unreachable!(),
        };
    }
}
#[no_mangle]
extern "C" fn clear_debugreg() {
    let mut s = STATE.lock().unwrap();
    s.trace.push((2, 0, [0; 8]));
    let dr4 = s.hardware[4];
    let dr5 = s.hardware[5];
    s.hardware = [0, 0, 0, 0, dr4, dr5, 0xffff0ff0, 0x400];
}
#[no_mangle]
unsafe extern "C" fn restore_debugreg(p: *mut u64) {
    let mut s = STATE.lock().unwrap();
    let id = buffer_id(&s, p);
    let mut values = [0; 8];
    for i in 0..8 { values[i] = p.add(i).read(); }
    s.trace.push((3, id, values));
    // Architecture skips DR4/DR5.
    for i in [0, 1, 2, 3, 6, 7] { s.hardware[i] = values[i]; }
}
#[no_mangle]
extern "C" fn observe_prepare() {
    STATE.lock().unwrap().trace.push((4, 0, [0; 8]));
}
#[no_mangle]
extern "C" fn observe_fp_restore() {
    STATE.lock().unwrap().trace.push((5, 0, [0; 8]));
}
#[derive(Debug, PartialEq)]
struct Snapshot {
    threads: [Vec<u8>; 2],
    buffers: [[u64; 8]; 2],
    hardware: [u64; 8],
    trace: Vec<(u8, usize, [u64; 8])>,
}
fn main() { unsafe {
    let layout = Layout::new::<Thread>();
    let a = alloc_zeroed(layout) as *mut Thread;
    let b = alloc_zeroed(layout) as *mut Thread;
    assert!(!a.is_null() && !b.is_null());
    let mut buffers = [[0u64; 8]; 2];
    let ptrs = [buffers[0].as_mut_ptr(), buffers[1].as_mut_ptr()];
    let mut count = 0;
    for prev_kind in 0..3 {
        for next_kind in 0..3 {
            for same_thread in 0..2 {
                for mutation in 0..4 {
                    for seed in 0..3 {
                        let next = if same_thread == 1 { a } else { b };
                        let prev = if prev_kind == 0 { null_mut() } else { a };
                        let mut results = Vec::new();
                        for variant in 0..3 {
                            write_bytes(a.cast::<u8>(), 0xa5, layout.size());
                            write_bytes(b.cast::<u8>(), 0x5a, layout.size());
                            for buf in 0..2 {
                                for i in 0..8 { ptrs[buf].add(i).write(1000 * (seed + 1) + 100 * buf as u64 + i as u64); }
                            }
                            (*a).ptrace_debugreg = if prev_kind == 2 { ptrs[0] } else { null_mut() };
                            // Same-thread case necessarily has a single pointer field.
                            (*next).ptrace_debugreg = match next_kind { 0 => null_mut(), 1 => ptrs[0], _ => ptrs[1] };
                            {
                                let mut s = STATE.lock().unwrap();
                                s.buffers = [ptrs[0] as usize, ptrs[1] as usize];
                                s.next = next as usize; s.mutation = mutation;
                                for i in 0..8 { s.hardware[i] = 9000 + 100 * seed + i as u64; }
                                s.trace.clear();
                            }
                            if variant == 0 { reference(prev, next); }
                            else if variant == 1 { sched_schedule_debug_handoff(prev, next); }
                            else { consumer(prev, next); }
                            let s = STATE.lock().unwrap();
                            let mut trace = s.trace.clone();
                            if variant == 2 {
                                assert_eq!(trace.first().unwrap().0, 4);
                                assert_eq!(trace.last().unwrap().0, 5);
                                trace.remove(0); trace.pop();
                            }
                            results.push(Snapshot {
                                threads: [std::slice::from_raw_parts(a.cast::<u8>(), layout.size()).to_vec(),
                                          std::slice::from_raw_parts(b.cast::<u8>(), layout.size()).to_vec()],
                                buffers, hardware: s.hardware, trace,
                            });
                        }
                        assert_eq!(results[0], results[1], "direct case {}", count);
                        assert_eq!(results[0], results[2], "consumer case {}", count);
                        count += 1;
                    }
                }
            }
        }
    }
    dealloc(a.cast(), layout); dealloc(b.cast(), layout);
    assert_eq!(count, 216);
    println!("PASS {} cases: C reference, actual Rust body, compiled consumer; full thread/buffer/hardware state and ordered callback arguments", count);
} }
