#!/usr/bin/env python3
"""Source-only, fail-closed candidate12 rename-back transaction.

It deliberately requires an immutable failed-attempt receipt and a later,
separately committed/fetched release.  The release does not hash itself.
"""
import argparse, ctypes, fcntl, hashlib, json, os, signal, stat, subprocess, sys
from pathlib import Path, PurePosixPath

REPO=Path('/home/holden/mckernel'); QROOT='/home/holden/mckernel-work/scratch/mckernel-exact-candidate-4e99a82c-scratch-12'; SCRATCH='/home/holden/mckernel-work/scratch'
DEFAULT_RECEIPT=SCRATCH+'/native-exact-candidate12-planbound-cleanup-20260930-2.receipt.json'; DEFAULT_Q=QROOT+'/.planbound-cleanup-20260930-2'; JOURNAL_PATH=SCRATCH+'/native-exact-candidate12-planbound-cleanup-20260930-2.journal.jsonl'
RECEIPT_SHA256='83d22b06d9d143b3acc0508d738f6b1039184a5d2d473d314f5a1e3a65cd3c52'; RECEIPT_SIZE=1399041; JOURNAL_SHA256='4749ea4d1b97bc99959c1ec75c0f329682f834d075738264a44efde33ce90d02'; JOURNAL_SIZE=3238188; EXPECTED_COUNT=2507
NOFOLLOW=os.O_NOFOLLOW|os.O_CLOEXEC; RENAME_NOREPLACE=1; _interrupted=False
class Refusal(RuntimeError): pass
def req(x,w):
    if not x: raise Refusal(w)
def digest(x): return hashlib.sha256(x).hexdigest()
def ident(s): return (s.st_dev,s.st_ino,stat.S_IFMT(s.st_mode),s.st_mode&0o7777,s.st_nlink,s.st_size,s.st_mtime_ns)
def canon(p):
    p=PurePosixPath(str(p)); req(p.is_absolute() and '.' not in p.parts and '..' not in p.parts,'path-noncanonical'); return str(p)
def inside(p,r): return p==r or p.startswith(r.rstrip('/')+'/')
def pairs(v):
    d={}
    for k,x in v: req(k not in d,'json-duplicate-key'); d[k]=x
    return d
def parse(b): return json.loads(b.decode(),object_pairs_hook=pairs)
def walkfd(path,directory=False):
    """Component-wise no-follow resolver; never trust a compound pathname."""
    parts=PurePosixPath(canon(path)).parts[1:]; fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|NOFOLLOW)
    try:
        for x in parts[:-1]: n=os.open(x,os.O_RDONLY|os.O_DIRECTORY|NOFOLLOW,dir_fd=fd); os.close(fd); fd=n
        if not parts: return fd
        n=os.open(parts[-1],os.O_RDONLY|NOFOLLOW|(os.O_DIRECTORY if directory else 0),dir_fd=fd); os.close(fd); return n
    except BaseException: os.close(fd); raise
def dirfd(p): return walkfd(p,True)
def read_regular(p):
    fd=walkfd(p)
    try:
        s=os.fstat(fd); req(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'not-private-regular')
        out=[]
        while True:
            b=os.read(fd,1048576)
            if not b: return b''.join(out)
            out.append(b)
    finally: os.close(fd)
def write_all(fd,b):
    b=memoryview(b)
    while b:
        n=os.write(fd,b); req(isinstance(n,int) and n>0,'short-or-zero-write'); b=b[n:]
def append(fd,o): write_all(fd,(json.dumps(o,sort_keys=True,separators=(',',':'))+'\n').encode()); os.fsync(fd)
def hashfd(fd):
    os.lseek(fd,0,0); h=hashlib.sha256()
    while True:
        b=os.read(fd,1048576)
        if not b:return h.hexdigest()
        h.update(b)
