// Functional-only source proposal rejected during local source review: private shared child.cpu_id=0, real destructor clears VM CPU bit without an owned publication credit. Never integrate.
    /// Cancel the exact constructor-issued shared child before any graph enqueue.
    ///
    /// # Safety
    /// This is the original successful CLONE_VM clone_thread return: it issued
    /// two Thread references and borrowed the current VM without adding a child
    /// VM edge. Caller has not chain_thread/chain_process/enqueued/ptrace-published
    /// it and has not independently released either constructor edge. Current
    /// parent still owns the same VM. The optional TID slot is retained by the
    /// ordinary real destructor; no local pool/reset/free replacement is used.
    pub(crate) unsafe fn cancel_before_graph_publication(self)->Result<(),CInt>{
        let record=self.record;core::mem::forget(self);
        let r=unsafe{&mut*record.as_ptr()};
        let required=ORIGINAL_CHILD|CHILD_PIN|VM_PIN;
        if r.obligations&required!=required
            ||r.obligations&(ORIGINAL_PUBLICATION_UNKNOWN|CHILD_RELEASE_STARTED|VM_RELEASE_STARTED|VM_TRANSFERRED_TO_CHILD)!=0
            ||r.constructor_thread_refs_remaining!=2{
            unsafe{retain_record(record.as_ptr(),-EBUSY);}return Err(-EBUSY);
        }
        // Consume our one NEW child storage edge first. No reference reset is
        // allowed; constructor provenance supplies the other two actual edges.
        r.obligations=(r.obligations&!CHILD_PIN)|CHILD_RELEASE_STARTED;
        let child=r.child;
        r.child_release_result=unsafe{crate::process_helpers::release_thread_checked(child)};
        if r.child_release_result!=0{
            let error=if r.child_release_result<0{r.child_release_result}else{-EBUSY};
            unsafe{retain_record(record.as_ptr(),error);}return Err(error);
        }
        // The shared child has no VM edge until chain_thread, which did not run.
        // Transfer only our actually acquired VM reference to its final Thread
        // destructor before either constructor edge is consumed. Never also
        // release it separately, including an unexpected/partial outcome.
        r.obligations=(r.obligations&!VM_PIN)|VM_TRANSFERRED_TO_CHILD;
        r.constructor_thread_refs_remaining=1; // mark BEFORE consuming edge one.
        r.child_release_result=unsafe{crate::process_helpers::release_thread_checked(child)};
        if r.child_release_result!=0{
            let error=if r.child_release_result<0{r.child_release_result}else{-EBUSY};
            unsafe{retain_record(record.as_ptr(),error);}return Err(error);
        }
        r.constructor_thread_refs_remaining=0; // mark BEFORE final original edge.
        r.child_release_result=unsafe{crate::process_helpers::release_thread_checked(child)};
        // The live current parent's VM edge means the transferred VM edge must
        // not be final. Result1 proves Thread destruction + nonfinal VM release.
        // Result0 retains an unexpected other Thread owner; negative/2/other
        // outcomes may be partial/destructive. None authorizes another callback.
        if r.child_release_result!=1{
            let error=if r.child_release_result<0{r.child_release_result}else{-EBUSY};
            unsafe{retain_record(record.as_ptr(),error);}return Err(error);
        }
        r.obligations&=!(ORIGINAL_CHILD|TID_SLOT|VM_TRANSFERRED_TO_CHILD);
        // Child/VM/process may no longer be dereferenced. Only this record and
        // its exact obtained CPU reservation remain ours.
        if r.obligations&CALLER_CPU!=0{
            r.obligations=(r.obligations&!CALLER_CPU)|CPU_RELEASE_STARTED;
            unsafe{crate::sched_helpers::release_cpuid(r.cpu);}
        }
        unsafe{crate::mem_helpers::kfree(record.as_ptr().cast());}
        Ok(())
    }

