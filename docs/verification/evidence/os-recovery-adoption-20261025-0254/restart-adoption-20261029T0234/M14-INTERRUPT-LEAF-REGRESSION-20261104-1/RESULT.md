Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This private host-only regression imports the actual Queue C `syscall_interrupt_arity3.rs` (SHA256 `c5c33714855e6417a8a40823c302e368fd1681eef9342bed0d6cfce787387251`) without editing it. Mock context/thread/process structs and a mock generic forwarder check kill number 62, signed-to-u64 pid/signal conversion, tid, and zero arguments 3–5 in four debug/error combinations. Both modeled origin cfg variants check their original debug line constant. A C logging stub counts calls; it does not verify their formatted text. The compiled leaf and tests passed, using Rust 1.85.1 and GCC 9.4.0:

```
work=$(mktemp -d /tmp/m14-interrupt-regression.XXXXXXXX)
cc -std=c11 -Wall -Wextra -Werror -c log.c -o "$work/log.o"
rustc +1.85.1 --edition=2021 -D warnings fixture.rs -C "link-arg=$work/log.o" -o "$work/fixture"
"$work/fixture"
rustc +1.85.1 --edition=2021 -D warnings --cfg f03_interrupt_origin_dispatch fixture.rs -C "link-arg=$work/log.o" -o "$work/fixture-dispatch"
"$work/fixture-dispatch"
PASS: four debug/error cases, exact kill number and six arguments
PASS: four debug/error cases, exact kill number and six arguments
```

The first compile failed because the fixture's `assert_eq!` created a shared reference to a mutable static under `-D warnings`. The single correction copies the counter into a local first; the command above then passed. No production leaf was changed. Fixture SHA256 `7e60b572997dec4575c05f2d116eb24d11f3564bda6a3367fc026381016ddff4`; C stub SHA256 `ce531d1a203906c26a45c14a0ee7cb778b11153b27792cca9a87b17bc7be39ec`.

This does not validate real kernel layouts, the selected forwarding implementation, debug metadata text, lifetime, compilation in the full candidate, link, native behavior or retirement. Existing independent review and pending-slot ownership holds remain. No native operation or controller change occurred.
