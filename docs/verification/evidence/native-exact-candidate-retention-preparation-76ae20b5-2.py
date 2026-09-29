#!/usr/bin/env python3
"""One-shot retention preparation, released only through an acyclic Git record.

The template is committed first.  A later release commit changes only the
release-hash literal below and adds a release JSON binding the prior template
commit/blobs.  Dynamic HEAD==upstream==FETCH_HEAD binds that release commit.
"""
from __future__ import print_function
import argparse, ctypes, errno, fcntl, hashlib, io, json, os, re, signal, stat, subprocess, sys, tarfile, time, types

SOURCE="/home/holden/mckernel"
MAIN_COMMIT="76ae20b523f57dee8e0fb1fb834caf5443f9f671"
IHK_COMMIT="3114d9e7101ad52030eb3effa849a5c108972a1f"
CANDIDATE="/dev/shm/mckernel-exact-candidate-76ae20b5-1"
BACKUP="/dev/shm/mckernel-exact-metadata-backup-76ae20b5-1"
CANDIDATE_ID={"dev":26,"inode":58679,"uid":1000,"gid":1000,"mode":0o755}
BACKUP_ID={"dev":26,"inode":69465,"uid":1000,"gid":1000,"mode":0o755}
WORK="/home/holden/mckernel-work/scratch"
DISK_CANDIDATE=WORK+"/mckernel-exact-candidate-76ae20b5-disk-1"
DISK_BACKUP=WORK+"/mckernel-exact-metadata-backup-76ae20b5-disk-1"
DISK_CANDIDATE_ID=dict(CANDIDATE_ID,dev=1831,inode=4194306)
DISK_BACKUP_ID=dict(BACKUP_ID,dev=1831,inode=4204970)
DISK_INVENTORY=WORK+"/native-exact-candidate-disk-copy-correction-76ae20b5-dest-final.json"
DISK_SHA="842f4522c0ff318aee68cb3387eca604e435f06aef334e125c7d2c6897d526ae"
SEAL=WORK+"/native-exact-candidate-disk-validation-76ae20b5-2-evidence/corrupt-tmpfs-archive.bin"
SEAL_SHA="192f8fe161ee0e486b0c0532f64bc34bb0684da2b113d01d13dc4f4ba7bb1c2c"
SEAL_SIZE=40004941
CORRUPT_MEMBER="docs/verification/evidence/stability-linux-collector-storage-fault-v2-source-review-input-20260916-57.tar.gz"
PLANNER="scripts/native_exact_candidate_retention_capsule.py"
ARCHIVER="scripts/native_exact_candidate_retention_archive.py"
PLANNER_SHA="d0bd9ce3b1fe110b71aee47362728997c7500216802e5740befd57b8273bbae1"
ARCHIVER_SHA="6a28184e13e4ddec3a5e2fe6229c618929df29f235901083d55918c8291ac06e"
PACKET_TEST="scripts/tests/test_native_exact_candidate_retention_preparation_76ae20b5_v2.py"
RELEASE_PATH="docs/verification/evidence/stability-native-exact-candidate-retention-preparation-76ae20b5-2.release.json"
RELEASE_SHA256="RELEASE_HASH_REQUIRED"
OUT=SOURCE+"/docs/verification/evidence/stability-native-exact-candidate-retention-76ae20b5-20260929-2.inventory.json"
ARCHIVE=SOURCE+"/docs/verification/evidence/stability-native-exact-candidate-retention-76ae20b5-20260929-2.tar"
SCRATCH=WORK+"/native-exact-candidate-retention-76ae20b5-2"
CLAIM=SCRATCH+"/claim.json"
# All future preparation, retirement and build participants must acquire COMMON.
# Legacy participants are excluded too by owning their actual O_EXCL lease paths.
COMMON=WORK+"/native-exact-candidate-operational-exclusion-76ae20b5.json"
LEASES=tuple(WORK+"/"+name for name in (
 "native-exact-build-lease-76ae20b5-1.json",
 "native-exact-build-lease-76ae20b5-disk-1.json",
 "native-exact-build-lease-76ae20b5-disk-validation-2.json",
 "native-exact-build-lease-76ae20b5-disk-retirement-1.json"))
