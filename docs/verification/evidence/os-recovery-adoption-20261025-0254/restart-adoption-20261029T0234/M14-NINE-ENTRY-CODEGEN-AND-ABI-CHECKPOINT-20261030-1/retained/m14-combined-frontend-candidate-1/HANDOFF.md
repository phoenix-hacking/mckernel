# Credential-first affected HOST frontend candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private candidate appends the real credential type-check module to the already-passed owner4/participants2 HOST crate, without selecting a C replacement. The source prior to the declaration is `syscall_policy.rs` SHA256 `217091d13694fb04a4b14930256e60dd9decdc5ae771fc101605b609aa35e403`; its new private postimage is `d4424121775c4ff0f07ec2660f8dfe5608b979ef458e6c297be8e86f1dc6ef9f`. The exact unmodified credential module is `702d402f3ba4b423972cc02321866f4eeda6a2d32f84e9e4eeef98cc015542e0`; its original wiring patch is `0230f8623d4e858bd1767df9ed6500833eb83a2c987b13f3df6d973fc7a3156c`. The same declaration is appended at the parent module end, where its `super::current_thread_ptr()` dependency is already defined. The module's private `f03_credential_snapshot_typecheck` cfg suppresses `no_mangle` for `do_setresuid` and `do_setresgid`, so existing default C and production selectors are not changed.

`PROFILE.SOURCE-ONLY.json` SHA256 `92f073cb206ea6c68d8a9198fba2a0ec483f8176f35d3510e155e14dc89d1343` specifies the 166 source rows, 204 Rust argv elements, the prior private perf cfg plus the credential-only type-check cfg, metadata and depinfo outputs, exact original C function names and prototypes, real crate dependencies and real unresolved owner extern prototypes. No fake owner or missing ABI provider is supplied. It is based on the previous actual owner4/participants2 metadata result `8c8e31677dc1f517de5e562a7c188bc588f1dddc51ebb7633c5d0984d6d24d91`, and reuses the admitted HOST toolchain manifest `9f25b4c4d927dfb2ec96abd662ba13a9c7641bb6a0004c84ccb5bd43855ec6c3` subject to current source/tool custody and review. It does not repeat the C witness or toolchain inventory.

`host_gate_typecheck.py` SHA256 `001b11428cf2aaebebf9db649832fcf88d2284a70d6f5ff151a426ef3589e4a6` and `host_typecheck_exec.py` SHA256 `523de7299e36c0c16d22398031e1f9c44bbf353c611201188e892b1414ded4e5` adapt the previously exercised direct staging/exec mechanism to this exact profile, fresh 166-file root and unique type-check grant. Previously consumed and abandoned nonces remain rejected. They and this profile have not been executed or independently reviewed.

Potential next command, **not authorized by this source document and not run**:

```
/usr/bin/python3 -s -E -S -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/m14-combined-frontend-candidate-1/host_typecheck_exec.py
```

Before any operation, independently review the exact sources and owner delta; Root must supply a fresh coordinator grant/nonce, actual control/weekly/resource and inherited-clock checks, exclusive source/tool/output custody, an outer process owner and positive retirement. Credential begin/snapshot/finish/failure owner implementations, serialized host mutation through guest commit, void caller reconciliation and coherent reader contracts remain unresolved; metadata success would not fix them. No production linking, default selection, C retirement, native result, runtime behavior or supported-scope acceptance follows. The single compositor ledger retains all 47 original rows and adds only the two unselected credential source rows.

No compiler, test, toolchain scan, C witness repeat, guest, native, container, mount, privileged, controller or cleanup action was performed for this candidate. Earlier perf and C-header witness successes remain at their exact respective scopes; the prior metadata result does not cover this new module.
