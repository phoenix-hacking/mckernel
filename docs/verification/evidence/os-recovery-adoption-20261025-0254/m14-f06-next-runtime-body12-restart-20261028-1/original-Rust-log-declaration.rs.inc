    fn arch_vdso_map_log_bridge(
        event: CInt,
        error: CInt,
        vm: *mut ProcessVm,
        a: CULong,
        b: CULong,
        c: CULong,
        d: CULong,
        pages: CInt,
    );