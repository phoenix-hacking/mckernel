Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

First attempt compiled Rust and actual C, then failed the host link before any
comparison case ran. The retained362-byte link diagnostic SHA256 is
798601aac871fac6452fabfdb689471b713dee99e1ddc237c7d325a40f828707.
Original source, objects and every capture remain unchanged under ../check-1/.
This is a host fixture initialization/provider failure, not a native OS failure.

Frozen real lib/include/string.h first declares ordinary memset, then maps its
name to __inline_memset under ARCH_FAST_MEMSET. The host test driver initialization
was consequently compiled against the kernel-only inline provider, whose out-of-
line definition is absent from this finite host link. The actual mutation itself
uses memcpy and has no memset dependency.

The sole bounded correction undefines that macro AFTER both exact extracted C
bodies and BEFORE the host test driver. The existing real memset declaration
now resolves test-only initialization to host libc. No fake __inline_memset stub,
production header edit, compiler-mode workaround, mutation change, Rust change,
layout change, expectation change or failure suppression is introduced.
fixture-only.patch shows the complete C delta. The driver/capture implementation,
profile, four stages and checks are unchanged apart from fresh private paths.

This correction is source preparation only. No compiler, test or execution ran.
The dispatcher owns CPU6 admission and the existing complete outer capture.
Any failure of this sole correction must be preserved and escalated to focused
expert review. Native/fullcrate/link/default-path/C-retirement claims remain open.
