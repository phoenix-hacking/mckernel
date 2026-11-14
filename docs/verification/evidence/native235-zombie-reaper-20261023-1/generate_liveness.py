"""Functional OS only; no security testing. Exact ProcessId bodies and referenced-task adapter."""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,str(Path.cwd()))
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item as item
O=Path(__file__).resolve().parent
head=r'''
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
'''
tests=r'''
fn identity(exit_state:i32,ordinary_state:u32)->(Box<bindings::task_struct>,Box<bindings::pid>,ProcessId){let mut t=Box::new(bindings::task_struct{exit_state,ordinary_state,references:AtomicUsize::new(0)});let mut p=Box::new(bindings::pid{task:&mut*t});let id=ProcessId(NonNull::from(&mut*p));(t,p,id)}
#[test]fn referenced_zombie_worker_is_terminal_and_reference_balances(){let(t,_p,id)=identity(0x20,0);assert_eq!(id.thread_alive(),@ZOMBIE@);assert_eq!(t.references.load(Ordering::Acquire),0);}
#[test]fn dead_worker_is_terminal_and_reference_balances(){let(t,_p,id)=identity(0x10,0);assert_eq!(id.thread_alive(),@ZOMBIE@);assert_eq!(t.references.load(Ordering::Acquire),0);}
#[test]fn running_sleeping_stopped_tasks_remain_live(){for state in[0,1,2,4,8,128]{let(t,_p,id)=identity(0,state);assert!(id.thread_alive());assert_eq!(t.references.load(Ordering::Acquire),0);}}
#[test]fn unavailable_task_link_returns_false_without_put(){let mut p=Box::new(bindings::pid{task:ptr::null_mut()});let id=ProcessId(NonNull::from(&mut*p));assert!(!id.thread_alive());assert!(!id.group_alive());}
#[test]fn exited_leader_does_not_retire_group_with_live_sibling(){let(t,_p,id)=identity(0x20,0);let(sibling,_sp,sid)=identity(0,1);assert!(sid.thread_alive());assert!(id.group_alive());assert_eq!(t.references.load(Ordering::Acquire),0);assert_eq!(sibling.references.load(Ordering::Acquire),0);}
'''
for mode in ['candidate','preimage']:
 s=(O/(mode+'-mcctrl_process.rs')).read_text();bodies='\n'.join(item(s,n) for n in ['fn thread_alive(&self)','fn group_alive(&self)','fn alive(&self,'])
 (O/(mode+'-liveness.rs')).write_text(head+'impl ProcessId{'+bodies+'}\n'+tests.replace('@ZOMBIE@','false' if mode=='candidate' else 'true'))
# Pin actual accepted Linux ABI used for candidate; Linux get_pid_task supplies RCU+reference.
root=Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output')
paths=[root/'build/rust/bindings/bindings_generated.rs',root/'source/linux-6.12.0-211.44.1.el10_2/kernel/pid.c',root/'build/rust/bindings/bindings_helpers_generated.rs']
rows=[]
for p in paths:
 s=p.read_text();needles=(['pub fn put_task_struct('] if 'helpers' in p.name else ['pub exit_state: core::ffi::c_int,','pub fn get_pid_task(']) if p.name.endswith('.rs') else ['struct task_struct *get_pid_task(']
 snippets={}
 for n in needles:
  i=s.index(n);snippets[n]=s[max(0,i-80):i+900 if 'get_pid_task' in n and p.name=='pid.c' else i+180]
 rows.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'snippets':snippets})
(O/'ACTUAL-LINUX-API-BINDING.json').write_text(json.dumps(rows,indent=2)+'\n')
