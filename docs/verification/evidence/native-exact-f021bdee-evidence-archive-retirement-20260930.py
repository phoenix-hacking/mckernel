#!/usr/bin/env python3
"""Fail-closed archive and separately reviewed retirement for f021 evidence."""
import argparse, gzip, hashlib, json, os, shutil, stat, subprocess, tempfile, tarfile
from pathlib import Path

REPO=Path('/home/holden/mckernel'); SCRATCH=Path('/home/holden/mckernel-work/scratch')
SOURCE=SCRATCH/'native-exact-build-evidence-f021bdee-scratch-8'; SOURCE_ID='1831:6684763'
SOURCE_DEVICE=1831
RETAINED=Path('/home/holden/mckernel-work/retained-exact-candidates')
ARCHIVE=RETAINED/'native-exact-build-evidence-f021bdee-scratch-8-20260930.tar.gz'
MAP=RETAINED/'native-exact-build-evidence-f021bdee-scratch-8-20260930.map.json'
FAILURE=REPO/'docs/verification/evidence/native-exact-build-f021bdee-scratch8-export-allowlist-failure-20260930.json'
FAILURE_SHA='2c40c821d23b0e79bba0eb2e151b47f8c99f5ffc60e36c1e93c97b692f1a59c6'
OUTPUT=SCRATCH/'native-exact-build-output-f021bdee-scratch-8'; CANDIDATE=SCRATCH/'mckernel-exact-candidate-f021bdee-scratch-8'
PROTECTED=(OUTPUT,CANDIDATE,SCRATCH/'native-exact-build-request-f021bdee-scratch-8.json',SCRATCH/'native-exact-inputs-f021bdee-scratch-8.json',SCRATCH/'native-exact-candidate-preparation-f021bdee-scratch-8-terminal.json',SCRATCH/'native-exact-candidate-preparation-f021bdee-scratch-8.log',SCRATCH/'native-exact-metadata-backup-f021bdee-scratch-8',SCRATCH/'native-exact-metadata-evidence-f021bdee-scratch-8',SCRATCH/'native-exact-candidate-operational-exclusion-selfdigest-13.json')
CONTAINER={'id':'b34323f6c4352e8bae669d006e11076a64a5734ed165a6ce866bd4e7aa04c001','name':'mckernel-exact-d01624939ead44118fc2352bc4d83860','state':'exited','exit_code':1}

def die(x): raise SystemExit('FAIL_CLOSED: '+x)
def digest(p):
    h=hashlib.sha256()
    fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW); f=os.fdopen(fd,'rb')
    with f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def run(a):
    try:
        p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15,check=False); return p.returncode,p.stdout,p.stderr
    except Exception as e: return 99,'',repr(e)
def census():
    rc,out,err=run(['sudo','-A','lsof','-nP','-w','+D',str(SOURCE)])
    if rc not in (0,1) or err.strip() or (rc==0 and [x for x in out.splitlines() if x and not x.startswith('COMMAND')]) or (rc==1 and out.strip()): die('open evidence reference')
    rc,out,err=run(['findmnt','-T',str(SOURCE),'-o','SOURCE,FSTYPE,MAJ:MIN,TARGET'])
    lines=[x.split() for x in out.splitlines() if x.strip() and not x.startswith('SOURCE')]
    if rc or lines != [['/dev/loop39','ext4','7:39','/home/holden/mckernel-work/scratch']]: die('unexpected evidence mount')
    rc,out,err=run(['sudo','-A','docker','ps','-a','--no-trunc','--format','{{json .}}'])
    if rc: die('Docker census failed')
    for line in out.splitlines():
        try: d=json.loads(line)
        except Exception: die('Docker census malformed')
        if str(d.get('State','')).lower() in ('running','restarting') and ('mckernel-exact' in str(d.get('Names','')) or '/home/holden/mckernel-work' in str(d.get('Mounts',''))): die('running relevant container')
    return {'lsof':{'returncode':rc},'mount':'/dev/loop39 ext4 7:39 /home/holden/mckernel-work/scratch','container':CONTAINER}
def guard():
    if not SOURCE.is_dir() or SOURCE.is_symlink(): die('source missing/linked')
    st=SOURCE.stat()
    if f'{st.st_dev}:{st.st_ino}' != SOURCE_ID: die('source identity')
    for p in PROTECTED:
        if os.path.lexists(p) and p.resolve()==SOURCE.resolve(): die('protected source alias')
        if os.path.lexists(p) and p.is_symlink(): die('protected path linked')
    if not FAILURE.is_file() or digest(FAILURE) != FAILURE_SHA: die('original failure changed')
    return census()
