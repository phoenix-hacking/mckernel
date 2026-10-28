Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Body5 replaces actual selected `arch_vdso_setup_log_bridge`: CURRENT116 arch77db1a40
has GLOBAL FUNC153bytes at0x15b0; actual adopted118 source still defines the same
four-event C body. No existing Rust implementation of that public provider was
found. The new private module reuses the real `kprintf` provider/ABI and owns only
event dispatch/message selection. Exact event constants1–4, message bytes, promoted
signed-int32 error arguments, ignored printer return and unknown-event silence
remain unchanged. Real `ekprintf` is an alias for `kprintf`; no dynamic-debug
descriptor, lock/ref, allocation, mapping or I/O ownership is moved or bypassed.
The only unsafe operations call existing kprintf with immutable NUL-terminated
formats and exact int32 arguments. No new formatter or runtime C is introduced.

Three additive private patches bind actual118 arch600159ad/CMake6a1cca7d/lib81eb7976
and preserve all existing selectors and exact fallback C body. No banked117/118,
body3 copy-to, body4 copy-from, held signal/undefined-domain/service path is ported
again or adopted by this lane. Root must compose reviewed candidates centrally,
rebind genuine origin/profile, and perform fullcrate/selected+fallbackTU/default
link checks later. Accepted actual116 artifact evidence remains separate from
adopted118 source; this lane supplies no default/native/file credit.

The genuine-debug-header witness checks variadic kprintf/public void(int,int)
signatures, int32/LP64 widths and real ekprintf expansion. The untouched C body
and four original event defines are extracted verbatim. The fixture includes the
entire Rust module and complete actual ABI file; kernel output is mocked. A
bounded memory-only HOST vsnprintf inside the mock renders formats for capture.
585 pairs cover every defined event, unknown/extreme event values, int32 error
extrema and ignored printer-result extrema, comparing complete format/rendered
bytes, argument presence/value, call counts and all unused trace canaries. One
mixed seven-event sequence additionally checks five real calls in exact order.
An independent Rust expected-message/render calculation checks every capture.
No kernel logger, actual usercopy/ptrace/syscall/MM/hardware/IKC/native/Docker/root/
guest/locks/network provider runs. Original C exists only as a test oracle.

The actual parent followup supplies standing bounded ordinary HOST authorization.
Worker-authored bindings record that authority explicitly; no Root-authored grant
file is fabricated. The exact fixed four argv/new output paths and source/header/
tool references are saved and checked before entry; guardian4889 checks live
account, process identities and strict UTC/MONO/BOOT before every command. Reuse
the existing bounded runner at CPU7/jobs1/AS2GiB/CPU60/wall90. First semantic/oracle
failure stops; only the parent-authorized obvious infrastructure correction is
allowed, retaining original failures and never replaying unchanged failures.
Pure source preparation initially named the compiler header under lib/include;
that pre-compiler path typo and original script are preserved in
preparation-failure-1. Actual header is kernel/include/lwk/compiler.h. No Rust,
C body, ABI expectation, fixture oracle or consumed runtime prefix changed.

Actual HOST outcomes are additive in ACTUAL-HOST-QUALIFICATION.json when run.
Whole-file/native credit remains open. Root retains the BFD physical retirement
obligation separately; these HOST joins never clear it. Only this new sibling is
written. Earlier source/results/grants/failures, controls/caps/credits, dirty tree,
exclusions, stopped scratch21 and permanent27:4 remain unchanged.
