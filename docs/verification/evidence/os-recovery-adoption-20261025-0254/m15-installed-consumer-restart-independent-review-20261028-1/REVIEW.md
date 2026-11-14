Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Independent decision: PASS at source/SDK-reuse scope for packet SOURCE-READY
31413165357bb231f8ee1ebf4437b97c6e9d0fc497183ffa532f0a2dc78cb7f8.
The restricted equal-capacity BUILDID reconciliation is accepted. This review
does not release execution or add configure/compiler/link/install/CLI/native,
default-compiler or whole-file credit.

The real SDK11 config literal is `3114d9e` (seven bytes, capacity eight).
The proposed `a7ddca2` literal has the same capacity. The eight-character
`a7ddca26` spelling and actual CMake fallback `1.7.0rc4` have capacity nine
and are incompatible. Future current configure output remains unobserved.
The guard correctly refuses either longer spelling; never replace generated
config or fabricate Git metadata to make it pass.

The pinned ihkconfig Rust source has exactly one IHKCONFIG_BUILDID reference:
`env!("IHKCONFIG_BUILDID").len() + 1`. Its only uses allocate the ioctl output
buffer and terminate its last byte. The get-buildid operation opens `/dev/mcdN`,
calls GET_BUILDID, prints the device-returned string, and closes the descriptor
on the ioctl success/failure branches. No compiled old revision string is used
as runtime version output. The build adapter supplies the configured plain ASCII
literal and the KRM cfg explicitly. Equal capacity therefore preserves the
existing buffer ABI, argument/error behavior and resource handling; this review
does not newly qualify the existing runtime implementation or other provider
buffer sizes. A later native run still needs its real matching provider/profile.

All 58 guarded current source files match their contract (including the private
selector postimage); all 57 files other than that selector also match the actual
accepted source export. All 18 public headers and membership match. There are
no generated public headers in the accepted SDK. All ten actual SDK input hashes
match, including the archive, CLI object, native-library response, producer
receipt and four generated Rust metadata files. The selected whole70 Rust
bodies contain no BUILDID reference. The receipt uses the selected x86_64
Linux/std/stat profile and the listed native-library order. The metadata retains
real ioctl/layout constants and original diagnostic origin strings; the source
witness explicitly fixes `/src/ihk/linux/user/ihklib.c` with #line, so reusing
those values does not invent a `/source` producer or imply a fresh producer run.
Host libc/BFD/toolchain/image compatibility remains an execution-profile
requirement; source/header identity alone does not qualify a different SDK image.

The selector candidate is exactly the canonical selector with the one install
statement split: ihkconfig gains its RUNTIME component, ihkosctl retains its prior
rule, destinations stay unchanged, and an unqualified install includes both.
No target, caller, object selection, CLI source or library provider changes.
The current source selects Rust and rejects unsupported whole-library features;
the explicit external-archive branch reuses the already accepted provider.
The guarded link token lists retain the Rust CLI object, Rust archive, all 70
function/six data roots, strict DSO undefined-symbol checks, BFD dependency and
native-library order. No project C object is added. Direct execution of generated
link scripts bypasses the producer custom commands and cannot prove the ordinary
default compiler path. Recipe fields correctly leave that credit false.

The install parser checks selected arms' expected INSTALL and RPATH_CHANGE
statements; it is not an interpreter or a full traversal proof for the parent
generated install scripts. Root must retain the genuine configure-generated
scripts and their component traversal, actual install receipts, measured ELF/RPATH
bytes and the private-loader result before accepting current installed artifacts.
The old consumer validator binds old installed hashes and must not be used
unchanged to certify newly linked/installed bytes. This is an existing actual
output/acceptance obligation, not a new runtime quota or a claim that the parser
has executed any CMake program.

Independent verification ran one CPU0, address-space-limited 2 GiB Python child
under a 30-second CPU limit, exit0. CHECKS.json records two positive and six
negative pure BUILDID controls, exact selector-edit reconstruction, and real
byte/membership comparisons. The negatives include the eight-character commit
spelling, actual fallback version, equal-width feature drift, C-string escape,
duplicate spaced directive and non-ASCII input. No actual guard entry, CMake,
compiler, link, install, ELF/CLI execution, Docker, guest, root or native command
ran. Original worker evidence and all canonical/dirty files remain untouched.

Next Root action: after its actual controls and fresh operation/account/identity/
resource admission plus applicable execution review, materialize the isolated
coherent source with this exact patch and genuine source identity, then execute
only the first configure argv in GUARDED-CURRENT-CONSUMER-RECIPE.json. Capture its
actual BUILDID/config, selected links and generated install traversal. Apply the
reviewed prelink guard to those genuine outputs and unchanged SDK inputs before
staging the object or linking; any mismatch stops for a concrete comparison.
Then finish the existing guarded links/selective installs and bind a fresh
artifact contract to their real receipts before consumer/native acceptance.

The same immutable UTC1793253600/MONO1035704.5689393478/BOOT1051042.6959879305
ceilings, credit run7f4af94a83b14cc08f97401f5891d965, ceiling57774.852125,
spent floor22812.3311 and all original holds/exclusions/prefixes are preserved.
