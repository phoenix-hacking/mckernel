"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only bootstrap primitives; no install, operation or controller is started.
"""
import fcntl
import base64
import hashlib
import os
import resource
import socket
import stat
import struct
import sys
import types

FS_IOC_GETFLAGS = 0x80086601
FS_IMMUTABLE_FL = 0x10


def immutable(fd):
    data=bytearray(4)
    fcntl.ioctl(fd,FS_IOC_GETFLAGS,data,True)
    return bool(struct.unpack('I',data)[0] & FS_IMMUTABLE_FL)


def pinned_root_file(path, expected_sha, limit=2*1024*1024):
    """Return retained FD and exact verified bytes; no symlink path components."""
    if os.geteuid()!=0 or type(path) is not str or not path.startswith('/') or '//' in path:
        raise ValueError('root absolute path required')
    parts=path.split('/')[1:]
    if not parts or any(part in ('','.','..') for part in parts): raise ValueError('bad path')
    root=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        for index,part in enumerate(parts):
            st=os.fstat(root)
            if st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022 or not stat.S_ISDIR(st.st_mode):
                raise ValueError('untrusted source ancestry')
            flags=os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW
            if index<len(parts)-1:flags|=os.O_DIRECTORY
            child=os.open(part,flags,dir_fd=root)
            os.close(root);root=child
        s=os.fstat(root)
        if (not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_nlink!=1 or
            stat.S_IMODE(s.st_mode)&0o022 or not immutable(root) or s.st_size>limit):
            raise ValueError('source is not immutable root-owned file')
        raw=b''
        while len(raw)<=limit:
            chunk=os.read(root,65536)
            if not chunk:break
            raw+=chunk
        if len(raw)>limit or hashlib.sha256(raw).hexdigest()!=expected_sha:
            raise ValueError('source bytes mismatch')
        after=os.fstat(root)
        if (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError('source changed')
        return root,raw
    except BaseException:
        os.close(root)
        raise


def load_verified_module(name,path,expected_sha):
    """Execute exactly the bytes read from a held immutable root-owned FD."""
    fd,raw=pinned_root_file(path,expected_sha)
    module=types.ModuleType(name);module.__file__=path
    sys.modules[name]=module
    try:
        exec(compile(raw,path,'exec'),module.__dict__)
        return fd,module
    except BaseException:
        sys.modules.pop(name,None);os.close(fd);raise


SUPERVISOR_INLINE = r"""import base64,json,os,sys,types
m=types.ModuleType('root_bootstrap');m.__file__='<verified-bootstrap-bytes>';sys.modules['root_bootstrap']=m
exec(compile(base64.b64decode(sys.argv[1],validate=True),m.__file__,'exec'),m.__dict__)
fd,raw=m.pinned_root_file(sys.argv[2],sys.argv[3]);hold=[fd]
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('duplicate loader key')
  d[k]=v
 return d
config=json.loads(raw,object_pairs_hook=unique)
if set(config)!={'modules','extra_files','operation_config_path','operation_config_sha','runtime'}:raise ValueError('loader config')
names=('ownership_latch','custody_protocol_v2','graph_observations','pidfd_compat','runtime_binding','deferred_fork','inplace_custody','immutable_epoch','adapter','materializer','source_freeze','split_inventory','union_server_guarded','graph_producer','graph_server','operation_supervisor','supervisor_entry')
if set(config['modules'])!=set(names):raise ValueError('module set')
checker=os.path.join(os.path.dirname(config['modules']['materializer']['path']),'verify_scripts_fd.py')
if set(config['extra_files'])!={checker}:raise ValueError('checker source closure')
for path,sha in config['extra_files'].items():
 fd,_=m.pinned_root_file(path,sha);hold.append(fd)
for name in names:
 spec=config['modules'][name]
 if set(spec)!={'path','sha256'}:raise ValueError('module pin')
 fd,mod=m.load_verified_module(name,spec['path'],spec['sha256']);hold.append(fd)
