# Linux collector storage-fault-v2 source correction packet 6

Status: DRAFT FOR INDEPENDENT PACKET REVIEW ONLY

This additive packet does not release compilation or execution. It supplements
accepted packets 1 through 5 without weakening any schedule, schema, identity,
cleanup, retention, or oracle requirement.

## Pre-ACK state machine

The owner must validate each packet before durable publication and ACK. Exact
kind fields, Python exact types (Boolean never aliases integer), nullability,
selector, sequence, phase, site/object/occurrence, operation result, stat object,
descriptor, acquisition, byte-count, and errno semantics are mandatory. It must
also maintain independent acquisition state: create AFTER establishes the exact
fd/dev/ino/mode/acquisition tuple; BIND consumes that tuple; every later IO joins
it. Imported request acquisition zero is established by the first request-write
BEFORE tuple, remains identical through every request write and request sync, and
has the reviewed 0/7/406 size transitions. Any mismatch is durably recorded and
receives no ACK.

## Absolute phase deadlines

READY has a ten-second absolute owner deadline. RELEASE starts a 140-second
absolute pre-fork/preparation ceiling, preserving the collector's 120-second
preparation deadline plus bounded process/cleanup margin. Receipt of the first
valid post-fork witness narrows the remaining evidence deadline to the earlier of
that ceiling or receipt plus 22 seconds, preserving the collector's ten-second
process and fifteen-second cleanup contracts without an unbounded extension.
Every RELEASE/ACK send retains its independent two-second absolute transport
deadline. An owner-triggered retirement retains the reviewed trigger-relative
22-second 16/1/5 cleanup bound.

## Buffered report and identity joins

Report-flush BEFORE may observe any regular-file prefix size from zero through
the eventual complete report length because `fprintf` may flush stdio buffers.
Flush AFTER and both report-sync packets must observe the exact retained full
report length and the same report acquisition identity. Request-sync must join
the exact request fd/dev/ino/mode tuple established by request-write, not merely
its size and acquisition number.

## Sticky cleanup and failure preservation

Every failed or missing second identity observation, identity birth mismatch,
deadline crossing immediately before a signal, failed signal, unreaped wait, or
nonempty owned scan is sticky in `unresolved`; a later empty scan/ECHILD cannot
erase it or yield `cleanup.complete=true`. The owner preserves the first failure
as `owner_failure` and appends ordered `secondary_failures` for cleanup, capture
fsync, artifact observation, OWNER_RESULT persistence, journal publication, and
directory-fsync failures. Every acquired descriptor is closed on constructor and
unwind failures. When the primary result file or journal cannot be published,
the caller receives the primary exception with secondary context; success is
never synthesized.

## Shared fresh-root layout

The owner exclusively creates one fresh canonical attempt root. It durably
copies and hash-checks the exact original 406-byte request, 76-byte selected
manifest, and 27,448-byte executable fixture into `retained-inputs/`, records
them in an exact `runtime_inputs` OWNER_RESULT object, and invokes the reviewed
ELF with exactly:

1. canonical retained ELF path;
2. `--linux-sealed-infrastructure-v1`;
3. canonical `retained-inputs/request.bin`;
4. canonical `retained-inputs/selected-inputs.json`;
5. canonical, initially absent `collection` path beneath that same root.

The source fixture path named inside the immutable request remains an additional
canonical runtime input and must independently equal the retained fixture bytes;
the later build/run packet must materialize its immutable `/work/...` pathname.
The oracle consumes only this owner-recorded root/layout, repeats all file hashes
with no symlink following, and rejects arbitrary external collection or retained
paths. Compilation inputs remain the four exact packet-3 records and are not
conflated with these three runtime inputs.

No source is accepted by this draft. A fresh independent review must approve the
literal packet hash before these broader corrections are materialized. Compiler,
root, native, application, and production gates remain closed.
