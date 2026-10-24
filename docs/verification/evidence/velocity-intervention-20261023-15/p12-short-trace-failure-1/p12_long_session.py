# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# PRIVATE derived segment consumer: version2, 90s mixed work, 600s wall, >=1 pair.
# Original version1 consumer remains unchanged. This is protocol-only segment proof.
"""Bounded explicit P205 long-mode wire checker.

The existing host lifecycle observer must pass first. ``pair_check`` must be
that observer's unchanged _pair_body; this module adds repetition accounting,
never replaces stream/trace/CPU/ownership oracles or native adjudication.
"""
import json
import re

NS = 1_000_000_000
PROFILE = dict(version=2, work_ns=90 * NS, wall_ns=600 * NS,
               min_launches=2, round_cap=2048, trace_cap=256 * 1024 * 1024)
SERIAL_CAP = 512 * 1024 * 1024
LINE_CAP = 65536
LINE_COUNT_CAP = 4_194_304
ROUND_TRACE_CAP = 1024 * 1024
STARTUP_CAP = 4096
MARKERS = {"ND_PAIR_LONG_PROFILE", "ND_PAIR_LONG_PROGRESS", "ND_PAIR_LONG_COMPLETE",
           "ND_PAIR_LONG_TRACE_BEGIN", "ND_PAIR_LONG_TRACE_END",
           "ND_PAIR_ROUND_START", "ND_PAIR_ROUND_END", "ND_PAIR"}
APP = re.compile(r"application(?:_syscall=\w+| SCHEDULE| retirement|_process=(?:release|cleanup_requested)| cleanup ACK| procfs \w+) os=(\d+) generation=(\d+) pid=(\d+)(?: |$)")

class LongSessionError(ValueError):
    pass

def need(ok, message):
    if not ok:
        raise LongSessionError(message)

def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result

def record(raw):
    def constant(_):
        raise LongSessionError("nonfinite JSON")
    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=constant)
    except (ValueError, TypeError) as error:
        raise LongSessionError("invalid wire JSON") from error
    need(type(value) is dict, "wire object required")
    return value

def keys(value, names):
    need(type(value) is dict and set(value) == set(names), "wire keys")

def integer(value, minimum=0):
    return type(value) is int and value >= minimum

