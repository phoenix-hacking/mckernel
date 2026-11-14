#!/usr/bin/env python3
"""Build and verify a sealed, deterministic candidate-retention archive."""
from __future__ import print_function
import argparse, errno, hashlib, io, json, os, stat, sys, tarfile, tempfile

class ArchiveError(RuntimeError): pass
# Every read-side descriptor is nonblocking until fstat has proved its type.
# Otherwise an attacker can replace an observed regular file with a FIFO in
# the lstat/open interval and indefinitely stall the retention worker.
_DIR = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
_FILE = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)

def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out: raise ArchiveError("duplicate JSON key: " + str(k))
        out[k] = v
    return out
def _kind(s):
    if stat.S_ISDIR(s.st_mode): return "directory"
    if stat.S_ISREG(s.st_mode): return "regular"
    if stat.S_ISLNK(s.st_mode): return "symlink"
    if stat.S_ISFIFO(s.st_mode): return "fifo"
    if stat.S_ISCHR(s.st_mode): return "character-device"
    if stat.S_ISBLK(s.st_mode): return "block-device"
    if stat.S_ISSOCK(s.st_mode): return "socket"
    return "unsupported"
def _stamp(s):
    return {"dev":s.st_dev,"inode":s.st_ino,"type":_kind(s),"mode":stat.S_IMODE(s.st_mode),"uid":s.st_uid,"gid":s.st_gid,"size":s.st_size,"nlink":s.st_nlink,"mtime_ns":s.st_mtime_ns,"ctime_ns":s.st_ctime_ns}
def _same(s, row): return all(_stamp(s)[k] == row[k] for k in _stamp(s))
def _safe_rel(p): return isinstance(p,str) and bool(p) and not p.startswith("/") and "//" not in p and "\x00" not in p and all(x not in ("", ".", "..") for x in p.split("/"))
def _safe_target(prefix, target):
    if not isinstance(target,str) or "\x00" in target or os.path.isabs(target): return False
    value=os.path.normpath(os.path.join(prefix,target)); return value != ".." and not value.startswith("../")

def _open_abs_dir(path):
    path=os.path.abspath(path); fd=os.open(os.path.sep,_DIR)
    try:
        for part in path.split(os.path.sep)[1:]:
            if not part: continue
            ls=os.stat(part,dir_fd=fd,follow_symlinks=False)
            if not stat.S_ISDIR(ls.st_mode): raise ArchiveError("path component is not a directory: "+path)
            child=os.open(part,_DIR,dir_fd=fd)
            if not _same(os.fstat(child),_stamp(ls)):
                os.close(child); raise ArchiveError("path component changed: "+path)
            os.close(fd); fd=child
        return fd
    except Exception:
        os.close(fd); raise
def _parent(path):
    p,n=os.path.split(os.path.abspath(path))
    if not n or n in (".","..") or "/" in n: raise ArchiveError("invalid leaf path")
    return p,n
def _names(fd, where):
    try: result=sorted(os.listdir(fd))
    except OSError as e: raise ArchiveError("cannot list %s: %s"%(where,e))
    if any(not x or x in (".","..") or "/" in x or "\x00" in x for x in result): raise ArchiveError("invalid directory entry")
    return result
def _digest(fd,size):
    h=hashlib.sha256(); total=0
    while True:
        b=os.read(fd,1024*1024)
        if not b: break
        h.update(b); total+=len(b)
    if total != size: raise ArchiveError("short source read")
    return h.hexdigest()

def _load(path):
    parent,name=_parent(path); pfd=_open_abs_dir(parent)
    try:
        ls=os.stat(name,dir_fd=pfd,follow_symlinks=False)
        if not stat.S_ISREG(ls.st_mode) or ls.st_nlink != 1: raise ArchiveError("manifest is not an unlinked regular file")
        fd=os.open(name,_FILE,dir_fd=pfd)
        try:
            before=os.fstat(fd)
            if not _same(before,_stamp(ls)): raise ArchiveError("manifest changed while opening")
            chunks=[]
            while True:
                b=os.read(fd,1024*1024)
                if not b: break
                chunks.append(b)
            raw=b"".join(chunks)
            if len(raw)!=before.st_size or not _same(os.fstat(fd),_stamp(before)): raise ArchiveError("manifest changed while reading")
        finally: os.close(fd)
    except OSError as e: raise ArchiveError("invalid manifest: %s"%e)
    finally: os.close(pfd)
    try: return raw,json.loads(raw.decode("utf-8"),object_pairs_hook=_pairs)
    except (UnicodeError,ValueError) as e: raise ArchiveError("invalid manifest JSON: %s"%e)

