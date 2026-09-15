# Linux collector adverse-v1 source packet

This packet is source-only until an independently reviewed build and root
execution packet enables it. It generates separately named guarded binaries
from the released collector source. Selector 0 is the unchanged control;
selectors 1, 2 and 3 are missing setup, 383-byte setup and completed-wait
interruption respectively. No production collector is replaced or modified.

Every attempt must retain the exact source and SHA, unique-match patch,
generated diff, compiler/dependency/ELF bindings, request, diagnostic witness,
setup bytes, both streams, event/report files, raw waits, PID/startticks,
deadlines, container/watchdog observations and verified final absence.

Attempt 4 replaces the earlier metadata emitters with executable programs.
The root owner uses the hash-pinned accepted full Docker inspection, owned
cleanup state machine, private control pipe, inherited serialization lock and
independent watchdog. Both build and run use the restricted UID0 profile;
this is an explicit review assumption. Build does not run a collector payload.
The actual run executes selector 0 and each of selectors 1–3 separately.
All four use the unchanged stdin-devnull fixture and the 40/15-second outer
collection bounds. The container deadline is 300 seconds.

The oracle opens every non-null retained artifact and checks sizes and SHA-256,
the actual null stdin artifact slot, literal request and output bytes, partial
READY packet prefix, process identities, both raw wait results, setup flags,
pipe EOFs, cleanup and the production report's flat timestamps and events.
The completed-wait witness is in the collector's outer stderr; the setup
witnesses are in child stderr. Post-exec observation is permitted for the
completed-wait case because the unchanged loop observes exec before waiting.

Unit tests use explicitly synthetic production-shaped records and real temporary
retained files. They exercise rejected mutations; they do not run a compiler,
collector, Docker container or guest. Before the single attempt-4 unit command,
the dispatcher/worker must retain the exact candidate tree and hash inventory,
command and selected environment; stdout, stderr and exit status are immutable
evidence. Stop after an unexpected result and do not repair within that attempt.
