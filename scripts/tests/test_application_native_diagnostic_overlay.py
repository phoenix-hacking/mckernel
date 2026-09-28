"""Real newc bytes and filesystem operations; no extraction/backend mocks."""
import contextlib
import gzip
import hashlib
import importlib.util
import io
import os
import stat
import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("overlay", ROOT / "scripts/application-tests/native_diagnostic_overlay.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def member(name, data=b"", mode=0o100755, **changes):
    """Independent tiny newc fixture producer, including CRC format controls."""
    values = dict(ino=17, mode=mode, uid=0, gid=0, nlink=1, mtime=0,
                  filesize=len(data), devmajor=0, devminor=0, rdevmajor=0,
                  rdevminor=0, namesize=len(name.encode()) + 1, check=0)
    magic = changes.pop("magic", b"070701")
    values.update(changes)
    raw = magic + ("%08x" * 13 % tuple(values.values())).encode()
    assert len(raw) == 110
    raw += name.encode() + b"\0"
    raw += bytes(-len(raw) % 4)
    raw += data
    raw += bytes(-len(raw) % 4)
    return raw


def archive(*members):
    return b"".join(members) + member("TRAILER!!!", mode=0)


def base_archive():
    raw = archive(member(".", mode=0o040755, nlink=2),
                  member("init", b"old-init"),
                  member("dev", mode=0o040755, nlink=2),
                  member("dev/console", mode=0o020600, rdevmajor=5, rdevminor=1),
                  member("dev/null", mode=0o020666, rdevmajor=1, rdevminor=3),
                  member("bin", mode=0o040755, nlink=2),
                  member("bin/sh", b"busybox", mode=0o120777),
                  member("bin/busybox", b"preserved bytes"))
    return raw + bytes(-len(raw) % 512)


def collector_elf(*, elf_type=2, machine=62, entry=0x400100, segments=None, **changes):
    """Synthetic static x86_64 exit(0) ELF, constructed without a compiler."""
    if segments is None:
        segments = [(1, 5, 0, 0x400000, 0, 512, 512, 4096)]
    values = dict(ident=b"\x7fELF\x02\x01\x01" + bytes(9), elf_type=elf_type,
                  machine=machine, version=1, entry=entry, phoff=64, shoff=0,
                  flags=0, ehsize=64, phentsize=56, phnum=len(segments),
                  shentsize=0, shnum=0, shstrndx=0)
    values.update(changes)
    data = bytearray(512)
    data[:64] = struct.pack("<16sHHIQQQIHHHHHH", *values.values())
    for i, segment in enumerate(segments):
        struct.pack_into("<IIQQQQQQ", data, 64 + 56 * i, *segment)
    data[256:265] = b"\x31\xff\xb8\x3c\x00\x00\x00\x0f\x05"
    return bytes(data)


@contextlib.contextmanager
def fixture(raw=None):
    raw = base_archive() if raw is None else raw
    compressed = gzip.compress(raw, mtime=0)
    constants = dict(BASE_SHA256=digest(compressed), BASE_SIZE=len(compressed),
                     BASE_CPIO_SHA256=digest(raw), BASE_CPIO_SIZE=len(raw),
                     PAYLOAD_SHA256=digest(b"payload"))
    with tempfile.TemporaryDirectory() as td, mock.patch.multiple(M, **constants):
        directory = Path(td)
        (directory / "base.gz").write_bytes(compressed)
        (directory / "app").write_bytes(b"payload")
        (directory / "collector").write_bytes(collector_elf())
        yield directory, raw


def build(directory, name="out.gz", **kwargs):
    kwargs.setdefault("collector_sha256", digest(collector_elf()))
    kwargs.setdefault("base_sha256", M.BASE_SHA256)
    kwargs.setdefault("base_size", M.BASE_SIZE)
    kwargs.setdefault("base_cpio_sha256", M.BASE_CPIO_SHA256)
    kwargs.setdefault("base_cpio_size", M.BASE_CPIO_SIZE)
    return M.build_overlay(directory / "base.gz", directory / "app",
                           directory / "collector", directory / name, **kwargs)


def overlay():
    return M._archive((("apps", b"", 0o040755), ("case", b"", 0o040755),
                       ("case/work", b"", 0o040755), ("init", b"collector", 0o100755),
                       ("apps/app", b"payload", 0o100755)))


class OverlayTests(unittest.TestCase):
    def test_exact_preserved_prefix_determinism_and_final_map(self):
        with fixture() as (d, raw):
            result = build(d)
            other = build(d, "other.gz")
            output = (d / "out.gz").read_bytes()
            self.assertEqual(output, (d / "other.gz").read_bytes())
            self.assertEqual(result["output_sha256"], other["output_sha256"])
            self.assertEqual(result["output_sha256"], digest(output))
            self.assertEqual(output[:10], b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff")
            unpacked = gzip.decompress(output)
            self.assertEqual(unpacked[:len(raw)], raw)
            appended, _ = M.parse_newc(unpacked[len(raw):])
            self.assertEqual([r["name"] for r in appended],
                             ["apps", "case", "case/work", "init", "apps/app"])
            self.assertEqual([r["mode"] for r in appended],
                             [0o040755, 0o040755, 0o040755, 0o100755, 0o100755])
            self.assertEqual(appended[3]["data"], (d / "collector").read_bytes())
            self.assertEqual(appended[4]["data"], b"payload")
            for record in appended:
                self.assertEqual((record["uid"], record["gid"], record["mtime"]), (0, 0, 0))
            self.assertEqual(result["final_map"]["bin/busybox"]["sha256"], digest(b"preserved bytes"))
            self.assertEqual(result["final_map"]["dev/console"]["rdevmajor"], 5)
            self.assertEqual(result["final_map"]["dev/null"]["rdevminor"], 3)
            self.assertEqual(result["base_cpio_sha256"], digest(raw))
            for name, filename in (("base", "base.gz"), ("payload", "app"), ("collector", "collector")):
                source = result["sources"][name]
                self.assertEqual(source["identity"], M._identity((d / filename).stat()))
                self.assertEqual(source["sha256"], digest((d / filename).read_bytes()))

    def test_independent_newc_header_layout(self):
        generated = M._newc("hello", b"bytes", 0o100755, ino=17)
        self.assertEqual(generated, member("hello", b"bytes"))
        self.assertEqual(M.parse_newc(archive(generated))[0][0]["data"], b"bytes")

    def test_multiple_base_archives_and_padding(self):
        first = archive(member("init", b"first"))
        second = archive(member("init", b"second"), member("keep", b"kept"))
        raw = first + bytes(-len(first) % 512) + second + b"\0" * 12
        with fixture(raw) as (d, original):
            result = build(d)
            self.assertEqual(gzip.decompress((d / "out.gz").read_bytes())[:len(raw)], original)
            self.assertEqual(result["final_map"]["keep"]["sha256"], digest(b"kept"))

    def test_checks_compressed_and_decompressed_identities(self):
        for key, value in (("base_sha256", "0" * 64), ("base_size", 1),
                           ("base_cpio_sha256", "0" * 64), ("base_cpio_size", 1)):
            with self.subTest(key=key), fixture() as (d, _):
                with self.assertRaises(M.OverlayError):
                    build(d, **{key: value})
                self.assertFalse((d / "out.gz").exists())

    def test_base_identity_binding_is_mandatory_and_strict(self):
        with fixture() as (d, _):
            for key, value in (("base_sha256", None), ("base_sha256", True),
                               ("base_size", True), ("base_size", "1"),
                               ("base_cpio_sha256", "x"), ("base_cpio_size", 0)):
                with self.subTest(key=key, value=value), self.assertRaises((M.OverlayError, TypeError)):
                    build(d, **{key: value})
                self.assertFalse((d / "out.gz").exists())

    def test_base_identity_size_ceiling_is_common_and_exact(self):
        with fixture() as (d, _):
            base = (d / "base.gz").read_bytes()
            identity = dict(base_sha256=digest(base), base_size=len(base),
                            base_cpio_sha256=digest(gzip.decompress(base)),
                            base_cpio_size=len(gzip.decompress(base)))
            for key, ceiling in (("base_size", M.MAX_SOURCE_SIZE),
                                 ("base_cpio_size", M.MAX_CPIO_SIZE)):
                with self.subTest(key=key):
                    self.assertRaises(M.OverlayError,
                                      lambda: build(d, **{**identity, key: ceiling + 1}))
                    self.assertRaises(M.OverlayError,
                                      lambda: M._authenticate_base(
                                          base, **{**identity, key: ceiling + 1}))
                    self.assertRaises(M.OverlayError,
                                      lambda: M.replay(base, overlay(),
                                                       **{**identity, key: ceiling + 1}))

    def test_changed_inputs_rejected(self):
        for name in ("base.gz", "app", "collector"):
            with self.subTest(name=name), fixture() as (d, _):
                expected = digest((d / "collector").read_bytes())
                (d / name).write_bytes(b"changed")
                with self.assertRaises(M.OverlayError):
                    build(d, collector_sha256=expected)
                self.assertFalse((d / "out.gz").exists())

    def test_source_mutation_during_compression(self):
        for name in ("base.gz", "app", "collector"):
            with self.subTest(name=name), fixture() as (d, _):
                original = M._gzip
                def mutate(data):
                    value = original(data)
                    (d / name).write_bytes(b"changed during compression")
                    return value
                with mock.patch.object(M, "_gzip", side_effect=mutate), self.assertRaisesRegex(M.OverlayError, "source identity changed"):
                    build(d)
                self.assertFalse((d / "out.gz").exists())

    def test_source_replacement_same_bytes(self):
        with fixture() as (d, _):
            original = M._gzip
            def replace(data):
                value = original(data)
                (d / "new").write_bytes((d / "app").read_bytes())
                os.replace(d / "new", d / "app")
                return value
            with mock.patch.object(M, "_gzip", side_effect=replace), self.assertRaisesRegex(M.OverlayError, "source identity changed"):
                build(d)

    def test_source_mutation_during_initial_read(self):
        with fixture() as (d, _):
            original = M._read_fd
            calls = 0
            def mutate(fd, *args):
                nonlocal calls
                result = original(fd, *args)
                calls += 1
                if calls == 1:
                    (d / "base.gz").write_bytes(b"raced")
                return result
            with mock.patch.object(M, "_read_fd", side_effect=mutate), self.assertRaisesRegex(M.OverlayError, "source identity changed"):
                build(d)

    def test_source_mutation_after_output_fsync(self):
        for directory_fsync in (False, True):
            with self.subTest(directory_fsync=directory_fsync), fixture() as (d, _):
                original = os.fsync
                def mutate(fd):
                    original(fd)
                    if stat.S_ISDIR(os.fstat(fd).st_mode) == directory_fsync:
                        (d / "collector").write_bytes(b"raced after fsync")
                with mock.patch.object(M.os, "fsync", side_effect=mutate), self.assertRaisesRegex(M.OverlayError, "source identity changed"):
                    build(d)
                self.assertTrue((d / "out.gz").exists())

    def test_reject_existing_output_and_aliases(self):
        for kind in ("file", "hardlink", "symlink", "dangling", "directory", "fifo"):
            with self.subTest(kind=kind), fixture() as (d, _):
                out = d / "out.gz"
                if kind == "file": out.write_bytes(b"existing")
                elif kind == "hardlink": os.link(d / "base.gz", out)
                elif kind == "symlink": out.symlink_to(d / "base.gz")
                elif kind == "dangling": out.symlink_to(d / "absent")
                elif kind == "directory": out.mkdir()
                else: os.mkfifo(out)
                with self.assertRaisesRegex(M.OverlayError, "output already exists"):
                    build(d)

    def test_output_source_same_path_and_source_alias(self):
        with fixture() as (d, _):
            with self.assertRaisesRegex(M.OverlayError, "output already exists"):
                build(d, "base.gz")
            (d / "collector").unlink()
            os.link(d / "app", d / "collector")
            with self.assertRaisesRegex(M.OverlayError, "source inputs alias"):
                build(d)

    def test_source_symlink_fifo_directory(self):
        for kind in ("symlink", "fifo", "directory"):
            with self.subTest(kind=kind), fixture() as (d, _):
                (d / "app").unlink()
                if kind == "symlink": (d / "app").symlink_to(d / "collector")
                elif kind == "fifo": os.mkfifo(d / "app")
                else: (d / "app").mkdir()
                with self.assertRaises(M.OverlayError): build(d)
                self.assertFalse((d / "out.gz").exists())

    def test_parent_symlinks_and_traversal(self):
        with fixture() as (d, _):
            (d / "link").symlink_to(d, target_is_directory=True)
            with self.assertRaises(M.OverlayError): build(d, "link/out.gz")
            with self.assertRaises(M.OverlayError): build(d / "link")
            with self.assertRaises(M.OverlayError): build(d, "missing/../out.gz")
            self.assertFalse((d / "out.gz").exists())

    def test_parent_replacement_during_compression(self):
        with fixture() as (d, _):
            (d / "outputs").mkdir()
            original = M._gzip
            def replace(data):
                result = original(data)
                (d / "outputs").rename(d / "old-outputs")
                (d / "outputs").mkdir()
                return result
            with mock.patch.object(M, "_gzip", side_effect=replace), self.assertRaisesRegex(M.OverlayError, "parent changed"):
                build(d, "outputs/out.gz")
            self.assertFalse((d / "old-outputs/out.gz").exists())

    def test_output_created_during_compression_is_not_overwritten(self):
        with fixture() as (d, _):
            original = M._gzip
            def create(data):
                result = original(data)
                (d / "out.gz").write_bytes(b"other owner")
                return result
            with mock.patch.object(M, "_gzip", side_effect=create), self.assertRaises(M.OverlayError):
                build(d)
            self.assertEqual((d / "out.gz").read_bytes(), b"other owner")

    def test_partial_writes_complete_and_fsync_order(self):
        with fixture() as (d, _):
            write = os.write
            fsync = os.fsync
            events = []
            def partial(fd, data):
                events.append("write")
                return write(fd, data[:7])
            def sync(fd):
                events.append("dir-fsync" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file-fsync")
                fsync(fd)
            with mock.patch.object(M.os, "write", side_effect=partial), mock.patch.object(M.os, "fsync", side_effect=sync):
                result = build(d)
            self.assertGreater(events.count("write"), 1)
            self.assertEqual(events[-2:], ["file-fsync", "dir-fsync"])
            self.assertEqual(result["output_sha256"], digest((d / "out.gz").read_bytes()))

    def test_zero_and_failed_partial_writes_leave_unaccepted_output(self):
        for zero in (True, False):
            with self.subTest(zero=zero), fixture() as (d, _):
                write = os.write
                calls = 0
                def failed(fd, data):
                    nonlocal calls
                    calls += 1
                    if calls == 1: return write(fd, data[:7])
                    if zero: return 0
                    raise OSError("injected write failure")
                with mock.patch.object(M.os, "write", side_effect=failed), self.assertRaises(M.OverlayError):
                    build(d)
                self.assertEqual((d / "out.gz").stat().st_size, 7)
                with self.assertRaisesRegex(M.OverlayError, "output already exists"): build(d)

    def test_output_corruption_on_fsync_rejected(self):
        with fixture() as (d, _):
            fsync = os.fsync
            def corrupt(fd):
                fsync(fd)
                if stat.S_ISREG(os.fstat(fd).st_mode): os.pwrite(fd, b"bad", 0)
            with mock.patch.object(M.os, "fsync", side_effect=corrupt), self.assertRaisesRegex(M.OverlayError, "output reread hash mismatch"):
                build(d)

    def test_output_replacement_or_hardlink_during_fsync_rejected(self):
        for hardlink in (False, True):
            with self.subTest(hardlink=hardlink), fixture() as (d, _):
                fsync = os.fsync
                def replace(fd):
                    fsync(fd)
                    if stat.S_ISREG(os.fstat(fd).st_mode):
                        if hardlink: os.link(d / "out.gz", d / "alias.gz")
                        else:
                            (d / "out.gz").rename(d / "moved.gz")
                            (d / "out.gz").write_bytes(b"replacement")
                with mock.patch.object(M.os, "fsync", side_effect=replace), self.assertRaisesRegex(M.OverlayError, "output identity/alias changed"):
                    build(d)

    def test_output_mutation_during_last_source_recheck(self):
        with fixture() as (d, _):
            verify = M._Source.verify
            fsync = os.fsync
            synced_directory = False
            def sync(fd):
                nonlocal synced_directory
                fsync(fd)
                if stat.S_ISDIR(os.fstat(fd).st_mode): synced_directory = True
            def mutate(source):
                verify(source)
                if synced_directory and source.path.name == "collector":
                    (d / "out.gz").write_bytes(b"late corruption")
            with mock.patch.object(M.os, "fsync", side_effect=sync), mock.patch.object(M._Source, "verify", mutate):
                with self.assertRaisesRegex(M.OverlayError, "during final source recheck"):
                    build(d)

    def test_broken_gzip_streams_and_expansion_bound(self):
        values = (b"bad", gzip.compress(b"x")[:-3],
                  b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff" + b"\xff" * 20)
        for value in values:
            with self.subTest(value=value), self.assertRaises(M.OverlayError): M._inflate(value, 1024)
        with self.assertRaisesRegex(M.OverlayError, "exceeds bound"):
            M._inflate(gzip.compress(b"x" * 1025), 1024)

    def test_malformed_newc(self):
        valid = archive(member("x", b"abc"))
        variants = [b"", valid[:20], b"070700" + valid[6:],
                    valid[:6] + b"       1" + valid[14:],
                    valid[:94] + b"ffffffff" + valid[102:],
                    valid[:54] + b"ffffffff" + valid[62:],
                    valid[:111] + b"x" + valid[112:],
                    valid[:-1], valid + b"x", member("x", b"abc"),
                    archive(member("../x")), archive(member("/x")),
                    archive(member("x//y")), archive(member("x/./y")),
                    archive(member("x\\y")), archive(member("x", nlink=0)),
                    archive(member("x", mode=0o040755, data=b"x")),
                    archive(member("x", mode=0o120777, data=b"a\0b")),
                    archive(member("x", mode=0o140777)),
                    archive(member("x", rdevmajor=1)),
                    archive(member("x", check=1)),
                    archive(member("x", b"abc", magic=b"070702", check=1)),
                    member("TRAILER!!!", b"nonempty", mode=0),
                    member("TRAILER!!!", mode=0, nlink=0),
                    archive(member("x")) + b"\0" + archive(member("y"))]
        for index, value in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(M.OverlayError): M.parse_newc(value)
        # Explicit header-name and data padding controls.
        padded = bytearray(archive(member("ab", b"x")))
        padded[113] = 1
        with self.assertRaisesRegex(M.OverlayError, "padding"): M.parse_newc(padded)
        padded = bytearray(archive(member("x", b"x")))
        padded[113] = 1
        with self.assertRaisesRegex(M.OverlayError, "padding"): M.parse_newc(padded)

    def test_crc_archive_positive(self):
        raw = archive(member("x", b"abc", magic=b"070702", check=sum(b"abc")))
        self.assertEqual(M.parse_newc(raw)[0][0]["sha256"], digest(b"abc"))

    def test_duplicate_paths_and_type_changes_rejected(self):
        variants = [archive(member("keep", b"a"), member("keep", b"b")),
                    archive(member("keep", b"a"), member("./keep", b"b")),
                    archive(member("init", b"target", mode=0o120777)),
                    archive(member("init", mode=0o010600)),
                    archive(member("init", mode=0o020600)),
                    archive(member("init", b"hardlink", nlink=2)),
                    archive(member("apps", b"where", mode=0o120777)),
                    archive(member("case", b"file"))]
        for index, value in enumerate(variants):
            with self.subTest(index=index), fixture(value) as (d, _):
                with self.assertRaises(M.OverlayError): build(d)
                self.assertFalse((d / "out.gz").exists())

    def test_missing_or_symlink_ancestor_in_base_rejected(self):
        variants = [archive(member("missing/child", b"x")),
                    archive(member("link", b"elsewhere", mode=0o120777), member("link/child", b"x"))]
        for value in variants:
            with fixture(value) as (d, _), self.assertRaisesRegex(M.OverlayError, "ancestor"): build(d)

    def test_hardlink_payload_replay_and_ambiguity_rejection(self):
        raw = archive(member("first", ino=9, nlink=2), member("second", b"shared", ino=9, nlink=2))
        with fixture(raw) as (d, _):
            result = build(d)
            self.assertEqual(result["final_map"]["first"]["sha256"], digest(b"shared"))
            self.assertEqual(result["final_map"]["second"]["sha256"], digest(b"shared"))
        raw = archive(member("first", b"one", ino=9, nlink=2), member("second", b"two", ino=9, nlink=2))
        with fixture(raw) as (d, _), self.assertRaisesRegex(M.OverlayError, "ambiguous newc hardlink"): build(d)

    def test_overlay_membership_type_and_canonical_metadata(self):
        variants = [M._archive((("init", b"a", 0o100755),)),
                    overlay() + archive(),
                    overlay().replace(b"apps\0", b"evil\0", 1),
                    M._archive((("apps", b"", 0o040755), ("case", b"", 0o040755),
                                ("case/work", b"", 0o040755), ("init", b"target", 0o120777),
                                ("apps/app", b"payload", 0o100755)))]
        with fixture() as (d, _):
            for index, value in enumerate(variants):
                with self.subTest(index=index), self.assertRaises(M.OverlayError):
                    base = (d / "base.gz").read_bytes()
                    M.replay(base, value, base_sha256=digest(base), base_size=len(base),
                             base_cpio_sha256=digest(gzip.decompress(base)),
                             base_cpio_size=len(gzip.decompress(base)))

    def test_static_collector_elf_positive_profiles(self):
        profiles = [collector_elf(), collector_elf(elf_type=3, entry=256,
                    segments=[(1, 5, 0, 0, 0, 512, 512, 4096)]),
                    collector_elf(segments=[(1, 5, 0, 0x400000, 0, 384, 384, 4096),
                                            (1, 6, 384, 0x401180, 0, 128, 256, 4096)])]
        for data in profiles:
            with self.subTest(elf=digest(data)), fixture() as (d, _):
                (d / "collector").write_bytes(data)
                result = build(d, collector_sha256=digest(data))
                self.assertEqual(result["final_map"]["init"]["sha256"], digest(data))

    def test_collector_invalid_formats_and_header_geometry(self):
        variants = [b"", b"arbitrary", b"#!/bin/sh\nexit 0\n", b"\x7fELF",
                    collector_elf()[:80], collector_elf(elf_type=1),
                    collector_elf(machine=183), collector_elf(version=0),
                    collector_elf(segments=[]), collector_elf(phoff=65),
                    collector_elf(phentsize=55), collector_elf(phnum=0xffff),
                    collector_elf(phoff=512), collector_elf(ehsize=63),
                    collector_elf(ident=b"\x7fELF\x02\x02\x01" + bytes(9))]
        for index, data in enumerate(variants):
            with self.subTest(index=index), fixture() as (d, _):
                (d / "collector").write_bytes(data)
                with self.assertRaises(M.OverlayError): build(d, collector_sha256=digest(data))
                self.assertFalse((d / "out.gz").exists())

    def test_collector_bad_load_and_entry_geometry(self):
        load = (1, 5, 0, 0x400000, 0, 512, 512, 4096)
        variants = [collector_elf(entry=0), collector_elf(entry=0x400200),
                    collector_elf(entry=0x3fffff),
                    collector_elf(segments=[(1, 4, *load[2:])]),
                    collector_elf(segments=[(4, *load[1:])]),
                    collector_elf(segments=[(1, 5, 0, 0x400000, 0, 513, 513, 4096)]),
                    collector_elf(segments=[(1, 5, 0, 0x400000, 0, 512, 511, 4096)]),
                    collector_elf(segments=[(1, 5, 0, 0x400000, 0, 0, 0, 4096)]),
                    collector_elf(segments=[(1, 5, 0, 0x400001, 0, 512, 512, 4096)]),
                    collector_elf(segments=[(1, 5, 0, 0x400000, 0, 512, 512, 3)]),
                    collector_elf(segments=[(1, 13, 0, 0x400000, 0, 512, 512, 4096)]),
                    collector_elf(segments=[(1, 5, 0, (1 << 47) - 4096, 0, 512, 8192, 4096)]),
                    collector_elf(segments=[load, (1, 6, 0, 0x401000, 0, 512, 512, 4096)]),
                    collector_elf(segments=[load, (1, 6, 384, 0x400180, 0, 128, 128, 4096)]),
                    collector_elf(segments=[(1, 5, 0, 0x400000, 0, 384, 384, 4096),
                                             (1, 6, 384, 0x400180, 0, 128, 128, 4096)]),
                    collector_elf(segments=[load, (3, 4, 0, 0, 0, 12, 12, 1)])]
        for index, data in enumerate(variants):
            with self.subTest(index=index), fixture() as (d, _):
                (d / "collector").write_bytes(data)
                with self.assertRaises(M.OverlayError): build(d, collector_sha256=digest(data))
                self.assertFalse((d / "out.gz").exists())

    def test_static_dynamic_table_and_external_dependency(self):
        def dynamic(tag, terminated=True):
            data = bytearray(collector_elf(elf_type=3, segments=[
                (1, 5, 0, 0x400000, 0, 512, 512, 4096),
                (2, 4, 384, 0x400180, 0, 32, 32, 8)]))
            struct.pack_into("<qQqQ", data, 384, tag, 1, 0 if terminated else tag, 0)
            return bytes(data)
        M._check_collector(dynamic(30))  # Static PIE flags, then DT_NULL.
        for data in (dynamic(1), dynamic(0x7ffffffd), dynamic(0x7fffffff), dynamic(30, False)):
            with self.subTest(elf=digest(data)), self.assertRaises(M.OverlayError): M._check_collector(data)

    def test_collector_hash_mandatory_and_strict(self):
        with fixture() as (d, _):
            with self.assertRaises(TypeError):
                M.build_overlay(d / "base.gz", d / "app", d / "collector", d / "out.gz")
            for value in (None, 1, "", "0" * 63, "0" * 65, "g" * 64,
                          " " + "0" * 63, "0" * 64 + "\n", "0" * 64):
                with self.subTest(value=value), self.assertRaises(M.OverlayError):
                    build(d, collector_sha256=value)
                self.assertFalse((d / "out.gz").exists())
            build(d, collector_sha256=digest(collector_elf()).upper())

    def test_cli_requires_valid_collector_hash(self):
        with fixture() as (d, _):
            paths = [str(d / name) for name in ("base.gz", "app", "collector", "out.gz")]
            for args in (paths, paths + ["--collector-sha256", "invalid"]):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                    M.main(args)
                self.assertEqual(caught.exception.code, 2)
                self.assertFalse((d / "out.gz").exists())

    def test_cli_rejects_base_size_above_ceiling(self):
        with fixture() as (d, _):
            base = (d / "base.gz").read_bytes()
            args = [str(d / name) for name in ("base.gz", "app", "collector", "out.gz")]
            args += ["--collector-sha256", digest(collector_elf()),
                     "--base-sha256", digest(base), "--base-size", str(len(base)),
                     "--base-cpio-sha256", digest(gzip.decompress(base)),
                     "--base-cpio-size", str(len(gzip.decompress(base)))]
            for option, value in (("--base-size", M.MAX_SOURCE_SIZE + 1),
                                  ("--base-cpio-size", M.MAX_CPIO_SIZE + 1)):
                with self.subTest(option=option):
                    invalid = args[:]
                    invalid[invalid.index(option) + 1] = str(value)
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                        M.main(invalid)
                    self.assertEqual(caught.exception.code, 2)
                    self.assertFalse((d / "out.gz").exists())


if __name__ == "__main__":
    unittest.main()
