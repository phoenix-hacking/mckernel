#!/usr/bin/env python3
"""Strict native phase/fault metadata. Physical/provenance acceptance stays external."""
import base64
import hashlib
import importlib.util
from pathlib import Path
import re

_PATH = Path(__file__).with_name("owner_observations.py")
_SPEC = importlib.util.spec_from_file_location("phase_owned_observations", _PATH)
owner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(owner)
ObservationError = owner.ObservationError
require = owner.require
MODES = {"prepublish-hard": 1, "postpublish-notify": 2,
         "recoverable-backpressure": 3, "permanent-backpressure": 4}
OWNER_MODES = {1: "hard-prepublication", 2: "postpublication-notify",
               3: "recovery-before-deadline", 4: "permanent-pressure"}
SCHEMAS = {
    "PHASE_SNAPSHOT_BEGIN": "version:u32 phase_sequence:u64 phase:phase nonce_low:hex16 nonce_high:hex16 mono_ns:u64 sampling:=independent_domains",
    "PHASE_SNAPSHOT_END": "version:u32 phase_sequence:u64 errno:i32 mono_ns:u64 barrier_calls:u64 verification_errno:i32",
    "PHASE_INVALID": "version:u32 phase:phase errno:i32 mono_ns:u64 publication_deadline_unchanged:bool",
    "FAULT_COUNTS": "version:u32 mode:u32 attempts:u64 barrier_attempts:u64 published:u64 notification_failures:u64 real_sends:u64 since_ns:u64 mono_ns:u64",
    "FAULT_SELECTED": "version:u32 mode:u32 selection:Selection buffer:hex bytes:u64 mono_ns:u64",
    "FAULT_REAL_SEND": "version:u32 mode:u32 attempt:u64 errno:i32 begin_ns:u64 end_ns:u64",
    "FAULT_PREPUBLICATION": "version:u32 errno:i32 attempts:u64 mono_ns:u64",
    "FAULT_PUBLISHED": "version:u32 mode:u32 attempts:u64 mono_ns:u64",
    "FAULT_RECOVERED": "version:u32 mode:u32 attempts:u64 mono_ns:u64",
    "FAULT_NOTIFICATION": "version:u32 errno:i32 published:u64 mono_ns:u64",
    "FAULT_INVALID": "version:u32 reason:=duplicate_selected_send",
}
FAULT_COUNTERS = ("attempts", "barrier_attempts", "published", "notification_failures", "real_sends", "since_ns")
EXTERNAL = ["actual_guest_kernel_module_image_and_hook_provenance", "host_task_and_uart_phase_acknowledgements",
            "physical_blocked_response_and_ring", "physical_prepublication_response_prefix",
            "publication_and_notification_ring_evidence", "launcher_raw_wait_and_deadlines",
            "same_os_eight_hello_provenance"]
PREFIX = re.compile(r"^(?:<[0-9]{1,3}>)?(?:\[ *[0-9]{1,10}\.[0-9]{1,9}\] )?")


def canonicalize_line(text):
    """Strip only the exact crate prefix bound to the marker's native producer."""
    require(type(text) is str and len(text) <= owner.MAX_LINE, "native line size/type")
    prefix = PREFIX.match(text)
    body = text[prefix.end():]
    match = re.match(r"(ihk_smp_x86_64|mcctrl): (STABILITY_(OWNER|RET|PHASE|FAULT)_[A-Z_]+ .*)$", body)
    require(match is not None, "missing/unknown native module prefix or marker")
    require(match[1] == ("mcctrl" if match[3] == "RET" else "ihk_smp_x86_64"), "marker came from wrong native module")
    return text[:prefix.end()] + match[2]


