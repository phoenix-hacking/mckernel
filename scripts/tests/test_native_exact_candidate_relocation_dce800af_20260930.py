import ast
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).parents[2]
PACKET = ROOT / "docs/verification/evidence/native-exact-candidate-relocation-dce800af-20260930.sh"


def source():
    return PACKET.read_text()


def helpers():
    lines = source().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("import ctypes, datetime, fcntl"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "def main():")
    tree = ast.parse("\n".join(lines[start:end]))
    wanted = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    wanted += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"durable", "under", "inventory", "equal_inventory", "mount_points", "proc_references", "safe_remove"}]
    ns = {"__name__": "fixture"}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), "relocation-fixture", "exec"), ns)
    return ns


def test_packet_is_bash_valid_and_all_frozen_inputs_are_bound():
    subprocess.run(["/usr/bin/bash", "-n", str(PACKET)], check=True)
    text = source()
    for value in (
        "dce800af8c19d014ef509e102ca4f4b1c473e2ab",
        "3114d9e7101ad52030eb3effa849a5c108972a1f",
        "b13f7065cc16bff1608a6f3d89ff65870400c3c6",
        "ce4715d7c9178ffebdf780251a1fcba70642d7e46b9d5d44e132466b916bc867",
        "f8522be9649def629b04a93d065f3ab79a5c7acdd7a2f2f221b7d759384c5952",
        "c334449c9d1081911a0de951a3b130b4b06de24414da5755801687407698a996",
        "2788c195965f7a12f92f1463065f70074ce48f2875d406fce2cfa293c6c9dcd9",
        "ef89d2384f417e02c4ae41192726ac76601376e189f0325e1932384add02c7c6",
        "cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7",
        "7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77",
        "91fe5688f3282c1617a75f08c4b435a793200f2cf9beafe432cef7ad3ca0bd4c",
        "1831",
        "66306",
    ):
        assert value in text
    prep_path = "docs/verification/evidence/native-exact-candidate-preparation-scratch-20260930-5.sh"
    assert text.count(prep_path) == 2
    assert "native-exact-candidate-preparation-scratch-20260929-1.sh" not in text


def test_happy_copy_verify_rename_delete_and_hardlinks():
    h = helpers()
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "source"
        base.mkdir(); (base / "d").mkdir(); (base / "d" / "payload").write_bytes(b"x")
        os.link(base / "d" / "payload", base / "alias")
        inv = h["inventory"](base)
        tmp = Path(td) / "tmp"; tmp.mkdir()
        subprocess.run(["/usr/bin/rsync", "-aHAX", "--numeric-ids", "--one-file-system", "--links", "--", str(base) + "/", str(tmp) + "/"], check=True)
        assert h["equal_inventory"](inv, h["inventory"](tmp))
        final = Path(td) / "final"; os.rename(tmp, final)
        assert h["equal_inventory"](inv, h["inventory"](final))
        ino = os.stat(final).st_ino; h["safe_remove"](final, os.stat(final).st_dev, ino)
        assert not final.exists()


def test_tamper_and_unsafe_symlink_fail_closed():
    h = helpers()
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "src"; src.mkdir(); (src / "x").write_bytes(b"good")
        dst = Path(td) / "dst"; shutil.copytree(src, dst); expected = h["inventory"](src)
        (dst / "x").write_bytes(b"tampered")
        assert not h["equal_inventory"](expected, h["inventory"](dst))
        bad = Path(td) / "bad"; bad.mkdir(); (bad / "escape").symlink_to("/etc/passwd")
        try:
            h["inventory"](bad)
        except RuntimeError as exc:
            assert str(exc) == "unsafe-symlink"
        else:
            raise AssertionError("unsafe symlink accepted")


def test_mount_process_existing_destination_and_exclusion_guards_are_present():
    h = helpers()
    assert h["mount_points"]("1 2 0:1 / /candidate rw - tmpfs tmpfs rw\n", "/candidate")
    with tempfile.TemporaryDirectory() as td:
        proc = Path(td) / "proc"; (proc / "123" / "fd").mkdir(parents=True)
        (proc / "123" / "fd" / "0").symlink_to("/candidate/file")
        (proc / "123" / "cwd").symlink_to("/candidate")
        (proc / "123" / "maps").write_text("unrelated mapping")
        assert h["proc_references"](proc, ["/candidate"])
        (proc / "124").mkdir()
        (proc / "124" / "maps").write_text("7f00-7f10 r--p 00000000 00:00 0 /candidate/mapped (deleted)\n")
        assert str(proc / "124") in h["proc_references"](proc, ["/candidate"])
    text = source()
    for needle in ("destination-exists", "source-mount-before-delete", "active-process-reference", "privileged-reference-census-failed", "/usr/bin/lsof", "active-build-or-guest", "active-docker", "active-lease", "insufficient-host-capacity", "emergency_reserve", "exclusion", "os.O_EXCL", "rename_noreplace(tmp,DEST,DEST_PARENT)", "safe_remove(C,SRC_DEV,src_ino)", "scratch_free_bytes_before", "host_free_bytes_after", "RELOCATION_TEST_SHA256", "preparation-binding", "DELETE_INTENT", "VERIFIED_DESTINATION_DELETION_START", "PARTIAL_DELETION_FAILURE", "rsync-verification"):
        assert needle in text
    assert "rm -rf" not in text and "shutil.rmtree" not in text


def test_packet_never_replaces_existing_exclusion_or_destination():
    text = source()
    assert "native-exact-candidate-operational-exclusion-lifecyclebinding-10.json" in text
    assert "native-exact-candidate-operational-exclusion-relocation-dce800af-12.json" in text
    assert '"$BUILD_EXCLUSION_SHA"' in text
    assert "os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW" in text
    assert "if pathlib.Path(DEST).exists() or pathlib.Path(DEST).is_symlink()" in text
    assert "durable(INTENT" in text
    assert "durable(DELETE_INTENT" in text
    assert text.count("durable(TERMINAL") == 2  # mutually exclusive failure or final PASS
    assert "fsync_tree(tmp)" in text


def test_distinct_deletion_intent_and_terminal_success_sequence():
    h = helpers()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "source"; root.mkdir(); (root / "payload").write_bytes(b"x")
        delete_intent = Path(td) / "delete-intent.json"
        terminal = Path(td) / "terminal.json"
        h["durable"](delete_intent, b'{"status":"VERIFIED_DESTINATION_DELETION_START"}\n')
        h["safe_remove"](root, os.stat(root).st_dev, os.stat(root).st_ino)
        h["durable"](terminal, b'{"status":"PASS"}\n')
        assert delete_intent.exists() and terminal.exists() and not root.exists()
