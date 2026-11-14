```json
{
  "status": "PASS",
  "decision": "PASS_ONE_EXACT_FAILED_OWNER_MINIMUM_READONLY_EXPORT_EXCEPTION",
  "reviewer": "/root/m07_outer_control_closure_expert",
  "implementation_ownership": false,
  "scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.",
  "findings": [],
  "evidence_sha256": "c6f062200e22bd1fefe83a59b657e1b2538b1e5be102b109242e47a95d5e3092",
  "reviewed_core_payload_sha256": "a4c616587ba4b3c32b91490e5ab322de2a0429206ac9fafde085c12460884315",
  "caller_sha256": "71ae1eaa7732d20d54afe940d2692d5c1896cfbde1718e6748ad05b28899da64",
  "conditional_command_permission": true,
  "execution_count": 1,
  "operation_index": 1,
  "max_archive_bytes": 33554432,
  "retirement_and_physical_acceptance": null,
  "native_acceptance": false,
  "application_acceptance": false
}
```

Permission covers only operation1 of the exact reviewed core: the bounded root tar export of `/home/holden/mckernel-work/scratch/m07rp-261022-1/t.owner-a7c3f1249e8b4da28f0c9d65e21b7063`. That directory matches the closed failed owner’s actual parent/nonce. Its caller status records exit1, direct join, group absence and no observer error.

The pending commands equal the core after removing the two declared release fields. Root may insert only:

- `release`: the genuine recorded exception review’s exact path/hash/bytes.
- `root_installed_release_path`: that same review path.

Root must then hash the complete ACTUAL commands file and supply its SHA to the unchanged caller with `--index 1`. Index0 must not execute. Index1 checks existing review bytes and performs no release installation.

Preserve CPU6, AS1GiB, CPU30s, internal timeout30s with 2s escalation, parent35s with 2s grace, stream32MiB, nofile256 and core0; retain current included-plan/capacity admission. Require exit0, direct join, group absence, closed stable streams, empty tar stderr and archive size ≤32MiB. Stop and preserve evidence on failure; no unchanged retry.

This is a fresh export exception, independent of the consumed success-only release. Actual exported atomic results, controller records and failed-owner physical retirement remain pending separate review.