TOMBSTONE=WORK+"/native-exact-candidate-retirement-tombstone-76ae20b5.json"
NOFOLLOW=getattr(os,"O_NOFOLLOW",0); NONBLOCK=getattr(os,"O_NONBLOCK",0); DFLAGS=os.O_RDONLY|getattr(os,"O_DIRECTORY",0)|NOFOLLOW|NONBLOCK; FFLAGS=os.O_RDONLY|NOFOLLOW|NONBLOCK
def fail(s): raise RuntimeError(s)
def sha_b(b): return hashlib.sha256(b).hexdigest()
def same(a,b): return (a.st_dev,a.st_ino,a.st_mode,a.st_uid,a.st_gid,a.st_nlink,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(b.st_dev,b.st_ino,b.st_mode,b.st_uid,b.st_gid,b.st_nlink,b.st_size,b.st_mtime_ns,b.st_ctime_ns)
def open_dir(path):
    fd=os.open("/",DFLAGS)
    try:
        for x in os.path.abspath(path).split("/")[1:]:
            if not x: continue
            before=os.stat(x,dir_fd=fd,follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode): fail("non-directory ancestor: "+path)
            child=os.open(x,DFLAGS,dir_fd=fd)
            if not same(before,os.fstat(child)): os.close(child);fail("directory changed: "+path)
            os.close(fd);fd=child
        return fd
    except BaseException: os.close(fd);raise
def snapshot(path,label):
    parent,name=os.path.split(os.path.abspath(path)); pfd=open_dir(parent)
    try:
        before=os.stat(name,dir_fd=pfd,follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1: fail(label+" is not a standalone regular file")
        fd=os.open(name,FFLAGS,dir_fd=pfd)
        try:
            if not same(before,os.fstat(fd)): fail(label+" changed while opening")
            data=b"".join(iter(lambda:os.read(fd,1048576),b""))
            if len(data)!=before.st_size or not same(before,os.fstat(fd)) or not same(before,os.stat(name,dir_fd=pfd,follow_symlinks=False)): fail(label+" changed while reading")
            return {"bytes":data,"sha256":sha_b(data),"stat":before}
        finally: os.close(fd)
    finally: os.close(pfd)
def sha(path): return snapshot(path,"hash input")["sha256"]
def fsync_parent(path):
    fd=open_dir(os.path.dirname(path))
    try: os.fsync(fd)
    finally: os.close(fd)
def exclusive(path,payload):
    parent,name=os.path.split(os.path.abspath(path));pfd=open_dir(parent)
    try:
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|NOFOLLOW,0o600,dir_fd=pfd)
        try:
            b=(json.dumps(payload,sort_keys=True,separators=(",",":"))+"\n").encode(); pos=0
            while pos<len(b):
                n=os.write(fd,b[pos:])
                if n<=0: fail("short durable write")
                pos+=n
            os.fsync(fd)
        finally: os.close(fd)
        os.fsync(pfd)
    finally: os.close(pfd)
def exclusive_bytes(path,data):
    parent,name=os.path.split(os.path.abspath(path));pfd=open_dir(parent)
    try:
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|NOFOLLOW,0o600,dir_fd=pfd)
        try:
            pos=0
            while pos<len(data):
                count=os.write(fd,data[pos:])
                if count<=0:fail("short evidence write")
                pos+=count
            os.fsync(fd)
        finally:os.close(fd)
        os.fsync(pfd)
    finally:os.close(pfd)
def absent(path):
    if os.path.lexists(path): fail("fresh path exists: "+path)
    fd=open_dir(os.path.dirname(path));os.close(fd)
def prepare_scratch(out,archive,scratch,children):
    """Reserve the parent before testing only its defined child evidence paths."""
    for path in (out,archive,scratch): absent(path)
    os.mkdir(scratch,0o700);fsync_parent(scratch)
    for name in children: absent(os.path.join(scratch,name))
def git_env(): return {"PATH":"/usr/bin:/bin","HOME":"/nonexistent","LANG":"C","LC_ALL":"C","TZ":"UTC","GIT_CONFIG_NOSYSTEM":"1","GIT_CONFIG_GLOBAL":"/dev/null","GIT_TERMINAL_PROMPT":"0","GIT_NO_REPLACE_OBJECTS":"1","GIT_OPTIONAL_LOCKS":"0","GIT_EXTERNAL_DIFF":"0","GIT_PAGER":"cat","GIT_EDITOR":"true","GIT_ASKPASS":"/bin/false"}
def validate_git_config(raw):
    """Parse inert bytes with Git's grammar, without includes or repo discovery.

    Credential helpers are never effective in this packet: all repository Git
    commands are local-only and explicitly reset the base and reviewed scoped
    helper. The sole shell-shaped allowance is the exact live GitHub setting.
    """
    command=["/usr/bin/git","config","--null","--no-includes","--file","-","--list"]
    parsed=subprocess.check_output(command,input=raw,cwd="/",env=git_env(),stderr=subprocess.PIPE,timeout=30)
    for record in parsed.split(b"\0"):
        if not record:continue
        key,separator,value=record.partition(b"\n")
        try:key=key.decode("ascii").lower();value=value.decode("utf-8")
        except UnicodeError:fail("unsafe Git config encoding")
        section=key.split(".",1)[0];leaf=key.rsplit(".",1)[-1]
        if section=="extensions":
            if key!="extensions.worktreeconfig" or value!="true":fail("unsafe Git config extension: "+key)
            continue
        if section in ("include","includeif","alias","filter") or key in ("core.worktree","core.hookspath","core.fsmonitor","core.sshcommand","core.gitproxy","core.askpass","core.pager","core.editor","sequence.editor","interactive.difffilter","diff.external"):
            fail("unsafe Git config: "+key)
        if (section=="diff" and leaf in ("command","textconv")) or (section=="merge" and leaf=="driver") or (section in ("gpg","ssh") and leaf=="program") or (section=="remote" and leaf in ("uploadpack","receivepack","vcs")):
            fail("unsafe Git config execution: "+key)
        if section=="protocol" and (leaf!="allow" or value!="never"):
            fail("unsafe Git config protocol: "+key)
        if section=="credential" and leaf=="helper":
            inert_builtin=value in ("","store","cache")
            reviewed_github=key=="credential.https://github.com.helper" and value=="!gh auth git-credential"
            if not (inert_builtin or reviewed_github):fail("unsafe Git config credential helper")
        if section=="credential" and leaf in ("interactive","guiprompt") and value not in ("false","never"):
            fail("unsafe Git config credential prompting")
    return parsed

