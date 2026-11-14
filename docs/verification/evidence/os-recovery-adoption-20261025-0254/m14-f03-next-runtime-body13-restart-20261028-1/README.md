Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

BODY13 moves BODY12's retained32-byte C-initialized debug record
`f03_util_register_desc_debug_v1[1]` into Rust-owned writable __verbose storage.
It does not add another logger implementation or claim another function port.
The exact existing global symbol, repr(C) Ddebug ABI, one-record extent, static
lifetime, writable flags and source metadata remain unchanged. The new Rust
static uses the original accepted C provenance from the retained389-record
registry, including /src/kernel/syscall.c, the original C function, logical line,
null fmt and zero flags. The original update/lifetime contract is retained.

The production C delta changes the BODY12 C definition into an extern declaration.
The Rust delta adds only the used/no_mangle/__verbose static. BODY12's logger
body/global callback and its caller remain unchanged. Exact full private
postimages and small patches from a private BODY12 predecessor are supplied in
SOURCE-MAP-FROM-BODY12.json. Root must first compose/select BODY12 and then this
delta; the packet supplies no canonical integration authority. BODY3–12 and the
reviewed cumulative source remain frozen. Other C storage and registry entries
retain their original scopes, and matching production registry389 proof is open.

The HOST plan compiles only the new Rust data object. It reuses BODY12's actual
already produced Rust logger object and ABI10 witness without recompilation.
A new genuine C consumer/oracle link resolves the unchanged global data symbol
to that new Rust object. The C oracle remains BODY12's verbatim function with a
test-only assembly link-name alias preserving its C identifier/__func__. Its
file provenance is bound to the actual accepted /src path for this storage test.

The fixture compares both genuine records' exact metadata and default/padding
bytes, then uses C bitfield assignments for all256 flag values. Each stored
allocation unit must equal original_line|(flags<<24), and the existing Rust
logger must read that same value through its unchanged extern declaration.
The256 C/Rust flag pairs use an independent exact print/count oracle and full
record snapshots; zero flags suppress output, all nonzero flags enable it.
Resetting flags must restore both initial records byte for byte. No descriptor
address, thread, registration, syscall, MM, IKC, hardware or lock is accessed.
All printing is mocked. Only one final result line reaches HOST stdout.

The actual parent BODY13 followup authorizes this storage boundary and ordinary
HOST under existing standing/aggregate limits. The worker-owned authority record
does not impersonate a Root grant. The same bounded runner retains CPU6/jobs1/
AS2GiB/CPU60s/wall90s, exact new inputs/reused object/tool bindings and current
reviewed guardian/account/tightcap checks before every fixed command. The three
commands leave one inherited correction slot within the <=4 bound. First semantic
or second failure stops. Full PID birth/positive wait4/group/stream/resources/raw
logs are retained. No heavy, Root, Docker, native, guest, network, subagents,
shared writes or new execution framework are introduced. All earlier evidence,
exclusions/dirty work/scratch21/permanent27:4/credit/window identity remain.

The expected new Rust-owned data is32bytes and the selected C data definition is
removed at source; actual default allocation/code/data ownership, full389
registry, matching native behavior and whole-file closure remain open. No new
kernel function, default/native run or file closure is credited by this packet.
