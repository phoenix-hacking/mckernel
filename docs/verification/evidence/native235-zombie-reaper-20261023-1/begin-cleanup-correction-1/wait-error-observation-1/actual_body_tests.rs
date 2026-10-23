// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual production Context::wait_syscall body; adapters model existing lookup/operation.
use std::sync::{Arc,Mutex,atomic::{AtomicUsize,Ordering}};
#[derive(Clone,Copy,Debug,PartialEq,Eq)] struct Error(i32);
impl Error { fn to_errno(&self)->i32 {-self.0} }
const EINTR:Error=Error(4);
type Result<T> = std::result::Result<T,Error>;
static EVENTS:Mutex<Vec<String>>=Mutex::new(Vec::new());
macro_rules! pr_info {($($arg:tt)*)=>{{EVENTS.lock().unwrap().push(format!($($arg)*));}};}
struct Registration {pid:i32,reply:Result<isize>,calls:Mutex<Vec<(usize,bool)>>}
impl Registration {fn wait_syscall(&self,argument:usize,compat:bool)->Result<isize>{self.calls.lock().unwrap().push((argument,compat));self.reply}}
mod actual {
use super::*;
pub(super) struct Context {pub(super) slot:u32,pub(super) generation:u64,pub(super) registration:Result<Arc<Registration>>,pub(super) lookups:AtomicUsize}
impl Context {
 fn registered(&self)->Result<Arc<Registration>>{self.lookups.fetch_add(1,Ordering::SeqCst);self.registration.clone()}
    pub(super) fn wait_syscall(&self, argument: usize, compat: bool) -> Result<isize> {
        match self.registered() {
            Ok(registration) => {
                let result = registration.wait_syscall(argument, compat);
                if let Err(error) = &result {
                    if *error != EINTR {
                        pr_info!("application_wait=failed os={} generation={} pid={} phase=operation errno={}\n",
                            self.slot, self.generation, registration.pid, error.to_errno());
                    }
                }
                result
            }
            Err(error) => {
                if error != EINTR {
                    pr_info!("application_wait=failed os={} generation={} pid=unknown phase=registration errno={}\n",
                        self.slot, self.generation, error.to_errno());
                }
                Err(error)
            }
        }
    }
}
}
fn context(reply:Result<isize>)->(actual::Context,Arc<Registration>){let r=Arc::new(Registration{pid:321,reply,calls:Mutex::new(Vec::new())});(actual::Context{slot:7,generation:19,registration:Ok(r.clone()),lookups:AtomicUsize::new(0)},r)}
fn reset(){EVENTS.lock().unwrap().clear();}
fn events()->Vec<String>{EVENTS.lock().unwrap().clone()}
#[test] fn success_result_arguments_and_no_event(){reset();for value in [0,37]{let(c,r)=context(Ok(value));assert_eq!(c.wait_syscall(0xfeed,true),Ok(value));assert_eq!(c.lookups.load(Ordering::SeqCst),1);assert_eq!(*r.calls.lock().unwrap(),vec![(0xfeed,true)]);assert_eq!(Arc::strong_count(&r),2);assert!(events().is_empty());}}
#[test] fn lookup_error_retains_errno_no_operation_and_unknown_pid(){reset();let c=actual::Context{slot:7,generation:19,registration:Err(Error(22)),lookups:AtomicUsize::new(0)};assert_eq!(c.wait_syscall(91,false),Err(Error(22)));assert_eq!(c.lookups.load(Ordering::SeqCst),1);assert_eq!(events(),vec!["application_wait=failed os=7 generation=19 pid=unknown phase=registration errno=-22\n"]);}
#[test] fn lookup_eintr_retains_error_without_event(){reset();let c=actual::Context{slot:7,generation:19,registration:Err(EINTR),lookups:AtomicUsize::new(0)};assert_eq!(c.wait_syscall(91,false),Err(EINTR));assert_eq!(c.lookups.load(Ordering::SeqCst),1);assert!(events().is_empty());}
#[test] fn operation_error_retains_errno_and_real_registration_pid(){reset();for errno in [2,5,16,32,71]{let(c,r)=context(Err(Error(errno)));assert_eq!(c.wait_syscall(93,false),Err(Error(errno)));assert_eq!(c.lookups.load(Ordering::SeqCst),1);assert_eq!(*r.calls.lock().unwrap(),vec![(93,false)]);assert_eq!(Arc::strong_count(&r),2);}let e=events();assert_eq!(e.len(),5);for (s,errno) in e.iter().zip([2,5,16,32,71]){assert_eq!(s,&format!("application_wait=failed os=7 generation=19 pid=321 phase=operation errno=-{}\n",errno));}}
#[test] fn operation_eintr_no_event_or_extra_reference(){reset();let(c,r)=context(Err(EINTR));assert_eq!(c.wait_syscall(94,true),Err(EINTR));assert_eq!(*r.calls.lock().unwrap(),vec![(94,true)]);assert_eq!(c.lookups.load(Ordering::SeqCst),1);assert_eq!(Arc::strong_count(&r),2);assert!(events().is_empty());}
#[test] fn repeated_invocations_do_not_retry_failed_operations(){reset();let(c,r)=context(Err(Error(5)));assert_eq!(c.wait_syscall(10,false),Err(Error(5)));assert_eq!(c.wait_syscall(11,true),Err(Error(5)));assert_eq!(*r.calls.lock().unwrap(),vec![(10,false),(11,true)]);assert_eq!(c.lookups.load(Ordering::SeqCst),2);assert_eq!(events().len(),2);assert_eq!(Arc::strong_count(&r),2);drop(c);assert_eq!(Arc::strong_count(&r),1);}
