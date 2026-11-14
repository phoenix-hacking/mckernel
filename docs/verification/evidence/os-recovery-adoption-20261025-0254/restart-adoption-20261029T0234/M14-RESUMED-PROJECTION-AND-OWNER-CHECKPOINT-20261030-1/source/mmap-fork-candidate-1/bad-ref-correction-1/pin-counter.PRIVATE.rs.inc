    // Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
    fn pin_live_counter(counter: &core::sync::atomic::AtomicI32) -> Result<(), CInt> {
        use core::sync::atomic::Ordering;
        let mut old = counter.load(Ordering::SeqCst);
        loop {
            // These classifications return without touching the counter. The
            // caller must quarantine UNKNOWN ownership; it cannot reset refs.
            if old <= 0 { return Err(-super::EINVAL); }
            if old == i32::MAX { return Err(-75); } // EOVERFLOW.
            match counter.compare_exchange_weak(old, old + 1, Ordering::SeqCst, Ordering::SeqCst) {
                Ok(_) => return Ok(()),
                Err(actual) => old = actual,
            }
        }
    }
