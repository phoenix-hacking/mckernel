# Additive compiler warning correction1

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The first actual Root HOST compile stopped on two unused Rust constants under
`-D warnings`; its original stderr and joined retirement remain preserved.
This successor removes only the unused `GATE_BASENAME` and `CASE_ID` declarations
from lifecycle.rs. Their values remain in the exact protocol interface; the
actual `GATE_PATH` literal is unchanged. No warning suppression is added.

All other Rust source files are byte-exact copies of independently reviewed
review-correction-1/READY2ecd (source reviewc1d30). The original candidate and
review-correction-1 remain unchanged. Interfacef38 is copied byte-exact. Runtime
logic, ABI/ownership fixes,36 prepared controls, serializer, raw log coverage,
oracles and deadlines remain unchanged. No compiler/test executable or runtime
command ran in this source worker. Root owns delta review and qualification.
