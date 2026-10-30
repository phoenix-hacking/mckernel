# M14 credential provider prerequisite and held candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The private paired credential candidate at `../m14-credential-paired-source-1/PAIR.PRIVATE.patch` remains **NO-GO / held**, including its earlier four-case mock result. Independent review found the host ioctl ABI/error change is unconditional even if the guest experimental option is off. The guest refresh entry returns void and drops the internal refresh failure, so a successful host credential-changing call may return success while McKernel fields remain old. Neither the actual selected native mcctrl provider nor response/mapping ownership, completion or visibility is bound. No end-to-end error or failure-propagation claim is made.

A bounded, dependency-ready check was carried out on the existing mcctrl Rust provider source without changing it or running host/kernel transport. The `control.c` source maps `MCEXEC_UP_GET_CRED` through its callback to `mcexec_getcred`; under `MCCTRL_RUST_HELPERS` it supplies real address and eight current-credential callbacks to `mcctrl_control_getcred_body_result`. That body validates callback presence, translates the supplied physical value with the provided callback, invokes each credential callback and writes all eight integers in order before returning zero. It does not validate that the translated pointer is valid; safe actual mapping/lifetime is a prerequisite, not proved by success in this fixture. The alternative C body has its own analogous writes, but source does not establish which object is linked in the live native module.

`extract.py` copies the actual two Rust bodies from `executer/kernel/mcctrl/rust/mcctrl_helpers.rs`, source SHA256 `abc99c0e160d3a8aa1aa182f37f297cf3827f86faaac559117ae4df3197e9d14`; extracted bodies SHA256 `a3a1c19a080444bff581116fd6eb571ad761d0341818c0742772786e675a738e`. The following command uses only model scalar types and mocked callbacks:

```
python3 extract.py > source-bindings.txt
rustc +1.85.1 --edition=2021 --test test.rs -o test-bin 2>compiler.stderr
./test-bin --test-threads=1 > test-output.txt
```

Two tests pass: the success mock returns zero after eight ordered writes and callback invocations; for each of nine missing callback inputs, the body returns -EINVAL before mapping or writing. This tests only the extracted body with a valid mock output array. It does not bind selected mcctrl binary, real ioctl, real physical address, task credentials, cross-kernel ordering or refresh caller. Result SHA256 `238ceceeb4a8af47816ccda3d7036ddbe40457ea4082e2c13d094978e91384a0`.

Next safe dependency: independently bind the actual qualified mcctrl module's selected source, compiler configuration and relocation to its GET_CRED implementation; prove physical buffer and request/response lifetime plus completion visibility for the original provider. Separately establish an explicit coherent guest failure contract for all credential callers, including the case where the host change has already succeeded. A reversible error cannot simply undo an already applied host change; source must define a correct reconciliation outcome and preserve caller semantics before writing a new implementation. Host/guest pairing and default-off behavior must be designed and independently reviewed. Do not execute a held transport or treat this mock as its qualification.
