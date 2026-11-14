# M14 F06: complete source-ownership candidate

Target: `arch/x86_64/kernel/syscall.c` (F06). **File acceptance remains open; M14 is still 4/6 accepted.** This checkpoint is not a new native or final-image acceptance record.

## Implemented

The complete Rust signal-delivery implementation is integrated as `kernel/rust/f06_signal_tail.rs`, rather than remaining an unselected tail inside the generic policy file. The supported-profile selector pairs its Rust modules with the C guards. The remaining XSAVE restore bridge and writable debugger constants now have actual Rust/assembly owners. The existing XRSTOR instruction helper is available at crate scope; its instruction body is unchanged.

The signal implementation preserves handler/default actions, restart policy, alternate-stack/frame handling, pending-node cleanup, lock release, tracing notifications and core-dump dispatch. Diagnostic and allocation-site metadata are derived from the retained, source-pinned C body. The existing compiler replacement checks and Rust dependency-file repair are preserved.

`ENABLE_RUST_F06_SYSCALL_WHOLE` stays **OFF by default** until matching production qualification. Enabling it requires the x86_64 Rust/Linux-6.12/non-UBSAN profile. This keeps an explicit default C control for comparison and does not silently promote an unqualified image.

## Reproducible checks

With the test toolchain from `.github/workflows/m14-f06-qualification.yml`:

```sh
python3 -B scripts/run_m14_focused_checks.py --json-output /tmp/m14-focused.json
python3 -B scripts/restore_ihk_source.py --destination /tmp/m14-ihk
python3 -B scripts/m14_f06_qualify.py --ihk-source /tmp/m14-ihk --output /tmp/m14-f06.json
```

The focused suite compiles the complete signal replacement in both native-layout and legacy-layout configurations. Its real GS/XSAVE/XRSTOR instructions are emitted, not executed. Genuine external provider signatures remain unresolved in this isolated object; it is not a production provider link.

The C-ownership check uses the actual kernel CMake file and genuine project/IHK headers. It checks both the default control and selected replacement at `-O0` and `-O2`, without LTO. The selected C object must have zero defined symbols, zero undefined symbols and no nonempty allocated runtime sections. The control must retain `do_signal`. The new debugger-data check compares all 96 bytes of the actual Rust `debug_constants` object against both real C objects.

Recovery qualification in Actions run [41576209259](https://github.com/phoenix-hacking/mckernel/actions/runs/41576209259) passed 37 top-level checks across 17 modules with zero failures/errors/skips, and the independent C-ownership check passed at both optimization levels. All 12 recovered/staged source objects were verified by their Git blob identities against the downloaded tested sources. The subsequently committed-source workflow is the authority for the final published checkpoint and additional debugger-data comparison.

## Still required for file acceptance

The complete supported production provider/image link and applicable native functional qualification have not been established. After those pass, the supported default selection and file-acceptance record can be advanced using the unchanged M14 criteria. Zero C output and isolated code generation alone must not change the accepted-file count. No native devices, reserved CPUs/memory, installed tools, or host lifecycle were touched by this workflow.
