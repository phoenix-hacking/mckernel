# M01-B packet29 correction42 — real post-store metadata hook

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This additive correction addresses
only attempt41's nonexistent observer call. Authenticate PASS review40 SHA256
`156b12d414da74512a82d1cd9e8be8008130f014ccd1bcafda1871547a3497de`,
failure41 record SHA256
`4aba65ebea6305122837e3137b1c59b9ca693e29a92576063a087e6de748da66`,
and immutable failure41 archive SHA256
`3281d44021b6af2adfe22ee4cf9f72bd4731e688d7b49acf74a88a28d5ee419f`.
All packet29 and corrections31/34/36/39 requirements remain normative.

In each mode's staged `application_syscall.rs`, extend the actual
`ResponseMemory` trait with exactly this test-only default method adjacent to
`verification_owner`:

```rust
#[cfg(test)]
fn verification_status_store(&self) {}
```

In `Completion::publish`, immediately after the real
`AtomicU64::from_ptr(...).store(1, Ordering::Release)` and before consuming
`response.memory.release()`, call exactly:

```rust
#[cfg(test)]
response.memory.verification_status_store();
```

The mode-local `TestResponseMemory` implementation overrides that actual trait
method and appends exactly one `StatusStore` event to its retained ledger. Add
`StatusStore` to the mode-local event enum. The hook must not access the backing
span, address or published bytes, must not call another module, and must not
fabricate or accept a status argument. `release` records only release/ownership
events and never records `StatusStore`.

The default method and call are both `cfg(test)` and must be absent from the
`cfg(not(test))` token/object path. Structural audit must prove the unique call
is between the unique real status store and release, that both mode-local trait
implementations override it, and that no unresolved `status_store` symbol or
cross-module forwarding helper exists. Row assertions retain packet29's exact
single status-store delta and event order.

Root41 and its archive remain immutable. A new absent root may be selected only
after independent `PASS_PACKET`; correction31's first-failure preservation and
all Phase II, compilation, execution and acceptance prohibitions remain active.
