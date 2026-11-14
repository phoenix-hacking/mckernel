# M14 F06 default-off origin route successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source and local CMake-script checks only. No full configure, kernel
compiler, Docker, privilege, guest or native operation.

Independent review identified that installing the e6a-rebound producer at the
predecessor's generic filename could change the default-off origin path. This
successor keeps those predecessor filenames for OFF, and selects distinct
`derive_f06_origin_e6a_guarded.py` and
`f06_origin_command_profile_e6a_guarded.json` only for the explicit combined
option ON. Their bytes are identical to the earlier guarded successor producer
and profile, SHA256 `0eecb12a434415523b744b73f1704f7cc68693ab3a28a328a3e354bf43c83f3c`
and `7b60afe60f069bb863e7c38ca8c28abe8ea682814d0207e54663572adfde7dca`.

The incremental `route.patch` SHA256
`0b9e8b6b4005d16a205d5f90c0606f7854606b28d7c531ff81733486513ff7b6`
is based on the prior guarded private CMake source, SHA256 `0a149e2f...`, and
produces `postimage/kernel/CMakeLists.txt` SHA256
`f34958844cf2a16d25244a3acc7c9610f262bc9cc64aba2db9706cc64a2a2655`.
It is not directly a patch against an arbitrary canonical checkout.

The source mount is part of the route: ON uses the exact guarded architecture C
source and guarded producer/profile; OFF must preserve its original predecessor
source and producer/profile, not mount the ON source. A local mixed-source check
confirmed the retained predecessor rejects the guarded source by exact hash.
This does not show that the e6a base tree alone can configure OFF: that base
lacks the predecessor files. It preserves the existing route where its original
inputs exist and prevents silently retargeting those inputs.

`python3 test_route.py` passed two tests. The first invokes `cmake -P` on the
exact extracted routing fragment for ON and OFF and verifies both path pairs;
the second invokes the predecessor producer's pure source check against the
mixed guarded input and observes rejection. No whole-project CMake configure ran.
The initial `prepare.py` assertion matched a nested indentation substring twice;
`prepare.initial.py` is retained, and one bounded correction anchored the exact
line before the successful preparation. This was a private script construction
failure, not a CMake or kernel result.

`FUTURE-CONFIGURE-PROPOSAL.json` SHA256
`b024be96058d944d50000cee0cc335910839cfc369b3eb85d83a10b885659764`
binds the distinct ON paths and explicitly requires actual generated source,
command, guard flag, effective header/macro and complete include/dependency
closure review. It is source-only with null authority; the stored e6a argv is
historical and does not establish the actual command. Existing full original389,
provider, source/quiescence, `/out/build`, owner, resource, review, release,
compile/link and native obligations remain open. No C retirement is claimed.
