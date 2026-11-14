import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

PACKET = (
    Path(__file__).parents[2]
    / "docs/verification/evidence/native-exact-retained-candidate-dce800af-evidence-cleanup-20260930.py"
)
SPEC = importlib.util.spec_from_file_location("packet", PACKET)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_packet_is_pinned_and_inert():
    text = PACKET.read_text()
    assert MODULE.CANDIDATE_COMMIT in text
    assert "mckernel-exact-candidate-dce800af-scratch-5" in text
    assert MODULE.CANDIDATE_IDENTITY in text
    assert "candidate root identity differs" in text
    assert "wrong candidate commit" in text
    assert "evidence ancestor missing or linked" in text
    assert "--apply" in text
    assert "os.unlink" in text
    assert "final target revalidation failed" in text
    assert "rmtree" not in text


def test_audit_rejects_disposable_root():
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "docs/verification/evidence").mkdir(parents=True)
        (repo / "docs/verification/evidence/x").write_bytes(b"good")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
             "commit", "-qm", "x"], check=True
        )
        commit = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"]
        ).decode().strip()
        with pytest.raises(SystemExit, match="wrong candidate root"):
            MODULE.audit(repo, repo, commit)


def test_apply_rejects_injected_target_before_unlink(monkeypatch, tmp_path):
    expected = {
        "schema": "mckernel.exact-evidence-cleanup.v1",
        "status": "AUDIT_PASS",
        "candidate_commit": MODULE.CANDIDATE_COMMIT,
        "candidate_root": str(MODULE.CANDIDATE_ROOT),
        "candidate_identity": MODULE.CANDIDATE_IDENTITY,
        "targets": [],
        "recovery": "restore each restore_git_path from blob at candidate_commit",
    }
    injected = json.loads(json.dumps(expected))
    injected["targets"].append({"path": str(tmp_path / "outside")})
    monkeypatch.setattr(MODULE, "root_guard", lambda *args: None)
    monkeypatch.setattr(MODULE, "audit", lambda *args: expected)
    called = []
    monkeypatch.setattr(MODULE.os, "unlink", lambda path: called.append(path))
    with pytest.raises(SystemExit, match="audit plan differs"):
        MODULE.apply(injected)
    assert called == []


def test_apply_requires_audit_status(monkeypatch):
    monkeypatch.setattr(MODULE, "root_guard", lambda *args: None)
    with pytest.raises(SystemExit, match="invalid audit plan"):
        MODULE.apply(
            {"schema": "mckernel.exact-evidence-cleanup.v1", "status": "APPLY_PASS"}
        )


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
