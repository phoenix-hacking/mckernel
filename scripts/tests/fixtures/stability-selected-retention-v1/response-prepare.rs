    pub(crate) fn prepare(self, servicing_tid: i32, value: i64) -> Result<Completion<M>, i32> {
        // Preserve the original unselected consuming/error behavior exactly.
        self.verification_prepare_retained(servicing_tid, value)
            .map_err(|(_response, error)| error)
    }

    /// Verification-only result ownership: every failure returns this exact
    /// Response, including a failed CAS after the prefix writes. The caller
    /// must quarantine it, never retry preparation or claim unchanged bytes.
    pub(crate) fn verification_prepare_retained(
        mut self,
        servicing_tid: i32,
        value: i64,
    ) -> Result<Completion<M>, (Self, i32)> {
        // Original host cancellation and in-kernel services use stid zero.
        if servicing_tid < 0 {
            return Err((self, -22));
        }
        // SAFETY: The constructor's exclusive response claim and retained
        // mapping cover all these aligned fields for this complete operation.
        let address = self.memory.address();
        let status = unsafe { AtomicU64::from_ptr(address.add(8).cast()) };
        let state = unsafe { AtomicU64::from_ptr(address.add(16).cast()) };
        if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
            return Err((self, -71));
        }
        // Preserve ttid, fault_address, the guest-only pde_data and all guards.
        unsafe {
            ptr::write_volatile(address.add(4).cast::<i32>(), servicing_tid);
            ptr::write_volatile(address.add(24).cast::<i64>(), value);
        }
        let wake = match state.compare_exchange(0, 1, Ordering::AcqRel, Ordering::Acquire) {
            Ok(_) => None,
            Err(2) => {
                if state
                    .compare_exchange(2, 1, Ordering::AcqRel, Ordering::Acquire)
                    .is_err()
                {
                    return Err((self, -71));
                }
                Some(self.request.wake())
            }
            Err(_) => return Err((self, -71)),
        };
        Ok(Completion {
            response: Some(self),
            wake,
        })
    }
