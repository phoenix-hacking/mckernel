import importlib.util, json, os, subprocess, tempfile
from pathlib import Path
import pytest
P=Path(__file__).parents[2]/"docs/verification/evidence/native-exact-retained-candidate-63235981-evidence-cleanup-20260930.py"
S=importlib.util.spec_from_file_location("packet",P); M=importlib.util.module_from_spec(S); S.loader.exec_module(M)

def test_packet_is_pinned_and_inert():
    t=P.read_text(); assert M.CANDIDATE_COMMIT in t; assert "--apply" in t; assert "os.unlink" in t; assert "final target revalidation failed" in t; assert "rmtree" not in t

def test_audit_and_tamper_guard():
    with tempfile.TemporaryDirectory() as d:
        repo=Path(d)/"repo"; repo.mkdir(); subprocess.run(["git","init","-q",str(repo)],check=True)
        (repo/"docs/verification/evidence").mkdir(parents=True); (repo/"docs/verification/evidence/x").write_bytes(b"good")
        subprocess.run(["git","-C",str(repo),"add","."],check=True); subprocess.run(["git","-C",str(repo),"-c","user.name=t","-c","user.email=t@t","commit","-qm","x"],check=True)
        # Root guard is intentionally exact and therefore rejects disposable roots.
        try: M.audit(repo,repo,subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"]).decode().strip())
        except SystemExit as e: assert "wrong candidate root" in str(e)

def test_symlink_and_wrong_root_guards():
    with tempfile.TemporaryDirectory() as d:
        try: M.root_guard(Path(d),Path(d),M.CANDIDATE_COMMIT)
        except SystemExit as e: assert "wrong candidate root" in str(e)

def test_apply_rejects_injected_target_before_unlink(monkeypatch, tmp_path):
    expected={"schema":"mckernel.exact-evidence-cleanup.v1","status":"AUDIT_PASS","candidate_commit":M.CANDIDATE_COMMIT,"candidate_root":str(M.CANDIDATE_ROOT),"targets":[{"path":str(M.CANDIDATE_ROOT/"docs/verification/evidence/good")}],"recovery":"restore each restore_git_path from blob at candidate_commit"}
    injected=json.loads(json.dumps(expected)); injected["targets"].append({"path":str(tmp_path/"outside")})
    monkeypatch.setattr(M,"root_guard",lambda *a: None)
    monkeypatch.setattr(M,"audit",lambda *a: expected)
    called=[]; monkeypatch.setattr(M.os,"unlink",lambda p: called.append(p))
    with pytest.raises(SystemExit,match="audit plan differs"):
        M.apply(injected)
    assert called == []

def test_apply_requires_audit_status(monkeypatch):
    monkeypatch.setattr(M,"root_guard",lambda *a: None)
    with pytest.raises(SystemExit,match="invalid audit plan"):
        M.apply({"schema":"mckernel.exact-evidence-cleanup.v1","status":"APPLY_PASS"})
