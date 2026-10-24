# QMP capacity correction — private source ready

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The released LONG inherited the short8MiB raw QMP default, while its50ms query-status loop could run7800seconds. It failed before60mixedminutes:364 rounds/728reported launches/2008.862mixedseconds. The later24MiB JSON writer check also failed before opening qmp.transcript.json, so that file is absent; exact raw bytes/row counts and growth were not retained. Do not invent them or claim a kernel pass. QEMU was reaped with-9; a fresh same-image session is required after physical clearance.

The six-file candidate binds LONG-only32MiB ordinary raw,128MiB ordinary JSON, existing2MiB raw recovery and8MiB JSON recovery, and1,048,576ordinary rows+4096recovery rows. Every ordinary offending record remains retained beforefailure; hard-reserve overflow remains fatal. No polls/commands/frames are dropped, coalesced or slowed. Terminal quit temporarily uses recovery mode and restores its prior state, allowing original failures to retain priority without ordinarycap blocking quit. Short default8MiB/raw and24MiB/2second capture remain unchanged.

The matched writer/owner cap is136MiB. LONG serialization gets10seconds only afterQEMU retirement; LONG owner readback/JSONvalidation reuses the existing sibling alarm for10seconds only aftercontainer removal/lockrelease. Normalreadback has no added timer. Sharedbuffer rises512→640MiB and logicalgrowth4096→4224MiB;384MiBperfile FSIZE remains sufficient. Maximum pending captures384serial+136QMP+12other+32metadata=564MiB leaves76MiB shared headroom.

The full7800s/50ms model allows156064status/controlpairs,192raw bytes/pair plus1MiBstartup, and96metadata bytes perrow. This is31,012,864raw bytes and91,990,018encoded bytes, below32/128MiBordinary budgets. Nominal312128rows have>3.35x margin beforethefinite rowbound. Actual request/status JSON format is covered by focused fixture; arbitrary larger/fragmented traffic remains bounded and fails truthfully.

Conservative memory uses512bytes perrow including headers/keys/listreference, plus2*34MiBhexchars and136MiBJSON unicode+136MiBencodedbytes. Innerpost-reap serialization including separate384serial/256trace/32metadata planning remains about1526MiB; outerreadback with640MiBpending+row/hexmetadata+136raw+136unicode isabout1494MiB. These are different processes/phases. Exact target-interpreter row-memory checks are prepared; no unmeasured runtime success is claimed. Existing12GiBcontainer/8GiBQEMU and aggregate controls remain fixed.

`SOURCE-READY.json` binds exact released bases/candidates, patch, focused fixture command and remaining root-owned machine-cohort/publication/admission steps. Candidate owner still contains immutable predecessor path/hash data; root must freeze a new coherent namespace and source pins before any runtime execution. No live source or control was modified.

Tests are prepared by extending existing test_qmp_capture.py; no tests/compilers/root/Docker/guest/workload ran in this source-preparation phase. Rootordinarygrant and independent source review remain prerequisites.
