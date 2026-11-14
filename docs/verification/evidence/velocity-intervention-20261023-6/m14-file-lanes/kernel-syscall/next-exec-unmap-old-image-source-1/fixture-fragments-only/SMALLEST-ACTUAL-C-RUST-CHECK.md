Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Source/fixture fragment only; no second executable queue or execution grant.

Compare literal old C munmap_all wrapper + its two single-use callbacks against
new actual Rust public entry, both using byte-identical munmap_all_body_result.
Close actual Rust write lock, cache/tree lookup, rb_next, and free-range engine;
control only preemption/physical free and existing munmap_do_bridge effects.
Do not substitute fake free-range core or panic ABI. If full provider closure
cannot be bound cheaply, report the exact missing provider before execution.

Cover empty/1/3 ranges, next acquired before current-node deletion, successful
unmap and error at first/middle/last range (negative and positive CInt errors),
continuation after each error, unlock before free_process_memory_ranges, and
map_end assigned from map_start AFTER that provider returns. Compare exact
variadic log bytes/argument types and order, current CPU/thread/VM identity,
reader/writer state and effects, and no dereference of a freed current range.
Use actual C process_vm/vm_range/vm_regions and Rust ABI size/alignment/offsets;
verify callback signatures and unique public Rust T/no selected old C wrapper.
The C munmap_do_bridge → existing do_munmap remains explicit production C debt.
No privileged memory/IRQ, actual exec, final link, native or full-file credit.
