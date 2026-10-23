# Private M14-F05 implementation candidate

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Implemented `clear_range_old_action()` and its `x86_clear_old_action_bridge()` output adapter in `kernel/rust/x86_memory_helpers.rs`. This is the bounded old-PTE classification slice of M14-05-03. It is a private candidate; canonical source and current235 image were not changed.

`cutover.patch` applies to the byte-matching canonical/frozen image10972 sources. `candidate/` contains the two complete proposed source files; `baseline/` contains the four exact fixture inputs. `source-bindings.json` and `selected-scope.json` bind the frozen source and selected inventory flags.

The original C bodies are unconditional in the frozen `memory.c`, so they remain live with `MCKERNEL_RUST_X86_MEMORY_PUBLIC` and `MCKERNEL_RUST_PTE_HELPERS` enabled. They are not excluded fallback bodies. Rust already owns old-PTE decode and final action classification; those existing functions are reused and are not counted as a new port.

The new Rust body owns the previously live C work: snapshot memory-object flags before output publication, publish optional file-offset status, skip page lookup for a file-offset entry, resolve the page for a physical entry, short-circuit its memory-object membership read, read the current free/memory-object state, and publish the optional page output only after classifying the entry. It calls the existing Rust page membership helper directly. The established `phys_to_page` boundary and existing allocator/hash/lock primitives are preserved; their broader implementation is outside this slice. No assembly or allocation/free/flush behavior changed.

Under the existing default PUBLIC selector, the two old C definitions become one external Rust callback declaration. The full original definitions remain in the excluded C fallback branch. Paired C/Rust size, alignment and field-offset witnesses cover the private 40-byte argument structure; C witnesses also check the reused memory-object flag values. No new compute-C behavior or capability flag is introduced.

The bounded CPU6 run passed on the first attempt:

- Exact unchanged original C body and adapter are included by `fixture.c` from `original-clear-range.c.inc`.
- Both variants use the real existing Rust PTE/action helpers and page-mode helper. The complete proposed Rust consumer and frozen `abi.rs`/`page_helpers.rs` were compiled, with unreachable boot diagnostic names supplied by fixture stubs.
- 129,888 vectors passed, digest `b2dcc6cc17fd6765`: 4 KiB/2 MiB/1 GiB and fallback sizes; physical masking; dirty/file-offset combinations; nullable memory objects; zero-fill/private/XPMEM/unrelated flags; zero/positive/negative free flags; missing pages and all relevant page modes; all optional-output combinations; callback-observed output order; flag snapshot preservation when lookup changes flags; current args reads when lookup changes free/object state. An independent action expectation checks both implementations.
- Pinned rustc 1.92.0 and host GCC9 ran sequentially, one compiler job, CGU1, `RUST_MIN_STACK=2097152`, CPU6, AS2 GiB, CPU60s, wall90s plus6s cleanup, FSIZE32 MiB, NOFILE256, core0. Elapsed1.017s, exit0, empty stderr; group3516228 absent after leader join. CPU6 release was reported immediately.
- `fixture-receipt.json` records exact commands, timings, source/artifact hashes and whole-group absence. `fixture.stdout`/`fixture.stderr` retain output. The Rust object defines the new callback and existing action/page helpers. `git apply --check` succeeded against canonical source; whitespace checks produced no diagnostics. The four bound canonical files still match their baselines.

Next executable check: with a new ordinary compile grant, compile the actual candidate `memory.c` using the frozen supported flags and generated headers, confirming the new C layout witnesses and the undefined Rust callback relocation; compile the production Rust library with its actual selected configuration and verify the callback owner. Integration owner then needs the normal matched successor link and applicable native clear/free-range regression before retirement credit. No production link, native validation, M14-F05 closure, or practical35 closure is claimed here. This candidate requires no process.c change and does not affect the root idle-scan lane.
