#!/usr/bin/env python3
"""One-shot retention preparation, released only through an acyclic Git record.

The template is committed first.  A later release commit changes only the
release-hash literal below and adds a release JSON binding the prior template
commit/blobs.  Dynamic HEAD==upstream==FETCH_HEAD binds that release commit.
"""
from __future__ import print_function
import argparse, errno, hashlib, importlib.util, io, json, os, signal, stat, subprocess, sys, tarfile, time

SOURCE="/home/holden/mckernel"; MAIN_COMMIT="675891545c881b8d625256ade56fe66ac69fe794"; IHK_COMMIT="3114d9e7101ad52030eb3effa849a5c108972a1f"
CANDIDATE="/dev/shm/mckernel-exact-candidate-67589154-1"; BACKUP="/dev/shm/mckernel-exact-metadata-backup-67589154-1"
CANDIDATE_ID={"dev":26,"inode":25166,"uid":1000,"gid":1000,"mode":0o755}; BACKUP_ID={"dev":26,"inode":35798,"uid":1000,"gid":1000,"mode":0o755}
PLANNER="scripts/native_exact_candidate_retention_capsule.py"; ARCHIVER="scripts/native_exact_candidate_retention_archive.py"; PACKET_TEST="scripts/tests/test_native_exact_candidate_retention_preparation_67589154.py"; CAPSULE_TEST="scripts/tests/test_native_exact_candidate_retention_capsule.py"; ARCHIVE_TEST="scripts/tests/test_native_exact_candidate_retention_archive.py"
PLANNER_SHA="ac3bb0354d1353928fd5f63ddf6743b636642fab79a4f5a3ec9195d5721d0b26"; ARCHIVER_SHA="6a28184e13e4ddec3a5e2fe6229c618929df29f235901083d55918c8291ac06e"
CAPSULE_TEST_SHA="ae6f129ac8f86379d98ad2ca1eec1e03034d3754a6786300014c140320743c9a"; ARCHIVE_TEST_SHA="fa9d727d74e462a9d6fdb2d96f3a3a597ccdab331b4321b92a2d11eaeb48355e"
RELEASE_PATH="docs/verification/evidence/stability-native-exact-candidate-retention-preparation-67589154-20260929-2.release.json"; RELEASE_SHA256="RELEASE_HASH_REQUIRED"
OUT=SOURCE+"/docs/verification/evidence/stability-native-exact-candidate-retention-67589154-20260929-2.inventory.json"; ARCHIVE=SOURCE+"/docs/verification/evidence/stability-native-exact-candidate-retention-67589154-20260929-2.tar"; SCRATCH="/home/holden/mckernel-work/scratch/native-exact-retention-preparation-evidence-67589154-2"; CLAIM=SCRATCH+"/claim-67589154-2.json"; LEASE=SCRATCH+"/lease-67589154-2.json"
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
            if len(data)!=before.st_size or not same(before,os.fstat(fd)): fail(label+" changed while reading")
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
def absent(path):
    if os.path.lexists(path): fail("fresh path exists: "+path)
    fd=open_dir(os.path.dirname(path));os.close(fd)
def prepare_scratch(out,archive,scratch,children):
    """Reserve the parent before testing only its defined child evidence paths."""
    for path in (out,archive,scratch): absent(path)
    os.mkdir(scratch,0o700);fsync_parent(scratch)
    for name in children: absent(os.path.join(scratch,name))
def git_env(): return {"PATH":"/usr/bin:/bin","HOME":"/nonexistent","LANG":"C","LC_ALL":"C","TZ":"UTC","GIT_CONFIG_NOSYSTEM":"1","GIT_CONFIG_GLOBAL":"/dev/null","GIT_TERMINAL_PROMPT":"0","GIT_NO_REPLACE_OBJECTS":"1","GIT_OPTIONAL_LOCKS":"0","GIT_EXTERNAL_DIFF":"0","GIT_PAGER":"cat","GIT_EDITOR":"true","GIT_ASKPASS":"/bin/false"}
def safe_git_metadata(repo):
    """Fingerprint bounded Git control-plane state, never object/log payloads."""
    meta=os.path.join(repo,".git"); st=os.lstat(meta)
    if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode): fail(".git must be a real directory (no gitfile)")
    digest=hashlib.sha256()
    controls={"config","HEAD","FETCH_HEAD","index","packed-refs","shallow","ORIG_HEAD"}
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
    visit(meta,"",True)
    cfg=os.path.join(meta,"config"); raw=snapshot(cfg,"Git config")["bytes"] if os.path.exists(cfg) else b""
    for x in (b"[include",b"includeif",b"worktree",b"hookspath",b"fsmonitor",b"external",b"sshcommand"):
        if x in raw.lower(): fail("unsafe Git config: "+x.decode())
    hooks=os.path.join(meta,"hooks")
    if os.path.isdir(hooks):
        with os.scandir(hooks) as scan:
            if any(not x.name.endswith(".sample") for x in scan): fail("active Git hook")
    return digest.hexdigest()
