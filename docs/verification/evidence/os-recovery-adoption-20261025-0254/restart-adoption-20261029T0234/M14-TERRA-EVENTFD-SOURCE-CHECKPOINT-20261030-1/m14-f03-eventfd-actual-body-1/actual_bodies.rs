unsafe fn zero_syscall_ikc_scd_packet(packet: *mut IkcScdPacket) {
    let words = size_of::<IkcScdPacket>() / size_of::<CULong>();
    let bytes = size_of::<IkcScdPacket>() % size_of::<CULong>();
    let wordp = packet.cast::<CULong>();
    let mut index = 0;

    while index < words {
        write_volatile(wordp.add(index), 0);
        index += 1;
    }

    let bytep = wordp.add(words).cast::<u8>();
    let mut byte = 0;
    while byte < bytes {
        write_volatile(bytep.add(byte), 0);
        byte += 1;
    }
}

pub unsafe extern "C" fn syscall_eventfd_packet_prepare_result(
    packet: *mut IkcScdPacket,
    msg: CInt,
    eventfd_type: CInt,
) -> CInt {
    if packet.is_null() {
        return -EINVAL;
    }

    zero_syscall_ikc_scd_packet(packet);
    write(core::ptr::addr_of_mut!((*packet).msg), msg);
    write(
        core::ptr::addr_of_mut!((*packet).body.eventfd_type),
        eventfd_type,
    );

    0
}

pub unsafe extern "C" fn syscall_eventfd_send_result(
    channel: *mut c_void,
    msg: CInt,
    eventfd_type: CInt,
    send_fn: Option<SyscallIkcSendFn>,
) -> CInt {
    let Some(send) = send_fn else {
        return -EINVAL;
    };

    let mut packet = MaybeUninit::<IkcScdPacket>::uninit();
    let prep_rc = syscall_eventfd_packet_prepare_result(packet.as_mut_ptr(), msg, eventfd_type);
    if prep_rc != 0 {
        return prep_rc;
    }

    send(channel, packet.as_mut_ptr().cast::<c_void>(), 0)
}

unsafe extern "C" fn f03_eventfd_send(
    channel: *mut c_void, packet: *mut c_void, opt: CInt,
) -> CInt {
    // SAFETY: Full existing packet helper supplies an initialized IkcScdPacket.
    // Channel is the unchanged CPU0 channel, borrowed through this synchronous send.
    unsafe { crate::ikc_manycore::ihk_ikc_send(channel.cast(), packet, opt) }
}

pub unsafe extern "C" fn eventfd(eventfd_type: CInt) {
    // SAFETY: Use the same CPU0 lookup, channel field and packet-preparation helper
    // as C. The helper initializes every packet byte before the real Rust send.
    let cpu0 = unsafe { crate::cls::get_cpu_local_var(0) };
    let channel = unsafe { (*cpu0).ikc2linux };
    let _ = unsafe {
        syscall_eventfd_send_result(channel, 0x46, eventfd_type, Some(f03_eventfd_send))
    };
}
