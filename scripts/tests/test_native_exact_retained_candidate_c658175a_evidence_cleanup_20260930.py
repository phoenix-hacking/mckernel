import importlib.util
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
    assert '"sudo","-A","lsof"' in text
    assert '"findmnt"' in text and '"docker","ps","-a"' in text
    assert 'os.replace' not in text
    assert 'os.link(tmp,path)' in text
    assert 'os.fsync(d)' in text