def canonicalize_capture(raw):
    require(type(raw) is bytes and 0 < len(raw) <= owner.MAX_BYTES and raw.endswith(b"\n"), "capture size/type/truncation")
    lines = raw.splitlines(keepends=True)
    require(len(lines) <= owner.MAX_LINES, "capture line cap")
    canonical, mapping = [], []
    for number, line in enumerate(lines, 1):
        require(len(line) <= owner.MAX_LINE, "overlong capture line")
        changed = line
        if any(marker in line for marker in (b"STABILITY_PHASE", b"STABILITY_FAULT", b"STABILITY_OWNER", b"STABILITY_RET")):
            require(line.endswith(b"\n") and b"\x00" not in line, "truncated/NUL native marker")
            try:
                text = line[:-1].removesuffix(b"\r").decode("ascii")
                changed = canonicalize_line(text).encode("ascii") + (b"\r\n" if line.endswith(b"\r\n") else b"\n")
            except UnicodeError as error:
                raise ObservationError(f"line {number}: non-ASCII native marker") from error
            mapping.append({"line": number, "original_sha256": hashlib.sha256(line).hexdigest(),
                            "canonical_sha256": hashlib.sha256(changed).hexdigest()})
        canonical.append(changed)
    return b"".join(canonical), mapping


class Literal(owner.Literal):
    def value(self, kind, depth=0):
        if kind == "hex16":
            match = re.compile(r"[0-9a-f]{16}").match(self.text, self.pos)
            require(match is not None, "nonce must contain exactly16 lowercase hex digits")
            self.pos = match.end()
            return int(match.group(), 16)
        return super().value(kind, depth)


def parse_line(text):
    return _parse_canonical_line(canonicalize_line(text))


def _parse_canonical_line(text):
    require(type(text) is str and len(text) <= owner.MAX_LINE, "phase line size/type")
    prefix = re.match(r"^(?:<[0-9]{1,3}>)?(?:\[ *[0-9]{1,10}\.[0-9]{1,9}\] )?", text)
    text = text[prefix.end():]
    match = re.match(r"STABILITY_((?:PHASE|FAULT)_[A-Z_]+) ", text)
    require(match is not None and match[1] in SCHEMAS, "unknown phase/fault marker or prefix")
    kind = match[1]
    result = Literal(text[match.end():]).record(owner.fields(SCHEMAS[kind]))
    require(result["version"] == 1, "unsupported phase/fault version")
    for key in ("mono_ns", "begin_ns", "end_ns"):
        if key in result:
            require(0 < result[key] < 1 << 63, "invalid native monotonic timestamp")
    return {"kind": kind, **result}


def _phases(mode):
    require(type(mode) is str and mode in MODES, "explicit frozen fault mode required")
    return ["BlockedRead", "AcceptedReturn"] + (["Recovery", "AfterEightHello"]
            if MODES[mode] == 3 else ["Terminal", "TerminalPlusFive"])


def _selected_call(snapshot):
    key = snapshot["selection"]
    deliveries = [row for row in snapshot["records"] if row["kind"] == "DELIVERY"
                  and row["application"] == key["application"] and row["row"]["serial"] == key["delivery"]]
    require(len(deliveries) == 1, "selected completion delivery missing/ambiguous")
    delivery = deliveries[0]
    request = delivery["row"]
    call = owner.one(snapshot["records"], "CALL", application=key["application"], ordinal=delivery["ordinal"])
    require(delivery["row"]["phase"] == "returning" and call["completion"]
            and call["completion_response"] and call["completion_wake"]
            and not any(call[k] for k in ("response", "cancelled", "kernel", "service")),
            "selected completion is not retained Returning response+wake")
    require(call["worker"] is not None and call["worker"][0] == key["worker"], "selected completion worker changed")
    require(request["phase_worker"] == call["worker"] and call["worker"][1] > 0
            and all(request[k] == key[k] for k in ("pid", "cpu", "requester", "response"))
            and request["number"] == 0 and request["arguments"][0] == 0 and request["arguments"][2] == 16,
            "selected completion request identity/operation changed")
    workers = [row["row"] for row in snapshot["records"] if row["kind"] == "WORKER"
               and row["application"] == key["application"] and row["row"]["handle"] == key["worker"]]
    require(len(workers) == 1 and workers[0]["tid"] == call["worker"][1]
            and workers[0]["delivery"] == key["delivery"] and workers[0]["completed"] != key["delivery"],
            "selected Returning WORKER inventory changed/completed")
    claim = call["owner"]
    require(claim is not None and (claim["os"], claim["generation"]) == (key["os"], key["generation"])
            and claim["response"] == {"index": key["ledger_index"], "serial": key["ledger_serial"],
                                      "physical": key["response"], "end": key["response_end"]},
            "selected completion claim changed")
    return call


