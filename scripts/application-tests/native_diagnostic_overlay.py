#!/usr/bin/env python3
"""Authenticated, minimal initramfs overlay builder.

The base archive is never rewritten: its decompressed bytes are the exact
prefix of the output stream.  The Linux initramfs unpacker applies later
entries over earlier entries, so the overlay deliberately contains the final
map for ``init`` and ``apps/app``.
"""
from __future__ import annotations
import argparse, gzip, hashlib, os, stat, struct
from pathlib import Path

BASE_SHA256 = "49fa5ec991faaa5fc745f10111ae1e9e2527621f90a1fd0ae3df02ab33dde293"
PAYLOAD_SHA256 = "ff227c83b2da598110768e13f5e042b437e049659706b56079cc73f7c818a836"
OVERLAY_NAMES = ("init", "apps/app", "case/work")
class OverlayError(ValueError): pass

def _die(msg): raise OverlayError(msg)
def _digest(data): return hashlib.sha256(data).hexdigest()
def _regular(path, label):
    try: st = os.stat(path, follow_symlinks=False)
    except OSError as e: _die(f"{label}: {e}")
    if not stat.S_ISREG(st.st_mode): _die(f"{label} is not a regular file")
    return st
def _read(path, label):
    fd = os.open(os.fspath(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode): _die(f"{label} is not a regular file")
        out = bytearray()
        while True:
            b = os.read(fd, 1024 * 1024)
            if not b: break
            out += b
        return bytes(out)
    finally: os.close(fd)

def _field(h, off, n):
    try: return int(h[off:off+n], 16)
    except (ValueError, TypeError): _die("invalid newc numeric field")

def parse_newc(data, *, require_trailer=True):
    """Parse one newc stream, returning ordered records and trailer offset."""
    records=[]; pos=0; trailer=None
    while pos + 110 <= len(data):
        h=data[pos:pos+110]
        if h[:6] not in (b"070701", b"070702"): _die("invalid newc magic")
        ino=_field(h,6,8); mode=_field(h,14,8); uid=_field(h,22,8); gid=_field(h,30,8)
        nlink=_field(h,38,8); mtime=_field(h,46,8); size=_field(h,54,8); namesize=_field(h,94,8)
        if namesize < 1 or namesize > len(data)-pos-110: _die("invalid newc name size")
        ns=pos+110; ne=ns+namesize
        if data[ne-1] != 0: _die("newc name is not nul terminated")
        name=data[ns:ne-1].decode("utf-8", "strict")
        if name == "TRAILER!!!":
            if size != 0: _die("nonempty newc trailer")
            trailer=pos; pos=ne; pos=(pos+3)&~3
            if pos != len(data): _die("bytes after newc trailer")
            break
        if not name or name.startswith("/") or "\\" in name or any(x in ("", ".", "..") for x in name.split("/")):
            _die("unsafe newc path")
        ds=(ne+3)&~3; de=ds+size; end=(de+3)&~3
        if end > len(data): _die("truncated newc payload")
        payload=data[ds:de]
        typ=stat.S_IFMT(mode)
        if typ not in (stat.S_IFREG, stat.S_IFDIR, stat.S_IFLNK): _die("unsupported newc member type")
        if typ == stat.S_IFLNK: _die("symlink in initramfs")
        records.append({"name":name,"mode":mode,"uid":uid,"gid":gid,"nlink":nlink,"mtime":mtime,"size":size,"sha256":_digest(payload),"data":payload})
        pos=end
    if require_trailer and trailer is None: _die("newc trailer missing")
    return records, trailer

def _newc(name, data, mode):
    nb=name.encode()+b"\0"; ino=0; uid=gid=0; nlink=2 if stat.S_ISDIR(mode) else 1
    fields=[ino,mode,uid,gid,nlink,0,len(data),0,0,len(nb),0]
    h=b"070701"+b"".join(f"{x:08x}".encode() for x in fields)
    raw=h+nb+b"\0"*((-len(h)-len(nb))%4)+data
    return raw+b"\0"*((-len(raw))%4)

def _archive(entries):
    out=bytearray()
    for name,data,mode in entries: out += _newc(name,data,mode)
    out += _newc("TRAILER!!!",b"",0)
    return bytes(out)

def replay(base_raw, overlay_raw, *, expected_base_sha256=BASE_SHA256, expected_overlay_names=OVERLAY_NAMES):
    if _digest(base_raw) != expected_base_sha256: _die("base gzip hash mismatch")
    try: base=gzip.decompress(base_raw)
    except (OSError, EOFError) as e: _die(f"invalid base gzip: {e}")
    base_records, _ = parse_newc(base)
    overlay_records, _ = parse_newc(overlay_raw)
    names=tuple(r["name"] for r in overlay_records)
    if names != tuple(expected_overlay_names): _die("overlay membership/order mismatch")
    final={r["name"]:r for r in base_records}
    for r in overlay_records: final[r["name"]]=r
    return {k:{x:r[x] for x in ("mode","uid","gid","mtime","size","sha256")} for k,r in final.items()}

def build_overlay(base, payload, collector, output, *, collector_sha256=None):
    base=Path(base); payload=Path(payload); collector=Path(collector); output=Path(output)
    if output.exists() or os.path.lexists(output): _die("output already exists")
    if not output.parent.is_dir(): _die("output parent missing")
    br=_read(base,"base"); pr=_read(payload,"payload"); cr=_read(collector,"collector")
    if _digest(br) != BASE_SHA256: _die("base gzip hash mismatch")
    if _digest(pr) != PAYLOAD_SHA256: _die("payload hash mismatch")
    if collector_sha256 is not None and _digest(cr) != collector_sha256: _die("collector hash mismatch")
    # If an ELF is provided, static means no PT_INTERP program header.
    if cr[:4] == b"\x7fELF":
        if cr[4] != 2 or cr[5] != 1: _die("collector is not little-endian ELF64")
        eh=struct.unpack_from("<16sHHIQQQIHHHHHH",cr,0); phoff,phentsz,phnum=eh[5],eh[9],eh[10]
        for i in range(phnum):
            off=phoff+i*phentsz
            if off+phentsz > len(cr): _die("truncated ELF program header")
            if struct.unpack_from("<I",cr,off)[0] == 3: _die("collector has an interpreter")
    overlay=_archive((("init",cr,0o100755),("apps/app",pr,0o100755),("case/work",b"",0o040755)))
    # Validate exact overlay and resulting duplicate-final map before publish.
    replay(br, overlay, expected_base_sha256=_digest(br))
    raw=gzip.compress(gzip.decompress(br)+overlay, compresslevel=9, mtime=0)
    fd=os.open(output, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC, 0o600)
    try:
        view=memoryview(raw)
        while view: view=view[os.write(fd,view):]
        os.fsync(fd)
    finally: os.close(fd)
    dfd=os.open(output.parent, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try: os.fsync(dfd)
    finally: os.close(dfd)
    return {"base_sha256":_digest(br),"payload_sha256":_digest(pr),"collector_sha256":_digest(cr),"output_sha256":_digest(raw),"overlay_sha256":_digest(overlay),"size":len(raw)}

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("base"); p.add_argument("payload"); p.add_argument("collector"); p.add_argument("output"); p.add_argument("--collector-sha256")
    a=p.parse_args(argv); print(build_overlay(a.base,a.payload,a.collector,a.output,collector_sha256=a.collector_sha256))
if __name__ == "__main__": main()
