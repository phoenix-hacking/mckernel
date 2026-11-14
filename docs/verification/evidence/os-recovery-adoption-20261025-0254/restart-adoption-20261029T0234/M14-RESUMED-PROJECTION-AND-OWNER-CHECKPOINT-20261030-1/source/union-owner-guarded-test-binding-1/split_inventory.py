"""FD-relative complete split-input inventory; source-only, no release.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The independently admitted manifest is mandatory; current identities are observed,
not copied from its claims. No mount, writer exclusion, or authority is inferred.
The returned digest matches graph_observations.inventory's row ordering and schema.
"""
import hashlib
import json
import os
import stat
import materializer as m
from source_freeze import require_immutable


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def snapshot(rootfd,expected_members,require_frozen=True):
    if type(expected_members) is not dict:raise ValueError('independently admitted full membership required')
    root_before=os.fstat(rootfd)
    if require_frozen:require_immutable(rootfd)
    entries={};seen=set();graph=[];total=0

    def walk(fd,prefix):
        nonlocal total
        initial=os.fstat(fd)
        if require_frozen:require_immutable(fd)
        names=sorted(os.listdir(fd));directories=[]
        for name in names:
            if name in ('.','..') or '/' in name or '\0' in name:raise ValueError('invalid directory entry')
            if len(graph)>=500000:raise ValueError('inventory entry cap')
            path=prefix+'/'+name if prefix else name
            before=os.stat(name,dir_fd=fd,follow_symlinks=False)
            if before.st_dev!=root_before.st_dev:raise ValueError('split input crosses device: '+path)
            key=(before.st_dev,before.st_ino)
            if key in seen:raise ValueError('in-tree inode alias: '+path)
            seen.add(key)
            item={'device':before.st_dev,'inode':before.st_ino,'mode':stat.S_IMODE(before.st_mode),'nlink':before.st_nlink}
            if stat.S_ISDIR(before.st_mode):
                item.update(type='directory');entries[path]=item
                graph.append([path,'directory',before.st_dev,before.st_ino]);directories.append((name,path,before))
            elif stat.S_ISREG(before.st_mode):
                total+=before.st_size
                if total>8*1024**3:raise ValueError('inventory byte cap')
                child=os.open(name,m._READ,dir_fd=fd)
                try:
                    if not m._same(before,os.fstat(child)):raise ValueError('file changed: '+path)
                    if require_frozen:require_immutable(child)
                    digest=hashlib.sha256();size=0
                    while True:
                        chunk=os.read(child,1<<20)
                        if not chunk:break
                        size+=len(chunk);digest.update(chunk)
                    if not m._same(before,os.fstat(child)) or size!=before.st_size:raise ValueError('file changed while read: '+path)
                    if require_frozen:require_immutable(child)
                    value=digest.hexdigest();item.update(type='file',bytes=size,sha256=value);entries[path]=item
                    graph.append([path,'file',before.st_dev,before.st_ino,value])
                finally:os.close(child)
            elif stat.S_ISLNK(before.st_mode):
                value=os.readlink(name,dir_fd=fd)
                if '\0' in value:raise ValueError('invalid link target')
                item.update(type='symlink',target=value);entries[path]=item
                graph.append([path,'symlink',before.st_dev,before.st_ino,value])
            else:raise ValueError('unsupported split-input entry: '+path)
            after=os.stat(name,dir_fd=fd,follow_symlinks=False)
            if not m._same(before,after):raise ValueError('named entry changed: '+path)
        # os.walk emits all current-directory entries before descending sorted dirs.
        for name,path,before in directories:
            child=os.open(name,m._DIR,dir_fd=fd)
            try:
                if not m._same(before,os.fstat(child)):raise ValueError('directory changed: '+path)
                walk(child,path)
                if not m._same(before,os.fstat(child)):raise ValueError('directory changed: '+path)
            finally:os.close(child)
        if names!=sorted(os.listdir(fd)) or not m._same(initial,os.fstat(fd)):raise ValueError('directory changed while scanned: '+prefix)
        if require_frozen:require_immutable(fd)

    walk(rootfd,'')
    if not m._same(root_before,os.fstat(rootfd)):raise ValueError('split root changed')
    projected={p:{k:v for k,v in row.items() if k not in ('device','inode','nlink')} for p,row in entries.items()}
    if projected!=expected_members:raise ValueError('split input inventory differs')
    result={'root':{'device':root_before.st_dev,'inode':root_before.st_ino,'kind':'directory'},'entries':entries}
    return result,hashlib.sha256(canonical(graph)).hexdigest()
