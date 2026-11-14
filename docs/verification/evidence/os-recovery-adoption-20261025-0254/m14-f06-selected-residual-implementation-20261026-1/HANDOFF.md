Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

M14-F06 selected mmap flag-provider candidate: ready for source review, with the exact retained configuration now bound; ordinary specific compiler admission remains required.

The dispatcher-selected SHF_ALLOC frontier identifies55 functions/24objects in the retained x86 syscall object and names the three architecture mmap flag providers as actual selected residuals. This candidate binds the frontier JSON; it does not repeat the object census or infer language percentages.

Primary candidate:

- syscall.mmap_flags.c: private entire current translation unit, enclosing only arch_mmap_supported_flags_bridge, arch_mmap_ignored_flags_bridge and arch_mmap_error_flags_bridge in default-OFF inverse MCKERNEL_RUST_F06_MMAP_FLAG_PROVIDERS guard. Original functions and both NOCACHE branches remain byte-exact.
- syscall_policy.mmap_flags.rs: private entire current policy file plus gated leaf-module declaration. Existing root extern callers resolve the exported providers; no shared ABI changes.
- f06_mmap_flags.rs: only the exact existing private fragment's constants and three safe exported flag functions. Existing policy MAP constants are borrowed through super. No logger, lock, special-register provider or mmap algorithm is copied/reimplemented.
- The two .diff files are precise central integration proposals. Materialize leaf module at kernel/rust/f06_mmap_flags.rs when applying the policy patch. Canonical integration belongs to Root.

Activation must pair C define MCKERNEL_RUST_F06_MMAP_FLAG_PROVIDERS with Rust cfg f06_mmap_flag_providers. Independently pair Rust cfg f06_use_nocache_mmap exactly when the genuine selected C compile defines USE_NOCACHE_MMAP. Absence/presence must come from the actual selected config/argv/header proof; neither branch is guessed here. GENUINE-NOCACHE-CONFIGURATION.json now binds the exact retained object/dependency/compile-command/generated-config/provenance sources: USE_NOCACHE_MMAP is undefined for that selected TU, so omit Rust f06_use_nocache_mmap for this candidate. This is an exact-build observation, not an unconditional default. Prior null bindings/RESULT are preserved in BEFORE-CONFIGURATION records. Enabling only one language selector creates missing/duplicate providers and is not admissible.

Focused checks verify current source/fragment/frontier identities, exact generated candidates, full inverse patch reversibility, byte-exact provider reuse, three exports only, no logger/unsafe extras, both NOCACHE source branches and existing huge-mask sign/width. These are source checks, not ABI/compiler/native results. Actual next compiler checks must include original-C/public-Rust exact three signatures/results under genuine selected NOCACHE configuration, selected C provider absence, Rust symbol uniqueness and linked final provider ownership; applicable native scope remains Root-owned. No new oracle or runner is supplied.

The earlier process-VM composition (unqualified private syscall.c/syscall_policy.rs/f06_process_vm_entry.rs and SOURCE-BINDINGS.json) remains a secondary retained proposal. The dispatcher narrowed the final active task to the three flag providers. Do not combine that proposal into this small compiler cohort. Both paths reuse original private algorithms rather than duplicate them.

Discovery evidence: one read-only frontier inspection assumed every list entry was a dict and returned AttributeError after printing the F06 row. Corrected bounded inspection used explicit known keys; no source/runtime operation failed. An attempted guessed config.h pathname was absent; this was not used as configuration evidence. No canonical writes, compiler, container, native, root operation, commit or push occurred.

Configuration continuation: bounded reads found nonzero135464-byte retained syscall.c.o, its2591-byte dependency file, generated build/config.h1055bytes, actual flags.make3993bytes and compile_commands.json74750bytes. Only that exact object dependency closure was examined; named source/header bytes match the retained provenance manifest. No USE_NOCACHE_MMAP macro directive occurs in those selected dependencies, and the exact selected command supplies no macro or forced includes. The configuration check and focused source check pass. No object census or new compiled result was produced.
