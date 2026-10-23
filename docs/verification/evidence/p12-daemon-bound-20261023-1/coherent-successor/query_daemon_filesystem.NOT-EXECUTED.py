"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Proposed read-only daemon/log-filesystem facts; one local GET /info only, no admission or workload.
Must receive a distinct exact-source review and source-bound owned_capture before execution.
"""
from pathlib import Path
import ast, hashlib, http.client, json, os, resource, socket, stat, struct, sys, time
from types import SimpleNamespace

BASE=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/identity-query/query.py')
BASE_SHA='2f88ff1f515ca3c8dbfa8b76718751a5e65f3842f4f187b3a387b0d776181cf9'
DAEMON_SHA='d9f25328687bb23bbe445a1f1bad90342388eace2723d4745903cd49cd1b2b66'
INFO_SOCKET='/var/run/docker.sock'
INFO_PATH='/info'

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
    """One read-only local /info request; no CLI/config/plugin/remote context."""
    class UnixConnection(http.client.HTTPConnection):
        def connect(self):
            self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
            self.sock.settimeout(15)
            self.sock.connect(INFO_SOCKET)
            self.peer=struct.unpack('3i',self.sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if self.peer[1]!=0:raise RuntimeError('local Docker endpoint peer is not root')
    connection=UnixConnection('localhost',timeout=15)
    try:
        connection.request('GET',INFO_PATH,headers={'Accept':'application/json',
                           'Accept-Encoding':'identity','Connection':'close'})
        response=connection.getresponse()
        if response.status!=200:raise RuntimeError('readonly local /info HTTP status='+str(response.status))
        if response.getheader('Content-Encoding') not in (None,'identity'):
            raise RuntimeError('unexpected readonly /info content encoding')
        raw=response.read(2*2**20+1)
        if len(raw)>2*2**20:raise RuntimeError('bounded readonly /info response exceeded')
        value=json.loads(raw)
        if type(value) is not dict or type(value.get('DockerRootDir')) is not str or not value['DockerRootDir']:
            raise RuntimeError('readonly /info root string required')
        return value['DockerRootDir'],dict(method='GET',path=INFO_PATH,socket=INFO_SOCKET,
                     peer=dict(pid=connection.peer[0],uid=connection.peer[1],gid=connection.peer[2]),
                     response_sha256=hashlib.sha256(raw).hexdigest(),response_bytes=len(raw),
                     status=response.status,configuration_or_plugin_reads=False,
                     peer_pid_matches_observed_daemon=connection.peer[0]==2036,
                     peer_qualification='SO_PEERCRED may identify socket-activation listener; record it, never infer process implementation binding from unmatchedPID.')
    finally:connection.close()

def main():
    if hashlib.sha256(BASE.read_bytes()).hexdigest()!=BASE_SHA:raise RuntimeError('reviewed identity source drift')
    if os.sched_getaffinity(0)!={7}:raise RuntimeError('exactCPU7 required')
    for kind,pair in [(resource.RLIMIT_AS,(2*2**30,)*2),(resource.RLIMIT_CPU,(30,30)),
                      (resource.RLIMIT_FSIZE,(8*2**20,)*2),(resource.RLIMIT_CORE,(0,0)),
                      (resource.RLIMIT_NOFILE,(256,256))]:
        if resource.getrlimit(kind)!=pair:raise RuntimeError('exact readonly query resource profile required')
    # Reuse only the two exact reviewed identity functions, not old module-level
    # 512MiB/FSIZE0 limits; parent uses its exact reviewed capture profile.
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
                allocation_tunables=knobs,effective_root_query=info_receipt,
                qualification='Facts only; not an ext4 allocation bound, admission, execution release or reader exclusion proof.',
                mutations=0,workloads=0)
    raw=json.dumps(result,sort_keys=True)
    if len(raw.encode())>16384:raise RuntimeError('bounded stdout record exceeded')
    print(raw,flush=True)

if __name__=='__main__':main()
