# M01-B packet29 correction39 — independent mode-tree ownership

Status: **DRAFT_PENDING_INDEPENDENT_REVIEW**. This additive correction addresses
only the Phase I attempt38 cross-mode substitution. Authenticate PASS packet
review37 SHA256
`130c30d31f4581c31699255559c2447f278559d6250b95f92689272b17480113`,
failure38 record SHA256
`8218fd88a3e1d631d775699d605cf1dcf33d833dbb6678c82bbccf94729d81e2`,
and immutable failure38 archive SHA256
`18653b8eed7614d42e7d72803845fd77f12472762caa3d4569ab7a0a388bef72`.
All packet29 and corrections31/34/36 requirements remain normative.

Each mode owns independent regular-file bytes for its `adapter.rs`, `runner.rs`
and all staged source changes. A mode2 file must not resolve, include, import,
re-export, symlink, hardlink, copy at staging time from, or otherwise depend on
any path below mode3; mode3 has the symmetric prohibition for mode2. Reject
literal or constructed `../mode2`, `../mode3`, absolute sibling-root paths,
Rust `include!`/`#[path]` cross-mode indirection, filesystem indirection, and
runtime file reads of the sibling tree. Every module loaded by a runner must be
the same mode's own regular file beneath that mode root.

Before a successful handoff, verify all 327 Phase I members are regular files,
have link count one, resolve beneath the canonical fresh root without symlinks,
and contain no cross-mode path or indirection. Record each mode's actual adapter,
runner and 51 source-member hashes in the canonical handoff. Shared semantics
may be authored independently, but a sibling tree can never serve as source or
execution backing.

Attempt38 and root38 remain immutable. One new absent root may be selected only
after an independent `PASS_PACKET` review. Correction31 failure preservation and
all prohibitions on Phase II, compilation, execution and acceptance remain in
force.
