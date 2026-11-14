#!/usr/bin/python3
"""Audit and (only with explicit release) archive one failed exact build.

This packet is archive-only: it never touches the candidate checkout and never
deletes or relocates anything.  It snapshots the declared evidence trees and
small records, rejects aliases/special files/hardlinks, and emits a
no-replace deterministic tar archive.
"""
from __future__ import annotations
import argparse, hashlib, json, os, stat, sys, tarfile, tempfile
from pathlib import Path

SCRATCH = Path('/home/holden/mckernel-work/scratch')
REPO = Path('/home/holden/mckernel')
CANDIDATE = SCRATCH/'mckernel-exact-candidate-c658175a-scratch-7'
OUTPUT = SCRATCH/'native-exact-build-output-c658175a-scratch-7-retry1'
EVIDENCE = SCRATCH/'native-exact-build-evidence-c658175a-scratch-7-retry1'
REQUEST = SCRATCH/'native-exact-build-request-c658175a-scratch-7-retry1.json'
MANIFEST = SCRATCH/'native-exact-inputs-c658175a-scratch-7-retry1.json'
PREP = SCRATCH/'native-exact-candidate-preparation-c658175a-scratch-7-retry1-terminal.json'
PREP_LOG = SCRATCH/'native-exact-candidate-preparation-c658175a-scratch-7-retry1.log'
EXCLUSION = SCRATCH/'native-exact-candidate-operational-exclusion-runtimeblob-12.json'
FAILURE = REPO/'docs/verification/evidence/native-exact-build-c658175a-scratch7-runtime-self-digest-failure-20260930.json'
ARCHIVE = SCRATCH/'native-exact-build-failure-c658175a-scratch-7-retry1-20260930-1.tar'
CANDIDATE_ID = '1831:6684719'
ROOT_IDS = {OUTPUT:'1831:5111838', EVIDENCE:'1831:5111853'}
EXCLUSION_ID = '1831:57616'
INPUT_DEVICE = 1831
INPUT_DEVICES = {FAILURE:66306}
EXPECTED = {
    REQUEST:'7a0a654c353f63e7680245f04d92dd361086abbe29e9e024e0ea42122faad826',
    MANIFEST:'e63cd03b1bf914e563d48e8b268c9aaebd4f04b99e59a3eb018c49daae9470a3',
    PREP:'99e4f0bf1f52f72a77233d5561b32f13de2eed9c4053efeb25a410ff74466ac4',
    PREP_LOG:'6a0582b7b68451e3f512dbd5394eef1fc33437a9460e0feb0064e13fb9e603c3',
    EXCLUSION:'9859dc32c9781a96ba6c0b6f86d14ae8fbf4af61ba0c838169b45ff53336997e',
    FAILURE:'5cbb715b9f0b99e82f9df36b3c5641ce6fdc83499594d606398a1732ee617c84',
}
REFERENCED = {
    EVIDENCE/'receipt.json':'64352f2b201467ee43fc7ec5bbd66d8f9e0b40b81b3204f6a84fa71fa8592c6e',
    EVIDENCE/'build/receipt.json':'10445c1a1654fa11545888714d13ec56b8f8d96c1b630c149afd4344a59d27fc',
    EVIDENCE/'build/driver.log':'484295d5c8ae461ba09c6509f462153c151cdea21d24525e1e5b7659764c3bee',
}
INPUTS = [(OUTPUT,'output'), (EVIDENCE,'evidence'), (REQUEST,'request'),
          (MANIFEST,'manifest'), (PREP,'prep-terminal'), (PREP_LOG,'prep-log'),
          (EXCLUSION,'runtimeblob12-exclusion'), (FAILURE,'failure-record')]
EXPECTED_DEVICES = {OUTPUT:1831, EVIDENCE:1831, REQUEST:1831, MANIFEST:1831,
                    PREP:1831, PREP_LOG:1831, EXCLUSION:1831, FAILURE:66306}
EXPECTED_IDENTITIES = {FAILURE:'66306:47495938'}

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def fail(msg): raise RuntimeError(msg)

def regular(p):
    st=os.lstat(p)
    if stat.S_ISLNK(st.st_mode): fail('symlink: '+str(p))
    if not stat.S_ISREG(st.st_mode): fail('non-regular: '+str(p))
    if st.st_nlink != 1: fail('hardlink: '+str(p))
    return st

