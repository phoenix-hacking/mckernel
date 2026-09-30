import importlib.util
import os
from pathlib import Path
import tempfile
import pytest

PACKET = Path(__file__).parents[2]/"docs/verification/evidence/native-exact-retained-candidate-c658175a-evidence-cleanup-20260930.py"
spec=importlib.util.spec_from_file_location("c658_cleanup",PACKET); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

def test_frozen_identity_scope_and_live_inputs():
    text=PACKET.read_text()
    assert M.CANDIDATE_COMMIT == "c658175ae1831e2caef6ecf59730a272f1324645"
    assert M.CANDIDATE_IDENTITY == "66306:47753167"
    assert "native-exact-build-evidence-c658175a-scratch-7-retry1" in text
    assert "native-exact-build-output-c658175a-scratch-7-retry1" in text
    assert "LIVE_FAILURE" in text and "live_failure_untouched" in text
    assert '"docker_all"' in text and '"mount_device"' in text and '"open_processes"' in text
    assert '"lease_exclusion_paths"' in text
    assert "rmtree" not in text

def test_wrong_root_and_identity_fail_closed(tmp_path):
    with pytest.raises(SystemExit,match="wrong candidate root"):
        M.root_guard(tmp_path, tmp_path, M.CANDIDATE_COMMIT)

def test_live_overlap_is_rejected(monkeypatch,tmp_path):
    root=tmp_path/"root"; root.mkdir()
    monkeypatch.setattr(M,"LIVE_FAILURE",root/"failure.json")
    with pytest.raises(SystemExit,match="overlaps live"):
        M.live_guard(root)

def test_default_cli_is_audit_only_and_does_not_write_plan():
    text=PACKET.read_text()
    assert "if a.write_plan: atomic_write(a.plan,result)" in text
    assert "if a.apply" in text
    assert "os.unlink" not in text.split("def audit",1)[1].split("def atomic_write",1)[0]

def test_preserves_mismatches_and_untracked_content_by_design():
    text=PACKET.read_text()
    assert 'content-or-size-differs-from-pinned-Git-blob' in text
    assert 'not-present-in-pinned-Git-commit' in text
    assert 'preserved' in text

def test_safety_census_is_read_only_commands():
    text=PACKET.read_text()
    assert '"sudo","-A","lsof","-nP","-w"' in text
    assert '"findmnt"' in text and '"docker","ps","-a"' in text
    assert 'os.replace' not in text
    assert 'os.link(tmp,path)' in text
    assert 'os.fsync(d)' in text

def good_census():
    return {"open_processes":{"returncode":1,"output":"","stderr":""},
            "mount_device":{"returncode":0,"output":"SOURCE FSTYPE MAJ:MIN TARGET\n/dev/nvme0n1p2 ext4 259:2 /\n","stderr":""},
            "docker_all":{"returncode":0,"output":"","stderr":""},"lease_exclusion_paths":[]}

@pytest.mark.parametrize("field,value", [
    ("open_processes", {"returncode":2,"output":"","stderr":"permission denied"}),
    ("mount_device", {"returncode":0,"output":"SOURCE FSTYPE MAJ:MIN TARGET\n/dev/other ext4 1:2 /\n","stderr":""}),
    ("docker_all", {"returncode":1,"output":"","stderr":"permission denied"}),
])
def test_each_safety_census_failure_blocks(field,value):
    c=good_census(); c[field]=value
    with pytest.raises(SystemExit): M.validate_census(c)

def self_starttime():
    text=Path('/proc/self/stat').read_text()
    return text.rsplit(')',1)[1].split()[19]

def test_relevant_running_container_rejected():
    c=good_census(); c['docker_all']['output']='{"Names":"mckernel-exact-fixture","State":"running","Mounts":"/home/holden/mckernel-work/scratch/x"}\n'
    with pytest.raises(SystemExit,match='running container'): M.validate_census(c)

def test_active_nonprotected_owner_rejected(tmp_path):
    c=good_census(); p=tmp_path/'lease.json'; p.write_text('{}')
    c['lease_exclusion_paths']=[{"path":str(p),"owner_record":{"pid":str(os.getpid()),"starttime":self_starttime()}}]
    with pytest.raises(SystemExit,match='active owner exclusion'): M.validate_census(c)

