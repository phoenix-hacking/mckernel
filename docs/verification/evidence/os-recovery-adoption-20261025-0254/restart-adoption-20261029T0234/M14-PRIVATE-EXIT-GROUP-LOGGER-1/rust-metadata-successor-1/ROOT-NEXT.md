Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

This fresh successor supersedes the earlier callback-only/Cmetadata partial attempt
without changing it. Both the selected callback and descriptor are Rust-owned.
The selected C arm is ONLY the existing callback extern; no selected projectC
Ddebug storage remains. OFF fallback retains the old C logger/descriptor. Exact
origin-based#line restoration5675/5680 continues to protect following metadata.

Reuse is the existing private F06 #[used]/#[link_section="__verbose"] static mut
Ddebug pattern, with the same current32B/align8/off24 ABI. The descriptor is private
Rust storage, with no export_name, no_mangle data symbol or new Cdata alias. It
retains af46's exact /src/kernel/syscall.c, exit_group_log_bridge, NULL fmt,
line5678 and flags0. Mutable flags remain visible to the original __verbose walk.
The expected tail padding remains0 and must be measured in the later linked
artifact; this source packet does not pretend compiler padding has been tested.

A volatile raw-address read checks the same nonzero high-byte flag predicate
before the unchanged signed-int%d log. No reference survives over kprintf.
Existing image lifetime and debug-update/exclusion contract remains; volatile
adds no synchronization, atomicity, new lock or ownership permission. Existing
Rust debug walker/update and F06 static patterns are source-pinned in the map.
Parent exit_group log-before-terminate and every process/thread body are unchanged.

Git apply --check and bounded source checks PASS. Full389 source projection is
exactly equal to the unchanged oracle; no expected record is rewritten. Layout
assertions32/8/off24, flag vectors0/1/2/128/255, private storage, selectedC absence,
format/CInt, OFF fallback and Settid/ClearPTE source composition are checked.
Module/CMake insertions match the prior candidate; only leaf metadata ownership
and Cselected storage change. All other packets/canonical/frozen119 stay intact.

Root still needs actual119feedback plus a later source/account/resource release
for compile/Cconsumer/relink, exact full389 bytes including padding/selection,
matching behavior and native qualification. No compiler, HOST payload, controller,
Docker or native operation ran. No whole-file or M14 retirement credit is claimed.
Weeklyincludedonly/reset1793774133 upperbound; M15 paused; no live owned resources.
