pub unsafe extern "C" fn ihk_mc_interrupt_cpu(cpu: CInt, vector: CInt) -> CInt {
    unsafe {
        x86_interrupt_cpu_result(
            cpu,
            vector,
            crate::ap::num_processors,
            Some(x86_cpu_local_native),
            size_of::<CULong>() as CULong,
            Some(x86_issue_ipi_bridge),
            Some(x86_interrupt_log_bridge),
        )
    }
}