def test_nested_mount_rejected():
    c=good_census(); c['mount_device']['output']='SOURCE FSTYPE MAJ:MIN TARGET\n/dev/nvme0n1p2 ext4 259:2 /\n/dev/loop0 ext4 7:0 /nested\n'
    with pytest.raises(SystemExit,match='nested mount'): M.validate_census(c)

def test_protected_disjoint_live_exclusion_owner_allowed(tmp_path):
    c=good_census(); p=M.PROTECTED_LIVE_EXCLUSION
    c['lease_exclusion_paths']=[{"path":str(p),"owner_record":{"pid":str(os.getpid()),"starttime":self_starttime()}}]
    M.validate_census(c)

def test_active_lsof_reference_rejected():
    c=good_census(); c['open_processes']={"returncode":0,"output":"COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\nworker 42 holden cwd DIR 1831 4096 1 /candidate\n","stderr":""}
    with pytest.raises(SystemExit,match='lsof reported'): M.validate_census(c)

def test_lsof_warning_or_error_stderr_is_not_ignored():
    c=good_census(); c['open_processes']={"returncode":1,"output":"","stderr":"lsof: WARNING: inaccessible FUSE mount\n"}
    with pytest.raises(SystemExit,match='lsof census error'): M.validate_census(c)
    c['open_processes']={"returncode":0,"output":"COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME\n","stderr":""}
    M.validate_census(c)

def make_apply_fixture(tmp_path):
    p=tmp_path/'duplicate'; p.write_bytes(b'exact')
    st=p.stat(); row={"path":str(p),"restore_git_path":"docs/verification/evidence/x","blob":"a"*40,"mode":st.st_mode & 0o7777,"mtime_ns":st.st_mtime_ns,"size":st.st_size,"sha256":M.sha(p.read_bytes()),"allocated_bytes":st.st_blocks*512,"dev":st.st_dev,"ino":st.st_ino}
    base=tmp_path
    plan={"schema":"mckernel.exact-evidence-cleanup.v1","status":"AUDIT_PASS","candidate_commit":M.CANDIDATE_COMMIT,"candidate_root":str(M.CANDIDATE_ROOT),"candidate_identity":M.CANDIDATE_IDENTITY,"targets":[row],"preserved":[],"safety_census":good_census(),"recovery":"r","live_failure_untouched":"f","live_build_inputs_untouched":["e"]}
    return p,plan,base

def test_apply_allows_only_dynamic_census_drift(monkeypatch,tmp_path):
    p,plan,base=make_apply_fixture(tmp_path); fresh=dict(plan); fresh["safety_census"]={**good_census(),"docker_all":{"returncode":0,"output":"different","stderr":""}}
    monkeypatch.setattr(M,"root_guard",lambda *args:None); monkeypatch.setattr(M,"evidence_base",lambda *args:(base,base)); monkeypatch.setattr(M,"audit",lambda *args:fresh)
    M.apply(plan); assert not p.exists() and "fresh_safety_census" in plan

@pytest.mark.parametrize("change", ["targets","preserved","candidate_root"])
def test_apply_rejects_stable_binding_drift(monkeypatch,tmp_path,change):
    p,plan,base=make_apply_fixture(tmp_path); fresh=dict(plan); fresh["safety_census"]=good_census()
    if change=="targets": fresh["targets"]=[]
    elif change=="preserved": fresh["preserved"]=[{"path":"x"}]
    else: fresh["candidate_root"]="/changed"
    monkeypatch.setattr(M,"root_guard",lambda *args:None); monkeypatch.setattr(M,"evidence_base",lambda *args:(base,base)); monkeypatch.setattr(M,"audit",lambda *args:fresh)
    with pytest.raises(SystemExit,match="audit plan differs"): M.apply(plan)
    assert p.exists()

def test_apply_rejects_fresh_census_failure(monkeypatch,tmp_path):
    p,plan,base=make_apply_fixture(tmp_path)
    monkeypatch.setattr(M,"root_guard",lambda *args:None); monkeypatch.setattr(M,"audit",lambda *args: (_ for _ in ()).throw(SystemExit("FAIL_CLOSED: census")))
    with pytest.raises(SystemExit,match="census"): M.apply(plan)
    assert p.exists()
