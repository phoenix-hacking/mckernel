"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Pure cold-phase boundary checks. No I/O, observations, approval or execution.
The caller authenticates reference bytes before calling this function.
"""


def validate_boundary_join(refs, boundary, schema, review):
    """Reject incomplete or inconsistent producer/observer/cold reference joins."""
    joins = {
        "nonce_ledger": "nonce_ledger",
        "native_custody_clearance": "native_custody_clearance",
        "observer": "observer_source",
        "independent_current_boundary_review": "current_boundary_review",
        "observer_schema": "observer_schema",
        "observer_schema_review": "observer_schema_review",
    }
    for boundary_key, refs_key in joins.items():
        if boundary_key not in boundary:
            raise ValueError("missing current boundary field: " + boundary_key)
        if refs_key not in refs or boundary[boundary_key] != refs[refs_key]:
            raise ValueError("current boundary/cold reference mismatch: " + boundary_key)
    if boundary.get("author") != "/root":
        raise ValueError("current boundary has no Root author")
    if boundary.get("decision") != "BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY":
        raise ValueError("unexpected current boundary decision")
    if boundary.get("root_attests_exact_current_boundary") is not True:
        raise ValueError("current boundary attestation missing")
    if schema.get("observer") != refs["observer_source"]:
        raise ValueError("schema/cold observer reference mismatch")
    if schema.get("schema_version") != "EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1":
        raise ValueError("unexpected observer schema version")
    if schema.get("current_boundary_key") != "current_boundary":
        raise ValueError("unexpected observer current-boundary field")
    if schema.get("latest_free_key") != "actual_latest_operation_postjoin_acceptance":
        raise ValueError("unexpected observer current-free field")
    for key in ("ledger_key", "expected_status"):
        if not isinstance(schema.get(key), str) or not schema[key]:
            raise ValueError("missing observer schema field: " + key)
    if review.get("reviewed_observer_schema") != refs["observer_schema"]:
        raise ValueError("review/cold observer-schema reference mismatch")
    if review.get("independent") is not True:
        raise ValueError("observer schema review is not independent")
    if review.get("decision") != "PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING":
        raise ValueError("observer schema review did not pass")
    return {"TEST_ONLY_pure_contract": True, "runtime_authority": None,
            "checked_boundary_reference_joins": len(joins)}
