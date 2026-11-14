#!/usr/bin/env python3
"""Source-derived hard-fault byte comparisons; no physical read or acceptance."""
import base64
import hashlib
import struct


class PhysicalObservationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PhysicalObservationError(message)


def retained(raw, size):
    require(type(raw) is bytes and len(raw) == size, "physical capture type/size")
    return {"size": size, "sha256": hashlib.sha256(raw).hexdigest(),
            "base64": base64.b64encode(raw).decode("ascii")}


def queue(raw, port):
    """Fresh native x86_64 16KiB ring; reject counter wrap in this profile."""
    artifact = retained(raw, 16384)
    require(type(port) is int and port in (501, 503), "explicit native control port")
    header = struct.unpack_from("<IHHIIQQQQIIII", raw)
    require(header[:4] == (1, port, 128, 127) and header[8] == 16256, "native queue geometry")
    read, published, reserved = header[5:8]
    require(read <= published <= reserved < (1 << 64) - 1 and reserved - read <= 126,
            "queue counters corrupt/wrapped/saturated")
    return {"port": port, "read": read, "published": published, "reserved": reserved,
            "retained_sequence_begin": max(0, reserved - 127), "header": list(header), "raw": artifact}


def request_fields(request):
    names = ("cpu", "pid", "requester", "target", "number", "response", "arguments")
    require(type(request) is dict and set(request) == set(names), "original request schema")
    for name in names[:-1]:
        require(type(request[name]) is int, "original request integer type")
    require(0 <= request["cpu"] < 512 and 0 < request["pid"] < 1 << 31
            and 0 < request["requester"] < 1 << 31 and 0 <= request["target"] < 1 << 31,
            "original request owner bounds")
    require(0 < request["response"] < (1 << 64) - 40 and request["response"] % 8 == 0,
            "original response physical span")
    args = request["arguments"]
    require(type(args) is list and len(args) == 6
            and all(type(arg) is int and 0 <= arg < 1 << 64 for arg in args), "six native request arguments")
    require(request["number"] == 0 and args[0] == 0 and args[2] == 16 and 0 < args[1] <= (1 << 64) - 16,
            "original request must be read(0, buffer, 16)")


def decode_request(packet):
    require(type(packet) is bytes and len(packet) == 128, "request packet size/type")
    require(struct.unpack_from("<i", packet, 8)[0] == 4
            and struct.unpack_from("<Q", packet, 56)[0] == 1, "request message/publication marker")
    return {"cpu": struct.unpack_from("<i", packet, 24)[0],
            "pid": struct.unpack_from("<i", packet, 32)[0],
            "requester": struct.unpack_from("<i", packet, 48)[0],
            "target": struct.unpack_from("<i", packet, 52)[0],
            "number": struct.unpack_from("<Q", packet, 64)[0],
            "arguments": list(struct.unpack_from("<6Q", packet, 72)),
            "response": struct.unpack_from("<Q", packet, 120)[0]}


def locate_consumed_request(receive, request):
    """Select only provably retained consumed sequences, never arbitrary slots."""
    request_fields(request)
    observed = queue(receive, 503)
    matches = []
    for sequence in range(observed["retained_sequence_begin"], observed["read"]):
        offset = 64 + (sequence % 127) * 128
        packet = receive[offset:offset + 128]
        if struct.unpack_from("<i", packet, 8)[0] == 4 and struct.unpack_from("<Q", packet, 56)[0] == 1:
            if decode_request(packet) == request:
                matches.append({"sequence": sequence, "slot": sequence % 127, "offset": offset,
                                "packet": retained(packet, 128)})
    require(len(matches) == 1, "selected consumed request missing/overwritten/ambiguous")
    return {"queue": observed, "selected_request": {**request, "arguments": list(request["arguments"])}, "match": matches[0]}


def no_new_requester_wake(before, after, requester):
    require(type(requester) is int and 0 < requester < 1 << 31, "wake requester type/range")
    first, last = queue(before, 501), queue(after, 501)
    require(first["header"][:5] + first["header"][8:] == last["header"][:5] + last["header"][8:],
            "outbound queue metadata changed")
    require(all(last[key] >= first[key] for key in ("read", "published", "reserved")), "outbound counters decreased")
    start, end = first["published"], last["published"]
    require(last["retained_sequence_begin"] <= start, "new publication interval overwritten; absence unprovable")
    for sequence in range(start, end):
        offset = 64 + (sequence % 127) * 128
        message = struct.unpack_from("<i", after, offset + 8)[0]
        ttid = struct.unpack_from("<i", after, offset + 24)[0]
        require(not (message == 0x14 and ttid == requester), "selected requester wake was published")
    return {"before": first, "after": last, "checked_publication_begin": start,
            "checked_publication_end": end, "new_matching_wakes": 0}


def compare_hard_response(blocked, terminal, plus_five, *, worker_tid):
    require(type(worker_tid) is int and 0 < worker_tid < 1 << 31, "original Linux worker TID")
    artifacts = {name: retained(raw, 40) for name, raw in
                 (("BlockedRead", blocked), ("Terminal", terminal), ("TerminalPlusFive", plus_five))}
    require(struct.unpack_from("<QQ", blocked, 8) == (0, 2), "blocked status/wake must be0/2")
    expected = bytearray(blocked)
    struct.pack_into("<i", expected, 4, worker_tid)
    struct.pack_into("<Qq", expected, 16, 1, 16)
    require(terminal == bytes(expected), "terminal differs from source-derived prepared response prefix")
    require(plus_five == terminal, "terminal response changed during quiet interval")
    return {"status": "HARD_RESPONSE_BYTES_MATCH_ONLY", "application_acceptance": False,
            "production_gate_credit": False, "raw": artifacts,
            "expected_prepublication_prefix": retained(bytes(expected), 40),
            "allowed_write_spans": [[4, 8], [16, 24], [24, 32]],
            "first_word_policy": "Preserve original bytes. ABI comment alone does not initialize response.ttid.",
            "accepted_return_physically_observed": False,
            "required_external_evidence": ["exact_source_image_module_and_selection_binding",
                "retained_response_owner_and_zero_release_at_each_physical_read",
                "stopped_capture_and_verified_resume", "native_phase_and_five_second_timing",
                "original_request_ring_binding", "absence_of_selected_wake_publication",
                "launcher_and_controller_provenance"]}
