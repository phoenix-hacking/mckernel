// SPDX-License-Identifier: GPL-2.0
//! Private M15 source candidate; no production/module/native acceptance.
//! Exact x86_64/SMP/PER_VMA_LOCK/TRACING/MEMCG/HAVE_JUMP_LABEL_HACK pin only.
//! No Rust reference or Rust load/store accesses the concurrently read u32
//! sequence words: explicit x86 asm performs those shared-memory operations.

#[cfg(m15_fixture)]
use crate::fixture_bindings as bindings;
#[cfg(not(m15_fixture))]
use kernel::bindings;
use core::{arch::asm, ptr};

#[cfg(all(not(m15_fixture), not(CONFIG_X86_64)))]
compile_error!("M15 candidate is pinned to x86_64");
#[cfg(all(not(m15_fixture), not(CONFIG_SMP)))]
compile_error!("M15 candidate requires the pinned SMP configuration");
#[cfg(all(not(m15_fixture), not(CONFIG_PER_VMA_LOCK)))]
compile_error!("M15 candidate requires PER_VMA_LOCK");
#[cfg(all(not(m15_fixture), not(CONFIG_TRACING)))]
compile_error!("M15 candidate requires TRACING");
#[cfg(all(not(m15_fixture), not(CONFIG_MEMCG)))]
compile_error!("M15 candidate requires the pinned MEMCG tracing helper");
#[cfg(all(not(m15_fixture), not(CONFIG_HAVE_JUMP_LABEL_HACK)))]
compile_error!("M15 candidate requires HAVE_JUMP_LABEL_HACK");
#[cfg(all(not(m15_fixture), any(CONFIG_KCSAN, CONFIG_DEBUG_LOCK_ALLOC, CONFIG_DEBUG_VM, CONFIG_LOCKDEP, CONFIG_NOINSTR_VALIDATION, CONFIG_PREEMPT_RT)))]
compile_error!("M15 candidate excludes diagnostic/RT configurations not implemented here");

#[cfg(all(not(m15_fixture), not(all(CONFIG_TRACEPOINTS, CONFIG_JUMP_LABEL,
    CONFIG_OBJTOOL, CONFIG_GENERIC_BUG, CONFIG_GENERIC_BUG_RELATIVE_POINTERS,
    CONFIG_DEBUG_BUGVERBOSE, CONFIG_BUG))))]
compile_error!("M15 candidate requires the exact tracepoint/jump-label/verbose relative bug-table pin");

#[cfg(not(target_arch = "x86_64"))]
compile_error!("M15 shared-word asm is x86_64 only");

#[cfg(not(m15_fixture))]
const _: () = {
    assert!(core::mem::offset_of!(bindings::tracepoint, key) == 8);
    assert!(core::mem::size_of::<bindings::seqcount_t>() == 4);
    assert!(core::mem::size_of::<core::ffi::c_uint>() == 4);
    assert!(core::mem::offset_of!(bindings::vm_area_struct, vm_lock_seq) % 4 == 0);
    assert!(core::mem::size_of::<bindings::atomic_long_t>() == 8);
    assert!(core::mem::align_of::<bindings::atomic_long_t>() == 8);
    assert!(core::mem::size_of::<bindings::bug_entry>() == 12);
    assert!(bindings::RWSEM_WRITER_LOCKED == 1);
    assert!(bindings::BUGFLAG_WARNING == 1);
    assert!(bindings::TAINT_WARN == 9);
};

#[cfg(not(m15_fixture))]
extern "C" {
    fn m15_mmap_write_lock_warning();
    fn m15_mmap_trace_start_enabled() -> bool;
    fn m15_mmap_trace_acquire_enabled() -> bool;
    fn m15_mmap_trace_release_enabled() -> bool;
}

// SAFETY: Each address is a live, naturally aligned u32 field in a Linux
// allocation. The caller owns the mmap write lock while reading/changing the
// sequence. Concurrent Linux readers are handled using the Linux shared-memory
// contract at this explicit assembly boundary, never via a Rust reference.
// Deliberately omit pure/nomem/readonly: asm is side-effecting and has a compiler
// memory clobber. These clobbers are stronger than C's unmarked field loads;
// they do not weaken any Linux barrier. Exact emitted code still needs review.
#[inline(always)]
unsafe fn shared_load_u32(address: *const u32) -> u32 {
    let value: u32;
    unsafe {
        asm!("mov {value:e}, dword ptr [{address}]",
            address = in(reg) address, value = out(reg) value,
            options(nostack, preserves_flags));
    }
    value
}

#[inline(always)]
unsafe fn shared_store_u32(address: *mut u32, value: u32) {
    unsafe {
        asm!("mov dword ptr [{address}], {value:e}",
            address = in(reg) address, value = in(reg) value,
            options(nostack, preserves_flags));
    }
}

