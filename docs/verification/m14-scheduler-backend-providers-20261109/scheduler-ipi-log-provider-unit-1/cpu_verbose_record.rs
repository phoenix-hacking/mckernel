mod selected_cpu_verbose_records {
    use crate::debug::Ddebug;

    const FILE: &[u8] = concat!(env!("MCKERNEL_CPU_C_FILE"), "\0").as_bytes();

    // Existing mutable flags are still owned by the dynamic-debug subsystem.
    #[used]
    #[no_mangle]
    #[link_section = "__verbose"]
    pub static mut x86_interrupt_log_debug: Ddebug = Ddebug {
        file: FILE.as_ptr().cast(),
        func: b"x86_interrupt_log_bridge\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: 3140,
    };
}
