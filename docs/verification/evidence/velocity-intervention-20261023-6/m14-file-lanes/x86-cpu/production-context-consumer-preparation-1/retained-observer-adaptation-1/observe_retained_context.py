"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Retained-only d21c observer, prepared without execution. No subprocess or object hashing.
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

def observe_retained(execution, durable_objects):
    """execution is ROOT-authored actual evidence, not a synthesized launch.
    Required: ready_sha256, source_identity, commands (actual11 exact argv),
    preflight_source_headers_verified and postflight_source_headers_verified.
    The root wholejoin must bind execution itself and its actual capture cohort.
    """
    ready_path = ROOT / "PRODUCTION-CONTEXT-CONSUMER-READY.json"
    assert hashed_small(ready_path)["sha256"] == "d21c285b22d0b3375c21fb504ffa89c4afd931ab339ddc9f20dc3485267f864d"
    ready = json.loads(ready_path.read_bytes())
    rust = load_bound(ready["Rust_recipe"])
    c = load_bound(ready["C_recipe"])
    oracle = load_bound(ready["exact_symbol_oracle"])
    assert execution["ready_sha256"] == hashed_small(ready_path)["sha256"]
    assert execution["source_identity"] == rust["source_identity"] == ready["source_identity"]
    assert execution["preflight_source_headers_verified"] is True
    assert execution["postflight_source_headers_verified"] is True
    assert len(execution["commands"]) == len(ready["commands"]) == 11
    for actual, frozen in zip(execution["commands"], ready["commands"]):
        assert actual["argv"] == frozen["argv"], frozen["label"]
    assert set(durable_objects) == {"mckernel_rust.o", "cpu.c.o", "cpu-rust-partial.o"}
    for row in durable_objects.values():
        stable_object(row)
        assert len(row["sha256"]) == 64
    cap = ROOT / "root-owned-exact11-1"
    results, texts, identities = [], [], []
    for i in range(11):
        p = cap / str(i)
        j = json.loads((p/"RESULT.json").read_bytes())
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
