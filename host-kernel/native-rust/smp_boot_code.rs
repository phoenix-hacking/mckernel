// SPDX-License-Identifier: GPL-2.0-only
//! Immutable startup templates adapted from the preserved IHK assembly.
//!
//! These bodies are copied into exclusively owned RAM before their header
//! fields are patched. Never execute or mutate the module's template storage.

// SAFETY: This checked, repository-local assembly supplies the single immutable
// trampoline-data symbol below and uses the declared AT&T syntax. Rust never
// executes or mutates that template directly; preparation copies it first.
core::arch::global_asm!(include_str!("smp_trampoline.S"), options(att_syntax));
// SAFETY: This separately checked, repository-local entry blob defines the
// paired start/end labels below with the expected link-visible names. It remains
// immutable module storage and is copied before any AP can observe the bytes.
core::arch::global_asm!(include_str!("smp_startup_entry.S"), options(att_syntax));

// SAFETY: The two global-assembly inputs above define these exact C-linkage
// symbols with the declared sizes and ordering for the module lifetime. Rust
// only forms immutable raw addresses and validates the startup label distance.
extern "C" {
    static mckernel_smp_trampoline_data: [u8; 4096];
    static mckernel_smp_startup_data: u8;
    static mckernel_smp_startup_end: u8;
}

pub(super) fn trampoline() -> &'static [u8; 4096] {
    // SAFETY: The assembly defines exactly one page of immutable, resident
    // storage at this symbol. Its complete bytes have a separate IHK witness.
    unsafe { &mckernel_smp_trampoline_data }
}

pub(super) fn startup() -> &'static [u8] {
    let first = &raw const mckernel_smp_startup_data;
    let end = &raw const mckernel_smp_startup_end;
    let length = (end as usize).checked_sub(first as usize).unwrap();
    assert!((56..4096).contains(&length));
    // SAFETY: Both assembly labels delimit one immutable resident section.
    // The emitted blob is checked against the original whole startup body.
    unsafe { core::slice::from_raw_parts(first, length) }
}
