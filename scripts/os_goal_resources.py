"""Campaign planning and explicit fresh HOST accounting, without mutations.

Launcher planning is not execution admission. A payload additionally needs a
fresh, complete accounting snapshot checked by ``check_payload_admission`` and
the Root's separate actual account, source, permission and ownership gates.
"""

import math
import os
from pathlib import Path
import shutil


GIB = 1024 ** 3
SCRATCH = Path("/home/holden/mckernel-work/scratch")
MEMORY_RESERVE_GIB = 4
HOST_CPUS = frozenset({0, 6, 7})
HOST_MEMORY_GIB = 4
HOST_MAX_JOBS = 3
SOURCE_OWNER_SLOTS = 6
PAYLOAD_MEMAVAILABLE_GIB = 26
MAX_ADMISSION_AGE_NS = 25_000_000_000
MAX_PAIRED_CLOCK_SKEW_NS = 1_000_000_000
HOST_DISK_FLOOR_GIB = 16
# Existing published/transport guests require >11 GiB in /work. Keep headroom
# above that requirement; packet-specific larger requirements still take priority.
SCRATCH_DISK_FLOOR_GIB = 12


def _positive(name, value, integral=False):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or (isinstance(value, float) and not math.isfinite(value))
            or value <= 0 or (integral and value != int(value))):
        raise ValueError(name + " must be a finite positive "
                         + ("integer" if integral else "number"))
    return int(value) if integral else value


def _available_memory_gib():
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        fields = line.split()
        if fields and fields[0] == "MemAvailable:":
            if len(fields) == 3 and fields[1].isdigit() and fields[2] == "kB":
                return int(fields[1]) * 1024 / GIB
            break
    raise RuntimeError("Cannot measure MemAvailable from /proc/meminfo")


