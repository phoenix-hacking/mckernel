"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Retained-only d21c stack2MiB correction observer, prepared without execution. No subprocess or object hashing.
Root supplies actual launch/source bindings and already-durable object metadata.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import stat

ROOT = Path(__file__).resolve().parent.parent
TARGET = "x86_context_line_log_bridge"

def hashed_small(path):
    path = Path(path)
    data = path.read_bytes()
    assert len(data) < 4 << 20, str(path)
    return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}

def load_bound(row):
    p = Path(row["path"])
    assert hashed_small(p)["sha256"] == row["sha256"], str(p)
    return json.loads(p.read_bytes())

def stable_object(row):
    # The durable SHA was taken by root before postprocessing. Do not hash again.
    p = Path(row["path"])
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        s = os.fstat(fd)
        assert stat.S_ISREG(s.st_mode)
        for key, attr in (("device","st_dev"),("inode","st_ino"),("uid","st_uid"),
                          ("gid","st_gid"),("nlink","st_nlink"),("size","st_size"),
                          ("mtime_ns","st_mtime_ns"),("ctime_ns","st_ctime_ns")):
            assert row[key] == getattr(s, attr), (str(p), key)
        assert row["mode"] == oct(stat.S_IMODE(s.st_mode))
        assert p.lstat() == s
    finally:
        os.close(fd)

def rows(text):
    return [line.split() for line in text.splitlines() if line.split()]

def unique(rs, name, kinds):
    found = [r for r in rs if r[-1] == name]
    assert len(found) == 1 and found[0][-2] in kinds, (name, found)
    return found[0]

def elf_global_func(text, name, defined):
    found = []
    for line in text.splitlines():
        r = line.split()
        if len(r) >= 8 and r[0].endswith(":") and r[7] == name:
            found.append(r)
    assert len(found) == 1, (name, found)
    r = found[0]
    assert r[3] == "FUNC" and r[4] == "GLOBAL", r
    assert (r[6] != "UND") == defined, r

