# F03 source-boundary expert correction

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
This is source-only evidence. No kernel, guest, container, privileged operation,
controller or cleanup was run.

The first retained checker counted call-shaped text inside C diagnostic strings;
its bounded correction omitted whitespace between `=` and the function name.
Both original failures remain in `../m14-f03-remaining-boundary-check-1/`.

The expert checker masks C comments and literals before isolating `do_mmap` and
counting the two assigned and one discarded direct calls. It also verifies the
bound C wrapper, Rust VMA chain and absence of the named kfree flags from the
exact composite CMake. In-memory regressions cover spacing, inert comments and
strings, and rejection of missing or extra direct calls. These are bounded source
checks, not a full C parser or proof of configured selection.

Actual direct call sites are physical source lines 6436, 6552 and 6753. The
`set_host_vma` C body returns to `set_host_vma_body_result` before its later
legacy mprotect forwarding code, so that later text is not the reachable branch.
The selected Linux-6.12 Rust body routes through `clear_host_pte_body_result`
and a three-argument forwarding provider; that dependency does not clear a held
forwarding, ownership or caller path.

Final invocation: `python3 -B check.py > final.stdout 2> final.stderr`; exit 0.
`check.py` SHA256 `0557ce52b7608946dba763489e83dee3a89713451909df35e90a4a09ffb5c36a`;
`final.stdout` SHA256 `728346b695c4c9597fc8d131307c90dcccf7f625355b7c4e9a36b66f033730a8`;
`final.stderr` empty SHA256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The output records all five input source hashes. Source/ABI/caller review,
actual flags, ownership, compilation, linking, native and acceptance remain open.
