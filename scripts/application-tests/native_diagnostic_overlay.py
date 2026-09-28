#!/usr/bin/env python3
"""Append a diagnostic archive to an authenticated initramfs without extraction.

The original decompressed bytes, including padding, are preserved verbatim.
This byte derivation is not execution authority. Failed outputs remain as
evidence and must not be consumed as successful outputs.
"""
from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import io
import json
import os
import re
import stat
import struct
import zlib

BASE_SHA256 = "49fa5ec991faaa5fc745f10111ae1e9e2527621f90a1fd0ae3df02ab33dde293"
BASE_SIZE = 11846636
BASE_CPIO_SHA256 = "4f36958f2f0e4c6684d3adbd2b8b5860693298b332d11e8bb9e47a063420b265"
BASE_CPIO_SIZE = 38358016
PAYLOAD_SHA256 = "ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836"
OVERLAY_NAMES = ("apps", "case", "case/work", "init", "apps/app")
OVERLAY_MODES = (0o040755, 0o040755, 0o040755, 0o100755, 0o100755)
MAX_SOURCE_SIZE = 256 * 1024 * 1024
MAX_CPIO_SIZE = 512 * 1024 * 1024
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_IDENTITY_FIELDS = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_uid",
                    "st_gid", "st_size", "st_mtime_ns", "st_ctime_ns")


class OverlayError(ValueError):
    pass


def _die(message):
    raise OverlayError(message)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _identity(st):
    return {key: getattr(st, key) for key in _IDENTITY_FIELDS}


def _object(st):
    return st.st_dev, st.st_ino, stat.S_IFMT(st.st_mode)


class _Path:
    """Pin every parent directory and never traverse a symbolic link."""

    def __init__(self, path):
        self.fds = []
        self.edges = []
        supplied = os.fspath(path)
        if not isinstance(supplied, str) or "\0" in supplied:
            _die("invalid source/output path")
        if ".." in supplied.split("/") or supplied.endswith("/"):
            _die("unsafe source/output path")
        self.path = os.path.abspath(supplied)
        parts = self.path.split("/")[1:]
        if not parts or not parts[-1]:
            _die("source/output must name a file")
        try:
            self.fds.append(os.open("/", _DIR_FLAGS))
            for name in parts[:-1]:
                parent = self.fds[-1]
                fd = os.open(name, _DIR_FLAGS, dir_fd=parent)
                self.fds.append(fd)
                self.edges.append((parent, name, _object(os.fstat(fd))))
            self.parent = self.fds[-1]
            self.name = parts[-1]
            self.verify()
        except BaseException:
            self.close()
            raise

    def verify(self):
        for parent, name, identity in self.edges:
            if _object(os.stat(name, dir_fd=parent, follow_symlinks=False)) != identity:
                _die("source/output parent changed")

    def lstat(self):
        return os.stat(self.name, dir_fd=self.parent, follow_symlinks=False)

    def close(self):
        for fd in reversed(self.fds):
            os.close(fd)
        self.fds = []


def _read_fd(fd, limit=MAX_SOURCE_SIZE):
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    size = 0
    while True:
        chunk = os.read(fd, min(1024 * 1024, limit + 1 - size))
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            _die("file exceeds bounded input size")


