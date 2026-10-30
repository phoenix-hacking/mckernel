// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(all(f03_perf_entry_candidate, enable_perf, target_arch = "x86_64"))]
#[path = "f03_perf_group_cleanup.rs"]
mod f03_perf_group_cleanup;
