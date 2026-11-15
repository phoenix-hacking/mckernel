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
SHARED_MEMORY_RESERVE_GIB = 2
HOST_CPUS = frozenset({0, 6, 7})
HOST_MEMORY_GIB = 4
NON_HOST_RESERVATION_GIB = 18
HOST_MAX_JOBS = 3
DEFAULT_SOURCE_OWNER_SLOTS = 6
PAYLOAD_MEMAVAILABLE_GIB = NON_HOST_RESERVATION_GIB + MEMORY_RESERVE_GIB + HOST_MEMORY_GIB
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


def _memory_gib(field):
    for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
        fields = line.split()
        if fields and fields[0] == field + ":":
            if len(fields) == 3 and fields[1].isdigit() and fields[2] == "kB":
                return int(fields[1]) * 1024 / GIB
            break
    raise RuntimeError("Cannot measure " + field + " from /proc/meminfo")


def _available_memory_gib():
    return _memory_gib("MemAvailable")


def _total_memory_gib():
    return _memory_gib("MemTotal")


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


def _payload_memavailable_bytes(host_memory_ceiling_bytes):
    return ((NON_HOST_RESERVATION_GIB + MEMORY_RESERVE_GIB) * GIB
            + host_memory_ceiling_bytes)


def resolve_resources(profile="aggressive", max_agents=None, build_jobs=None,
                      memory_gib=None, repo=None, *, host_cpu_affinity=None,
                      host_max_jobs=None, work_memory_gib=None):
    """Return planning ceilings, never free payload capacity or a live grant.

    Both retained profile names default to three HOST jobs and 4 GiB TOTAL.
    An explicit memory_gib may select the measured headroom after 18 GiB of non-HOST
    reservations and the 4 GiB machine reserve in measured available memory.
    Explicit CPU/job selections replace the defaults, within measured affinity
    and fresh actual ownership admission. Explicit build_jobs also selects the
    aggregate job ceiling unless host_max_jobs selects a separate bound.
    Source-owner slots default to six;
    an explicit count plans the next supported server configuration, never
    changes its currently loaded limit. Slots do not reserve memory slices;
    their measured local overhead belongs in the shared total at admission.
    Explicit work_memory_gib instead selects one shared work pool including the
    preserved non-HOST reservations. Its ceiling uses MemTotal minus a 2 GiB OS
    reserve; already resident controller memory is inside this pool.
    No CPU affinity or execution profile is changed by this function.
    """
    if profile not in ("aggressive", "balanced"):
        raise ValueError("profile must be aggressive or balanced")
    for name, value in (("max_agents", max_agents), ("build_jobs", build_jobs),
                        ("host_max_jobs", host_max_jobs),
                        ("memory_gib", memory_gib), ("work_memory_gib", work_memory_gib)):
        if value is not None:
            _positive(name, value, integral=name not in {"memory_gib", "work_memory_gib"})

    # Do not fall back to a wider online CPU count when an affinity probe fails.
    if not hasattr(os, "sched_getaffinity"):
        raise RuntimeError("Cannot measure CPU affinity; no HOST CPU is inferred")
    observed_affinity = sorted(os.sched_getaffinity(0))
    if not observed_affinity:
        raise RuntimeError("No CPUs available in the current affinity")
    if host_cpu_affinity is None:
        affinity = sorted(set(observed_affinity) & HOST_CPUS)
    else:
        selected_cpus = _cpu_list("host_cpu_affinity", host_cpu_affinity)
        if not selected_cpus.issubset(observed_affinity):
            raise ValueError("host_cpu_affinity exceeds the measured process affinity")
        affinity = sorted(selected_cpus)
    cpu_count = len(affinity)
    available_memory = _available_memory_gib()
    if work_memory_gib is not None:
        total_memory = _total_memory_gib()
        if work_memory_gib > total_memory - SHARED_MEMORY_RESERVE_GIB:
            raise ValueError("work_memory_gib exceeds measured MemTotal minus the 2 GiB machine reserve")
        memory_limit = work_memory_gib - NON_HOST_RESERVATION_GIB
        if memory_limit <= 0:
            raise ValueError("Shared work memory must exceed preserved 18 GiB non-HOST reservations")
    else:
        expanded = memory_gib is not None and memory_gib > HOST_MEMORY_GIB
        reservation = MEMORY_RESERVE_GIB + (NON_HOST_RESERVATION_GIB if expanded else 0)
        memory_limit = max(0, available_memory - reservation)
        if not expanded:
            memory_limit = min(HOST_MEMORY_GIB, memory_limit)
    if memory_gib is not None and memory_gib > memory_limit:
        raise ValueError("memory_gib exceeds the profile/available ceiling of {:g} GiB"
                         .format(memory_limit))
    memory = memory_limit if memory_gib is None else float(memory_gib)
    if host_max_jobs is not None:
        selected_job_limit = int(host_max_jobs)
    elif build_jobs is not None:
        selected_job_limit = int(build_jobs)
    else:
        selected_job_limit = HOST_MAX_JOBS
    job_limit = (min(cpu_count, selected_job_limit)
                 if host_max_jobs is None and build_jobs is None else selected_job_limit)
    if build_jobs is not None and build_jobs > job_limit:
        raise ValueError("build_jobs exceeds the selected HOST job ceiling of {}".format(job_limit))
    owner_slots = DEFAULT_SOURCE_OWNER_SLOTS if max_agents is None else int(max_agents)

    repo = Path(repo).resolve() if repo is not None else Path(__file__).resolve().parents[1]
    scratch_mounted = os.path.ismount(SCRATCH)
    result = {
        "profile": profile,
        "max_agents": owner_slots,
        "build_jobs": job_limit if build_jobs is None else int(build_jobs),
        "host_max_jobs": selected_job_limit,
        "memory_gib": memory,
        "host_memory_ceiling_bytes": int(memory * GIB),
        "payload_memavailable_gib": _payload_memavailable_bytes(int(memory * GIB)) / GIB,
        "cpu_count": cpu_count,
        "cpu_affinity": affinity,
        "host_cpu_affinity": list(affinity),
        "observed_cpu_affinity": observed_affinity,
        "available_memory_gib": available_memory,
        "memory_reserve_gib": MEMORY_RESERVE_GIB,
        "machine_reserve_gib": MEMORY_RESERVE_GIB,
        "non_host_reservation_gib": NON_HOST_RESERVATION_GIB,
        "agent_memory_gib": None,
        "source_owner_slots": owner_slots,
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
    if work_memory_gib is not None:
        result.update({"work_memory_gib": float(work_memory_gib),
                       "work_memory_ceiling_bytes": int(work_memory_gib * GIB),
                       "total_memory_gib": total_memory,
                       "memory_reserve_gib": SHARED_MEMORY_RESERVE_GIB,
                       "machine_reserve_gib": SHARED_MEMORY_RESERVE_GIB,
                       "heavy_jobs": selected_job_limit,
                       "payload_memavailable_gib": None})
    return result


def check_resources(resources):
    """Check launcher planning capacity only; this never admits a payload.

    Callers may raise either disk's min_free_gib to a reviewed packet's measured
    requirement. The launch floors of 16/12 GiB cannot be lowered. This snapshot
    check is not a lease. Cached planning cannot replace fresh payload accounting.
    """
    failures = []
    if not resources["cpu_affinity"]:
        failures.append("No campaign HOST CPU in the measured selected affinity")
    elif not set(resources["cpu_affinity"]).issubset(
            set(resources.get("host_cpu_affinity", HOST_CPUS))
            & set(resources.get("observed_cpu_affinity", resources["cpu_affinity"]))):
        raise ValueError("Planning CPU affinity is outside the measured HOST selection")
    if "work_memory_ceiling_bytes" in resources:
        work_ceiling = _integer("work_memory_ceiling_bytes", resources["work_memory_ceiling_bytes"], 1)
        if work_ceiling > int((resources["total_memory_gib"] - SHARED_MEMORY_RESERVE_GIB) * GIB):
            raise ValueError("Shared work pool exceeds measured MemTotal minus the 2 GiB machine reserve")
        if int(resources["memory_gib"] * GIB) + NON_HOST_RESERVATION_GIB * GIB > work_ceiling:
            raise ValueError("HOST ceiling plus preserved non-HOST reservations exceeds shared work pool")
        if resources["available_memory_gib"] < SHARED_MEMORY_RESERVE_GIB:
            failures.append("Shared work pool leaves less than the 2 GiB machine-free floor")
    elif resources["memory_gib"] > HOST_MEMORY_GIB:
        required = _payload_memavailable_bytes(int(resources["memory_gib"] * GIB)) / GIB
        if resources["available_memory_gib"] < required:
            failures.append("Expanded HOST pool requires at least {:g} GiB MemAvailable "
                            "including 18 GiB non-HOST reservations and the 4 GiB host reserve"
                            .format(required))
    job_limit = _integer("host_max_jobs", resources.get("host_max_jobs", HOST_MAX_JOBS), 1)
    if resources["build_jobs"] > job_limit:
        raise ValueError("HOST planning exceeds the selected job ceiling")
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


def check_machine_headroom(repo, memory_reserve_gib=MEMORY_RESERVE_GIB):
    """A cheap live machine guard; this never grants a workload admission."""
    reserve = _positive("memory_reserve_gib", memory_reserve_gib)
    if reserve < SHARED_MEMORY_RESERVE_GIB:
        raise ValueError("Machine reserve cannot be below 2 GiB")
    available = _available_memory_gib()
    host_free = shutil.disk_usage(repo).free / GIB
    scratch_free = shutil.disk_usage(SCRATCH).free / GIB if os.path.ismount(SCRATCH) else None
    if (available < reserve or host_free < HOST_DISK_FLOOR_GIB
            or scratch_free is not None and scratch_free < SCRATCH_DISK_FLOOR_GIB):
        raise RuntimeError("Machine headroom exhausted: MemAvailable={:.3f} GiB (reserve {}); "
                           "host_free={:.3f} GiB (floor {}); scratch_free={} GiB (floor {})"
                           .format(available, reserve, host_free, HOST_DISK_FLOOR_GIB,
                                   scratch_free, SCRATCH_DISK_FLOOR_GIB))


def check_payload_admission(snapshot, request, *, now_utc_ns, now_mono_ns):
    """Check one fresh explicit HOST resource decision, without I/O or release.

    The sole compositor supplies the complete retained HOST charge list (UNKNOWN
    charges included), ALL measured controller/worker overhead, exact reviewed
    packet floors and a positive compatibility decision for current exclusivity.
    Missing data never means zero. This resource-only result supplies no account,
    source, permission, native or lifecycle authorization and is not a stored lease.
    Optional host_memory_ceiling_bytes, host_cpu_affinity and host_max_jobs select
    one aggregate pool. Omission retains 4 GiB, CPUs 0,6,7 and three jobs. Explicit
    expansion must fit measured headroom/affinity and actual ownership admission.
    It does not enlarge a payload's enforced memory limit or release any charge.
    An explicit shared work_memory_ceiling_bytes includes the preserved 18 GiB
    non-HOST reservation, uses measured MemTotal minus a 2 GiB machine reserve,
    and checks only additional obligations against fresh MemAvailable. Optional
    non_host_resident_bytes credits measured non-HOST resident memory only.
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
        selected_cpus = (_cpu_list("host_cpu_affinity", request["host_cpu_affinity"])
                         if "host_cpu_affinity" in request else set(HOST_CPUS))
        if "host_cpu_affinity" in request and not selected_cpus.issubset(measured_cpus):
            raise RuntimeError("Selected HOST CPUs are outside measured process affinity")
        if not requested_cpus.issubset(measured_cpus & selected_cpus):
            raise RuntimeError("Payload CPU is outside measured selected HOST affinity")
        new_bytes = _integer("planning_bytes", request["planning_bytes"], 1)
        new_jobs = _integer("jobs", request["jobs"], 1)
        memory_ceiling = _integer("host_memory_ceiling_bytes",
                                  request.get("host_memory_ceiling_bytes", HOST_MEMORY_GIB * GIB), 1)
        job_limit = _integer("host_max_jobs", request.get("host_max_jobs", HOST_MAX_JOBS), 1)
        host_floor = _integer("host_floor_bytes", request["host_floor_bytes"],
                              HOST_DISK_FLOOR_GIB * GIB)
        scratch_floor = _integer("scratch_floor_bytes", request["scratch_floor_bytes"],
                                 SCRATCH_DISK_FLOOR_GIB * GIB)
        available = _integer("MemAvailable_bytes", snapshot["MemAvailable_bytes"])
        host_free = _integer("host_free_bytes", snapshot["host_free_bytes"])
        scratch_free = _integer("scratch_free_bytes", snapshot["scratch_free_bytes"])
        work_ceiling = None
        non_host_resident = 0
        machine_reserve = MEMORY_RESERVE_GIB * GIB
        if "work_memory_ceiling_bytes" in request:
            _integer("host_memory_ceiling_bytes", request["host_memory_ceiling_bytes"], 1)
            work_ceiling = _integer("work_memory_ceiling_bytes", request["work_memory_ceiling_bytes"], 1)
            total_memory = _integer("MemTotal_bytes", snapshot["MemTotal_bytes"], 1)
            machine_reserve = SHARED_MEMORY_RESERVE_GIB * GIB
            if work_ceiling + machine_reserve > total_memory:
                raise RuntimeError("Shared work pool exceeds measured MemTotal minus the 2 GiB machine reserve")
            if memory_ceiling + NON_HOST_RESERVATION_GIB * GIB > work_ceiling:
                raise ValueError("HOST ceiling plus preserved non-HOST reservations exceeds shared work pool")
            non_host_resident = _integer("non_host_resident_bytes", snapshot.get("non_host_resident_bytes", 0))
            if non_host_resident > NON_HOST_RESERVATION_GIB * GIB:
                raise ValueError("Measured non-HOST resident credit exceeds its preserved reservation")
    except KeyError as error:
        raise ValueError("Missing explicit payload accounting field: " + str(error.args[0])) from error

    total_bytes = retained_bytes + overhead + new_bytes
    total_jobs = retained_jobs + new_jobs
    if total_bytes > memory_ceiling or total_jobs > job_limit:
        raise RuntimeError(
            "Retained charges + ALL overhead + new family exceed {:g} GiB/max{} HOST jobs: "
            "retained_bytes={}; measured_overhead_bytes={}; requested_family_bytes={}; "
            "total_bytes={}/{}; total_jobs={}/{}; maximum_new_family_bytes={}; maximum_new_jobs={}. "
            "Select greater explicit limits only with fresh measured capacity and actual ownership, "
            "or choose another fitting task; unchanged retries add no capacity."
            .format(memory_ceiling / GIB, job_limit, retained_bytes, overhead, new_bytes,
                    total_bytes, memory_ceiling, total_jobs, job_limit,
                    max(0, memory_ceiling - retained_bytes - overhead), max(0, job_limit - retained_jobs)))
    required_available = (_payload_memavailable_bytes(memory_ceiling) if work_ceiling is None else
                          NON_HOST_RESERVATION_GIB * GIB - non_host_resident
                          + retained_bytes + new_bytes + machine_reserve)
    if available < required_available:
        if work_ceiling is not None:
            raise RuntimeError("Shared work admission requires {} fresh MemAvailable bytes for "
                               "unallocated non-HOST reservations, retained HOST charges, new family "
                               "and the 2 GiB machine-free floor; measured controller RSS is already in the pool"
                               .format(required_available))
        raise RuntimeError("Payload admission requires at least {:g} GiB MemAvailable "
                           "for the {:g} GiB aggregate HOST ceiling, 18 GiB non-HOST "
                           "reservations and 4 GiB machine reserve"
                           .format(required_available / GIB, memory_ceiling / GIB))
    if host_free < host_floor or scratch_free < scratch_floor:
        raise RuntimeError("Fresh host/scratch space does not meet the exact packet floors")
    return {"scope": "HOST_resource_check_only", "accounted_total_bytes": total_bytes,
            "host_memory_ceiling_bytes": memory_ceiling,
            "host_cpu_affinity": sorted(measured_cpus & selected_cpus),
            "host_max_jobs": job_limit,
            "work_memory_ceiling_bytes": work_ceiling,
            "shared_work_pool": work_ceiling is not None,
            "machine_reserve_bytes": machine_reserve,
            "machine_reserve_gib": machine_reserve / GIB,
            "non_host_reservation_bytes": NON_HOST_RESERVATION_GIB * GIB,
            "non_host_resident_bytes": non_host_resident,
            "accounted_work_total_bytes": (NON_HOST_RESERVATION_GIB * GIB + total_bytes
                                             if work_ceiling is not None else None),
            "required_memavailable_bytes": required_available,
            "accounted_total_jobs": total_jobs, "retained_bytes": retained_bytes,
            "retained_jobs": retained_jobs, "measured_overhead_bytes": overhead,
            "new_family_bytes": new_bytes, "new_family_jobs": new_jobs,
            "CPU": sorted(requested_cpus), "observed_utc_ns": utc_observed,
            "observed_mono_ns": mono_observed}


def resource_instructions(resources):
    """Compact coordinator guidance; grants no guest/root execution release."""
    guidance = dict(resources)
    guidance["host_cpu_affinity_text"] = ",".join(
        str(cpu) for cpu in resources.get("host_cpu_affinity", resources["cpu_affinity"]))
    guidance["host_max_jobs"] = resources.get("host_max_jobs", HOST_MAX_JOBS)
    guidance["heavy_work"] = (
        "Run independent HOST compiles and checks in parallel within the shared limits; "
        "keep one actual native executor and respect existing exclusive ownership. "
        if "work_memory_ceiling_bytes" in resources else
        "The coordinator owns one heavy build/guest at a time; reconcile existing leases before starting it. ")
    if "work_memory_ceiling_bytes" in resources:
        guidance["memory_admission"] = (
            "a {:g} GiB TOTAL shared work ceiling containing the preserved 18 GiB non-HOST reservation "
            "and the {:g} GiB HOST ceiling, "
            "bounded by measured MemTotal minus the 2 GiB machine reserve. Fresh MemAvailable must "
            "cover unallocated non-HOST reservations plus retained HOST charges, the new family "
            "and a 2 GiB machine-free floor. Measured controller RSS is already allocated inside "
            "the shared pool and is not charged twice. Only positively measured non_host_resident_bytes "
            "may reduce additional non-HOST headroom; no missing ownership or UNKNOWN charge is released. "
            "Bind work_memory_ceiling_bytes alongside host_memory_ceiling_bytes. "
            .format(resources["work_memory_ceiling_bytes"] / GIB, resources["memory_gib"]))
    else:
        guidance["memory_admission"] = (
            "at least {:g} GiB MemAvailable preserving 18 GiB of non-HOST reservations plus "
            "the 4 GiB machine reserve. "
            .format(_payload_memavailable_bytes(int(resources["memory_gib"] * GIB)) / GIB))
    return (
        "Host scheduling profile {profile}: selected {max_agents} remote source-owner child agents "
        "for the next supported server configuration; its actual loaded slot limit remains binding, "
        "no recursive agents (maximum depth 1). Parallelize disjoint source and "
        "light-test work. {heavy_work}HOST uses only the measured "
        "selected CPUs {host_cpu_affinity_text}, up to {host_max_jobs} aggregate payload jobs "
        "(host build parallelism {build_jobs}) and "
        "{memory_gib:g} GiB TOTAL including every retained UNKNOWN charge and ALL "
        "measured controller/worker/capture overhead. Remote owner slots do not "
        "reserve or multiply 2 GiB of payload RAM per model. Planning/cache is not "
        "execution admission. Before each new family the sole Root needs fresh "
        "paired-clock accounting, compatible exclusive ownership, {memory_admission}"
        "Exact packet floors and actual account/source/permission "
        "admission must also pass. Missing accounting is UNKNOWN, never zero. "
        "Bind host_memory_ceiling_bytes, host_cpu_affinity and host_max_jobs in each "
        "payload admission request; omission retains the 4 GiB/CPUs 0,6,7/max3 defaults. Explicit "
        "pool expansion requires fresh measured headroom and actual compatible ownership and "
        "does not change any command's enforced memory limit. "
        "Independent Docker builds/checks may overlap under their actual "
        "unprivileged profiles, disjoint output roots and measured shared CPU/RAM/"
        "storage headroom; never multiply the shared budget by the container count. "
        "Preserve the separate actual native owner on CPUs 2-5/12 GiB; selected "
        "HOST limits never clear native ownership, retained UNKNOWN charges or other holds. "
        "Any CPU overlap requires current actual ownership compatibility. The native "
        "pinned container has no swap, 512 tasks and no network. Guest/root profile "
        "expansion requires independent execution review. Build environment "
        "defaults apply only to host tools in the launcher's process tree. "
        "The existing container runner does not forward these variables or "
        "automatically resize containers; select explicit reviewed per-command "
        "container job limits within the aggregate HOST cap. Memory is a planning "
        "ceiling, not an enforced cgroup limit. Apply selected limits only inside "
        "the admitted workload; preserve global system settings. Remeasure "
        "host/scratch capacity before heavy work; preserve "
        "at least 16/12 GiB free respectively and any greater measured packet "
        "requirements, capture needs and emergency headroom. A positively scoped "
        "lane block retains its charges and exclusions while independent eligible "
        "source work continues. Park the blocked task; a terminal model turn frees "
        "only its logical agent slot, never unjoined processes or RAM/job/lease "
        "charges. Unknown scope is not clearance. Global account, "
        "auth, budget/unknown accounting and user pause stop new work. When no "
        "eligible work fits, wait for meaningful input; do not fill slots artificially."
    ).format(**guidance)


def resource_environment(resources):
    """Host process-tree overrides only; no global or container configuration."""
    jobs = str(_positive("build_jobs", resources["build_jobs"], integral=True))
    result = {
        "MAKEFLAGS": "-j" + jobs,
        "CMAKE_BUILD_PARALLEL_LEVEL": jobs,
        "CARGO_BUILD_JOBS": jobs,
        "MCKERNEL_OS_RESOURCE_PROFILE": resources["profile"],
        "MCKERNEL_OS_MAX_AGENTS": str(resources["max_agents"]),
        "MCKERNEL_OS_BUILD_JOBS": jobs,
        "MCKERNEL_OS_MEMORY_GIB": "{:g}".format(resources["memory_gib"]),
        "MCKERNEL_OS_HOST_MEMORY_CEILING_BYTES": str(int(resources["memory_gib"] * GIB)),
        "MCKERNEL_OS_HOST_CPU_AFFINITY": ",".join(
            str(cpu) for cpu in resources.get("host_cpu_affinity", resources["cpu_affinity"])),
        "MCKERNEL_OS_HOST_MAX_JOBS": str(resources.get("host_max_jobs", HOST_MAX_JOBS)),
        "MCKERNEL_OS_MAX_DEPTH": str(resources["max_depth"]),
        "MCKERNEL_OS_HEAVY_JOBS": str(resources["heavy_jobs"]),
    }
    if "work_memory_ceiling_bytes" in resources:
        result["MCKERNEL_OS_WORK_MEMORY_GIB"] = "{:g}".format(resources["work_memory_ceiling_bytes"] / GIB)
        result["MCKERNEL_OS_WORK_MEMORY_CEILING_BYTES"] = str(resources["work_memory_ceiling_bytes"])
        result["MCKERNEL_OS_MACHINE_RESERVE_GIB"] = str(SHARED_MEMORY_RESERVE_GIB)
    return result
