#!/usr/bin/env python3
"""Retained-byte comparisons for published modes; no physical reads or acceptance."""
import importlib.util
from pathlib import Path
import struct


# Resolve this exact sibling, never a similarly named module on sys.path. The
# caller retains and binds both source files before importing this component.
_BASE_PATH = Path(__file__).resolve().with_name("physical_observations.py")
_SPEC = importlib.util.spec_from_file_location("_published_physical_base", _BASE_PATH)
base = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(base)
PhysicalObservationError = base.PhysicalObservationError


def _scope():
    return {"status": "PHYSICAL_BYTES_MATCH_ONLY", "application_acceptance": False,
            "transport_acceptance": False, "production_gate_credit": False,
            "physical_reads_performed": False,
            "required_external_evidence": [
                "exact_source_image_module_and_original_request_selection_binding",
                "same_os_generation_and_physical_queue_identities",
                "stopped_complete_capture_and_verified_resume",
                "native_phase_identity_order_and_timing",
                "pre_release_owner_proof_for_every_selected_response_read",
                "no_selected_response_read_after_release_became_possible",
                "native_return_errno_owner_inventory_and_controller_provenance"]}


def compare_prepared_response(blocked, accepted, *, worker_tid):
    """Compare the original response with its actually captured prepared prefix.

    The caller must establish both inputs' physical identity and pre-release
    lifetime. No Terminal/Recovery response bytes are accepted by this API.
    """
    base.require(type(worker_tid) is int and 0 < worker_tid < 1 << 31,
                 "original Linux worker TID")
    artifacts = {"BlockedRead": base.retained(blocked, 40),
                 "AcceptedReturn": base.retained(accepted, 40)}
    base.require(struct.unpack_from("<QQ", blocked, 8) == (0, 2),
                 "blocked status/wake must be0/2")
    expected = bytearray(blocked)
    struct.pack_into("<i", expected, 4, worker_tid)
    struct.pack_into("<Qq", expected, 16, 1, 16)
    base.require(accepted == bytes(expected),
                 "accepted differs from source-derived prepared response prefix")
    return {**_scope(), "comparison": "BlockedRead_to_AcceptedReturn",
            "worker_tid": worker_tid, "raw": artifacts,
            "expected_prepublication_prefix": base.retained(bytes(expected), 40),
            "allowed_write_spans": [[4, 8], [16, 24], [24, 32]],
            "first_word_policy": "Preserve original bytes; response.ttid is opaque.",
            "phase_labels_are_caller_claims": True}


def one_new_requester_wake(before, after, requester):
    """Count one selected wake in a complete retained publication interval.

    Read/published/reserved counters and 127-slot geometry come from the frozen
    base parser. Reservations may overwrite a slot before publication; a
    truncated interval therefore cannot prove either uniqueness or absence.
    """
    base.require(type(requester) is int and 0 < requester < 1 << 31,
                 "wake requester type/range")
    first, last = base.queue(before, 501), base.queue(after, 501)
    base.require(first["header"][:5] + first["header"][8:]
                 == last["header"][:5] + last["header"][8:],
                 "outbound queue metadata changed")
    base.require(all(last[key] >= first[key] for key in ("read", "published", "reserved")),
                 "outbound counters decreased")
    start, end = first["published"], last["published"]
    base.require(last["retained_sequence_begin"] <= start,
                 "new publication interval overwritten; uniqueness unprovable")
    matches = []
    for sequence in range(start, end):
        offset = 64 + (sequence % 127) * 128
        packet = after[offset:offset + 128]
        # Native Request::wake() writes precisely these two discriminators.
        # Neither traditional.pid (32) nor request.target (52) is the wake TID.
        message = struct.unpack_from("<i", packet, 8)[0]
        ttid = struct.unpack_from("<i", packet, 24)[0]
        if message == 0x14 and ttid == requester:
            matches.append({"sequence": sequence, "slot": sequence % 127,
                            "offset": offset, "packet": base.retained(packet, 128)})
    base.require(len(matches) == 1, "selected requester wake missing or duplicated")
    return {**_scope(), "comparison": "one_new_requester_wake",
            "requester": requester, "before": first, "after": last,
            "checked_publication_begin": start, "checked_publication_end": end,
            "new_matching_wakes": 1, "match": matches[0],
            "complete_ring_equivalence_proved": False}
