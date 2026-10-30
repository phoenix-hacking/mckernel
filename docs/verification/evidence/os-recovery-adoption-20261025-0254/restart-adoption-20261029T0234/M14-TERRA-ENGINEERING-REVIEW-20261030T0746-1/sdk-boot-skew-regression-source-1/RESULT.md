# SDK BOOTTIME clock-skew regression source

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The retained v8 source is the expert bounded correction, already conditionally
source-reviewed; no new owner successor was created. Its SHA-256 is
`fd5663f7ec5dd1e253de4d2254f255fb7b771b229e8fbe9a8f9669b74606d1f6`.
The retained v7 SHA-256 is
`58e9dea81b771bda4454f1598a71e6e285697296965544a38ef8a363cb5bd2c6`.
The existing actual corrected-1 receipt records 9/9 v8 synthetic and 5/5 helper
checks, direct joins and group closure; the v8 review identifies a separate
BOOT-limiting dynamic case as uncovered. No retained check was replayed.

`test_sdk_boot_skew.py` SHA-256
`f6b20a83002d5d492e8af6c8cbc4520bf3562f419bf7af2b1dbb6cd9513ba6b6`
AST-extracts the actual v7/v8 gate with local fake dependencies. It supplies a
BOOT-limiting sample delay and a BOOT retirement-window exhaustion case. It
expects v7's late anchor to produce 80 versus v8's early anchor 70, and tests
that v8 refuses an exhausted window without increasing its call count.

Static syntax compilation via `/home/holden/anaconda3/bin/python3 -I -B -c`
passed. The new fixture is NOT_RUN: the identified existing SDK receipt is
bound to its consumed exact fixture and CPU0 admission, and no separately
reviewed reusable profile covering this new command and input path was found.
No physical execution, SDK owner, Docker, root, live query, controller or native
operation was performed. Watchdog/clock-change/suspend, actual identity and all
physical execution and retirement gates remain outstanding.
