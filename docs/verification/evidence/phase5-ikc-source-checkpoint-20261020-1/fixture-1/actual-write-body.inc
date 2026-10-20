unsafe fn memcpyl(dest: *mut c_void, src: *const c_void, len: usize) {
    // The public legacy queue API accepts arbitrary byte packet sizes.
    // Native queues separately enforce their pre-existing whole-word ABI.
    copy_nonoverlapping(src.cast::<u8>(), dest.cast::<u8>(), len);
}
unsafe fn rem_u64_nonzero(value: u64, divisor: u64) -> u64 {
    let quotient: u64;
    let remainder: u64;

    core::arch::asm!(
        "xor edx, edx",
        "div {divisor}",
        divisor = in(reg) divisor,
        inlateout("rax") value => quotient,
        out("rdx") remainder,
        options(nostack),
    );
    let _ = quotient;
    remainder
}
pub unsafe extern "C" fn ihk_ikc_write_queue(
    q: *mut IhkIkcQueueHead,
    packet: *mut c_void,
    _flag: CInt,
) -> CInt {
    if q.is_null() || packet.is_null() {
        return -22;
    }
    // The caller retains the mapping and immutable geometry through this call.
    // Enforce the selected consumer's geometry before claiming a slot.
    // Legacy packets remain byte-sized; native ABI2 requires whole words.
    let count = (*q).pktcount as u64;
    let packet_size = (*q).pktsize as usize;
    let payload_bytes = (*q).queue_size;
    if count == 0 || packet_size == 0
        || (cfg!(native_linux_irq_work_v6_12)
            && (count < 2 || packet_size % core::mem::size_of::<CULong>() != 0))
        || count.checked_mul(packet_size as u64) != Some(payload_bytes)
        || (q as usize).checked_add(core::mem::size_of::<IhkIkcQueueHead>())
            .and_then(|start| start.checked_add(payload_bytes as usize)).is_none()
    {
        return -22;
    }

    let mut attempt = 0;
    loop {
        let read = load_queue_counter(&raw mut (*q).read_off);
        let write = load_queue_counter(&raw mut (*q).write_off);
        compiler_fence(Ordering::SeqCst);

        // read and write are independent loads. A stale read can observe a
        // delta above capacity while other producers/consumer progress. Never
        // reserve from that mixed view; retry only after fresh counter loads.
        if write.wrapping_sub(read) >= count.wrapping_sub(1) {
            attempt += 1;
            if attempt > IHK_IKC_WRITE_QUEUE_RETRY {
                kprintf(
                    c"%s: queue %p r: %llu, w: %llu is full\n".as_ptr().cast(),
                    c"ihk_ikc_write_queue".as_ptr(),
                    virt_to_phys(q.cast::<c_void>()),
                    read,
                    write,
                );
                return -16;
            }
            continue;
        }
        // Geometry stays immutable; only the reservation counter may change.
        // Recompute this exact candidate after every failed CAS. No fallible
        // geometry work may abandon an already reserved publication sequence.
        let offset = core::mem::size_of::<IhkIkcQueueHead>()
            + (rem_u64_nonzero(write, count) * packet_size as u64) as usize;
        if cmpxchg_u64(&raw mut (*q).write_off, write, write.wrapping_add(1)) != write {
            continue;
        }
        memcpyl(
            (q as *mut u8).add(offset).cast::<c_void>(),
            packet,
            packet_size,
        );

        while cmpxchg_u64(&raw mut (*q).max_read_off, write, write.wrapping_add(1)) != write {}

        return 0;
    }
}
