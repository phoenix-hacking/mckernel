Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Bounded successor to the failed/insufficient projection oracle. Earlier materializer,
oracle, artifacts, hashes and review remain preserved byte for byte. This directory
adds source only; no test, compiler, container, runtime or physical operation ran.
Effective permissions remain danger-full-access/approval_policy=never as confirmed
for this recovered thread. No other writer's files were changed.

exact_projection.py replaces SequenceMatcher/presence checking with strict unified
patch parsing and exact in-memory byte construction. Every nonempty old hunk anchor
must occur exactly once at its stated original line, every hunk count is checked,
all ranges must be disjoint, and staged bytes must equal the entire expected result.
At most 16 hunks are allowed: bounded old-anchor scans and full-byte construction are
O(N) for this fixed batch. Deletion-only edits require actual removal. No difflib,
compiler, subprocess, large diff or test execution is used by the checker.

check_source_projection.py binds the exact real source and patch files in INPUTS.json,
replays both two-hunk C packets independently against their real candidate files,
combines their four hunks with precisely the three eligible constructor C hunks,
and compares the entire staged C file. The staged Rust file must equal the complete
real baseline plus exactly one combined append; that append must itself equal the
two exact approved fragments and module declaration. The constructor must be the
exact approved source. The staged source-file set must contain exactly those three
paths. Thus changes outside approved C ranges or the Rust append, including changes
to held functions anywhere in those full files, fail whole-byte equality.

The complete host patch is independently replayed and must equal exactly the two
specified original-function edits; the full host function must also match that
expected correction. Every host byte outside those edits is copied unchanged from
the real baseline. This closes the earlier gap where the checker only looked for
strings in a function fragment. It supplies source consistency only.

test_exact_projection.py provides 17 small synthetic cases: correct projection;
deletion-only fake; extraneous held-C placeholder change; missing Rust append;
extra combined Rust; changed Rust baseline; repeated anchor; overlapping unique
anchors; repeated hunk; host patch/outside change; host function change; constructor
change; extra staged path; malformed count; wrong exact line; new-file section parsing; and hunk resource bound.
No real held caller/request content is used in synthetic negatives.

The uti_info move remains CONDITIONAL on an inactive, exclusive single descriptor
for the attempt, with no prior outstanding borrower. The actual intercept uti_desc
is process-wide static: the source and original review do not prove this condition.
The descriptor's previous uti_info state is deliberately unchanged on preactivation
failure; unchanged previous state is not proof that it was safe. Descriptor reuse,
prior/other borrowers, worker cancellation, activation/switch UNKNOWN, current
thread/stack, context/physical mapping, final host use and drain remain OPEN. Neither
the exact source checker nor callback fixture supplies a lifetime ACK or clears any
held scope/default/global selector. The existing do_syscall/util selector gates and
all original physical execution/ownership controls remain unchanged.

Exact cheap next check for Root's reviewed CPU6/1-job/512-MiB pure source-test
profile, subject to its fresh owner grant: working directory is this directory;
argv ["python3", "-B", "-m", "unittest", "-v", "test_exact_projection.py"].
Then, as a separate command under the same valid profile/grant, argv
["python3", "-B", "check_source_projection.py"]. Both are UNRUN here. No kernel
or host code is executed by either. The existing actual-body Rust callback and
selected-header ABI compile/run checks remain separate pending work.
