# Native phase and fault observations

`phase_observations.py` joins the version 1 phase envelope and transport-fault
records with the unchanged typed parser in `owner_observations.py`. It is a
bounded metadata comparison, with `application_acceptance` and
`production_gate_credit` always false. A matching label is not guest acceptance.

The caller freezes a mode and the two nonzero-in-combination 64-bit nonce halves
before collection. Supported mode names are exactly:

| Mode | Number | Final phases | RET errno | Transport errno |
| --- | ---: | --- | ---: | ---: |
| `prepublish-hard` | 1 | Terminal, TerminalPlusFive | -71 | -5 |
| `postpublish-notify` | 2 | Terminal, TerminalPlusFive | -71 | -5 |
| `recoverable-backpressure` | 3 | Recovery, AfterEightHello | 0 | 0 |
| `permanent-backpressure` | 4 | Terminal, TerminalPlusFive | -71 | -110 |

All modes begin with BlockedRead and AcceptedReturn. A complete comparison
requires the original selected worker, read(0, buffer, 16), response ledger
identity, native RET value 16 and accepted bit 1. `owner_contract` is the separate,
caller-frozen contract described in `owner-observations.md`; its payload call and
byte counters remain explicit inputs. The parser does not infer them from the
word “AcceptedReturn.”

```python
prefix = phase.parse_envelopes(
    raw_serial_bytes, mode="prepublish-hard", nonce_low=low, nonce_high=high)
blocked = prefix["snapshots"][0]["owner"]
tid = phase.owner.original_worker(blocked)

comparison = phase.validate_capture(
    raw_serial_bytes, mode="prepublish-hard", nonce_low=low, nonce_high=high,
    owner_contract=frozen_owner_contract)
```

`parse_envelopes` accepts a complete contiguous prefix of one through four
snapshots. BlockedRead collection can therefore precede RET entry and completion.
Its `COMPLETE_PHASE_PREFIX_ONLY` result establishes envelope/inventory integrity;
the RET records present so far must have the original key and the native phase
ordering, and fault events must follow the completed AcceptedReturn envelope
and precede RET leave. It does not require RET records that belong to future
phases. The complete comparison still requires all three RET records.
Use `validate_capture` for the complete mode outcome, RET bracket, actual send
callback outcomes, stable final counters and inventories. Incomplete final
lines, snapshots or envelopes fail closed. This API does not trim an actively
growing serial log to the last complete snapshot; a collector must preserve and
identify any separately selected complete prefix.

Native Rust printk includes the module name. Only `ihk_smp_x86_64: ` is accepted
for OWNER, PHASE and FAULT markers, and only `mcctrl: ` for RET markers. The
mapping is bound to the actual module declarations and pinned kernel's
`rust/kernel/print.rs` crate-prefix formatting. Optional priority and decimal
timestamp prefixes are accepted. Unknown labels, labels on the wrong marker
family, unlabelled markers, unsupported versions and extra fields are rejected.
`canonicalize_line` removes only this exact producer label for callers needing
the unchanged owner's single-line parser. `canonicalize_capture` retains every
other byte and records original and canonical hashes for each marker line.
The parsed result preserves the original full capture as size, SHA-256 and
base64. Owner row hashes identify the derived canonical lines; the explicit
line mapping ties them to the original serial bytes. Kernel timestamps printed
in the log prefix are not used as native phase timing evidence.

Limits inherited from the owner parser are 16 MiB per capture, 65,536 lines,
2,048 bytes per line and 4,096 marker records. Fault event records are capped at
40 and actual send records at 32. Numeric fields use the literal grammar's exact
bounded integer types, with no evaluation of Rust Debug text. Phase nonces use
exactly 16 lowercase hex digits per half. Version, field order, snapshot sequence,
native monotonic time order and count completeness are checked. Invalid or
saturated counters prevent a match.

The complete mode comparison checks the actual callback errno sequence and
post-callback publication timestamps. Mode 2 permits bounded real callback
backpressure before one success and its notification error. Mode 3 requires
the two-second injected hold before actual send, followed by exactly one real
success. Mode 4 requires the retained production timer and terminal observation
after its unchanged five-second deadline. The original RET must leave within
15 seconds. Final and quiet fault counters remain equal; terminal inventories
must remain stable across the separately timed five-second interval.

Two legitimate races matter. AcceptedReturn can have zero barrier attempts if
RET commits after that pump's publication scan. Its `publication_since` can also
be absent if RET commits after the timeout scan; the next advance initializes
the original coarse timer. The parser never invents that timer. For recovery,
an absent observed timer yields `METADATA_MATCH_WITH_MISSING_TIMER` and an
explicit missing deadline-evidence gate. With the timer present, the actual
successful callback must finish before the original deadline. These states are
distinct from `NATIVE_METADATA_MATCH_ONLY`, which also grants no acceptance.

Physical and provenance checks remain external. In particular, automatic
AcceptedReturn metadata publication releases the barrier before a host QMP
controller can guarantee a stopped physical response capture, especially in
modes 2 and 3. The separate physical prepublication-prefix gate remains open.
Never reread the original response after a published or released observation.
Blocked physical response and ring bytes, publication/notification ring evidence,
the actual guest kernel/module/image/hook identities, host task state, UART
acknowledgements, launcher wait status and the eight same-OS HELLO launches must
be independently retained and evaluated. These injected EAGAIN modes do not
prove physical ring saturation. Metadata from independently sampled owner
domains and atomic counters is not a single simultaneous memory snapshot.
