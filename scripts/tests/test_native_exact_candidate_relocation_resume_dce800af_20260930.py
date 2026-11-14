import ast
import os
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).parents[2]
PACKET = ROOT / "docs/verification/evidence/native-exact-candidate-relocation-resume-dce800af-20260930.sh"

def source(): return PACKET.read_text()

def helpers():
    lines = source().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("import ctypes,datetime"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "def main():")
    tree = ast.parse("\n".join(lines[start:end]))
    wanted = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    wanted += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"under", "inventory", "equal", "durable", "safe_remove", "privileged_references", "rename_noreplace", "require_hash"}]
    ns = {"__name__": "fixture"}; exec(compile(ast.Module(body=wanted, type_ignores=[]), "resume-fixture", "exec"), ns); return ns

def test_packet_and_bindings_are_fail_closed():
    subprocess.run(["/usr/bin/bash", "-n", str(PACKET)], check=True)
    text = source()
    for needle in ("resume-dce800af-13", "557425", "1831", "66306", "native-exact-candidate-relocation-dce800af-20260930-intent.json", "native-exact-candidate-operational-exclusion-relocation-dce800af-12.json", "native-exact-candidate-relocation-dce800af-20260930.log", "0a98a1ea5c62bd80999fb73bdc1ab8b7a107f629d387933535b84dd2a39480a1", "RESUME_PACKET_SHA256", "RESUME_TEST_SHA256", "release-not-fetched", "release-blob-binding", "local-byte-binding", "privileged-reference-census-failed", "insufficient-capacity-floor", "RESUME_OLD_INTENT_PATH", "rsync-verification", "temporary-mutated-during-resume", "rename_noreplace(TMP,DEST,parent)", "source-mount-before-delete", "ancestor-changed-before-delete", "safe_remove(C,SRC_DEV", "VERIFIED_DESTINATION_DELETION_START", "PARTIAL_DELETION_FAILURE", "POST_RENAME_FAILURE", "docker-census-failed"):
        assert needle in text
    assert "mckernel-exact-candidate-preparation-scratch-20260929-1.sh" not in text
    assert "rsync -aHAX" not in text
    assert "rm -rf" not in text and "shutil.rmtree" not in text

def test_cross_filesystem_directory_sizes_are_ignored_but_regulars_are_not():
    h = helpers()
    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a"; b = Path(td) / "b"; a.mkdir(); b.mkdir()
        (a / "nested").mkdir(); (b / "nested").mkdir()
        (a / "nested" / "x").write_bytes(b"same"); (b / "nested" / "x").write_bytes(b"same")
        ai, bi = h["inventory"](a), h["inventory"](b)
        ai[0]["size"] += 4096; ai[1]["size"] += 8192
        assert h["equal"](ai, bi)
        next(x for x in ai if x["path"] == "nested/x")["size"] += 1
        assert not h["equal"](ai, bi)

def test_existing_temp_hardlinks_symlinks_and_safe_delete():
    h = helpers()
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "src"; tmp = Path(td) / "tmp"; src.mkdir(); tmp.mkdir()
        (src / "x").write_bytes(b"x"); os.link(src / "x", src / "alias"); (src / "link").symlink_to("x")
        (tmp / "x").write_bytes(b"x"); os.link(tmp / "x", tmp / "alias"); (tmp / "link").symlink_to("x")
        assert h["equal"](h["inventory"](src), h["inventory"](tmp))
        ino, dev = os.stat(src).st_ino, os.stat(src).st_dev; h["safe_remove"](src, dev, ino); assert not src.exists()

def test_sequence_checks_and_no_new_copy_allocation():
    text = source()
    assert text.index("privileged_references([C,TMP,DEST])") < text.index("src=inventory(C,SRC_DEV)") < text.index("rsync-verification") < text.index("rename_noreplace(TMP,DEST,parent)") < text.index("durable(DELETE_INTENT") < text.index("safe_remove(C,SRC_DEV")
    assert "if pathlib.Path(DEST).exists()" in text and "active-build-or-guest" in text and "active-lease" in text and "12*1024**3" in text and "16*1024**3" in text
    assert "O_CREAT|os.O_EXCL|os.O_NOFOLLOW" in text
    assert "durable(INTENT" in text
    assert "tree-changed-before-delete" in text
    assert "os.fsync(pfd)" in text

def test_reference_census_skips_absent_and_rejects_auth_failure():
    h=helpers()
    with tempfile.TemporaryDirectory() as td:
        missing=str(Path(td)/"missing")
        with mock.patch.object(h["subprocess"],"run") as run:
            assert h["privileged_references"]([missing]) == []
            run.assert_not_called()
        clean=SimpleNamespace(returncode=1,stdout="",stderr="")
        with mock.patch.object(h["subprocess"],"run",return_value=clean):
            assert h["privileged_references"]([td]) == []
        failed=SimpleNamespace(returncode=1,stdout="",stderr="sudo: authentication failed\n")
        with mock.patch.object(h["subprocess"],"run",return_value=failed):
            try: h["privileged_references"]([td])
            except RuntimeError as exc: assert str(exc)=="privileged-reference-census-failed"
            else: raise AssertionError("privilege failure accepted")

def test_local_byte_binding_rejects_mutation():
    h=helpers()
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"packet"; p.write_bytes(b"reviewed")
        import hashlib
        expected=hashlib.sha256(b"reviewed").hexdigest()
        h["require_hash"](p,expected)
        p.write_bytes(b"mutated")
        try: h["require_hash"](p,expected)
        except RuntimeError as exc: assert str(exc)=="local-byte-binding"
        else: raise AssertionError("mutated local packet accepted")
