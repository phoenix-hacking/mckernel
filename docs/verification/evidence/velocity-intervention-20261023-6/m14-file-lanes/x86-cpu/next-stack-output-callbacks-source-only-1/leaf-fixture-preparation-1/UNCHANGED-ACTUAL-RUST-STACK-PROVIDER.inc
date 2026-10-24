#[no_mangle]
pub unsafe extern "C" fn __print_stack(mut rbp: *mut CULong, first: CULong) {
    // Exact existing C STACK_BUF_LEN: 1024-sizeof("[  0]: ").
    const BUF_LEN: usize = 1024 - b"[  0]: \0".len();
    let mut buf = [0i8; BUF_LEN];
    let out = buf.as_mut_ptr();
    let mut len = unsafe {
        snprintf(
            out, BUF_LEN,
            b"addr2line -e smp-x86/kernel/mckernel.img -fpia\0".as_ptr().cast(),
        )
    } as usize;
    if first != 0 {
        len = len.wrapping_add(unsafe {
            snprintf(
                out.wrapping_add(len), BUF_LEN.wrapping_sub(len),
                b" %#16lx\0".as_ptr().cast(), first,
            )
        } as usize);
    }
    while (rbp as CULong) > 0xffff880000000000
        && BUF_LEN.wrapping_sub(len) > b" 0x0123456789abcdef\0".len()
    {
        let ip = unsafe { rbp.add(1).read() };
        len = len.wrapping_add(unsafe {
            snprintf(
                out.wrapping_add(len), BUF_LEN.wrapping_sub(len),
                b" %#16lx\0".as_ptr().cast(), ip,
            )
        } as usize);
        rbp = unsafe { rbp.read() } as *mut CULong;
    }
    unsafe { __kprintf(b"%s\n\0".as_ptr().cast(), out); }
}
