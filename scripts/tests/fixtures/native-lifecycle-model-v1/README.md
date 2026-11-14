# Native lifecycle publication model v1

Every result is `MODEL_ONLY`. This is a safe, bounded producer-state model—not a
native ABI, production hook, runtime collector, application result, or production
gate. Its authority and source requirements are:

- `docs/verification/stability-native-collector-lifecycle-model-design-20260915-1.md`
- `docs/verification/stability-native-collector-lifecycle-model-correction-map-20260915-1.md`

`vectors.json` contains strict eight-field JSON operations and fault seeds. The
harness validates them without accepting booleans as integers, then converts them
to a width-checked canonical line representation for two standalone models. Each
model emits one strict JSON result array per operation. Exact literal expectations
are expanded only by named pool substitution; no oracle transition is computed.
Rust and C must each match those literals before cross-comparison.

The model retains separate process and thread registries and never removes retired
identities. Unpublished exclusive destruction authority is created only by
allocation, is irreversibly revoked by added references or consumed by birth, and
may be consumed exactly once by aborted unscheduled destruction. Numeric PID/TID
values are checked attributes; the seven-component key is identity.

Limits: two applications, four processes, eight threads, 128 operations and 256
event attempts per vector. Sticky event loss never blocks state cleanup but always
prevents complete capture. Deterministic interleavings do not prove real races,
memory ordering, durable transport, deadlines, native lifetime hooks, or ABI
acceptance.