def _health(snapshot, error):
    rows = snapshot["records"]
    require(owner.one(rows, "RUNTIME")["runtime_error"] == error
            and owner.one(rows, "DOMAIN", domain="applications")["transport_error"] == error,
            "mode runtime/application transport errno mismatch")
    if error:
        apps = [r["row"] for r in rows if r["kind"] == "APP"]
        require(any(r["token"] == snapshot["selection"]["application"] for r in apps), "terminal original application missing")
        require(all(r["quarantined"] and r["needs_cleanup"] for r in apps), "terminal application not quarantined")
        boxes = [r["state"] for r in rows if r["kind"] == "DOMAIN" and r["domain"] == "mailbox"]
        require(all(r["closed"] and r["quarantined"] for r in boxes), "terminal mailbox not quarantined")


def parse_envelopes(raw, *, mode, nonce_low, nonce_high):
    """Parse a complete contiguous phase prefix; RET completion is not required."""
    expected = _phases(mode)
    owner.numeric(nonce_low); owner.numeric(nonce_high)
    require(nonce_low | nonce_high, "zero capture nonce")
    canonical, mapping = canonicalize_capture(raw)
    lines = canonical.splitlines(keepends=True)
    require(len(lines) <= owner.MAX_LINES, "capture line cap")
    snapshots, events, ret, current = [], [], [], None
    marker_count = 0
    for number, line in enumerate(lines, 1):
        require(len(line) <= owner.MAX_LINE, "overlong capture line")
        if not any(marker in line for marker in (b"STABILITY_PHASE", b"STABILITY_FAULT", b"STABILITY_OWNER", b"STABILITY_RET")):
            continue
        marker_count += 1
        require(marker_count <= owner.MAX_RECORDS, "phase/owner marker cap")
        try:
            require(b"\x00" not in line, "NUL marker")
            text = line[:-1].removesuffix(b"\r").decode("ascii")
            if b"STABILITY_OWNER" in line or b"STABILITY_RET" in line:
                row = owner.parse_line(text)
                row.update(line=number, raw_sha256=hashlib.sha256(line).hexdigest())
                if row["family"] == "RET":
                    require(current is None and len(ret) < 3 and len(snapshots) == len(ret)
                            and row["kind"] == ("SELECTED", "ENTER", "LEAVE")[len(ret)],
                            "RET prefix missing/duplicate/reordered/outside native phase bracket")
                    ret.append(row)
                    continue
                require(current is not None and current["counts"] is None, "owner row outside its phase envelope")
                require(row["sequence"] == current["begin"]["phase_sequence"], "owner/phase sequence mismatch")
                records = current["owner_records"]
                require(not records or records[-1]["kind"] != "END", "owner row after completed snapshot")
                require((not records) == (row["kind"] == "BEGIN"), "missing/duplicate owner begin")
                current["owner_records"].append(row)
                continue
            row = _parse_canonical_line(text)
            row.update(line=number, raw_sha256=hashlib.sha256(line).hexdigest())
            kind = row["kind"]
            require(kind not in ("PHASE_INVALID", "FAULT_INVALID"), "native verification invalid marker")
            if "mode" in row:
                require(row["mode"] == MODES[mode], "mixed or unexpected frozen fault mode")
            if kind == "PHASE_SNAPSHOT_BEGIN":
                require(current is None and len(snapshots) < 4, "nested/extra phase begin")
                require(row["phase_sequence"] == len(snapshots) + 1 and row["phase"] == expected[len(snapshots)], "phase gap/reuse/order")
                require((row["nonce_low"], row["nonce_high"]) == (nonce_low, nonce_high), "phase nonce mismatch")
                require(not snapshots or snapshots[-1]["end"]["mono_ns"] <= row["mono_ns"], "phase time overlap/decrease")
                current = {"begin": row, "owner_records": [], "counts": None}
            elif kind == "FAULT_COUNTS":
                require(current is not None and current["counts"] is None, "missing/duplicate/outside fault counts")
                require(current["owner_records"] and current["owner_records"][-1]["kind"] == "END", "counts before complete owner snapshot")
                current["counts"] = row
            elif kind == "PHASE_SNAPSHOT_END":
                require(current is not None and current["counts"] is not None, "phase end without begin/counts")
                require(row["phase_sequence"] == current["begin"]["phase_sequence"] and row["errno"] == row["verification_errno"] == 0,
                        "phase end identity/error")
                snapshot = owner.validate_snapshot(current.pop("owner_records"))
                require(snapshot["phase"] == current["begin"]["phase"], "owner/phase name mismatch")
                require(current["begin"]["mono_ns"] <= current["counts"]["mono_ns"] <= row["mono_ns"], "phase count timestamp outside envelope")
                require(row["barrier_calls"] == current["counts"]["barrier_attempts"] < owner.U64_MAX, "barrier counter mismatch/overflow")
                current.update(end=row, owner=snapshot)
                snapshots.append(current); current = None
            else:
                require(current is None and len(snapshots) == len(ret) == 2,
                        "fault event outside AcceptedReturn-to-RET-leave interval")
                require(len(events) < 40, "fault event cap")
                events.append(row)
        except (ObservationError, UnicodeError) as error:
            raise ObservationError(f"line {number}: {error}") from error
    require(current is None and snapshots, "incomplete/missing phase envelope")
    selected = snapshots[0]["owner"]["selection"]
    original_tid = owner.original_worker(snapshots[0]["owner"])
    original_request = next(row["row"] for row in snapshots[0]["owner"]["records"]
                            if row["kind"] == "DELIVERY" and row["application"] == selected["application"]
                            and row["row"]["serial"] == selected["delivery"])
    require(len(ret) >= min(len(snapshots), 3), "missing native RET prefix")
    ret_key = {k: selected[k] for k in ("os", "generation", "pid", "worker", "delivery")}
    ret_key["tid"] = original_tid
    require(all(row["key"] == ret_key for row in ret), "RET prefix key differs from original worker")
    require(ret[0]["valid"] and 0 < ret[0]["mono_ns"] <= snapshots[0]["begin"]["mono_ns"],
            "invalid/late RET selection")
    for index, row in enumerate(ret[1:], 1):
        require(not row["duplicate"] and snapshots[index - 1]["end"]["mono_ns"] <= row["mono_ns"] < 1 << 63,
                "duplicate/early/out-of-range RET prefix timestamp")
        if index < len(snapshots):
            require(row["mono_ns"] <= snapshots[index]["begin"]["mono_ns"], "RET prefix timestamp after following phase")
        if index == 1:
            require(row["cpu"] == selected["cpu"] and row["value"] == 16, "RET prefix CPU/value mismatch")
        else:
            require((row["errno"], row["accepted"]) == (0 if MODES[mode] == 3 else -71, 1), "RET prefix mode outcome mismatch")
    for index, snapshot in enumerate(snapshots):
        require(snapshot["owner"]["selection"] == selected, "selection changed between phase envelopes")
        for row in snapshot["owner"]["records"]:
            if row["kind"] == "DELIVERY" and row["application"] == selected["application"] and row["row"]["serial"] == selected["delivery"]:
                require(all(row["row"][k] == original_request[k] for k in ("target", "number", "arguments")),
                        "immutable selected request target/number/arguments changed")
        counts = snapshot["counts"]
        require(all(counts[k] < owner.U64_MAX for k in FAULT_COUNTERS), "fault counter overflow")
        require(counts["published"] <= 1 and counts["notification_failures"] <= 1 and counts["real_sends"] <= 32, "fault counter cap")
        if index < 2:
            require(all(counts[k] == 0 for k in FAULT_COUNTERS if k != "barrier_attempts"), "fault attempt before accepted barrier release")
            _health(snapshot["owner"], 0)
        if index == 0:
            require(counts["barrier_attempts"] == 0, "blocked read already deferred publication")
        if index == 1:
            call = _selected_call(snapshot["owner"])
            require(call["worker"][1] == original_tid, "selected completion TID changed")
            require(call["publication_since"] is None or call["publication_since"] * 1_000_000_000 <= snapshot["begin"]["mono_ns"], "future production timer")
        if index:
            prior = snapshots[index - 1]["counts"]
            require(all(counts[k] >= prior[k] for k in FAULT_COUNTERS), "fault counter decrease")
            require(not prior["since_ns"] or counts["since_ns"] == prior["since_ns"], "first-attempt timer changed")
    return {"schema_version": 1, "record_kind": "native_phase_fault_prefix", "status": "COMPLETE_PHASE_PREFIX_ONLY",
            "application_acceptance": False, "production_gate_credit": False, "mode": mode,
            "nonce": {"low": nonce_low, "high": nonce_high}, "snapshots": snapshots, "events": events, "ret_prefix": ret,
            "canonicalization": {"policy": "exact_native_crate_prefix_only", "size": len(canonical),
                                 "sha256": hashlib.sha256(canonical).hexdigest(), "lines": mapping},
            "raw": {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "base64": base64.b64encode(raw).decode("ascii")}}