def _open_regular(path, label):
    """No-follow, nonblocking open of an archive-like regular input."""
    parent,name=_parent(path); pfd=_open_abs_dir(parent)
    try:
        ls=os.stat(name,dir_fd=pfd,follow_symlinks=False)
        if not stat.S_ISREG(ls.st_mode): raise ArchiveError(label+" is not a regular file")
        fd=os.open(name,_FILE,dir_fd=pfd)
        try:
            if not _same(os.fstat(fd),_stamp(ls)):
                raise ArchiveError(label+" changed while opening")
            return fd
        except Exception:
            os.close(fd); raise
    finally: os.close(pfd)

def _read_regular_bytes(path, label):
    """Read one sealed regular input once; callers must not reopen its path."""
    fd=_open_regular(path,label)
    try:
        before=os.fstat(fd); chunks=[]
        while True:
            data=os.read(fd,1024*1024)
            if not data: break
            chunks.append(data)
        value=b"".join(chunks)
        if len(value)!=before.st_size or not _same(os.fstat(fd),_stamp(before)):
            raise ArchiveError(label+" changed while reading")
        return value
    finally: os.close(fd)

def _scan(root,label):
    rootfd=_open_abs_dir(root)
    try:
        rootrow=_stamp(os.fstat(rootfd))
        if rootrow["type"] != "directory": raise ArchiveError("root is not a directory")
        rows=[]; bypath={}; seen=set()
        def visit(dfd,prefix,expected):
            if not _same(os.fstat(dfd),expected): raise ArchiveError("directory changed: "+(prefix or label))
            names=_names(dfd,prefix or label); expected["members"]=names
            for name in names:
                rel=name if not prefix else prefix+"/"+name; ls=os.stat(name,dir_fd=dfd,follow_symlinks=False); row=_stamp(ls); row.update({"root":label,"path":rel})
                if (ls.st_dev,ls.st_ino) in seen: raise ArchiveError("hardlink or duplicate inode: "+rel)
                seen.add((ls.st_dev,ls.st_ino))
                if row["type"] not in ("directory","regular","symlink"): raise ArchiveError("unsupported required node %s (%s)"%(rel,row["type"]))
                if row["type"] == "regular":
                    if ls.st_nlink != 1: raise ArchiveError("hardlink count is not one: "+rel)
                    cfd=os.open(name,_FILE,dir_fd=dfd)
                    try:
                        if not _same(os.fstat(cfd),row): raise ArchiveError("file changed while opening: "+rel)
                        row["sha256"]=_digest(cfd,row["size"])
                        if not _same(os.fstat(cfd),row): raise ArchiveError("file changed while reading: "+rel)
                    finally: os.close(cfd)
                elif row["type"] == "symlink":
                    target=os.readlink(name,dir_fd=dfd); end=os.stat(name,dir_fd=dfd,follow_symlinks=False)
                    if not _same(end,row) or not _safe_target(prefix,target): raise ArchiveError("unsafe or changed symlink: "+rel)
                    row["target"]=target; row["size"]=len(os.fsencode(target))
                rows.append(row); bypath[rel]=row
                if row["type"] == "directory":
                    cfd=os.open(name,_DIR,dir_fd=dfd)
                    try:
                        if not _same(os.fstat(cfd),row): raise ArchiveError("directory changed while opening: "+rel)
                        visit(cfd,rel,row)
                    finally: os.close(cfd)
            if _names(dfd,prefix or label)!=names or not _same(os.fstat(dfd),expected): raise ArchiveError("directory changed while scanning: "+(prefix or label))
        visit(rootfd,"",rootrow)
        if not _same(os.fstat(rootfd),rootrow): raise ArchiveError("root changed: "+label)
        return rootrow,rows,bypath
    finally: os.close(rootfd)