def observe_retained():
    """Read only ROOT's corrected actual cohort and its sealed metadata.
    No first-cohort output is reused as a corrected-profile observation.
    This function does not launch a process, rehash an object, or write a receipt.
    """
    ready_path = ROOT / "PRODUCTION-CONTEXT-CONSUMER-READY.json"
    assert hashed_small(ready_path)["sha256"] == "d21c285b22d0b3375c21fb504ffa89c4afd931ab339ddc9f20dc3485267f864d"
    ready = json.loads(ready_path.read_bytes())
    rust = load_bound(ready["Rust_recipe"])
    c = load_bound(ready["C_recipe"])
    oracle = load_bound(ready["exact_symbol_oracle"])
    cap = ROOT / "root-owned-exact11-stack2m-correction-1"
    root_record = json.loads((cap/"ACTUAL-WHOLE-JOIN.json").read_bytes())
    profile = load_bound(root_record["profile"])
    commands = load_bound(root_record["commands"])
    assert root_record["CPU6_released"] is True
    assert root_record["ready_sha256"] == hashed_small(ready_path)["sha256"]
    assert root_record["source_identity"] == rust["source_identity"] == ready["source_identity"]
    assert profile["original_ready_sha256"] == root_record["ready_sha256"]
    assert profile["source_identity"] == root_record["source_identity"]
    for key, value in {"AS": 2<<30, "CPU": [6], "CPU_seconds": 60,
                       "FSIZE": 32<<20, "NOFILE": 256, "core": 0,
                       "RUST_MIN_STACK": "2097152", "stack": 2<<20,
                       "wall_seconds": 90, "grace": 6}.items():
        assert profile[key] == value, (key, profile.get(key))
    assert len(commands) == len(ready["commands"]) == 11
    old_output, new_output = str(ROOT/"output-1"), str(ROOT/"output-stack2m-1")
    for actual, frozen in zip(commands, ready["commands"]):
        assert actual["label"] == frozen["label"]
        assert actual["argv"] == [arg.replace(old_output,new_output) for arg in frozen["argv"]], frozen["label"]
    # Check frozen private source/header/witness bytes, never historical canonical
    # bytes which may legitimately advance in another implementation lane.
    assert len(rust["source_inputs"]) == 78 and len(c["actual_header_closure"]) == 56
    source_rows = [v["private"] for v in rust["source_inputs"].values()]
    source_rows += list(c["actual_header_closure"].values())
    source_rows += [c["private_source"], c["ABI_witness"], c["selected_declaration_source"]]
    for row in source_rows:
        fact = hashed_small(row["path"])
        assert fact["sha256"] == row["sha256"], row["path"]
        assert fact["bytes"] == row["bytes"], row["path"]
    durable_objects = {Path(row["path"]).name: row for row in root_record["objects"]}
    assert set(durable_objects) == {"mckernel_rust.o", "cpu.c.o", "cpu-rust-partial.o"}
    for row in durable_objects.values():
        stable_object(row)
        assert len(row["sha256"]) == 64
    results, texts, identities = [], [], []
    for i in range(11):
        p = cap / str(i)
        command = json.loads((p/"command.json").read_bytes())
        assert command["argv"] == commands[i]["argv"]
        assert command["label"] == commands[i]["label"]
        assert command["profile"] == root_record["profile"]
        j = json.loads((p/"RESULT.json").read_bytes())
        assert j == root_record["results"][i]
        assert j["returncode"] == 0 and not j["timed_out"], i
        assert j["direct_child_joined"] and j["group_absent"] and j["closed_streams"], i
        assert j["error"] is None and j["retirement_error"] is None, i
        assert not j["remaining_group_members"] and not j["unexpected_group_members"], i
        for stream in ("stdout", "stderr"):
            actual = hashed_small(p/stream)
            assert actual["sha256"] == j["captures"][stream]["sha256"], (i, stream)
            assert actual["bytes"] == j["captures"][stream]["size"], (i, stream)
        results.append(j)
        texts.append((p/"stdout").read_text())
        identities.append(hashed_small(p/"RESULT.json"))
    rn = rows(texts[1])
    ts = {r[-1] for r in rn if r[-2] == "T"}
    us = {r[-1] for r in rn if r[-2] == "U"}
    assert ts == set(oracle["expected_T"]) and len(ts) == 3047
    assert us == set(oracle["expected_U"]) and len(us) == 583
    for name in oracle["all_prior_T"]:
        unique(rn, name, {"T"})
    unique(rn, TARGET, {"T"})
    for name in (TARGET, "x86_cpu_ulong_log_bridge", "kprintf", "__kprintf"):
        elf_global_func(texts[2], name, True)
    assert not re.search(r"\bvoid\s+x86_context_line_log_bridge\s*\([^;{}]*\)\s*\{", texts[3])
    cn = rows(texts[6])
    unique(cn, TARGET, {"U"})
    for name in c["preserved_C_providers"]:
        unique(cn, name, {"T"})
    data = unique(cn, c["expected_data"]["name"], {c["expected_data"]["kind"]})
    assert int(data[-3], 16) == c["expected_data"]["size"] == 4
    caller = unique(cn, "ihk_mc_print_user_context", {"T"})
    low, size = int(caller[-4],16), int(caller[-3],16)
    section, target_relocs = "", []
    for line in texts[7].splitlines():
        if line.startswith("Relocation section "):
            section = line
        if TARGET in line and ".rela.text" in section:
            offset = int(line.split()[0],16)
            assert low <= offset < low+size, (caller,line)
            target_relocs.append(line)
    assert len(target_relocs) == c["expected_named_target_text_relocations"] == 1
    # Undefined C ELF symbol is NOTYPE, so its kind is checked by actual NM above.
    pn = rows(texts[10])
    for name in oracle["expected_T"] + c["preserved_C_providers"]:
        unique(pn, name, {"T"})
    for name in c["expected_partial_unique_T"]:
        unique(pn, name, {"T"})
    assert not any(r[-1] == TARGET and r[-2] == "U" for r in pn)
    data = unique(pn, "no_turbo", {"D"})
    assert int(data[-3],16) == 4
    for row in durable_objects.values():
        stable_object(row)
    return {
        "scope": __doc__.splitlines()[0],
        "status": "PASS_ACTUAL_CURRENT78_RUST_AND_SELECTED_COMPLETE_GCC9_CONTEXT_CONSUMER_ONLY",
        "root_wholejoin": hashed_small(cap/"ACTUAL-WHOLE-JOIN.json"),
        "actual_profile": root_record["profile"],
        "actual_commands": root_record["commands"],
        "explicit_RLIMIT_STACK_2MiB_and_RUST_MIN_STACK_2MiB": True,
        "original_8MiB_cohort_preserved_not_profile_accepted": True,
        "source_identity": rust["source_identity"],
        "private_source78_headers56_and_ABI_bytes_verified": True,
        "result_bindings": identities, "actual_results": results,
        "durable_objects_not_rehashed": durable_objects,
        "Rust_T_count": len(ts), "Rust_U_count": len(us),
        "all3046prior_Rust_T_preserved": True,
        "new_Rust_T": [TARGET], "removed_Rust_U": [TARGET], "added_Rust_U": [],
        "actual_C_target_text_relocations": target_relocs,
        "actual_C_caller": "ihk_mc_print_user_context",
        "real_header_ABI_command4_passed": True,
        "remaining_C_outerlock_and_other_callbacks_explicit_debt": True,
        "commands_replayed": 0, "objects_rehashed": 0,
        "canonical_writes": 0, "default_GCC14_finalkernel_native": False,
        "stack_NMI_interrupt_exit_included": False,
    }
