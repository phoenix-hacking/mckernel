"""Verified owner import closure; functional McKernel work only, no security testing.

Source-only helper. Root bootstrap must itself execute these exact loader bytes
from a separately authenticated admission, pin interpreter/argv, keep the returned
bundle live, and independently review the combined operation. No CLI or release.
"""
import hashlib
import os
import stat
import sys
import types
from pathlib import Path

OWNER_FILES={
 'materializer.py':'c3115c13a29dde74f6d316b64d26a6266c5a5cfeed877ef19de088844e09ba37',
 'verify_scripts_fd.py':'34bd9802c507b3408b685c6233f0a2f711edbdf7a6f31c5dcd3eaba70128ba8f',
 'source_freeze.py':'2a3cea45022e2104b6faa1ed8561ef9db1000a8a3734d94a1f17efab50ec8228',
 'split_inventory.py':'9bc54a33407c8abaed384a5d998fa3cea34d7f15179349e27e6122c09849de04',
 'union_owner.py':'955d879ff8fc0da6b81457bcea53415254a96367b9e23825bf07e8efb89ae2bb',
}
PROTOCOL_SHA='587cebf7b8359a1711f078882a012a701e290902dc4376d1bc6e4c03f7ce8cbb'
DIR=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC
READ=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
FIELDS=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')


def need(ok,message):
    if not ok:raise ValueError(message)


def values(st):return tuple(getattr(st,k) for k in FIELDS)


def open_dir(path):
    path=os.fspath(path)
    need(os.path.isabs(path) and os.path.normpath(path)==path,'canonical source root')
    fd=os.open('/',DIR)
    try:
        for name in (v for v in path.split('/') if v):
            before=os.stat(name,dir_fd=fd,follow_symlinks=False)
            need(stat.S_ISDIR(before.st_mode),'source ancestry not a directory')
            child=os.open(name,DIR,dir_fd=fd)
            if (os.fstat(child).st_dev,os.fstat(child).st_ino)!=(before.st_dev,before.st_ino):
                os.close(child);raise ValueError('source ancestry changed')
            os.close(fd);fd=child
        return fd
    except BaseException:
        os.close(fd);raise


def open_bound(directory_fd,name,expected):
    fd=os.open(name,READ,dir_fd=directory_fd)
    try:
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=1<<20,'source file identity')
        data=bytearray()
        while True:
            chunk=os.read(fd,65536)
            if not chunk:break
            data.extend(chunk);need(len(data)<=1<<20,'source file size')
        named=os.stat(name,dir_fd=directory_fd,follow_symlinks=False)
        need(values(before)==values(os.fstat(fd))==values(named) and len(data)==before.st_size,'source changed while read')
        need(hashlib.sha256(data).hexdigest()==expected,'source hash differs: '+name)
        return fd,bytes(data),values(before)
    except BaseException:
        os.close(fd);raise


class PinnedBundle:
    def __init__(self,directories,entries,named_roots):
        self.directories=directories;self.entries=entries;self.named_roots=named_roots
    def verify(self):
        for path,fd,expected in self.named_roots:
            current=open_dir(path)
            try:
                before=os.fstat(fd);after=os.fstat(current)
                need((before.st_dev,before.st_ino)==expected==(after.st_dev,after.st_ino),'loaded source directory changed')
            finally:os.close(current)
        for directory_fd,name,fd,identity,expected in self.entries:
            named=os.stat(name,dir_fd=directory_fd,follow_symlinks=False)
            need(values(os.fstat(fd))==identity==values(named),'loaded source changed: '+name)
            h=hashlib.sha256();offset=0
            while True:
                chunk=os.pread(fd,65536,offset)
                if not chunk:break
                h.update(chunk);offset+=len(chunk)
            need(offset==identity[4] and h.hexdigest()==expected and values(os.fstat(fd))==identity,'loaded source bytes changed: '+name)
        return True
    def close_after_independent_retirement(self):
        raise RuntimeError('no source-only authority to release source custody')


def load(owner_dir,expected_root):
    root=Path(owner_dir);need(root.is_absolute() and str(root)==os.path.normpath(str(root)),'canonical owner path')
    rootfd=open_dir(root);fds=[rootfd];entries=[];loaded=[]
    try:
        current=os.fstat(rootfd)
        need(type(expected_root) is dict and set(expected_root)=={'device','inode','kind'} and
             type(expected_root['device']) is int and expected_root['device']>=0 and
             type(expected_root['inode']) is int and expected_root['inode']>0 and
             expected_root=={'device':current.st_dev,'inode':current.st_ino,'kind':'directory'},'admitted owner source root differs')
        blobs={}
        for name,sha in OWNER_FILES.items():
            fd,raw,identity=open_bound(rootfd,name,sha);fds.append(fd);entries.append((rootfd,name,fd,identity,sha));blobs[name]=raw
        protocol_dir=root.parent/'authenticated-adapter-successor-1';pfd=open_dir(protocol_dir);fds.append(pfd)
        fd,raw,identity=open_bound(pfd,'custody_protocol_v2.py',PROTOCOL_SHA)
        fds.append(fd);entries.append((pfd,'custody_protocol_v2.py',fd,identity,PROTOCOL_SHA))
        protocol_root=os.fstat(pfd)
        bundle=PinnedBundle(fds,entries,[(str(root),rootfd,(current.st_dev,current.st_ino)),
                                       (str(protocol_dir),pfd,(protocol_root.st_dev,protocol_root.st_ino))]);bundle.verify()
        for name in ('materializer','source_freeze','split_inventory','union_owner'):
            need(name not in sys.modules,'refusing preloaded owner dependency: '+name)
            module=types.ModuleType(name);module.__file__=str(root/(name+'.py'))
            sys.modules[name]=module;loaded.append(name)
            exec(compile(blobs[name+'.py'],module.__file__,'exec'),module.__dict__)
        bundle.verify()
        return sys.modules['union_owner'],bundle
    except BaseException:
        for name in reversed(loaded):sys.modules.pop(name,None)
        for fd in reversed(fds):
            try:os.close(fd)
            except OSError:pass
        raise