def _entry(e):
    needed={"root","path","type","mode","uid","gid","size","classification"}
    if not isinstance(e,dict) or not needed.issubset(e) or e["type"] not in ("directory","regular","symlink") or e["classification"] not in ("capsule-required","reconstructible") or not _safe_rel(e["path"]): raise ArchiveError("malformed manifest entry")
    if not all(isinstance(e[k],int) and e[k]>=0 for k in ("mode","uid","gid","size")): raise ArchiveError("bad manifest entry metadata")
    if e["type"]=="regular" and (not isinstance(e.get("sha256"),str) or len(e["sha256"])!=64): raise ArchiveError("regular entry lacks digest")
    if e["type"]=="symlink" and not isinstance(e.get("target"),str): raise ArchiveError("symlink entry lacks target")
def _selection(m):
    if not isinstance(m,dict) or set(m)!={"format","roots","revisions","entries","capsule_required"} or m["format"]!="native-exact-candidate-retention-v1" or not isinstance(m["revisions"],dict) or not all(isinstance(m[k],list) for k in ("roots","entries","capsule_required")): raise ArchiveError("wrong manifest schema")
    rows={}; required=set()
    for e in m["entries"]:
        _entry(e); key=(e["root"],e["path"])
        if e["root"] not in ("candidate","metadata-backup") or key in rows: raise ArchiveError("duplicate or invalid manifest entry")
        rows[key]=e
        if e["classification"]=="capsule-required": required.add(e["root"]+":"+e["path"])
    if len(m["capsule_required"])!=len(set(m["capsule_required"])) or set(m["capsule_required"])!=required: raise ArchiveError("capsule_required mismatch")
    selected=set()
    for k,e in rows.items():
        if e["type"]=="symlink" and e["classification"]=="capsule-required": raise ArchiveError("required symlink: %s:%s"%k)
        if e["type"]!="symlink" and (e["root"]=="metadata-backup" or e["classification"]=="capsule-required"): selected.add(k)
    for root,path in list(selected):
        bits=path.split("/")[:-1]
        while bits:
            p="/".join(bits); k=(root,p)
            if k not in rows or rows[k]["type"]!="directory": raise ArchiveError("selected entry lacks directory ancestor")
            selected.add(k); bits.pop()
    return rows,selected
def _validate(m,croot,mroot):
    rows,selected=_selection(m); expected={"candidate":os.path.abspath(croot),"metadata-backup":os.path.abspath(mroot)}; roots={}
    if os.path.commonpath((expected["candidate"],expected["metadata-backup"])) in (expected["candidate"],expected["metadata-backup"]): raise ArchiveError("roots must not contain one another")
    for r in m["roots"]:
        if not isinstance(r,dict) or set(r)!={"name","path","identity"} or r.get("name") not in expected or r.get("path")!=expected[r["name"]] or r["name"] in roots or not isinstance(r["identity"],dict) or not {"dev","inode","uid","gid","mode"}.issubset(r["identity"]) or not set(r["identity"]).issubset({"dev","inode","uid","gid","mode","nlink","size","mtime_ns","ctime_ns"}): raise ArchiveError("invalid manifest root")
        roots[r["name"]]=r["identity"]
    if set(roots)!=set(expected) or len(m["roots"])!=2: raise ArchiveError("missing manifest root")
    actual={}; snaps={}
    for label,path in expected.items():
        rr,scan,bypath=_scan(path,label)
        if any(k not in rr or rr[k]!=roots[label][k] for k in roots[label]): raise ArchiveError("root changed: "+label)
        snaps[label]=(rr,bypath)
        for row in scan: actual[(label,row["path"])]=row
    if set(actual)!=set(rows): raise ArchiveError("missing or additional manifest entry")
    for k,sealed in actual.items():
        plan=rows[k]
        for field in ("type","mode","uid","gid","size"):
            if plan.get(field)!=sealed[field]: raise ArchiveError("changed entry: %s:%s"%k)
        for field in ("dev","inode"):
            if field in plan and plan[field]!=sealed[field]: raise ArchiveError("changed identity: %s:%s"%k)
        if sealed["type"]=="regular" and plan.get("sha256")!=sealed["sha256"]: raise ArchiveError("changed contents: %s:%s"%k)
        if sealed["type"]=="symlink" and plan.get("target")!=sealed["target"]: raise ArchiveError("changed symlink: %s:%s"%k)
    return snaps,[actual[k] for k in sorted(selected)]

