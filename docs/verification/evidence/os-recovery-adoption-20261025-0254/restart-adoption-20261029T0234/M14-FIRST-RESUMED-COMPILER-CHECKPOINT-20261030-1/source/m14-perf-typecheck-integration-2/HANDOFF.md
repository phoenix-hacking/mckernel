# Perf owner 4 / participant 2 frontend rerun

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The preserved predecessor `m14-perf-typecheck-integration-1` actually passed whole-crate metadata type-check for owner3 and participants1, SHA256 `91064f0439f3ca69eb47a549874cef19f4394bc45397eae1f8ba6177b8df5b24`; that result does not cover the corrected source. This private successor changes precisely two of its 165 staged source rows: owner4 SHA256 `1ae7b90a48bb80e7b08e034c77332c2d4300fee3649ce1578e46c90106cd8ed6` and participants2 SHA256 `b2b2c3ca6ead9bbe630f94d1937a8abf4e73d92f30d3544b07cdf126dacb4da0`, copied byte-for-byte from `perf-descriptor-participants-2` manifest SHA256 `ee6bd44ccf1f3ff2ccd870b4dec8d16b8cbf2151971c3920361e25fa508eb47e`. Its syscall-policy module declarations and all other 163 source rows remain exactly unchanged.

`PROFILE.SOURCE-ONLY.json` SHA256 `6e46cbc07637ea6985119caffe1993258a8ed1f2a7542a42d9e2d92fffa88083` contains the 202-element rustc argv. Only elements 142 and 197 change for fresh metadata/depinfo and source-root paths; the only environment changes are fresh HOME, TMPDIR and included metadata paths. The same type-check-only cfg and HOST toolchain manifest `9f25b4c4d927dfb2ec96abd662ba13a9c7641bb6a0004c84ccb5bd43855ec6c3` are retained. No C header-witness repeat or new toolchain inventory is proposed.

Private derivatives of the previously used direct staging/exec mechanism are `host_gate_typecheck.py` SHA256 `b8fc9ec7e82afdd4243bc2c5d632fcea495c2f142432f8ef0d90c0fd952f171a` and `host_typecheck_exec.py` SHA256 `b7a8fd40555cfbddcfa58212e871586cdcade9938a24578895e82cceb50f9fc3`. The gate binds this exact profile and rejects the predecessor's consumed nonce. The prospective source/output root and grant are fresh and do not yet exist. No predecessor source, output, consumed nonce or evidence was changed.

Potential direct entry, **not run or authorized by this document**:

```
/usr/bin/python3 -s -E -S -B /home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/m14-perf-typecheck-integration-2/host_typecheck_exec.py
```

Independent review of the four underlying source corrections and this exact profile/owner delta, a fresh one-shot coordinator grant and nonce, current actual controls/weekly/resource and tighter inherited clocks, verified source/tool ownership, fresh exclusive output and an independently controlled process owner with positive retirement remain prerequisites. This metadata-only diagnostic does not select or link production functions. The permanent record owner, descriptor/fork/monitor/IRQ/counter/host/finalization contracts and native/SDK evidence remain open. The one compositor ledger updates only six changed private helper rows; no original C-function retirement count changes.

No compiler, test, toolchain scan, C witness, native, guest, container, mount, privileged, controller or cleanup operation ran while preparing this successor.
