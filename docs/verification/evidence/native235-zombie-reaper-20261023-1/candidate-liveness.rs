
#![allow(dead_code,non_camel_case_types,non_upper_case_globals)]
use core::ptr::{self,NonNull};
use core::sync::atomic::{AtomicUsize,Ordering};
mod bindings {
 use super::*;
 pub type pid_type=u32;pub const pid_type_PIDTYPE_PID:u32=0;pub const pid_type_PIDTYPE_TGID:u32=1;
 pub struct task_struct{pub exit_state:i32,pub ordinary_state:u32,pub references:AtomicUsize}
 pub struct pid{pub task:*mut task_struct}
 pub unsafe fn get_pid_task(p:*mut pid,_:pid_type)->*mut task_struct {let t=unsafe{(*p).task};if !t.is_null(){unsafe{(*t).references.fetch_add(1,Ordering::AcqRel)};}t}
 pub unsafe fn put_task_struct(t:*mut task_struct){assert_eq!(unsafe{(*t).references.fetch_sub(1,Ordering::AcqRel)},1);}
}
struct ProcessId(NonNull<bindings::pid>);
impl ProcessId{fn thread_alive(&self) -> bool {
        self.alive(bindings::pid_type_PIDTYPE_PID, true)
    }
fn group_alive(&self) -> bool {
        // An exited leader can still have executing siblings. Preserve this
        // conservative group identity check; only per-worker tasks retire here.
        self.alive(bindings::pid_type_PIDTYPE_TGID, false)
    }
fn alive(&self, kind: bindings::pid_type, executing: bool) -> bool {
        // SAFETY: The referenced PID excludes object reuse. Linux checks its
        // task link under RCU and returns an owned task reference on success.
        let task = unsafe { bindings::get_pid_task(self.0.as_ptr(), kind) };
        if task.is_null() {
            return false;
        }
        // SAFETY: get_pid_task owns the task_struct through this aligned scalar
        // volatile read (READ_ONCE semantics). exit_state is terminal and cannot
        // return to zero; ordinary runnable/sleeping tasks keep exit_state zero.
        let alive = !executing || unsafe { ptr::read_volatile(ptr::addr_of!((*task).exit_state)) } == 0;
        // SAFETY: Balance exactly get_pid_task's task reference after inspection.
        unsafe { bindings::put_task_struct(task) };
        alive
    }}

fn identity(exit_state:i32,ordinary_state:u32)->(Box<bindings::task_struct>,Box<bindings::pid>,ProcessId){let mut t=Box::new(bindings::task_struct{exit_state,ordinary_state,references:AtomicUsize::new(0)});let mut p=Box::new(bindings::pid{task:&mut*t});let id=ProcessId(NonNull::from(&mut*p));(t,p,id)}
#[test]fn referenced_zombie_worker_is_terminal_and_reference_balances(){let(t,_p,id)=identity(0x20,0);assert_eq!(id.thread_alive(),false);assert_eq!(t.references.load(Ordering::Acquire),0);}
#[test]fn dead_worker_is_terminal_and_reference_balances(){let(t,_p,id)=identity(0x10,0);assert_eq!(id.thread_alive(),false);assert_eq!(t.references.load(Ordering::Acquire),0);}
#[test]fn running_sleeping_stopped_tasks_remain_live(){for state in[0,1,2,4,8,128]{let(t,_p,id)=identity(0,state);assert!(id.thread_alive());assert_eq!(t.references.load(Ordering::Acquire),0);}}
#[test]fn unavailable_task_link_returns_false_without_put(){let mut p=Box::new(bindings::pid{task:ptr::null_mut()});let id=ProcessId(NonNull::from(&mut*p));assert!(!id.thread_alive());assert!(!id.group_alive());}
#[test]fn exited_leader_does_not_retire_group_with_live_sibling(){let(t,_p,id)=identity(0x20,0);let(sibling,_sp,sid)=identity(0,1);assert!(sid.thread_alive());assert!(id.group_alive());assert_eq!(t.references.load(Ordering::Acquire),0);assert_eq!(sibling.references.load(Ordering::Acquire),0);}
