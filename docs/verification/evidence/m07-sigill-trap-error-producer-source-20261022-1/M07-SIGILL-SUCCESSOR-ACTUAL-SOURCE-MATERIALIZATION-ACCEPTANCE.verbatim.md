{
  "scope": "Functional McKernel OS/apps and Rust/assembly migration only; no security testing.",
  "reviewer": "/root/m07_remaining_stager_consumer_review",
  "implementation_ownership": false,
  "decision": "PASS_ACTUAL6959_PRIVATE_SOURCE_RECEIPT_JOURNAL_CLOSED_CAPTURE_ONLY",
  "root": "/home/holden/mckernel-work/host-preparation/m07-sigill-current-image-successor-preparation-20261022-1",
  "source": "/home/holden/mckernel-work/host-preparation/m07-sigill-current-image-successor-preparation-20261022-1/source-materialization-1/materialized-source",
  "source_derivative_sha256": "1c25d0ce017d4b39b9f667e94367e3cd5198b8223f787820e34bb090b19fa2d4",
  "materialization_sha256": "dac8439cb8c70432f4f8fcde60a831552eef6ee79edfac6b5d92d96d8cc90013",
  "references_relative_to_root": {
    "source-materialization-1/materialization-receipt.json": {
      "sha256": "17e14263e9d3d24bd368afba420d58e6e8fd6b587cb26e3c838d689a40a830bd",
      "bytes": 514
    },
    "source-materialization-1/materialization-journal.jsonl": {
      "sha256": "3d5e408e3aaa4722a17be3cb5e5880ac9b4c3444a70fc45441cbb9ccc09c9139",
      "bytes": 1072990
    },
    "source-materialization-1/actual-materialization-capture-1/completed.json": {
      "sha256": "b8ccb3b6da35041ca53dd60c0b1be25ce01f46032aa5ef47054d4ba866f3d16b",
      "bytes": 1170
    },
    "source-materialization-1/actual-materialization-capture-1/direct-join.json": {
      "sha256": "8d28df4aab8c7f60b01a63b2911303e994a71e6f7ced1383f77cd72f956a005d",
      "bytes": 258
    }
  },
  "findings": [],
  "accepted_evidence": {
    "actual_argv_equals_reviewed_materialize_command": true,
    "journal_rows": 6959,
    "unique_paths": 6959,
    "regular_files": 6910,
    "tracked_symlinks": 49,
    "IHK_metadata_entries": 21,
    "journal_manifest_path_and_digest_mismatches": 0,
    "symlink_target_mismatches": 0,
    "receipt_manifest_fingerprints_match": true,
    "overlay_joins": "interrupt.S9cff/5678 and native_signal.rsaea4/12106 exactly match accepted overlay manifest.",
    "actual_validator": "Qualified materializer reached receipt creation after its unchanged full validate_thin_source call."
  },
  "actual_lifecycle": {
    "pid": 3004352,
    "starttime": 44512526,
    "returncode": 0,
    "seconds": 9.429581543954555,
    "child_joined": true,
    "group_absent": true,
    "streams_closed": true,
    "stderr_bytes": 0,
    "errors": null
  },
  "projection_permission": "Root may record this genuine actual-source acceptance and proceed with the existing exact whole-source checker once under its reviewed ordinary grant/profile.",
  "limitations": "Receipt/journal/captures reviewed; no repeated full-tree hash, materialization or producer audit. Whole-source checker, compiler output, image linkage, artifact and native acceptance remain unproven. Root must observe later source/runtime identities rather than infer them from this receipt.",
  "builds": 0,
  "guest_runs": 0,
  "native_credit_delta": 0,
  "execution_release": null,
  "quiescent": true
}