def safe_ancestors(p):
    """Reject symlink ancestors and cross-device inputs before traversal."""
    cur = Path(p.anchor)
    for part in p.parts[1:-1]:
        cur /= part
        if os.path.islink(cur): fail('symlink ancestor: '+str(cur))
    if os.path.islink(p): fail('symlink input: '+str(p))

def source_for(rel):
    label, _, suffix = rel.partition('/')
    for root, name in INPUTS:
        if name == label:
            return root if not suffix else root/Path(suffix)
    fail('unknown snapshot member: '+rel)

def inventory():
    rows=[]
    if not CANDIDATE.is_dir() or os.path.islink(CANDIDATE): fail('candidate missing or aliased')
    cst=os.lstat(CANDIDATE)
    if f'{cst.st_dev}:{cst.st_ino}' != CANDIDATE_ID: fail('candidate identity')
    if not EXCLUSION.is_file() or os.path.islink(EXCLUSION): fail('exclusion missing or aliased')
    est=os.lstat(EXCLUSION)
    if f'{est.st_dev}:{est.st_ino}' != EXCLUSION_ID: fail('exclusion identity')
    for root,label in INPUTS:
        if not os.path.lexists(root): fail('missing: '+str(root))
        if root == CANDIDATE: fail('candidate included')
        safe_ancestors(root)
        rst=os.lstat(root)
        expected_device = EXPECTED_DEVICES.get(root, INPUT_DEVICES.get(root, INPUT_DEVICE))
        if rst.st_dev != expected_device: fail('input device: '+str(root))
        expected_identity = EXPECTED_IDENTITIES.get(root)
        if expected_identity and f'{rst.st_dev}:{rst.st_ino}' != expected_identity: fail('input identity: '+str(root))
        if root in ROOT_IDS:
            if not stat.S_ISDIR(rst.st_mode) or f'{rst.st_dev}:{rst.st_ino}' != ROOT_IDS[root]: fail('root identity: '+str(root))
        if root.is_dir():
            def walk_error(exc): fail('tree traversal error: '+str(exc))
            for d, dirs, files in os.walk(root, topdown=True, onerror=walk_error, followlinks=False):
                ds=os.lstat(d)
                if not stat.S_ISDIR(ds.st_mode) or ds.st_dev != rst.st_dev: fail('non-directory/cross-device tree node')
                rel=f'{label}/{Path(d).relative_to(root)}' if Path(d) != root else label
                rows.append((rel,'dir',ds.st_mode & 0o7777,0,ds.st_mtime_ns,''))
                dirs.sort(); files.sort()
                for n in dirs:
                    q=Path(d)/n
                    if os.path.islink(q): fail('symlink directory: '+str(q))
                for n in files:
                    q=Path(d)/n; st=regular(q)
                    if st.st_dev != rst.st_dev: fail('cross-device file: '+str(q))
                    rel=f'{label}/{q.relative_to(root)}'
                    rows.append((rel,'file',st.st_mode & 0o7777,st.st_size,st.st_mtime_ns,digest(q)))
        else:
            st=regular(root); rows.append((label,'file',st.st_mode & 0o7777,st.st_size,st.st_mtime_ns,digest(root)))
    for q,want in EXPECTED.items():
        if digest(q) != want: fail('digest mismatch: '+str(q))
    for q,want in REFERENCED.items():
        if digest(q) != want: fail('referenced digest mismatch: '+str(q))
    return tuple(rows)

