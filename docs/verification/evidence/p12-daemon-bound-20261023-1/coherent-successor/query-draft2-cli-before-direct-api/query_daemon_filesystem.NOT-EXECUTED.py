"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Proposed read-only daemon/log-filesystem facts; Docker info only, no admission or workload.
Must receive a distinct exact-source review and source-bound owned_capture before execution.
"""
from pathlib import Path
import ast, hashlib, json, os, resource, selectors, stat, struct, subprocess, sys, time
from types import SimpleNamespace

BASE=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/identity-query/query.py')
BASE_SHA='2f88ff1f515ca3c8dbfa8b76718751a5e65f3842f4f187b3a387b0d776181cf9'
DAEMON_SHA='d9f25328687bb23bbe445a1f1bad90342388eace2723d4745903cd49cd1b2b66'
CLI_SHA='2e94ad2db8c6c9cfffd02d403eea69a2d0bd14c84eb9dccdcebbcf2a68fcc257'
INFO_ARGV=['/usr/bin/docker','info','--format','{{json .DockerRootDir}}']

def bounded(path, cap):
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:
        before=os.fstat(fd);raw=os.read(fd,cap+1);after=os.fstat(fd)
        if len(raw)>cap:raise RuntimeError('bounded readonly input exceeded')
        if stat.S_ISREG(before.st_mode):
            for key in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns'):
                if getattr(before,key)!=getattr(after,key):raise RuntimeError('readonly input changed')
        return raw
    finally:os.close(fd)

def mount_for(path, text):
    rows=[]
    for line in text.splitlines():
        a,b=line.split(' - ',1);left=a.split();right=b.split()
        target=left[4].replace('\\040',' ')
        if str(path)==target or str(path).startswith(target.rstrip('/')+'/'):
            rows.append((len(target),left,right))
    if not rows:raise RuntimeError('no filesystem mount match')
    _,left,right=max(rows)
    return dict(device=left[2],mountpoint=left[4],mount_options=left[5],
                fs_type=right[0],source=right[1],super_options=right[2])

def effective_root():
    """One fixed read-only local Docker info request; bound/drain/join its CLI."""
    env={k:v for k,v in os.environ.items() if not k.startswith('DOCKER_')}
    env['DOCKER_HOST']='unix:///var/run/docker.sock'
    child=subprocess.Popen(INFO_ARGV,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,env=env,close_fds=True)
    out=[bytearray(),bytearray()];end=time.monotonic()+15
    try:
        with selectors.DefaultSelector() as poll:
            for index,stream in enumerate((child.stdout,child.stderr)):
                os.set_blocking(stream.fileno(),False);poll.register(stream,selectors.EVENT_READ,index)
            while poll.get_map():
                left=end-time.monotonic()
                if left<=0:raise RuntimeError('readonly info CLI deadline')
                for key,_ in poll.select(min(left,.1)):
                    raw=os.read(key.fd,4096)
                    if not raw:poll.unregister(key.fileobj)
                    else:
                        if len(out[key.data])+len(raw)>16384:raise RuntimeError('readonly info capture bound')
                        out[key.data].extend(raw)
        code=child.wait(timeout=max(.001,end-time.monotonic()))
        if code!=0 or out[1]:raise RuntimeError('readonly info failed, exit='+str(code)+' stderr_sha256='+hashlib.sha256(out[1]).hexdigest())
        value=json.loads(out[0])
        if type(value) is not str or not value:raise RuntimeError('readonly info root string required')
        return value,dict(argv=INFO_ARGV,endpoint=env['DOCKER_HOST'],stdout_sha256=hashlib.sha256(out[0]).hexdigest(),
                          stdout_bytes=len(out[0]),stderr_bytes=0,returncode=code,direct_child_joined=True)
    except BaseException:
        print(json.dumps(dict(readonly_info_partial_stdout_hex=bytes(out[0]).hex(),
                              readonly_info_partial_stderr_hex=bytes(out[1]).hex())),file=sys.stderr,flush=True)
        raise
    finally:
        if child.poll() is None:child.kill()
        child.wait(timeout=2)
        child.stdout.close();child.stderr.close()

def main():
    if hashlib.sha256(BASE.read_bytes()).hexdigest()!=BASE_SHA:raise RuntimeError('reviewed identity source drift')
    if os.sched_getaffinity(0)!={7}:raise RuntimeError('exactCPU7 required')
    for kind,pair in [(resource.RLIMIT_AS,(2*2**30,)*2),(resource.RLIMIT_CPU,(30,30)),
                      (resource.RLIMIT_FSIZE,(8*2**20,)*2),(resource.RLIMIT_CORE,(0,0)),
                      (resource.RLIMIT_NOFILE,(256,256))]:
        if resource.getrlimit(kind)!=pair:raise RuntimeError('exact readonly query resource profile required')
    # Reuse only the two exact reviewed identity functions, not old module-level
    # 512MiB/FSIZE0 limits which cannot run the reviewed Go CLI.
    tree=ast.parse(BASE.read_bytes(),str(BASE));names={'identity','digest'}
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    if len(functions)!=2:raise RuntimeError('reviewed helper function set changed')
    namespace=dict(os=os,stat=stat,hashlib=hashlib,PID=2036,EXPECTED_START='1513')
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(BASE),'exec'),namespace)
    q=SimpleNamespace(**namespace)
    if len(sys.argv)!=2 or q.digest(str(Path(__file__).resolve()))['sha256']!=sys.argv[1]:
        raise RuntimeError('exact readonly query source argument required')
    before=q.identity();pid=q.PID
    if os.readlink('/proc/%d/exe'%pid)!='/usr/bin/dockerd':raise RuntimeError('unexpected daemon executable')
    running=q.digest('/proc/%d/exe'%pid)
    if running['sha256']!=DAEMON_SHA:raise RuntimeError('daemon distro binding changed')
    root=os.stat('/proc/%d/root'%pid);host=os.stat('/')
    if (root.st_dev,root.st_ino)!=(host.st_dev,host.st_ino):raise RuntimeError('daemon root differs from host')
    status=bounded('/proc/%d/status'%pid,16384).decode()
    uid=next(x for x in status.splitlines() if x.startswith('Uid:')).split()[1:]
    if uid!=['0']*4:raise RuntimeError('root daemon expected')
    cli=q.digest('/usr/bin/docker')
    if cli['sha256']!=CLI_SHA:raise RuntimeError('readonly CLI distro binding changed')
    effective,info_receipt=effective_root()
    path=Path(effective)
    if not path.is_absolute() or path.resolve(strict=True)!=path:raise RuntimeError('canonical daemon root required')
    info=path.stat();v=os.statvfs(path)
    mounts=bounded('/proc/%d/mountinfo'%pid,262144).decode()
    mount=mount_for(path,mounts)
    if mount['fs_type']!='ext4':raise RuntimeError('actual Docker log filesystem is not ext4')
    if mount['device']!='%d:%d'%(os.major(info.st_dev),os.minor(info.st_dev)):
        raise RuntimeError('daemon root mounted device mismatch')
    device=Path(mount['source'])
    if not str(device).startswith('/dev/') or device.resolve(strict=True)!=device:
        raise RuntimeError('canonical block source required')
    block=device.stat()
    if not stat.S_ISBLK(block.st_mode) or block.st_rdev!=info.st_dev:raise RuntimeError('ext4 block identity mismatch')
    fd=os.open(device,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    try:superblock=os.pread(fd,1024,1024)
    finally:os.close(fd)
    if len(superblock)!=1024 or struct.unpack_from('<H',superblock,56)[0]!=0xef53:
        raise RuntimeError('ext4 superblock identity mismatch')
    fields={name:struct.unpack_from('<I',superblock,offset)[0] for name,offset in
            [('log_block_size',24),('log_cluster_size',28),('blocks_per_group',32),
             ('clusters_per_group',36),('feature_compat',92),('feature_incompat',96),('feature_ro_compat',100)]}
    sysroot=Path('/sys/fs/ext4')/device.name
    knobs={name:bounded(sysroot/name,1024).decode().strip() for name in
           ('mb_group_prealloc','mb_stream_req','mb_order2_req','max_writeback_mb_bump')}
    if q.identity()!=before or os.readlink('/proc/%d/exe'%pid)!='/usr/bin/dockerd':
        raise RuntimeError('daemon changed during readonly query')
    result=dict(scope=__doc__.splitlines()[0],observed_unix_ns=time.time_ns(),identity=before,
                running=running,kernel=dict(release=os.uname().release,version=os.uname().version),
                daemon_root=str(path),root_device=info.st_dev,root_inode=info.st_ino,mount=mount,
                statvfs=dict(f_bsize=v.f_bsize,f_frsize=v.f_frsize),
                ext4_superblock=fields,superblock_sha256=hashlib.sha256(superblock).hexdigest(),
                allocation_tunables=knobs,effective_root_query=info_receipt,cli=cli,
                qualification='Facts only; not an ext4 allocation bound, admission, execution release or reader exclusion proof.',
                mutations=0,workloads=0)
    raw=json.dumps(result,sort_keys=True)
    if len(raw.encode())>16384:raise RuntimeError('bounded stdout record exceeded')
    print(raw,flush=True)

if __name__=='__main__':main()