def snapshot():
    def linkrow(p):
        st=os.lstat(p); target=os.readlink(p)
        if not target or os.path.isabs(target): die('absolute/empty symlink: '+str(p))
        try: resolved=(p.parent/target).resolve(strict=True)
        except OSError: die('dangling symlink: '+str(p))
        if os.path.commonpath((str(SOURCE.resolve()),str(resolved))) != str(SOURCE.resolve()): die('escaping symlink: '+str(p))
        return {'path':str(p.relative_to(SOURCE)),'type':'symlink','mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'size':0,'linkname':target}
    rows=[]
    for d,dirs,files in os.walk(SOURCE,topdown=True,followlinks=False):
        dirs.sort(); files.sort(); ds=os.lstat(d)
        if not stat.S_ISDIR(ds.st_mode) or ds.st_dev!=SOURCE_DEVICE: die('bad directory')
        rel='.' if Path(d)==SOURCE else str(Path(d).relative_to(SOURCE)); rows.append({'path':rel,'type':'dir','mode':stat.S_IMODE(ds.st_mode),'uid':ds.st_uid,'gid':ds.st_gid,'mtime_ns':ds.st_mtime_ns,'size':0})
        for n in list(dirs):
            p=Path(d)/n
            if p.is_symlink(): dirs.remove(n); rows.append(linkrow(p))
        for n in files:
            p=Path(d)/n; st=os.lstat(p)
            if stat.S_ISLNK(st.st_mode): rows.append(linkrow(p)); continue
            if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_dev!=SOURCE_DEVICE: die('special/link/hardlink member: '+str(p))
            rows.append({'path':str(p.relative_to(SOURCE)),'type':'file','mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'size':st.st_size,'sha256':digest(p),'allocated_bytes':st.st_blocks*512})
    if not rows: die('empty evidence root')
    return rows
def verify(path,rows):
    expected={x['path']:x for x in rows}
    try:
        with tarfile.open(path,'r:gz') as tf:
            members=tf.getmembers()
            if [x.name for x in members] != list(expected): die('archive member closure mismatch')
            for m in members:
                r=expected[m.name]
                if r['type']=='dir' and not m.isdir(): die('directory type mismatch')
                if r['type']=='symlink' and (not m.issym() or m.linkname!=r['linkname']): die('symlink member mismatch')
                if r['type']=='file' and (not m.isfile() or m.size!=r['size'] or hashlib.sha256(tf.extractfile(m).read()).hexdigest()!=r['sha256']): die('file member mismatch')
                if (m.mode&0o7777,m.uid,m.gid)!=(r['mode'],r['uid'],r['gid']): die('member metadata mismatch')
    except (OSError,tarfile.TarError) as exc: die('archive unreadable: '+str(exc))
def atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix='.f021-',dir=path.parent); ident=os.fstat(fd)
    try:
        view=memoryview(data)
        while view:
            n=os.write(fd,view)
            if n<=0: die('short map write')
            view=view[n:]
        os.fsync(fd); os.close(fd)
        if os.path.lexists(path) or (lambda s:(s.st_dev,s.st_ino)!=(ident.st_dev,ident.st_ino))(os.lstat(tmp)): die('destination/temp identity')
        os.link(tmp,path); d=os.open(path.parent,os.O_DIRECTORY); os.fsync(d); os.close(d)
    finally:
        if os.path.lexists(tmp) and (lambda s:(s.st_dev,s.st_ino)==(ident.st_dev,ident.st_ino))(os.lstat(tmp)): os.unlink(tmp)
def archive():
    safety=guard(); rows=snapshot()
    if os.path.lexists(ARCHIVE) or os.path.lexists(MAP): die('archive/map exists')
    fd,tmp=tempfile.mkstemp(prefix='.f021-archive-',dir=ARCHIVE.parent); ident=os.fstat(fd)
    try:
        stream=os.fdopen(fd,'w+b',closefd=False)
        with tarfile.open(fileobj=stream,mode='w:gz') as tf:
            for r in rows:
                p=SOURCE/r['path'] if r['path']!='.' else SOURCE; ti=tf.gettarinfo(str(p),arcname=r['path']);
                if r['type']=='file':
                    sfd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW); f=os.fdopen(sfd,'rb')
                    with f: tf.addfile(ti,f)
                else: tf.addfile(ti)
        stream.flush(); os.fsync(fd); stream.close()
        st=os.lstat(tmp)
        if (st.st_dev,st.st_ino)!=(ident.st_dev,ident.st_ino) or not stat.S_ISREG(st.st_mode) or st.st_nlink!=1: die('archive temp identity changed')
        verify(tmp,rows)
        st=os.lstat(tmp)
        if (st.st_dev,st.st_ino)!=(ident.st_dev,ident.st_ino) or not stat.S_ISREG(st.st_mode) or st.st_nlink!=1: die('archive temp replaced before link')
        if os.path.lexists(ARCHIVE): die('archive destination exists')
        os.link(tmp,ARCHIVE); afd=os.open(ARCHIVE,os.O_RDONLY|os.O_NOFOLLOW); os.fsync(afd); os.close(afd); d=os.open(ARCHIVE.parent,os.O_DIRECTORY); os.fsync(d); os.close(d)
        record={'schema':'mckernel.f021-evidence-archive.v1','status':'ARCHIVE_PASS','source':str(SOURCE),'source_identity':SOURCE_ID,'archive':str(ARCHIVE),'archive_sha256':digest(ARCHIVE),'failure_record':str(FAILURE),'failure_sha256':digest(FAILURE),'protected_paths':[str(p) for p in PROTECTED],'container':CONTAINER,'safety_census':safety,'members':rows}
        atomic(MAP,(json.dumps(record,sort_keys=True,indent=2)+'\n').encode()); return record
    finally:
        try: os.close(fd)
        except OSError: pass
        if os.path.lexists(tmp):
            st=os.lstat(tmp)
            if (st.st_dev,st.st_ino)==(ident.st_dev,ident.st_ino): os.unlink(tmp)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--audit',action='store_true'); ap.add_argument('--archive',action='store_true'); ap.add_argument('--retire',action='store_true'); a=ap.parse_args()
    if sum((a.audit,a.archive,a.retire))!=1: ap.error('choose one mode')
    if a.audit: print(json.dumps({'status':'AUDIT_PASS','source':str(SOURCE),'source_identity':SOURCE_ID,'safety_census':guard(),'members':len(snapshot())},sort_keys=True)); return
    if a.archive: print(json.dumps(archive(),sort_keys=True)); return
    die('retirement requires separately reviewed archive/map release')
if __name__=='__main__': main()