def make_archive(rows):
    if ARCHIVE.exists() or os.path.lexists(ARCHIVE): fail('archive exists')
    parent=ARCHIVE.parent; fd,tmp=tempfile.mkstemp(prefix='.c658-archive-',dir=parent)
    temp_st=os.fstat(fd)
    manifest=json.dumps({'schema':'native-exact-candidate-archive-v1','candidate_excluded':True,
                         'candidate_identity':CANDIDATE_ID,'rows':[list(x) for x in rows]},sort_keys=True,separators=(',',':')).encode()+b'\n'
    try:
        with os.fdopen(fd,'w+b',closefd=False) as stream, tarfile.open(fileobj=stream,mode='w',format=tarfile.PAX_FORMAT) as tf:
            tf.pax_headers={'mtime':'0'}
            seen=set()
            for rel,kind,mode,size,mtime,sha in rows:
                if rel in seen: fail('duplicate member')
                seen.add(rel)
                src=source_for(rel)
                # Re-read and compare the immutable snapshot immediately before adding.
                st=os.lstat(src)
                if kind == 'file':
                    regular(src)
                    if (st.st_size,st.st_mtime_ns,digest(src)) != (size,mtime,sha): fail('source mutated: '+str(src))
                elif not stat.S_ISDIR(st.st_mode) or st.st_mtime_ns != mtime: fail('directory mutated: '+str(src))
                ti=tarfile.TarInfo(rel); ti.mode=mode; ti.uid=st.st_uid; ti.gid=st.st_gid; ti.mtime=0; ti.size=size
                ti.type=tarfile.DIRTYPE if kind == 'dir' else tarfile.REGTYPE
                if kind == 'file':
                    with src.open('rb') as f: tf.addfile(ti,f)
                else: tf.addfile(ti)
            mi=tarfile.TarInfo('snapshot-manifest.json'); mi.mode=0o600; mi.uid=0; mi.gid=0; mi.mtime=0; mi.size=len(manifest); tf.addfile(mi,__import__('io').BytesIO(manifest))
            stream.flush(); os.fsync(fd)
        now_st=os.fstat(fd)
        if (now_st.st_dev,now_st.st_ino) != (temp_st.st_dev,temp_st.st_ino): fail('temporary archive identity changed')
        path_st=os.lstat(tmp)
        if (path_st.st_dev,path_st.st_ino)!=(temp_st.st_dev,temp_st.st_ino): fail('temporary pathname replaced before verify')
        verify_archive(tmp, rows, manifest)
        now_st=os.fstat(fd)
        if (now_st.st_dev,now_st.st_ino) != (temp_st.st_dev,temp_st.st_ino): fail('temporary archive identity changed after verify')
        path_st=os.lstat(tmp)
        if (path_st.st_dev,path_st.st_ino)!=(temp_st.st_dev,temp_st.st_ino): fail('temporary pathname replaced before publish')
        os.link(tmp,ARCHIVE)
        afd=os.open(ARCHIVE,os.O_RDONLY); os.fsync(afd); os.close(afd)
        pfd=os.open(parent,os.O_RDONLY); os.fsync(pfd); os.close(pfd)
    finally:
        os.close(fd)
        try:
            path_st=os.lstat(tmp)
            if (path_st.st_dev,path_st.st_ino)==(temp_st.st_dev,temp_st.st_ino): os.unlink(tmp)
        except FileNotFoundError: pass
    return digest(ARCHIVE)

def verify_archive(path, rows, manifest):
    expected={r[0]:r for r in rows}; expected['snapshot-manifest.json']=None
    with tarfile.open(path,'r:') as tf:
        members=tf.getmembers()
        if [x.name for x in members] != list(expected): fail('archive member order/name mismatch')
        for ti in members:
            if ti.name == 'snapshot-manifest.json':
                if ti.size != len(manifest) or tf.extractfile(ti).read() != manifest: fail('manifest mismatch')
                continue
            rel,kind,mode,size,mtime,sha=expected[ti.name]
            if (ti.isdir() and kind != 'dir') or (ti.isfile() and kind != 'file') or (not ti.isdir() and not ti.isfile()): fail('archive type mismatch')
            if (ti.mode & 0o7777,ti.size) != (mode,size): fail('archive metadata mismatch')
            if kind == 'file' and hashlib.sha256(tf.extractfile(ti).read()).hexdigest() != sha: fail('archive content mismatch')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--audit',action='store_true'); ap.add_argument('--release',action='store_true'); a=ap.parse_args()
    if a.audit == a.release: ap.error('choose exactly one of --audit or --release')
    rows=inventory()
    if a.audit: print(json.dumps({'status':'PASS_AUDIT','members':len(rows),'candidate_excluded':True},sort_keys=True)); return 0
    if os.environ.get('ARCHIVE_RELEASE') != '1': fail('release requires ARCHIVE_RELEASE=1')
    ah=make_archive(rows); print(json.dumps({'status':'PASS_ARCHIVE','archive':str(ARCHIVE),'archive_sha256':ah,'members':len(rows),'candidate_excluded':True},sort_keys=True)); return 0
if __name__=='__main__':
    try: raise SystemExit(main())
    except (RuntimeError,OSError,tarfile.TarError) as e: print('FAIL: '+str(e),file=sys.stderr); raise SystemExit(1)
