"""Pure ordinary-file consumer; never observes Docker, extracts, or cleans up."""
import hashlib
import json
import os
from pathlib import Path
import stat

IDENTITY_FIELDS = ('path','device','inode','mode','uid','gid','size','nlink','sha256')
REQUIRED_AUTHORITY = ('path','device','inode','mode','size','sha256')

def need(value, reason):
    if not value:
        raise RuntimeError(reason)

def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def join_one(engine, bound):
    """Use actual observe_identity shape; timestamps come from a held descriptor."""
    need(isinstance(bound,dict) and set(REQUIRED_AUTHORITY)<=bound.keys(),'actual retained authority row required')
    path=Path(bound['path'])
    parent,_=engine.directory(path.parent)
    fd=None
    try:
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode),'regular production artifact required')
        fresh=engine.observe_identity(path)
        after=os.fstat(fd)
        named=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
        keys=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in keys),'artifact identity raced')
        need(set(fresh)==set(IDENTITY_FIELDS),'actual engine identity shape differs')
        need(all(fresh[k]==bound[k] for k in REQUIRED_AUTHORITY),'actual retained artifact binding differs')
        need((fresh['device'],fresh['inode'],fresh['mode'],fresh['size'],fresh['nlink'],fresh['uid'],fresh['gid'])==(after.st_dev,after.st_ino,oct(stat.S_IMODE(after.st_mode)),after.st_size,after.st_nlink,after.st_uid,after.st_gid),'held artifact descriptor differs')
        row=dict(fresh,mtime_ns=after.st_mtime_ns,ctime_ns=after.st_ctime_ns)
        for field in ('uid','gid','nlink','mtime_ns','ctime_ns'):
            if field in bound:
                need(row[field]==bound[field],'actual retained artifact '+field+' differs')
        return row
    finally:
        if fd is not None:
            os.close(fd)
        os.close(parent)

def join_pairs(engine, pairs):
    need(isinstance(pairs,list) and pairs,'actual new retained rows required')
    rows=[]
    for pair in pairs:
        need(isinstance(pair,dict) and pair.get('outside_generic_receipt_inventory') is True,'explicit production pair required')
        original,retained=(join_one(engine,pair[k]) for k in ('original','retained'))
        need(original['path']!=retained['path'] and original['sha256']==retained['sha256'] and original['size']==retained['size'],'independent retained destination bytes differ')
        need((original['device'],original['inode'])!=(retained['device'],retained['inode']) and original['nlink']==retained['nlink']==1,'independent single-link retained artifact required')
        rows.append(dict(original=original,retained=retained,outside_generic_receipt_inventory=True))
    return rows

def validate_review(review, release, observer_sha, source_sha, tests_sha, execution=False):
    """Exact existing observer decision fields; source/execution roles independent."""
    need(review.get('status')=='PASS' and isinstance(review.get('reviewer'),str) and bool(review['reviewer']) and review['reviewer']!=release['author'] and review.get('implementation_ownership') is False,'independent exact observation review required')
    need(review.get('observer_sha256')==observer_sha and review.get('cleanup_source_sha256')==source_sha and review.get('cleanup_tests_sha256')==tests_sha,'exact observer/source/tests map required')
    if execution:
        payload={k:v for k,v in release.items() if k!='execution_review'}
        need(review.get('reviewed_observation_payload_sha256')==hashlib.sha256(canonical(payload)).hexdigest(),'exact observation execution payload differs')
