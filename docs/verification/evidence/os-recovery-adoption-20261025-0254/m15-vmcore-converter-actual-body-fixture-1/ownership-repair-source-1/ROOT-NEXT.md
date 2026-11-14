Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private Rust ownership repair dc0d6f75 is ready for independent source/oracle and
actual HOST review. Canonical source, ACK candidate5205663e, original Rust4e036420,
original40-case evidence,20ownership failures and all first-failure artifacts
remain immutable. No source integration or SDK/native run was performed.

OwnedAllocation registers bitmap, outer chunks and payload immediately. Its Drop
covers allocation, metadata and all early conversion returns. OwnedSectionNames
uses private40B linked blocks (8B owner link + existing32B name bytes) and keeps
all names, including a name allocated before a section-creation failure, until
BFD teardown. Static section names are never owned/freed. OwnedBfd is declared
after names and buffers, so ordinary returns drop BFD before its borrowed storage.

Normal completion consumes the handle before calling existing bfd_close once.
FALSE preserves the original close diagnostic and returns; no second close is
possible. Earlier errors retain their primary diagnostic before Drop invokes
bfd_close_all_done once, avoiding finalization of pending output. This one new
FFI import has exact C bool/Rust bool return ABI, bound to selected pinned bfd.h
line2968 and selected opncls.c920–936. Source facts3db997f0 show unconditional BFD
deletion even on FALSE; section.c confirms name borrowing. After successful close,
all names/payload/chunks guards are explicitly dropped before exact PATH ACK/flush.
Public data layouts, file format, section names/flags/sizes/VMA/LMA and existing
read/write/error-observation logic remain unchanged.

The strict derivative runs the entire actual new Rust command through its real
registered callback. All27 original ACK/read/write/diagnostic checks are retained,
compared field-for-field against their immutable observed results.29 additional
faults cover open/format/time/localtime, each of7 section-create/size/flag positions,
three physical-section lookup failures and abort-close FALSE. Allocation failures
1through7 remain swept; first/middle/last physical read failure retains the same
later observations and diagnostic. Normal-close FALSE and abort-close FALSE each
consume the mock handle exactly once, with no double close or later handle use.

All56cases pass zero-live-project-allocation and zero-live-owned-mock-handle
assertions at return. Dynamic section-name allocation validity and content are
checked at every BFD call and during final teardown. The fake BFD handle now has
an actual separately allocated test object with explicit live/destroyed accounting;
it proves this stated mock contract. The test no longer reclaims producer
allocations after observing a failure. Original ownership failure reports remain.

Actual first repair compiler/link/runtime attempt passes:1Rust1.92 compile,
1nm undefined-symbol inventory,1C test link and56body executions,59direct children
all positive wait4 joined/rc0, wall0.468032s, childCPU0.399138s, peakRSS99916KiB.
CPU0/jobs1,AS2GiB,CPU60,FSIZE64MiB,CORE0 and90s envelope/argv/outputs/joins are
retained under actual-strict-run-1. A source-preparation token-count assertion
failed before candidate output; its correction is recorded separately. No failed
compiler/runtime repair retry was needed.

Limits remain explicit. Official Rocky2.41-63 header and linker-script bytes
match pinned metadata; /usr/lib64/libbfd.so is a script selecting libbfd.a. Actual
selected SDK libbfd.a bytes remain unbound, and no real BFD heap/file descriptor,
file output, SDK or native behavior is qualified here. In selected BFD source,
target cleanup FALSE can skip iovec bclose while still destroying the handle;
this repair never retries that destroyed handle, and mock handle release does
not prove underlying real OS descriptor cleanup. ACK-sink fprintf/fflush errors,
repeated real command sessions and valid native dumps remain outside this matrix.
No whole-file/M15 closure follows from these results.

Next: independent review of candidate, source-lifetime/new-FFI contract, exact
repair diff and strict oracle/results. Root owns any later SDK integration and
must bind the selected actual static archive and preserve all runtime controls.
