"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Proposed read-only daemon/log-filesystem facts; no Docker API, admission or workload.
Must receive a distinct exact-source execution review and pipe capture before execution.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, stat, struct, time

BASE=Path('/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/identity-query/query.py')
BASE_SHA='2f88ff1f515ca3c8dbfa8b76718751a5e65f3842f4f187b3a387b0d776181cf9'
DAEMON_SHA='d9f25328687bb23bbe445a1f1bad90342388eace2723d4745903cd49cd1b2b66'

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

def main():
    if hashlib.sha256(BASE.read_bytes()).hexdigest()!=BASE_SHA:raise RuntimeError('reviewed identity source drift')
    s=importlib.util.spec_from_file_location('released_identity_helper',BASE)
    q=importlib.util.module_from_spec(s);s.loader.exec_module(q)  # Existing512MiB/10CPU/FSIZE0 limits.
    before=q.identity();pid=q.PID
    if os.readlink('/proc/%d/exe'%pid)!='/usr/bin/dockerd':raise RuntimeError('unexpected daemon executable')
    running=q.digest('/proc/%d/exe'%pid)
    if running['sha256']!=DAEMON_SHA:raise RuntimeError('daemon distro binding changed')
    root=os.stat('/proc/%d/root'%pid);host=os.stat('/')
    if (root.st_dev,root.st_ino)!=(host.st_dev,host.st_ino):raise RuntimeError('daemon root differs from host')
    status=bounded('/proc/%d/status'%pid,16384).decode()
    uid=next(x for x in status.splitlines() if x.startswith('Uid:')).split()[1:]
    if uid!=['0']*4:raise RuntimeError('root daemon expected')
    args=bounded('/proc/%d/cmdline'%pid,32768).decode().rstrip('\0').split('\0')
    data_root=None;config_path='/etc/docker/daemon.json'
    for index,arg in enumerate(args[1:],1):
        for flag in ('--data-root','-g','--config-file'):
            if arg==flag:
                if index+1>=len(args):raise RuntimeError('incomplete daemon option')
                if flag=='--config-file':config_path=args[index+1]
                else:data_root=args[index+1]
            elif arg.startswith(flag+'='):
                if flag=='--config-file':config_path=arg.split('=',1)[1]
                else:data_root=arg.split('=',1)[1]
    config={};config_sha=None
    try:
        raw=bounded(config_path,65536);config=json.loads(raw);config_sha=hashlib.sha256(raw).hexdigest()
    except FileNotFoundError:pass
    if type(config) is not dict:raise RuntimeError('daemon config object required')
    if data_root is not None and 'data-root' in config:raise RuntimeError('ambiguous daemon data-root')
    path=Path(data_root or config.get('data-root','/var/lib/docker'))
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
                allocation_tunables=knobs,config_path=config_path,config_sha256=config_sha,
                qualification='Facts only; not an ext4 allocation bound, admission, execution release or reader exclusion proof.',
                mutations=0,workloads=0)
    raw=json.dumps(result,sort_keys=True)
    if len(raw.encode())>16384:raise RuntimeError('bounded stdout record exceeded')
    print(raw,flush=True)

if __name__=='__main__':main()