if config['modules']['supervisor_entry']['path']!=sys.argv[4]:raise ValueError('entry path')
if set(config['runtime'])!={'path','sha256'}:raise ValueError('runtime binding')
sys.modules['runtime_binding'].verify_current(config['runtime']['path'],config['runtime']['sha256'])
root_fd=int(os.environ['MCKERNEL_OPERATION_ROOT_FD']);lease_fd=int(os.environ['MCKERNEL_OPERATION_LEASE_FD'])
sys.modules['supervisor_entry'].run(config['operation_config_path'],config['operation_config_sha'],root_fd,lease_fd)
"""


def supervisor_argv(executable,verified_bootstrap_bytes,loader_manifest,loader_sha,entry_path):
    """Use parent-verified bytes in argv; child executes exactly those bytes."""
    if type(verified_bootstrap_bytes) is not bytes or not verified_bootstrap_bytes:
        raise ValueError('verified bootstrap bytes required')
    return [executable,'-I','-B','-c',SUPERVISOR_INLINE,
            base64.b64encode(verified_bootstrap_bytes).decode('ascii'),loader_manifest,loader_sha,entry_path]


OWNER_INLINE = r"""import base64,os,sys,types
m=types.ModuleType('root_bootstrap');m.__file__='<verified-bootstrap-bytes>';sys.modules['root_bootstrap']=m
exec(compile(base64.b64decode(sys.argv[1],validate=True),m.__file__,'exec'),m.__dict__)
fd,entry=m.load_verified_module('root_owner_entry',sys.argv[2],sys.argv[3])
entry.run(sys.argv[4],sys.argv[5],int(os.environ['MCKERNEL_UNION_CUSTODY_FD']))
"""


def owner_argv(executable,verified_bootstrap_bytes,entry_path,entry_sha,config_path,config_sha):
    if type(verified_bootstrap_bytes) is not bytes or not verified_bootstrap_bytes:
        raise ValueError('verified bootstrap bytes required')
    return [executable,'-I','-B','-c',OWNER_INLINE,base64.b64encode(verified_bootstrap_bytes).decode('ascii'),
            entry_path,entry_sha,config_path,config_sha]


def fork_validator(executable,argv,uid,gid,environment,record,guard):
    """Root creates socketpair then forks; child cannot retain root custody FDs.

    Caller must have source-bound and admitted the executable, argv, uid/gid,
    resource limits, identities and operation. The caller retains the socket,
    process ownership and all operation leases. No call occurs at import.
    """
    if os.geteuid()!=0 or type(uid) is not int or uid<=0 or type(gid) is not int or gid<=0:
        raise ValueError('root parent and ordinary child required')
    if type(argv) is not list or not argv or argv[0]!=executable or not all(type(x) is str for x in argv):
        raise ValueError('exact validator argv required')
    if type(environment) is not dict or any(type(k) is not str or type(v) is not str for k,v in environment.items()):
        raise ValueError('exact validator environment required')
    from ownership_latch import ChildRecord
    from deferred_fork import DeferredFork
    if type(record) is not ChildRecord or type(guard) is not DeferredFork or not guard.entered:
        raise ValueError('guarded pre-registered child custody required')
    parent,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    record.add(parent,child)
    try:
        pid,pidfd,birth=guard.fork_and_pin(record)
        if pid==0:
            try:
                parent.close()
                channel=child.fileno();os.set_inheritable(channel,True)
                upper=resource.getrlimit(resource.RLIMIT_NOFILE)[0]
                if upper==resource.RLIM_INFINITY or upper>1048576:upper=1048576
                os.closerange(3,channel);os.closerange(channel+1,int(upper))
                os.setgroups([]);os.setresgid(gid,gid,gid);os.setresuid(uid,uid,uid)
                env=dict(environment);env['MCKERNEL_CUSTODY_FD']=str(channel)
                os.execve(executable,argv,env)
            finally:
                os._exit(127)
        child.close()
        return parent,pid,pidfd,('BOUND',None)
    except BaseException as error:
        record.unknown(error);raise


def fork_union_owner(executable,argv,environment,record,guard):
    """Fork a separately source-bound root union owner on a root-created channel.

    This does not itself authenticate an executable or grant a workload release;
    the caller must first verify the root-owned immutable executable and exact
    loaded source bytes, one-shot admission and resource ownership.
    """
    if os.geteuid()!=0 or type(argv) is not list or not argv or argv[0]!=executable:
        raise ValueError('root parent and exact owner argv required')
    if type(environment) is not dict or any(type(k) is not str or type(v) is not str for k,v in environment.items()):
        raise ValueError('exact owner environment required')
    from ownership_latch import ChildRecord
    from deferred_fork import DeferredFork
    if type(record) is not ChildRecord or type(guard) is not DeferredFork or not guard.entered:
        raise ValueError('guarded pre-registered child custody required')
    parent,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    record.add(parent,child)
    try:
        pid,pidfd,birth=guard.fork_and_pin(record)
        if pid==0:
            try:
                parent.close();channel=child.fileno();os.set_inheritable(channel,True)
                upper=resource.getrlimit(resource.RLIMIT_NOFILE)[0]
                if upper==resource.RLIM_INFINITY or upper>1048576:upper=1048576
                os.closerange(3,channel);os.closerange(channel+1,int(upper))
                env=dict(environment);env['MCKERNEL_UNION_CUSTODY_FD']=str(channel)
                os.execve(executable,argv,env)
            finally:os._exit(127)
        child.close()
        return parent,pid,pidfd,('BOUND',None)
    except BaseException as error:
        record.unknown(error);raise


if __name__=='__main__':
    raise RuntimeError('SOURCE ONLY: no reviewed root bootstrap, owner custody or execution admission')
