"""Functional-only fixed Root parent/keeper loader; source only, no self-launch."""
import hashlib
import json
import os
import signal
import socket
import stat
import sys
import types

BASE='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1'
HERE=BASE+'/root-install-direct-child-successor-1'
PACKAGE=BASE+'/root-install-source-10/package'
PRELIM=BASE+'/postjoin-daemon-metadata-observer-source-1/root_parent_preliminary.py'
IPC=BASE+'/root-install-parent-successor-1/parent_control.py'
PINS={'ownership_latch':'fb264b1e6f12852e6a11c44239089a015a02e25019f9094af586422398bfa390',
      'graph_observations':'df7bb673c206585318a4e41a58486c05548d9981b81074baeb29437f458114ed',
      'pidfd_compat':'068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c',
      'pidfd_custody':'3b22cac50183723456e6701031f00bdc446c04641c08c5864f1a379b5407686e',
      'deferred_fork':'b28d2f3483fb90c858479b65c9cebe6bd1b586c01902f004ec44964da6b4625f'}
INSTALL_SHA='6fa1cca87cb3e5b2cfdfc746875dd3909bfa084052b9344d48931de959e68888'
ISSUER_SHA='6f2af752859fea25da9fb9f477cec0d2d7560b9a7acdc374e1259c4f2db0c9d3'
COMPLETION_SHA='95e8cb63f3eec26956f6a46ca612d13d26aef70deb291b1ad453b74fb537aa1c'
PHASE_SHA='71924a45f37d9b440eb4e398899f0336a9c2ab5414bffc9d02d24ec907811777'
WAIT_SHA='f635e2c1daf9942b830a3aed3e8fdff2a8abe13096256a886193f5d4773354a2'
IPC_SHA='eda1ff0139c3bbf0c713009fc7728eccf3418cc7ce5d028731bc443837d49bbe'
CLOSURE_SHA='81be55d5bf48ff462d291683ef1a26238b27581026bc5ffacc488125b6667ba6'
PRELIM_SHA='de6de10ff79d07281e95216a5ecf751d03bade1d75445c87abd8a2e0405e124d'
HELD=[]
LOADED=None
STOPS=(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM)


def held_open(path,flags,dir_fd=None):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        HELD.append(None);slot=len(HELD)-1
        try:fd=os.open(path,flags,dir_fd=dir_fd)
        except BaseException:HELD.pop();raise
        HELD[slot]=fd;return fd
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def verified(path,expected):
    if type(path) is not str or not path.startswith('/') or '//' in path:raise ValueError('absolute source path')
    parts=path.split('/')[1:]
    if not parts or any(part in ('','.','..') for part in parts):raise ValueError('source path components')
    current=held_open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    for part in parts[:-1]:current=held_open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=current)
    fd=held_open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=current)
    st=os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_size>2097152:raise ValueError('bounded regular source required')
    raw=b''
    while len(raw)<=2097152:
        block=os.read(fd,min(65536,2097153-len(raw)))
        if not block:break
        raw+=block
    after=os.fstat(fd)
    if ((st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(raw)!=st.st_size or hashlib.sha256(raw).hexdigest()!=expected):raise ValueError('verified source differs')
    return fd,raw


def module(name,path,expected):
    fd,raw=verified(path,expected)
    value=types.ModuleType(name);value.__file__=path;sys.modules[name]=value
    exec(compile(raw,path,'exec'),value.__dict__)
    return value,fd,raw


def load_for_parent():
    """Load the fixed exact closure before fork; never starts an operation."""
    global LOADED
    if LOADED is not None:return LOADED['completion']
    for name in ('ownership_latch','graph_observations','pidfd_compat','pidfd_custody','deferred_fork'):
        module(name,PACKAGE+'/'+name+'.py',PINS[name])
    ipc,ipc_fd,ipc_raw=module('parent_control',IPC,IPC_SHA)
    installer_fd,installer_raw=verified(HERE+'/install_source_closure.py',INSTALL_SHA)
    install=types.ModuleType('install_source_closure');install.__file__=HERE+'/install_source_closure.py'
    install._BOOTSTRAP_INSTALLER_HASH=INSTALL_SHA;install._BOOTSTRAP_SOURCE_FD=installer_fd
    sys.modules['install_source_closure']=install
    exec(compile(installer_raw,install.__file__,'exec'),install.__dict__)
    prelim,_,_=module('reviewed_controller_reader',PRELIM,PRELIM_SHA)
    completion,_,completion_raw=module('install_completion',HERE+'/install_completion.py',COMPLETION_SHA)
    sys.modules['direct_completion']=completion
    issuer,_,issuer_raw=module('install_issuer',HERE+'/install_issuer.py',ISSUER_SHA)
    phase,_,_=module('direct_phase0',HERE+'/phase0.py',PHASE_SHA)
    _,wait_raw=verified(HERE+'/WAIT-INSTALL-CODE.py',WAIT_SHA)
    _,closure_raw=verified(BASE+'/root-install-source-10/SOURCE-CLOSURE.json',CLOSURE_SHA)
    verified(HERE+'/DIRECT-MODEL.json','98ea72583a41f747f01c5bdb04b545319fc08cedf443366a6c2637a35562ed04')
    pins={'issuer_sha256':hashlib.sha256(issuer_raw).hexdigest(),'completion_sha256':hashlib.sha256(completion_raw).hexdigest(),'ipc_sha256':hashlib.sha256(ipc_raw).hexdigest()}
    completion.SOURCE_PINS=dict(pins)
    LOADED={'install':install,'issuer':issuer,'completion':completion,'prelim':prelim,'phase':phase,
            'wait_raw':wait_raw,'closure_raw':closure_raw,'pins':pins,'ipc':ipc}
    return completion


def run(channel_fd,root_parent_pid,root_parent_birth,admission_raw,admission_sha256,review_raw,review_sha256):
    """Called only inside the separately reviewed actual direct child."""
    load_for_parent()
    if type(channel_fd) is not int or channel_fd<0 or type(root_parent_pid) is not int or os.getppid()!=root_parent_pid:
        raise ValueError('actual inherited direct-parent channel required')
    if type(root_parent_birth) is not str or not root_parent_birth.isdigit():raise ValueError('parent birth required')
    if type(admission_raw) is not bytes or type(review_raw) is not bytes or len(admission_raw)>2097152 or len(review_raw)>2097152:
        raise ValueError('bounded reviewed bytes required')
    if hashlib.sha256(admission_raw).hexdigest()!=admission_sha256 or hashlib.sha256(review_raw).hexdigest()!=review_sha256:
        raise ValueError('actual approved bytes differ')
    install=LOADED['install'];request=json.loads(admission_raw,object_pairs_hook=install.unique)
    if request.get('owner_release',{}).get('review_sha256')!=review_sha256:raise ValueError('selected review mismatch')
    channel=socket.socket(fileno=channel_fd)
    return LOADED['phase'].run(request,install,LOADED['issuer'],LOADED['prelim'],LOADED['completion'],
                               LOADED['closure_raw'],LOADED['wait_raw'],review_raw,LOADED['pins'],
                               channel,root_parent_pid,root_parent_birth)
