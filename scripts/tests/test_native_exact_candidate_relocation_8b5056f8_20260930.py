import ast
import os
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).parents[2]
PACKET = ROOT / "docs/verification/evidence/native-exact-candidate-relocation-8b5056f8-scratch6-20260930.sh"


def source():
    return PACKET.read_text()


def helpers():
    lines = source().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("import ctypes, datetime, fcntl"))
    end = next(i for i in range(start, len(lines)) if lines[i] == "def main():")
    tree = ast.parse("\n".join(lines[start:end]))
    wanted = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))]
    wanted += [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {"durable", "under", "inventory", "equal_inventory", "mount_points", "proc_references", "privileged_references", "validate_historical_leases", "safe_remove"}]
    ns = {"__name__": "fixture", "SRC_DEV": 1831}
    exec(compile(ast.Module(body=wanted, type_ignores=[]), "relocation-fixture", "exec"), ns)
    return ns


def test_packet_is_bash_valid_and_all_frozen_inputs_are_bound():
    subprocess.run(["/usr/bin/bash", "-n", str(PACKET)], check=True)
    text = source()
    for value in (
        "8b5056f836ecd3e6916625696750c4dfadbaaf9f",
        "3114d9e7101ad52030eb3effa849a5c108972a1f",
        "63b16c48f230deb4273bee8bc361f1cbfa222b49",
        "9e3e757596190f2d023a0fe372cdefff86d20df2af488a84c25593194979cd08",
        "RELOCATION_ARCHIVE_SHA256",
        "e7ec55b2c263e2c9afd94a1f7c99ed96576a0f069ec7d1d91ec21ac41c2d5f4a",
        "dd243ae0f14025bccafeab21654478780f102ddc64668770820d79b5a0379b95",
        "4f3f3ec96b1366cdbac384ff70d54f0576f99308a33ad7986dc804ca5f8511ee",
        "cbaaec7b649608674747e4d88acdd1f0a005cff6ff696046b8d96ed959af49e7",
        "7abb77fdc3049a54caebc3344de14c41e779502b4abcb7f301de4a647e15bf77",
        "91fe5688f3282c1617a75f08c4b435a793200f2cf9beafe432cef7ad3ca0bd4c",
        "1831",
        "66306",
    ):
        assert value in text
    prep_path = "docs/verification/evidence/native-exact-candidate-preparation-scratch-20260930-6.sh"
    assert text.count(prep_path) == 2
    assert "native-exact-candidate-preparation-scratch-20260930-7.sh" not in text
    assert "native-exact-build-failure-8b5056f8-scratch-6-20260930.tar" in text
    assert "native-exact-build-failure-8b5056f8-scratch-6-20260930-1.tar" not in text
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
    for needle in ("destination-exists", "source-mount-before-delete", "active-process-reference", "privileged-reference-census-failed", "/usr/bin/lsof", "active-build-or-guest", "active-docker", "active-lease", "native-exact-build-lease-*.json", "/run/mckernel-build.lock", "insufficient-host-capacity", "emergency_reserve", "exclusion", "os.O_EXCL", "rename_noreplace(tmp,DEST,DEST_PARENT)", "safe_remove(C,SRC_DEV,src_ino)", "scratch_free_bytes_before", "host_free_bytes_after", "RELOCATION_TEST_SHA256", "preparation-binding", "DELETE_INTENT", "VERIFIED_DESTINATION_DELETION_START", "PARTIAL_DELETION_FAILURE", "rsync-verification"):
        assert needle in text
    assert "rm -rf" not in text and "shutil.rmtree" not in text


def test_packet_never_replaces_existing_exclusion_or_destination():
    text = source()
    assert "native-exact-candidate-operational-exclusion-objtoolbinding-11.json" in text
    assert "native-exact-candidate-operational-exclusion-relocation-8b5056f8-13.json" in text
    assert "scratch6-20260930-retry1.log" in text
    assert "retry1-terminal.json" in text
    assert '"$BUILD_EXCLUSION_SHA"' in text
    assert "os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW" in text
    assert "if pathlib.Path(DEST).exists() or pathlib.Path(DEST).is_symlink()" in text
    assert "durable(INTENT" in text
    assert "durable(DELETE_INTENT" in text
    assert text.count("durable(TERMINAL") == 2  # mutually exclusive failure or final PASS
    assert "fsync_tree(tmp)" in text


