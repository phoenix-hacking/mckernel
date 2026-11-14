Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Finite source/symbol mapping for independent review; original failure remains unchanged. Pointer cells are distinct objects, not aliases or the mutable storage.

| C storage | Exact Rust leaf | Image address | Size/align | Pointer cell |
|---|---|---|---|---|
| fixed_virt | OWNED_FIXED_VIRT | 0xfffffffffe950018 | 8/8 | x86_memory_fixed_virt_slot |
| init_pt_lock | OWNED_INIT_PT_LOCK | 0xfffffffffe950020 | 4/4 | x86_memory_init_pt_lock_address |
| init_pt_loaded | OWNED_INIT_PT_LOADED | 0xfffffffffe950028 | 4/4 | x86_memory_init_pt_loaded_slot |
| boot_pt | OWNED_BOOT_PT | 0xfffffffffe950000 | 8/8 | x86_memory_boot_pt_slot |
| init_pt | OWNED_INIT_PT | 0xfffffffffe950008 | 8/8 | x86_memory_init_pt_slot |
| last_page | OWNED_LAST_PAGE | 0xfffffffffe950010 | 8/8 | x86_memory_last_page_slot |
| use_1gb_page | OWNED_USE_1GB_PAGE | 0xfffffffffe950024 | 4/4 | x86_clear_l3_use_1gb_page |

All seven Rust storage definitions are allocated writable NOBITS, with zero/null source initializers matching the retained C declarations and seven C ABI rows. See JSON for exact mangled names, section indices/alignment, source line references and input hashes.

No compiled pointer-cell target/consumer relocation edge is proved: the complete Rust relocation dump was intentionally omitted and the image capture has no cell hex dump. Source consumer references are recorded separately. A future bounded exact-seven-cell byte/relocation observation needs its own coordinator/reviewer decision; this is not a third observer retry. No C retirement or native credit.
