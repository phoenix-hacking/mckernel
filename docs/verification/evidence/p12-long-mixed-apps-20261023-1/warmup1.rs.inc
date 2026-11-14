// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod long_warmup {
    use super::{permitted, worker, Slot};
    use std::sync::{Arc, Barrier, Condvar, Mutex};
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::time::{Duration, Instant};
    pub fn run() -> Result<(), String> {
        let allowed = permitted()?;
        let cpu = (0..1024).find(|i| allowed[i / 8] & (1 << (i % 8)) != 0).ok_or("LONG no CPU")?;
        let slots = Arc::new([Slot::new(), Slot::new()]);
        let phases = Arc::new(Barrier::new(2));
        let stop = Arc::new(AtomicBool::new(false));
        let gate = Arc::new((Mutex::new((false, false)), Condvar::new()));
        let mut handles = Vec::new();
        let mut first_error = None;
        for id in 0..2usize {
            let shared_slots = Arc::clone(&slots);
            let barrier = Arc::clone(&phases);
            let shared_stop = Arc::clone(&stop);
            let shared_gate = Arc::clone(&gate);
            match std::thread::Builder::new().name(format!("long-fp-{id}")).stack_size(2 * 1024 * 1024).spawn(move || -> Result<u64, String> {
                let mut memory = vec![0u8; 16385];
                {
                    let mut state = shared_gate.0.lock().map_err(|_| "LONG FP gate poisoned")?;
                    while !state.0 { state = shared_gate.1.wait(state).map_err(|_| "LONG FP gate wait poisoned")?; }
                    if state.1 { return Err("LONG FP peer spawn failed".into()); }
                }
                let begin = Instant::now();
                let mut iterations = 0u64;
                let mut error = None;
                loop {
                    // No peer can enter the next probe before both have reset
                    // their own slots and crossed this separate phase barrier.
                    shared_slots[id].ready.store(0, Ordering::Relaxed);
                    shared_slots[id].progress.store(0, Ordering::Relaxed);
                    shared_slots[id].error.store(0, Ordering::Relaxed);
                    barrier.wait();
                    if let Err(e) = worker(id, cpu, Arc::clone(&shared_slots), Arc::clone(&barrier)) {
                        error.get_or_insert(e);
                        shared_stop.store(true, Ordering::Release);
                    }
                    // The original unchanged worker executes the unchanged ASM
                    // FP/context probe, verifies reports and restores controls.
                    let seed = (id * 13 + (iterations % 251) as usize) % 251;
                    for (i, byte) in memory.iter_mut().enumerate() { *byte = ((seed + i * 17) % 251) as u8; }
                    std::hint::black_box(&mut memory);
                    let mut expected = seed;
                    for &byte in &memory {
                        if usize::from(byte) != expected {
                            error.get_or_insert_with(|| "LONG FP memory pattern".to_string());
                            shared_stop.store(true, Ordering::Release);
                            break;
                        }
                        expected = (expected + 17) % 251;
                    }
                    iterations += 1;
                    barrier.wait();
                    if id == 0 && begin.elapsed() >= Duration::from_secs(3) { shared_stop.store(true, Ordering::Release); }
                    barrier.wait();
                    if shared_stop.load(Ordering::Acquire) { break; }
                }
                if let Some(e) = error { return Err(e); }
                if iterations == 0 { return Err("LONG FP no work".into()); }
                if id == 0 && begin.elapsed() < Duration::from_secs(3) { return Err("LONG FP work interval".into()); }
                Ok(iterations)
            }) {
                Ok(handle) => handles.push(handle),
                Err(e) => { first_error = Some(format!("LONG FP spawn {e}")); break; },
            }
        }
        {
            let mut state = gate.0.lock().map_err(|_| "LONG FP start gate poisoned")?;
            *state = (true, first_error.is_some());
            gate.1.notify_all();
        }
        for handle in handles {
            match handle.join() {
                Ok(Ok(_)) => {},
                Ok(Err(e)) => { first_error.get_or_insert(e); },
                Err(_) => { first_error.get_or_insert_with(|| "LONG FP worker panic".to_string()); },
            }
        }
        if let Some(e) = first_error { return Err(e); }
        Ok(())
    }
}

fn main() {
    if let Err(e) = pair_pin() { eprintln!("PREREQUISITE {e}"); std::process::exit(77); }
    if let Err(e) = gate_avx() { eprintln!("PREREQUISITE {e}"); std::process::exit(77); }
    if let Err(e) = long_warmup::run() { eprintln!("LONG warmup {e}"); std::process::exit(1); }
    original_main();
}
