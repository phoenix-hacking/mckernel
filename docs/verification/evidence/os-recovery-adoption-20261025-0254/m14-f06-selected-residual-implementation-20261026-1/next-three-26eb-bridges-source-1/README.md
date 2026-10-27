Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Three genuinely selected current26eb residuals are prepared in disjoint private
directories: arch_copy_to_user_bridge, arch_copy_from_user_bridge and
arch_syscall_forward_context_bridge. Their exact names occur in the dispatcher's
accepted31-function cursor. No old55 census or whole-file retirement inference
is used. The selected object identity is authenticated without a new census.

Both copy bodies are exact excerpts of the existing b2d73c99 private Rust port;
the forwarding body is an exact excerpt of 8bdc1447. Imports and isolated module
selection are the only new Rust composition. Copy adapters call the existing
Rust x86_memory_helpers::copy_to_user/copy_from_user mechanisms and preserve the
original pointer bits, length and signed CInt-to-CLong conversion. The forwarding
adapter calls the existing syscall_policy::syscall_generic_forwarding with the
real context type. No new algorithm, memcpy substitute, logger, context owner,
reference or provider body is introduced.

Each whole-file C candidate guards only its one original body under a new paired
selector; helper-disabled and selector-disabled fallback text is reversible
byte-for-byte. Existing policy extern declarations and callers remain unchanged.
Each isolated policy candidate appends only its private module gate. Dispatcher
must combine these proposals centrally: the isolated private file bridge.rs
must be installed under a distinct canonical name for each leaf (for example
f06_copy_to_user_bridge.rs), with its #[path] updated in the central composition.
The Rust body bytes need not change. These isolated candidates are not three
concurrent canonical writers and must not overwrite each other's policy snapshot.

The proposed three-command recipe per leaf builds a focused Rust archive,
compiles/links the original C and selected Rust adapters with genuine full
headers, then runs a controlled ABI fixture. Copy fixtures cover 175 pairs each:
five pointer-bit patterns, five length values and seven signed CInt results.
The forwarding fixture covers 140 pairs: four signed syscall numbers, five
context patterns and seven full-width signed CLong results. Each side must call
the distinctive inert endpoint exactly once with unchanged arguments and return
the exact expected result. Endpoint functions never dereference these deliberately
opaque pointer values or perform actual user-copy/kernel syscall effects.

This is SOURCE ONLY. Source identity, selector/fallback and provider-predicate
checks pass; no compiler, fixture execution, canonical/default or native claim
is made. Each fresh output remains absent. Ordinary Root CPU6 admission/grant is
required before any proposed command, using the unchanged reviewed supervisor,
04b5/adf account controls, cutoff/boot binding and resource floors. Genuine
usercopy range/fault-fixup/partial-copy behavior, forwarding context ownership,
real process/stack lifetimes, default link and native qualification remain open.

The first source preparation failed on an overly broad symbol-substring check:
legitimate ABI declarations/calls were mistaken for definitions. Its generator,
stderr and failure record remain retained. Root authorized one definition-aware
predicate correction; three extern/call positives and four duplicate-definition
or export-alias negatives pass. No production ABI declaration was removed.
