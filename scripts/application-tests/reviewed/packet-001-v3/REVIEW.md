# Packet 001 version 3: fixture corrections

This additive revision preserves the original released packet and draft files.
It authorizes source review and pinned-container compilation only. No case may
execute until the global runtime gates and a separate execution release pass.
Independent review and compilation are pending when this revision is created.

- `startup.argv-empty`: the catalog requires argc=4 with `app`, `A`, empty,
  `B`. The previous proposed argv has five elements and the old fixture emits
  an extra environment line absent from its oracle. Install the pinned ELF as
  `/apps/app`, use executable path `/apps/app` and argv `[app,A,"",B]` on Linux,
  and `/bin/mcexec -t 1 0 app A "" B` with literal argv on McKernel. Both engines
  receive the same PATH beginning `/apps`, cwd and exact environment. The
  existing launcher resolves PATH independently of the original argument vector:
  `mcexec.c` calls `load_elf_desc_shebang(argv[optind],...,1)` and then
  `flatten_strings(...,argv+optind,...)`; the Rust build retains these semantics.
  Actual guest execution must still prove the contract.
- `startup.environment`: freeze the original draft's two key/value pairs and
  require the third key to be absent, including rejection of an empty value.
  Inspect actual getenv results before emitting the fixed-shape JSON record.
- `startup.stdout-stderr`: the old source wrote four stdout-indexed bytes to
  stdout instead of its declared stderr payload. The corrected case alternates
  sixteen 256-byte chunks on each real descriptor. Stdout is bytes 0..255
  repeated sixteen times; stderr is bytes 255..0 repeated sixteen times. Every
  write and partial-write continuation is checked. Streams are independently
  byte-compared; cross-stream ordering is not imposed. This case deliberately
  emits binary streams instead of a JSON success record, as its catalog requires.

The oracles freeze these contracts before execution. They are independent byte
sequences, not output learned from any run. No extra environment probing is
added to the argv case, and an output label alone never counts as acceptance.
The runner must retain identity, real McKernel routing and normal cleanup evidence.

Negative infrastructure checks must detect wrong argc/argv0/empty-argument
position, missing/wrong/empty environment entries, an unexpectedly present third
key, incomplete stream writes, truncated output and wrong raw exit status.
Those fixtures are not to be executed on the workstation as application evidence.
