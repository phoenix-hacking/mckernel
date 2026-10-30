"""One-shot root parent bootstrap, source-only; hashes must be reviewed."""
import fcntl,hashlib,json,os,signal,stat,sys,types
from decimal import Decimal

BASE='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1'
PARENT_PATH=BASE+'/root-install-parent-successor-4/root_parent.py'
ENTRY_PATH=BASE+'/root-install-direct-child-successor-4/direct_entry.py'
DATA_PATH=BASE+'/root-install-caller-data-output-1/data_output.py'
DATA_SHA='6e1197061e4c7f99abcea965c6b1fd6beb18556497174ed38e725dbbeeef3b22'
PARENT_SHA='ffdad75a89dd433fa459968a3758e28d24809119698ba0afb2fd7ffbc02eeba3'
ENTRY_SHA='7ac4718a01be185cc1d816bf5c91e84960b73ca51209d7c3b909cda354ccfcea'
MAX=2097152
hold=[]


def unique(pairs):
    out={}
    for key,value in pairs:
        if key in out:raise ValueError('duplicate JSON key')
        out[key]=value
    return out


def read_fd(fd,maximum):
    st=os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_size>maximum:raise ValueError('bounded regular input')
    os.lseek(fd,0,os.SEEK_SET);chunks=[];total=0
    while total<=maximum:
        chunk=os.read(fd,min(65536,maximum+1-total))
        if not chunk:break
        chunks.append(chunk);total+=len(chunk)
    now=os.fstat(fd);raw=b''.join(chunks)
    if total!=st.st_size or total>maximum or (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)!=(now.st_dev,now.st_ino,now.st_size,now.st_mtime_ns,now.st_ctime_ns):raise ValueError('input changed')
    return raw


STOPS=(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM)


def owned_open(path,flags,dir_fd=None):
    # Register before allocation; a deferred handler sees a recorded leaf.
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        record={'state':'PENDING_OPEN','fd':None,'historical_fd':None};hold.append(record)
        try:fd=os.open(path,flags,dir_fd=dir_fd)
        except BaseException:
            record['state']='OPEN_UNKNOWN';raise
        record['fd']=fd;record['state']='OWNED'
        return record
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def close_ancestor(record):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        if record['state']!='OWNED' or type(record['fd']) is not int:raise ValueError('ancestor disposition')
        fd=record['fd'];record['fd']=None;record['historical_fd']=fd;record['state']='CLOSING'
        try:os.close(fd)
        except BaseException:
            record['state']='CLOSURE_UNKNOWN'
            raise
        record['state']='VERIFIED_CLOSED'
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def open_absolute(path):
    if type(path) is not str or not path.startswith('/') or '//' in path:raise ValueError('absolute source path')
    parts=path.split('/')[1:]
    if not parts or any(x in ('','.','..') for x in parts):raise ValueError('path component')
    current=owned_open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    for component in parts[:-1]:
        child=owned_open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=current['fd'])
        close_ancestor(current);current=child
    leaf=owned_open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=current['fd'])
    close_ancestor(current)
    return leaf['fd']


def verified(path,digest):
    fd=open_absolute(path);raw=read_fd(fd,MAX)
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('fixed source/input hash')
    return raw


def load(name,path,raw):
    if name in sys.modules:raise ValueError('preloaded module')
    module=types.ModuleType(name);module.__file__=path;sys.modules[name]=module
    exec(compile(raw,path,'exec'),module.__dict__)
    return module


def main():
    if os.getuid()!=0 or os.geteuid()!=0 or len(sys.argv)!=6:raise ValueError('root and exact arguments')
    admission_sha,review_path,review_sha,capture_device,capture_inode=sys.argv[1:]
    if not capture_device.isdigit() or not capture_inode.isdigit():raise ValueError('capture identity arguments')
    capture=os.fstat(1);flags=fcntl.fcntl(1,fcntl.F_GETFL)
    if (not stat.S_ISREG(capture.st_mode) or capture.st_uid!=1000 or capture.st_nlink!=1 or
        stat.S_IMODE(capture.st_mode)!=0o600 or (flags&os.O_ACCMODE)==os.O_RDONLY or
        (capture.st_dev,capture.st_ino)!=(int(capture_device),int(capture_inode))):
        raise ValueError('actual caller stdout capture identity differs')
    if any(len(x)!=64 or any(c not in '0123456789abcdef' for c in x) for x in (admission_sha,review_sha)):raise ValueError('input digest')
    admission_raw=read_fd(0,MAX)
    if hashlib.sha256(admission_raw).hexdigest()!=admission_sha:raise ValueError('stdin admission bytes')
    review_raw=verified(review_path,review_sha)
    entry_raw=verified(ENTRY_PATH,ENTRY_SHA);parent_raw=verified(PARENT_PATH,PARENT_SHA)
    entry=load('direct_entry',ENTRY_PATH,entry_raw)
    entry.load_for_parent()
    data_raw=verified(DATA_PATH,DATA_SHA)
    load('caller_data_output',DATA_PATH,data_raw)
    parent=load('root_parent',PARENT_PATH,parent_raw)
    parent.EXPECTED_CAPTURE=(capture.st_dev,capture.st_ino)
    request=json.loads(admission_raw,object_pairs_hook=unique)
    if type(request) is not dict or request.get('outer_pid')!=2996005 or request.get('outer_birth')!='118034116':raise ValueError('actual Root outer identity')
    prelim=sys.modules['reviewed_controller_reader'];issuer=sys.modules['install_issuer']
    issuer.require_outer_ancestor(prelim,request['outer_pid'],request['outer_birth'])
    controls_raw,_=prelim.read_bound(prelim.CONTROLS,1<<20);capacity_raw,_=prelim.read_bound(prelim.CAPACITY,1<<20)
    controls=prelim.strict_json(controls_raw);capacity=prelim.strict_json(capacity_raw)
    live=prelim.controller_checks(controls,capacity,__import__('time').time())
    ns=lambda x:int(Decimal(str(x))*1000000000)
    caps={'boot_ns':request['deadline_boot_ns'],'mono_ns':request['deadline_mono_ns'],'utc_ns':request['utc_cap_ns']}
    if any(type(x) is not int for x in caps.values()) or caps['boot_ns']>ns(live['boot_deadline']) or caps['mono_ns']>ns(live['monotonic_deadline']) or caps['utc_ns']>ns(live['deadline']):raise ValueError('inherited caps')
    roles=list(controls['binding'].values())+[capacity['supervisor']]
    actor_pids=[row['pid'] for row in roles]
    # The parent publishes the full DATA and its final disposition itself.
    parent.serve(admission_raw,admission_sha,review_raw,review_sha,request['nonce'],caps,actor_pids)


if __name__=='__main__':main()
