// Genuine kernel-required unsigned-division provider selection.
// All selected upstream function and macro bodies remain unchanged.
#![cfg_attr(feature = "compiler-builtins", compiler_builtins)]
#![cfg_attr(all(target_family = "wasm"), feature(wasm_numeric_instr))]
#![feature(abi_custom)]
#![feature(abi_unadjusted)]
#![feature(asm_experimental_arch)]
#![feature(cfg_target_has_atomic)]
#![feature(compiler_builtins)]
#![feature(core_intrinsics)]
#![feature(linkage)]
#![feature(naked_functions)]
#![feature(repr_simd)]
#![feature(macro_metavar_expr_concat)]
#![feature(rustc_attrs)]
#![cfg_attr(f16_enabled, feature(f16))]
#![cfg_attr(f128_enabled, feature(f128))]
#![no_builtins]
#![no_std]
#![allow(unstable_name_collisions)] // FIXME(float_bits_const): remove when stable
#![allow(unused_features)]
#![allow(internal_features)]
// `mem::swap` cannot be used because it may generate references to memcpy in unoptimized code.
#![allow(clippy::manual_swap)]
// Support compiling on both stage0 and stage1 which may differ in supported stable features.
#![allow(stable_features)]
// By default, disallow this as it is forbidden in edition 2024. There is a lot of unsafe code to
// be migrated, however, so exceptions exist.
#![warn(unsafe_op_in_unsafe_fn)]

// We disable #[no_mangle] for tests so that we can verify the test results
// against the native compiler-rt implementations of the builtins.

// NOTE cfg(all(feature = "c", ..)) indicate that compiler-rt provides an arch optimized
// implementation of that intrinsic and we'll prefer to use that

// NOTE(aapcs, aeabi, arm) ARM targets use intrinsics named __aeabi_* instead of the intrinsics
// that follow "x86 naming convention" (e.g. addsf3). Those aeabi intrinsics must adhere to the
// AAPCS calling convention (`extern "aapcs"`) because that's how LLVM will call them.

#[cfg(test)]
extern crate core;

#[macro_use]
#[path = "/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/lib/rustlib/src/rust/library/compiler-builtins/compiler-builtins/src/macros.rs"]
mod macros;

pub mod int {
    #[path = "/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/lib/rustlib/src/rust/library/compiler-builtins/compiler-builtins/src/int/specialized_div_rem/mod.rs"]
    mod specialized_div_rem;
    #[path = "/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/lib/rustlib/src/rust/library/compiler-builtins/compiler-builtins/src/int/udiv.rs"]
    pub mod udiv;
}