def safe_git_metadata(repo):
    """Fingerprint bounded Git control-plane state, never object/log payloads."""
    meta=os.path.join(repo,".git"); st=os.lstat(meta)
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode): fail(".git must be a real directory (no gitfile)")
    digest=hashlib.sha256()
    controls={"config","config.worktree","HEAD","FETCH_HEAD","index","packed-refs","shallow","ORIG_HEAD"}
    configs={}
    def visit(path,rel,read_contents=True):
        names=sorted(os.listdir(path));digest.update(rel.encode("utf-8","surrogateescape")+b"\0"+"\0".join(names).encode("utf-8","surrogateescape"))
        for name in names:
            full=os.path.join(path,name); node=os.lstat(full)
            if stat.S_ISLNK(node.st_mode): fail("Git metadata symlink")
            child=name if not rel else rel+"/"+name
            if stat.S_ISDIR(node.st_mode):
                # Objects and logs may be huge; retain their directory names but
                # never open immutable object-pack/blob or reflog payloads.
                if child=="objects/info":
                    if "alternates" in os.listdir(full): fail("shared/alternate Git metadata")
                    visit(full,child,False)
                elif child in ("objects","logs") or child.startswith("objects/") or child.startswith("logs/"):
                    visit(full,child,False)
                else: visit(full,child,read_contents)
            elif not stat.S_ISREG(node.st_mode): fail("unsupported Git metadata node")
            elif ((rel=="" and name=="commondir") or
                  (rel=="objects/info" and name=="alternates")):
                fail("shared/alternate Git metadata")
            elif read_contents and (rel=="" and name in controls or rel=="refs" or rel.startswith("refs/")):
                value=snapshot(full,"Git control metadata")["bytes"]
                digest.update(child.encode("utf-8","surrogateescape")+b"\0"+hashlib.sha256(value).digest())
                if child in ("config","config.worktree"):configs[child]=value
    visit(meta,"",True)
    for name,raw in configs.items():
        validate_git_config(raw)
        if snapshot(os.path.join(meta,name),"Git config post-parse")["bytes"]!=raw:fail("Git config changed during validation")
    hooks=os.path.join(meta,"hooks")
    if os.path.isdir(hooks):
        with os.scandir(hooks) as scan:
            if any(not x.name.endswith(".sample") for x in scan): fail("active Git hook")
    return digest.hexdigest()
def git_prefix(repo):
    return ["/usr/bin/git","--no-optional-locks","-c","core.hooksPath=/dev/null","-c","core.fsmonitor=false","-c","credential.helper=","-c","credential.https://github.com.helper=","-c","credential.interactive=false","-c","protocol.allow=never","-c","protocol.file.allow=never","-C",repo]
def git(repo,args):
    local_revision=len(args)==2 and args[0]=="rev-parse" and args[1] in ("HEAD","@{upstream}","FETCH_HEAD")
    local_pair=len(args)==4 and args[:2] in (["merge-base","--is-ancestor"],["diff","--name-only"]) and all(re.fullmatch(r"[0-9a-f]{40}",v) for v in args[2:])
    if not (local_revision or local_pair):fail("nonlocal or unreviewed Git command")
    return subprocess.check_output(git_prefix(repo)+args,env=git_env(),stderr=subprocess.PIPE,timeout=30).decode().strip()
def git_blob(repo,commit,path):
    if not re.fullmatch(r"[0-9a-f]{40}",commit) or not path or path.startswith("/") or any(p in ("",".","..") for p in path.split("/")) or "\0" in path:fail("invalid local Git blob")
    return subprocess.check_output(git_prefix(repo)+["show",commit+":"+path],env=git_env(),stderr=subprocess.PIPE,timeout=30)
def normalize_packet(b,release_sha=RELEASE_SHA256): return b.replace(release_sha.encode(),b"RELEASE_HASH_REQUIRED")
def admit_repository(cfg):
    """Acyclic template-commit -> release-commit admission (testable in temp Git)."""
    repo=cfg["source"]; before=safe_git_metadata(repo); head,upstream,fetched=(git(repo,["rev-parse",x]) for x in ("HEAD","@{upstream}","FETCH_HEAD"))
    if head!=upstream or head!=fetched: fail("HEAD/upstream/FETCH_HEAD release mismatch")
    release_snapshot=snapshot(os.path.join(repo,cfg["release_path"]),"release")
    if release_snapshot["sha256"]!=cfg["release_sha256"] or git_blob(repo,fetched,cfg["release_path"])!=release_snapshot["bytes"]: fail("live release is not exact FETCH_HEAD blob/hash")
    try: release=json.loads(release_snapshot["bytes"].decode())
    except (ValueError,UnicodeError): fail("invalid release JSON")
    wanted={"status","one_shot","mutation_scope","cleanup","retirement","runtime_acceptance","template_commit","template","inputs"}
    if set(release)!=wanted or release["status"]!="PASS_ONE_SHOT_RETENTION_PREPARATION" or not release["one_shot"] or release["mutation_scope"]!="manifest_archive_only" or release["cleanup"] or release["retirement"] or release["runtime_acceptance"]: fail("invalid release scope")
    if release["inputs"]!=cfg["inputs"]: fail("exact roots/commits/outputs/tools input binding")
    t=release["template"]; need={"packet_path","packet_sha256","test_path","test_sha256","normalised_packet_sha256"}
    if set(t)!=need or t["packet_path"]!=cfg["packet_path"] or t["test_path"]!=cfg["test_path"]: fail("template fields")
    template_commit=release["template_commit"]
    if not isinstance(template_commit,str) or not template_commit: fail("missing immutable prior template commit")
    if template_commit==fetched: fail("template commit is not prior")
    try: git(repo,["merge-base","--is-ancestor",template_commit,fetched])
    except subprocess.CalledProcessError: fail("template commit is not an immutable prior ancestor")
    old_packet=git_blob(repo,template_commit,cfg["packet_path"]); old_test=git_blob(repo,template_commit,cfg["test_path"])
    if sha_b(old_packet)!=t["packet_sha256"] or sha_b(old_test)!=t["test_sha256"] or sha_b(old_packet)!=t["normalised_packet_sha256"]: fail("template blob digest")
    live_packet=snapshot(os.path.join(repo,cfg["packet_path"]),"packet")["bytes"];live_test=snapshot(os.path.join(repo,cfg["test_path"]),"packet test")["bytes"]
    if git_blob(repo,fetched,cfg["packet_path"])!=live_packet or git_blob(repo,fetched,cfg["test_path"])!=live_test: fail("live packet/test is not exact FETCH_HEAD blob")
    if normalize_packet(live_packet,cfg["release_sha256"])!=old_packet: fail("non-mechanical packet change")
    if live_test!=old_test: fail("packet test changed after template")
    changed=set(git(repo,["diff","--name-only",template_commit,fetched]).splitlines())
    if changed!={cfg["packet_path"],cfg["release_path"]}: fail("release changed paths are not exact")
    for path,expected in cfg["support_hashes"].items():
        live=snapshot(os.path.join(repo,path),"support test")["bytes"]
        if sha_b(live)!=expected or git_blob(repo,fetched,path)!=live: fail("support test blob/hash mismatch: "+path)
    if safe_git_metadata(repo)!=before: fail("Git metadata bytes changed")
    return release_snapshot,release
