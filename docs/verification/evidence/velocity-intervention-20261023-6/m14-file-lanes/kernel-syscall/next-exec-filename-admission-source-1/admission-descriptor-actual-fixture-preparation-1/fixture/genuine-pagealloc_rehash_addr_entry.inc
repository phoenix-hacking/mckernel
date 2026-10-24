#[inline(always)]
unsafe fn pagealloc_rehash_addr_entry(
    addr_entry: *mut PageallocTrackAddrEntry,
    addr_hash: *mut AbiListHead,
    addr_locks: *mut IhkSpinlock,
    lock: MemKmallocSpinLockFn,
    unlock: MemKmallocSpinUnlockFn,
) {
    let addr_hash_index = pagealloc_addr_hash((*addr_entry).addr);
    let addr_lock = addr_locks.add(addr_hash_index as usize);
    let irq_flags = lock(addr_lock as CULong);
    list_add_after(
        &raw mut (*addr_entry).hash,
        addr_hash.add(addr_hash_index as usize),
    );
    unlock(addr_lock as CULong, irq_flags);
}
