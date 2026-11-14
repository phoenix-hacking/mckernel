#![allow(dead_code,non_camel_case_types,non_upper_case_globals)]
use std::{ptr,sync::{Mutex,MutexGuard,atomic::{AtomicUsize,Ordering}},ptr::NonNull};
type Result<T=()>=std::result::Result<T,i32>;const EIO:i32=-5;
struct Lock<T>(Mutex<T>);impl<T> Lock<T>{fn lock(&self)->MutexGuard<'_,T>{self.0.lock().unwrap()}}
mod bindings {
use super::*;
pub struct Signal{pub nr_threads:i32}pub struct task_struct{pub signal:*mut Signal}pub struct pid{pub task:*mut task_struct}
pub struct Mask{pub bits:[u64;1]}pub static mut __cpu_online_mask:Mask=Mask{bits:[3]};pub static mut nr_cpu_ids:u32=2;
pub const pid_type_PIDTYPE_TGID:u32=1;pub static GET:AtomicUsize=AtomicUsize::new(0);pub static PUT:AtomicUsize=AtomicUsize::new(0);pub static CPU:AtomicUsize=AtomicUsize::new(0);
pub unsafe fn get_pid_task(pid:*mut pid,_:u32)->*mut task_struct{let t=(*pid).task;if !t.is_null(){GET.fetch_add(1,Ordering::SeqCst);}t}
pub unsafe fn put_task_struct(_:*mut task_struct){PUT.fetch_add(1,Ordering::SeqCst);}
pub unsafe fn cpus_read_lock(){CPU.fetch_add(1,Ordering::SeqCst);}pub unsafe fn cpus_read_unlock(){CPU.fetch_sub(1,Ordering::SeqCst);}
}
struct ProcessId(NonNull<bindings::pid>);unsafe impl Send for ProcessId{}
struct Process{slot:u32,generation:u64,registration:Lock<Option<()>>,pid:ProcessId}
struct Entry{process:Process}static TABLE:Lock<Vec<Entry>>=Lock(Mutex::new(Vec::new()));fn table()->&'static Lock<Vec<Entry>>{&TABLE}
struct Context{slot:u32,generation:u64}impl Context{fn registered(&self)->Result{Ok(())}
    fn pool_thread_limit(&self) -> Result<isize> {
        let _registration=self.registered()?;
        let mut threads=0usize;
        {
            let entries=table().lock();
            for entry in entries.iter() {
                let process=&entry.process;
                if process.slot!=self.slot||process.generation!=self.generation
                    ||process.registration.lock().is_none(){continue;}
                // SAFETY: the owned PID yields an owned task. Its signal is
                // live until put_task_struct; match get_nr_threads READ_ONCE.
                unsafe {
                    let task=bindings::get_pid_task(process.pid.0.as_ptr(),bindings::pid_type_PIDTYPE_TGID);
                    if task.is_null(){continue;}
                    let signal=(*task).signal;
                    let count=ptr::read_volatile(ptr::addr_of!((*signal).nr_threads));
                    bindings::put_task_struct(task);
                    threads=threads.saturating_add(count.max(0) as usize);
                }
            }
        }
        // SAFETY: CPU hotplug read exclusion keeps the online bitmap stable.
        // Bounds use its actual generated array and Linux's CPU-ID limit.
        let online=unsafe {
            bindings::cpus_read_lock();
            let words=ptr::addr_of!(bindings::__cpu_online_mask.bits);
            let limit=(bindings::nr_cpu_ids as usize).min((&*words).len()*64);
            let mut count=0usize;
            for cpu in 0..limit {
                let mask=ptr::read_volatile(words.cast::<u64>().add(cpu/64));
                count+=usize::from(mask&(1u64<<(cpu%64))!=0);
            }
            bindings::cpus_read_unlock();
            count
        };
        if online==0{return Err(EIO);}
        Ok(isize::from(threads>online.saturating_mul(128)))
    }
}
fn setup(counts:&[(u32,u64,i32,bool)]){let mut entries=table().lock();entries.clear();for &(slot,generation,n,registered) in counts{let signal=Box::into_raw(Box::new(bindings::Signal{nr_threads:n}));let task=Box::into_raw(Box::new(bindings::task_struct{signal}));let pid=Box::into_raw(Box::new(bindings::pid{task}));entries.push(Entry{process:Process{slot,generation,registration:Lock(Mutex::new(if registered{Some(())}else{None})),pid:ProcessId(NonNull::new(pid).unwrap())}});}bindings::GET.store(0,Ordering::SeqCst);bindings::PUT.store(0,Ordering::SeqCst);unsafe{bindings::__cpu_online_mask.bits=[3];}}
#[test]fn legacy_threshold_and_scope(){let c=Context{slot:0,generation:1};setup(&[(0,1,128,true),(0,1,128,true),(1,1,999,true),(0,2,999,true),(0,1,999,false)]);assert_eq!(c.pool_thread_limit(),Ok(0));assert_eq!(bindings::GET.load(Ordering::SeqCst),2);assert_eq!(bindings::PUT.load(Ordering::SeqCst),2);setup(&[(0,1,128,true),(0,1,129,true)]);assert_eq!(c.pool_thread_limit(),Ok(1));assert_eq!(bindings::CPU.load(Ordering::SeqCst),0);}
#[test]fn zero_online_is_error_and_references_balance(){setup(&[(0,1,4,true)]);unsafe{bindings::__cpu_online_mask.bits=[0];}assert_eq!(Context{slot:0,generation:1}.pool_thread_limit(),Err(EIO));assert_eq!(bindings::GET.load(Ordering::SeqCst),bindings::PUT.load(Ordering::SeqCst));assert_eq!(bindings::CPU.load(Ordering::SeqCst),0);}
