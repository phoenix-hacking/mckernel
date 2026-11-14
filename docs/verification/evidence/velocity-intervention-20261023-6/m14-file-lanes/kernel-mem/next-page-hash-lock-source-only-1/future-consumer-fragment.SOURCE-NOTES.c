/* Functional OS/Rust only; no security testing. Future fragment, not a standalone test. */
/* Link actual spinlock_helpers; publicIRQ/preempt endpoints controlled. OriginalC
 * adapters are byte-extracted. For every validflags bit pattern and lock head=tail
 * (0,65534,65535), compare returnedflags, head/tail wrap, exactpreempt/IRQ order;
 * initialization always resets full32bit ticketword using the real Rust provider.
 * Unlock must consume the original returnedflags exactly once after head advance.
 * No host popfq/IRQ instruction and no fake mapping/unmap completion. */
extern unsigned long page_hash_lock_bridge(unsigned long);
extern void page_hash_unlock_bridge(unsigned long,unsigned long);
extern void page_hash_lock_init_bridge(unsigned long);
