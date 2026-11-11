"""Actual FD-bound immutable-input checks for a future guarded scripts union.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Checks enforce immutable flags on every inventoried input inode. Root supervisor
must independently exclude privileged flag changes and keep lease/channel alive.
This module neither creates a snapshot nor grants operation authority.
"""
import fcntl
import os
import stat
import struct
from pathlib import Path
import materializer as m

FS_IOC_GETFLAGS=0x80086601
FS_IOC_SETFLAGS=0x40086602
FS_IMMUTABLE_FL=0x10


def immutable(fd):
    raw=bytearray(4)
    fcntl.ioctl(fd,FS_IOC_GETFLAGS,raw,True)
    return bool(struct.unpack('I',raw)[0] & FS_IMMUTABLE_FL)


def require_immutable(fd):
    if not immutable(fd): raise ValueError('source inode lacks immutable flag')


def st_id(fd):
    x=os.fstat(fd)
    return tuple(getattr(x,k) for k in m._FIELDS)


def mount_id(fd):
    raw=Path('/proc/self/fdinfo/%d'%fd).read_text()
    if len(raw)>65536:raise ValueError('fdinfo oversized')
    values=[line.split(':',1)[1].strip() for line in raw.splitlines() if line.startswith('mnt_id:')]
    if len(values)!=1 or not values[0].isdigit() or int(values[0])<=0:
        raise ValueError('descriptor mount id unavailable')
    return int(values[0])


class FrozenInputs:
    """Hold base directory FDs and added input FDs throughout owner lifetime."""
    def __init__(self,root,document):
        self.root=str(root);self.document=document;self.fds=[];self.directories={};self.added={}
        try:
            ns=m._load_checker()
            base={'base_root_mode':document['base_root_mode'],'base_members':document['base_members'],'additions':[]}
            self.mode,self.entries=ns['index_manifest'](base);self.checker=ns
            _,union=ns['index_manifest'](document)
            additions=document['additions']
            if len(additions)!=6 or any(x['type']!='file' or '/' in x['path'] for x in additions):
                raise ValueError('exact six top-level additions required')
            self.rootfd,self.rootpins=m._absolute_dir_pins(self.root);self.fds.append(self.rootfd)
            self.directories['']=(self.rootfd,st_id(self.rootfd));require_immutable(self.rootfd)
            paths=sorted((p for p,r in self.entries.items() if r['type']=='directory'),key=lambda p:(p.count('/'),p))
            identities={}
            for path in paths:
                fd=m._relative_dir(self.rootfd,path.split('/'),identities)
                self.fds.append(fd);require_immutable(fd)
                identities[path]=m._id(os.fstat(fd));self.directories[path]=(fd,st_id(fd))
            self.dirpins=identities
            for row in additions:
                path=row['source_candidate']
                if not os.path.isabs(path) or os.path.normpath(path)!=path:raise ValueError('invalid addition source path')
                parent,pins=m._absolute_dir_pins(os.path.dirname(path));self.fds.append(parent)
                require_immutable(parent)
                fd=os.open(os.path.basename(path),m._READ,dir_fd=parent);self.fds.append(fd)
                st=os.fstat(fd)
                if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1:raise ValueError('addition source is not unique file')
                require_immutable(fd)
                self.added[row['path']]=(parent,pins,fd,st_id(fd),path)
            self.verify()
        except BaseException:
            self.close();raise

    def verify(self):
        m._revalidate_destination_parent(self.root,self.rootpins,self.rootfd)
        for path,(fd,identity) in self.directories.items():
            if st_id(fd)!=identity:raise ValueError('source directory identity changed: '+path)
            require_immutable(fd)
            if path:
                current=m._relative_dir(self.rootfd,path.split('/'),self.dirpins)
                try:
                    if st_id(current)!=identity:raise ValueError('named source directory changed: '+path)
                finally:os.close(current)
        for path,row in self.entries.items():
            if row['type']!='file':continue
            parts=path.split('/');parent=self.directories['/'.join(parts[:-1])][0]
            before=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
            fd=os.open(parts[-1],m._READ,dir_fd=parent)
            try:
                current=os.fstat(fd)
                if not stat.S_ISREG(current.st_mode) or current.st_nlink!=1 or not m._same(before,current):
                    raise ValueError('source file changed: '+path)
                require_immutable(fd)
            finally:os.close(fd)
        for name,(parent,pins,fd,identity,path) in self.added.items():
            m._revalidate_destination_parent(os.path.dirname(path),pins,parent)
            if st_id(fd)!=identity or m._id(os.stat(os.path.basename(path),dir_fd=parent,follow_symlinks=False))!=m._id(os.fstat(fd)):
                raise ValueError('addition identity changed: '+name)
            require_immutable(parent);require_immutable(fd)
        m._verify(self.checker,self.rootfd,self.mode,self.entries)

    def epoch_start(self):
        self.epoch={fd:(st_id(fd),mount_id(fd)) for fd in self.fds}
        self.epoch_check()

    def epoch_check(self):
        if not hasattr(self,'epoch'):raise ValueError('source epoch not established')
        for fd,(identity,mount) in self.epoch.items():
            if st_id(fd)!=identity or mount_id(fd)!=mount:raise ValueError('source held descriptor changed')
            require_immutable(fd)
        m._revalidate_destination_parent(self.root,self.rootpins,self.rootfd)
        named_root=m._absolute_dir(self.root)
        try:
            if m._id(os.fstat(named_root))!=m._id(os.fstat(self.rootfd)) or mount_id(named_root)!=mount_id(self.rootfd):
                raise ValueError('source root mount changed')
        finally:os.close(named_root)
        for path,(fd,_) in self.directories.items():
            current=m._relative_dir(self.rootfd,path.split('/') if path else [],self.dirpins)
            try:
                if m._id(os.fstat(current))!=m._id(os.fstat(fd)) or mount_id(current)!=mount_id(fd):
                    raise ValueError('source named directory or mount changed: '+path)
            finally:os.close(current)
        for name,(parent,pins,fd,identity,path) in self.added.items():
            m._revalidate_destination_parent(os.path.dirname(path),pins,parent)
            named_parent=m._absolute_dir(os.path.dirname(path))
            try:
                if m._id(os.fstat(named_parent))!=m._id(os.fstat(parent)) or mount_id(named_parent)!=mount_id(parent):
                    raise ValueError('addition parent mount changed: '+name)
            finally:os.close(named_parent)
            named=os.open(os.path.basename(path),m._READ,dir_fd=parent)
            try:
                if st_id(named)!=identity or mount_id(named)!=mount_id(fd):raise ValueError('addition name or mount changed: '+name)
            finally:os.close(named)

    def close(self):
        for fd in reversed(self.fds):
            try:os.close(fd)
            except OSError:pass
        self.fds=[]

