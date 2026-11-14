// M14-F03: replace the remaining C callback consumed by Rust sys_signalfd4.
// The caller owns thread/proc lifetime and supplies a live kernel mask pointer.
#[no_mangle]
pub unsafe extern "C" fn syscall_signalfd_publish_bridge(
    threadp: *mut c_void,
    fd: CInt,
    maskp: *const CULong,
    create: CInt,
) -> CLong {
    let thread = threadp.cast::<Thread>();
    let proc = (*thread).proc;
    let lock = addr_of_mut!((*proc).mckfd_lock).cast::<c_void>();
    let mut sfd: *mut Mckfd;
    let irqstate: CLong;

    if create != 0 {
        sfd = syscall_alloc_bridge(size_of::<Mckfd>(), IHK_MC_AP_NOWAIT).cast::<Mckfd>();
        if sfd.is_null() {
            return -(ENOMEM as CLong);
        }
        core::ptr::write_bytes(sfd.cast::<u8>(), 0, size_of::<Mckfd>());
        (*sfd).fd = fd;
        irqstate = syscall_mckfd_lock_bridge(lock);
        (*sfd).next = (*proc).mckfd.cast::<Mckfd>();
        (*proc).mckfd = sfd.cast::<c_void>();
    } else {
        irqstate = syscall_mckfd_lock_bridge(lock);
        sfd = (*proc).mckfd.cast::<Mckfd>();
        while !sfd.is_null() {
            if (*sfd).fd == fd {
                break;
            }
            sfd = (*sfd).next;
        }
        if sfd.is_null() {
            syscall_mckfd_unlock_bridge(lock, irqstate);
            return -(EINVAL as CLong);
        }
    }

    // Byte copy preserves all unsigned mask bits in the signed C long field.
    copy_nonoverlapping(
        maskp.cast::<u8>(),
        addr_of_mut!((*sfd).data).cast::<u8>(),
        size_of::<CULong>(),
    );
    syscall_mckfd_unlock_bridge(lock, irqstate);
    // Retain the original C return load after unlock, including callback order.
    (*sfd).fd as CLong
}
