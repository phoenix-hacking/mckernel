Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Whole M07 remains open for one finite item: the requirements-to-preservation join for MPX BNDREGS/BNDCSR (components 3/4) and PKRU (9). P-M07-01 and P-M07-02 remain complete. The existing independent assessment 0d97ef50 is unchanged.

Accepted current-profile evidence proves selected x87/MXCSR/YMM state across syscall, blocking-futex and signal boundaries on two McKernel CPUs: exact 380-byte stdout, empty stderr and exit 0. Its actual headers expose XCR0 0x21f and 2,696-byte XSAVE extent, but the tested mask is 0x7. CPUID advertises MPX and PKU; OSPKE is clear. None of those headers proves MPX/PKRU use, nonuse or noninitial-state preservation.

The retained compiler/application/library declaration deliberately includes possibly required components 3/4/9. It records direct selected bodies without MPX/PKRU and libc pkey APIs containing RDPKRU/WRPKRU, while preserving unresolved transitive applicability. Full-mask/full-extent save/copy/restore is structural support, not the missing observation.

The final 10972f87 image, dca02501 launcher and accepted SDK5 source ba0e1be7 remain bound by the first-V3 acceptance. That lifecycle success and the later LONG app references do not supply this particular used-state fact. Historical CPUID observations are not relabeled as fresh SDK5 measurements.

The smallest remaining resolution is either a bounded relevant-path/eligibility exclusion for these components or one reviewed extension of the existing state-preservation application: establish instruction eligibility first, then seed/read back valid noninitial state for each remaining required executable component, compare it across the existing syscall/futex/signal boundaries and restore the original state. Inapplicable components must be recorded as not executed, never as preservation PASS. No whole-libc audit, IFUNC-address census, AVX512/profile expansion, M14 completion or unconditional guest replay is introduced.

REVIEW-READY.json binds the finite inputs and limits. No source, ledger, runtime, probe, compiler or hardware test was changed or run.
