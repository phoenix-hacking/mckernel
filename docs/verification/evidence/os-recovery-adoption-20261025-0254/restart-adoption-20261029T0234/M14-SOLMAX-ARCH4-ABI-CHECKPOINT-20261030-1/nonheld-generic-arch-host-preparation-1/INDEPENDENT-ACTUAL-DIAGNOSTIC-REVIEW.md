# Independent actual nonheld generic and architecture HOST diagnostic review

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Decision: **PASS_HOST_DIAGNOSTIC_COMPILE_LINK_PROVIDER_SCOPE_ONLY**. The retained data supports the stated HOST compiler, raw-link and selected input-provider observations. It does not accept SDK21/GCC14, original 389 metadata, default production selection, functional/native behavior, C retirement, M14 file closure or the held caller graph. No compiler, preprocessor, linker, test, guest or produced code was run during this review.

## Evidence bound

| Record | SHA-256 |
| --- | --- |
| `RESULT.ACTUAL.json` | `057f4cc1f6f6f1b9614d65f81e1bd44414e558e9a8ffbab6fe74a37583d9fcb6` |
| `PROVIDERS.RESULT.ACTUAL.json` | `92f24fc0530f613e1a64dbd37938875cdc5d7b480378ca07021110f8cfb9e45f` |
| `DEPENDENCIES.RESULT.ACTUAL.json` | `97b16780ea2a67ee4d4065af47177725450413602b68cc173047b432c0c4e777` |
| `ACTUAL-ORIGIN-MAP-BINDING.ACTUAL.json` | `5c6c5d43db707d1aa89793e9d99955d92e7758b19cfbafce728661804d023b89` |

The retained `run.sh` contains the admitted Rust, architecture C and HOST raw-link vectors, and all three exit files report zero. The result records immediate empty-group validation, the released 4-GiB planning share and the retained compiler streams; Rust warnings remain part of that evidence. The output image is 10,420,016 bytes with SHA-256 `bd1ef83d0489dcb2b5d435a39483b959f8410b3081c116f38601b0f113620932`; the new Rust and architecture C objects are `4ee1de9f3d9ae6c14deb4c7c5de3847cbf0bd5beea6c7e8b2006627e0252d7f0` and `b6b94ed3ae40afb09be84a62626ea3dfb5909a673ec7a946cf63460ed06605a7`. Read-only parsing independently matched these object/image hashes and their symbol tables to the retained result.

Each of the eight generic and four architecture names listed in the provider result has exactly one strong global function definition in the new Rust input and is present as a strong global function in the final diagnostic image. Across the exact 11 recorded link inputs, no other strong input provider for those 12 names was found. The new architecture C object defines `do_signal` and does not define any of the four selected architecture bridge names. The disabled whole-signal `arch_do_signal_core_terminate_result`/atomic-state symbol and the reviewed ARCH5/sigreturn witness symbols and sections are absent from the final image. These observations do not independently validate the full caller graph or unsafe bridge runtime contracts.

The eight retained input paths, the existing generic C object, and the new architecture C and Rust objects are 11 unique inputs appearing once in the actual admitted link command and present in its retained map. The old architecture object path is absent. The HOST linker compatibility form omits the previously unsupported dependency-file option; this diagnostic link is not production dependency proof. Each later link needs its own exact input and witness-identity checks.

The retained Rust and C depfile first-rule multisets match the recorded 142 and 70 references respectively, with no extra entries in the dependency result. The result records the exact source/header bindings; this focused review did not rehash every dependency. The actual architecture source hashes to `78546125873dbf1f3619c2ce678bf9a07cc306b72db73f4597cc3d85ac4146de`, and the admitted phase command maps that exact operand to `/src/arch/x86_64/kernel/syscall.c`; C exit zero is evidence the original `__FILE__` guard passed under that command. The original `ADMISSION.header_origin` descriptive field retained the earlier witness physical path; the additive origin-map binding identifies the actual current operand and is authoritative for this diagnostic. Neither mapping extends the old `b5e9…` full-source receipt or proves original 389 metadata.

The selected production image `1cd7e4e6…` and its 23 generic plus five architecture C definitions remain unchanged; M14 remains 4/6. The four architecture bridge source/unsafe contracts—including GS/TSS, xstate and native lifecycle—remain unqualified. All service holds, Root70 UNKNOWN, resource controls and held generic-C direct-TID/terminate-host and execve-transfer/ACK exclusions remain in force.
