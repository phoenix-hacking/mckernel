# Independent source rereview: sigreturn ABI witness successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: **PASS_SOURCE_ONLY_WITH_ISOLATION_CONDITION**. The successor addresses the previous nested signal-mask geometry and production-array isolation findings in source. No compiler, test, physical workload or native execution was performed. This is not an actual C/Rust ABI comparison, linked selection or native acceptance.

## Bound witness inputs

| File | SHA-256 |
| --- | --- |
| `GEOMETRY.json` | `5b3ef073c45b3e4f7e170f725025c3c5f5375555318cae3264736068f934c50b` |
| `sigreturn-extra-abi.inc` | `5c560e42682c7e6bb180908b3bfde6dddd2a6288a936e38b5c5f257835e0af64` |
| `sigreturn_extra_abi.rs` | `5fa1e835f4c937993323bd6490f1c805fd3ce6f874f73f01c8397dd171860ccc` |
| `make_witness.py` | `2ae312e29303a1440aa9153feb1c7e3ca7a135845d2e1d245377a6667e73f2c3` |

These hashes match the retained `RESULT.txt`. The earlier 40-row geometry is retained, and six added entries compare the actual enclosing thread offset, sigset size and alignment, first-word offset within the set and thread, and first-word width. The inspected x86 C `sigset_t` has `unsigned long __val[1]`, and the C thread member uses that type. Rust uses `#[repr(C)] SigSet { val: [CULong; 1] }` and the corresponding thread member. The added source expressions map those actual fields; numerical equality and compiler behavior remain unproved until a controlled paired-object comparison.

The earlier reviewed frame, register and VM mappings remain scoped to the selected native signal frame and do not alone establish whole ABI, field value semantics, lifetimes or native behavior. Native sigreturn uses the checked FP restore bridge; the raw XRSTOR leaf belongs to the non-native configuration path and must not be counted as native execution.

## Isolation condition

The C array is enclosed by `MCKERNEL_SIGRETURN_ABI_WITNESS_ONLY` and requires `MCKERNEL_NATIVE_SIGNAL_STACK`; the Rust module body is enclosed by `sigreturn_abi_witness_only`. With these gates absent the respective arrays are suppressed. Gate-enabled arrays still carry used/global symbols and may enter a linked artifact: compile and compare them only in separate temporary witness objects excluded from production/default links. Any later production build must use the gates off and inspect selected objects or the final artifact for absence of both witness symbols and sections. Source gates and comments alone do not establish that physical isolation occurred.

Fresh applicable resource controls and independent compiler-operation review remain required before physical compilation. The witness does not establish actual C/Rust layout equality, ownership, linked ABI, native restore behavior or M14 acceptance.