def git(repo,args):
    return subprocess.check_output(["/usr/bin/git","--no-optional-locks","-c","core.hooksPath=/dev/null","-c","core.fsmonitor=false","-c","credential.helper=","-c","protocol.file.allow=never","-C",repo]+args,env=git_env(),stderr=subprocess.PIPE).decode().strip()
def git_blob(repo,commit,path):
    return subprocess.check_output(["/usr/bin/git","--no-optional-locks","-c","core.hooksPath=/dev/null","-c","core.fsmonitor=false","-c","credential.helper=","-c","protocol.file.allow=never","-C",repo,"show",commit+":"+path],env=git_env(),stderr=subprocess.PIPE)
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
        return {"pid":pid,"state":fields[0],"flags":int(fields[6]),"starttime":int(fields[19])}
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
def run(argv,label,scratch=SCRATCH,timeout=1800):
    base=os.path.join(scratch,label);out,err,status=base+".stdout",base+".stderr",base+".status";proc=None;identity=None;started=time.time();handlers={};signals=(signal.SIGTERM,signal.SIGHUP,signal.SIGINT);oldmask=None
    try:
        def interrupted(signum,frame): raise KeyboardInterrupt("interrupted by signal %d"%signum)
        for signum in signals: handlers[signum]=signal.signal(signum,interrupted)
        # Keep a signal arriving at Popen-return pending until `proc` has been
        # assigned; then the handler enters the BaseException cleanup path.
        if hasattr(signal,"pthread_sigmask"):
            oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,signals)
        so=open(out,"xb")
        try: se=open(err,"xb")
        except BaseException: so.close();raise
        try: proc=subprocess.Popen(argv,stdout=so,stderr=se,close_fds=True,start_new_session=True)
        finally: so.close();se.close()
        if oldmask is not None:
            signal.pthread_sigmask(signal.SIG_SETMASK,oldmask);oldmask=None
        identity=proc_identity(proc.pid)
        if identity is None: fail(label+" identity unavailable")
        identity.update({"pgid":os.getpgid(proc.pid),"sid":os.getsid(proc.pid)})
        rc=proc.wait(timeout=timeout);seal_evidence(out,err);exclusive(status,{"returncode":rc,"identity":identity,"elapsed":time.time()-started})
        if rc: fail(label+" failed rc="+str(rc))
        if not retired(identity["pgid"]): fail(label+" descendants not retired")
        return {"label":label,"returncode":rc,"identity":identity}
    except BaseException as exc:
        if proc is not None:
            try: os.killpg(proc.pid,signal.SIGKILL)
            except OSError: pass
            try: proc.wait(timeout=2)
            except BaseException: pass
            try: retired(proc.pid)
            except BaseException: pass
        try: seal_evidence(out,err)
        except BaseException: pass
        try: exclusive(status,{"returncode":"EXCEPTION","identity":identity,"error":type(exc).__name__})
        except BaseException: pass
        raise
    finally:
        if oldmask is not None: signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)
        for signum,previous in handlers.items(): signal.signal(signum,previous)
