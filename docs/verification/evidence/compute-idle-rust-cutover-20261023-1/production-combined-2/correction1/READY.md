# One bounded M14 capture-cap correction passed its actual-body fixture

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

The private driver changes one callsite: `_m14_observe` now requests1MiB instead
of32MiB. The original `_run_process` body and its existing `0 < cap <=1MiB`
admission are unchanged. The first candidate and committed evidence remain
untouched. No global limit, compiler flag, ABI, ownership or production gate
was relaxed. Larger future observation output fails under the existing cap;
there is no automatic widening or replay.

Known retained outputs fit: memory preprocessing286,557bytes, memory relocation
output331,425bytes, full Rust/final symbol inventories186,705/230,346bytes.
The fixture additionally ran the actual baseline process relocation observer
through the corrected M14 callsite; its485,588bytes fit within1MiB. These are
expected-output evidence, not a guarantee about every future candidate.

The fixture extracts the exact original/corrected function bodies and their
actual dependencies from the pinned driver sources. `_run_process` is AST
identical. Its `Popen` instrumentation delegates to the real implementation;
neither process outcomes nor resource limits are mocked. Thirteen cases pass:

- The original M14 request for32MiB is rejected before any launch.
- The corrected M14 callsite runs a real child that verifies kernel-enforced
  FSIZE exactly1MiB, and runs the actual baseline process `readelf -rW` command.
- Existing `None` and4096-byte caps still launch with their original limits.
- Zero, negative,1MiB+1,32MiB, bool, string and float cap controls are rejected
  before `Popen` (eight controls).

All four real children joined and their groups were absent. The accepted
owned_capture990807ab then joined outer creator3557775/start53664646 with
return0, group absent, closed streams, empty stderr, null error and null
retirement_error. Capture wall time0.475781414seconds, whole CPU0.498190seconds.
It ran CPU6, one sequential job, AS2GiB/CPU30/FSIZE32MiB/NOFILE256/core0.
The work deadline was tightened to32seconds so the unchanged helper cleanup
fits within the granted35+3-second total ceiling. No production compiler,
root, Docker, image build, native workload or old vector suite ran.

Exact corrected pins are:

| Artifact | SHA256 |
|---|---|
| Image driver | `1d1d600cdd1f3a1236c89b736c0d57f4c52b148b2dda30b99afe00b4fcf2724c` |
| Outer owner | `6b8f196220496a91e8ca23bf7aabee5d8ba2656764db59f85f47c418c53e8863` |
| Unchanged provenance | `1be3a017e2ae47a0d1ecfcd4e1d22d7d8d569808e495d2b6d055c851d0582ae2` |
| Fresh compact static request | `3a196216266c320bd59975622a71453e7e126b174801299d1669c7e0b2789c40` |
| Corrected operation proposal | `e8b207bb781cefabb295ca012695760bc36136980c0a907c17e6fd1b0d251b74` |

The owner/request changes only bind the corrected source capsule and a fresh
output/common-exclusion namespace, rejecting the prior namespace. Exact five
kernel postimages, manifest9b86c84a, gitlink authority, toolchain, current110GiB
profile and all other request fields remain unchanged. The compact request is
26,524,779bytes; it was bounded before exclusive creation and reread checked.

`READY-FOR-REREVIEW.json` binds sources, operation, fixture and whole join.
The6,768,647-byte archive retains corrected controllers/request and all raw
fixture/capture data, SHA256
`bca97acbfd937990a701067c77bbef67cbd3c6ee68ebfb964da46c3fada1fba2`.
Focused independent rereview and the normal fresh root admission/release remain
required. Production default linking/native acceptance and full M14 remain open.
