// Production Remote call/wait/publish/reply/shutdown and Attribute Drop bodies
// execute with std synchronization. Linux callback removal and hardware are
// outside this test; SharedData backing stays owned by the test until join.
#![allow(dead_code)]
use std::{ptr, sync::{Arc, atomic::{AtomicBool, Ordering}}, time::{Duration, Instant}};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct Error(i32);
impl Error { fn to_errno(self) -> i32 { self.0 } }
type Result<T = ()> = std::result::Result<T, Error>;
const EIO: Error = Error(-5);
const EINVAL: Error = Error(-22);
const ENODEV: Error = Error(-19);
const EINTR: Error = Error(-4);
const EBUSY: Error = Error(-16);
mod kernel { pub mod error { pub fn to_result(n: i32) -> super::super::Result { if n < 0 { Err(super::super::Error(n)) } else { Ok(()) } } } }
macro_rules! pr_err { ($($t:tt)*) => { { let _ = format_args!($($t)*); } } }
mod sysfs_request { // PRODUCTION_CLIENT
}
mod sysfs_rpc { // PRODUCTION_RPC
}
use sysfs_request::Client;
use sysfs_rpc::{Call, Exchange, PACKET_BYTES};
struct Mutex<T>(std::sync::Mutex<T>);
struct Guard<'a,T>(Option<std::sync::MutexGuard<'a,T>>);
impl<T> Mutex<T> {
    fn new(v:T)->Self { Self(std::sync::Mutex::new(v)) }
    fn lock(&self)->Guard<'_,T> { Guard(Some(self.0.lock().unwrap())) }
}
impl<T> std::ops::Deref for Guard<'_,T> { type Target=T; fn deref(&self)->&T { self.0.as_ref().unwrap() } }
impl<T> std::ops::DerefMut for Guard<'_,T> { fn deref_mut(&mut self)->&mut T { self.0.as_mut().unwrap() } }
struct CondVar { cv: std::sync::Condvar, interrupt: AtomicBool }
impl CondVar {
    fn new()->Self { Self { cv: std::sync::Condvar::new(), interrupt: AtomicBool::new(false) } }
    fn wait<T>(&self,g:&mut Guard<'_,T>) { g.0=Some(self.cv.wait(g.0.take().unwrap()).unwrap()); }
    fn wait_interruptible<T>(&self,g:&mut Guard<'_,T>)->bool {
        self.wait(g); self.interrupt.swap(false,Ordering::AcqRel)
    }
    fn notify_all(&self) { self.cv.notify_all(); }
}
type Owner=super::smp_resource::OsToken;
fn owner(slot:u32,generation:u64)->Owner {super::smp_cpu::fixture_owner(slot,generation)}
struct SharedData { owner:Owner, address:u64 }
// PRODUCTION_STATE
struct Remote { data:SharedData, state:Mutex<State>, changed:CondVar }
// PRODUCTION_ERRNO
impl Remote { // PRODUCTION_METHODS
}
// PRODUCTION_ATTRIBUTE
// PRODUCTION_DROP
fn setup(address:u64)->Arc<Remote> { setup_owner(address,owner(7,91)) }
fn setup_owner(address:u64,owner:Owner)->Arc<Remote> {
    Arc::new(Remote { data:SharedData {owner,address},
        state:Mutex::new(State {exchange:Exchange::new(),caller:false,callbacks:0,peer_stopped:false}), changed:CondVar::new() })
}
fn client()->Client { Client {operations:1001,instance:99} }
fn wait_for(r:&Remote, count:usize) {
    let deadline=Instant::now()+Duration::from_secs(2);
    loop {
        if r.state.lock().callbacks==count { return; }
        assert!(Instant::now()<deadline,"callback admission timeout");
        std::thread::yield_now();
    }
}
fn publish(r:&Remote)->[u8;PACKET_BYTES] {
    let mut packet=[0;PACKET_BYTES];
    assert!(r.publish(|p| {packet=*p;Ok(())}).unwrap()); packet
}
fn response(mut packet:[u8;PACKET_BYTES], bytes:i64)->[u8;PACKET_BYTES] {
    let kind=i32::from_le_bytes(packet[8..12].try_into().unwrap())+1;
    packet[8..12].copy_from_slice(&kind.to_le_bytes());
    packet[12..16].copy_from_slice(&0i32.to_le_bytes());
    packet[32..40].copy_from_slice(&bytes.to_le_bytes()); packet
}
#[test] fn blocked_release_drop_and_pending_show_cancel_without_payload_release() {
    super::smp_cpu::fixture_peer_scope(|proof| {
    let page=Box::new([0xa5u8;4096]);
    let r=setup(page.as_ptr() as u64); let weak=Arc::downgrade(&r);
    let attribute=Attribute {remote:r.clone(),client:client(),published:AtomicBool::new(true)};
    let release=std::thread::spawn(move || drop(attribute));
    wait_for(&r,1); let packet=publish(&r);
    let token=r.state.lock().exchange.token();
    let other=r.clone(); let show=std::thread::spawn(move || {
        let mut out=[0x7bu8;8];
        assert_eq!(other.call(client(),Call::Show {capacity:8},&[],&mut out,true),Err(ENODEV));
        assert_eq!(out,[0x7b;8]);
    });
    wait_for(&r,2);
    assert!(!r.shutdown_drained(proof).unwrap());
    assert!(!r.shutdown_after_peer_stop(proof).unwrap());
    release.join().unwrap();show.join().unwrap();
    assert!(r.shutdown_drained(proof).unwrap());
    assert_eq!(r.state.lock().callbacks,0);
    assert!(!r.state.lock().caller);
    assert_eq!(r.state.lock().exchange.token(),token);
    assert_eq!(r.reply(&response(packet,0)),Err(ENODEV));
    assert_eq!(r.state.lock().exchange.token(),token);
    assert_eq!(page.as_slice(),&[0xa5;4096]);
    assert_eq!(Arc::strong_count(&r),1);
    assert!(weak.upgrade().is_some());drop(r);assert!(weak.upgrade().is_none());
    });
}
#[test] fn foreign_generation_or_slot_has_zero_effect_then_normal_reply_succeeds() {
    super::smp_cpu::fixture_peer_scope(|proof| {
    let page=Box::new([0x66u8;4096]);
    // Each remote belongs to a foreign owner. The proof comes only from the
    // actual scoped CPU/IRQ producer; no owner-field proof fabrication remains.
    for foreign in [owner(7,90),owner(8,91)] {
        let r=setup_owner(page.as_ptr() as u64,foreign);
        let other=r.clone();let task=std::thread::spawn(move || {
            let mut out=[0;4];let result=other.call(client(),Call::Show {capacity:4},&[],&mut out,true);
            (result,out)
        });
        wait_for(&r,1); let packet=publish(&r);
        assert_eq!(r.shutdown_after_peer_stop(proof),Err(EINVAL));
        assert_eq!(r.shutdown_drained(proof),Err(EINVAL));
        assert!(!r.state.lock().peer_stopped);
        assert_eq!(r.state.lock().callbacks,1);
        r.reply(&response(packet,4)).unwrap();
        assert_eq!(task.join().unwrap(),(Ok(4),[0x66;4]));
    }
    let r=setup(page.as_ptr() as u64);
    assert!(r.shutdown_after_peer_stop(proof).unwrap());
    });
}
#[test] fn terminal_admission_and_duplicate_stop_do_not_publish_or_reuse_payload() {
    super::smp_cpu::fixture_peer_scope(|proof| {
    let r=setup(0);assert!(r.shutdown_after_peer_stop(proof).unwrap());
    assert!(r.shutdown_after_peer_stop(proof).unwrap());assert!(!r.queued());
    let mut touched=false;
    assert_eq!(r.publish(|_| {touched=true;Ok(())}),Err(ENODEV)); assert!(!touched);
    assert_eq!(r.call(client(),Call::Store {bytes:1},&[1],&mut [],true),Err(ENODEV));
    assert_eq!(r.call(client(),Call::Release,&[],&mut [],false),Err(ENODEV));
    assert_eq!(r.state.lock().callbacks,0);assert!(r.state.lock().exchange.token().is_none());
    // Actual Attribute::drop must return without queuing another Release.
    drop(Attribute {remote:r.clone(),client:client(),published:AtomicBool::new(true)});
    assert!(r.state.lock().exchange.token().is_none());
    });
}
#[test] fn interrupted_published_exchange_remains_owned_until_peer_stop_cancels_successor() {
    super::smp_cpu::fixture_peer_scope(|proof| {
    let r=setup(0);let other=r.clone();
    let show=std::thread::spawn(move || other.call(client(),Call::Show {capacity:0},&[],&mut [],true));
    wait_for(&r,1);let packet=publish(&r);
    {let _state=r.state.lock();r.changed.interrupt.store(true,Ordering::Release);r.changed.notify_all();}
    assert_eq!(show.join().unwrap(),Err(EINTR));
    let token=r.state.lock().exchange.token();assert!(token.is_some());
    let other=r.clone();let release=std::thread::spawn(move || other.call(client(),Call::Release,&[],&mut [],false));
    wait_for(&r,1);assert!(!r.shutdown_after_peer_stop(proof).unwrap());
    assert_eq!(release.join().unwrap(),Err(ENODEV));
    assert!(r.shutdown_drained(proof).unwrap());
    assert_eq!(r.state.lock().exchange.token(),token);
    assert_eq!(r.reply(&response(packet,0)),Err(ENODEV));
    });
}
