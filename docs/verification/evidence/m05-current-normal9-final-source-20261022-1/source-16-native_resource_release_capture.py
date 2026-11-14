"""Strict public-release protocol decoder; grants no native restoration credit."""
import json


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def _constant(_):
    raise ValueError("nonfinite JSON number")


def evaluate(stdout, stderr, returncode):
    if (type(stdout) is not bytes or type(stderr) is not bytes or
            type(returncode) is not int or returncode != 0 or stderr or
            not stdout or len(stdout) > 262144):
        raise ValueError("failed/bounded capture")
    text = stdout.decode("ascii")
    if not text.endswith("\n") or "\r" in text:
        raise ValueError("incomplete/non-LF framing")
    try:
        rows = [json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
                for line in text.split("\n")[:-1]]
    except RecursionError as exc:
        raise ValueError("excessive JSON nesting") from exc
    cursor = iter(rows)

    def row():
        value = next(cursor)
        if type(value) is not dict:
            raise ValueError("object required")
        return value

    def event(stage, request=0, result=0, opened=False, error=0):
        value = row()
        if set(value) != {"stage", "request", "return", "errno", "linux_result"}:
            raise ValueError("event fields")
        if any(type(value[key]) is not int for key in ("request", "return", "errno", "linux_result")):
            raise ValueError("integer event")
        if value["stage"] != stage or value["request"] != request or value["errno"] != error:
            raise ValueError("event identity/errno")
        linux_result = -error if result == -1 else (value["return"] if opened else result)
        if value["linux_result"] != linux_result or (value["return"] < 0 if opened else value["return"] != result):
            raise ValueError("event result")

    def online(stage, expected):
        event(stage, opened=True)
        event("cpu_online_read", result=2)
        value = row()
        if (set(value) != {"stage", "value"} or
                value["stage"] != "cpu_online_value" or
                type(value["value"]) is not int or value["value"] != expected):
            raise ValueError("online state")
        event("cpu_online_close")

    def cpu(stage, request, expected):
        event(stage, request)
        value = row()
        if (set(value) != {"stage", "count", "cpus"} or
                value["stage"] != "cpu_inventory" or
                type(value["count"]) is not int or value["count"] != len(expected) or
                type(value["cpus"]) is not list or
                any(type(cpu_id) is not int for cpu_id in value["cpus"]) or
                value["cpus"] != expected):
            raise ValueError("CPU ownership")

    def memory(stage, request, expected):
        event(stage, request)
        value = row()
        if set(value) != {"stage", "chunks", "bytes"} or value["stage"] != "memory_inventory":
            raise ValueError("memory fields")
        if type(value["bytes"]) is not int or value["bytes"] != expected or type(value["chunks"]) is not list:
            raise ValueError("memory total")
        total = 0
        for chunk in value["chunks"]:
            if type(chunk) is not list or len(chunk) != 2 or any(type(x) is not int for x in chunk):
                raise ValueError("chunk shape")
            size, node = chunk
            if size <= 0 or size % 4096 or node != 0:
                raise ValueError("chunk identity")
            total += size
        if total != expected or len(value["chunks"]) > 4096:
            raise ValueError("chunk total")

    try:
        event("open_control", opened=True)
        event("open_os", opened=True)
        event("status_after_external_stop", 0x112a03)
        online("online_before_release", 1)
        cpu("reserved_cpu_before", 0x112906, [])
        memory("reserved_mem_before", 0x112907, 128 * 1024 * 1024)
        event("assigned_cpu_unavailable", 0x112a26, -1, error=16)
        if row() != {"stage": "os_inventory_unavailable", "resource": "cpu", "reason": "closed_admission"}:
            raise ValueError("CPU inventory unavailable reason")
        event("assigned_mem_unavailable", 0x112a27, -1, error=16)
        if row() != {"stage": "os_inventory_unavailable", "resource": "memory", "reason": "closed_admission"}:
            raise ValueError("memory inventory unavailable reason")
        event("close_os")
        event("destroy_os", 0x112901)
        cpu("reserved_cpu_returned", 0x112906, [])
        memory("reserved_mem_returned", 0x112907, 128 * 1024 * 1024)
        event("release_device_mem", 0x112905)
        cpu("reserved_cpu_final", 0x112906, [])
        memory("reserved_mem_final", 0x112907, 0)
        online("online_after_release", 1)
        event("close_control")
        value = row()
        if (set(value) != {"schema", "result", "physical_identity_verified", "generation_verified", "reboot_verified"} or
                value["schema"] != "native-resource-release-v2" or
                value["result"] != "PASS_PUBLIC_RELEASE" or
                any(value[field] is not False for field in
                    ("physical_identity_verified", "generation_verified", "reboot_verified"))):
            raise ValueError("scope")
        if list(cursor):
            raise ValueError("trailing rows")
    except StopIteration as exc:
        raise ValueError("incomplete trace") from exc
    return {"public_release_protocol": "PASS", "native_execution_verified": False,
            "resource_restoration_verified": False}
