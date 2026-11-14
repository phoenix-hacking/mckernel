Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

One additive bounded correction for the NEXT117 recipe-coherence family. Original
recipe, parent source-controls/failure evidence and all seven source postimages
remain byte-identical. Use the corrected recipe only after independent review;
no command, source adoption or runtime authority is created by this directory.

Corrected command0 argv_sha256 is
1e16c2698dad82321faa1bfff7ed2b9e00d2197895f79c609b017c69b147630f;
command2 is2d8cb4709ae3dfde39f37148391801d2d9e80b620c99b019942bb0ad8f0c98d7.
Commands1/3 hashes and all four argv/cwd/new_output values remain unchanged.
prerequisite_origin.output now equals/work/output/build/kernel/rust/f06-origin,
the actual Rust metadata environment path's parent and exact arch-I path.

Encoding is the existing canonical_bytes implementation extracted from the
BYTE-bound local source in INPUTS.json, not an invented encoding: json.dumps
with sort_keys=True/separators comma-colon, then one LF, UTF8. The source module
is not imported or run; only that pure AST function is extracted. All four
accepted CURRENT115 PROFILE.SOURCE-ONLY command hash values reproduce exactly
with it. The actual116 runner commands_for_plan and build_only_worker consume
literal argv/cwd/output directly and do not validate argv_sha256. This correction
verifies the recipe field as consistency metadata without pretending it is a
new execution guard. Literal command order, arguments and source bindings remain
exactly what the actual consumer uses.

The separate history table preserves historical116 recorded hashes and computes
historical116 true hashes, rather than claiming copied115 hashes were current.
Both changed116 command rows already carried their older115 digest. The old
candidate origin profile's ancillary argv_sha256 is likewise historical: the
actual derive_f06_origin producer authenticates complete profile BYTE hash and
uses its literal command; it does not read that ancillary digest. Its seven
reviewed source postimages are unchanged. This recipe is the current117 command
hash metadata authority. Historical records are neither overwritten nor revived.

Ten pure controls PASS, including original bad recipe refusal, changed-command
hashes differing from both historical recorded and recomputed116 hashes,
tampered Rust/arch argv refusal, missing finalLF refusal, exact origin-output
path and include drift refusal even if the argument hash is recomputed. A reverse
check restores the original recipe after undoing only corrected digest/path
fields and additive history: no other recipe field changed. No compiler,
Docker/root/guest, source canonical write, grant/nonce/clock/controller, budget
or profile change occurred. Failure family has now used its one bounded correction;
further reproduced failures require expert escalation.
