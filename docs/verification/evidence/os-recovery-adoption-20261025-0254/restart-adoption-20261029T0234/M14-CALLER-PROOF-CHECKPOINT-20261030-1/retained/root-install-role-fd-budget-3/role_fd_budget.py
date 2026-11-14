"""Functional M14 role FD exercise. Source only until separately admitted.

Uses selected immutable-source functions on ordinary temporary fixture files.
No fork, root, signals, pidfd, real installer write or cleanup is performed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import resource
import signal
import stat
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1')
CHILD=BASE/'root-install-direct-child-successor-4'
ENTRY_SHA='7ac4718a01be185cc1d816bf5c91e84960b73ca51209d7c3b909cda354ccfcea'
BOUND_SHA='5cc545b852a95ff9504baac5a97a6936c0647127691908fd88ac52934ea256b8'
CLOSURE_SHA='81be55d5bf48ff462d291683ef1a26238b27581026bc5ffacc488125b6667ba6'
PARENT3_SHA='e1ccd682987ee66ed4bf98648b86877edefbd6fceb6f342caa274d6762821f27'
NONCE='a'*64
RELEASE='b'*64
MAX_BYTES=2*1024*1024
ACTIVE={}


def sha(data):return hashlib.sha256(data).hexdigest()


def bound(path,digest):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd);chunks=[];total=0
        while total<=MAX_BYTES:
            part=os.read(fd,min(65536,MAX_BYTES+1-total))
            if not part:break
            chunks.append(part);total+=len(part)
        after=os.fstat(fd);raw=b''.join(chunks)
        if (total>MAX_BYTES or len(raw)!=before.st_size or
            (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or sha(raw)!=digest):
            raise ValueError('fixed source bytes changed: '+str(path))
        return raw
    finally:os.close(fd)


def identity(st):return {'device':st.st_dev,'inode':st.st_ino}


def actual_count():
    # listdir transiently owns one directory descriptor; report separately.
    return len(os.listdir('/proc/self/fd'))-1


class Observer:
    def __init__(self):
        self.real_open=os.open;self.real_close=os.close
        self.start=actual_count();self.peak=self.start;self.events=[];self.close_unknown=[];self.pending_open=[]
    def sample(self,kind,fd):
        count=actual_count();self.peak=max(self.peak,count);self.events.append((kind,fd,count))
    def open(self,path,flags,mode=0o777,*,dir_fd=None):
        fd=self.real_open(path,flags,mode,dir_fd=dir_fd)
        self.pending_open.append(fd)
        self.sample('open',fd)
        self.pending_open.remove(fd);return fd
    def close(self,fd):
        try:self.real_close(fd)
        except BaseException:
            self.close_unknown.append(fd);raise
        self.sample('close',fd)


class StatProxy:
    # Test-only ownership/ancestor permissions; all other metadata is real.
    def __init__(self,real,operation_root):self.real=real;self.operation_root=operation_root
    def __getattr__(self,name):
        if name=='st_uid':return 0
        if name=='st_mode' and stat.S_ISDIR(self.real.st_mode):
            if (self.real.st_dev,self.real.st_ino)==self.operation_root:return self.real.st_mode
            return (self.real.st_mode & ~0o022) | 0o001
        return getattr(self.real,name)


def ancestors(path):
    path=Path(path)
    if not path.is_absolute():raise ValueError('absolute fixture path required')
    seq=[Path('/')];current=Path('/')
    for part in path.parts[1:]:current=current/part;seq.append(current)
    return [identity(os.stat(str(item))) for item in seq]


def stage(parent,closure):
    # Exclusive temporary fixture; intentionally retained, never cleaned here.
    work=Path(tempfile.mkdtemp(prefix='m14-fd-budget-',dir=parent))
    root=work/'root';code=work/'code';root.mkdir(mode=0o700);code.mkdir(mode=0o755)
    out=code/('installed-source-'+NONCE);out.mkdir(mode=0o755);(out/'parser').mkdir(mode=0o755)
    root.chmod(0o700);code.chmod(0o755);out.chmod(0o755);(out/'parser').chmod(0o755)
    (work/'lease').write_bytes(b'')
    source=Path(closure['source_directory']);rows=[]
    for row in closure['files']:
        raw=(source/row['name']).read_bytes()
        if len(raw)!=row['size'] or sha(raw)!=row['sha256']:raise ValueError('fixture source differs')
        target=out/row['name'];target.write_bytes(raw);target.chmod(0o444)
        rows.append((row,identity(target.stat())))
    out_id=identity(out.stat());parser_id=identity((out/'parser').stat())
    records=[{'state':'CLAIMED','nonce':NONCE,'release_sha256':RELEASE,'closure_sha256':CLOSURE_SHA},
             {'state':'DIRECTORY_CREATED','name':'parser','identity':parser_id},
             {'state':'BEFORE_DIRECTORY_IMMUTABLE','name':'root','identity':out_id},
             {'state':'BEFORE_DIRECTORY_IMMUTABLE','name':'parser','identity':parser_id}]
    for row,ident in rows:
        for state in ('BEFORE_CREATE','BEFORE_WRITER_CLOSE','WRITER_CLOSED','BEFORE_IMMUTABLE','FILE_HELD'):
            event={'state':state,'name':row['name']}
            if state in ('BEFORE_CREATE','FILE_HELD'):event['sha256']=row['sha256']
            if state!='BEFORE_CREATE':event['identity']=ident
            records.append(event)
    records.append({'state':'SOURCE_INSTALLED','nonce':NONCE,'closure_sha256':CLOSURE_SHA,'identity':out_id})
    journal=root/('INSTALL-'+NONCE+'.jsonl')
    journal.write_bytes(b''.join((json.dumps(x,sort_keys=True,separators=(',',':'))+'\n').encode() for x in records));journal.chmod(0o600)
    return work,root,code,source,out


def load_entry():
    raw=bound(CHILD/'direct_entry.py',ENTRY_SHA)
    bound(CHILD/'SOURCE-BOUND.json',BOUND_SHA)
    bound(BASE/'root-install-parent-successor-3'/'FROZEN-SOURCE.json',PARENT3_SHA)
    spec=importlib.util.spec_from_file_location('budget_direct_entry',str(CHILD/'direct_entry.py'))
    entry=importlib.util.module_from_spec(spec)
    exec(compile(raw,str(CHILD/'direct_entry.py'),'exec'),entry.__dict__)
    entry.load_for_parent()
    return entry


def cap_template():
    return {'deadline_boot_ns':time.clock_gettime_ns(time.CLOCK_BOOTTIME)+120000000000,
            'deadline_mono_ns':time.monotonic_ns()+120000000000,'utc_cap_ns':time.time_ns()+120000000000}


def walk_three(install,root,code,source,repeats):
    # Same three open_exact paths as the parent context; caller counts real FDs.
    for _ in range(repeats):
        install.open_exact(str(root),ancestors(root),True)
        install.open_exact(str(code),ancestors(code),True,True)
        install.open_exact(str(source),ancestors(source))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--role',choices=('parent','keeper','installer'),required=True)
    parser.add_argument('--fixture-parent',required=True);args=parser.parse_args()
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    if soft not in (128,256) or hard not in (128,256) or soft>hard:raise ValueError('existing 128/256 FD profile required')
    if os.sched_getaffinity(0)!={6}:raise ValueError('existing CPU6 affinity required')
    if os.getuid()==0 or os.geteuid()==0:raise ValueError('unprivileged exercise only')
    closure_raw=bound(BASE/'root-install-source-10'/'SOURCE-CLOSURE.json',CLOSURE_SHA)
    closure=json.loads(closure_raw);work,root,code,source,out=stage(args.fixture_parent,closure)
    # Baseline includes already-open stdin/out/err, fixture setup and caller FDs.
    actual_root_stat=os.stat(str(root));actual_root_identity=(actual_root_stat.st_dev,actual_root_stat.st_ino)
    baseline=actual_count();observer=Observer();normal_fstat=os.fstat
    ACTIVE.update(observer=observer,role=args.role,baseline=baseline,fixture=str(work),nofile_soft=soft,nofile_hard=hard)
    masks=mock.patch.object(signal,'pthread_sigmask',return_value=set())
    with masks, mock.patch.object(os,'open',side_effect=observer.open), mock.patch.object(os,'close',side_effect=observer.close):
        entry=load_entry();install=entry.LOADED['install'];completion=entry.LOADED['completion'];phase=entry.LOADED['phase']
        loader_count=actual_count();assert len([fd for fd in entry.HELD if fd is not None])==14
        root_fd=os.open(str(root),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        code_fd=os.open(str(code),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        source_fd=os.open(str(source),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
        closure_fd=os.open(str(BASE/'root-install-source-10'/'SOURCE-CLOSURE.json'),os.O_RDONLY|os.O_CLOEXEC)
        # Only the UID and controlled-directory mode/immutable checks are mocked.
        with mock.patch.object(os,'fstat',side_effect=lambda fd:StatProxy(normal_fstat(fd),actual_root_identity)), \
             mock.patch.object(install,'flags',return_value=install.IMMUTABLE):
            if args.role=='parent':
                walk_three(install,root,code,source,2)
                proof_held=[]
                proof=completion.install_proof(install,root_fd,code_fd,closure_fd,NONCE,RELEASE,cap_template(),proof_held)
                if len(proof['files'])!=23:raise ValueError('parent proof incomplete')
                case={'open_exact_repetitions':2,'proof_files_hashed':len(proof['files']),'proof_held':len(proof_held)}
            elif args.role=='keeper':
                phase.verify_source(install,source_fd,closure_raw)
                walk_three(install,root,code,source,1)
                proof_held=[]
                proof=completion.install_proof(install,root_fd,code_fd,closure_fd,NONCE,RELEASE,cap_template(),proof_held)
                if len(proof['files'])!=23:raise ValueError('keeper proof incomplete')
                case={'source_leaves_verified':23,'open_exact_repetitions':1,'proof_files_hashed':len(proof['files']),'proof_held':len(proof_held)}
            else:
                # Execute the real installer until its first journal create.
                # No production write, mount, freeze or controller action occurs.
                class BeforeMutation(Exception):pass
                open_observed=observer.open
                def readonly_open(path,flags,mode=0o777,*,dir_fd=None):
                    if flags&(os.O_CREAT|os.O_WRONLY|os.O_RDWR|os.O_TRUNC):raise BeforeMutation('first installer mutation')
                    return open_observed(path,flags,mode,dir_fd=dir_fd)
                release={'operation_path':str(root),'operation_ancestors':ancestors(root),'code_path':str(code),
                  'code_ancestors':ancestors(code),'source_ancestors':ancestors(source),
                  'operation_root':identity(os.stat(str(root))),'code_parent':identity(os.stat(str(code))),
                  'source_dir':identity(os.stat(str(source))),'lease':identity(os.fstat(root_fd)),
                  'installer_sha256':install._BOOTSTRAP_INSTALLER_HASH,'interpreter':{},'nonce':NONCE,
                  'controls_sha256':sha(b''),'capacity_sha256':sha(b''),'host_install_custody_sha256':sha(b''),'owner_release_sha256':sha(b'')}
                # A normal local regular file models the already-held lease inode.
                lease_path=work/'lease';lease_fd=os.open(str(lease_path),os.O_RDONLY|os.O_CLOEXEC)
                release['lease']=identity(os.fstat(lease_fd))
                empty_fd=os.open(str(lease_path),os.O_RDONLY|os.O_CLOEXEC)
                with mock.patch.object(os,'getuid',return_value=0),mock.patch.object(os,'geteuid',return_value=0), \
                     mock.patch.object(os,'open',side_effect=readonly_open), \
                     mock.patch.object(install,'verify_release',return_value=release), \
                     mock.patch.object(install,'verify_base_runtime'),mock.patch.object(install,'verify_host_receipt'), \
                     mock.patch.object(install,'root_file'),mock.patch.object(install,'clock_check'):
                    try:install.install(empty_fd,RELEASE,source_fd,root_fd,code_fd,lease_fd,closure_fd,empty_fd,empty_fd,empty_fd,empty_fd)
                    except BeforeMutation:pass
                    else:raise ValueError('installer did not stop before mutation')
                # Match the actual installer's retained descriptors to every
                # source inode and independently reread/hash all 23 leaves.
                held_by_inode={}
                for fd in install._HELD:
                    if type(fd) is int:
                        st=os.fstat(fd);held_by_inode[(st.st_dev,st.st_ino)]=fd
                for row in closure['files']:
                    st=os.stat(str(source/row['name']))
                    fd=held_by_inode.get((st.st_dev,st.st_ino))
                    if fd is None:raise ValueError('missing retained source leaf '+row['name'])
                    raw=install.read_stable(fd,install.MAX_SOURCE)
                    if len(raw)!=row['size'] or sha(raw)!=row['sha256']:raise ValueError('retained source bytes differ')
                case={'source_leaves_verified':23,'stopped_before_first_journal_create':True,'install_held':len(install._HELD)}
        end=actual_count()
        result={'scope':'MOCKED_ROLE_FD_EXERCISE_NOT_PRODUCTION_PEAK','role':args.role,'nofile_soft':soft,'nofile_hard':hard,
          'cpu_affinity':[6],'preoccupied_fds':baseline,'loader_delta':loader_count-baseline,'exit_live_fds':end,
          'peak_live_fds':observer.peak,'peak_including_observer_fd':observer.peak+1,'observer_temporary_fds':1,
          'events_recorded':len(observer.events),'close_unknown':observer.close_unknown,'fixture':str(work),
          'case':case,'source_closure_sha256':CLOSURE_SHA,'entry_sha256':ENTRY_SHA,'native_release':False,
          'native_currentfree':None,'full_operation_fd_peak':'UNKNOWN'}
        if observer.close_unknown:raise ValueError('uncertain FD close; no retry')
        print(json.dumps(result,sort_keys=True,separators=(',',':')))


if __name__=='__main__':
    try:main()
    except Exception as error:
        observer=ACTIVE.get('observer')
        failure={'scope':'MOCKED_ROLE_FD_EXERCISE_NOT_PRODUCTION_PEAK','status':'FAILED_UNKNOWN',
                 'role':ACTIVE.get('role'),'fixture':ACTIVE.get('fixture'),'preoccupied_fds':ACTIVE.get('baseline'),
                 'nofile_soft':ACTIVE.get('nofile_soft'),'nofile_hard':ACTIVE.get('nofile_hard'),
                 'peak_live_fds_before_failure':None if observer is None else observer.peak,
                 'observer_temporary_fds':1,'close_unknown':[] if observer is None else observer.close_unknown,
                 'pending_open_fds':[] if observer is None else observer.pending_open,
                 'error_type':type(error).__name__,'error':str(error),
                 'native_release':False,'native_currentfree':None,'full_operation_fd_peak':'UNKNOWN'}
        print(json.dumps(failure,sort_keys=True,separators=(',',':')),file=sys.stderr)
        raise
