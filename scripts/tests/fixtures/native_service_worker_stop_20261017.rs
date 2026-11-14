// Production Entry/run/Thread activation, stop_join and Drop execute below.
// Only allocation/task/scheduler and Runtime work boundaries are substituted.
// Thread::new, Linux task implementation and full service retirement are untested.
#![allow(dead_code)]
use std::{sync::{Arc, Mutex, atomic::{AtomicBool, AtomicU8, AtomicUsize, Ordering}}, time::{Duration,Instant}};
#[derive(Clone, Copy, Debug)] struct Error;
type Result<T=()> = std::result::Result<T,Error>;
struct Runtime { calls:AtomicUsize, work:Mutex<()> }
impl Runtime {
    fn pump(&self) { self.calls.fetch_add(1,Ordering::AcqRel); let _work=self.work.lock().unwrap(); }
    fn metadata(&self)->Result<bool> { self.pump();Ok(true) }
    fn zeroing(&self)->Result<bool> { self.pump();Ok(true) }
    fn fail(&self,_:Error) { panic!("unexpected service failure") }
}
mod bindings {
    use super::*;
    std::thread_local! { static STOP:std::cell::RefCell<Option<Arc<AtomicBool>>> = const { std::cell::RefCell::new(None) }; }
    #[allow(non_camel_case_types)]
    pub struct task_struct {
        pub stops:AtomicUsize, pub wakes:AtomicUsize, pub stop:Arc<AtomicBool>,
        pub task:Mutex<Option<std::thread::JoinHandle<i32>>>, pub data:usize,
        pub wake_gate:Mutex<()>, pub waking:AtomicBool,
    }
    pub unsafe fn wake_up_process(task:*mut task_struct)->i32 {
        let t=unsafe {&*task};t.waking.store(true,Ordering::Release);
        let _wake=t.wake_gate.lock().unwrap();
        assert_eq!(t.stops.load(Ordering::Acquire),0,"wake after task retirement");
        assert_eq!(t.wakes.fetch_add(1,Ordering::AcqRel),0);
        let stop=t.stop.clone();let data=t.data;
        *t.task.lock().unwrap()=Some(std::thread::spawn(move || {
            STOP.with(|s| *s.borrow_mut()=Some(stop));
            unsafe {run(data as *mut core::ffi::c_void)}
        }));1
    }
    pub unsafe fn kthread_should_stop()->bool {
        STOP.with(|s| s.borrow().as_ref().unwrap().load(Ordering::Acquire))
    }
    pub unsafe fn kthread_stop(task:*mut task_struct)->i32 {
        let t=unsafe {&*task};assert_eq!(t.stops.fetch_add(1,Ordering::AcqRel),0,"double kthread_stop");
        t.stop.store(true,Ordering::Release);
        if let Some(task)=t.task.lock().unwrap().take() { task.join().unwrap() } else { 0 }
    }
    pub unsafe fn msleep(ms:u32) { std::thread::sleep(Duration::from_millis(ms as u64)); }
}
// PRODUCTION_ITEMS
impl Thread { // PRODUCTION_METHODS
}
fn setup(role:Role)->(Arc<Thread>,Box<bindings::task_struct>,Arc<Runtime>) {
    let runtime=Arc::new(Runtime {calls:AtomicUsize::new(0),work:Mutex::new(())});
    let entered=Arc::new(AtomicBool::new(false));
    let entry=Box::into_raw(Box::new(Entry {runtime:runtime.clone(),entered:entered.clone(),role}));
    let mut task=Box::new(bindings::task_struct {stops:AtomicUsize::new(0),wakes:AtomicUsize::new(0),
        stop:Arc::new(AtomicBool::new(false)),task:Mutex::new(None),data:entry as usize,
        wake_gate:Mutex::new(()),waking:AtomicBool::new(false)});
    let thread=Arc::new(Thread {task:&mut *task,entry,entered,lifecycle:AtomicU8::new(THREAD_CREATED)});
    (thread,task,runtime)
}
fn until(test:impl Fn()->bool) {
    let deadline=Instant::now()+Duration::from_secs(2);
    while !test() { assert!(Instant::now()<deadline,"test boundary timeout");std::thread::yield_now(); }
}
#[test] fn unentered_context_is_reclaimed_by_single_join_and_drop_does_not_rejoin() {
    let (thread,task,runtime)=setup(Role::Packets);
    assert_eq!(Arc::strong_count(&runtime),2);
    thread.stop_join();thread.stop_join();thread.activate();
    assert_eq!(Arc::strong_count(&runtime),1);
    assert!(!thread.entered.load(Ordering::Acquire));
    assert_eq!(task.stops.load(Ordering::Acquire),1);assert_eq!(task.wakes.load(Ordering::Acquire),0);
    drop(thread);assert_eq!(task.stops.load(Ordering::Acquire),1);
}
#[test] fn actual_callback_claims_context_and_join_reclaims_each_role_once() {
    for role in [Role::Packets,Role::Metadata,Role::Zeroing] {
        let (thread,task,runtime)=setup(role);
        thread.activate();thread.activate();until(|| runtime.calls.load(Ordering::Acquire)>0);
        assert!(thread.entered.load(Ordering::Acquire));
        assert_eq!(Arc::strong_count(&runtime),2);
        thread.stop_join();thread.activate();thread.stop_join();
        assert_eq!(Arc::strong_count(&runtime),1);
        assert_eq!(task.stops.load(Ordering::Acquire),1);assert_eq!(task.wakes.load(Ordering::Acquire),1);
        drop(thread);assert_eq!(task.stops.load(Ordering::Acquire),1);
    }
}
#[test] fn concurrent_join_retains_owner_until_callback_exits_without_holding_work_lock() {
    let (thread,task,runtime)=setup(Role::Packets);
    let work=runtime.work.lock().unwrap();
    thread.activate();until(|| runtime.calls.load(Ordering::Acquire)>0);
    let weak=Arc::downgrade(&thread);
    let other=thread.clone();let first=std::thread::spawn(move || other.stop_join());
    until(|| task.stops.load(Ordering::Acquire)==1);
    let other=thread.clone();let second=std::thread::spawn(move || other.stop_join());
    drop(thread);
    assert!(weak.upgrade().is_some());assert_eq!(Arc::strong_count(&runtime),2);
    assert!(!first.is_finished());assert!(!second.is_finished());
    drop(work);first.join().unwrap();second.join().unwrap();
    assert!(weak.upgrade().is_none());assert_eq!(Arc::strong_count(&runtime),1);
    assert_eq!(task.stops.load(Ordering::Acquire),1);
}
#[test] fn activation_in_progress_excludes_join_then_future_activation_is_inert() {
    let (thread,task,runtime)=setup(Role::Packets);
    let gate=task.wake_gate.lock().unwrap();
    let other=thread.clone();let activating=std::thread::spawn(move || other.activate());
    until(|| task.waking.load(Ordering::Acquire));
    assert_eq!(thread.lifecycle.load(Ordering::Acquire),THREAD_ACTIVATING);
    let other=thread.clone();let stopping=std::thread::spawn(move || other.stop_join());
    assert_eq!(task.stops.load(Ordering::Acquire),0);
    drop(gate);activating.join().unwrap();stopping.join().unwrap();
    thread.activate();drop(thread);
    assert_eq!(task.wakes.load(Ordering::Acquire),1);assert_eq!(task.stops.load(Ordering::Acquire),1);
    assert_eq!(Arc::strong_count(&runtime),1);
}
#[test] fn final_drop_without_explicit_stop_still_joins_unentered_task() {
    let (thread,task,runtime)=setup(Role::Metadata);drop(thread);
    assert_eq!(task.stops.load(Ordering::Acquire),1);assert_eq!(Arc::strong_count(&runtime),1);
}