class _Source:
    def __init__(self, path, stack):
        self.path = _Path(path)
        stack.callback(self.path.close)
        # NONBLOCK prevents a raced-in FIFO blocking before fstat can reject it.
        self.fd = os.open(self.path.name, os.O_RDONLY | os.O_NOFOLLOW |
                          os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=self.path.parent)
        stack.callback(os.close, self.fd)
        st = os.fstat(self.fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_SOURCE_SIZE:
            _die("source is not a bounded regular file")
        self.identity = _identity(st)
        self.data = _read_fd(self.fd)
        self.sha256 = _digest(self.data)
        self.verify()

    def verify(self):
        self.path.verify()
        if (_identity(os.fstat(self.fd)) != self.identity or
                _identity(self.path.lstat()) != self.identity):
            _die("source identity changed")
        if _digest(_read_fd(self.fd)) != self.sha256:
            _die("source content changed")
        if (_identity(os.fstat(self.fd)) != self.identity or
                _identity(self.path.lstat()) != self.identity):
            _die("source identity changed during recheck")

    def manifest(self):
        return {"path": self.path.path, "identity": self.identity,
                "sha256": self.sha256}


def _fields(header):
    if len(header) != 110 or header[:6] not in (b"070701", b"070702"):
        _die("invalid/truncated newc header")
    if re.fullmatch(b"[0-9a-fA-F]{104}", header[6:]) is None:
        _die("invalid newc numeric field")
    return [int(header[i:i + 8], 16) for i in range(6, 110, 8)]


def _padding(data, start, end):
    if end > len(data) or any(data[start:end]):
        _die("truncated or nonzero newc padding")


def parse_newc(data, *, require_trailer=True):
    """Strictly parse concatenated newc archives and zero block padding.

    Base special files/symlinks are represented explicitly, never extracted.
    Return ordered records and the last trailer offset.
    """
    if not require_trailer:
        _die("trailer validation cannot be disabled")
    records = []
    pos = 0
    archive = 0
    trailer = None
    in_archive = False
    allowed_types = {stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK,
                     stat.S_IFCHR, stat.S_IFBLK, stat.S_IFIFO}
    while pos < len(data):
        if not in_archive and data[pos] == 0:
            while pos < len(data) and data[pos] == 0:
                pos += 1
            if pos == len(data):
                break
            if pos % 4:
                _die("unaligned archive after padding")
        header = data[pos:pos + 110]
        values = _fields(header)
        (ino, mode, uid, gid, nlink, mtime, size, devmajor, devminor,
         rdevmajor, rdevminor, namesize, check) = values
        if namesize < 2 or namesize > 4096:
            _die("invalid newc name size")
        ns = pos + 110
        ne = ns + namesize
        if ne > len(data) or data[ne - 1] != 0 or b"\0" in data[ns:ne - 1]:
            _die("invalid newc name terminator")
        try:
            name = data[ns:ne - 1].decode("utf-8", "strict")
        except UnicodeDecodeError:
            _die("invalid newc name encoding")
        ds = (ne + 3) & ~3
        de = ds + size
        end = (de + 3) & ~3
        _padding(data, ne, ds)
        if de > len(data):
            _die("truncated newc payload")
        _padding(data, de, end)
        payload = data[ds:de]
        if ((header[:6] == b"070701" and check != 0) or
                (header[:6] == b"070702" and check != (sum(payload) & 0xffffffff))):
            _die("invalid newc checksum")
        if name == "TRAILER!!!":
            if size or mode or uid or gid or mtime or devmajor or devminor or rdevmajor or rdevminor or nlink != 1:
                _die("invalid newc trailer metadata")
            trailer = pos
            archive += 1
            in_archive = False
            pos = end
            continue
        if name.startswith("./"):
            name = name[2:]
        if (not name or name.startswith("/") or "\\" in name or
                (name != "." and any(x in ("", ".", "..") for x in name.split("/")))):
            _die("unsafe newc path")
        typ = stat.S_IFMT(mode)
        if mode & ~0xffff or typ not in allowed_types or not nlink:
            _die("invalid newc member mode/link count")
        if name == "." and typ != stat.S_IFDIR:
            _die("newc root is not a directory")
        if typ not in (stat.S_IFREG, stat.S_IFLNK) and size:
            _die("nonempty special newc member")
        if typ == stat.S_IFLNK and (not payload or b"\0" in payload):
            _die("invalid newc symlink target")
        if typ not in (stat.S_IFCHR, stat.S_IFBLK) and (rdevmajor or rdevminor):
            _die("non-device newc member has device numbers")
        records.append(dict(name=name, ino=ino, mode=mode, uid=uid, gid=gid,
                            nlink=nlink, mtime=mtime, size=size, devmajor=devmajor,
                            devminor=devminor, rdevmajor=rdevmajor, rdevminor=rdevminor,
                            sha256=_digest(payload), data=payload, archive=archive))
        in_archive = True
        pos = end
    if trailer is None or in_archive:
        _die("newc trailer missing")
    return records, trailer


def _newc(name, data, mode, *, ino=0):
    nb = name.encode("utf-8") + b"\0"
    nlink = 2 if stat.S_ISDIR(mode) else 1
    fields = [ino, mode, 0, 0, nlink, 0, len(data), 0, 0, 0, 0, len(nb), 0]
    header = b"070701" + b"".join(f"{x:08x}".encode("ascii") for x in fields)
    raw = header + nb + b"\0" * ((-len(header) - len(nb)) % 4) + data
    return raw + b"\0" * (-len(raw) % 4)


def _archive(entries):
    return b"".join(_newc(name, data, mode, ino=i)
                    for i, (name, data, mode) in enumerate(entries, 1)) + _newc("TRAILER!!!", b"", 0)


def _inflate(raw, limit):
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
            result = stream.read(limit + 1)
            if len(result) > limit:
                _die("decompressed archive exceeds bound")
            return result
    except (OSError, EOFError, zlib.error) as exc:
        _die(f"invalid gzip: {exc}")


def _authenticate_base(raw):
    if len(raw) != BASE_SIZE or _digest(raw) != BASE_SHA256:
        _die("base gzip identity mismatch")
    data = _inflate(raw, BASE_CPIO_SIZE)
    if len(data) != BASE_CPIO_SIZE or _digest(data) != BASE_CPIO_SHA256:
        _die("base cpio identity mismatch")
    return data


def _replay_records(records):
    final = {}
    links = {}
    for record in records:
        name = record["name"]
        if name in final and name not in OVERLAY_NAMES:
            _die("duplicate newc path outside overlay allowlist")
        # Lexical paths must match the unpacked namespace: no symlink ancestors.
        parts = name.split("/")
        for i in range(1, len(parts)):
            parent = "/".join(parts[:i])
            if parent not in final or not stat.S_ISDIR(final[parent]["mode"]):
                _die("missing or non-directory newc ancestor")
        if name in final and stat.S_IFMT(final[name]["mode"]) != stat.S_IFMT(record["mode"]):
            _die("newc duplicate changes member type")
        if stat.S_ISREG(record["mode"]) and record["nlink"] > 1:
            if name in OVERLAY_NAMES:
                _die("overlay destination is a hardlink")
            key = (record["archive"], record["devmajor"], record["devminor"], record["ino"])
            group = links.setdefault(key, [])
            if group:
                first = group[0]
                if any(record[k] != first[k] for k in ("mode", "uid", "gid", "nlink", "mtime")):
                    _die("inconsistent newc hardlink metadata")
                if record["size"] and any(r["size"] for r in group):
                    _die("ambiguous newc hardlink payload")
            group.append(record)
            if len(group) > record["nlink"]:
                _die("newc hardlink count overflow")
        final[name] = record
    for group in links.values():
        payload = next((r for r in group if r["size"]), group[0])
        for member in group:
            if final.get(member["name"]) is member:
                final[member["name"]] = dict(member, data=payload["data"],
                                             size=payload["size"], sha256=payload["sha256"])
    return final


def _manifest(final):
    fields = ("mode", "uid", "gid", "nlink", "mtime", "size", "sha256",
              "rdevmajor", "rdevminor")
    return {name: {field: record[field] for field in fields}
            for name, record in sorted(final.items())}


def replay(base_raw, overlay_raw):
    base = _authenticate_base(base_raw)
    base_records, _ = parse_newc(base)
    overlay_records, _ = parse_newc(overlay_raw)
    if tuple(r["name"] for r in overlay_records) != OVERLAY_NAMES:
        _die("overlay membership/order mismatch")
    if any(r["archive"] != 0 for r in overlay_records):
        _die("overlay must be one archive")
    if overlay_raw != _archive((r["name"], r["data"], r["mode"]) for r in overlay_records):
        _die("overlay is not the canonical deterministic archive")
    for record, mode in zip(overlay_records, OVERLAY_MODES):
        if (record["mode"] != mode or record["uid"] or record["gid"] or record["mtime"] or
                record["nlink"] != (2 if stat.S_ISDIR(mode) else 1) or
                record["devmajor"] or record["devminor"] or record["rdevmajor"] or record["rdevminor"]):
            _die("invalid overlay member metadata")
    final = _manifest(_replay_records(base_records + overlay_records))
    combined, _ = parse_newc(base + overlay_raw)
    if final != _manifest(_replay_records(combined)):
        _die("concatenated archive replay mismatch")
    return final


def _check_collector(data):
    if len(data) < 64 or data[:7] != b"\x7fELF\x02\x01\x01":
        _die("collector is not valid little-endian ELF64")
    header = struct.unpack_from("<16sHHIQQQIHHHHHH", data)
    ident, elf_type, machine, version, entry = header[:5]
    if (elf_type not in (2, 3) or machine != 62 or version != 1 or
            header[7] != 0 or ident[7] not in (0, 3) or any(ident[8:])):
        _die("collector must be a System V/Linux x86_64 executable ELF")
    phoff, ehsize, phentsize, phnum = header[5], header[8], header[9], header[10]
    if (ehsize != 64 or phentsize != 56 or not 0 < phnum <= 65536 // 56 or
            phoff < 64 or phoff % 8):
        _die("invalid collector ELF program headers")
    if phoff + phentsize * phnum > len(data):
        _die("truncated collector ELF program headers")
    loads = []
    dynamics = []
    for i in range(phnum):
        kind, flags, offset, vaddr, paddr, filesz, memsz, align = struct.unpack_from(
            "<IIQQQQQQ", data, phoff + i * phentsize)
        if kind == 3:
            _die("collector has an interpreter")
        if kind == 0:  # PT_NULL fields are unspecified and not consumed.
            continue
        if offset > len(data) or filesz > len(data) - offset:
            _die("collector program header file range is out of bounds")
        if flags & ~7 or (align > 1 and align & (align - 1)):
            _die("invalid collector program header flags/alignment")
        if kind == 2:
            dynamics.append((offset, filesz, vaddr))
        if kind != 1:
            continue
        if (not memsz or filesz > memsz or vaddr >= 1 << 47 or
                memsz > (1 << 47) - vaddr):
            _die("invalid collector PT_LOAD memory range")
        if vaddr % 4096 != offset % 4096 or (align > 1 and vaddr % align != offset % align):
            _die("invalid collector PT_LOAD alignment")
        current = (offset, filesz, vaddr, memsz, flags)
        for old_offset, old_filesz, old_vaddr, old_memsz, _ in loads:
            # Linux maps entire pages: overlapping page mappings are ambiguous
            # even if the nominal byte ranges do not overlap.
            if (vaddr // 4096 < (old_vaddr + old_memsz + 4095) // 4096 and
                    old_vaddr // 4096 < (vaddr + memsz + 4095) // 4096):
                _die("overlapping collector PT_LOAD memory ranges")
            if filesz and old_filesz and offset < old_offset + old_filesz and old_offset < offset + filesz:
                _die("overlapping collector PT_LOAD file ranges")
        loads.append(current)
    if not loads or not entry or not any(flags & 1 and vaddr <= entry < vaddr + filesz
                                         for _, filesz, vaddr, _, flags in loads):
        _die("collector entry is not inside an executable file-backed PT_LOAD")
    # ET_DYN is permitted only without an interpreter or external libraries.
    # A static PIE may retain its own relocation table in PT_DYNAMIC.
    if len(dynamics) > 1:
        _die("multiple collector PT_DYNAMIC segments")
    for offset, size, vaddr in dynamics:
        if not size or size % 16 or offset % 8:
            _die("invalid collector PT_DYNAMIC geometry")
        if not any(start <= offset and offset + size <= start + filesz and
                   vaddr == load_vaddr + offset - start
                   for start, filesz, load_vaddr, _, _ in loads):
            _die("collector PT_DYNAMIC is outside a file-backed PT_LOAD")
        terminated = False
        for at in range(offset, offset + size, 16):
            tag, value = struct.unpack_from("<qQ", data, at)
            if tag == 0:
                terminated = True
                break
            if tag in (1, 0x7ffffffd, 0x7fffffff):  # NEEDED, AUXILIARY, FILTER
                _die("collector requires an external dynamic library")
        if not terminated:
            _die("collector PT_DYNAMIC has no terminator")


def _collector_hash(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        _die("collector SHA256 must be exactly 64 hexadecimal characters")
    return value.lower()


def _gzip(data):
    out = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=out, compresslevel=9, mtime=0) as stream:
        stream.write(data)
    return out.getvalue()


def build_overlay(base, payload, collector, output, *, collector_sha256):
    collector_sha256 = _collector_hash(collector_sha256)
    try:
        with contextlib.ExitStack() as stack:
            target = _Path(output)
            stack.callback(target.close)
            try:
                target.lstat()
            except FileNotFoundError:
                pass
            else:
                _die("output already exists")
            sources = [_Source(path, stack) for path in (base, payload, collector)]
            identities = [(s.identity["st_dev"], s.identity["st_ino"]) for s in sources]
            if len(set(identities)) != len(identities):
                _die("source inputs alias one another")
            br, pr, cr = (s.data for s in sources)
            original = _authenticate_base(br)
            if _digest(pr) != PAYLOAD_SHA256:
                _die("payload hash mismatch")
            if _digest(cr) != collector_sha256:
                _die("collector hash mismatch")
            _check_collector(cr)
            overlay = _archive((("apps", b"", 0o040755), ("case", b"", 0o040755),
                                ("case/work", b"", 0o040755), ("init", cr, 0o100755),
                                ("apps/app", pr, 0o100755)))
            final_map = replay(br, overlay)
            raw = _gzip(original + overlay)
            for source in sources:
                source.verify()
            target.verify()
            fd = os.open(target.name, os.O_RDWR | os.O_CREAT | os.O_EXCL |
                         os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=target.parent)
            stack.callback(os.close, fd)
            created = _object(os.fstat(fd))
            view = memoryview(raw)
            while view:
                written = os.write(fd, view)
                if written <= 0 or written > len(view):
                    _die("output write made invalid progress")
                view = view[written:]
            os.fsync(fd)
            output_identity = _identity(os.fstat(fd))
            observed = _read_fd(fd, MAX_CPIO_SIZE + MAX_SOURCE_SIZE)
            if len(observed) != len(raw) or _digest(observed) != _digest(raw):
                _die("output reread hash mismatch")
            unpacked = _inflate(observed, len(original) + len(overlay))
            if unpacked != original + overlay:
                _die("output decompressed bytes mismatch")
            observed_records, _ = parse_newc(unpacked)
            if _manifest(_replay_records(observed_records)) != final_map:
                _die("output final map mismatch")
            for source in sources:
                source.verify()
            target.verify()
            st = os.fstat(fd)
            if (_object(st) != created or st.st_nlink != 1 or
                    _identity(st) != output_identity or
                    _identity(target.lstat()) != _identity(st)):
                _die("output identity/alias changed")
            os.fsync(target.parent)
            target.verify()
            if (_identity(target.lstat()) != output_identity or
                    _identity(os.fstat(fd)) != output_identity):
                _die("output identity changed after directory fsync")
            if _digest(_read_fd(fd, MAX_CPIO_SIZE + MAX_SOURCE_SIZE)) != _digest(raw):
                _die("output changed after directory fsync")
            for source in sources:
                source.verify()
            target.verify()
            if (_identity(target.lstat()) != output_identity or
                    _identity(os.fstat(fd)) != output_identity or
                    os.fstat(fd).st_nlink != 1):
                _die("output identity changed during final source recheck")
            return {"sources": dict(zip(("base", "payload", "collector"),
                                        (s.manifest() for s in sources))),
                    "base_sha256": _digest(br), "base_cpio_sha256": _digest(original),
                    "base_cpio_size": len(original), "payload_sha256": _digest(pr),
                    "collector_sha256": _digest(cr), "overlay_sha256": _digest(overlay),
                    "output_sha256": _digest(raw), "output_identity": output_identity,
                    "size": len(raw), "final_map": final_map}
    except OSError as exc:
        raise OverlayError(f"overlay I/O rejected: {exc}") from exc


def main(argv=None):
    parser = argparse.ArgumentParser()
    for name in ("base", "payload", "collector", "output"):
        parser.add_argument(name)
    parser.add_argument("--collector-sha256", required=True, type=_collector_hash)
    args = parser.parse_args(argv)
    print(json.dumps(build_overlay(args.base, args.payload, args.collector, args.output,
                                   collector_sha256=args.collector_sha256), sort_keys=True))


if __name__ == "__main__":
    main()
