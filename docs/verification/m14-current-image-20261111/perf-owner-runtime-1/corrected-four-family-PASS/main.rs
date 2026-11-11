// HOST-only actual-source changed-function qualification. Not kernel/native code.
#![allow(dead_code,unused_imports,unused_mut,non_snake_case)]
#[path="production/abi.rs"] mod abi;
#[path="production/atomic_helpers.rs"] mod atomic_helpers;
#[path="production/lock_helpers.rs"] mod lock_helpers;
#[path="production/rbtree.rs"] mod rbtree;
#[path="production/waitq.rs"] mod waitq;
#[path="production/f03_perf_attr_callbacks.rs"] mod f03_perf_attr_callbacks;
#[path="production/x86_cpu_helpers.rs"] mod x86_cpu_helpers;
#[path="host_lower_effects.rs"] pub(crate) mod host_effects;
#[path="host_perf_bindings.rs"] pub(crate) mod host_perf_bindings;
#[path="spinlock_effects.rs"] mod spinlock_helpers;
#[path="platform_bindings.rs"] mod platform_bindings;
#[path="production/process_helpers.rs"] mod process_helpers;
#[path="production/syscall_policy.rs"] mod syscall_policy;
pub(crate) use syscall_policy::f03_perf_owner;
pub(crate) use host_effects::{cls,mem_helpers,x86_local};
// The actual x86 provider type/no-op math/legacy allocator snippets below come
// from the qualified source. Only named PMU instructions and their effects are
// controlled through the separately reviewed lower binding unit.
#[path="x86_perfctr_bindings.rs"] mod x86_perfctr;
fn main(){unsafe{f03_perf_owner::host_case_driver::run()}}