def capacity():
    got={}
    for n,p,floor in (("host","/",16<<30),("scratch","/home/holden/mckernel-work/scratch",12<<30),("tmpfs","/dev/shm",4<<30)):
        got[n]=os.statvfs(p).f_bavail*os.statvfs(p).f_frsize
        if got[n]<floor: fail(n+" capacity floor")
    with open("/proc/meminfo") as f: got["memory"]=next((int(x.split()[1])*1024 for x in f if x.startswith("MemAvailable:")),0)
    if got["memory"]<4<<30: fail("memory capacity floor")
    return got
def capacity_delta(before,after,maxima={"host":512<<20,"scratch":512<<20,"tmpfs":512<<20,"memory":2<<30}):
    for n,m in maxima.items():
        if before[n]-after[n]>m: fail("allocation delta exceeds bound: "+n)
def proc_identity(pid):
    try:
        pid=int(pid)
        with open("/proc/%d/stat"%pid) as f: raw=f.read()
        end=raw.rfind(")");fields=raw[end+2:].split()
        return {"pid":pid,"state":fields[0],"flags":int(fields[6]),"ppid":int(fields[1]),"pgid":int(fields[2]),"sid":int(fields[3]),"starttime":int(fields[19])}
    except (OSError,IOError,TypeError,ValueError,IndexError): return None
def proc_vanished(pid):
    """Return true only when /proc/<pid> is confirmed absent."""
    try: os.stat("/proc/%s"%pid,follow_symlinks=False); return False
    except OSError as exc: return exc.errno in (errno.ENOENT,errno.ESRCH)
def census(lease_paths=()):
    ours={os.getpid()}; parent=os.getppid()
    while parent>1 and parent not in ours:
        ours.add(parent)
        try:
            with open("/proc/%d/stat"%parent) as f: parent=int(f.read().split()[3])
        except (OSError,IOError,ValueError,IndexError): break
    relevant={"make","cmake","ninja","cc","gcc","clang","rustc","cargo","qemu","mcexec"};found=[]
    for name in os.listdir("/proc"):
        if not name.isdigit() or int(name) in ours: continue
        try: base=os.path.basename(os.readlink("/proc/"+name+"/exe"))
        except OSError as exc:
            if exc.errno in (errno.ENOENT,errno.ESRCH) and proc_vanished(name): continue
            try:
                with open("/proc/"+name+"/cmdline","rb") as cmdline:
                    first=cmdline.read().split(b"\0",1)[0]
                base=os.path.basename(first.decode("utf-8","surrogateescape")) if first else ""
            except OSError as second:
                if second.errno in (errno.ENOENT,errno.ESRCH) and proc_vanished(name): continue
                fail("unreadable process identity: "+name)
        if not base:
            identity=proc_identity(name)
            if identity is None:
                if proc_vanished(name): continue
                fail("unstable empty process identity: "+name)
            if identity["state"]=="Z" or identity["flags"] & 0x00200000: continue
            fail("live userspace process has empty identity: "+name)
        if base in relevant or base.startswith("qemu-system-"):
            ident=proc_identity(int(name))
            if ident is None:
                if proc_vanished(name): continue
                fail("unstable conflicting process: "+name)
            found.append(dict(ident,basename=base))
    if found: fail("conflicting executable census: "+repr(found))
    for p in lease_paths:
        if os.path.lexists(p):
            try: record=json.loads(snapshot(p,"competing lease")["bytes"].decode())
            except (ValueError,UnicodeError): fail("unreadable competing lease")
            now=proc_identity(record.get("pid",-1)) if isinstance(record,dict) else None
            if now and now.get("starttime")==record.get("starttime"): fail("live competing lease: "+p)
            fail("stale competing lease requires operator review: "+p)
    return {"self":proc_identity(os.getpid()),"observed":found}