def check_long_session(manifest, observation, pair_check):
    """Validate captured text using the unchanged strict per-pair callback.

    Returns protocol-only metrics. No physical/native acceptance is inferred.
    All input captures and JSON records must already be bound to the new
    explicit profile by the existing runtime owner and stage manifest.
    """
    need(callable(pair_check), "unchanged per-pair checker required")
    need(type(manifest) is dict and manifest.get("pair_long_session") == PROFILE,
         "explicit long-mode manifest profile")
    need(all(type(manifest["pair_long_session"][key]) is int for key in PROFILE),
         "profile integer types")
    need(type(observation) is dict and type(observation.get("serial")) is str,
         "serial text required")
    serial = observation["serial"]
    need(serial.isascii() and "\0" not in serial and len(serial) <= SERIAL_CAP,
         "serial capture encoding/cap")
    # Count before splitlines allocates Python line objects. Even maximally
    # short malformed lines must remain within the outer12GiB envelope.
    need(serial.count("\n") <= LINE_COUNT_CAP, "serial line-count cap")
    rows = {key: [] for key in MARKERS}
    # Linux console ONLCR adds one CR before each LF. Keep raw capture hashes,
    # caps and observation bytes unchanged; decode only this local parser view.
    if "\r" in serial:
        need(serial.count("\r\n") == serial.count("\r") == serial.count("\n"),
             "uniform UART CRLF framing")
        serial = serial.replace("\r\n", "\n")
    lines = serial.splitlines(keepends=True)
    for index, line in enumerate(lines):
        need(line.endswith("\n") and len(line) < LINE_CAP, "partial/oversize wire line")
        name, _, raw = line.rstrip("\n").partition(" ")
        if name.startswith("ND_"):
            need(name in MARKERS, "unknown/short/failure wire marker")
            need(len(line) < (4096 if name == "ND_PAIR" else 1024), "wire frame cap")
            rows[name].append((index, record(raw)))
            limit = PROFILE["round_cap"] if name in ("ND_PAIR", "ND_PAIR_ROUND_START", "ND_PAIR_ROUND_END", "ND_PAIR_LONG_PROGRESS") else 1
            need(len(rows[name]) <= limit, "wire record cap")
    for key in ("ND_PAIR_LONG_PROFILE", "ND_PAIR_LONG_COMPLETE",
                "ND_PAIR_LONG_TRACE_BEGIN", "ND_PAIR_LONG_TRACE_END"):
        need(len(rows[key]) == 1, "missing/duplicate " + key)
    profile_at, profile = rows["ND_PAIR_LONG_PROFILE"][0]
    need(profile == PROFILE and all(type(profile[k]) is int for k in PROFILE), "wire profile")
    complete_at, complete = rows["ND_PAIR_LONG_COMPLETE"][0]
    keys(complete, ("rounds", "launches", "work_ns", "elapsed_ns", "trace_bytes",
                    "os", "generation", "procfs_empty"))
    need(all(integer(complete[k]) for k in complete if k != "procfs_empty") and
         complete["os"] == 0 and complete["generation"] == 1 and
         complete["procfs_empty"] is True, "completion identity/types")
    count = complete["rounds"]
    need(1 <= count <= PROFILE["round_cap"] and complete["launches"] == count * 2,
         "round/actual-launch count")
    starts, ends, reports, progress = (rows[key] for key in
        ("ND_PAIR_ROUND_START", "ND_PAIR_ROUND_END", "ND_PAIR", "ND_PAIR_LONG_PROGRESS"))
    need(len(starts) == len(ends) == len(reports) == len(progress) == count,
         "incomplete/duplicate round record set")
    trace_begin_at, trace_begin = rows["ND_PAIR_LONG_TRACE_BEGIN"][0]
    trace_end_at, trace_end = rows["ND_PAIR_LONG_TRACE_END"][0]
    keys(trace_begin, ("bytes",)); keys(trace_end, ("bytes",))
    need(profile_at < starts[0][0] and progress[-1][0] < trace_begin_at < trace_end_at < complete_at,
         "profile/trace/completion wire order")
    # Authenticate exact bytes without copying the full retained trace.
    trace_bytes = sum(len(lines[index]) for index in range(trace_begin_at + 1, trace_end_at))
    need(integer(trace_begin["bytes"], 1) and trace_begin == trace_end and
         trace_begin["bytes"] == trace_bytes == complete["trace_bytes"] <= PROFILE["trace_cap"],
         "trace exact bytes/cap")
    # Index each accepted application record exactly once; reject foreign and
    # malformed domains before projecting a strict one-pair view.
    pid_round = {}
    for round_id, (_, report) in enumerate(reports):
        apps = report.get("apps")
        need(type(apps) is list and len(apps) == 2, "two actual apps per round")
        for app in apps:
            need(type(app) is dict and integer(app.get("pid"), 1) and
                 app["pid"] not in pid_round, "duplicate/missing top-level PID")
            pid_round[app["pid"]] = round_id
    grouped = [[] for _ in range(count)]
    grouped_bytes = [0] * count
    startup = []
    startup_bytes = 0
    tokens = set()
    app_markers = ("application_syscall=", "application SCHEDULE ", "application retirement ",
                   "application_process=release ", "application_process=cleanup_requested ",
                   "application cleanup ACK ", "application procfs ")
    for index, line in enumerate(lines):
        if any(marker in line for marker in app_markers):
            need(trace_begin_at < index < trace_end_at, "application record outside retained trace")
            match = APP.search(line)
            need(match is not None and match.group(1, 2) == ("0", "1") and
                 int(match.group(3)) in pid_round, "foreign/malformed application trace")
            group = pid_round[int(match.group(3))]
            need(grouped_bytes[group] + len(line) <= ROUND_TRACE_CAP, "per-round trace cap")
            grouped_bytes[group] += len(line)
            grouped[group].append(line)
            if "application retirement " in line:
                token = re.search(r" token=(\d+) errno=-?\d+\s*$", line)
                need(token is not None and 0 < int(token.group(1)) < 2**64 and
                     int(token.group(1)) not in tokens, "missing/reused retirement token")
                tokens.add(int(token.group(1)))
        elif "control accepted " in line or "NATIVE_PAIR_CPU " in line:
            need(trace_begin_at < index < trace_end_at, "startup record outside retained trace")
            need(startup_bytes + len(line) <= STARTUP_CAP, "startup trace cap")
            startup_bytes += len(line)
            startup.append(line)
    total = 0
    previous_end = 0
    first_work = last_work = None
    for round_id, ((start_at, start), (end_at, end), (report_at, report), (progress_at, step)) in enumerate(zip(starts, ends, reports, progress)):
        for boundary in (start, end):
            keys(boundary, ("round", "time_ns", "procfs_empty"))
            need(integer(boundary["round"]) and boundary["round"] == round_id and
                 integer(boundary["time_ns"], 1) and boundary["procfs_empty"] is True,
                 "round handoff identity")
        need(start_at < report_at < end_at < progress_at < trace_begin_at and
             previous_end <= start["time_ns"] < end["time_ns"], "round time/order")
        if round_id:
            need(progress[round_id - 1][0] < start_at, "interleaved rounds")
        # Preserve the full original per-app byte/exit/CPU/trace/lifetime gates.
        view = "".join(startup + grouped[round_id]) + "ND_PAIR " + json.dumps(report) + "\n"
        checked = pair_check(manifest, dict(observation, serial=view))
        need(type(checked) is dict and checked.get("status") == "PROTOCOL_PASS",
             "existing strict pair checker did not pass")
        apps = report["apps"]
        need(all(all(integer(app.get(k), 1) for k in ("started_ns", "reaped_ns", "finished_ns"))
                 and start["time_ns"] <= app["started_ns"] <= app["reaped_ns"] <= app["finished_ns"] <= end["time_ns"]
                 and app["reaped_ns"] - app["started_ns"] <= 10 * NS for app in apps),
             "payload10s/handoff deadline")
        need(max(app["started_ns"] for app in apps) < min(app["reaped_ns"] for app in apps),
             "required actual mixed overlap")
        low = min(app["started_ns"] for app in apps)
        high = max(app["reaped_ns"] for app in apps)
        if first_work is None:
            first_work = low
        last_work = high
        work = high - low
        total += work
        need(end["time_ns"] - first_work < PROFILE["wall_ns"], "long wall deadline")
        keys(step, ("round", "work_ns", "cumulative_work_ns", "launches"))
        need(all(integer(step[k]) for k in step) and step == dict(round=round_id,
             work_ns=work, cumulative_work_ns=total, launches=(round_id + 1) * 2),
             "work union/progress accounting")
        if round_id + 1 < count:
            need(total < PROFILE["work_ns"] or (round_id + 1) * 2 < PROFILE["min_launches"],
                 "work continued after completion quota")
        previous_end = end["time_ns"]
    need(total >= PROFILE["work_ns"] and complete["work_ns"] == total and
         complete["elapsed_ns"] == last_work - first_work < PROFILE["wall_ns"],
         "actual-work duration/elapsed completion")
    return dict(status="PROTOCOL_PASS", application_acceptance=False,
                native_acceptance=False, successful_launches=count * 2,
                successful_rounds=count, actual_mixed_work_ns=total,
                elapsed_work_span_ns=last_work-first_work,
                trace_bytes=trace_bytes, physical_retirement_accepted=False)
