import importlib.util, json, os
from pathlib import Path
import pytest

SRC = Path(__file__).parents[2] / "docs/verification/evidence/native-exact-retained-candidate-6fed3a10-source-evidence-audit-20261001.py"
spec = importlib.util.spec_from_file_location("audit_6fed", SRC)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_bindings_and_plan_contract():
    assert m.COMMIT == "6fed3a1022db0b4f9828dd42a8bd8f88fc052053"
    assert m.IDENTITY == "1831:3169097"
    assert m.IHK_COMMIT == "3114d9e7101ad52030eb3effa849a5c108972a1f"
    assert m.EXCLUSION_IDENTITY == "1831:90679"
    assert any("exportset-25" in str(p) for p in m.PROTECTED)
    assert any("scratch-12" in str(p) for p in m.PROTECTED)

def test_no_census_or_mutation_dispatch():
    text = SRC.read_text()
    for token in ("--census", "CENSUS_PASS", "subprocess.run", "os.unlink", "os.remove", "os.rmdir", "p.unlink", "p.rmdir"):
        assert token not in text
    assert "--plan" in text and "os.link" in text

def fixture(tmp_path):
    root = tmp_path / "root"; evidence = root / "docs/verification/evidence"; evidence.mkdir(parents=True)
    exact = evidence / "exact.json"; exact.write_bytes(b"exact")
    exact2 = evidence / "exact2.json"; exact2.write_bytes(b"exact")
    different = evidence / "different.json"; different.write_bytes(b"changed")
    os.link(exact, evidence / "hard.json")
    (evidence / "link.json").symlink_to(exact)
    return root, evidence, exact, exact2, different

def test_disposable_audit_filters_and_emits_explicit_anchors(tmp_path, monkeypatch):
    root, evidence, exact, exact2, different = fixture(tmp_path)
    monkeypatch.setattr(m, "ROOT", root); monkeypatch.setattr(m, "EVIDENCE", evidence); monkeypatch.setattr(m, "ANCHORS", (root, evidence))
    monkeypatch.setattr(m, "PROTECTED", ())
    monkeypatch.setattr(m, "guard", lambda: None)
    monkeypatch.setattr(m, "protected_inventory", lambda: [])
    monkeypatch.setattr(m, "git_blob", lambda p: b"exact" if p.endswith(("exact.json", "exact2.json")) else b"other" if p.endswith("different.json") else None)
    monkeypatch.setattr(m, "git", lambda *a: "blob")
    out = m.audit()
    assert set(out) == {"anchor_inventory", "candidate_commit", "candidate_identity", "candidate_root", "nested_delta_preserved", "preserved", "protected_inventory", "protected_paths", "schema", "status", "targets"}
    assert [Path(x["path"]).name for x in out["targets"]] == ["exact2.json"]
    assert [Path(x["path"]).name for x in out["preserved"]] == ["different.json"]
    assert [x["path"] for x in out["anchor_inventory"]] == [str(root), str(evidence)]

def test_protected_regular_and_symlink_fifo_refusal(tmp_path, monkeypatch):
    regular = tmp_path / "regular"; regular.write_bytes(b"protected")
    monkeypatch.setattr(m, "PROTECTED", (regular,))
    assert m.protected_inventory()[0]["sha256"] == m.digest(b"protected")
    hard = tmp_path / "hard"; os.link(regular, hard)
    monkeypatch.setattr(m, "PROTECTED", (regular,))
    assert m.protected_inventory()[0]["nlink"] == 2
    root = tmp_path / "root"; root.mkdir(); link = root / "linked"; link.symlink_to(tmp_path, target_is_directory=True)
    monkeypatch.setattr(m, "PROTECTED", (link,))
    with pytest.raises(SystemExit): m.protected_inventory()
    fifo = tmp_path / "fifo"; os.mkfifo(fifo)
    with pytest.raises(SystemExit): m.read_checked(str(fifo))

def test_link_count_drift_fails_closed(tmp_path):
    p = tmp_path / "read"; p.write_bytes(b"before"); old_hash = m.hash_fd
    def add_link(fd):
        os.link(p, tmp_path / "new-link"); return old_hash(fd)
    m.hash_fd = add_link
    try:
        with pytest.raises(SystemExit): m.read_checked(str(p), require_nlink1=False)
    finally: m.hash_fd = old_hash

def test_read_replacement_and_parent_replacement_fail_closed(tmp_path):
    p = tmp_path / "read"; p.write_bytes(b"before"); expected = m.metadata(m.inspect_entry(p)); old_hash = m.hash_fd
    def replace(fd):
        os.utime(p, ns=(expected["mtime_ns"] + 1, expected["mtime_ns"] + 1)); return old_hash(fd)
    m.hash_fd = replace
    try:
        with pytest.raises(SystemExit): m.read_checked(str(p), expected)
    finally: m.hash_fd = old_hash
    parent = tmp_path / "parent"; parent.mkdir(); child = parent / "child"; child.write_bytes(b"x")
    def replace_parent(fd):
        parent.rename(tmp_path / "moved"); parent.mkdir(); return old_hash(fd)
    m.hash_fd = replace_parent
    try:
        with pytest.raises(SystemExit): m.read_checked(str(child))
    finally: m.hash_fd = old_hash

def test_durable_no_replace_and_short_write(tmp_path, monkeypatch):
    p = tmp_path / "plan"; m.publish(p, {"status":"AUDIT_PASS"})
    with pytest.raises(SystemExit): m.publish(p, {"status":"AUDIT_PASS"})
    q = tmp_path / "short"; real = os.write; monkeypatch.setattr(m.os, "write", lambda fd, data: real(fd, data[:1]))
    m.publish(q, {"x":"y"}); assert json.loads(q.read_text())["x"] == "y"

def test_plan_row_and_lock_contract():
    text = SRC.read_text()
    for token in ("mtime_ns", "sha256", "allocated_bytes", "dev", "ino", "nlink", "protected_inventory", "anchor_inventory", "GIT_OPTIONAL_LOCKS", "mckernel.exact-git-source-audit.v1"):
        assert token in text
