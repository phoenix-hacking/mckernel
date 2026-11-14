Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The installed-consumer lane now has an IHK-relative component patch and an
executable prelink reuse guard. The canonical files remain untouched. The patch
passes `git -C ihk apply --check` at IHK HEAD
`a7ddca26b0dfb087569d652dce5f4262e1311b70`, against selector preimage
`a21e1cfbb064a03458201bfbea520d2f04e87ea287f58451d65031e74d728369`.
Its postimage is the already-prepared `fd6b3959` candidate, without another body
port. Splitting ihkconfig's install rule adds `ihkconfig_runtime`; unqualified
full installs retain the CLI, library and ihkosctl rules and destinations.

All 28 existing Rust/buildadapter inputs, 18 public headers, four ABI witnesses,
the top-level/IHK CMake/config templates and the remaining source dependencies
match the SDK11 accepted source. The guard binds 58 current source files, ten
accepted SDK files, both exact generated link commands and the two selective
install/RPATH rules. The accepted archive/object/native response, four generated
Rust metadata files, actual stat configuration and producer receipt are reused.
The seven original artifact hashes, including installed CLI/DSO, still match.

The concrete compatibility gap is BUILDID: SDK11 config contains `3114d9e`,
while current IHK HEAD abbreviates to `a7ddca2`. No current configure was run, so
the actual future generated BUILDID remains unobserved. Whole-file config
equality in the original recipe would refuse that ordinary source revision.
The pinned buildadapter passes BUILDID to IHKCONFIG_BUILDID, and the pinned Rust
CLI reads it only to compute buffer length plus one. Neither the whole70 Rust
bodies nor the generated ABI constants consume BUILDID. The prepared guard
therefore permits only one plain ASCII BUILDID spelling change of equal byte
length, preserving capacity eight, while requiring every other config byte and
all header membership/bytes to remain exact. Different capacity, feature drift,
duplicates and unsupported encodings are refused. This bounded reconciliation
requires independent review before execution use. A source export that generates
the longer fallback version will fail; do not replace its config or fabricate Git
metadata to pass.

`GUARDED-CURRENT-CONSUMER-RECIPE.json` replaces the old implicit prerequisites with
the guard and an explicit destination-directory command before staging. Its eight
commands configure the isolated current selection, validate reuse, create the
private destination, stage the accepted object, execute two generated links and
install the two runtime components. No `make`, `cmake --build`, Rust compile or
SDK source export is replayed. Exact generated link templates retain all 76
provider roots, strict undefined-symbol checks, accepted archive/object operands,
native-library order, selected BFD linkage and current build RPATH. A mismatch
stops before linking and needs a concrete comparison, never a broader match.

The original six-command fresh installed-consumer recipe remains a separate
ready dependency for the already-installed SDK11 bytes. Its pinned loader/image,
four public CLI imports, 70 function/six data providers, usage stderr/exit1 and
normal child-retirement contract remain unchanged. Newly linked/installed bytes
need a new artifact contract derived from genuine link/install receipts; the
retained validator's old installed hashes must not be reused for that claim.

Pure verification passed seven test methods: two positive configurations and
31 negative controls, including rejection of the actual old SDK11 link/install
rules as current rules. The captured Python child joined normally; wall time
0.187899 seconds. These are file/parser fixtures, including explicitly synthetic
archive/object bytes; no CLI/ELF, configure, link, install, compiler, Docker,
module, native or privileged command ran. No HOST runtime, default artifact,
native or file-closure credit is added. M15 F05/F06 remain OPEN.

Root owns the next executable command, the first configure argv in the guarded
recipe, after independent source/execution review and fresh actual controls,
operation and resource admission. This source result does not claim those gates
or clear any retained holder, exclusion or failure. The same immutable window,
credit run and cumulative ceiling remain in force.
