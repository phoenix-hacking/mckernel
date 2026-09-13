#!/usr/bin/env python3
"""Strict version-1 typed owner/RET observations; never an acceptance oracle.

The schemas mirror the verification-only Rust appendices. This is deliberately
not a general Rust Debug parser. No evaluation, fallback coercion, field elision,
or acceptance from phase/result labels is permitted. See owner-observations.md.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_BYTES = 16 * 1024 * 1024
MAX_LINE = 2048
MAX_LINES = 65536
MAX_RECORDS = 4096
U64_MAX = (1 << 64) - 1
PHASES = ("BlockedRead", "AcceptedReturn", "Terminal", "TerminalPlusFive", "Recovery", "AfterEightHello")
CLASSES = ("fixed", "requests", "responses", "payloads", "snoops", "procfs", "zeroing")
MODES = ("hard-prepublication", "postpublication-notify", "recovery-before-deadline", "permanent-pressure")
COUNTERS = ("address_calls", "payload_calls", "payload_bytes", "release_calls", "released", "after_release_calls", "duplicate_release")


class ObservationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ObservationError(message)


def fields(description):
    return dict(item.split(":", 1) for item in description.split())


STRUCTS = {
    "Tag": fields("index:u64 serial:?u64 physical:u64 end:u64"),
    "Claim": fields("os:u32 generation:u64 response:Tag payload:?Tag"),
    "Delivery": fields("serial:u64 phase:delivery_phase phase_worker:?worker_pair pid:i32 cpu:i32 requester:i32 target:i32 number:u64 response:u64 arguments:arguments"),
    "Worker": fields("index:u64 handle:u64 tid:i32 delivery:?u64 completed:?u64"),
    "Mailbox": fields("call_slots:u64 worker_slots:u64 closed:bool quarantined:bool completion_cursor:u64"),
    "Rpc": fields("token:u64 os:i32 cpu:i32 pid:i32 message:i32 reply:i32 argument:u64 phase:rpc_phase result:?i32 waiter:bool unscheduled_deleted:bool retirement_query:bool"),
    "Process": fields("token:u64 pid:i32 cpu:i32 live:bool published:bool main_seen:bool tids:u64"),
    "App": fields("index:u64 token:u64 pid:i32 owner_slot:i32 prepare:?u64 schedule:?u64 retirement:?u64 retirement_after:u64 procfs:?Process scheduled:bool needs_cleanup:bool closed:bool quarantined:bool"),
    "Image": fields("exchange:Rpc result:?i32 thread:u64 page_table:u64 buffers_retained:bool descriptor:?u64 args:?u64 envs:?u64"),
    "Pager": fields("index:u64 token:u64 references:u64 readable_owner:u64 writable_owner:?u64"),
    "Selection": fields("os:u32 generation:u64 pid:i32 cpu:i32 requester:i32 application:u64 worker:u64 delivery:u64 ledger_serial:u64 ledger_index:u64 response:u64 response_end:u64"),
    "StabilityRetKey": fields("os:u32 generation:u64 pid:i32 tid:i32 worker:u64 delivery:u64"),
}
ENUMS = {
    "phase": PHASES,
    "class": CLASSES,
    "role": ("cleanup", "schedule", "retirement"),
    "result": ("COMPLETE_SNAPSHOT", "INCOMPLETE_FAIL", "COUNTER_FAIL"),
    "delivery_phase": tuple('"' + x + '"' for x in ("queued", "copying", "delivered", "returning", "servicing", "cancelling", "complete")),
    "rpc_phase": tuple('"' + x + '"' for x in ("reserved", "queued", "published", "complete")),
}
COMMON = fields("version:u32 sequence:u64")
SCHEMAS = {
    "BEGIN": fields("phase:phase selection:Selection sampling:=independent_domains"),
    "RUNTIME": fields("os:u32 generation:u64 runtime_owner:hex runtime_error:i32 metadata_pending:u64 procfs_pending:u64 zero_pending:u64 completed:u64 rejected:u64 zeroed:u64"),
    "DOMAIN/applications": fields("domain:=applications os:u32 generation:u64 transport_error:i32 slots:u64 total:u64 emitted:u64 complete:bool release_token:u64"),
    "APP": fields("ordinal:u64 row:App"),
    "DETAIL": fields("application:u64 present:bool complete:bool"),
    "RPC/cleanup": fields("application:u64 role:=cleanup row:Rpc"),
    "RPC/schedule": fields("application:u64 role:=schedule row:?Rpc"),
    "RPC/retirement": fields("application:u64 role:=retirement row:?Rpc"),
    "IMAGE": fields("application:u64 row:?Image"),
    "DOMAIN/mailbox": fields("domain:=mailbox application:?u64 release_token:u64 state:?Mailbox calls_total:u64 calls_emitted:u64 workers_total:u64 workers_emitted:u64 claims_known:bool complete:bool"),
    "DELIVERY": fields("application:?u64 ordinal:u64 row:Delivery"),
    "CALL": fields("application:?u64 ordinal:u64 slot:u64 owner:?Claim response:bool completion:bool completion_response:bool completion_wake:bool worker:?worker_pair cancelled:bool kernel:bool service:bool transferred:bool publication_since:?u64"),
    "WORKER": fields("application:?u64 ordinal:u64 row:Worker"),
    "DOMAIN/pagers": fields("domain:=pagers slots:u64 total:u64 emitted:u64 complete:bool linux_file_refcount:=not_observed"),
    "PAGER": fields("ordinal:u64 row:Pager"),
    "DOMAIN/ledger": fields("domain:=ledger class:class os:u32 generation:u64 last_serial:u64 slots:u64 total:u64 emitted:u64 complete:bool"),
    "TAG": fields("class:class ordinal:u64 row:Tag"),
    "COUNTERS": fields("selected_ledger_serial:?u64 address_calls:u64 payload_calls:u64 payload_bytes:u64 release_calls:u64 released:bool after_release_calls:u64 duplicate_release:u64 sampling:=independent_atomics"),
    "END": fields("complete:bool counters_valid:bool result:result"),
}
RET_SCHEMAS = {
    "SELECTED": fields("version:u32 key:StabilityRetKey valid:bool mono_ns:u64"),
    "ENTER": fields("version:u32 key:StabilityRetKey value:i64 cpu:i64 duplicate:bool mono_ns:u64"),
    "LEAVE": fields("version:u32 key:StabilityRetKey errno:i32 accepted:u64 duplicate:bool mono_ns:u64"),
}


class Literal:
    def __init__(self, text):
        self.text, self.pos = text, 0

    def take(self, literal):
        require(self.text.startswith(literal, self.pos), f"expected {literal!r} at column {self.pos}")
        self.pos += len(literal)

    def value(self, kind, depth=0):
        require(depth <= 12, "literal nesting limit")
        if kind.startswith("?"):
            if self.text.startswith("None", self.pos):
                self.take("None")
                return None
            self.take("Some(")
            result = self.value(kind[1:], depth + 1)
            self.take(")")
            return result
        if kind in STRUCTS:
            self.take(kind + " { ")
            result = {}
            for index, (name, field_type) in enumerate(STRUCTS[kind].items()):
                if index:
                    self.take(", ")
                self.take(name + ": ")
                result[name] = self.value(field_type, depth + 1)
            self.take(" }")
            return result
        if kind in ("arguments", "worker_pair"):
            self.take("[" if kind == "arguments" else "(")
            result = []
            for index, field_type in enumerate(["u64"] * 6 if kind == "arguments" else ["u64", "i32"]):
                if index:
                    self.take(", ")
                result.append(self.value(field_type, depth + 1))
            self.take("]" if kind == "arguments" else ")")
            return result
        if kind.startswith("="):
            self.take(kind[1:])
            return kind[1:]
        if kind == "bool" or kind in ENUMS:
            choices = ("true", "false") if kind == "bool" else ENUMS[kind]
            match = next((x for x in sorted(choices, key=len, reverse=True) if self.text.startswith(x, self.pos)), None)
            require(match is not None, f"invalid {kind} at column {self.pos}")
            self.take(match)
            return match == "true" if kind == "bool" else match.strip('"')
        pattern = r"(?:0|[1-9a-f][0-9a-f]{0,15})" if kind == "hex" else r"-?(?:0|[1-9][0-9]{0,19})"
        match = re.compile(pattern).match(self.text, self.pos)
        require(match is not None, f"invalid {kind} at column {self.pos}")
        token = match.group()
        require(token != "-0", "noncanonical negative zero")
        self.pos = match.end()
        value = int(token, 16 if kind == "hex" else 10)
        numeric(value, kind)
        return value

    def record(self, schema):
        result = {}
        for index, (name, kind) in enumerate(schema.items()):
            if index:
                self.take(" ")
            self.take(name + "=")
            result[name] = self.value(kind)
        require(self.pos == len(self.text), f"unexpected trailing data at column {self.pos}")
        return result


def numeric(value, kind="u64"):
    bits = 32 if kind in ("u32", "i32") else 64
    signed = kind.startswith("i")
    require(type(value) is int and (-(1 << (bits - 1)) if signed else 0) <= value < (1 << (bits - (1 if signed else 0))), f"invalid {kind} integer")
    return value


def exact_keys(value, keys, label):
    require(type(value) is dict and set(value) == set(keys), f"{label}: exact fields required")


def strictly_equal(actual, expected):
    """Walk only the bounded reparsed shape; bool is never an integer here."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is dict:
        return len(actual) == len(expected) and all(key in actual and strictly_equal(actual[key], value) for key, value in expected.items())
    if type(expected) is list:
        return len(actual) == len(expected) and all(strictly_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def parse_line(text):
    # Accept only raw printk, dmesg timestamps, or kernel priority+timestamp.
    prefix = re.match(r"^(?:<[0-9]{1,3}>)?(?:\[ *[0-9]{1,10}\.[0-9]{1,9}\] )?", text)
    text = text[prefix.end():]
    match = re.match(r"STABILITY_(OWNER|RET)_([A-Z]+) ", text)
    require(match is not None, "unknown marker or unsupported log prefix")
    family, name = match.groups()
    payload = text[match.end():]
    key = name
    if family == "OWNER" and name in ("DOMAIN", "RPC"):
        field = "domain" if name == "DOMAIN" else "role"
        subtype = re.search(r" " + field + r"=([a-z]+) ", payload)
        require(subtype is not None, "missing domain/role")
        key += "/" + subtype.group(1)
    schemas = SCHEMAS if family == "OWNER" else RET_SCHEMAS
    require(key in schemas, f"unknown {family} record {key}")
    schema = {**COMMON, **schemas[key]} if family == "OWNER" else schemas[key]
    data = Literal(payload).record(schema)
    require(data["version"] == 1, "unsupported or mixed observer version")
    return {"family": family, "kind": name, **data}


def rows(records, kind, count, cap, label):
    selected = [r for r in records if r["kind"] == kind]
    require(count <= cap and len(selected) == count, f"{label}: row count/cap")
    require([r["ordinal"] for r in selected] == list(range(count)), f"{label}: ordinal discrepancy")
    return selected


def one(records, kind, **keys):
    selected = [r for r in records if r["kind"] == kind and all(r.get(k) == v for k, v in keys.items())]
    require(len(selected) == 1, f"exactly one {kind} {keys} required")
    return selected[0]


def inventory(header, cap):
    require(header["complete"] and header["total"] == header["emitted"] <= cap and header["total"] <= header["slots"], "incomplete/overflow inventory")


def unique_indices(row_records, slots, label):
    indices = [r["row"]["index"] for r in row_records]
    require(indices == sorted(set(indices)) and all(x < slots for x in indices), f"{label}: duplicate/invalid/unordered slot")


def validate_snapshot(records):
    begin, end = records[0], records[-1]
    require(begin["kind"] == "BEGIN" and end["kind"] == "END", "snapshot boundaries missing")
    require(end["complete"] and end["counters_valid"] and end["result"] == "COMPLETE_SNAPSHOT", "incomplete snapshot or counter failure")
    require(len(records) <= 600, "snapshot record cap")
    selected = begin["selection"]
    require(all(selected[x] > 0 for x in ("generation", "pid", "application", "worker", "delivery", "ledger_serial", "response")), "invalid selected identity")
    require(selected["response_end"] - selected["response"] == 40, "selected response span is not 40 bytes")
    runtime = one(records, "RUNTIME")
    apps = one(records, "DOMAIN", domain="applications")
    pagers = one(records, "DOMAIN", domain="pagers")
    counters = one(records, "COUNTERS")
    for r in (runtime, apps):
        require((r["os"], r["generation"]) == (selected["os"], selected["generation"]), "OS generation drift")
    require(runtime["runtime_owner"] > 0, "missing Runtime owner")
    require(counters["selected_ledger_serial"] == selected["ledger_serial"], "selected counter serial drift")
    require(counters["after_release_calls"] == counters["duplicate_release"] == 0, "counter access/release failure")
    require(counters["release_calls"] <= 1 and counters["released"] == bool(counters["release_calls"]), "inconsistent release atomics")
    require(all(counters[x] < U64_MAX for x in COUNTERS if x != "released"), "counter overflow boundary")
    inventory(apps, 8)
    inventory(pagers, 16)
    app_rows = rows(records, "APP", apps["emitted"], 8, "applications")
    unique_indices(app_rows, apps["slots"], "applications")
    tokens = [r["row"]["token"] for r in app_rows]
    require(len(set(tokens)) == len(tokens) and all(tokens), "duplicate/missing application token")
    require(not any(r["kind"] == "DETAIL" for r in records), "missing application detail")
    require(len([r for r in records if r["kind"] == "RPC"]) == 3 * len(tokens), "extra/missing RPC details")
    require(len([r for r in records if r["kind"] == "IMAGE"]) == len(tokens), "extra/missing image details")
    for token in tokens:
        one(records, "IMAGE", application=token)
        for role in ("cleanup", "schedule", "retirement"):
            one(records, "RPC", application=token, role=role)
    mailboxes = [r for r in records if r["kind"] == "DOMAIN" and r["domain"] == "mailbox"]
    require(len(mailboxes) == len(tokens) + 1 and {r["application"] for r in mailboxes} == {*tokens, None}, "missing/duplicate/unknown mailbox domain")
    for mailbox in mailboxes:
        token = mailbox["application"]
        require(mailbox["release_token"] == apps["release_token"], "release mailbox token drift")
        require(mailbox["complete"] and mailbox["claims_known"] and mailbox["state"] is not None, "incomplete mailbox/owner metadata")
        state = mailbox["state"]
        members = [r for r in records if r["kind"] in ("DELIVERY", "CALL", "WORKER") and r["application"] == token]
        calls = rows(members, "CALL", mailbox["calls_emitted"], 8, "calls")
        deliveries = rows(members, "DELIVERY", mailbox["calls_emitted"], 8, "deliveries")
        workers = rows(members, "WORKER", mailbox["workers_emitted"], 16, "workers")
        require(mailbox["calls_total"] == len(calls) <= state["call_slots"] and mailbox["workers_total"] == len(workers) <= state["worker_slots"], "mailbox total/slot drift")
        slots = [r["slot"] for r in calls]
        require(slots == sorted(set(slots)) and all(x < state["call_slots"] for x in slots), "call slot discrepancy")
        unique_indices(workers, state["worker_slots"], "workers")
        require(len({r["row"]["serial"] for r in deliveries}) == len(deliveries), "duplicate delivery serial")
        require(len({r["row"]["handle"] for r in workers}) == len(workers), "duplicate worker identity")
        for call in calls:
            require(not (call["response"] and call["completion_response"]), "double response ownership")
            require(not (call["completion_response"] or call["completion_wake"]) or call["completion"], "completion child without parent")
            require(not (call["response"] or call["completion_response"]) or call["owner"] is not None, "missing native response claim")
            if call["owner"] is not None:
                claim = call["owner"]
                require((claim["os"], claim["generation"]) == (selected["os"], selected["generation"]), "claim OS generation drift")
                require(claim["response"]["serial"] is not None and claim["response"]["end"] - claim["response"]["physical"] == 40, "invalid native claim tag")
    require(all(r["application"] in {*tokens, None} for r in records if r["kind"] in ("CALL", "DELIVERY", "WORKER")), "orphan mailbox row")
    pager_rows = rows(records, "PAGER", pagers["emitted"], 16, "pagers")
    unique_indices(pager_rows, pagers["slots"], "pagers")
    ledger = [r for r in records if r["kind"] == "DOMAIN" and r["domain"] == "ledger"]
    require([r["class"] for r in ledger] == list(CLASSES), "missing/duplicate/reordered ledger classes")
    require(len([r for r in records if r["kind"] == "DOMAIN"]) == 9 + len(mailboxes), "extra domain")
    for header in ledger:
        require((header["os"], header["generation"]) == (selected["os"], selected["generation"]), "ledger OS generation drift")
        inventory(header, 16)
        tags = rows([r for r in records if r.get("class") == header["class"]], "TAG", header["emitted"], 16, "ledger tags")
        unique_indices(tags, header["slots"], "ledger tags")
        serials = []
        for tag in tags:
            row = tag["row"]
            require(row["physical"] < row["end"], "empty/reversed ledger span")
            if header["class"] == "fixed":
                require(row["serial"] is None, "fixed ledger has allocation serial")
            else:
                require(row["serial"] is not None and 0 < row["serial"] <= header["last_serial"], "invalid ledger serial")
                serials.append(row["serial"])
        require(len(set(serials)) == len(serials), "duplicate ledger serial")
        if header["class"] not in ("requests", "responses", "payloads"):
            require(header["slots"] == len(tags) and [t["row"]["index"] for t in tags] == list(range(len(tags))), "dense ledger discrepancy")
    # Preserve records separately: do not equate app/procfs/RPC/ledger values
    # sampled under different locks during traffic.
    return {"sequence": begin["sequence"], "phase": begin["phase"], "selection": selected, "records": records, "counters": {k: counters[k] for k in COUNTERS}}


def original_worker(snapshot):
    s = snapshot["selection"]
    require(snapshot["phase"] == "BlockedRead", "original BlockedRead observation required")
    records = snapshot["records"]
    candidates = [r for r in records if r["kind"] == "DELIVERY" and r["application"] == s["application"] and r["row"]["serial"] == s["delivery"]]
    require(len(candidates) == 1, "original selected delivery missing/ambiguous")
    delivery = candidates[0]
    d = delivery["row"]
    call = one(records, "CALL", application=s["application"], ordinal=delivery["ordinal"])
    mailbox = one(records, "DOMAIN", domain="mailbox", application=s["application"])
    require(not mailbox["state"]["closed"] and not mailbox["state"]["quarantined"], "selected mailbox already terminal")
    require(d["phase"] == "delivered" and d["number"] == 0 and d["arguments"][0] == 0 and d["arguments"][2] == 16, "selected operation is not delivered read16")
    require(all(d[k] == s[k] for k in ("pid", "cpu", "requester", "response")), "selected request identity drift")
    require(call["response"] and not any(call[k] for k in ("completion", "cancelled", "kernel", "service")), "selected original response ownership invalid")
    require(call["worker"] is not None and call["worker"][0] == s["worker"] and call["worker"][1] > 0, "selected original worker missing")
    require(d["phase_worker"] == call["worker"], "delivery/worker identity mismatch")
    workers = [r["row"] for r in records if r["kind"] == "WORKER" and r["application"] == s["application"] and r["row"]["handle"] == s["worker"]]
    require(len(workers) == 1 and workers[0]["tid"] == call["worker"][1] and workers[0]["delivery"] == s["delivery"], "selected WORKER inventory identity/delivery mismatch")
    # reserve() retains the worker's older completed serial when taking a new
    # delivery. It must not already designate this still-Delivered operation.
    require(workers[0]["completed"] != s["delivery"], "selected active delivery already completed")
    claim = call["owner"]
    require(claim is not None and claim["response"] == {"index": s["ledger_index"], "serial": s["ledger_serial"], "physical": s["response"], "end": s["response_end"]}, "selected original claim mismatch")
    return call["worker"][1]


def parse_observations(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "capture size/type limit")
    require(raw.endswith(b"\n"), "truncated final line")
    lines = raw.splitlines(keepends=True)
    require(len(lines) <= MAX_LINES, "capture line cap")
    snapshots, current, ret = [], None, []
    record_count = 0
    for number, line in enumerate(lines, 1):
        require(len(line) <= MAX_LINE, f"line {number}: overlong line")
        if b"STABILITY_OWNER" not in line and b"STABILITY_RET" not in line:
            continue
        try:
            require(line.endswith(b"\n") and b"\x00" not in line, "truncated/NUL marker")
            text = line[:-1].removesuffix(b"\r").decode("ascii")
            r = parse_line(text)
            r["line"] = number
            r["raw_sha256"] = hashlib.sha256(line).hexdigest()
            record_count += 1
            require(record_count <= MAX_RECORDS, "marker record cap")
            if r["family"] == "RET":
                require(len(ret) < 3 and r["kind"] == ("SELECTED", "ENTER", "LEAVE")[len(ret)], "missing/duplicate/reordered RET record")
                ret.append(r)
            else:
                if r["kind"] == "BEGIN":
                    require(current is None and len(snapshots) < len(PHASES), "duplicate/nested begin or snapshot cap")
                    require(r["sequence"] == len(snapshots) + 1, "sequence gap/reuse; complete fresh-module capture required")
                    current = []
                require(current is not None, "owner record without begin")
                require(not current or r["sequence"] == current[0]["sequence"], "interleaved/unknown sequence")
                current.append(r)
                if r["kind"] == "END":
                    snapshots.append(validate_snapshot(current))
                    current = None
        except (ObservationError, UnicodeDecodeError) as error:
            raise ObservationError(f"line {number}: {error}") from error
    require(current is None and snapshots and len(ret) == 3, "missing snapshot end/owner/RET evidence")
    require(len({s["phase"] for s in snapshots}) == len(snapshots), "duplicate phase")
    selected = snapshots[0]["selection"]
    tid = original_worker(snapshots[0])
    require(all(s["selection"] == selected for s in snapshots), "selection changed across snapshots")
    key = {k: selected[k] for k in ("os", "generation", "pid", "worker", "delivery")}
    key["tid"] = tid
    require(all(r["key"] == key for r in ret), "RET key differs from original native selection")
    require(ret[1]["cpu"] == selected["cpu"], "RET routed CPU differs from original request")
    require(ret[0]["valid"] and not ret[1]["duplicate"] and not ret[2]["duplicate"], "invalid/duplicate RET observation")
    require(0 < ret[0]["mono_ns"] <= ret[1]["mono_ns"] <= ret[2]["mono_ns"] < (1 << 63), "RET monotonic timestamp ordering/range")
    for before, after in zip(snapshots, snapshots[1:]):
        require(all(after["counters"][k] >= before["counters"][k] for k in COUNTERS), "selected counter decrease/overflow")
    return {"schema_version": 1, "record_kind": "typed_owner_ret_observations", "status": "COMPLETE_OBSERVATIONS_ONLY", "application_acceptance": False, "production_gate_credit": False,
            "sampling": "independent_domains_and_atomics", "raw": {"size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "base64": base64.b64encode(raw).decode("ascii")},
            "snapshots": snapshots, "ret": {"records": ret, "key": key, "value": ret[1]["value"], "cpu": ret[1]["cpu"], "errno": ret[2]["errno"], "accepted": ret[2]["accepted"], "enter_ns": ret[1]["mono_ns"], "leave_ns": ret[2]["mono_ns"], "elapsed_ns": ret[2]["mono_ns"] - ret[1]["mono_ns"]},
            "required_separate_evidence": ["physical_response_and_ring_bytes", "host_task_state", "uart_acknowledgements", "phase_barrier_and_timing_provenance", "actual_guest_module_image_and_hook_provenance", "launcher_wait_status", "same_os_followup_applications"]}


def inventory_projection(snapshot):
    # Keep *all* independently sampled domains and rows, including allocation
    # serials and Runtime counts; omit only log position/envelope/counters.
    return [{k: v for k, v in r.items() if k not in ("line", "raw_sha256", "sequence", "version", "family")}
            for r in snapshot["records"] if r["kind"] not in ("BEGIN", "END", "COUNTERS")]


def validate_run(observations, contract, timing):
    """Compare observations with explicit caller-frozen expectations, not provenance.

    Reparse retained bytes to prevent callers from modifying the parsed result.
    Timing is a separate input: this module validates its arithmetic/schema, but
    cannot certify that supplied intervals describe real barriers or events.
    """
    require(type(observations) is dict and type(observations.get("raw")) is dict, "missing retained capture")
    encoded = observations["raw"].get("base64")
    require(type(encoded) is str and 0 < len(encoded) <= 4 * ((MAX_BYTES + 2) // 3), "retained base64 type/encoded-size limit")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (KeyError, ValueError, TypeError) as error:
        raise ObservationError("invalid retained raw bytes") from error
    reparsed = parse_observations(raw)
    require(strictly_equal(observations, reparsed), "parsed observations changed from retained bytes")
    observations = reparsed
    exact_keys(contract, ("schema_version", "observer_version", "mode", "expected_counters", "ret"), "frozen contract")
    require(type(contract["schema_version"]) is int and contract["schema_version"] == 1 and type(contract["observer_version"]) is int and contract["observer_version"] == 1, "contract version")
    require(contract["mode"] in MODES, "unknown frozen mode")
    recovery = contract["mode"] == "recovery-before-deadline"
    phases = ["BlockedRead", "AcceptedReturn"] + (["Recovery", "AfterEightHello"] if recovery else ["Terminal", "TerminalPlusFive"])
    require([s["phase"] for s in observations["snapshots"]] == phases, "missing/extra/reordered mode phases")
    exact_keys(contract["expected_counters"], phases, "phase counter expectations")
    for index, snapshot in enumerate(observations["snapshots"]):
        counts = contract["expected_counters"][snapshot["phase"]]
        exact_keys(counts, COUNTERS, "counter expectations")
        for name in COUNTERS:
            if name == "released":
                require(type(counts[name]) is bool, "released expectation must be boolean")
            else:
                numeric(counts[name])
        final_release = index >= 2 and (recovery or contract["mode"] == "postpublication-notify")
        require(counts["address_calls"] == (0 if index == 0 else 2 if final_release else 1) and counts["release_calls"] == int(final_release) and counts["released"] == final_release, "frozen mode address/release expectations contradict source epoch")
        require(counts["after_release_calls"] == counts["duplicate_release"] == 0, "frozen counter failure expectation")
        require(snapshot["counters"] == counts, "observed serial counts differ from frozen expectations")
    require(observations["snapshots"][-1]["counters"] == observations["snapshots"][-2]["counters"], "old serial changed after terminal/recovery")
    ret_expected = contract["ret"]
    exact_keys(ret_expected, ("errno", "accepted", "value", "maximum_elapsed_ns"), "RET expectations")
    for field, kind in (("errno", "i32"), ("accepted", "u64"), ("value", "i64"), ("maximum_elapsed_ns", "u64")):
        numeric(ret_expected[field], kind)
    require(0 < ret_expected["maximum_elapsed_ns"] <= 15_000_000_000, "RET deadline must be positive and at most 15 seconds")
    require(all(observations["ret"][k] == ret_expected[k] for k in ("errno", "accepted", "value")), "raw RET result/value differs from frozen expectations")
    require(observations["ret"]["elapsed_ns"] <= ret_expected["maximum_elapsed_ns"], "RET deadline exceeded")
    exact_keys(timing, ("schema_version", "clock", "phases"), "phase timing evidence")
    require(type(timing["schema_version"]) is int and timing["schema_version"] == 1 and timing["clock"] == "host_kernel_monotonic", "phase timing version/clock")
    exact_keys(timing["phases"], phases, "phase timing intervals")
    previous_end = 0
    for phase in phases:
        interval = timing["phases"][phase]
        exact_keys(interval, ("begin_ns", "end_ns"), "phase interval")
        start, end = numeric(interval["begin_ns"]), numeric(interval["end_ns"])
        require(previous_end <= start <= end < (1 << 63), "phase timing order/range")
        previous_end = end
    require(timing["phases"]["BlockedRead"]["end_ns"] <= observations["ret"]["enter_ns"], "RET began before blocked observation ended")
    if not recovery:
        require(timing["phases"]["TerminalPlusFive"]["begin_ns"] - timing["phases"]["Terminal"]["end_ns"] >= 5_000_000_000, "terminal comparison is less than five seconds later")
        require(inventory_projection(observations["snapshots"][-2]) == inventory_projection(observations["snapshots"][-1]), "terminal inventories changed")
    return {"schema_version": 1, "record_kind": "owner_ret_contract_comparison", "status": "OBSERVATIONS_MATCH_FROZEN_CONTRACT", "application_acceptance": False, "production_gate_credit": False, "mode": contract["mode"], "observations": observations, "contract": contract, "phase_timing_evidence": timing, "timing_provenance_verified": False, "external_acceptance_evidence_complete": False}


def read_artifact(path, cap=MAX_BYTES):
    path = Path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_size <= cap, "artifact must be a bounded regular nonsymlink file")
        chunks, size = [], 0
        while True:
            data = os.read(fd, min(65536, cap + 1 - size))
            if not data:
                break
            chunks.append(data)
            size += len(data)
            require(size <= cap, "artifact grew beyond cap")
        after = os.fstat(fd)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), "artifact changed during read")
        raw = b"".join(chunks)
        return raw, {"path": str(path.absolute()), "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    finally:
        os.close(fd)


def load_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ObservationError("nonfinite JSON")))
    except (ValueError, RecursionError) as error:
        raise ObservationError(f"invalid JSON: {error}") from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--phase-timing", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = {"schema_version": 1, "status": "REJECTED_OBSERVATIONS", "application_acceptance": False, "production_gate_credit": False, "inputs": []}
    code = 0
    try:
        require(bool(args.contract) == bool(args.phase_timing), "contract and phase timing must be supplied together")
        raw, identity = read_artifact(args.log)
        result["inputs"].append(identity)
        result["raw"] = {**identity, "base64": base64.b64encode(raw).decode("ascii")}
        parsed = parse_observations(raw)
        if args.contract:
            inputs = []
            for path in (args.contract, args.phase_timing):
                data, identity = read_artifact(path, 65536)
                result["inputs"].append(identity)
                inputs.append(load_json(data))
            result["comparison"] = validate_run(parsed, *inputs)
            result["status"] = result["comparison"]["status"]
        else:
            result["observations"] = parsed
            result["status"] = parsed["status"]
    except (ObservationError, OSError) as error:
        result["error"] = str(error)
        code = 1
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
