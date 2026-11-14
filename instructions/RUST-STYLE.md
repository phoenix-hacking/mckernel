# Rust style

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This is the target style for all maintained project Rust, including new functional
test code. Apply it immediately to new and substantively changed sources. Working OS behavior,
M14/M15 implementation and qualified native results take priority over appearance.
Keep a style-only change separate from a behavioral port when practical. Do not
rewrite untouched files or refresh hash-bound evidence to satisfy formatting.

## Readability

Use idiomatic Rust names, focused functions and leaf modules named for their main
abstraction. Keep module roots mainly declarations and deliberate re-exports.
Prefer clear types and ordinary functions over unnecessary macros or traits.
Use standard conversion naming and descriptive lifetimes where relationships are
nontrivial. Keep comments useful: explain invariants and reasons, not each statement.

Keep lines within 100 columns where practical. Use four spaces and LF line endings.
Manually wrap prose and use lowercase hex digits in new literals. Preserve readable
ABI tables, literal strings and exact generated or protocol bytes when wrapping
would obscure or change them.

Prefer explicit imports. Manually separate standard-library imports (`core`,
`alloc`, or `std` as applicable), external dependencies, and local imports with blank
lines. Import items from one module per `use` statement; group sibling items inside
braces. Avoid glob imports outside small test scopes or deliberate re-exports.
Use qualified free-function calls when their origin would otherwise be unclear.

## Kernel contracts

Preserve `no_std`, existing target editions, calling conventions, exported symbols,
layout attributes, integer widths, error codes, config gates and assembly interfaces.
Existing ABI spellings may intentionally differ from ordinary Rust names. Do not
rename or reorder fields, change visibility or alter link selection for aesthetics.
Required pinned language features remain valid; style does not replace toolchain
or build admission. The compute crate currently uses edition 2021 and required
feature gates; the host build has its own pinned Linux integration requirements.

Prefer borrows and slices when ownership need not transfer. Make resource ownership,
lock scope, initialization, teardown and error rollback visible. Keep lifetime
relationships honest; do not add cloning, reference counts, allocation or broad
generic abstractions merely to silence borrow errors or shorten a signature.

Use contextual `Result` errors inside Rust where callers need recovery information;
use `Option` for straightforward absence. Translate at existing FFI boundaries
without changing their return conventions. Preserve allocation-free/no-panic paths.
Do not introduce a panic into kernel handling of routine input failure. Assertions
should identify the invariant and useful values, with meaningful failure messages;
never replace a production error check with an assertion that disappears in release.

Use the smallest practical `unsafe` scope. Each unsafe operation needs a meaningful
`SAFETY` explanation covering the actual pointer validity, alignment, lifetime,
aliasing and synchronization assumptions. Public unsafe APIs document caller
obligations in a `# Safety` section. Tie claims to the real guard or ownership
contract, including IRQ context and user-copy requirements where relevant. Preserve
reviewed volatile/atomic ordering and assembly constraints. A cosmetic unsafe-block
split must not introduce references or extend object/lock lifetimes accidentally.

## Formatting a reviewed change

The explicit `config/rustfmt.toml` uses stable options supported by rustfmt 1.8.0 shipped with
Rust 1.92.0. It does not set a target edition or enable unstable features. Import
grouping, comment wrapping and hex case remain manual review because the corresponding
formatter options are unstable in that version. Module declaration order is retained.

The configuration is passed explicitly, so adding this tooling does not silently
change direct formatter invocations on frozen evidence or third-party inputs.
A later root-level config requires its existing consumers to be reconciled first.

Using available ordinary resources coordinated with active source owners, check
only named canonical sources:

```sh
python3 scripts/check_rust_style.py \
  --rustfmt /absolute/path/to/pinned-1.92.0/bin/rustfmt \
  --edition 2021 kernel/rust/numparse.rs
```

Use the selected target's actual existing edition. The helper is read-only and
prints a diff; exit 0 means matching bytes, 1 means a formatting difference, and 2
means an input/formatter diagnostic. It feeds one selected file at a time through
stdin so external module children are never visited. It rejects all formatter
stderr, including ignored-option warnings. Review and apply only the intended diff
through the source owner's normal workflow, then retain appropriate build/link and
native proof for any semantic change. Formatting does not prove ABI or behavior.

The first helper covers tracked runtime Rust under `kernel/rust`,
`host-kernel/native-rust`, `executer/kernel/mcctrl/rust`, `executer/user/rust`,
`tools/crash/rust` and `tools/mcstat/rust`. Tests, fixtures, evidence, retained
snapshots, generated and third-party code are outside its scope. New untracked
files enter after the owning change tracks them; expanding the source roots is a
small explicit helper change. A source owner must first release any frozen source
binding even when its file lives under a canonical runtime directory.

## References

The general readability principles are adapted for this kernel from the
[Rust style guide](https://google.github.io/styleguide/rustguide.html). Project ABI,
ownership and evidence requirements above govern local exceptions. Formatter
behavior is checked against the
[Rust 1.92.0 formatter documentation](https://github.com/rust-lang/rust/blob/1.92.0/src/tools/rustfmt/Configurations.md)
and its
[stdin module resolution](https://github.com/rust-lang/rust/blob/1.92.0/src/tools/rustfmt/src/modules.rs#L120).
