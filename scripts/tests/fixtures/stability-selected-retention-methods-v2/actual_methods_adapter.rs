//! cfg(test)-only source adapter; emitted after the selected-retention stager.
//! This is deliberately source-only: it is compiled only by a separately
//! reviewed runner against the exact candidate tree.
#[cfg(test)]
mod stability_selected_retention_methods_v2 {
    use super::*;
    use core::ptr::NonNull;
    use std::sync::{Arc, atomic::{AtomicU64, Ordering}};

    pub const RESPONSE_BYTES: usize = 32;
    #[derive(Clone, Copy, Debug, PartialEq, Eq)] pub enum Event { Address, Send, Status, Release, Drop }
    pub struct Ledger { pub address: AtomicU64, pub send: AtomicU64, pub status: AtomicU64, pub release: AtomicU64, pub drop: AtomicU64, pub clock_ns: AtomicU64, pub second_cas: AtomicU64 }
    impl Ledger {
        pub fn new() -> Arc<Self> { Arc::new(Self { address: AtomicU64::new(0), send: AtomicU64::new(0), status: AtomicU64::new(0), release: AtomicU64::new(0), drop: AtomicU64::new(0), clock_ns: AtomicU64::new(0), second_cas: AtomicU64::new(0) }) }
        pub fn record(&self, event: Event) { let slot = match event { Event::Address => &self.address, Event::Send => &self.send, Event::Status => &self.status, Event::Release => &self.release, Event::Drop => &self.drop }; slot.fetch_add(1, Ordering::SeqCst); }
        pub fn advance_two_seconds(&self) { self.clock_ns.fetch_add(2_000_000_000, Ordering::SeqCst); }
    }
    pub struct TestResponseMemory { ptr: NonNull<u8>, physical: u64, ledger: Arc<Ledger>, released: bool }
    impl TestResponseMemory { pub fn new(ptr: NonNull<u8>, physical: u64, ledger: Arc<Ledger>) -> Self { assert_eq!(ptr.as_ptr() as usize & 7, 0); Self { ptr, physical, ledger, released: false } } pub fn physical(&self) -> u64 { self.physical } }
    impl ResponseMemory for TestResponseMemory { fn address(&self) -> NonNull<u8> { self.ledger.record(Event::Address); self.ptr } fn release(&mut self) { self.ledger.record(Event::Release); self.released = true; } }
    impl Drop for TestResponseMemory { fn drop(&mut self) { self.ledger.record(Event::Drop); } }

    #[derive(Clone, Copy)] struct Row { stage: u8, commit: u8, wake: Option<bool>, selected: bool, changed: bool, cancel_after: bool }
    pub const ROWS: &[Row] = &[
        Row{stage:0,commit:0,wake:None,selected:true,changed:false,cancel_after:false}, Row{stage:1,commit:0,wake:None,selected:true,changed:false,cancel_after:false}, Row{stage:2,commit:0,wake:None,selected:true,changed:false,cancel_after:false}, Row{stage:4,commit:0,wake:None,selected:true,changed:false,cancel_after:false}, Row{stage:5,commit:0,wake:None,selected:true,changed:false,cancel_after:false}, Row{stage:6,commit:0,wake:None,selected:true,changed:false,cancel_after:false}, Row{stage:255,commit:0,wake:None,selected:true,changed:false,cancel_after:false},
        Row{stage:3,commit:0,wake:Some(false),selected:true,changed:false,cancel_after:false}, Row{stage:3,commit:0,wake:Some(true),selected:true,changed:false,cancel_after:false}, Row{stage:3,commit:2,wake:Some(false),selected:true,changed:false,cancel_after:false}, Row{stage:3,commit:2,wake:Some(true),selected:true,changed:false,cancel_after:false}, Row{stage:3,commit:1,wake:Some(false),selected:true,changed:false,cancel_after:false}, Row{stage:3,commit:1,wake:Some(true),selected:true,changed:false,cancel_after:false}, Row{stage:3,commit:1,wake:Some(true),selected:true,changed:true,cancel_after:false}, Row{stage:3,commit:1,wake:Some(false),selected:false,changed:false,cancel_after:false}, Row{stage:3,commit:1,wake:Some(false),selected:true,changed:false,cancel_after:true}];
    pub const NEGATIVE_CATEGORIES: &[&str] = &["negative servicing TID", "initial nonzero completed status", "invalid wake state", "failed second compare-exchange after prefix writes", "pre-start cancellation with Response", "in-flight cancellation around Completion construction", "post-publication cancellation after committed release without rollback"];

    // The runner supplies real private Mailbox/Call construction in this module.
    pub fn construct_actual<M: ResponseMemory>(memory: M, mailbox: &mut Mailbox<M>, worker: &Worker<M>, value: i64) -> Result<(), i32> {
        let response = Response::from_memory(memory);
        let call = Call::from_response(response);
        mailbox.test_insert(call);
        let _completion: Completion<M> = mailbox.open_worker(worker)?.prepare(worker.worker.tid(), value)?;
        Ok(())
    }
    pub fn actual_method_bindings<M: ResponseMemory>(mailbox: &mut Mailbox<M>, call: Call<M>, worker: &Worker<M>, value: i64) -> Result<(), i32> {
        mailbox.test_insert(call);
        let _ = mailbox.open_worker(worker);
        mailbox.test_cancel_pending();
        mailbox.test_publish(worker.worker.tid(), |call| { let response = call.response.take().ok_or(-71)?; let completion = response.prepare(worker.worker.tid(), value)?; call.completion = Some(completion); Ok(()) })
    }
    pub fn mode3_recovery(ledger: &Ledger) { ledger.advance_two_seconds(); }
}
