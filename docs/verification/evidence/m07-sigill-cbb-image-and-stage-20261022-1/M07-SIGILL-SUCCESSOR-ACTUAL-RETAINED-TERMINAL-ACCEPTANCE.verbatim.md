```json
{
  "status": "PASS",
  "decision": "PASS_CURRENT_IMAGE_RETAINED_TERMINAL_RECEIPT_AND_CONTROLLER_JOINS_ONLY",
  "reviewer": "/root/m07_outer_control_closure_expert",
  "implementation_ownership": false,
  "scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.",
  "findings": [],
  "container_id": "c8fd6e8525d8d63c43d380f2b045e141568d0847457eed97553a00be821dcbbf",
  "owner_nonce": "99a386bfa1434b96b70441a7c257b4f7",
  "owner_pid": 3015039,
  "owner_start": 44686763,
  "owner_receipt_sha256": "17c6b69546fddd1c0cbccb701d77313ec6ae6e9685bbd5b3421ab8bdcf30ea6a",
  "guard_result_sha256": "35fe62e5b45c1f6de6a50ea7219637f7a3b9b46e69fdb6a3bd7cf2f7a2e4bc2a",
  "controller_pair_sha256": "71274961498eaf5f9479bb054bd2d5456b113a6f14391dbfb3ea5946ab3c94c3",
  "docker_client_terminal_records": 8,
  "lease_absent": true,
  "terminal_container_retained": true,
  "common_shared_retained": true,
  "cleanup_permission": false,
  "artifact_acceptance": false,
  "native_acceptance": false,
  "continuing_global_clearance": false
}
```

The actual dispatcher birth3015036/44686737 joins its direct-wait/status records: exit0, direct join, group absent and empty stderr. Guard execution completes0. Stream hashes and the postjoin receipt/proof references match.

All eight captured Docker clients record exited0. The [fresh retained-terminal inspection](/home/holden/mckernel-work/scratch/native-rust-phase5-current-optin-image-guard-edb0baa5c4924f018ad3e5089c77f4bf/inspect-terminal-fresh.json) matches the current CID/nonce and records exited/PID0/exit0 without OOM or daemon error. Client OS birth/group identities are not added where unrecorded.

The consumed release matches the exact reviewed canonical payload. Common/shared records match their recorded filesystem identities and current owner birth. Their distinct request hashes match the respective authenticated serialization conventions. The receipt preserves `terminal_container_info_current=false`; the separate fresh inspection supplies the later observation.

The controller pair matches its raw protocol records: item `exec-27aa894d-8ea0-4e47-b4d0-4e2137394d7d`, handle59640, completes0 and names the exact outer status hash. Unobserved outer OS fields remain NULL.

The recorded postjoin mutex reacquisition is accepted within its observation scope. This decision permits no cleanup, retry or new operation and establishes no artifact/native acceptance. The dispatcher may record it verbatim while preserving the independent reviewer and original producer provenance.