// Exact no-lockdep rwsem assertion is NOT disabled on this pin. Linux reads
// atomic_long_t once and warns on every failure (WARN_ON, not WARN_ON_ONCE).
// A u64 assembly read matches x86 atomic_long_read -> READ_ONCE(counter).
#[inline(always)]
unsafe fn mmap_assert_write_locked(mm: *mut bindings::mm_struct) {
    let address = unsafe {
        ptr::addr_of!((*mm).__bindgen_anon_1.mmap_lock.count.counter)
    };
    let count: u64;
    unsafe {
        asm!("mov {count}, qword ptr [{address}]",
            address = in(reg) address, count = out(reg) count,
            options(nostack, preserves_flags));
    }
    #[cfg(m15_fixture)]
    unsafe { bindings::m15_fixture_note_assert_read(count); }
    if count & 1 == 0 {
        #[cfg(m15_fixture)]
        unsafe { bindings::m15_fixture_write_lock_warning(); }
        #[cfg(not(m15_fixture))]
        unsafe { m15_mmap_write_lock_warning(); }
    }
}

#[cfg(m15_fixture)]
#[no_mangle]
pub(crate) unsafe extern "C" fn m15_rust_assert_mmap_write_locked(mm: *mut bindings::mm_struct) {
    unsafe { mmap_assert_write_locked(mm); }
}

// Exact retained x86 smp_wmb() is barrier() with KCSAN disabled: a compiler
// memory clobber, no hardware fence. The empty side-effecting asm expresses it.
#[inline(always)]
unsafe fn smp_wmb() {
    unsafe { asm!("", options(nostack, preserves_flags)); }
    #[cfg(m15_fixture)]
    unsafe { bindings::m15_fixture_smp_wmb(); }
}

#[inline(always)]
unsafe fn sequence_address(mm: *mut bindings::mm_struct) -> *mut u32 {
    unsafe { ptr::addr_of_mut!((*mm).__bindgen_anon_1.mm_lock_seq.sequence) }
}

#[inline(always)]
unsafe fn sequence_increment(mm: *mut bindings::mm_struct) {
    let sequence = unsafe { sequence_address(mm) };
    let previous = unsafe { shared_load_u32(sequence) };
    unsafe { shared_store_u32(sequence, previous.wrapping_add(1)); }
}

#[inline(always)]
unsafe fn trace_enabled(event: u32) -> bool {
    #[cfg(m15_fixture)]
    { unsafe { bindings::m15_fixture_outer_gate(event) } }
    #[cfg(not(m15_fixture))]
    {
        match event {
            0 => unsafe { m15_mmap_trace_start_enabled() },
            1 => unsafe { m15_mmap_trace_acquire_enabled() },
            2 => unsafe { m15_mmap_trace_release_enabled() },
            _ => false,
        }
    }
}

/// # Safety
/// Live pinned MM; sleeping-lock context; caller does not already hold this
/// nonrecursive write lock. This operation is infallible under Linux's API.
#[inline(always)]
pub(crate) unsafe fn mmap_write_lock(mm: *mut bindings::mm_struct) {
    if unsafe { trace_enabled(0) } {
        unsafe { bindings::__mmap_lock_do_trace_start_locking(mm, true); }
    }
    unsafe { bindings::down_write(ptr::addr_of_mut!((*mm).__bindgen_anon_1.mmap_lock)); }
    unsafe { sequence_increment(mm); smp_wmb(); }
    if unsafe { trace_enabled(1) } {
        unsafe { bindings::__mmap_lock_do_trace_acquire_returned(mm, true, true); }
    }
}

/// # Safety
/// Same live MM and task own the write lock; no nested provider/publication
/// lock or lifetime transfer is introduced. Sequence end releases all VMA
/// write epochs before up_write, exactly as vma_end_write_all on the pin.
#[inline(always)]
pub(crate) unsafe fn mmap_write_unlock(mm: *mut bindings::mm_struct) {
    if unsafe { trace_enabled(2) } {
        unsafe { bindings::__mmap_lock_do_trace_released(mm, true); }
    }
    unsafe { mmap_assert_write_locked(mm); smp_wmb(); sequence_increment(mm); }
    unsafe { bindings::up_write(ptr::addr_of_mut!((*mm).__bindgen_anon_1.mmap_lock)); }
}

/// # Safety
/// Live VMA stable under this task's mmap write lock. vm_mm and vm_lock cannot
/// change in this scope. Sequence stores are a single aligned x86 mov, matching
/// the retained WRITE_ONCE's naturally aligned volatile-u32 access width.
#[inline(always)]
pub(crate) unsafe fn vma_start_write(vma: *mut bindings::vm_area_struct) {
    let mm = unsafe { (*vma).vm_mm };
    unsafe { mmap_assert_write_locked(mm); }
    let mm_sequence = unsafe { shared_load_u32(sequence_address(mm)) };
    let vma_sequence = unsafe { ptr::addr_of_mut!((*vma).vm_lock_seq) };
    if unsafe { shared_load_u32(vma_sequence) } == mm_sequence {
        return;
    }
    let lock = unsafe { (*vma).vm_lock };
    unsafe { bindings::down_write(ptr::addr_of_mut!((*lock).lock)); }
    unsafe { shared_store_u32(vma_sequence, mm_sequence); }
    #[cfg(m15_fixture)]
    unsafe { bindings::m15_fixture_note_write_once_u32(vma_sequence, mm_sequence); }
    unsafe { bindings::up_write(ptr::addr_of_mut!((*lock).lock)); }
}
