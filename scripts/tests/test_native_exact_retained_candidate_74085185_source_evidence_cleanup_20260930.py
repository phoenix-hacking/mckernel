#!/usr/bin/env python3
import importlib.util, json, os, stat, tempfile
from pathlib import Path
import pytest

SRC = Path(__file__).parents[2]/"docs/verification/evidence/native-exact-retained-candidate-74085185-source-evidence-cleanup-20260930.py"
spec = importlib.util.spec_from_file_location("cleanup740", SRC); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

def census_ok():
    inspect={"Id":"80e172a592939e2c30ca87a5bc3b9356467876f8ca1716b4ccf718320593eb22","Name":"/mckernel-exact-d60382667e3d4c1f89a61850e5a1ba59","State":{"Status":"exited","Running":False,"Pid":0,"ExitCode":1,"OOMKilled":False}}
    return {"open_processes":{"returncode":1,"output":"","stderr":""}, "mount_device":{"returncode":0,"output":"SOURCE FSTYPE MAJ:MIN TARGET\n/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch\n"}, "docker_all":{"returncode":0,"output":""}, "docker_inspect":{"returncode":0,"output":json.dumps(inspect)+"\n"}}

def test_pins_candidate_identity_and_commit():
    assert mod.CANDIDATE_COMMIT == "740851854b53036d4834dfb86a5fc7fb0f3954e6"
    assert mod.CANDIDATE_IDENTITY == "1831:3932163"
    assert str(mod.CANDIDATE_ROOT).endswith("mckernel-exact-candidate-74085185-scratch-3")

def test_protected_file_modes_match_live_bindings():
    assert mod.EXPECTED_FILES[mod.REQUEST][3] == 0o644
    assert mod.EXPECTED_FILES[mod.INPUTS][3] == 0o644
    assert mod.EXPECTED_FILES[mod.PREP_TERM][3] == 0o644
    assert mod.EXPECTED_FILES[mod.PREP_LOG][3] == 0o600

def test_census_accepts_empty_lsof_and_exact_scratch_mount(): mod.validate_census(census_ok())

@pytest.mark.parametrize("bad", [
    {"returncode":2,"output":"","stderr":""},
    {"returncode":1,"output":"COMMAND PID\npython 7\n","stderr":""},
    {"returncode":1,"output":"","stderr":"warning"},
])
def test_census_rejects_lsof_failure_reference_or_error(bad):
    c=census_ok(); c["open_processes"]=bad
    with pytest.raises(SystemExit): mod.validate_census(c)

def test_census_rejects_nested_or_wrong_device():
    c=census_ok(); c["mount_device"]["output"]="SOURCE FSTYPE MAJ:MIN TARGET\n/dev/nvme0n1p2 ext4 259:2 /\n"
    with pytest.raises(SystemExit): mod.validate_census(c)

def test_census_rejects_relevant_running_container():
    c=census_ok(); c["docker_all"]["output"] = json.dumps({"State":"running","Names":"mckernel-exact-foo","Mounts":"/home/holden/mckernel-work"})
    with pytest.raises(SystemExit): mod.validate_census(c)

def test_census_rejects_docker_error():
    c=census_ok(); c["docker_all"]["returncode"]=125
    with pytest.raises(SystemExit): mod.validate_census(c)

@pytest.mark.parametrize("change", [
    {"Running":True}, {"Pid":12}, {"ExitCode":0}, {"OOMKilled":True},
])
def test_census_rejects_container_state_drift(change):
    c=census_ok(); obj=json.loads(c["docker_inspect"]["output"]); obj["State"].update(change); c["docker_inspect"]["output"]=json.dumps(obj)
    with pytest.raises(SystemExit): mod.validate_census(c)

def test_census_rejects_missing_container_inspect():
    c=census_ok(); c["docker_inspect"]={"returncode":1,"output":"","stderr":"missing"}
    with pytest.raises(SystemExit): mod.validate_census(c)

def test_binding_guard_rejects_missing_lease(monkeypatch):
    monkeypatch.setattr(mod, "EXPECTED_FILES", {}); monkeypatch.setattr(mod, "EXPECTED_DIRS", {}); monkeypatch.setattr(mod, "LEASE", Path(tempfile.mkdtemp())/"lease")
    mod.validate_bindings()

def test_binding_guard_rejects_lease_presence(monkeypatch, tmp_path):
    monkeypatch.setattr(mod, "EXPECTED_FILES", {}); monkeypatch.setattr(mod, "EXPECTED_DIRS", {}); lease=tmp_path/"lease"; lease.write_text("x"); monkeypatch.setattr(mod, "LEASE", lease)
    with pytest.raises(SystemExit): mod.validate_bindings()

def test_durable_write_uses_no_replace_and_is_readable(tmp_path):
    p=tmp_path/"plan.json"; mod.durable_write(p,{"status":"AUDIT_PASS"})
    assert json.loads(p.read_text())["status"] == "AUDIT_PASS"
    with pytest.raises(SystemExit): mod.durable_write(p,{"status":"other"})

def test_durable_write_preserves_existing_destination(tmp_path):
    p=tmp_path/"plan.json"; p.write_text("old\n")
    with pytest.raises(SystemExit): mod.durable_write(p,{"new":True})
    assert p.read_text()=="old\n"

def test_row_records_git_restore_and_allocation(tmp_path, monkeypatch):
    base=tmp_path/"evidence"; base.mkdir(); f=base/"x"; f.write_bytes(b"abc")
    monkeypatch.setattr(mod, "git", lambda *args: "a"*40)
    r=mod.row(f,base,mod.REPO,mod.CANDIDATE_COMMIT)
    assert r["restore_git_path"]=="docs/verification/evidence/x"
    assert r["allocated_bytes"] == f.stat().st_blocks*512 and r["nlink"] == 1

def test_apply_rejects_non_audit_schema():
    with pytest.raises(SystemExit): mod.apply({"schema":"wrong","status":"AUDIT_PASS"})

def test_apply_rejects_target_replacement(tmp_path, monkeypatch):
    target=tmp_path/"x"; target.write_bytes(b"new")
    plan={"schema":"mckernel.exact-git-source-cleanup.v1","status":"AUDIT_PASS","candidate_root":str(mod.CANDIDATE_ROOT),"candidate_commit":mod.CANDIDATE_COMMIT,"targets":[{"path":str(target),"dev":target.stat().st_dev,"ino":target.stat().st_ino+1,"size":3,"mode":stat.S_IMODE(target.stat().st_mode),"sha256":"bad"}]}
    monkeypatch.setattr(mod,"root_guard",lambda *a,**k: None); monkeypatch.setattr(mod,"audit",lambda *a,**k: plan.copy()); monkeypatch.setattr(mod,"evidence_base",lambda *a:(tmp_path,tmp_path))
    with pytest.raises(SystemExit): mod.apply(plan)
    assert target.exists()

def test_packet_is_audit_only_by_default():
    text=SRC.read_text(); assert "--apply" in text and "container_removal" in text and "p.unlink()" in text