def retired(pgid,deadline=2):
    end=time.time()+deadline
    while time.time()<end:
        alive=[]
        for n in os.listdir("/proc"):
            if n.isdigit():
                try:
                    if os.getpgid(int(n))==pgid: alive.append(n)
                except OSError: pass
        if not alive:return True
        time.sleep(.02)
    return False
def seal_evidence(*paths):
    for path in paths:
        parent,name=os.path.split(path);pfd=open_dir(parent)
        try:
            fd=os.open(name,os.O_RDONLY|NOFOLLOW|NONBLOCK,dir_fd=pfd)
            try:
                if not stat.S_ISREG(os.fstat(fd).st_mode):fail("evidence is not regular")
                os.fsync(fd)
            finally:os.close(fd)
            os.fsync(pfd)
        finally:os.close(pfd)
def manifest_contract(m,expected_roots=None,expected_revisions=None,expected_links=None):
    if set(m)!={"format","roots","revisions","entries","capsule_required"} or m["format"]!="native-exact-candidate-retention-v1":fail("manifest schema")
    roots={x.get("name"):x for x in m["roots"] if isinstance(x,dict)}
    if len(roots)!=2 or set(roots)!={"candidate","metadata-backup"}:fail("manifest roots")
    if expected_roots is not None:
        for n,(path,ident) in expected_roots.items():
            if roots[n].get("path")!=os.path.abspath(path) or roots[n].get("identity")!=ident:fail("manifest root identity")
    if expected_revisions is not None and m["revisions"]!=expected_revisions:fail("manifest revisions")
    rows={};required=set();links=[]
    for x in m["entries"]:
        if not isinstance(x,dict) or x.get("root") not in roots or x.get("type") not in ("directory","regular","symlink") or x.get("classification") not in ("capsule-required","reconstructible") or not isinstance(x.get("path"),str) or not x["path"] or x["path"].startswith("/") or ".." in x["path"].split("/"):fail("manifest entry")
        key=(x["root"],x["path"])
        if key in rows:fail("duplicate manifest entry")
        rows[key]=x
        if x["classification"]=="capsule-required":required.add(x["root"]+":"+x["path"])
        if x["type"]=="symlink":links.append(x)
        metadata=x["root"]=="metadata-backup" or x["path"]==".git" or x["path"].startswith(".git/") or x["path"]=="ihk/.git" or x["path"].startswith("ihk/.git/")
        if metadata and x["classification"]!="capsule-required":fail("metadata classification coverage")
    if set(m["capsule_required"])!=required or len(m["capsule_required"])!=len(required):fail("capsule full coverage")
    if any(x["root"]!="candidate" or x["classification"]!="reconstructible" for x in links):fail("link classification")
    if expected_links is not None and len(links)!=expected_links:fail("exact reconstructible link count")
    return rows
def postflight_equal(admitted,postflight):
    if admitted["bytes"]!=postflight["bytes"]:fail("post-archive source descendant mutation")
def check_manifest_archive(ms,ars,verifier):
    m=json.loads(ms["bytes"].decode()); rows=manifest_contract(m); verifier.verify_archive_bytes(ars["bytes"],ms["bytes"])
    selected=set()
    for k,x in rows.items():
        if x["type"]!="symlink" and (x["root"]=="metadata-backup" or x["classification"]=="capsule-required"): selected.add(k)
    for root,path in list(selected):
        bits=path.split("/")[:-1]
        while bits: selected.add((root,"/".join(bits)));bits.pop()
    with tarfile.open(fileobj=io.BytesIO(ars["bytes"]),mode="r:") as tf:
        members=tf.getmembers(); expected=["manifest.json"]+[a+"/"+b for a,b in sorted(selected)]
        if [x.name for x in members]!=expected: fail("exact archive member-name/order/ancestor closure mismatch")
        for member in members[1:]:
            root,path=member.name.split("/",1);row=rows[(root,path)]
            if (member.mode,member.uid,member.gid,member.mtime)!=(row["mode"],row["uid"],row["gid"],0): fail("archive member metadata mismatch")
    return m,len(members)
def root_id(path):
    s=os.lstat(path)
    if not stat.S_ISDIR(s.st_mode) or stat.S_ISLNK(s.st_mode):fail("root is not real directory")
    return {"dev":s.st_dev,"inode":s.st_ino,"uid":s.st_uid,"gid":s.st_gid,"mode":stat.S_IMODE(s.st_mode)}

class SignalLatch:
    """Signals record intent; cleanup cannot be interrupted by another signal."""
    def __init__(self): self.received=[]; self.previous={}
    def __enter__(self):
        for signum in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP):
            self.previous[signum]=signal.signal(signum,lambda n,f:self.received.append(n))
        return self
    def check(self):
        if self.received: raise KeyboardInterrupt("latched signals: %r"%self.received)
    def __exit__(self,*args):
        for n,handler in self.previous.items(): signal.signal(n,handler)

def sealed_fd(data):
    libc=ctypes.CDLL(None,use_errno=True)
    create=libc.memfd_create;create.argtypes=(ctypes.c_char_p,ctypes.c_uint);create.restype=ctypes.c_int
    fd=create(b"retention-sealed",3) # Linux MFD_CLOEXEC | MFD_ALLOW_SEALING
    if fd<0:raise OSError(ctypes.get_errno(),"memfd_create")
    try:
        pos=0
        while pos<len(data):
            wrote=os.write(fd,data[pos:])
            if wrote<=0: fail("short seal write")
            pos+=wrote
        os.lseek(fd,0,os.SEEK_SET)
        fcntl.fcntl(fd,1033,15) # Linux F_ADD_SEALS: WRITE | GROW | SHRINK | SEAL
        return fd
    except BaseException: os.close(fd);raise

