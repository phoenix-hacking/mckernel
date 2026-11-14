#!/usr/bin/env python3
"""Pure, fail-closed native shutdown phase evidence checker.

This program does not query a host, load a module, or run a guest.  A later
reviewed Rocky harness may collect snapshots and pass their bounded JSON here.
``PROTOCOL_PASS`` is diagnostic evidence only, never execution acceptance.
"""
import argparse
import hashlib
import json
import os
import re
import stat
import sys

MAX_JSON = 4 * 1024 * 1024
MAX_TEXT = 4096
PHASES = (
    "clean_baseline", "booted", "workload_live", "workload_retired_pre_stop",
    "destroyed_resources_released_provider_present", "fully_unloaded", "policy_restored",
)
# CPUs may be taken offline while the provider owns them, but every release
# boundary must prove restoration to the clean inventory.
CPU_RESTORED_PHASES = ("clean_baseline", "destroyed_resources_released_provider_present",
                       "fully_unloaded", "policy_restored")
CPU_TRANSIENT_PHASES = ("booted", "workload_live", "workload_retired_pre_stop")
LIMITATIONS = frozenset(("internal_mapping_ledger_unobserved",
                         "internal_callback_ledger_unobserved",
                         "recreate_not_exercised"))
RESERVE_STATUSES = frozenset(("available", "unavailable"))
UNAVAILABLE_REASONS = frozenset(("provider_absent", "query_unavailable"))


