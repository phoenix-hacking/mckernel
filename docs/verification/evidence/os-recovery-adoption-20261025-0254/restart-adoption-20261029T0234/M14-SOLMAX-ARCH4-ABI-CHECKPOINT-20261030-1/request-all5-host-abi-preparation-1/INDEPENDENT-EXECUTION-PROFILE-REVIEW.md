# Independent execution-profile review: all-five HOST request ABI witness

**Decision: conditional pass for the bounded, disjoint HOST-only operation.** This is a source review and conditional profile decision, not evidence of execution or a release of resources. The Root owner must make the fresh admission described below. Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

## Reviewed bindings and operation

- `PROPOSED-EXECUTION.json`: SHA-256 `708c0fd2fed0a09de82336957ab514e1ed98a51e694a5216f88ed0f8995a06a7`.
- `ALL5-HOST-ABI.SOURCE-ONLY.json`: SHA-256 `18d74ceabb8b24acbf2411f9086c3256f37bbdd8af7022d9354aacbaa21cbcb0`.
- Serial shell `run.sh`: SHA-256 `964963cc64f401d8eda143eba3f2b4776fec4a0a831fb1917acded52faaee61a`. Its time-wrapped C compile and `ld -r` argument vectors match the proposal. The link runs only after a successful C compile.
- C witness translation unit: SHA-256 `94de267897da23aaae301bf1c14a983585a058287f1a38a4ae36bd2dd4c271c0`, exact byte concatenation of the candidate generic-C prefix `4af4524be701ecdbaae09fba906c99bd065364c4caefdcf007820f463773eaf4` and reviewed all-five witness suffix `5c8f8550f97498b58d72bc12f05aafccdd80d749498bff7dc8a2eaf37b69b8fe`.
- Previously emitted HOST Rust object: SHA-256 `9c325baf712ccb7157530c1db93eee8688cfa7a8471d43afadf8ead6270f7d29`. Root must rebind its actual bytes before use.

The finite operation is one GCC 9 C `-c` witness compile followed, on success, by one `ld -r` partial link with that Rust object. It has no final-image link, linker script, entry point, input-code execution, production output mutation or native operation. The C flags select the reviewed nonheld perf, signal-forward and request-constructor scopes. The retained baseline exec-defined-tail setting does not authorize or select the held execve transfer/ACK request. This profile excludes the held generic_c direct-TID/terminate_host request and equivalent work, the held execve transfer/ACK request, and FULL28. No held work is released by this decision.

The isolated witness C object and resulting partial object are test-only and must be excluded by identity from every kernel image. Preserve the actual inputs and failures. GCC 9/HOST observations do not establish the original 389/SDK14 production profile, complete original source coverage, native behavior, or M14 acceptance and C retirement.

## Conditions for fresh admission

Root must establish current armed Sol/max controls, included-only allowance below the stop, original and tighter clock ceilings, permissions, namespace, tool and source identities, and absence of overlapping owners before execution. Bind the exact witness bytes and Rust object, generated nonzero config, real headers and include resolution, the GCC driver and its cc1/as support, linker and required tool/support bytes to their admitted identities. Keep the private scratch/output root under the reviewed owner's control, reject aliases or unexpected existing outputs, and retain its pristine admission. Prior compiler/link owners and their groups must already be closed. Protected-native historical UNKNOWN is preserved; this distinct ordinary unprivileged diagnostic operation makes no current-free or native ownership claim.

Use the proposed clean `env -i`, CPU 6, one job and one 4 GiB planning share, with address-space 4 GiB, CPU 150 seconds, nofile 256, file size 64 MiB, core 0 and timeout 180 seconds plus 5 seconds. The proposed maximum is eight processes. The share must fit the aggregate 7-job/22.3811 GiB ceiling with no overlapping CPU 6/4 GiB grant. Fresh available memory must be at least 24 GiB and host/scratch free space must satisfy the 16/12 GiB floors and actual packet needs. These are admission conditions, not inferred guarantees of descendant termination.

Retain direct terminal result, both command statuses when reached, standard output/error, timing, depfile, objects and actual runner PID, birth identity and process group. After the direct terminal return, Root must independently observe the owned group and known descendants absent before releasing the share. The shell's identity writes are not themselves checked by the script: missing, malformed or inconsistent identity/closure evidence is failure or UNKNOWN, not proof of retirement; retain the ownership and evidence in that case. No privileged raw-wait4 requirement is introduced for this ordinary profile.

## Interpretation of the result

The suffix checks real C declarations, scalar/layout assertions and five used witness slots for direct-two, policy-two, direct-three, policy-three and wait4. The policy-two declaration is local to the witness and does not prove an emitted Rust provider. After an actual successful compile and partial link, retain the actual C dependency closure and inspect each of the five slots' real relocations and target symbols, including strong provider binding and symbol types in the resulting ET_REL. Resolve any aliases and relocation addends on the observed output; source labels or a successful linker exit alone are insufficient. These later inspections require their applicable admitted commands; this source-profile decision does not execute or silently release an unlisted checker.

A partial link may retain unrelated undefined references and does not prove the historical full 8-provider/11-input image, production ABI, consumer selection, functional behavior or native operation. Do not insert either witness artifact into a kernel link.

After an actual first compiler/linker failure, this same profile can cover at most one bounded ordinary type, name or header-path correction with the first failure preserved, a fresh source and output admission, the same selector scope, tool family, command family and resource limits. Do not change ABI/layout, unsafe behavior, held scope or witness values/oracle to force success; a change outside those bounds needs its applicable review. Do not repeat an unchanged deterministic failure.

No compiler, linker, checker, test, native, cleanup or controller operation was run for this review.
