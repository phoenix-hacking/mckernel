    pub(super) fn syscall(self: &Arc<Self>, request: &SyscallRequest) -> Result<SyscallResponse> {
        let mut conflict = None;
        let result = (|| {
            let physical = request.response();
            if physical % 8 != 0 {
                return Err(EINVAL);
            }
            let address = self.address(physical, RESPONSE_BYTES)?;
            let span = Span::new(physical, RESPONSE_BYTES)?;
            let mut ledger = self.ledger.lock();
            if ledger.conflicts(span, true) {
                conflict = ledger.diagnostic_conflict(span, true);
                return Err(EBUSY);
            }
            let slot = ledger
                .responses
                .iter()
                .position(Option::is_none)
                .ok_or(EAGAIN)?;
            // SAFETY: The checked exact-generation RAM is aligned and disjoint
            // from every active service access. The guest owns only atomic state.
            let status = unsafe { AtomicU64::from_ptr((address as *mut u8).add(8).cast()) };
            // SAFETY: The same retained, response-sized mapping covers the
            // eight-byte-aligned state word at offset 16. The held ledger claim
            // excludes host aliases, while the guest accesses this shared word
            // atomically; this creates no Rust reference to guest memory.
            let state = unsafe { AtomicU64::from_ptr((address as *mut u8).add(16).cast()) };
            if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
                return Err(errno(-71));
            }
            let tag = ledger.tag(span)?;
            ledger.responses[slot] = Some(tag);
            Ok(SyscallResponse {
                memory: self.clone(),
                address,
                tag,
                slot,
                payload: None,
                exec_group: None,
            })
        
        })();
        // The original ledger guard has ended. The copied snapshot has no
        // borrowed tag/pointer, and this diagnostic runs BEFORE returning the
        // same error to the unchanged mailbox/Remote quarantine path.
        if let Err(error) = &result {
            if *error != EAGAIN && super::diagnostic_ticket(&self.failure_contexts) {
                let context = syscall_failure_context(request, conflict);
                pr_err!("IHK-SMP: service failure context os={} generation={} origin=syscall_response_claim errno={} route={:?}; diagnostic only, owners unchanged\n",
                    self.owner.slot(), self.owner.generation(), error.to_errno(), context);
            }
        }
        result
    }
