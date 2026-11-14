# M14 F06 origin actual-compile guard successor

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source-only successor. No full-project configure, production compiler,
Docker, privilege, guest or native operation was executed.

The archived e6a command does not prove actual CMake-generated compile flags or
transitive macro state. Under the explicit combined-only selector
`MCKERNEL_M14_F06_ORIGIN_GUARD`, this successor adds compile-time checks at the
actual architecture source, after the `DEBUG_PRINT_SC` toggle and immediately
before clone provider selection. The actual C compiler must see both Rust pairing
defines, reject `DEBUG_PRINT_SC`, require defined `DDEBUG_DEFAULT` equal to zero,
and verify `__FILE__` is the bound `/src/arch/x86_64/kernel/syscall.c`. This
checks actual macro state at that point, including transitive header effects; it
does not establish other headers, ABI, source quiescence or emitted command.
The guard compiles away when the new option is off; no runtime C body is added.

The private CMake successor appends the guard define only when the previously
prepared combined option is selected. It modifies neither default-off CMake
selection nor the archived e6a manual argv. The e6a origin profile/producer is
rebound to the exact guarded source, with archived manual argv explicitly
retained as historical input. Generated clone metadata and origin header retain
SHA256 `71e4b0ab7f5ca612e4cd06bf2150e2e6b7b5e3e39717e466cfb626b1ce249a48`
and `aeece54c3b6f01c326fff3eb925b89b88acd3b198b0047393c8c9c0d78f74ded`.

Exact candidate bindings:

- Architecture C `postimage/arch/x86_64/kernel/syscall.c`: `9a356317ff621decba53a11fe0967ae9eee1bb5059d262e6b2402f90042a4a25`.
- CMake `postimage/kernel/CMakeLists.txt`: `0a149e2fa29522150f1a6bf39d544062581ff7ebd5c528d8f19eb766c1dcb536`.
- Origin producer: `0eecb12a434415523b744b73f1704f7cc68693ab3a28a328a3e354bf43c83f3c`.
- Origin profile: `7b60afe60f069bb863e7c38ca8c28abe8ea682814d0207e54663572adfde7dca`.
- Architecture patch `origin-guard.patch`: `6875c3d318aa3da1d805eb008ca8620ce448f14448f68b49603a7f803b7b612f`.
- Incremental CMake patch `origin-guard-cmake.patch`: `819e63a78173b54bc1f03221cb365eb5f3b8c40c27204d8a44b956a962119056`, based on the prior private CMake candidate, not canonical source.
- Updated future proposal `FUTURE-CONFIGURE-PROPOSAL.json`: `a3130573c981ee0ada6b1a01d1b3b224481e4f4bb20de25eeb8a41580220412e`.

`python3 test_guard.py` passed seven actual extracted-guard C compile cases using
Ubuntu GCC 9.4.0: selected valid input, transitive debug switch, transitive
nonzero default, missing default, wrong origin, missing provider and guard-off
behavior. This fixture uses stand-in headers and `#line` for the logical path;
it is not the real kernel compilation. `python3 test_origin.py` passed seven
source/profile drift and positive tests. `python3 static_check.py` passed the
combined-only selection and source placement check. Output streams are retained;
no failure occurred. The source-only origin producer also succeeded against the
exact guarded C copy and defining debug header. These tests do not supersede the
original389 oracle or demonstrate actual compiler header state.

Before future use: independent review of guard placement, source/CMake/profile,
actual generated commands and all additional macro inputs; ensure the actual
architecture command includes `MCKERNEL_M14_F06_ORIGIN_GUARD`; bind exact source,
headers, `/out/build`, quiescence and fresh release. Full integrated configure,
compiler/link, original389, provider, default, native and C retirement proof
remain open. The proposal grants no execution or cleanup authority.
