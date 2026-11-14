import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

PACKET = Path(__file__).parents[2] / "docs/verification/evidence/native-exact-retained-candidate-43e9-evidence-cleanup-20260930.py"
SPEC = importlib.util.spec_from_file_location("packet_43e9", PACKET)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_packet_is_pinned_and_inert():
    text = PACKET.read_text()
    assert MODULE.CANDIDATE_COMMIT in text
    assert MODULE.CANDIDATE_IDENTITY in text
    assert "mckernel-exact-candidate-43e9dbbd-scratch-5" in text
    assert "--apply" in text and "os.unlink" in text
    assert "final target revalidation failed" in text
    assert "rmtree" not in text


def test_disposable_root_rejected():
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory) / "repo"
        repo.mkdir()
        with pytest.raises(SystemExit, match="wrong candidate root"):
            MODULE.root_guard(repo, repo, MODULE.CANDIDATE_COMMIT)


def test_apply_rejects_injected_target_before_unlink(monkeypatch, tmp_path):
    expected = {"schema": "mckernel.exact-evidence-cleanup.v1", "status": "AUDIT_PASS",
                "candidate_commit": MODULE.CANDIDATE_COMMIT, "candidate_root": str(MODULE.CANDIDATE_ROOT),
                "candidate_identity": MODULE.CANDIDATE_IDENTITY, "targets": [],
                "recovery": "restore each restore_git_path from blob at candidate_commit"}
    injected = json.loads(json.dumps(expected))
    injected["targets"].append({"path": str(tmp_path / "outside")})
    monkeypatch.setattr(MODULE, "root_guard", lambda *args: None)
    monkeypatch.setattr(MODULE, "audit", lambda *args: expected)
    called = []
    monkeypatch.setattr(MODULE.os, "unlink", lambda path: called.append(path))
    with pytest.raises(SystemExit, match="audit plan differs"):
        MODULE.apply(injected)
    assert called == []


def test_wrong_commit_and_symlinked_ancestor_rejected(tmp_path):
    with pytest.raises(SystemExit, match="wrong candidate commit"):
        MODULE.root_guard(MODULE.CANDIDATE_ROOT, Path(__file__).parents[2], "0" * 40)
    outside = tmp_path / "outside"
    (outside / "verification/evidence").mkdir(parents=True)
    root = tmp_path / "candidate"
    root.mkdir()
    (root / "docs").symlink_to(outside)
    with pytest.raises(SystemExit, match="evidence ancestor missing or linked"):
        MODULE.evidence_base(root)