def _open_member(root,rootrow,paths,row):
    fd=_open_abs_dir(root)
    try:
        if not _same(os.fstat(fd),rootrow): raise ArchiveError("root changed before copy")
        bits=[]
        for part in row["path"].split("/")[:-1]:
            parent="/".join(bits); expected=paths.get(parent,rootrow)
            if _names(fd,parent or row["root"])!=expected["members"] or not _same(os.fstat(fd),expected): raise ArchiveError("directory membership changed before copy")
            bits.append(part); expected=paths["/".join(bits)]; child=os.open(part,_DIR,dir_fd=fd); os.close(fd); fd=child
            if not _same(os.fstat(fd),expected): raise ArchiveError("directory changed before copy")
        parent="/".join(bits); expected=paths.get(parent,rootrow)
        if _names(fd,parent or row["root"])!=expected["members"] or not _same(os.fstat(fd),expected): raise ArchiveError("directory membership changed before copy")
        leaf=row["path"].split("/")[-1]; child=os.open(leaf,_DIR if row["type"]=="directory" else _FILE,dir_fd=fd)
        try:
            if not _same(os.fstat(child),row): raise ArchiveError("required member changed before copy")
        except Exception: os.close(child); raise
        return child
    finally: os.close(fd)
def _tarinfo(name,row):
    i=tarfile.TarInfo(name); i.mode=row["mode"]; i.uid=row["uid"]; i.gid=row["gid"]; i.mtime=0; i.uname=i.gname=""; i.type=tarfile.DIRTYPE if row["type"]=="directory" else tarfile.REGTYPE; i.size=0 if row["type"]=="directory" else row["size"]; return i
class _Reader(object):
    def __init__(self,fd,size): self.fd=fd; self.left=size; self.total=0; self.h=hashlib.sha256()
    def read(self,n=-1):
        if self.left==0:return b""
        b=os.read(self.fd,min(self.left,self.left if n is None or n<0 else n))
        if not b: raise ArchiveError("short source read while archiving")
        self.left-=len(b);self.total+=len(b);self.h.update(b);return b
def _create_temp(pfd):
    for _ in range(128):
        name=".retention-archive."+next(tempfile._get_candidate_names())
        try:return name,os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=pfd)
        except OSError as e:
            if e.errno!=errno.EEXIST:raise
    raise ArchiveError("cannot allocate archive temporary")
def _output_parent(out,roots):
    parent,name=_parent(out); absolute=os.path.abspath(out)
    if any(os.path.commonpath((root,absolute))==root for root in roots): raise ArchiveError("output must be outside roots")
    pfd=_open_abs_dir(parent)
    try:
        try: os.stat(name,dir_fd=pfd,follow_symlinks=False)
        except OSError as e:
            if e.errno!=errno.ENOENT: raise
        else: raise ArchiveError("output already exists")
        return pfd,name
    except Exception: os.close(pfd);raise

def build_archive(manifest_path,candidate_root,metadata_backup_root,output):
    raw,m=_load(manifest_path); roots=[os.path.abspath(candidate_root),os.path.abspath(metadata_backup_root)]; snaps,members=_validate(m,*roots); pfd,outname=_output_parent(output,roots); tmp=None; outfd=None
    try:
        tmp,outfd=_create_temp(pfd)
        with os.fdopen(outfd,"wb",closefd=True) as out:
            outfd=None
            with tarfile.open(fileobj=out,mode="w",format=tarfile.USTAR_FORMAT) as tf:
                mi=tarfile.TarInfo("manifest.json");mi.size=len(raw);mi.mode=0o600;mi.uid=mi.gid=mi.mtime=0;mi.uname=mi.gname="";tf.addfile(mi,io.BytesIO(raw))
                for row in members:
                    root=roots[0] if row["root"]=="candidate" else roots[1]; rr,paths=snaps[row["root"]]; source=_open_member(root,rr,paths,row)
                    try:
                        info=_tarinfo(row["root"]+"/"+row["path"],row)
                        if row["type"]=="directory": tf.addfile(info)
                        else:
                            reader=_Reader(source,row["size"]);tf.addfile(info,reader)
                            if reader.left or reader.total!=row["size"] or reader.h.hexdigest()!=row["sha256"] or not _same(os.fstat(source),row): raise ArchiveError("required file changed during copy")
                    finally: os.close(source)
            out.flush();os.fsync(out.fileno())
        os.link(tmp,outname,src_dir_fd=pfd,dst_dir_fd=pfd,follow_symlinks=False);os.unlink(tmp,dir_fd=pfd);tmp=None;os.fsync(pfd)
    except Exception:
        if outfd is not None:
            try:os.close(outfd)
            except OSError:pass
        if tmp is not None:
            try:os.unlink(tmp,dir_fd=pfd)
            except OSError:pass
        raise
    finally: os.close(pfd)
    verify_archive(os.path.abspath(output),raw,members)