def git(*args):
    e={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}; e.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_TERMINAL_PROMPT='0')
    p=subprocess.run(['git','-c','safe.directory='+str(REPO),'-C',str(REPO),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=e,timeout=45); req(p.returncode==0,'git-failed'); return p.stdout
def check_at(parent,name,row):
    fd=os.open(name,os.O_RDONLY|NOFOLLOW,dir_fd=parent)
    try:
        s=os.fstat(fd); req(stat.S_ISREG(s.st_mode) and s.st_nlink==1,'row-type-or-link')
        for k,a in (('dev',s.st_dev),('ino',s.st_ino),('mode',s.st_mode&0o7777),('nlink',s.st_nlink),('size',s.st_size),('mtime_ns',s.st_mtime_ns),('allocated_bytes',s.st_blocks*512)):
            if k in row:req(row[k]==a,'row-'+k)
        req(hashfd(fd)==row['sha256'],'row-content'); req(ident(s)==ident(os.fstat(fd)),'row-raced')
    finally: os.close(fd)
def location(path,row):
    try:
        p=PurePosixPath(path); d=dirfd(str(p.parent))
        try:check_at(d,p.name,row)
        finally:os.close(d)
        return 'expected'
    except FileNotFoundError:return 'missing'
    except BaseException:return 'wrong'
def reconcile(row,qfd,i):
    a=location(row['path'],row)
    try:check_at(qfd,str(i),row); b='expected'
    except FileNotFoundError:b='missing'
    except BaseException:b='wrong'
    return 'original' if a=='expected' and b=='missing' else 'staged' if a=='missing' and b=='expected' else 'uncertain'
def scan(fd):
    out=[]
    def rec(d,prefix):
        for n in os.listdir(d):
            s=os.stat(n,dir_fd=d,follow_symlinks=False); e={'path':prefix+n,'kind':stat.S_IFMT(s.st_mode),'mode':s.st_mode&0o7777,'dev':s.st_dev,'ino':s.st_ino,'nlink':s.st_nlink,'size':s.st_size,'mtime_ns':s.st_mtime_ns}
            if stat.S_ISREG(s.st_mode):
                x=os.open(n,os.O_RDONLY|NOFOLLOW,dir_fd=d)
                try:e['sha256']=hashfd(x)
                finally:os.close(x)
            elif stat.S_ISLNK(s.st_mode):e['target']=os.readlink(n,dir_fd=d)
            out.append(e)
            if stat.S_ISDIR(s.st_mode):
                x=os.open(n,os.O_RDONLY|os.O_DIRECTORY|NOFOLLOW,dir_fd=d)
                try:rec(x,prefix+n+'/')
                finally:os.close(x)
    rec(fd,''); return sorted(out,key=lambda x:x['path'])
def namespace(fd,want):
    a,b=scan(fd),scan(fd); req(a==b,'namespace-raced')
    # A rename necessarily changes its parent directory's mtime/size.  Every
    # immutable leaf field remains exact; mutable directory timestamps are
    # excluded only after type/identity/name validation.
    def stable(v):
        return [{k:x for k,x in e.items() if not (e['kind']==stat.S_IFDIR and k in ('mtime_ns','size'))} for e in v]
    req(stable(a)==stable(want),'namespace-drift-or-unplanned-type')
def load_receipt(path):
    raw=read_regular(path); r=parse(raw); req(canon(path)==DEFAULT_RECEIPT and len(raw)==RECEIPT_SIZE and digest(raw)==RECEIPT_SHA256,'receipt-identity')
    rows=r.get('restoration'); req(r.get('status')=='FAIL' and r.get('phase')=='staged-admission' and r.get('interrupted') is False and isinstance(rows,list) and len(rows)==EXPECTED_COUNT and r.get('states')==['staged']*EXPECTED_COUNT,'receipt-state')
    seen=set()
    for x in rows:
        p=canon(x.get('path','')); req(inside(p,QROOT+'/docs/verification/evidence/') and p not in seen and all(k in x for k in ('sha256','dev','ino','mode','nlink','size','mtime_ns')),'receipt-row'); seen.add(p); req(x['nlink']==1 and x['mode'] in (0o644,0o755),'receipt-metadata')
    req(isinstance(r.get('quarantine_namespace'),list) and isinstance(r.get('restored_namespace'),list),'receipt-full-namespace')
    return r
def validate_attempt_journal(path=JOURNAL_PATH):
    raw=read_regular(path); req(len(raw)==JOURNAL_SIZE and digest(raw)==JOURNAL_SHA256,'journal-identity'); ev=[parse(x) for x in raw.splitlines() if x]; kinds=[x.get('event') for x in ev]
    req(kinds.count('stage-intent')==EXPECTED_COUNT and kinds.count('staged')==EXPECTED_COUNT and not ({'delete-intent','deleted','irreversible-delete-admitted'}&set(kinds)),'journal-events'); req(kinds[-1:] == ['failure'] and ev[-1].get('error')=='open-references-or-incomplete-census','journal-final'); return ev
def validate_admission(rel,source):
    a=rel.get('admission'); req(isinstance(a,dict) and a.get('status')=='PASS','admission-status'); p=canon(a.get('path','')); rp=str(Path(p).relative_to(REPO)); raw=read_regular(p); req(digest(raw)==a.get('sha256')==digest(git('show',source+':'+rp)),'admission-bytes'); v=parse(raw)
    req(v.get('generator') not in (None,'recovery-script') and v.get('status')=='PASS','admission-independent')
    for k in ('containers','leases','open_references','mount_identities'):req(isinstance(v.get(k),list),'admission-'+k)
    req(not v['containers'] and not v['leases'] and not v['open_references'] and v['mount_identities'],'admission-exclusion'); return v
def validate_release(path):
    raw=read_regular(path); r=parse(raw); req(r.get('schema')=='mckernel.candidate12.renameback.recovery.v2' and r.get('status')=='PASS','release-schema'); source,released,upstream,fetched=[r.get(k,'') for k in ('source_commit','release_commit','upstream_commit','fetched_commit')]
    req(all(isinstance(x,str) and len(x)==40 and set(x)<=set('0123456789abcdef') for x in (source,released,upstream,fetched)) and source!=released and released==upstream==fetched,'release-commits'); req(git('merge-base','--is-ancestor',source,released)==b'' and git('rev-parse','HEAD').strip()==released and git('rev-parse','@{upstream}').strip()==upstream and git('rev-parse','FETCH_HEAD').strip()==fetched,'release-remote')
    rp=str(Path(path).relative_to(REPO)); req(git('show',released+':'+rp)==raw,'release-fetched-bytes'); arts=r.get('source_artifacts'); req(isinstance(arts,dict),'release-artifacts')
    for n in ('tool','test'):
        x=arts.get(n); req(isinstance(x,dict),'artifact-'+n); p=canon(x.get('path','')); q=str(Path(p).relative_to(REPO)); b=read_regular(p); req(digest(b)==x.get('sha256')==digest(git('show',source+':'+q))==digest(git('show',released+':'+q)),'artifact-'+n+'-bytes')
    validate_admission(r,source); return r
def rename_noreplace(sf,s,df,d):
    f=ctypes.CDLL(None,use_errno=True).renameat2; f.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    if f(sf,os.fsencode(s),df,os.fsencode(d),RENAME_NOREPLACE):raise OSError(ctypes.get_errno(),'renameat2(RENAME_NOREPLACE)')
def _sig(*_):
    global _interrupted; _interrupted=True
def recover(receipt_path,outputs,release_path):
    global _interrupted; _interrupted=False; r=load_receipt(receipt_path); req(outputs.get('quarantine')==r.get('quarantine')==DEFAULT_Q,'quarantine-binding'); validate_attempt_journal(); validate_release(release_path)
    names=('journal','receipt','status','lock'); vals=[canon(outputs[k]) for k in names]; req(len(set(vals))==len(vals),'output-alias')
    for p in vals:req(inside(p,SCRATCH) and not inside(p,QROOT) and p!=SCRATCH,'output-scope')
    for a in vals:
        for b in vals:req(a==b or (not inside(a,b) and not inside(b,a)),'output-parent-alias')
    fds=[]; parents={}; states=['staged']*EXPECTED_COUNT; result=None; admitted=False
    old={n:signal.signal(n,_sig) for n in (signal.SIGTERM,signal.SIGINT)}
    try:
        root=dirfd(QROOT); q=dirfd(outputs['quarantine']); fds += [root,q]; req(os.fstat(root).st_dev==os.fstat(q).st_dev,'cross-device')
        # Pre-create every distinct output and retain its dirfd; no mutation starts before this succeeds.
        for k in names:
            p=PurePosixPath(outputs[k]); d=dirfd(str(p.parent)); fds.append(d)
            try: fd=os.open(p.name,os.O_RDWR|os.O_CREAT|os.O_EXCL|NOFOLLOW,0o600,dir_fd=d)
            except OSError as e: raise Refusal('output-not-fresh:'+str(e.errno))
            fds.append(fd); parents[k]=(d,fd)
        fcntl.flock(parents['lock'][1],fcntl.LOCK_EX|fcntl.LOCK_NB); os.fsync(parents['lock'][0])
        for row in r['restoration']:
            p=PurePosixPath(row['path']); key=str(p.parent)
            if key not in parents: d=dirfd(key); fds.append(d); parents[key]=(d,None)
        namespace(q,r['quarantine_namespace']); journal=parents['journal'][1]; append(journal,{'event':'admitted','count':EXPECTED_COUNT,'receipt_sha256':RECEIPT_SHA256}); admitted=True
        for i,row in enumerate(r['restoration']):
            req(not _interrupted,'signal-latched'); p=PurePosixPath(row['path']); d=parents[str(p.parent)][0]; req(ident(os.fstat(d))==ident(os.stat(str(p.parent),follow_symlinks=False)),'destination-parent-swapped'); check_at(q,str(i),row)
            try:os.stat(p.name,dir_fd=d,follow_symlinks=False); raise Refusal('destination-exists')
            except FileNotFoundError:pass
            append(journal,{'event':'rename-intent','index':i,'source':str(i),'destination':row['path']}); rename_noreplace(q,str(i),d,p.name); os.fsync(d); os.fsync(q); check_at(d,p.name,row); states[i]='restored'; append(journal,{'event':'restored','index':i})
        req(not _interrupted and not os.listdir(q),'signal-or-quarantine-not-empty'); namespace(root,r['restored_namespace']); append(journal,{'event':'complete','count':EXPECTED_COUNT}); result={'status':'PASS','phase':'complete','states':states,'receipt':receipt_path}
    except BaseException as e:
        if not admitted: raise
        for i,row in enumerate(r['restoration']): states[i]=reconcile(row,q,i); append(parents['journal'][1],{'event':'reconciled','index':i,'state':states[i]})
        result={'status':'FAIL','phase':'rename-back','states':states,'uncertain':True,'error':str(e) if isinstance(e,Refusal) else type(e).__name__}; append(parents['journal'][1],{'event':'uncertain','result':result})
    finally:
        for n,h in old.items():signal.signal(n,h)
        if result and 'receipt' in parents and 'status' in parents:
            for k,o in (('receipt',result),('status',{'status':result['status'],'journal':outputs['journal'],'states':states})):
                d,f=parents[k]; write_all(f,(json.dumps(o,sort_keys=True,separators=(',',':'))+'\n').encode()); os.fsync(f); os.fsync(d)
        for x in reversed(fds):
            try:os.close(x)
            except OSError:pass
    return result
def main(argv=None):
    p=argparse.ArgumentParser(); g=p.add_mutually_exclusive_group(required=True); g.add_argument('--validate-only',action='store_true'); g.add_argument('--execute',action='store_true'); p.add_argument('--receipt',default=DEFAULT_RECEIPT); p.add_argument('--release'); p.add_argument('--quarantine',default=DEFAULT_Q); p.add_argument('--journal'); p.add_argument('--output-receipt'); p.add_argument('--status'); p.add_argument('--lock'); a=p.parse_args(argv)
    try:
        if a.validate_only:load_receipt(a.receipt); validate_attempt_journal(); print('VALIDATION_PASS; source-only'); return 0
        req(all((a.release,a.journal,a.output_receipt,a.status,a.lock)),'release-and-outputs-required'); r=recover(a.receipt,{'quarantine':a.quarantine,'journal':a.journal,'receipt':a.output_receipt,'status':a.status,'lock':a.lock},a.release); print('RECOVERY_'+r['status']); return 0 if r['status']=='PASS' else 1
    except BaseException as e:print('FAIL_CLOSED: '+(str(e) if isinstance(e,Refusal) else type(e).__name__),file=sys.stderr); return 1
if __name__=='__main__':raise SystemExit(main())
