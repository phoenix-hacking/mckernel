import importlib.util
import os
from pathlib import Path
import pytest

PACKET=Path(__file__).parents[2]/'docs/verification/evidence/native-exact-retained-candidate-f021bdee-scratch8-evidence-cleanup-20260930.py'
spec=importlib.util.spec_from_file_location('f021_cleanup',PACKET); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)

def test_frozen_f021_identity_and_protected_inputs():
    text=PACKET.read_text()
    assert M.CANDIDATE_COMMIT=='f021bdee206944fc9c68a3f1f2e0f6683a849435'
    assert M.CANDIDATE_IDENTITY=='1831:5242921'
    assert len(M.LIVE_PATHS)==9
    assert M.PROTECTED_CONTAINER['state']=='exited'
    assert M.PROTECTED_CONTAINER['exit_code']==1
    assert 'native-exact-build-output-f021bdee-scratch-8' in text
    assert 'native-exact-build-evidence-f021bdee-scratch-8' in text
    assert 'native-exact-candidate-operational-exclusion-selfdigest-13.json' in text
    assert 'BASE.atomic_write' in text and '--apply' in text

def test_live_guard_rejects_overlap(tmp_path):
    root=tmp_path/'root'; root.mkdir()
    M.LIVE_PATHS.append(root/'protected')
    try:
        with pytest.raises(SystemExit,match='overlaps protected'):
            M.live_guard(root)
    finally: M.LIVE_PATHS.pop()

def test_live_guard_rejects_linked_protected_input(tmp_path):
    root=tmp_path/'root'; root.mkdir(); outside=tmp_path/'outside'; outside.write_text('x')
    linked=root/'protected'; linked.symlink_to(outside); M.LIVE_PATHS.append(linked)
    try:
        with pytest.raises(SystemExit,match='linked'):
            M.live_guard(root)
    finally: M.LIVE_PATHS.pop()

def test_no_heavy_execution_in_packet():
    text=PACKET.read_text().lower()
    assert 'docker' not in text and 'qemu' not in text
    assert 'subprocess.run' not in text

def census_mount(output):
    return {"open_processes":{"returncode":1,"output":"","stderr":""},"mount_device":{"returncode":0,"output":output,"stderr":""},"docker_all":{"returncode":0,"output":"","stderr":""},"lease_exclusion_paths":[]}

def test_exact_scratch_mount_allowed():
    M.validate_census(census_mount('SOURCE FSTYPE MAJ:MIN TARGET\n/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch\n'))

def test_wrong_or_nested_mount_rejected():
    with pytest.raises(SystemExit,match='nested mount'):
        M.validate_census(census_mount('SOURCE FSTYPE MAJ:MIN TARGET\n/dev/nvme0n1p2 ext4 259:2 /\n'))
    with pytest.raises(SystemExit,match='nested mount'):
        M.validate_census(census_mount('SOURCE FSTYPE MAJ:MIN TARGET\n/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch\n/dev/loop40 ext4 7:40 /nested\n'))

def test_audit_adapter_rejects_wrong_binding():
    with pytest.raises(SystemExit,match='wrong f021 audit binding'):
        M.audit(M.CANDIDATE_ROOT,M.REPO,'0'*40)

def test_base_apply_integration_has_no_signature_typeerror(monkeypatch,tmp_path):
    target=tmp_path/'exact'; target.write_bytes(b'x'); st=target.stat()
    row={"path":str(target),"restore_git_path":"docs/verification/evidence/x","blob":"a"*40,"mode":st.st_mode&0o7777,"mtime_ns":st.st_mtime_ns,"size":1,"sha256":M.BASE.sha(b'x'),"allocated_bytes":st.st_blocks*512,"dev":st.st_dev,"ino":st.st_ino}
    plan={"schema":"mckernel.exact-evidence-cleanup.v1","status":"AUDIT_PASS","candidate_commit":M.CANDIDATE_COMMIT,"candidate_root":str(M.CANDIDATE_ROOT),"candidate_identity":M.CANDIDATE_IDENTITY,"targets":[row],"preserved":[],"safety_census":census_mount('SOURCE FSTYPE MAJ:MIN TARGET\n/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch\n'),"recovery":"r","live_failure_untouched":"f","live_build_inputs_untouched":[],"protected_f021_runtime":{"paths":[str(p) for p in M.LIVE_PATHS],"container":M.PROTECTED_CONTAINER}}
    fresh=dict(plan); fresh['safety_census']=plan['safety_census']
    monkeypatch.setattr(M.BASE,'root_guard',lambda *args:None); monkeypatch.setattr(M.BASE,'evidence_base',lambda *args:(tmp_path,tmp_path)); monkeypatch.setattr(M,'_BASE_AUDIT',lambda root,repo,commit:fresh)
    M.BASE.apply(plan)
    assert not target.exists()
