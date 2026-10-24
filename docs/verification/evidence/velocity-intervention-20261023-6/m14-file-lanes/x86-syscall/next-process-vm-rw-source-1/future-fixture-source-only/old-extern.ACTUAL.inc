    fn do_process_vm_read_writev(
        pid: CInt,
        local_iov: *const c_void,
        liovcnt: CULong,
        remote_iov: *const c_void,
        riovcnt: CULong,
        flags: CULong,
        op: CInt,
    ) -> CInt;
