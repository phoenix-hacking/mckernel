Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is one private SOURCE-ONLY controlled HOST driver. No compiler or runtime
command has run. It consumes the existing typed public entry and all thirteen
adapters unchanged. The canonical Rust orchestration, constants, callback types,
offsets and lock-node definition are exact snapshots, not replacement algorithms.
The existing ABI caller from the successful genuine-header compile is reused with
all its assertions and 22-fact comparison unchanged. Its old four invalid-flags
comparisons also execute both real public entries if this driver is later run.

The C baseline is the original selected C public wrapper with its original
thirteen adapters. It invokes the same canonical Rust body as production. The
Rust side is the exact existing public entry module. Only genuine external
providers are redirected: CPU-local getter, two lock families, process lookup,
hash unlock, VM hold/release, range lookup, translation, fault, physical address
conversion, byte copy and logger. C header declarations and real object layouts
remain genuine. The fixture has no GS/MSR/IRQ/refcount/MM operation. It borrows
static real-layout C objects, checks pointer identities and lock-node alignment,
and records normalized ordered effects. Logger handling reads only initialized
event fields, never record padding or uninitialized members.

The forty paired scenarios cover READ/WRITE across twenty cases: normal,
invalid flags/counts, missing descriptor ranges, unequal lengths, missing/exited
remote process, absent remote VM, credential rejection, missing range permission,
translation fault/retry, fault failure, error after a partial copy, second failed
translation, rejected full range and zero total length. Providers check lock
balance, distinct stack nodes and matching unlock nodes, hash/update locks around
the VM hold, unlocked range boundaries during copy/fault, and one final VM
release. The copy result and normalized effect order must match on both sides.
Expected outcomes also assert the current body independently: normal copies 32,
the partial-failure case copies 16 then returns -EFAULT. That inherited negative
return is deliberately preserved. Controlled sixteen-byte page boundaries are
fixture inputs, not claims about native page geometry.

The four exact future commands build a focused Rust static archive, compile the
genuine-header C fixture, link, and run the driver. They are proposed ordinary
HOST checks requiring a fresh Root grant and the unchanged reviewed admission,
resource floors and limits. The fresh output directory must not exist. No whole
crate/default image or earlier accepted logger/offset matrix is rebuilt.

This qualifies public-entry ABI and controlled boundary orchestration only if
its actual build/run later passes. It cannot prove concurrent real lock behavior,
user-copy safety, real VM mappings/faults, final process-reference lifetime,
current-stack retirement or native/default selection. The direct VMlock192/ABI6
receipt remains unresolved and is not substituted by its historical summary.
The shared canonical body also preserves its current li-based remote range
check; the fixture uses one iovec per side and makes no broader index coverage
claim. Dispatcher retains all selection and production acceptance authority.
