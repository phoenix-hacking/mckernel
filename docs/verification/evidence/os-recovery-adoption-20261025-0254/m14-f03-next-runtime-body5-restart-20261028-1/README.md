Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Body5 replaces the actual CURRENT116 selected318-byte
`perf_event_open_alloc_event_bridge`, including its inlined `mc_perf_event_alloc`
setup. It reuses the complete existing Rust allocation/init/map bodies and the
complete existing full-event/attribute/extra-register Rust layouts. The new Rust
entry supplies genuine layout offsets, reads original attribute scalars and the
frequency bit, and preserves C int return narrowing. An immutable actual-header
C binding retains the original twelve providers and five constants; no new C
runtime function is added. The original two C entry/helper functions are retained
verbatim in the opposite selector branch. Existing synchronized selectors and
logical-line restoration avoid additional CMake/shared ABI changes.

Source inspection found a real ordering discrepancy in the reused Rust map body:
the original C calls cache-event map, then cache-extra map; the original Rust
reversed these. Both original bodies are retained. The private candidate changes
only that ordering before its first HOST run, keeping the original C oracle and
the same provider values/error/resource/publication contracts.

The HOST driver includes the verbatim original C entry/helper and three complete
C allocator bodies. It separately constructs expected full event bytes, output
pointer state and ordered callback effects. All allocation/free, atomic stores,
event maps, validation, extra-register lookups and hardware initialization are
ordinary local mocks. No actual allocation provider, PMU, MM, syscall, IKC,
module, Docker, root or guest action is performed. ABI52 compares the genuine C
event/attribute layouts, every consumed offset, provider binding and constants
against reused Rust declarations. Attribute frequency is exercised through the
actual C bitfield, including full-width union sampling values.

The fixed1152 C/Rust pairs cover hardware/cache/raw/unknown types, allocation
failure, validation failure, negative/zero/large extra-register IDs, negative and
positive hardware-init outcomes, frequency settings and zero/reference/high-bit/
max sampling values. Four additional null input/output calls check defined
original EINVAL boundaries. Each invocation checks exact provider arguments and
order, both atomic writes, expected entire initialized/partly initialized event,
unchanged entire attribute, exact signed error, failure free and success-only
publication. Reference-cycle bypass retains its original no-map/no-hw-init path.

The actual parent followup_task supplies standing ordinary HOST authorization
for at most4 new fixed compiler/fixture commands after bindings are saved and
checked. WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json honestly records that
authority as a worker-authored receipt; it is not a Root-authored grant. The
three-command fixed plan and existing runner retain CPU6/jobs1/AS2GiB/CPU60s/
wall90s limits and fresh reviewed guardian/account/deadline checks before every
command. The first semantic/oracle failure stops. Original failures and any
allowed infrastructure-only correction remain retained without unchanged retry.

The current canonical source preimages and accepted116 artifact frontier remain
separate. Successful HOST fixture proof does not qualify real allocator/hardware
effects, current default object/image selection, native behavior or full F03
closure. Original project provider code remains explicit debt at its actual
accepted scope. Banked117/118/body3/body4, all held credential/request/endpoint/
signal/service paths, dirty work, failed evidence, scratch21, permanent27:4,
immutable window clamps and cumulative credit identity are preserved.