def validate_capture(raw, *, mode, nonce_low, nonce_high, owner_contract):
    """Join original bytes with caller-frozen owner payload counts and native phases."""
    parsed = parse_envelopes(raw, mode=mode, nonce_low=nonce_low, nonce_high=nonce_high)
    snapshots, events = parsed["snapshots"], parsed["events"]
    require(len(snapshots) == 4, "complete four-phase run required")
    mode_id = MODES[mode]
    canonical, _ = canonicalize_capture(raw)
    owned = owner.parse_observations(canonical)
    require(owner.strictly_equal([s["owner"] for s in snapshots], owned["snapshots"]), "owner parser/envelope disagreement")
    owner.exact_keys(owner_contract, ("schema_version", "observer_version", "mode", "expected_counters", "ret"), "owner contract")
    require(owner_contract["mode"] == OWNER_MODES[mode_id], "owner/fault contract mode mismatch")
    timing = {"schema_version": 1, "clock": "host_kernel_monotonic", "phases": {
        s["begin"]["phase"]: {"begin_ns": s["begin"]["mono_ns"], "end_ns": s["end"]["mono_ns"]} for s in snapshots}}
    comparison = owner.validate_run(owned, owner_contract, timing)
    ret = owned["ret"]
    require((ret["errno"], ret["accepted"], ret["value"]) == (0 if mode_id == 3 else -71, 1, 16), "frozen mode RET errno/accepted/value mismatch")
    require(ret["enter_ns"] <= snapshots[1]["begin"]["mono_ns"] <= snapshots[1]["end"]["mono_ns"] <= ret["leave_ns"]
            <= snapshots[2]["begin"]["mono_ns"], "RET bracket/accepted/final phase order")
    require(snapshots[0]["end"]["line"] < ret["records"][1]["line"] < snapshots[1]["begin"]["line"]
            and snapshots[1]["end"]["line"] < ret["records"][2]["line"] < snapshots[2]["begin"]["line"],
            "RET log position outside its native phase bracket")
    final = snapshots[2]["counts"]
    require(all(final[k] == snapshots[3]["counts"][k] for k in FAULT_COUNTERS), "post-RET/quiet fault counters changed")
    require(final["barrier_attempts"] == snapshots[1]["counts"]["barrier_attempts"], "barrier rearmed after accepted snapshot")
    selected = [r for r in events if r["kind"] == "FAULT_SELECTED"]
    require(len(selected) == 1, "missing/duplicate selected fault event")
    selected = selected[0]
    key = owned["snapshots"][0]["selection"]
    original_tid = owner.original_worker(owned["snapshots"][0])
    require(selected["selection"] == key and selected["bytes"] == 16, "fault selection changed")
    delivery = next(r["row"] for r in owned["snapshots"][0]["records"] if r["kind"] == "DELIVERY"
                    and r["application"] == key["application"] and r["row"]["serial"] == key["delivery"])
    require(selected["buffer"] == delivery["arguments"][1] and selected["buffer"] > 0, "selected payload address mismatch")
    require(final["since_ns"] == selected["mono_ns"] and snapshots[1]["end"]["mono_ns"] <= selected["mono_ns"] <= ret["leave_ns"], "first fault attempt timing mismatch")
    real = [r for r in events if r["kind"] == "FAULT_REAL_SEND"]
    require([r["attempt"] for r in real] == list(range(1, len(real) + 1)) and final["real_sends"] == len(real), "real-send count/ordinal mismatch")
    previous_end = selected["mono_ns"]
    for row in real:
        require(previous_end <= row["begin_ns"] <= row["end_ns"] <= ret["leave_ns"], "real-send interval order")
        previous_end = row["end_ns"]
    required = {1: ["FAULT_SELECTED", "FAULT_PREPUBLICATION"],
                2: ["FAULT_SELECTED"] + ["FAULT_REAL_SEND"] * len(real) + ["FAULT_PUBLISHED", "FAULT_NOTIFICATION"],
                3: ["FAULT_SELECTED"] + ["FAULT_REAL_SEND"] * len(real) + ["FAULT_RECOVERED"],
                4: ["FAULT_SELECTED"]}[mode_id]
    require([r["kind"] for r in events] == required, "missing/duplicate/reordered/mode-incompatible fault events")
    if mode_id in (1, 4):
        require(final["attempts"] >= 1 and final["published"] == final["notification_failures"] == final["real_sends"] == 0, "unpublished mode counters")
        if mode_id == 1:
            event = events[1]
            require(final["attempts"] == event["attempts"] == 1 and event["errno"] == -5 and event["mono_ns"] == selected["mono_ns"], "prepublication injection mismatch")
    else:
        require(real and final["published"] == 1 and final["notification_failures"] == int(mode_id == 2), "published mode counters")
        require(all(r["errno"] in (-11, -16) for r in real[:-1]) and real[-1]["errno"] == 0, "real callback outcomes lack unique final success")
        require(final["attempts"] == len(real) if mode_id == 2 else final["attempts"] > len(real), "frozen mode attempt accounting")
        publication = events[-2] if mode_id == 2 else events[-1]
        require(publication["attempts"] == final["attempts"] and real[-1]["end_ns"] <= publication["mono_ns"] <= ret["leave_ns"], "post-callback publication timing")
        if mode_id == 2:
            notify = events[-1]
            require(notify["errno"] == -5 and notify["published"] == 1 and publication["mono_ns"] <= notify["mono_ns"] <= ret["leave_ns"], "postpublication notification mismatch")
        else:
            require(real[0]["begin_ns"] - selected["mono_ns"] >= 2_000_000_000, "recovery hold shorter than frozen2seconds")
    timer = _selected_call(snapshots[1]["owner"])["publication_since"]
    for snapshot in snapshots[2:]:
        error = 0 if mode_id == 3 else (-110 if mode_id == 4 else -5)
        _health(snapshot["owner"], error)
        if mode_id == 3:
            require(owner.one(snapshot["owner"]["records"], "DOMAIN", domain="applications")["total"] == 0, "recovery still owns application entries")
        if mode_id in (1, 4):
            call = _selected_call(snapshot["owner"])
            require(call["worker"][1] == original_tid, "retained terminal completion TID changed")
            require(timer is None or timer == call["publication_since"], "production timer changed")
            if mode_id == 4:
                require(call["publication_since"] is not None, "permanent pressure lacks retained production timer")
                timer = call["publication_since"]
                require(snapshot["begin"]["mono_ns"] >= (timer + 5) * 1_000_000_000, "terminal pressure before production deadline")
    deadline_status = "NOT_REQUIRED_FOR_RECOVERY_IN_THIS_MODE"
    missing = list(EXTERNAL)
    if mode_id == 3:
        deadline_status = "MISSING_OBSERVED_PRODUCTION_TIMER" if timer is None else "OBSERVED_SUCCESS_BEFORE_PRODUCTION_DEADLINE"
        if timer is None:
            missing.append("observed_original_production_publication_timer")
        else:
            require(real[-1]["end_ns"] < (timer + 5) * 1_000_000_000, "recovery succeeded after production deadline")
    return {"schema_version": 1, "record_kind": "native_phase_fault_comparison",
            "status": "METADATA_MATCH_WITH_MISSING_TIMER" if mode_id == 3 and timer is None else "NATIVE_METADATA_MATCH_ONLY",
            "application_acceptance": False, "production_gate_credit": False, "external_acceptance_evidence_complete": False,
            "phase_observations": parsed, "owner_comparison": comparison, "publication_timer_seconds": timer,
            "recovery_deadline_evidence": deadline_status, "missing_external_gates": missing,
            "physical_accepted_return_capture_verified": False,
            "physical_capture_limit": "AcceptedReturn metadata is released before host QMP can guarantee a stopped physical snapshot, especially modes2/3. A separate prepublication-prefix gate remains open. Never reread an original response after published/released observations.",
            "physical_full_ring_verified": False, "sampling": "independent_domains_and_atomics"}
