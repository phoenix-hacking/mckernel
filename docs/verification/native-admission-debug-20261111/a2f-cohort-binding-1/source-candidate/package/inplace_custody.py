"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Reviewed future in-place immutable acquisition; no action runs on import.
Original source paths and bytes are retained; no flags are cleared here.
"""
import errno
import fcntl
import hashlib
import json
import os
import stat
import struct
import graph_observations as obs
from ownership_latch import CustodyLatch

GETFLAGS=0x80086601
SETFLAGS=0x40086602
IMMUTABLE=0x10


def check(ok,message):
    if not ok:raise ValueError(message)


def flags(fd):
    value=bytearray(4);fcntl.ioctl(fd,GETFLAGS,value,True)
    return struct.unpack('I',value)[0]


def unique(pairs):
    result={}
    for key,value in pairs:
        check(key not in result,'duplicate manifest key');result[key]=value
    return result


def write_all(fd,raw):
    position=0
    while position<len(raw):
        n=os.write(fd,raw[position:]);check(n>0,'short durable write');position+=n


def root_private(fd):
    st=os.fstat(fd)
    check(stat.S_ISDIR(st.st_mode) and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o700,'root-private operation directory')
    try:os.getxattr(fd,'system.posix_acl_access')
    except OSError as e:
        if e.errno==errno.ENODATA:return
        raise
    raise ValueError('extended ACL on private operation root')


def open_exact(path):
    """Pin actual host path, refusing symlink components and noncanonical names."""
    check(type(path) is str and path.startswith('/') and '//' not in path,'absolute host path')
    parts=path.split('/')[1:]
    check(parts and all(x not in ('','.','..') for x in parts),'host path')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        for i,part in enumerate(parts):
            st=os.stat(part,dir_fd=fd,follow_symlinks=False)
            check(stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode),'symlink or special source path')
            opts=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
            if i<len(parts)-1:opts|=os.O_DIRECTORY
            child=os.open(part,opts,dir_fd=fd)
            check(obs.stable(os.fstat(child))==obs.stable(st),'host identity changed while opening')
            os.close(fd);fd=child
        return fd
    except BaseException:
        os.close(fd);raise


def walk(fd,path,operation,receipt_fd=None):
    """Visit exact inode tree, rejecting links and preserving old flags in receipt."""
    before=os.fstat(fd)
    check(stat.S_ISDIR(before.st_mode) or stat.S_ISREG(before.st_mode),'unsupported source inode')
    if stat.S_ISDIR(before.st_mode):
        names=sorted(os.listdir(fd));check(len(names)<=500000,'source entry cap')
        for name in names:
            child_st=os.stat(name,dir_fd=fd,follow_symlinks=False)
            check(stat.S_ISDIR(child_st.st_mode) or stat.S_ISREG(child_st.st_mode),'source has symlink or special entry')
            opts=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
            if stat.S_ISDIR(child_st.st_mode):opts|=os.O_DIRECTORY
            child=os.open(name,opts,dir_fd=fd)
            try:
                check(obs.stable(os.fstat(child))==obs.stable(child_st),'source entry changed')
                walk(child,path+'/'+name,operation,receipt_fd)
            finally:os.close(child)
        check(sorted(os.listdir(fd))==names,'source membership changed')
    check(not stat.S_ISREG(before.st_mode) or before.st_nlink==1,'multiply linked source file')
    old=flags(fd)
    if operation=='inspect':return
    if operation=='freeze':
        check(receipt_fd is not None,'durable flag journal required')
        # Durable prior flags make later independently reviewed retirement possible.
        row={'path':path,'device':before.st_dev,'inode':before.st_ino,'old_flags':old}
        write_all(receipt_fd,obs.canonical(row)+b'\n');os.fsync(receipt_fd)
        if not old&IMMUTABLE:fcntl.ioctl(fd,SETFLAGS,struct.pack('I',old|IMMUTABLE))
    elif operation!='verify':raise ValueError('unknown source operation')
    after=os.fstat(fd)
    check((before.st_dev,before.st_ino)==(after.st_dev,after.st_ino) and flags(fd)&IMMUTABLE,'source identity/immutable changed')


def enumerate_source(fd,path,device,plan,seen):
    """Collect one first-record per exact inode before any flag is changed."""
    st=os.fstat(fd)
    check(st.st_dev==device and (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)), 'cross-device or unsupported source')
    check(not stat.S_ISREG(st.st_mode) or st.st_nlink==1, 'multiply linked source')
    key=(st.st_dev,st.st_ino)
    if key in seen:
        check(seen[key]==path, 'source inode has multiple paths')
        return
    check(len(plan)<500000, 'source enumeration cap')
    seen[key]=path
    original=flags(fd)
    plan[path]=(st.st_dev,st.st_ino,stat.S_IFMT(st.st_mode),original)
    if stat.S_ISDIR(st.st_mode):
        names=sorted(os.listdir(fd))
        for name in names:
            item=os.stat(name,dir_fd=fd,follow_symlinks=False)
            check(stat.S_ISDIR(item.st_mode) or stat.S_ISREG(item.st_mode), 'source symlink or special inode')
            opts=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
            if stat.S_ISDIR(item.st_mode):opts|=os.O_DIRECTORY
            child=os.open(name,opts,dir_fd=fd)
            try:
                check(obs.stable(os.fstat(child))==obs.stable(item),'source changed during enumeration')
                enumerate_source(child,path+'/'+name,device,plan,seen)
            finally:os.close(child)
        check(sorted(os.listdir(fd))==names and obs.stable(os.fstat(fd))==obs.stable(st),'source directory changed during enumeration')


def apply_plan(plan,journal,lease,latch,token):
    """Each inode has exactly one fsynced prior-flags record before ioctl."""
    for path in sorted(plan,key=lambda x:(-x.count('/'),x)):
        lease.verify();latch.check(token)
        fd=open_exact(path)
        try:
            st=os.fstat(fd);device,inode,kind,original=plan[path]
            check((st.st_dev,st.st_ino,stat.S_IFMT(st.st_mode),flags(fd))==(device,inode,kind,original),'planned inode/flags changed')
            write_all(journal,obs.canonical({'path':path,'device':device,'inode':inode,'old_flags':original})+b'\n')
            os.fsync(journal)
            if not original&IMMUTABLE:
                latch.publish(token,lambda:fcntl.ioctl(fd,SETFLAGS,struct.pack('I',original|IMMUTABLE)))
            check((os.fstat(fd).st_dev,os.fstat(fd).st_ino)==(device,inode) and flags(fd)&IMMUTABLE,'freeze not held')
        finally:os.close(fd)

def digest_path(path,st):
    return obs.inventory(path) if stat.S_ISDIR(st.st_mode) else obs.file_sha(path)


class ExactSourceCustody:
    """Hold 12 pinned original sources and four independently held owner outputs.

    Constructor and acquire are future root-only operations requiring an exact
    reviewed manifest, real lease, current owner and separate operation admission.
    The authenticated root supervisor validates these inputs; this class never
    accepts a Boolean callback or makes native/current-free claims.
    """
    def __init__(self,lease,root_fd,manifest_bytes,expected_manifest_sha,owner_fds,deadline_boot,latch):
        check(type(latch) is CustodyLatch,'operation latch required')
        check(os.geteuid()==0,'root supervisor required');root_private(root_fd)
        check(hashlib.sha256(manifest_bytes).hexdigest()==expected_manifest_sha,'manifest hash differs')
        manifest=json.loads(manifest_bytes,object_pairs_hook=unique)
        check(type(manifest) is dict and set(manifest)=={'sources','inode_plan_sha256','mount_map_sha256'},'manifest shape')
        for key in ('inode_plan_sha256','mount_map_sha256'):
            value=manifest[key]
            check(type(value) is str and len(value)==64 and all(x in '0123456789abcdef' for x in value),'manifest plan digest')
        self.expected_plan_sha=manifest['inode_plan_sha256'];self.expected_mount_sha=manifest['mount_map_sha256']
        specs=obs.contract()['mounts'];pinned=[x for x in specs if x['host'] is not None]
        sources=manifest['sources']
        check(type(sources) is list and len(sources)==len(pinned)==12,'12 original sources required')
        check(type(owner_fds) is dict and set(owner_fds)=={'/src/scripts','/out/build','/out/source/linux-6.12.0-211.44.1.el10_2','/work'},'four actual owner FDs required')
        self.lease,self.root_fd,self.sources,self.owner_fds=lease,root_fd,sources,dict(owner_fds)
        self.fds={};self.state='NEW';self.before={};self.epoch=None;self.deadline_boot=deadline_boot;self.latch=latch
        self.namespace_fd=os.open('/proc/self/ns/mnt',os.O_RDONLY|os.O_CLOEXEC)
        ns=os.fstat(self.namespace_fd);self.namespace_identity=(ns.st_dev,ns.st_ino)
        self.custody_sha256=hashlib.sha256(obs.canonical({'lease_sha256':lease.lease_sha256,'nonce':lease.nonce,
                                        'operation_root':obs.ident(os.fstat(root_fd))})).hexdigest()
        for row,spec in zip(sources,pinned):
            check(type(row) is dict and set(row)=={'target','host','content_sha256'},'source row shape')
            check(row['target']==spec['target'] and row['host']==spec['host'],'source contract changed')
            check(type(row['content_sha256']) is str and len(row['content_sha256'])==64 and all(x in '0123456789abcdef' for x in row['content_sha256']),'source digest')
            check(spec['sha256'] is None or spec['sha256']==row['content_sha256'],'source expected bytes differ')
            self.fds[row['target']]=open_exact(row['host'])
        self.lease.verify()

    def acquire(self):
        check(self.state=='NEW','single-use acquisition')
        token=self.latch.begin('OWNER_HELD')
        self.lease.verify();root_private(self.root_fd)
        # Enumerate every admitted mount/inode and original flag before mutation.
        plan={};seen={}
        process_identity=obs.process(os.getpid())
        check((process_identity[1],process_identity[2])==self.namespace_identity,'source namespace changed')
        mounts=obs.read_mountinfo(os.getpid(),process_identity)
        source_mounts={}
        # Verify every source before any flag mutation; existing bytes never change.
        for row in self.sources:
            fd=self.fds[row['target']];st=os.fstat(fd);named,_=obs.direct_path(row['host'])
            check((st.st_dev,st.st_ino)==(named.st_dev,named.st_ino),'source path changed')
            check(digest_path(row['host'],st)==row['content_sha256'],'source inventory mismatch')
            check(not any(m!=row['host'] and m.startswith(row['host'].rstrip('/')+'/') for m in mounts),'nested source mount')
            parents=[m for m in mounts if row['host']==m or row['host'].startswith(m.rstrip('/')+'/')]
            check(bool(parents),'source mount not observed')
            selected=max(parents,key=len)
            source_mounts[row['host']]={'mountpoint':selected,**mounts[selected]}
            enumerate_source(fd,row['host'],st.st_dev,plan,seen)
            self.before[row['target']]=(st.st_dev,st.st_ino)
        check(obs.process(os.getpid())==process_identity and obs.read_mountinfo(os.getpid(),process_identity)==mounts,'mount table changed during preflight')
        plan_bytes=obs.canonical({path:list(plan[path]) for path in sorted(plan)})
        mount_bytes=obs.canonical({'namespace':[process_identity[1],process_identity[2]],'roots':source_mounts})
        check(hashlib.sha256(plan_bytes).hexdigest()==self.expected_plan_sha,'admitted inode/flag plan differs')
        check(hashlib.sha256(mount_bytes).hexdigest()==self.expected_mount_sha,'admitted mount plan differs')
        name='SOURCE-FREEZE-INTENT-'+self.lease.nonce+'.jsonl'
        journal=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=self.root_fd)
        try:
            write_all(journal,obs.canonical({'status':'INTENT','lease_sha256':self.lease.lease_sha256,'nonce':self.lease.nonce,'custody_sha256':self.custody_sha256})+b'\n')
            os.fsync(journal);os.fsync(self.root_fd);self.state='FREEZE_INTENT'
            apply_plan(plan,journal,self.lease,self.latch,token)
            check(obs.process(os.getpid())==process_identity and obs.read_mountinfo(os.getpid(),process_identity)==mounts,'mount changed during freeze')
            for row in self.sources:
                st=os.fstat(self.fds[row['target']])
                check(digest_path(row['host'],st)==row['content_sha256'],'source bytes changed during freeze')
            write_all(journal,obs.canonical({'status':'HELD','nonce':self.lease.nonce})+b'\n');os.fsync(journal)
            self.state='VERIFYING'
            import immutable_epoch
            roots={row['target']:row['host'] for row in self.sources}
            hashes={row['target']:row['content_sha256'] for row in self.sources}
            self.epoch=immutable_epoch.ImmutableEpoch.__new__(immutable_epoch.ImmutableEpoch)
            self.epoch.__init__(roots,hashes,self.deadline_boot)
            self.verify()
            self.latch.publish(token,lambda:setattr(self,'state','HELD'))
        except BaseException:
            self.state='UNKNOWN_RETAINED';raise
        finally:os.close(journal)

    def verify(self):
        check(self.state in ('VERIFYING','HELD'),'source custody not established');self.lease.verify();root_private(self.root_fd)
        ns=os.fstat(self.namespace_fd);current=obs.process(os.getpid())
        check((ns.st_dev,ns.st_ino)==self.namespace_identity==(current[1],current[2]),'source namespace FD changed')
        for row in self.sources:
            fd=self.fds[row['target']];st=os.fstat(fd);named,_=obs.direct_path(row['host'])
            check((st.st_dev,st.st_ino)==self.before[row['target']]==(named.st_dev,named.st_ino),'source identity changed')
        check(self.epoch is not None,'full after-freeze epoch absent')
        self.epoch.verify()
        self.lease.verify()