def load_bytes(data,name):
    module=types.ModuleType(name);module.__file__="<authenticated-"+name+">"
    exec(compile(data,module.__file__,"exec"),module.__dict__)
    return module

def authenticate_helpers():
    result={}
    for path,expected in ((PLANNER,PLANNER_SHA),(ARCHIVER,ARCHIVER_SHA)):
        sealed=snapshot(os.path.join(SOURCE,path),"helper")
        if sealed["sha256"]!=expected: fail("helper digest mismatch")
        result[path]=sealed
    return result

def descendant_census():
    rows={}
    for name in os.listdir("/proc"):
        if name.isdigit():
            row=proc_identity(int(name))
            if row is not None: rows[row["pid"]]=row
            elif not proc_vanished(name): fail("unreadable child census identity")
    descendants={os.getpid()}
    while True:
        expanded=descendants|{p for p,r in rows.items() if r["ppid"] in descendants}
        if expanded==descendants:break
        descendants=expanded
    return {p:rows[p] for p in descendants if p!=os.getpid()}

def run(argv,label,scratch=SCRATCH,timeout=1800,pass_fds=(),latch=None):
    """Own one bounded session; prove group and adopted descendants disappear."""
    if latch is None:
        with SignalLatch() as local:
            return run(argv,label,scratch,timeout,pass_fds,local)
    latch.check()
    out=os.path.join(scratch,label+".stdout");err=os.path.join(scratch,label+".stderr")
    status=os.path.join(scratch,label+".status");identity=None;proc=None;error=None
    seen={};started=time.monotonic();retirement=False;rc=None
    # Trusted helpers do not daemonize, but subreaping also owns a forked orphan.
    libc=ctypes.CDLL(None,use_errno=True);prior=ctypes.c_int()
    if libc.prctl(37,ctypes.byref(prior),0,0,0)!=0 or libc.prctl(36,1,0,0,0)!=0:fail("cannot own descendants")
    try:
        if descendant_census():fail("packet already has children")
        with open(out,"xb") as so,open(err,"xb") as se:
            proc=subprocess.Popen(argv,stdout=so,stderr=se,env=git_env(),start_new_session=True,close_fds=True,pass_fds=pass_fds)
        identity=proc_identity(proc.pid)
        if identity is None or identity["pgid"]!=proc.pid or identity["sid"]!=proc.pid:fail("child identity/session unavailable")
        exclusive(os.path.join(scratch,label+".identity.json"),identity)
        while proc.poll() is None:
            seen.update(descendant_census());latch.check()
            if time.monotonic()-started>timeout:raise subprocess.TimeoutExpired(argv,timeout)
            time.sleep(.02)
        rc=proc.wait();latch.check()
        if rc:fail(label+" failed rc="+str(rc))
    except BaseException as exc:error=exc
    finally:
        # Handlers keep latching throughout TERM/KILL/wait and durable reporting.
        if proc is not None:
            deadline=time.monotonic()+5
            while True:
                observed=descendant_census();seen.update(observed)
                group=[]
                for name in os.listdir("/proc"):
                    if name.isdigit():
                        row=proc_identity(int(name))
                        if row and row["pgid"]==proc.pid:group.append(row)
                live={p:r for p,r in seen.items() if (proc_identity(p) or {}).get("starttime")==r["starttime"]}
                if not observed and not group and not live:retirement=True;break
                for row in list(live.values())+group:
                    now=proc_identity(row["pid"])
                    if now and now["starttime"]==row["starttime"]:
                        try:os.kill(row["pid"],signal.SIGKILL)
                        except ProcessLookupError:pass
                try:proc.wait(timeout=.05)
                except subprocess.TimeoutExpired:pass
                while True:
                    try:
                        pid,_=os.waitpid(-1,os.WNOHANG)
                        if pid==0:break
                    except ChildProcessError:break
                if time.monotonic()>deadline:break
                time.sleep(.02)
        else:retirement=not descendant_census()
        if retirement:libc.prctl(36,prior.value,0,0,0)
        # Failure to prove disappearance overrides ordinary success or error.
        if not retirement:error=RuntimeError("descendant disappearance unproven; preserve all identities and exclusion")
        if os.path.exists(out) and os.path.exists(err):seal_evidence(out,err)
        result={"label":label,"returncode":rc,"identity":identity,"descendants":list(seen.values()),"descendants_absent":retirement,"signals":list(latch.received),"elapsed":time.monotonic()-started,"error":None if error is None else type(error).__name__+": "+str(error)}
        exclusive(status,result)
    if error is not None:raise error
    latch.check()
    return result