def archive_module():
    spec=importlib.util.spec_from_file_location("retention_archive",os.path.join(SOURCE,ARCHIVER));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
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
def check_manifest_archive(ms,ars):
    m=json.loads(ms["bytes"].decode()); rows=manifest_contract(m); archive_module().verify_archive_bytes(ars["bytes"],ms["bytes"])
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
def execute(provided_release_sha=None):
    if RELEASE_SHA256=="RELEASE_HASH_REQUIRED" or provided_release_sha!=RELEASE_SHA256: print("DRAFT_NOT_RELEASED",file=sys.stderr);return 3
    if os.geteuid()==0:fail("ordinary user required")
    cfg={"source":SOURCE,"release_path":RELEASE_PATH,"release_sha256":RELEASE_SHA256,"packet_path":os.path.relpath(__file__,SOURCE),"test_path":PACKET_TEST,"support_hashes":{CAPSULE_TEST:CAPSULE_TEST_SHA,ARCHIVE_TEST:ARCHIVE_TEST_SHA},"inputs":{"planner_sha256":PLANNER_SHA,"archiver_sha256":ARCHIVER_SHA,"capsule_test_path":CAPSULE_TEST,"capsule_test_sha256":CAPSULE_TEST_SHA,"archive_test_path":ARCHIVE_TEST,"archive_test_sha256":ARCHIVE_TEST_SHA,"main_commit":MAIN_COMMIT,"ihk_commit":IHK_COMMIT,"candidate":CANDIDATE_ID,"metadata_backup":BACKUP_ID,"output":OUT,"archive":ARCHIVE,"scratch":SCRATCH,"claim":CLAIM,"lease":LEASE}};admission,release=admit_repository(cfg)
    prepare_scratch(OUT,ARCHIVE,SCRATCH,("claim-67589154-2.json","lease-67589154-2.json","planner.stdout","planner.stderr","planner.status","archive.stdout","archive.stderr","archive.status","postflight-planner.stdout","postflight-planner.stderr","postflight-planner.status","postflight-manifest.json","receipt.json"))
    if root_id(CANDIDATE)!=CANDIDATE_ID or root_id(BACKUP)!=BACKUP_ID:fail("root identity mismatch")
    if sha(os.path.join(SOURCE,PLANNER))!=PLANNER_SHA or sha(os.path.join(SOURCE,ARCHIVER))!=ARCHIVER_SHA:fail("tool digest")
    before=capacity();leases=("/home/holden/mckernel-work/scratch/native-exact-build-lease-67589154-1.json",);census(leases)
    own=dict(census()["self"] or {});own.update({"schema":"native-exact-retention-claim-v2","packet":sha(__file__)});exclusive(CLAIM,own);exclusive(LEASE,dict(own,claim=CLAIM))
    planner=run([sys.executable,"-E","-s","-B",os.path.join(SOURCE,PLANNER),"--candidate-root",CANDIDATE,"--metadata-backup-root",BACKUP,"--main-revision",MAIN_COMMIT,"--ihk-revision",IHK_COMMIT,"--output",OUT],"planner");ms=snapshot(OUT,"manifest")
    archive=run([sys.executable,"-E","-s","-B",os.path.join(SOURCE,ARCHIVER),"--manifest",OUT,"--candidate-root",CANDIDATE,"--metadata-backup-root",BACKUP,"--output",ARCHIVE],"archive");ars=snapshot(ARCHIVE,"archive");m,count=check_manifest_archive(ms,ars);manifest_contract(m,{"candidate":(CANDIDATE,CANDIDATE_ID),"metadata-backup":(BACKUP,BACKUP_ID)},{"main":MAIN_COMMIT,"ihk":IHK_COMMIT},49);after=capacity();capacity_delta(before,after);post=census(leases)
    postflight_out=os.path.join(SCRATCH,"postflight-manifest.json")
    postflight=run([sys.executable,"-E","-s","-B",os.path.join(SOURCE,PLANNER),"--candidate-root",CANDIDATE,"--metadata-backup-root",BACKUP,"--main-revision",MAIN_COMMIT,"--ihk-revision",IHK_COMMIT,"--output",postflight_out],"postflight-planner")
    postflight_snapshot=snapshot(postflight_out,"postflight manifest")
    postflight_equal(ms,postflight_snapshot)
    exclusive(os.path.join(SCRATCH,"receipt.json"),{"schema":"native-exact-candidate-retention-preparation-v2","status":"PASS","release_sha256":admission["sha256"],"planner":planner,"archive":archive,"postflight":postflight,"manifest_sha256":ms["sha256"],"postflight_manifest_sha256":postflight_snapshot["sha256"],"archive_sha256":ars["sha256"],"member_count":count,"capacity_before":before,"capacity_after":after,"census":post})
    for path in (LEASE,CLAIM): os.unlink(path);fsync_parent(path)
    return 0
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument("--release-hash");return execute(p.parse_args(argv).release_hash)
if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:print("retention preparation failed: %s"%e,file=sys.stderr);sys.exit(2)