def verify_immutable_union(rootfd,document):
    """Check an existing complete union, including immutable flag on each inode."""
    ns=m._load_checker();mode,entries=ns['index_manifest'](document)
    require_immutable(rootfd)
    m._verify(ns,rootfd,mode,entries)
    pins={}
    for path in sorted((p for p,r in entries.items() if r['type']=='directory'),key=lambda p:(p.count('/'),p)):
        fd=m._relative_dir(rootfd,path.split('/'),pins)
        try:require_immutable(fd);pins[path]=m._id(os.fstat(fd))
        finally:os.close(fd)
    for path,row in entries.items():
        if row['type']!='file':continue
        parts=path.split('/');parent=m._relative_dir(rootfd,parts[:-1],pins)
        try:
            before=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
            fd=os.open(parts[-1],m._READ,dir_fd=parent)
            try:
                now=os.fstat(fd)
                if not stat.S_ISREG(now.st_mode) or now.st_nlink!=1 or not m._same(before,now):
                    raise ValueError('union file identity changed: '+path)
                require_immutable(fd)
            finally:os.close(fd)
        finally:os.close(parent)
    m._verify(ns,rootfd,mode,entries)


def freeze_union(rootfd,document,guard,journal):
    """Set immutable on all private union files then directories, root last.

    The owner must first durably publish an irreversible freeze intent. This
    routine never clears flags; any partial failure retains UNKNOWN ownership.
    Caller supplies a live, independently authenticated supervisor guard.
    """
    ns=m._load_checker();mode,entries=ns['index_manifest'](document)
    m._verify(ns,rootfd,mode,entries)
    paths=sorted((p for p,r in entries.items() if r['type']=='directory'),
                 key=lambda p:(p.count('/'),p))
    pins={}
    for path in paths:
        fd=m._relative_dir(rootfd,path.split('/'),pins)
        try:pins[path]=m._id(os.fstat(fd))
        finally:os.close(fd)

    def freeze(fd,path):
        if guard() is not True:raise ValueError('custody guard did not pass')
        before=os.fstat(fd);os.fsync(fd)
        raw=bytearray(4);fcntl.ioctl(fd,FS_IOC_GETFLAGS,raw,True)
        flags=struct.unpack('I',raw)[0]
        journal({'path':path,'device':before.st_dev,'inode':before.st_ino,
                 'mount_id':mount_id(fd),'prior_flags':flags,'new_flags':flags|FS_IMMUTABLE_FL})
        if guard() is not True:raise ValueError('custody guard lost after intent')
        fcntl.ioctl(fd,FS_IOC_SETFLAGS,struct.pack('I',flags|FS_IMMUTABLE_FL))
        os.fsync(fd);require_immutable(fd)
        if m._id(before)!=m._id(os.fstat(fd)):raise ValueError('freeze identity changed')
        if guard() is not True:raise ValueError('custody guard lost after freeze')

    for path,row in sorted(entries.items()):
        if row['type']!='file':continue
        parts=path.split('/');parent=m._relative_dir(rootfd,parts[:-1],pins)
        try:
            fd=os.open(parts[-1],m._READ,dir_fd=parent)
            try:freeze(fd,path)
            finally:os.close(fd)
        finally:os.close(parent)
    for path in reversed(paths):
        fd=m._relative_dir(rootfd,path.split('/'),pins)
        try:freeze(fd,path)
        finally:os.close(fd)
    freeze(rootfd,'.')
    verify_immutable_union(rootfd,document)