def run_helper(helper,args,label,latch,manifest=None):
    """Execute the authenticated snapshot; never reopen executable source paths."""
    sourcefd=sealed_fd(helper["bytes"]);manifestfd=None
    loader="import os,sys; f=int(sys.argv.pop(1)); raw=os.fdopen(f,'rb').read(); g={'__name__':'sealed_helper','__file__':'<sealed-helper>'}; exec(compile(raw,g['__file__'],'exec'),g); "
    fds=[sourcefd];argv=[sys.executable,"-I","-B","-c",loader,str(sourcefd)]
    try:
        if manifest is not None:
            manifestfd=sealed_fd(manifest["bytes"]);fds.append(manifestfd)
            argv[4]+="f=int(sys.argv.pop(1)); mr=os.fdopen(f,'rb').read(); g['_load']=lambda path:(mr,g['json'].loads(mr.decode(),object_pairs_hook=g['_pairs'])); "
            argv.append(str(manifestfd))
        argv[4]+="sys.exit(g['main'](sys.argv[1:]))"
        return run(argv+args,label,pass_fds=tuple(fds),latch=latch)
    finally:
        os.close(sourcefd)
        if manifestfd is not None:os.close(manifestfd)

class Exclusion:
    """Common ownership plus actual legacy build/retirement O_EXCL leases.

    Partial acquisitions remain as failure evidence. No stale-lock reclamation.
    A permanent retirement tombstone is deliberately never created or removed.
    """
    def __init__(self,paths):self.paths=tuple(paths);self.owned={}
    def acquire(self):
        for path in self.paths:absent(path)
        identity=proc_identity(os.getpid())
        if identity is None:fail("owner identity unavailable")
        with open("/proc/sys/kernel/random/boot_id") as stream:boot=stream.read().strip()
        for path in self.paths:
            exclusive(path,{"schema":"mckernel.operational-exclusion.v1","operation":"retention-preparation","boot_id":boot,**identity})
            self.owned[path]=snapshot(path,"owned exclusion")
    def verify(self):
        for path,expected in self.owned.items():
            current=snapshot(path,"owned exclusion")
            if current["bytes"]!=expected["bytes"] or not same(current["stat"],expected["stat"]):fail("exclusion replaced")
        if len(self.owned)!=len(self.paths):fail("incomplete exclusion")
    def release(self):
        self.verify()
        for path in reversed(self.paths):os.unlink(path);fsync_parent(path)

def disk_inventory(verifier,roots=None):
    """Reproduce the accepted full inventory, including inode/time snapshots."""
    roots=roots or (("candidate",DISK_CANDIDATE),("backup",DISK_BACKUP))
    rows=[];snapshots=[]
    for label,path in roots:
        root,children,_=verifier._scan(path,label)
        for entry in [dict(root,path=".",root=label)]+children:
            typ={"directory":"dir","regular":"file","symlink":"symlink"}[entry["type"]]
            row={k:entry[k] for k in ("root","path","mode","uid","gid","mtime_ns")};row["type"]=typ
            if typ!="dir":
                row["size"]=entry["size"]
                key="sha256" if typ=="file" else "target";row[key]=entry[key]
            kind={"dir":stat.S_IFDIR,"file":stat.S_IFREG,"symlink":stat.S_IFLNK}[typ]
            identity=[entry["dev"],entry["inode"],kind|entry["mode"],entry["size"],entry["nlink"],entry["uid"],entry["gid"],entry["mtime_ns"],entry["ctime_ns"]]
            rows.append(row);snapshots.append({"root":label,"path":entry["path"],"identity":identity})
    return (json.dumps({"schema":"mckernel.exact-tree-inventory.v2","roots":[r[0] for r in roots],"rows":rows,"snapshots":snapshots},sort_keys=True,separators=(",",":"))+"\n").encode()

def protected(verifier,accepted):
    if root_id(DISK_CANDIDATE)!=DISK_CANDIDATE_ID or root_id(DISK_BACKUP)!=DISK_BACKUP_ID:fail("protected disk root changed")
    seal=snapshot(SEAL,"corruption seal");st=seal["stat"]
    if (st.st_dev,st.st_ino,st.st_size)!=(1831,4849667,SEAL_SIZE) or seal["sha256"]!=SEAL_SHA:fail("protected corruption seal changed")
    current=disk_inventory(verifier)
    if current!=accepted["bytes"] or sha_b(current)!=DISK_SHA:fail("complete protected disk inventory differs")
    return sha_b(current)

def corruption_contract(manifest,archive_bytes):
    rows=manifest_contract(manifest,{"candidate":(CANDIDATE,CANDIDATE_ID),"metadata-backup":(BACKUP,BACKUP_ID)},{"main":MAIN_COMMIT,"ihk":IHK_COMMIT},49)
    row=rows.get(("candidate",CORRUPT_MEMBER),{})
    if row.get("classification")!="capsule-required" or row.get("sha256")!=SEAL_SHA or row.get("size")!=SEAL_SIZE:fail("corrupt member must be capsule-required")
    with tarfile.open(fileobj=io.BytesIO(archive_bytes),mode="r:") as archive:
        member=archive.extractfile("candidate/"+CORRUPT_MEMBER)
        if member is None or sha_b(member.read())!=SEAL_SHA:fail("corrupt archive member changed")

def finish(receipt,checks,sync_paths,payload,latch,release=lambda:None):
    """Every final validation and durability operation precedes PASS creation."""
    for check in checks:check();latch.check()
    seal_evidence(*sync_paths);latch.check();release();latch.check()
    exclusive(receipt,payload)

