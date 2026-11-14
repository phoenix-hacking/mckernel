# One bounded caller fixture — PASS, synthetic only

Explicit root allocation after exporter retirement; CPU7/job1/1GiB virtual-address limit/30CPU-second bound/nice19. Direct exit0 in0.452459563s, first attempt; no bounded correction used. CPU7 explicitly released immediately after join to root/2022. Full result and every synthetic source/release/journal remain under `caller-fixture-attempt-1/`; no test files were cleaned up.

- Missing coordinator identity: refuses before lock/effects; all120 candidates remain, zero unlinks.
- Drift in last frozen row: refuses all120 before journal/first unlink; all120 remain.
- Injected second unlink failure: journal records one removed, one failed/uncertain,118 not attempted;119 candidate names remain and all120 retained copies remain.
- Positive full entrypoint:120 exact synthetic removals, complete journal, all120 retained copies and persistent synthetic mutex remain.
- No-follow ancestor rejection and descendant/ancestor exposure distinction checked.

This verifies finite entrypoint flow and failure accounting on tiny private fixture files with privileged admissions mocked. It is not proof that live root process/container/mount census will pass. No root, real cleanup, archive body read/rehash, Docker, guest/build, trim or Git operation ran. Real observation/release/executor identities remain pending coordinator binding and independent review.
