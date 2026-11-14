// SPDX-License-Identifier: GPL-2.0
// Test-only mock ABI. Production consumes the exact SDK bindings instead.
#![allow(non_camel_case_types)]
#[repr(C)] pub struct atomic_long_t { pub counter: i64 }
#[repr(C)] pub struct rw_semaphore { pub fixture_id: u32, pub held: u32, pub count: atomic_long_t }
#[repr(C)] pub struct seqcount_t { pub sequence: u32 }
#[repr(C)] pub struct mm_inner { pub mmap_lock: rw_semaphore, pub mm_lock_seq: seqcount_t }
#[repr(C)] pub struct mm_struct { pub __bindgen_anon_1: mm_inner }
#[repr(C)] pub struct vma_lock { pub lock: rw_semaphore }
#[repr(C)] pub struct vm_area_struct {
    pub vm_mm: *mut mm_struct,
    pub vm_lock_seq: u32,
    pub vm_lock: *mut vma_lock,
}
extern "C" {
    pub fn m15_fixture_note_assert_read(count: u64);
    pub fn m15_fixture_write_lock_warning();
    pub fn down_write(sem: *mut rw_semaphore);
    pub fn up_write(sem: *mut rw_semaphore);
    pub fn __mmap_lock_do_trace_start_locking(mm: *mut mm_struct, write: bool);
    pub fn __mmap_lock_do_trace_acquire_returned(mm: *mut mm_struct, write: bool, success: bool);
    pub fn __mmap_lock_do_trace_released(mm: *mut mm_struct, write: bool);
    pub fn m15_fixture_outer_gate(event: u32) -> bool;
    pub fn m15_fixture_smp_wmb();
    pub fn m15_fixture_note_write_once_u32(address: *mut u32, value: u32);
}
