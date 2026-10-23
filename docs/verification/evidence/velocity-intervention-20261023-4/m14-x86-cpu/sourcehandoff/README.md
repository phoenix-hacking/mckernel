Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private M14F04 slice retires the currently C-defined init_pstate_and_turbo(void) entry into the existing x86_cpu_helpers module. It does not retire cpu.c as a whole. The current selected Rust body is reused byte for byte. The original fallback remains byte-identical; unrelated accepted cpu.c correctness fixes are untouched.

Existing global no_turbo remains C-owned boot data. Two existing static bridges become externally visible under the existing Rust selection. Four C callbacks remain explicit debt: KVM query, CPUID6 and two MSR primitives. No new C functionality or getters are introduced.

The next executable observation is the exact ordinary fixture recipe:18432 selected-original C/Rust pairs,18432 original-fallback/Rust pairs and15 missing-callback masks. The original fallback fixture changes only CPUID acquisition to the named host model; MSR/KVM models retain ordered full-value logs. No privileged instructions run in the fixture. The complete current selected cpu.c TU and actual-header ABI witness then compile under GCC9, with symbol/partial-link checks. The actual image was built with GCC14: exact production compiler, coherent whole Rust crate, default image and native acceptance remain open.

No compiler or test has run in this lane. Execution needs root's ordinary slot grant and existing owned_capture990807 with registered handlers, fresh aggregate/floor/fullgap checks, limits, whole joins and durable objects. Stop at the first unexpected failure. Source preparation grants no file/default/native credit.