def _integer(name, value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(name + " must be a Python integer >= " + str(minimum))
    return value


def _cpu_list(name, value):
    if (not isinstance(value, (list, tuple)) or not value
            or any(type(cpu) is not int or cpu < 0 for cpu in value)
            or len(set(value)) != len(value)):
        raise ValueError(name + " must contain distinct measured CPU integers")
    return set(value)


def resolve_resources(profile="aggressive", max_agents=None, build_jobs=None,
                      memory_gib=None, repo=None):
    """Return planning ceilings, never free payload capacity or a live grant.

    Both retained profile names obey the current campaign's three HOST jobs and
    4 GiB TOTAL ceiling. Six remote source-owner slots do not reserve 2 GiB each;
    their measured local overhead belongs in the shared total at admission.
    No CPU affinity or execution profile is changed by this function.
    """
    if profile not in ("aggressive", "balanced"):
        raise ValueError("profile must be aggressive or balanced")
    for name, value in (("max_agents", max_agents), ("build_jobs", build_jobs),
                        ("memory_gib", memory_gib)):
        if value is not None:
            _positive(name, value, integral=name != "memory_gib")

    # Do not fall back to a wider online CPU count when an affinity probe fails.
    if not hasattr(os, "sched_getaffinity"):
        raise RuntimeError("Cannot measure CPU affinity; no HOST CPU is inferred")
    observed_affinity = sorted(os.sched_getaffinity(0))
    if not observed_affinity:
        raise RuntimeError("No CPUs available in the current affinity")
    affinity = sorted(set(observed_affinity) & HOST_CPUS)
    cpu_count = len(affinity)
    available_memory = _available_memory_gib()
    memory_limit = max(0, min(HOST_MEMORY_GIB, available_memory - MEMORY_RESERVE_GIB))
    if memory_gib is not None and memory_gib > memory_limit:
        raise ValueError("memory_gib exceeds the profile/available ceiling of {:g} GiB"
                         .format(memory_limit))
    memory = memory_limit if memory_gib is None else float(memory_gib)
    job_limit = min(cpu_count, HOST_MAX_JOBS)
    for name, value, limit in (("max_agents", max_agents, SOURCE_OWNER_SLOTS),
                               ("build_jobs", build_jobs, job_limit)):
        if value is not None and value > limit:
            raise ValueError("{} exceeds the profile/available ceiling of {}".format(name, limit))

    repo = Path(repo).resolve() if repo is not None else Path(__file__).resolve().parents[1]
    scratch_mounted = os.path.ismount(SCRATCH)
    return {
        "profile": profile,
        "max_agents": SOURCE_OWNER_SLOTS if max_agents is None else int(max_agents),
        "build_jobs": job_limit if build_jobs is None else int(build_jobs),
        "memory_gib": memory,
        "cpu_count": cpu_count,
        "cpu_affinity": affinity,
        "observed_cpu_affinity": observed_affinity,
        "available_memory_gib": available_memory,
        "memory_reserve_gib": MEMORY_RESERVE_GIB,
        "agent_memory_gib": None,
        "source_owner_slots": SOURCE_OWNER_SLOTS,
        "payload_admission_required": True,
        "native": {"cpu_affinity": [2, 3, 4, 5], "memory_gib": 12,
                   "max_owners": 1, "separate_admission_required": True},
        "max_depth": 1,
        "heavy_jobs": 1,
        "host_disk": {"path": str(repo), "free_gib": shutil.disk_usage(repo).free / GIB,
                      "min_free_gib": HOST_DISK_FLOOR_GIB},
        "scratch_disk": {"path": str(SCRATCH), "mounted": scratch_mounted,
                         "free_gib": shutil.disk_usage(SCRATCH).free / GIB if scratch_mounted else None,
                         "min_free_gib": SCRATCH_DISK_FLOOR_GIB},
    }


def check_resources(resources):
    """Check launcher planning capacity only; this never admits a payload.

    Callers may raise either disk's min_free_gib to a reviewed packet's measured
    requirement. The launch floors of 16/12 GiB cannot be lowered. This snapshot
    check is not a lease. Cached planning cannot replace fresh payload accounting.
    """
    failures = []
    if not resources["cpu_affinity"]:
        failures.append("No campaign HOST CPU in the measured affinity (allowed: 0,6,7)")
    elif not set(resources["cpu_affinity"]).issubset(HOST_CPUS):
        raise ValueError("Planning CPU affinity includes a non-HOST CPU")
    if resources["memory_gib"] > HOST_MEMORY_GIB:
        raise ValueError("HOST planning exceeds the 4 GiB TOTAL ceiling")
    if resources["build_jobs"] > min(HOST_MAX_JOBS, len(resources["cpu_affinity"])):
        raise ValueError("HOST planning exceeds the measured three-job ceiling")
    if resources["memory_gib"] <= 0:
        failures.append("MemAvailable leaves no memory after the 4 GiB host reserve")
    for key, minimum in (("host_disk", HOST_DISK_FLOOR_GIB),
                         ("scratch_disk", SCRATCH_DISK_FLOOR_GIB)):
        disk = resources[key]
        if key == "scratch_disk" and not disk["mounted"]:
            continue
        floor = max(minimum, _positive(key + ".min_free_gib", disk["min_free_gib"]))
        if disk["free_gib"] < floor:
            failures.append("{} has {:g} GiB free; requires at least {:g} GiB"
                            .format(disk["path"], disk["free_gib"], floor))
    if failures:
        raise RuntimeError("Insufficient resources: " + "; ".join(failures))


def check_payload_admission(snapshot, request, *, now_utc_ns, now_mono_ns):
    """Check one fresh explicit HOST resource decision, without I/O or release.

    The sole compositor supplies the complete retained HOST charge list (UNKNOWN
    charges included), ALL measured controller/worker overhead, exact reviewed
    packet floors and a positive compatibility decision for current exclusivity.
    Missing data never means zero. This resource-only result supplies no account,
    source, permission, native or lifecycle authorization and is not a stored lease.
    """
    if not isinstance(snapshot, dict) or not isinstance(request, dict):
        raise ValueError("Explicit accounting snapshot and payload request are required")
    try:
        utc_now = _integer("now_utc_ns", now_utc_ns)
        mono_now = _integer("now_mono_ns", now_mono_ns)
        utc_observed = _integer("observed_utc_ns", snapshot["observed_utc_ns"])
        mono_observed = _integer("observed_mono_ns", snapshot["observed_mono_ns"])
        max_age = _integer("max_age_ns", request["max_age_ns"], 1)
        if max_age > MAX_ADMISSION_AGE_NS:
            raise ValueError("Payload freshness cannot exceed 25 seconds")
        utc_age, mono_age = utc_now - utc_observed, mono_now - mono_observed
        if (min(utc_age, mono_age) < 0 or max(utc_age, mono_age) > max_age
                or abs(utc_age - mono_age) > MAX_PAIRED_CLOCK_SKEW_NS):
            raise RuntimeError("Fresh paired UTC/monotonic accounting is required")

        if snapshot["retained_charges_complete"] is not True:
            raise RuntimeError("Complete retained HOST accounting is required")
        charges = snapshot["retained_charges"]
        if not isinstance(charges, list):
            raise ValueError("retained_charges must be an explicit list")
        retained_bytes = retained_jobs = 0
        for charge in charges:
            if not isinstance(charge, dict):
                raise ValueError("Every retained charge must be explicit")
            owner = charge["owner"]
            if not isinstance(owner, str) or not owner.strip():
                raise ValueError("Every retained charge owner must be named")
            if (not isinstance(charge["state"], str)
                    or charge["state"] not in {"ACTIVE", "RETAINED", "UNKNOWN"}):
                raise ValueError("Retained charge state must preserve ACTIVE/RETAINED/UNKNOWN")
            # Multiple retained families may belong to the same Root. Count
            # every row; never deduplicate charges by a logical owner slot.
            retained_bytes += _integer("retained planning_bytes", charge["planning_bytes"], 1)
            retained_jobs += _integer("retained jobs", charge["jobs"], 1)
        if snapshot["all_controller_worker_overhead_measured"] is not True:
            raise RuntimeError("ALL controller/worker overhead must be measured")
        overhead = _integer("controller_worker_overhead_bytes",
                            snapshot["controller_worker_overhead_bytes"], 1)
        if snapshot["exclusive_scope_compatible"] is not True:
            raise RuntimeError("Current exclusive ownership is not compatible")

        measured_cpus = _cpu_list("cpu_affinity", snapshot["cpu_affinity"])
        requested_cpus = _cpu_list("CPU", request["CPU"])
        if not requested_cpus.issubset(measured_cpus & HOST_CPUS):
            raise RuntimeError("Payload CPU is outside measured HOST CPUs 0,6,7")
        new_bytes = _integer("planning_bytes", request["planning_bytes"], 1)
        new_jobs = _integer("jobs", request["jobs"], 1)
        host_floor = _integer("host_floor_bytes", request["host_floor_bytes"],
                              HOST_DISK_FLOOR_GIB * GIB)
        scratch_floor = _integer("scratch_floor_bytes", request["scratch_floor_bytes"],
                                 SCRATCH_DISK_FLOOR_GIB * GIB)
        available = _integer("MemAvailable_bytes", snapshot["MemAvailable_bytes"])
        host_free = _integer("host_free_bytes", snapshot["host_free_bytes"])
        scratch_free = _integer("scratch_free_bytes", snapshot["scratch_free_bytes"])
    except KeyError as error:
        raise ValueError("Missing explicit payload accounting field: " + str(error.args[0])) from error

    total_bytes = retained_bytes + overhead + new_bytes
    total_jobs = retained_jobs + new_jobs
    if total_bytes > HOST_MEMORY_GIB * GIB or total_jobs > HOST_MAX_JOBS:
        raise RuntimeError("Retained charges + ALL overhead + new family exceed 4 GiB/max3 HOST jobs")
    if available < PAYLOAD_MEMAVAILABLE_GIB * GIB:
        raise RuntimeError("Payload admission requires at least 26 GiB MemAvailable")
    if host_free < host_floor or scratch_free < scratch_floor:
        raise RuntimeError("Fresh host/scratch space does not meet the exact packet floors")
    return {"scope": "HOST_resource_check_only", "accounted_total_bytes": total_bytes,
            "accounted_total_jobs": total_jobs, "retained_bytes": retained_bytes,
            "retained_jobs": retained_jobs, "measured_overhead_bytes": overhead,
            "new_family_bytes": new_bytes, "new_family_jobs": new_jobs,
            "CPU": sorted(requested_cpus), "observed_utc_ns": utc_observed,
            "observed_mono_ns": mono_observed}


def resource_instructions(resources):
    """Compact coordinator guidance; grants no guest/root execution release."""
    return (
        "Host scheduling profile {profile}: up to {max_agents} remote source-owner child agents, "
        "no recursive agents (maximum depth 1). Parallelize disjoint source and "
        "light-test work. The coordinator owns one heavy build/guest at a time; "
        "reconcile existing leases before starting it. HOST uses only the measured "
        "intersection with CPUs 0,6,7, up to {build_jobs} aggregate payload jobs and "
        "{memory_gib:g} GiB TOTAL including every retained UNKNOWN charge and ALL "
        "measured controller/worker/capture overhead. Remote owner slots do not "
        "reserve or multiply 2 GiB of payload RAM per model. Planning/cache is not "
        "execution admission. Before each new family the sole Root needs fresh "
        "paired-clock accounting, compatible exclusive ownership, at least 26 GiB "
        "MemAvailable, exact packet floors and actual account/source/permission "
        "admission. Missing accounting is UNKNOWN, never zero. "
        "Multiple light Docker checks may overlap only under their reviewed "
        "unprivileged profiles, disjoint output roots and measured shared CPU/RAM/"
        "storage headroom; they do not create another heavy build/guest lease. "
        "Preserve the separate single native owner on CPUs 2-5/12 GiB; never "
        "borrow native CPUs or infer its clearance from HOST capacity. The native "
        "pinned container has no swap, 512 tasks and no network. Guest/root profile "
        "expansion requires independent execution review. Build environment "
        "defaults apply only to host tools in the launcher's process tree. "
        "The existing container runner does not forward these variables or "
        "automatically resize containers; select explicit reviewed per-command "
        "container job limits within the aggregate HOST cap. Memory is a planning "
        "ceiling, not an enforced cgroup limit. Do not widen affinity or system "
        "limits. Remeasure host/scratch capacity before heavy work; preserve "
        "at least 16/12 GiB free respectively and any greater measured packet "
        "requirements, capture needs and emergency headroom. A positively scoped "
        "lane block retains its charges and exclusions while independent eligible "
        "source work continues. Park the blocked task; a terminal model turn frees "
        "only its logical agent slot, never unjoined processes or RAM/job/lease "
        "charges. Unknown scope is not clearance. Global account, "
        "auth, budget/unknown accounting and user pause stop new work. When no "
        "eligible work fits, wait for meaningful input; do not fill slots artificially."
    ).format(**resources)


def resource_environment(resources):
    """Host process-tree overrides only; no global or container configuration."""
    jobs = str(_positive("build_jobs", resources["build_jobs"], integral=True))
    return {
        "MAKEFLAGS": "-j" + jobs,
        "CMAKE_BUILD_PARALLEL_LEVEL": jobs,
        "CARGO_BUILD_JOBS": jobs,
        "MCKERNEL_OS_RESOURCE_PROFILE": resources["profile"],
        "MCKERNEL_OS_MAX_AGENTS": str(resources["max_agents"]),
        "MCKERNEL_OS_BUILD_JOBS": jobs,
        "MCKERNEL_OS_MEMORY_GIB": "{:g}".format(resources["memory_gib"]),
        "MCKERNEL_OS_MAX_DEPTH": str(resources["max_depth"]),
        "MCKERNEL_OS_HEAVY_JOBS": str(resources["heavy_jobs"]),
    }