class ShutdownObservationError(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise ShutdownObservationError(message)


def _keys(value, required):
    _need(type(value) is dict and set(value) == set(required), "snapshot keys differ")


def _text(value, label):
    _need(type(value) is str and len(value) <= MAX_TEXT and "\x00" not in value, label)
    return value


def _pairs(rows):
    result = {}
    for key, value in rows:
        _need(type(key) is str and key not in result, "duplicate JSON key")
        result[key] = value
    return result


def _identity(row):
    _keys(row, ("pid", "starttime_ticks"))
    _need(all(type(row[key]) is int and row[key] > 0 for key in row), "invalid process identity")
    return (row["pid"], row["starttime_ticks"])


def _bounded_map(value, label):
    _need(type(value) is dict and len(value) <= 4096, label)
    result = {}
    for key, item in value.items():
        _text(key, label)
        _text(item, label)
        result[key] = item
    return result


def _map_digest(value):
    """Stable digest of bounded observed procfs content."""
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _procfs(value):
    _keys(value, ("state", "numeric_nodes", "status", "maps", "errors"))
    _need(value["state"] in ("absent", "present"), "procfs state")
    _need(type(value["errors"]) is list and not value["errors"], "procfs read/query error")
    _need(type(value["numeric_nodes"]) is list and len(value["numeric_nodes"]) <= 4096,
          "procfs numeric nodes")
    nodes = []
    for item in value["numeric_nodes"]:
        _need(type(item) is int and item >= 0, "procfs nonnumeric node")
        nodes.append(item)
    _need(nodes == sorted(set(nodes)), "procfs duplicate/unordered nodes")
    status, maps = _bounded_map(value["status"], "procfs status"), _bounded_map(value["maps"], "procfs maps")
    if value["state"] == "absent":
        _need(not nodes and not status and not maps, "absent procfs has residual nodes")
    return {"state": value["state"], "numeric_nodes": nodes, "status": status, "maps": maps}


def _devices(value):
    _need(type(value) is list and len(value) <= 1024, "device inventory")
    result = {}
    for row in value:
        _keys(row, ("path", "role", "type", "major", "minor", "owner", "mode", "sysfs"))
        path = _text(row["path"], "device path")
        _need(path.startswith("/dev/") and path not in result, "device path")
        if re.fullmatch(r"/dev/mcd[0-9]+", path):
            role = "provider"
        elif re.fullmatch(r"/dev/mcos[0-9]+", path):
            role = "os"
        else:
            raise ShutdownObservationError("unclassified device node")
        _need(row["role"] == role, "device role/path mismatch")
        _need(row["type"] in ("char", "block"), "device type")
        _need(type(row["major"]) is int and row["major"] >= 0 and type(row["minor"]) is int and row["minor"] >= 0,
              "device major/minor")
        _need(type(row["owner"]) is dict and set(row["owner"]) == {"uid", "gid"} and
              all(type(row["owner"][key]) is int and row["owner"][key] >= 0 for key in ("uid", "gid")),
              "device owner")
        _need(type(row["mode"]) is int and 0 <= row["mode"] <= 0o7777, "device mode")
        sysfs = _bounded_map(row["sysfs"], "device sysfs")
        _need(sysfs.get("dev") == "%d:%d" % (row["major"], row["minor"]), "device/sysfs major/minor mismatch")
        _need(sysfs.get("type") == row["type"], "device/sysfs type mismatch")
        result[path] = {"role": role, "type": row["type"], "major": row["major"], "minor": row["minor"],
                        "owner": dict(row["owner"]), "mode": row["mode"], "sysfs": sysfs}
    return result


def _modules(value):
    _need(type(value) is dict and len(value) <= 1024, "module inventory")
    result = {}
    for name, row in value.items():
        _text(name, "module name")
        _keys(row, ("refcount", "holders"))
        _need(type(row["refcount"]) is int and row["refcount"] >= 0, "module refcount")
        _need(type(row["holders"]) is list and row["holders"] == sorted(set(row["holders"])) and
              all(type(holder) is str and holder for holder in row["holders"]), "module holders")
        result[name] = {"refcount": row["refcount"], "holders": list(row["holders"])}
    return result


def _reserves(value):
    _keys(value, ("cpu", "numa_memory"))
    result = {}
    for group in ("cpu", "numa_memory"):
        item = value[group]
        _need(type(item) is dict and set(item) == {"status", "queries", "reason"}, "reserve query shape")
        _need(item["status"] in RESERVE_STATUSES, "reserve query status")
        if item["status"] == "available":
            _need(type(item["queries"]) is dict and item["queries"], "reserve query absent")
            _need(item["reason"] is None, "available reserve has reason")
            output = {}
            for key, row in item["queries"].items():
                _text(key, "reserve query name")
                _keys(row, ("values",))
                _need(type(row["values"]) is list and
                      all(type(entry) is int and entry >= 0 for entry in row["values"]), "reserve query failed")
                output[key] = {"values": list(row["values"])}
            result[group] = {"status": "available", "queries": output, "reason": None}
        else:
            _need(item["queries"] == {}, "unavailable reserve has queries")
            _need(item["reason"] in UNAVAILABLE_REASONS, "bad unavailable reserve reason")
            result[group] = {"status": "unavailable", "queries": {}, "reason": item["reason"]}
    return result


def _irqs(value):
    _keys(value, ("inventory", "added", "removed"))
    _need(type(value["inventory"]) is dict and type(value["added"]) is list and type(value["removed"]) is list,
          "IRQ observation")
    inventory = {}
    for irq, row in value["inventory"].items():
        _need(type(irq) is str and irq.isdigit() and type(row) is dict and set(row) == {"affinity"}, "IRQ inventory")
        inventory[int(irq)] = _text(row["affinity"], "IRQ affinity")
    _need(len(inventory) <= 65536 and len(inventory) == len(value["inventory"]), "IRQ duplicate inventory")
    for name in ("added", "removed"):
        _need(all(type(item) is int and item >= 0 for item in value[name]) and
              value[name] == sorted(set(value[name])), "IRQ reconciliation")
    _need(not set(value["added"]) & set(value["removed"]), "IRQ add/remove overlap")
    return {"inventory": inventory, "added": list(value["added"]), "removed": list(value["removed"])}


def _policy(value):
    _keys(value, ("selinux", "swappiness", "irqbalance"))
    _keys(value["selinux"], ("enforcing", "config"))
    _need(type(value["selinux"]["enforcing"]) is bool, "SELinux state")
    _text(value["selinux"]["config"], "SELinux config")
    _need(type(value["swappiness"]) is int and 0 <= value["swappiness"] <= 100, "swappiness")
    _keys(value["irqbalance"], ("state", "config"))
    _need(value["irqbalance"]["state"] in ("active", "inactive", "masked", "absent"), "irqbalance state")
    _text(value["irqbalance"]["config"], "irqbalance config")
    return {"selinux": dict(value["selinux"]), "swappiness": value["swappiness"],
            "irqbalance": dict(value["irqbalance"])}


def _snapshot(value):
    _keys(value, ("phase", "processes", "procfs", "devices", "modules", "reserves", "cpu_online", "irqs",
                  "policy", "limitations"))
    _need(value["phase"] in PHASES, "unknown phase")
    _need(type(value["processes"]) is list, "process list")
    observed = [_identity(row) for row in value["processes"]]
    _need(observed == sorted(set(observed)), "duplicate/unordered process identity")
    devices, modules = _devices(value["devices"]), _modules(value["modules"])
    _need(type(value["cpu_online"]) is list and value["cpu_online"] == sorted(set(value["cpu_online"])) and
          all(type(cpu) is int and cpu >= 0 for cpu in value["cpu_online"]), "CPU online inventory")
    _need(type(value["limitations"]) is list and set(value["limitations"]) <= LIMITATIONS and
          len(value["limitations"]) == len(set(value["limitations"])), "unknown diagnostic limitation")
    return {"phase": value["phase"], "processes": observed, "procfs": _procfs(value["procfs"]),
            "devices": devices, "modules": modules, "reserves": _reserves(value["reserves"]),
            "cpu_online": list(value["cpu_online"]), "irqs": _irqs(value["irqs"]),
            "policy": _policy(value["policy"]), "limitations": list(value["limitations"])}


def _expectations(value):
    _keys(value, ("processes", "procfs", "devices", "modules", "cpu_online", "irqs", "policy"))
    expected = {"processes": {}, "procfs": {}, "devices": {}, "modules": {}}
    for group in ("processes", "procfs", "devices", "modules"):
        _need(type(value[group]) is dict and set(value[group]) == set(PHASES), "immutable phase expectations")
    for name in PHASES:
        rows = value["processes"][name]
        _need(type(rows) is list, "expected process list")
        identities = [_identity(row) for row in rows]
        _need(identities == sorted(set(identities)), "expected process identity")
        expected["processes"][name] = identities
        proc = value["procfs"][name]
        _keys(proc, ("state", "numeric_nodes", "status_sha256", "maps_sha256"))
        _need(proc["state"] in ("absent", "present") and type(proc["numeric_nodes"]) is list and
              proc["numeric_nodes"] == sorted(set(proc["numeric_nodes"])) and
              all(type(node) is int and node >= 0 for node in proc["numeric_nodes"]), "expected procfs")
        for digest in ("status_sha256", "maps_sha256"):
            _need(type(proc[digest]) is str and len(proc[digest]) == 64 and
                  all(char in "0123456789abcdef" for char in proc[digest]), "expected procfs digest")
        expected["procfs"][name] = dict(proc)
        expected["devices"][name] = _devices(value["devices"][name])
        expected["modules"][name] = _modules(value["modules"][name])
    _need(type(value["cpu_online"]) is dict and set(value["cpu_online"]) == set(PHASES),
          "expected phase CPU online inventories")
    expected["cpu_online"] = {}
    for phase in PHASES:
        cpus = value["cpu_online"][phase]
        _need(type(cpus) is list and cpus == sorted(set(cpus)) and
              all(type(cpu) is int and cpu >= 0 for cpu in cpus), "expected CPU online")
        expected["cpu_online"][phase] = list(cpus)
    baseline_cpus = expected["cpu_online"]["clean_baseline"]
    for phase in CPU_RESTORED_PHASES:
        _need(expected["cpu_online"][phase] == baseline_cpus,
              "expected CPU online restoration baseline")
    for phase in CPU_TRANSIENT_PHASES:
        _need(set(expected["cpu_online"][phase]) <= set(baseline_cpus),
              "expected CPU online transient inventory")
    expected["irqs"] = _irqs({"inventory": value["irqs"], "added": [], "removed": []})["inventory"]
    expected["policy"] = _policy(value["policy"])
    return expected


def _cpu_expectations(value):
    _keys(value, ("baseline", "offline", "phases"))
    def cpus(item, label):
        _need(type(item) is list and item == sorted(set(item)) and
              all(type(cpu) is int and cpu >= 0 for cpu in item), label)
        return list(item)
    baseline, offline = cpus(value["baseline"], "trusted CPU baseline"), cpus(value["offline"], "trusted CPU offline set")
    _need(set(offline) <= set(baseline), "trusted CPU offline set outside baseline")
    _need(type(value["phases"]) is dict and set(value["phases"]) == set(PHASES), "trusted phase CPU inventories")
    phases = {phase: cpus(value["phases"][phase], "trusted CPU phase inventory") for phase in PHASES}
    for phase in CPU_RESTORED_PHASES:
        _need(phases[phase] == baseline, "trusted CPU restoration baseline")
    for phase in CPU_TRANSIENT_PHASES:
        _need(phases[phase] == sorted(set(baseline) - set(offline)), "trusted CPU transient inventory is not authorized")
    return {"baseline": baseline, "offline": offline, "phases": phases}


def validate(document, trusted_cpu_expectations):
    """Validate seven snapshots and return bounded diagnostic-only evidence."""
    _keys(document, ("schema", "expectations", "phases"))
    _need(document["schema"] == "native-shutdown-observer-v3" and type(document["phases"]) is list,
          "shutdown observer schema")
    trusted = _cpu_expectations(trusted_cpu_expectations)
    expected, snapshots = _expectations(document["expectations"]), [_snapshot(row) for row in document["phases"]]
    _need(expected["cpu_online"] == trusted["phases"], "in-document CPU expectations differ from trusted input")
    _need([row["phase"] for row in snapshots] == list(PHASES), "missing/duplicate/out-of-order phase")
    baseline = snapshots[0]
    _need(baseline["procfs"]["state"] == "absent" and not baseline["processes"] and
          not baseline["devices"] and not baseline["modules"], "unclean baseline")
    _need(all(group["status"] == "unavailable" for group in baseline["reserves"].values()),
          "baseline reserve provider unexpectedly available")
    _need(snapshots[1]["procfs"]["state"] == "present", "booted procfs absent")
    _need(snapshots[2]["procfs"]["state"] == "present" and snapshots[2]["processes"], "workload not live")
    _need(snapshots[3]["procfs"]["state"] == "present" and not snapshots[3]["processes"], "workload not retired")
    for index in (1, 2, 3):
        roles = {row["role"] for row in snapshots[index]["devices"].values()}
        _need("provider" in roles and "os" in roles, "live provider/OS device missing")
    release = snapshots[4]
    _need(release["procfs"]["state"] == "absent" and
          all(row["role"] == "provider" for row in release["devices"].values()) and release["devices"],
          "provider resources not released")
    _need(release["modules"], "provider missing before unload")
    _need(all(group["status"] == "available" and group["queries"] and
              all(not query["values"] for query in group["queries"].values())
              for group in release["reserves"].values()), "reserve release queries unavailable or residual")
    for index in (1, 2, 3, 4):
        _need(all(group["status"] == "available" for group in snapshots[index]["reserves"].values()),
              "provider reserve query unavailable")
    unloaded = snapshots[5]
    _need(unloaded["procfs"]["state"] == "absent" and not unloaded["devices"] and not unloaded["modules"],
          "fully unloaded state has residual provider")
    for index in (5, 6):
        _need(not snapshots[index]["devices"] and not snapshots[index]["modules"],
              "provider remains after unload")
        _need(all(group["status"] == "unavailable" and
                  group["reason"] == "provider_absent" and not group["queries"]
                  for group in snapshots[index]["reserves"].values()),
              "provider-absent reserve query not explicitly unavailable")
    for row in snapshots:
        phase = row["phase"]
        _need(row["processes"] == expected["processes"][phase], "process identity/starttime mismatch")
        proc = expected["procfs"][phase]
        _need(row["procfs"]["state"] == proc["state"] and row["procfs"]["numeric_nodes"] == proc["numeric_nodes"] and
              _map_digest(row["procfs"]["status"]) == proc["status_sha256"] and
              _map_digest(row["procfs"]["maps"]) == proc["maps_sha256"], "procfs content/digest mismatch")
        _need(row["devices"] == expected["devices"][phase], "device/sysfs transition mismatch")
        _need(row["modules"] == expected["modules"][phase], "module refcount/holders transition mismatch")
        _need(row["cpu_online"] == trusted["phases"][phase], "CPU online phase expectation mismatch")
        _need(row["irqs"]["added"] == sorted(set(row["irqs"]["inventory"]) - set(expected["irqs"])),
              "IRQ added reconciliation")
        _need(row["irqs"]["removed"] == sorted(set(expected["irqs"]) - set(row["irqs"]["inventory"])),
              "IRQ removed reconciliation")
    baseline_cpus = trusted["baseline"]
    for index in (0, 4, 5, 6):
        _need(snapshots[index]["cpu_online"] == baseline_cpus,
              "CPU online restoration drift")
    for index in (1, 2, 3):
        _need(set(snapshots[index]["cpu_online"]) <= set(baseline_cpus),
              "CPU online transient inventory drift")
    for index in (0, 5, 6):
        _need(snapshots[index]["irqs"]["inventory"] == expected["irqs"], "IRQ affinity restoration drift")
    _need(snapshots[-1]["policy"] == expected["policy"], "policy restoration drift")
    for index in (1, 2):
        _need(snapshots[index]["devices"] and snapshots[index]["modules"], "boot/workload provider missing")
        _need(all(row["refcount"] >= len(row["holders"]) and row["holders"]
                  for row in snapshots[index]["modules"].values()), "unattributable live module ref")
    _need(not snapshots[3]["processes"], "workload nodes not retired before stop")
    _need(all(row["refcount"] >= len(row["holders"]) for row in release["modules"].values()),
          "invalid provider dependency refs")
    return {"status": "PROTOCOL_PASS", "application_acceptance": False,
            "limitations": sorted(set(item for row in snapshots for item in row["limitations"])),
            "phases": list(PHASES)}


def _read(path):
    with open(path, "rb") as stream:
        raw = stream.read(MAX_JSON + 1)
    _need(len(raw) <= MAX_JSON, "oversize shutdown evidence")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)


def _read_trusted(path, digest):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        _need(stat.S_ISREG(os.fstat(fd).st_mode), "CPU expectations must be a regular file")
        raw = os.read(fd, MAX_JSON + 1)
    finally:
        os.close(fd)
    _need(len(raw) <= MAX_JSON, "oversize CPU expectations")
    _need(hashlib.sha256(raw).hexdigest() == digest, "CPU expectations hash mismatch")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)


def main(argv=None):
    parser = argparse.ArgumentParser(description="validate native shutdown snapshots", allow_abbrev=False)
    parser.add_argument("input")
    parser.add_argument("--cpu-expectations", required=True)
    parser.add_argument("--cpu-expectations-sha256", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        _need(re.fullmatch(r"[0-9a-f]{64}", args.cpu_expectations_sha256) is not None,
              "CPU expectations hash format")
        result = validate(_read(args.input), _read_trusted(args.cpu_expectations,
                                                            args.cpu_expectations_sha256))
        raw = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if args.output:
            fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.write(fd, raw)
                os.fsync(fd)
            finally:
                os.close(fd)
        else:
            sys.stdout.buffer.write(raw)
        return 0
    except BaseException as exc:
        sys.stderr.write("native shutdown observer: %s\n" % str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
