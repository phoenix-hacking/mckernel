## Separate active milestone: M15 custom runtime Rust cutover

See [RUST-CUTOVER-M15.md](RUST-CUTOVER-M15.md) and [rust-cutover-m15.json](rust-cutover-m15.json). Existing native IHK/SMP/mcctrl Rust implementations are reused. Remaining project C adapters, executors, libraries and installed programs stay explicit.

This milestone is outside the 35 functional checks and M14. Source selection is not final link/native proof; no completion percentage is inferred from these rows.

| Goal | Project runtime source | State |
| --- | --- | --- |
| M15-F01 | host-kernel/native-rust/mcctrl_vm_write_compat.c | open |
| M15-F02 | executer/user/mcexec.c | open |
| M15-F03 | executer/user/mcinspect_bfd_shim.c | open |
| M15-F04 | executer/user/eclair_bfd_shim.c | open |
| M15-F05 | ihk/linux/user/ihklib.c | open |
| M15-F06 | ihk/linux/user/ihkconfig.c | open |
| M15-F07 | ihk/linux/user/ihkosctl.c | open |
| M15-F08 | ihk/linux/user/ihkmond.c | open |
| M15-P01 | scripts/mcreboot-smp.sh.in | open |
| M15-P02 | scripts/mcstop+release-smp.sh.in | open |
| M15-P03 | scripts/eclair-dump-backtrace.exp.in | open |
| M15-P04 | executer/user/vmcore2mckdump.in | open |
| M15-P05 | executer/user/mcps.in | open |

M15 closes with the delivered-runtime ownership manifest, actual Rust/assembly project artifacts and matching functional module/application/lifecycle evidence.