def test_absent_fixed_lease_paths_are_filtered_before_privileged_read():
    text = source()
    assert "lease_paths=[p for p in lease_paths if os.path.lexists(p)]" in text
    assert "lease-read-failed:'+str(path)+':rc='+str(r.returncode)" in text


def test_distinct_deletion_intent_and_terminal_success_sequence():
    h = helpers()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "source"; root.mkdir(); (root / "payload").write_bytes(b"x")
        outside = Path(td) / "outside"; outside.write_bytes(b"preserved")
        (root / "internal-link").symlink_to("payload")
        (root / "external-link").symlink_to(outside)
        delete_intent = Path(td) / "delete-intent.json"
        terminal = Path(td) / "terminal.json"
        h["durable"](delete_intent, b'{"status":"VERIFIED_DESTINATION_DELETION_START"}\n')
        h["safe_remove"](root, os.stat(root).st_dev, os.stat(root).st_ino)
        h["durable"](terminal, b'{"status":"PASS"}\n')
        assert delete_intent.exists() and terminal.exists() and not root.exists() and outside.read_bytes() == b"preserved"


def test_privileged_reference_census_distinguishes_clean_from_tool_failure():
    h = helpers()
    with tempfile.TemporaryDirectory() as td:
        clean = SimpleNamespace(returncode=1, stdout="", stderr="")
        with mock.patch.object(h["subprocess"], "run", return_value=clean):
            assert h["privileged_references"]([td]) == []
        auth_failure = SimpleNamespace(returncode=1, stdout="", stderr="sudo: authentication failed\n")
        with mock.patch.object(h["subprocess"], "run", return_value=auth_failure):
            try:
                h["privileged_references"]([td])
            except RuntimeError as exc:
                assert str(exc) == "privileged-reference-census-failed"
            else:
                raise AssertionError("sudo/lsof failure was accepted as a clean census")


def test_historical_lease_tombstones_require_terminal_or_reused_owner():
    h = helpers()
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); proc = root / "proc"; lease = root / "lease.json"
        boot = "c733d83b-a5ae-4f91-9ce6-9f8ccf119afd"
        def row(pid=123, start=77, **extra):
            value = {"schema":"mckernel.retirement-build-owner-exclusion.v2", "state":"retirement-owned-immutable-one-shot-tombstone", "boot_id":boot, "filesystem_device":1831, "operational_exclusion":str(lease), "pid":pid, "starttime":start, "release_sha256":"a"*64}
            value.update(extra); return value
        def write(value): lease.write_text(__import__("json").dumps(value))
        # Absent owner is terminal and accepted.
        reader = lambda path: Path(path).read_text()
        write(row()); h["validate_historical_leases"]([lease], boot, proc_root=proc, reader=reader)
        # Reused PID has a different starttime and is accepted.
        stat = proc / "123" / "stat"; stat.parent.mkdir(parents=True); stat.write_text("1 (reused) " + " ".join(["S"] + ["0"]*18 + ["78"]))
        h["validate_historical_leases"]([lease], boot, proc_root=proc, reader=reader)
        # Same PID/starttime is live and rejected.
        stat.write_text("1 (live) " + " ".join(["S"] + ["0"]*18 + ["77"]))
        try: h["validate_historical_leases"]([lease], boot, proc_root=proc, reader=reader)
        except RuntimeError as exc: assert str(exc) == "active-lease-owner"
        else: raise AssertionError("live lease owner accepted")
        lease.write_text("not-json")
        try: h["validate_historical_leases"]([lease], boot, proc_root=proc, reader=reader)
        except RuntimeError as exc: assert str(exc) == "malformed-lease"
        else: raise AssertionError("malformed lease accepted")
