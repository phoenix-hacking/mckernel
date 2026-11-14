from pathlib import Path
p=Path('postimage/smp_application_syscall.rs');s=Path('preimage/smp_application_syscall.rs').read_text()
def once(old,new):
 global s
 assert s.count(old)==1,(old[:80],s.count(old));s=s.replace(old,new)
once('''    transferred: bool,
''','''    transferred: bool,
    #[cfg(m14_getcred_private_candidate)]
    credential_written: bool,
''')
once('''            transferred: false,
''','''            transferred: false,
            #[cfg(m14_getcred_private_candidate)]
            credential_written: false,
''')
once('''        if self.quarantined {
            return Err(-71);
        }
        if self
            .calls
            .iter()
            .flatten()
            .any(|call| call.delivery.request() == &request)''','''        if self.quarantined {
            return Err(-71);
        }
        #[cfg(m14_getcred_private_candidate)]
        if service.is_some() && credential_request(&request) {
            return Err(-22);
        }
        if self
            .calls
            .iter()
            .flatten()
            .any(|call| call.delivery.request() == &request)''')
marker='''    /// Copy a running settid payload while the caller holds the application'''
method='''    /// Private source candidate. The caller holds the exact application
    /// mailbox lock and supplies a kernel-owned credential snapshot from the
    /// referenced current worker. This never publishes a response.
    #[cfg(m14_getcred_private_candidate)]
    pub(crate) fn write_credentials(
        &mut self, handle: u64, serial: u64, physical: u64, bytes: &mut [u8],
        copy: impl FnOnce(&Request, &mut M, u64, &mut [u8]) -> Result,
    ) -> Result {
        if self.closed || self.quarantined { return Err(-32); }
        let worker = self.workers.iter().flatten()
            .find(|state| state.worker.wire() == handle).ok_or(-2)?;
        if worker.delivery.map(Token::wire) != Some(serial) { return Err(-16); }
        let call = self.calls.iter_mut().flatten()
            .find(|call| call.delivery.serial().wire() == serial).ok_or(-2)?;
        if call.kernel || call.fork_parked || call.service || call.cancelled
            || call.credential_written || call.completion.is_some() { return Err(-16); }
        let request = call.delivery.request();
        call.delivery.check_return(worker.worker, request.cpu() as i64)?;
        if !credential_request(request) || request.arguments()[0] != physical
            || physical == 0 || physical % 4 != 0 || bytes.len() != 32
            || physical.checked_add(32).is_none() || physical % 4096 > 4096 - 32
        { return Err(-22); }
        copy(request, call.response.as_mut().ok_or(-71)?.memory_mut(), physical, bytes)?;
        // The closure returns only after all 32 stores and retained payload
        // claim; return/cancel and guest publication run under the same lock.
        call.credential_written = true;
        Ok(())
    }

'''
once(marker,method+marker)
once('''        let request = call.delivery.request();
        if value == 0 && request.number() == 186''','''        let request = call.delivery.request();
        #[cfg(m14_getcred_private_candidate)]
        if credential_request(request) && !call.credential_written {
            return Err(-16);
        }
        if value == 0 && request.number() == 186''')
once('''        if call.completion.is_some() {
            return Ok(());
        }
        if call.kernel || call.fork_parked''','''        if call.completion.is_some() {
            return Ok(());
        }
        // The guest ignores every do_syscall result. A negative cancellation
        // also wakes it, so retain the response rather than publish stale data.
        #[cfg(m14_getcred_private_candidate)]
        if credential_request(call.delivery.request()) && !call.credential_written {
            call.cancelled = true;
            return Err(-16);
        }
        if call.kernel || call.fork_parked''')
anchor='''type Result<T = ()> = core::result::Result<T, i32>;'''
once(anchor,anchor+'''

#[cfg(m14_getcred_private_candidate)]
fn credential_request(request: &Request) -> bool {
    request.number() == 122 && request.arguments()[1] == 1
}''')
p.write_text(s)
p=Path('postimage/sysfs_memory.rs');s=p.read_text();anchor='''    pub(crate) fn pager_copy(&mut self, offset: usize, bytes: &mut [u8], to_guest: bool) -> Result {'''
method='''    /// Private candidate: invoked only with the original Delivered request
    /// under the application mailbox lock; this is not a public physical map.
    #[cfg(m14_getcred_private_candidate)]
    pub(crate) fn copy_credentials(&mut self, request: &SyscallRequest, physical: u64,
        bytes: &mut [u8]) -> Result {
        if request.number() != 122 || request.arguments()[1] != 1
            || request.arguments()[0] != physical || physical == 0
            || physical % 4 != 0 || physical % 4096 > 4096 - 32 || bytes.len() != 32
            || physical.checked_add(32).is_none() { return Err(EINVAL); }
        // One-page range remains within one original page-aligned PageOwner;
        // the retained Memory owner and ledger also cover its entire extent.
        self.prepare_payload(physical, 32, true)?;
        self.pager_copy(0, bytes, true)
    }

'''
assert s.count(anchor)==1;s=s.replace(anchor,method+anchor);p.write_text(s)