def _archive_name(name): return name=="manifest.json" or (isinstance(name,str) and (name.startswith("candidate/") or name.startswith("metadata-backup/")) and _safe_rel(name.split("/",1)[1]))
def verify_archive_bytes(data,manifest_raw=None,members=None):
    if not isinstance(data,bytes): raise ArchiveError("archive bytes are not bytes")
    try:
        with tarfile.open(fileobj=io.BytesIO(data),mode="r:") as tf:
            infos=tf.getmembers()
            if not infos or infos[0].name!="manifest.json":raise ArchiveError("manifest member missing")
            mi=infos[0]
            if not mi.isfile() or mi.type!=tarfile.REGTYPE or mi.mode!=0o600 or mi.uid!=0 or mi.gid!=0 or mi.mtime!=0 or mi.uname or mi.gname or mi.pax_headers:raise ArchiveError("manifest header is not normalized")
            f=tf.extractfile(mi)
            if f is None:raise ArchiveError("manifest unreadable")
            raw=f.read()
            if len(raw)!=mi.size:raise ArchiveError("short manifest member")
            if manifest_raw is not None and raw!=manifest_raw:raise ArchiveError("embedded manifest changed")
            try:m=json.loads(raw.decode("utf-8"),object_pairs_hook=_pairs)
            except (UnicodeError,ValueError) as e:raise ArchiveError("invalid embedded manifest: %s"%e)
            rows,selected=_selection(m); expected_rows={k:rows[k] for k in selected}
            if members is not None:
                supplied={(r["root"],r["path"]):r for r in members}
                if set(supplied)!=selected:raise ArchiveError("caller member set mismatch")
                expected_rows=supplied
            order=["manifest.json"]+[root+"/"+path for root,path in sorted(expected_rows)]
            expected=set(order); names=set(); actual_order=[]
            for i in infos:
                if i.name in names or not _archive_name(i.name) or i.name not in expected:raise ArchiveError("unsafe or unexpected archive member")
                names.add(i.name); actual_order.append(i.name)
                if i.pax_headers or i.uid<0 or i.gid<0 or i.mtime!=0 or i.uname or i.gname:raise ArchiveError("non-normalized archive member")
                if i.name=="manifest.json":continue
                root,rel=i.name.split("/",1);row=expected_rows[(root,rel)];typ=tarfile.DIRTYPE if row["type"]=="directory" else tarfile.REGTYPE
                if i.type!=typ or i.issym() or i.islnk() or i.mode!=row["mode"] or i.uid!=row["uid"] or i.gid!=row["gid"]:raise ArchiveError("archive member header changed: "+i.name)
                if row["type"]=="directory":
                    if i.size!=0:raise ArchiveError("directory has data")
                else:
                    f=tf.extractfile(i)
                    if f is None:raise ArchiveError("file member unreadable")
                    b=f.read()
                    if len(b)!=i.size or i.size!=row["size"] or hashlib.sha256(b).hexdigest()!=row["sha256"]:raise ArchiveError("archive member changed: "+i.name)
            if names!=expected:raise ArchiveError("missing archive member")
            if actual_order!=order:raise ArchiveError("archive member order changed")
    except (OSError,tarfile.TarError) as e:raise ArchiveError("archive verification failed: %s"%e)
    return True
def verify_archive(path,manifest_raw=None,members=None):
    return verify_archive_bytes(_read_regular_bytes(path,"archive"),manifest_raw,members)
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--manifest",required=True);p.add_argument("--candidate-root",required=True);p.add_argument("--metadata-backup-root",required=True);p.add_argument("--output",required=True);a=p.parse_args(argv);build_archive(a.manifest,a.candidate_root,a.metadata_backup_root,a.output);return 0
if __name__=="__main__":
    try:sys.exit(main())
    except (ArchiveError,OSError) as e:print("retention archive failed: %s"%e,file=sys.stderr);sys.exit(2)
