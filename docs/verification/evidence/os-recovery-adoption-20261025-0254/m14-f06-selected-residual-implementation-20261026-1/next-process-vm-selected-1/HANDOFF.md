Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

M14-F06 next selected slice: arch_prctl_set_register_bridge, one provider only.

The authoritative retained55-function SHF_ALLOC frontier explicitly names this C provider. The old mapping/prctl/clone fragment already implements its Rust adapter; this candidate reuses exactly that function and its Safety contract. It delegates to existing x86_cpu_helpers::ihk_mc_arch_set_special_register unchanged. The genuine CPU provider still owns register validation and WRMSR effects; this slice adds no register policy, memory ownership or hardware implementation.

The private whole syscall.c candidate wraps only the original C function in inverse MCKERNEL_RUST_F06_PRCTL_SET_REGISTER selection. The private whole syscall_policy.rs candidate appends a leaf module selected by f06_prctl_set_register_candidate. Existing root extern callers stay unchanged. Materialize f06_prctl_set_register.rs at kernel/rust/f06_prctl_set_register.rs, and pair the C/Rust selectors centrally. Getter, mmap providers, logger, VM adapters, ABI and canonical CMake remain unchanged. Canonical integration belongs to Root. The earlier mmap three-provider/configuration cohort remains frozen and is not copied here.

SOURCE-CHECK.stdout records focused source proof: frozen source/frontier references, exact existing Rust reuse, whole-file inverse reversibility, one export, real header prototype/current CPU-helper signature and future-fixture scope. It is not compiler, link, native or retirement evidence.

FUTURE-COMPILER-ARGV.json contains exact bounded future HOST commands: one Rust staticlib compile, genuine-header C/link and one728-case fixture run. Before executing, Root must pin actual compiler binaries and byte-identical materialized sources/real headers/generated config in the ordinary approved profile; the packet grants no CPU slot or execution. No current compiler was launched.

The fixture includes the actual extracted C bridge with only its public symbol renamed, plus the exact reused Rust provider. Both call the same controlled CPU-provider effect. It compares13 register-type bit patterns,8 full-width values and7 provider return statuses, including positive and negative statuses. Each side must issue exactly one identical call and return its exact status. Real header enum/int/unsigned-long width assertions bind the expected32/32/64-bit ABI at future compilation. This validates adapter forwarding only. It does not validate native WRMSR, underlying CPU policy, production default selection or final link ownership.

Next: independent source review and specific ordinary compiler admission when CPU6 becomes available. After successful HOST parity, Root qualifies paired selected-C absence/Rust unique provider in the real full crate and link, then applicable native scope. No automatic acceptance.
