"""Host scheduling budgets, without changing affinity, limits or environment.

Resolve a fresh snapshot immediately before launch; dry runs may report it even
when check_resources would reject admission. Memory is a shared planning budget,
not a cgroup limit. Reviewed execution packets retain their own stricter limits.
"""

import math
import os
from pathlib import Path
import shutil


GIB = 1024 ** 3
SCRATCH = Path("/home/holden/mckernel-work/scratch")
MEMORY_RESERVE_GIB = 4
AGENT_MEMORY_GIB = 2
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


def resolve_resources(profile="aggressive", max_agents=None, build_jobs=None,
                      memory_gib=None, repo=None):
    """Return JSON-safe limits and measured CPU, memory and disk capacity.

    Aggressive permits two remote-inference/source children per allowed CPU;
    balanced permits one. Each child has a 2-GiB planning share, with a minimum
    of one child on constrained hosts. Build jobs remain bounded by CPU affinity,
    and all concurrent work shares memory_gib.
    Aggressive defaults to eight children; an explicit count may exceed eight
    if capacity permits. Balanced keeps its three-child/four-job/12-GiB caps.
    Invalid or excessive overrides raise ValueError; unreadable probes fail.
    Insufficient disk or no memory after the reserve is reported for dry runs
    and rejected separately by check_resources.
    """
    if profile not in ("aggressive", "balanced"):
        raise ValueError("profile must be aggressive or balanced")
    for name, value in (("max_agents", max_agents), ("build_jobs", build_jobs),
                        ("memory_gib", memory_gib)):
        if value is not None:
            _positive(name, value, integral=name != "memory_gib")

    # Do not fall back to a wider online CPU count when an affinity probe fails.
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None
    cpu_count = len(affinity) if affinity is not None else (os.cpu_count() or 1)
    if cpu_count < 1:
        raise RuntimeError("No CPUs available in the current affinity")
    available_memory = _available_memory_gib()
    balanced = profile == "balanced"
    memory_limit = max(0, min(12 if balanced else 24,
                              available_memory - MEMORY_RESERVE_GIB))
    if memory_gib is not None and memory_gib > memory_limit:
        raise ValueError("memory_gib exceeds the profile/available ceiling of {:g} GiB"
                         .format(memory_limit))
    memory = memory_limit if memory_gib is None else float(memory_gib)
    job_limit = min(cpu_count, 4) if balanced else cpu_count
    agent_cpu_limit = cpu_count if balanced else cpu_count * 2
    agent_limit = max(1, min(agent_cpu_limit, int(memory // AGENT_MEMORY_GIB)))
    if balanced:
        agent_limit = min(3, agent_limit)
    for name, value, limit in (("max_agents", max_agents, agent_limit),
                               ("build_jobs", build_jobs, job_limit)):
        if value is not None and value > limit:
            raise ValueError("{} exceeds the profile/available ceiling of {}".format(name, limit))

    repo = Path(repo).resolve() if repo is not None else Path(__file__).resolve().parents[1]
    scratch_mounted = os.path.ismount(SCRATCH)
    return {
        "profile": profile,
        "max_agents": min(3 if balanced else 8, agent_limit) if max_agents is None else int(max_agents),
        "build_jobs": job_limit if build_jobs is None else int(build_jobs),
        "memory_gib": memory,
        "cpu_count": cpu_count,
        "cpu_affinity": affinity,
        "available_memory_gib": available_memory,
        "memory_reserve_gib": MEMORY_RESERVE_GIB,
        "agent_memory_gib": AGENT_MEMORY_GIB,
        "max_depth": 1,
        "heavy_jobs": 1,
        "host_disk": {"path": str(repo), "free_gib": shutil.disk_usage(repo).free / GIB,
                      "min_free_gib": HOST_DISK_FLOOR_GIB},
        "scratch_disk": {"path": str(SCRATCH), "mounted": scratch_mounted,
                         "free_gib": shutil.disk_usage(SCRATCH).free / GIB if scratch_mounted else None,
                         "min_free_gib": SCRATCH_DISK_FLOOR_GIB},
    }


def check_resources(resources):
    """Raise RuntimeError for an inadmissible snapshot; return None on success.

    Callers may raise either disk's min_free_gib to a reviewed packet's measured
    requirement. The launch floors of 16/12 GiB cannot be lowered. This snapshot
    check is not a lease: remeasure before each heavy operation.
    """
    failures = []
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


def resource_instructions(resources):
    """Compact coordinator guidance; grants no guest/root execution release."""
    return (
        "Host scheduling profile {profile}: up to {max_agents} child agents, "
        "no recursive agents (maximum depth 1). Parallelize disjoint source and "
        "light-test work. The coordinator owns one heavy build/guest at a time; "
        "reconcile existing leases before starting it. All concurrent work shares "
        "an aggregate {build_jobs}-job/{memory_gib:g}-GiB budget; divide jobs and "
        "memory among workers, never multiply the budget per agent. "
        "User-authorized host scheduling supersedes older coordinator caps only. "
        "Preserve reviewed execution profiles: the pinned container has CPUs 2-5 "
        "(4 CPUs), 12 GiB, no swap, 512 tasks and no network. Guest/root profile "
        "expansion requires independent execution review. Build environment "
        "defaults apply only to host tools in the launcher's process tree. "
        "The existing container runner does not forward these variables or "
        "automatically resize containers; select explicit reviewed per-command "
        "container job limits (currently -j<=4). Memory is a planning "
        "ceiling, not an enforced cgroup limit. Do not widen affinity or system "
        "limits. Remeasure host/scratch capacity before heavy work; preserve "
        "at least 16/12 GiB free respectively and any greater measured packet "
        "requirements, capture needs and emergency headroom."
    ).format(**resources)


def resource_environment(resources):
    """Host process-tree overrides only; no global or container configuration."""
    jobs = str(resources["build_jobs"])
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