def execute(provided_release_sha=None):
    if RELEASE_SHA256=="RELEASE_HASH_REQUIRED" or provided_release_sha!=RELEASE_SHA256:
        print("DRAFT_NOT_RELEASED",file=sys.stderr);return 3
    if os.geteuid()==0:fail("ordinary user required")
    inputs={"main":MAIN_COMMIT,"ihk":IHK_COMMIT,"candidate":[CANDIDATE,CANDIDATE_ID],"backup":[BACKUP,BACKUP_ID],"disk_candidate":[DISK_CANDIDATE,DISK_CANDIDATE_ID],"disk_backup":[DISK_BACKUP,DISK_BACKUP_ID],"disk_inventory":[DISK_INVENTORY,DISK_SHA],"seal":[SEAL,1831,4849667,SEAL_SIZE,SEAL_SHA],"corrupt_member":CORRUPT_MEMBER,"planner_sha256":PLANNER_SHA,"archiver_sha256":ARCHIVER_SHA,"out":OUT,"archive":ARCHIVE,"scratch":SCRATCH,"common":COMMON,"leases":list(LEASES),"tombstone":TOMBSTONE}
    cfg={"source":SOURCE,"release_path":RELEASE_PATH,"release_sha256":RELEASE_SHA256,"packet_path":os.path.relpath(__file__,SOURCE),"test_path":PACKET_TEST,"support_hashes":{PLANNER:PLANNER_SHA,ARCHIVER:ARCHIVER_SHA},"inputs":inputs}
    admission,_=admit_repository(cfg)
    helpers=authenticate_helpers();verifier=load_bytes(helpers[ARCHIVER]["bytes"],"retention_archive")
    accepted=snapshot(DISK_INVENTORY,"accepted disk inventory")
    if accepted["sha256"]!=DISK_SHA:fail("accepted disk inventory digest")
    # No mutation occurs before release admission, source authentication, root,
    # resource, existing-work and all fresh-target checks have passed.
    for path in (OUT,ARCHIVE,SCRATCH,COMMON,TOMBSTONE)+LEASES:absent(path)
    if root_id(CANDIDATE)!=CANDIDATE_ID or root_id(BACKUP)!=BACKUP_ID:fail("tmpfs roots changed")
    before=capacity();census(LEASES);exclusion=Exclusion((COMMON,)+LEASES)
    with SignalLatch() as latch:
        exclusion.acquire();latch.check()
        prepare_scratch(OUT,ARCHIVE,SCRATCH,())
        exclusive(CLAIM,dict(proc_identity(os.getpid()),release_sha256=admission["sha256"]))
        pre_disk=protected(verifier,accepted);latch.check()
        tmpfs_roots=(("candidate",CANDIDATE),("metadata-backup",BACKUP))
        tmpfs_before=disk_inventory(verifier,tmpfs_roots)
        tmpfs_pre_path=os.path.join(SCRATCH,"tmpfs.pre.json")
        exclusive_bytes(tmpfs_pre_path,tmpfs_before);latch.check()
        args=["--candidate-root",CANDIDATE,"--metadata-backup-root",BACKUP,"--main-revision",MAIN_COMMIT,"--ihk-revision",IHK_COMMIT,"--allow-dirty-tracked-regular"]
        planner=run_helper(helpers[PLANNER],args+["--output",OUT],"planner",latch)
        ms=snapshot(OUT,"pre-archive inventory")
        archive=run_helper(helpers[ARCHIVER],["--manifest",OUT,"--candidate-root",CANDIDATE,"--metadata-backup-root",BACKUP,"--output",ARCHIVE],"archive",latch,manifest=ms)
        ars=snapshot(ARCHIVE,"archive");manifest,count=check_manifest_archive(ms,ars,verifier)
        corruption_contract(manifest,ars["bytes"])
        post_path=os.path.join(SCRATCH,"post.inventory.json")
        post=run_helper(helpers[PLANNER],args+["--output",post_path],"postflight-planner",latch)
        postflight_equal(ms,snapshot(post_path,"post inventory"))
        after=capacity();capacity_delta(before,after)
        def final_sources():
            postflight_equal(ms,snapshot(OUT,"original inventory"))
            postflight_equal(ars,snapshot(ARCHIVE,"original archive"))
            if root_id(CANDIDATE)!=CANDIDATE_ID or root_id(BACKUP)!=BACKUP_ID:fail("tmpfs roots changed")
            protected(verifier,accepted)
            tmpfs_after=disk_inventory(verifier,tmpfs_roots)
            if tmpfs_after!=tmpfs_before:fail("complete tmpfs inventory changed")
            exclusive_bytes(os.path.join(SCRATCH,"tmpfs.post.json"),tmpfs_after)
            if descendant_census():fail("children remain")
            census();exclusion.verify()
        receipt=os.path.join(SCRATCH,"receipt.json")
        payload={"schema":"native-exact-retention-preparation-v3","status":"PASS","release_sha256":admission["sha256"],"planner":planner,"archive":archive,"postflight":post,"manifest_sha256":ms["sha256"],"archive_sha256":ars["sha256"],"member_count":count,"disk_inventory_sha256":pre_disk,"tmpfs_inventory_sha256":sha_b(tmpfs_before),"capacity_before":before,"capacity_after":after,"claim":CLAIM,"operational_exclusions":list(exclusion.paths),"operational_exclusions_released":True}
        # Release completed-operation locks only after all source checks and
        # evidence fsync. The last filesystem write is the PASS receipt.
        finish(receipt,[final_sources],(OUT,ARCHIVE,post_path,CLAIM,tmpfs_pre_path,os.path.join(SCRATCH,"tmpfs.post.json")),payload,latch,exclusion.release)
    return 0

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument("--release-hash")
    return execute(parser.parse_args(argv).release_hash)

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as error:
        print("retention preparation failed: %s"%error,file=sys.stderr);sys.exit(2)
