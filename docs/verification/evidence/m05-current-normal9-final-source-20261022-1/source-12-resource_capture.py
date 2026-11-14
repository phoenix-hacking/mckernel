"""Decode only this case's bounded collector transport; no runtime credit."""
import json
import re


def decode(serial):
    def need(ok, reason):
        if not ok:
            raise ValueError(reason)

    def pairs(rows):
        value = {}
        for key, item in rows:
            need(key not in value, "duplicate JSON key")
            value[key] = item
        return value

    need(type(serial) is str and len(serial.encode("utf-8")) <= 4 * 1024 * 1024,
         "bounded serial text")
    rows = []
    payload_seen = 0
    for line in serial.splitlines(keepends=True):
        if line.startswith("ND_PAYLOAD "):
            payload_seen += 1
            need(payload_seen == 1 and bool(rows), "payload after resource capture")
        if line.startswith("ND_RESOURCE"):
            need(payload_seen == 0, "resource records precede payload")
            need(line.endswith("\n") and len(line) <= 4097,
                 "complete bounded transport record")
            wire = line[:-1]
            if wire.endswith("\r"):
                wire = wire[:-1]
            need("\r" not in wire and len(wire) <= 4095,
                 "only one terminal transport CR allowed")
            prefix, data = wire.split(" ", 1)
            value = json.loads(data, object_pairs_hook=pairs,
                              parse_constant=lambda _: need(False, "nonfinite"))
            need(type(value) is dict, "object record")
            rows.append((prefix, value))
    need(payload_seen == 1, "one subsequent independent payload frame")
    need(bool(rows) and rows[0][0] == "ND_RESOURCE", "resource header first")
    header = rows.pop(0)[1]
    fields = {"argv", "helper_result", "raw_wait_status", "fault", "timeout",
              "clean", "child_stage", "child_errno", "started_ns", "reaped_ns",
              "finished_ns"}
    need(set(header) == fields and header["argv"] == ["/bin/native-resource-release-probe"],
         "resource header fields")
    for key in fields - {"argv"}:
        need(type(header[key]) is int and 0 <= header[key] < 2**64,
             "integer header")
    for key in ("helper_result", "raw_wait_status", "fault", "timeout", "child_stage", "child_errno"):
        need(header[key] == 0, "helper failure")
    need(header["clean"] == 1 and
         0 < header["started_ns"] <= header["reaped_ns"] <= header["finished_ns"],
         "helper retirement/timestamps")
    streams = {}
    for name in ("stdout", "stderr"):
        need(bool(rows), "missing stream metadata")
        prefix, meta = rows.pop(0)
        need(prefix == "ND_RESOURCE_STREAM" and set(meta) ==
             {"name", "eof", "observed", "retained", "discarded", "limit", "eof_ns"},
             "stream metadata fields")
        need(meta["name"] == name and meta["eof"] is True, "stream identity/EOF")
        for key in ("observed", "retained", "discarded", "limit", "eof_ns"):
            need(type(meta[key]) is int and 0 <= meta[key] < 2**64,
                 "integer stream accounting")
        need(meta["limit"] == 4096 and meta["discarded"] == 0 and
             meta["observed"] == meta["retained"] <= 4096 and
             header["started_ns"] <= meta["eof_ns"] <= header["finished_ns"],
             "complete resource stream")
        body = bytearray()
        while len(body) < meta["retained"]:
            need(bool(rows), "missing chunk")
            prefix, chunk = rows.pop(0)
            need(prefix == "ND_RESOURCE_CHUNK" and set(chunk) == {"name", "offset", "hex"},
                 "chunk fields")
            need(chunk["name"] == name and type(chunk["offset"]) is int and
                 chunk["offset"] == len(body) and type(chunk["hex"]) is str and
                 re.fullmatch(r"(?:[0-9a-f]{2}){1,512}", chunk["hex"]) is not None,
                 "ordered bounded chunk")
            raw = bytes.fromhex(chunk["hex"])
            need(len(raw) == min(512, meta["retained"] - len(body)), "exact chunk size")
            body.extend(raw)
        streams[name] = bytes(body)
    need(not rows, "extra/duplicate resource record")
    return streams["stdout"], streams["stderr"], header["raw_wait_status"]
