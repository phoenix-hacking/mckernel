# Native collector ABI review — 2026-09-15

Status: **FAIL_DESIGN_FREEZE**. No implementation, build, test or guest run is
authorized by this record. The reviewed proposal is suitable only as a draft
offline synthetic-fixture reducer and must be consolidated and reviewed again.

## Required corrections to the earlier proposal

- Launcher and payload numeric PIDs can legitimately be equal. Use disjoint
  typed identity domains joined by run ID, native application token, retained OS
  identity and OS generation; never require numeric inequality.
- The request wire `osnum` stays zero and is not authoritative. OS/generation
  provenance must come from the retained queue owner.
- Preserve launcher RET CPU and routed guest delivery CPU separately. Only the
  routed guest CPU must equal the request CPU.
- START scheduling has no reply. Require source-bound schedule publication and
  never fabricate a START acknowledgement.
- `exit`/`exit_group` deliberately omit RET. Keep terminal request, actual native
  terminal observation, launcher raw wait and eventual guest retirement as four
  distinct observations. Launcher wait is not the payload result; terminal
  delivery alone is not retirement.
- Existing `Process.tids` is a count, not a TID inventory. Existing selected
  fault owner observations also cannot establish complete normal lifetime.
- Unchanged `mcexec` mixes launcher and payload output. Stream attribution and
  framing require their own source-bound no-loss contract.

## Narrow first implementation proposed, but not frozen

If a later consolidated review passes, it may add only
`scripts/application-tests/native_collector.py`,
`scripts/application-tests/native-collector.md`,
`scripts/tests/test_native_collector.py`, and a new
`scripts/tests/fixtures/native-collector-v1/` fixture. It must not edit existing
evaluators, supervisors, collectors, observers, catalog/release records, native
kernel or launcher code. The first reducer is limited to one synthetic
application, one main guest thread, one worker, one returned `write` delivery
and one terminal `exit_group` delivery. It may return structural PASS only for
synthetic fixture bytes and must return BLOCKED for every otherwise-valid native
capture until producer authenticity and completeness are integrated. Malformed
native data still fails. No application, transport or production credit follows.

The next freeze must consolidate exact strict-width JSON types, duplicate-key
rejection, 4-MiB document/16-MiB raw limits, 4,096 records, 16,384-byte JSONL
records, contiguous sequences and explicit zero-loss capture end; immutable
artifact references; checked raw event offsets and hashes; acyclic raw-event to
derived-observation references; selected inputs and literal argv/environment/cwd;
typed application and thread-instance identities; prepare and START publication;
WAIT/RET/response-claim ownership; terminal/retirement separation; clock domains
and exact deadlines; source-bound loader maps; complete scoped owner snapshots;
bounded filesystem before/after rows; and a complete byte-for-byte stream
partition. Expected maps, owners, side effects and framing must be independently
frozen literal artifacts, never derived from the record under test.

The negative matrix must cover identity/generation reuse, requester/target/CPU
mismatch, response claim/value/order errors, fabricated START ACK, illegal RET
for the terminal delivery, terminal status inconsistencies, forged Linux wait,
sequence/loss/hash/offset failures, loader omissions or overlaps, selected owner
leaks, deletion of unrelated owners, side-effect mismatch, stream gaps/overlaps
or unattributed bytes, exact deadline +1 ns, mixed clocks and signal-only native
outcomes. Tests must parse retained raw fixture bytes, not match substrings or
self-generate expectations.

## Unresolved freeze blockers

1. Authoritative source-bound native terminal encoding and executed hook.
2. Stable thread birth identity rather than TID/pointer aliases.
3. Complete loader and transient mapping observation.
4. Stream attribution for unchanged `mcexec`.
5. Qualified no-loss, clock-domain and ownership capture guarantees.

Reviewed source identities: `runtime_contracts.py`
`6d25c35718c056e9ee67dc8c0f132a650d1020a67cb9d9503a36092bba58b13e`,
`supervisor.py` `8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873`,
`owner_observations.py`
`97466f94dff53fc250509859d164a9858a4f361405ad62b82bb59ab621f77bcf`,
native `application_syscall.rs`
`a1f5e98413a83f7c11c069d23d883379aa64578b55e011dff49c528a236321fd`,
`smp_application.rs`
`c63a0179a648b0ab90c09c55cf5462779de12937cd5fa2dfa461e34ea29f94a0`,
`smp_application_syscall.rs`
`4118de1401f33b2df17393660e6acbce2f337dca8a9cdfcf10965b1d3dc84c55`,
`mcctrl_process.rs`
`392391cc1db8eaf8d26283ca77a7d69150a0bbf026dfd01120970d7fd601a925`,
`application_rpc.rs`
`9f811c86c4e996294a6cd3be6b83315dabd20a3fb375419e091f4b9dedcfad39`,
`application_image.rs`
`25b7810c273c9f4b5dbff073f54e67db52c69636e63760c7d5f62e471b7a61b2`,
`smp_procfs.rs`
`7aba4319fdc6fa76761ca01128c7a7d920c4be85244737167122c914fc1268d5`,
and `mcexec.c`
`0264d8ad51e00fdaa6348c72db16063f61b4284fe3643b4dae00248727fc0c61`.
