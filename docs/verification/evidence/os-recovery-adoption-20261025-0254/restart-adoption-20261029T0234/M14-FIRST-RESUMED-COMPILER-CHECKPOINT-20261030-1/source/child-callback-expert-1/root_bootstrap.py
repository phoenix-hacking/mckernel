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


def _pinned_file(path, expected_sha, limit=2*1024*1024):
    """Return retained FD and exact verified bytes; no symlink path components."""
    if type(path) is not str or not path.startswith('/') or '//' in path:
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


def pinned_root_file(path,expected_sha,limit=2*1024*1024):
    if os.geteuid()!=0:raise ValueError('root required')
    return _pinned_file(path,expected_sha,limit)


def pinned_validator_file(path,expected_sha,limit=2*1024*1024):
    if os.getuid()!=1000 or os.geteuid()!=1000:raise ValueError('ordinary validator required')
    return _pinned_file(path,expected_sha,limit)


def load_verified_validator_module(name,path,expected_sha):
    fd,raw=pinned_validator_file(path,expected_sha)
    module=types.ModuleType(name);module.__file__=path
    if name in sys.modules:os.close(fd);raise ValueError('module already loaded')
    sys.modules[name]=module
    try:
        exec(compile(raw,path,'exec'),module.__dict__)
        return fd,module
    except BaseException:
        sys.modules.pop(name,None);os.close(fd);raise


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
names=('ownership_latch','custody_protocol_v2','graph_observations','pidfd_compat','runtime_binding','pidfd_custody','deferred_fork','inplace_custody','immutable_epoch','adapter','materializer','source_freeze','split_inventory','union_server_guarded','graph_producer','graph_server','operation_supervisor','supervisor_entry')
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


VALIDATOR_INLINE = r"""import base64,json,os,sys,types
m=types.ModuleType('root_bootstrap');m.__file__='<verified-bootstrap-bytes>';sys.modules['root_bootstrap']=m
exec(compile(base64.b64decode(sys.argv[1],validate=True),m.__file__,'exec'),m.__dict__)
fd,raw=m.pinned_validator_file(sys.argv[2],sys.argv[3]);hold=[fd]
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('duplicate loader key')
  d[k]=v
 return d
config=json.loads(raw,object_pairs_hook=unique)
if set(config)!={'modules','extra_files','runtime'}:raise ValueError('validator loader config')
names=('ownership_latch','graph_observations','pidfd_compat','pidfd_custody','deferred_fork','runtime_binding','adapter','compositor','validator_entry')
if set(config['modules'])!=set(names):raise ValueError('validator module set')
base='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/RESTART-REPAIR-20261030/combined-graph-source-1'
local=os.path.dirname(config['modules']['adapter']['path'])
if local!=os.path.dirname(config['modules']['compositor']['path']):raise ValueError('validator source directory')
expected={os.path.join(local,'custody_protocol_v2.py'):'587cebf7b8359a1711f078882a012a701e290902dc4376d1bc6e4c03f7ce8cbb',
 os.path.join(base,'candidate_data.py'):'74eec517909d92d178d77771dd8ae59e826df50cd17121957a03e320b93d1c96',
 os.path.join(base,'contract.json'):'d4b38335f7d1af1998b9999a676ae5eee40b2b640021a144d19169328d68e0fd',
 os.path.join(local,'GRAPH-CONTRACT.json'):'d4b38335f7d1af1998b9999a676ae5eee40b2b640021a144d19169328d68e0fd'}
profile=os.path.join(local,'PROFILE.V2.SOURCE-ONLY.json')
if set(config['extra_files'])!=set(expected)|{profile}:raise ValueError('validator source closure')
if any(config['extra_files'][path]!=sha for path,sha in expected.items()):raise ValueError('validator source closure hash')
for path,sha in config['extra_files'].items():
 fd,_=m.pinned_validator_file(path,sha);hold.append(fd)
for name in names:
 spec=config['modules'][name]
 if set(spec)!={'path','sha256'}:raise ValueError('validator module pin')
 fd,mod=m.load_verified_validator_module(name,spec['path'],spec['sha256']);hold.append(fd)
if config['modules']['validator_entry']['path']!=sys.argv[4]:raise ValueError('validator entry path')
if set(config['runtime'])!={'path','sha256'}:raise ValueError('validator runtime binding')
sys.modules['runtime_binding'].verify_current(config['runtime']['path'],config['runtime']['sha256'])
sys.modules['validator_entry'].run()
"""


def validator_argv(executable,verified_bootstrap_bytes,loader_manifest,loader_sha,entry_path):
    if type(verified_bootstrap_bytes) is not bytes or not verified_bootstrap_bytes:
        raise ValueError('verified bootstrap bytes required')
    return [executable,'-I','-B','-c',VALIDATOR_INLINE,
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


def fork_validator(executable,argv,uid,gid,environment,record,guard,journal_fd,nonce):
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
    if type(nonce) is not str or len(nonce)!=64 or any(x not in '0123456789abcdef' for x in nonce):raise ValueError('operation nonce required')
    if type(journal_fd) is not int or journal_fd<3:raise ValueError('owned custody journal required')
    journal=os.fstat(journal_fd);mode=fcntl.fcntl(journal_fd,fcntl.F_GETFL)
    if (not stat.S_ISREG(journal.st_mode) or journal.st_uid!=0 or stat.S_IMODE(journal.st_mode)!=0o600 or
        journal.st_nlink!=1 or not mode&os.O_APPEND or mode&os.O_ACCMODE==os.O_RDONLY):
        raise ValueError('root-created append-only custody journal required')
    parent,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_STREAM)
    record.add(parent,child,journal_fd)
    try:
        def child_exec():
            parent.close()
            channel=child.fileno()
            if channel==journal_fd:raise ValueError('journal and channel alias')
            for fd in (channel,journal_fd):os.set_inheritable(fd,True)
            upper=resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            if upper==resource.RLIM_INFINITY or upper>1048576:upper=1048576
            keep=sorted((channel,journal_fd))
            os.closerange(3,keep[0]);os.closerange(keep[0]+1,keep[1]);os.closerange(keep[1]+1,int(upper))
            os.setgroups([]);os.setresgid(gid,gid,gid);os.setresuid(uid,uid,uid)
            env=dict(environment);env['MCKERNEL_CUSTODY_FD']=str(channel)
            env['MCKERNEL_PIDFD_CUSTODY_JOURNAL_FD']=str(journal_fd)
            env['MCKERNEL_PIDFD_CUSTODY_NONCE']=nonce
            os.execve(executable,argv,env)
        pid,pidfd,birth=guard.fork_and_pin(record,child_exec)
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
        def child_exec():
            parent.close();channel=child.fileno();os.set_inheritable(channel,True)
            upper=resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            if upper==resource.RLIM_INFINITY or upper>1048576:upper=1048576
            os.closerange(3,channel);os.closerange(channel+1,int(upper))
            env=dict(environment);env['MCKERNEL_UNION_CUSTODY_FD']=str(channel)
            os.execve(executable,argv,env)
        pid,pidfd,birth=guard.fork_and_pin(record,child_exec)
        child.close()
        return parent,pid,pidfd,('BOUND',None)
    except BaseException as error:
        record.unknown(error);raise


if __name__=='__main__':
    raise RuntimeError('SOURCE ONLY: no reviewed root bootstrap, owner custody or execution admission')
