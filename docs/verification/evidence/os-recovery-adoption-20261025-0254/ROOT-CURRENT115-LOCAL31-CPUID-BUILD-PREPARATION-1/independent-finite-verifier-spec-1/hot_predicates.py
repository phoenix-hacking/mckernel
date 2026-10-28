"""Functional McKernel OS/apps and Rust migration only; no security testing.

Review-local pure predicate specification, not an execution/review authority.
The source owner may adapt its data names, preserving every predicate. Only the
independent reviewer invokes an adopted utility for a real independent decision.
This module performs no imports of producer code, file IO, queries or writes.
"""
import math


def need(condition, message):
    if not condition:
        raise ValueError(message)


def triplet(values):
    need(type(values) in (list, tuple) and len(values) == 3, "three clocks")
    need(all(type(v) in (int, float) and math.isfinite(v) and v > 0
             for v in values), "finite positive clocks")
    return list(values)


def hot_predicates(cold, grant, resource, ready, bootstrap, root_input,
                   physical_envelope, profile, request_adoption, export,
                   ledger, publication, now_clocks):
    """All arguments are exact-ref-authenticated complete JSON objects.

    `cold` is derived from genuine final Root static inputs before the clock.
    It pins every static ref and the actual nonce, never an old packet value.
    The caller also authenticates the complete-capture marker, file identities,
    exact pending SHA, all referenced small files, and absent launch paths.
    """
    nonce = cold["nonce"]
    need(grant["author"] == "/root" and grant["decision"] ==
         "GRANT_ONE_CURRENT290_BUILD_ONLY", "exact Root grant kind")
    need(type(grant["maximum_invocations"]) is int and
         grant["maximum_invocations"] == 1 and grant["review"] is None and
         grant["root_docker_client_only"] is True, "one unreviewed build only")
    for key in ("runner", "worker", "profile", "input_export_authority",
                "native_custody_clearance", "fresh_output_root",
                "docker_client_prefix"):
        need(grant[key] == cold[key], "cold grant binding " + key)
    need(grant["nonce"] == resource["nonce"] == ready["nonce"] ==
         bootstrap["nonce"] == profile["actual_nonce"] == nonce,
         "exact nonce across all actual subjects")
    need(root_input["author"] == "/root" and
         root_input["actual_reservations_attested"] is True and
         root_input["root_attests_only_intervening_holder_preparation"] is True,
         "Root actual reservations and custody continuity")
    need(type(root_input["maximum_invocations"]) is int and
         root_input["maximum_invocations"] == 1 and
         root_input["nonce"] == nonce, "Root input exact one nonce")
    for input_key, cold_key in (("profile", "profile"),
            ("runner", "runner"), ("worker", "worker"),
            ("input_export_authority", "input_export_authority"),
            ("native_custody_clearance", "native_custody_clearance"),
            ("nonce_ledger", "nonce_ledger"),
            ("current_boundary", "current_boundary"),
            ("source_publication", "source_publication")):
        need(root_input[input_key] == cold[cold_key],
             "Root input cold binding " + input_key)
    need(root_input["request_sha256"] == profile["request_sha256"] ==
         export["request_sha256"] == request_adoption["request_sha256"] ==
         cold["request_sha256"], "same exact adopted source request")
    need(request_adoption["profile"] == cold["profile"] and
         request_adoption["current_physical_clearance"] ==
         cold["native_custody_clearance"], "adoption profile/custody")
    holder = resource["reservation_holder"]
    need(holder == ready["holder"] and holder["device"] == 27 and
         holder["inode"] == 4 and holder["fd"] == 3 and
         type(holder["pid"]) is int and holder["pid"] > 1 and
         type(holder["starttime"]) is int and holder["starttime"] > 0,
         "actual same permanent mutex holder/birth/FD")
    need(bootstrap["author"] == "/root" and
         bootstrap["decision"] == "GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER"
         and type(bootstrap["maximum_invocations"]) is int and
         bootstrap["maximum_invocations"] == 1,
         "Root sole holder-only bootstrap")
    for key in ("runner", "worker", "profile", "native_custody_clearance"):
        need(bootstrap[key] == cold[key], "holder bootstrap " + key)
    need(resource["heavy_slots_held"] == 1 and
         resource["other_heavy_slots"] == 0 and
         resource["reservation_owner"] == nonce and
         resource["cpu_reservation_held"] is True and
         resource["native_custody_unchanged"] is True and
         resource["native_custody_clearance"] == cold["native_custody_clearance"],
         "one held slot and unchanged accepted native custody")
    need(resource["cpus"] == profile["CPU"] == [2, 3, 4, 5] and
         resource["container_memory_bytes"] == profile["memory_bytes"] ==
         12884901888 and resource["container_pids"] == profile["pids"] == 512,
         "original 4CPU/12GiB/512 task reservation")
    for key in ("other_reserved_memory_bytes", "other_reserved_pids",
                "aggregate_pid_budget"):
        need(resource[key] == root_input[key] == cold[key],
             "Root actual other reservation " + key)
    need(resource["container_memory_bytes"] +
         resource["other_reserved_memory_bytes"] <=
         resource["aggregate_memory_budget_bytes"] ==
         profile["aggregate_memory_budget_bytes"] == 23259332608,
         "aggregate 21.6619GiB remains one shared budget")
    need(resource["container_pids"] + resource["other_reserved_pids"] <=
         resource["aggregate_pid_budget"], "shared task reservation")
    observed = resource["actual_observations"]
    need(observed["memory"]["MemAvailable"] >= 24 * 2**30,
         "existing strict memory headroom")
    need(observed["capacity"]["host"] >= resource["host_required_free_bytes"]
         >= 16 * 2**30 and observed["capacity"]["scratch"] >=
         resource["scratch_required_free_bytes"] >= 14091616256,
         "original HOST/scratch floors and packet growth")
    cgroup = observed["cgroups"]
    expected = {
        "/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_period_us": "100000",
        "/sys/fs/cgroup/cpu/mckernel-dev/cpu.cfs_quota_us": "400000",
        "/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes": "12884901888",
        "/sys/fs/cgroup/pids/mckernel-dev/pids.max": "512",
        "/sys/fs/cgroup/pids/mckernel-dev/pids.current": "0",
    }
    need(cgroup == expected, "exact actual cgroup/cpu/memory/tasks/occupancy")
    docker = observed["no_running_containers"]
    need(docker["returncode"] == 0 and docker["stdout"] ==
         docker["stderr"] == "", "no actual running container")
    target_rows = []
    for line in observed["lock_rows"].splitlines():
        words = line.split()
        if len(words) >= 8 and words[5] == "00:1b:4":
            target_rows.append(words)
    need(len(target_rows) == 1 and target_rows[0][1:4] ==
         ["FLOCK", "ADVISORY", "WRITE"] and
         target_rows[0][4] == str(holder["pid"]) and
         target_rows[0][6:8] == ["0", "EOF"], "sole exact holder full-EOF flock")
    physical = physical_envelope["physical"]
    need(physical["boot_id"] == "7bfc5687-6c04-4d15-84eb-b92ab9a55dcb"
         and physical["no_existing_heavy"] is True and
         physical["pids_current"] == 0 and
         physical["active_shared_records_absent"] is True,
         "fresh original current physical predicates")
    need(physical["root_ledger35"] == cold["nonce_ledger"] and
         physical["actual_latest_operation_postjoin_acceptance"] ==
         cold["native_custody_clearance"], "physical latest ledger/current free")
    need(ledger == cold["ledger_data"] and
         ledger["latest_accepted_free_boundary"] == cold["native_custody_clearance"]
         and nonce not in ledger["consumed_nonces"] +
         ledger["reserved_abandoned_unconsumed_nonces"], "unchanged current ledger")
    need(publication == cold["publication_data"] and
         profile == cold["profile_data"] and export == cold["export_data"],
         "immutable cold static subjects")
    need(physical_envelope["observed_clocks"][0] <= root_input["at_epoch"] <=
         resource["observed_at_epoch"], "preholder then actual held capture")
    ceilings = [min(v) for v in zip(triplet(profile["fixed_three_clock_cutoffs"]),
        triplet(physical["fixed_cutoffs"]), triplet(cold["authorized_clamps"]))]
    need(all(a < b for a, b in zip(triplet(resource["observed_clocks"]), ceilings))
         and all(a < b for a, b in zip(triplet(now_clocks), ceilings)),
         "all original earliest UTC/MONO/BOOT clamps")
    age = now_clocks[0] - resource["observed_at_epoch"]
    need(0 <= age <= 120, "actual held resource <= original120 seconds")
    return {"holder": holder, "resource_age_seconds": age,
            "effective_fixed_three_clock_cutoffs": ceilings}
