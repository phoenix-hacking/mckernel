Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private F03 slice: the CURRENT115 selected `perf_mmap` callback is still a genuine
196-byte local C function in the accepted generic syscall object. It is outside
the seven F03 callbacks already adopted for CURRENT116. The private current F03
candidates inspected contain the existing `perf_mmap_body_result`, but no Rust
entry replacing `perf_mmap`. This slice reuses that exact complete current Rust
body and the six actual current x86 syscall getters; neither is reimplemented.

The new Rust entry decodes all six original registers in order and preserves
the C scalar conversions: address/length keep their full width, prot/flags/fd
truncate to signed int, and offset retains signed long bits. The descriptor is
still unused. A genuine header-produced immutable C data binding supplies mapping
flags, perf-page offsets, RDPMC bit and the original `do_mmap` function pointer.
It adds no runtime C function, inferred perf-page layout, allocation, host call,
trace, lock, cleanup or ownership. Existing Rust mapping error handling is kept
byte-for-byte. The selected C callback goes away under the existing
MCKERNEL_RUST_SYSCALL_POLICY_HELPERS selector; ENABLE_PERF and Rust enable_perf
remain the existing outer gates. No CMake, shared ABI or canonical file is edited.

`syscall.c.patch` retains the exact C fallback under the opposite branch and
preserves its logical line state. The unconditional prior directive20792 makes
the fallback start21087; continuation after the removed body remains source-bound.
`syscall_policy.rs.patch` appends the private enable_perf module. Root must
reconcile both preimages before adopting only these hunks.

The HOST fixture includes exact current Rust ABI definitions, getter bodies and
mapping body. Its C driver compiles against actual runtime headers and compares
18 ABI words, including real context register and binding offsets. It invokes
the unchanged original C callback and the selected Rust entry against one mock
mapping provider. Eight cyclic full-width register patterns cover signed int
truncation and negative offsets; five mapping outcomes include four exact
negative errors; four initial capability words cover existing/set/unset bits.
The planned160 pairs each independently assert one exact eight-argument provider
call, unchanged full context, exact entire page bytes and surrounding canaries.
Success writes only data_head16 and capability bit2. Negative errors leave every
page byte unchanged. This exercises ordinary functional argument, ABI and memory
behavior only; no actual mmap, PMU, syscall, Docker, guest or root operation runs.

No compiler or behavioral test has run in this lane. The three-command plan is
NOT a grant. It reuses the previously qualified perf callback HOST compiler
profile as source, with disjoint output paths; Root must bind all required actual
header/tool inputs and obtain fresh ordinary admission before executing it.
The plan's first Rust object compile is the next executable check. No old
account/window/grant/nonce or authority is revived. Deadline2026-10-29T06:00Z and
creditrun7f4af94a83b14cc08f97401f5891d965/cumulative57774.852125 remain unchanged.

Actual removal condition: the current selected generic C TU must have no
defined `perf_mmap`, its actual production descriptor installation must resolve
to `f03_perf_mmap_v1` from the Rust object, and the header-produced data binding
must contain the unchanged `do_mmap` provider and real offsets/constants. Then
the matched image must preserve the original perf mmap/application behavior and
lifecycle before claiming actual runtime retirement. C `do_mmap` remains explicit
separate debt. This packet predicts one C-function removal, with no actual
build/object/image/native count change and no F03 supported-file closure claim.

Other workers' changes, all prior evidence, dirty tree, scratch21, failed96 and
permanent27:4 remain preserved. Root owns integration, Git, compiler admissions,
native release and all control processes.
