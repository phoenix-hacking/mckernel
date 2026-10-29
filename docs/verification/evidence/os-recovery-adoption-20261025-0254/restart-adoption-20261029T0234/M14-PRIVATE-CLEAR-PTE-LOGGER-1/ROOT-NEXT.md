Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Private source candidate only. Original callback unconditionally calls kprintf
with static clear_host_pte failed. %ld newline and its signed long argument.
No dkprintf descriptor/event/flag gate exists inside this leaf. Existing parent
Rust body logs only when lerror!=0 after the original forwarding/lock sequence;
that entire body and callback order stay byte-identical. CLong=i64 supplies the
selected64-bit C long vararg directly, without guessed casts or width changes.
One unsafe block relies on static NUL termination and matching%ld/CLong only.

Four complete private postimages/patch: Rust child leaf, parent module declaration,
existing policy-selector Cextern with exact old Cstatic fallback in the OFF arm,
and one explicit CMake dependency. No new selector, EXPORT_SYMBOL/registry/API
name, event or descriptor is introduced. Same callback name becomes the Rust
linkable definition when policy helpers select it; actual link binding/resolution
is still untested. No VM/offload body changes or canonical/shared writes occur.

Source checks and git apply --check PASS. Exact format/newline/NUL/long signature,
single unchanged argument/call, existing body gate/order, retained fallback and
line reset before the next debug log are checked. These checks do not substitute
for the original389 linked oracle or runtime proof, which remain unchanged/open.

Settid and ptrace packets stay frozen. In-memory source composition starts with
the separate Settid postimages and adds this packet's C logger replacement,
Rust child module after the unique waitq import, and CMake entry after the unique
x86_memory_logger_bridges dependency. Both sibling modules/dependencies remain
present exactly once. No Settid patch/leaf is duplicated or reapplied here.
Root should merge these exact disjoint insertions onto its then-current reviewed
candidate; do not overwrite one packet's shared full postimages with another.

Next executable only after Root/current119 feedback and a new matching source,
account/resource/operation release: selected mckernel_rust_obj build, selected C
consumer compile/coherent relink, same-name callback resolution and actual matching
functional/native evidence. No compiler, HOST payload, controller, Docker, guest
or native operation ran. Whole-file retirement/native/M14 acceptance remain open.
Weekly allowance only through100%used, reset1793774133 upperbound; M15 paused.
