// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[no_mangle]pub extern "C" fn f06_clone_cpu_Rust_ABI_fact(i:usize)->usize {
 let x=[size_of::<CpuSet>(),size_of::<CpuLocalVar>(),align_of::<CpuLocalVar>(),size_of::<crate::abi::IhkSpinlock>(),offset_of!(CpuLocalVar,runq_lock),offset_of!(CpuLocalVar,runq_len),offset_of!(CpuLocalVar,runq_reserved),offset_of!(CpuLocalVar,status)];x.get(i).copied().unwrap_or(usize::MAX)
}
