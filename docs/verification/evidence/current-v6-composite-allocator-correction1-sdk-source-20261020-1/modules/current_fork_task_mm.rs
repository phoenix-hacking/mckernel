// SPDX-License-Identifier: GPL-2.0
//! Referenced current child task plus structural MM identity. An active MM is
//! separately acquired for each critical scope and never stored in a VMA owner.
use core::{ptr::{self, NonNull}, sync::atomic::{AtomicI32, Ordering}};
use kernel::{bindings, prelude::*};

pub(super) struct ChildTaskMm {
    task: NonNull<bindings::task_struct>,
    mm: NonNull<bindings::mm_struct>,
    tgid: i32,
}
// SAFETY: Linux references pin both opaque objects. Mapping access requires
// the independently acquired ActiveChildMm below; pointers grant no MM access.
unsafe impl Send for ChildTaskMm {}
unsafe impl Sync for ChildTaskMm {}

struct TaskReference(NonNull<bindings::task_struct>);
impl Drop for TaskReference {
    fn drop(&mut self) { unsafe { bindings::put_task_struct(self.0.as_ptr()) }; }
}
pub(super) struct ActiveChildMm<'a> {
    owner: &'a ChildTaskMm,
    mm: NonNull<bindings::mm_struct>,
}
impl Drop for ActiveChildMm<'_> {
    fn drop(&mut self) {
        // This guard is scoped outside provider/publication/MM locks. No
        // mm_users reference survives in the durable ChildTaskMm owner.
        unsafe { bindings::mmput(self.mm.as_ptr()) };
    }
}
impl ChildTaskMm {
    pub(super) fn current(expected_tgid: i32) -> Result<Self> {
        let current = unsafe { bindings::get_current() };
        let tgid = NonNull::new(unsafe {
            bindings::get_task_pid(current, bindings::pid_type_PIDTYPE_TGID)
        }).ok_or(ESRCH)?;
        let number = unsafe {
            bindings::pid_nr_ns(tgid.as_ptr(), ptr::addr_of_mut!(bindings::init_pid_ns))
        };
        unsafe { bindings::put_pid(tgid.as_ptr()) };
        if number <= 0 || number != expected_tgid { return Err(EACCES); }
        let tid = NonNull::new(unsafe {
            bindings::get_task_pid(current, bindings::pid_type_PIDTYPE_PID)
        }).ok_or(ESRCH)?;
        let task = NonNull::new(unsafe {
            bindings::get_pid_task(tid.as_ptr(), bindings::pid_type_PIDTYPE_PID)
        });
        unsafe { bindings::put_pid(tid.as_ptr()) };
        let task = TaskReference(task.ok_or(ESRCH)?);
        // The referenced thread must be this exact calling task. PID numbers
        // and shared MM pointers are not accepted as a replacement identity.
        if task.0.as_ptr() != current { return Err(EACCES); }
        let mm = NonNull::new(unsafe { bindings::get_task_mm(task.0.as_ptr()) }).ok_or(ESRCH)?;
        let count = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*mm.as_ptr()).__bindgen_anon_1.__bindgen_anon_1.mm_count.counter
        )) };
        let grabbed = count.fetch_update(Ordering::Relaxed, Ordering::Relaxed,
            |n| if n > 0 { n.checked_add(1) } else { None });
        // No publication/provider/MM lock is held here or on the error path.
        unsafe { bindings::mmput(mm.as_ptr()) };
        if grabbed.is_err() { return Err(super::errno(-(bindings::EOVERFLOW as i32))); }
        let result = Self { task: task.0, mm, tgid: number };
        core::mem::forget(task);
        Ok(result)
    }

    pub(super) fn active(&self) -> Result<ActiveChildMm<'_>> {
        // A structural pin alone cannot authorize this scope. Acquire an
        // actual mm_users reference from the exact retained task on every use.
        let mm = NonNull::new(unsafe { bindings::get_task_mm(self.task.as_ptr()) }).ok_or(ESRCH)?;
        if mm != self.mm || self.task.as_ptr() != unsafe { bindings::get_current() } {
            unsafe { bindings::mmput(mm.as_ptr()) };
            return Err(EACCES);
        }
        Ok(ActiveChildMm { owner: self, mm })
    }
    /// Identity metadata only; this grants no mapping/active-MM access.
    pub(super) fn identity(&self)->u64 {self.mm.as_ptr() as u64}
    pub(super) fn tgid(&self) -> i32 { self.tgid }
}
impl ActiveChildMm<'_> {
    /// Comparison only; the guard owns the actual active-MM permit.
    pub(super) fn identity(&self) -> usize {
        debug_assert_eq!(self.owner.mm, self.mm);
        self.mm.as_ptr() as usize
    }
}
impl Drop for ChildTaskMm {
    fn drop(&mut self) {
        // Only mm_count survives across scopes, excluding an mm_users cycle.
        let count = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*self.mm.as_ptr()).__bindgen_anon_1.__bindgen_anon_1.mm_count.counter
        )) };
        let old = count.fetch_sub(1, Ordering::SeqCst);
        assert!(old > 0);
        if old == 1 { unsafe { bindings::__mmdrop(self.mm.as_ptr()) }; }
        unsafe { bindings::put_task_struct(self.task.as_ptr()) };
    }
}
