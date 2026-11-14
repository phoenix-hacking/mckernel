"""Finite actual-source code-readback tuple checks; Root executes after review.

The selected whole module runs under a non-main name. Only its OS file boundary
is controlled. Saved public metadata bytes/stats are copied, never installed
files. The first /var/lib open is a stop sentinel, not a physical readback PASS.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import types

HERE=Path(__file__).resolve().parent
INPUTS=json.loads((HERE/'INPUTS.json').read_text())
assert sys.version_info[:2]==(3,8)


def checked(row):
    raw=Path(row['path']).read_bytes()
    assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    return raw


def caught(call):
    try:call()
    except BaseException as error:return error
    raise AssertionError('declared refusal/boundary was not reached')


class InstalledBoundaryReached(Exception):pass


class MetadataFiles:
    """Finite copied-metadata filesystem. No real OS file-call fallback."""
    def __init__(self):
        self.files={}
        self.stats={}
        for row in INPUTS['metadata_files']:
            self.files[row['origin']]=checked(row)
            self.stats[row['origin']]=dict(row['origin_stat'])
        self.directories={'/'}
        for path in self.files:
            parent=Path(path).parent
            while str(parent) not in self.directories:
                self.directories.add(str(parent));parent=parent.parent
        self.dir_stats={path:dict(st_dev=991,st_ino=1000+index,st_uid=0,st_gid=0,
            st_mode=stat.S_IFDIR|0o755,st_nlink=1,st_size=0,st_mtime_ns=1,st_ctime_ns=1)
            for index,path in enumerate(sorted(self.directories))}
        self.fds={};self.next_fd=100;self.opens=[];self.closes=[];self.file_reads=[]
        self.namespace=[];self.handles=None
    def st(self,path):
        assert path in self.stats or path in self.dir_stats,'unbound virtual metadata path: '+path
        return types.SimpleNamespace(**(self.stats[path] if path in self.stats else self.dir_stats[path]))
    def resolve(self,path,dir_fd):
        assert type(path) is str
        if path.startswith('/'):
            assert dir_fd is None
            return path
        assert dir_fd in self.fds
        parent=self.fds[dir_fd]['path'];assert parent in self.directories
        return parent.rstrip('/')+'/'+path
    def open(self,path,flags,mode=0o777,dir_fd=None):
        full=self.resolve(path,dir_fd)
        assert not full.startswith('/var/lib/'),'installed access cannot fall through the boundary'
        assert full in self.files or full in self.directories,'no external filesystem fallback'
        assert flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)==0,'read-only lower effect only'
        if flags & os.O_DIRECTORY:assert full in self.directories
        fd=self.next_fd;self.next_fd+=1;self.fds[fd]=dict(path=full,offset=0)
        self.opens.append((fd,full));return fd
    def fstat(self,fd):
        assert fd in self.fds
        return self.st(self.fds[fd]['path'])
    def stat(self,path,dir_fd=None,follow_symlinks=False):
        assert follow_symlinks is False
        return self.st(self.resolve(path,dir_fd))
    def read(self,fd,count):
        assert fd in self.fds and 0<count<=65536
        row=self.fds[fd];path=row['path'];assert path in self.files
        if row['offset']==0:self.file_reads.append(path)
        raw=self.files[path];start=row['offset'];part=raw[start:start+count]
        row['offset']+=len(part);return part
    def close(self,fd):
        assert fd in self.fds,'no unowned close or numeric retry'
        assert self.handles is not None
        rows=[r for r in self.handles.records if r['historical_fd']==fd]
        assert len(rows)==1 and rows[0]['fd'] is None and rows[0]['state']=='CLOSING'
        self.closes.append(fd);del self.fds[fd]
    def os(self):
        effects=self
        class ControlledOS:
            def __getattr__(self,name):
                if name.startswith('O_'):return getattr(os,name)
                raise AssertionError('undeclared OS effect: '+name)
            def open(self,*args,**kwargs):return effects.open(*args,**kwargs)
            def fstat(self,fd):return effects.fstat(fd)
            def stat(self,*args,**kwargs):return effects.stat(*args,**kwargs)
            def read(self,*args):return effects.read(*args)
            def close(self,fd):return effects.close(fd)
        return ControlledOS()


def load():
    raw=checked(INPUTS['selected_source']);effects=MetadataFiles()
    ns=dict(__name__='controlled_exact_tuple_readback',__file__=INPUTS['selected_source']['origin'])
    exec(compile(raw,INPUTS['selected_source']['origin'],'exec'),ns)
    ns['os']=effects.os()
    ns['fcntl']=types.SimpleNamespace(ioctl=lambda *a:(_ for _ in ()).throw(AssertionError('no flags ioctl')))
    original=ns['open_exact']
    def bounded_open(path,handles,root_ancestors=False,directory=False):
        if path.startswith('/var/lib/'):
            assert path==INPUTS['expected_destination'] and root_ancestors is True and directory is True
            effects.namespace.append(dict(path=path,root_ancestors=root_ancestors,directory=directory))
            raise InstalledBoundaryReached('STOP_BEFORE_INSTALLED_NAMESPACE')
        return original(path,handles,root_ancestors=root_ancestors,directory=directory)
    ns['open_exact']=bounded_open
    handles=ns['Handles']();effects.handles=handles
    return ns,effects,handles


def close_all(handles,effects):
    assert handles.close()==[]
    assert effects.fds=={}
    assert all(r['state']=='VERIFIED_CLOSED' and r['fd'] is None for r in handles.records)
    previous=list(effects.closes);assert handles.close()==[] and effects.closes==previous


def root_record():return json.loads(checked(INPUTS['root_capsule']))


def helper_arguments(effects):
    paths=INPUTS['paths']
    actual=effects.files[paths['actual_values']]
    terminal_raw=effects.files[paths['caller_terminal']]
    return [root_record(),actual,INPUTS['nonce'],terminal_raw,json.loads(terminal_raw)]


def exact_tuple():
    # Inspect the actual new helper's narrow result without inventing resource
    # or native fields; then exercise the whole actual run_readback gate chain.
    ns,effects,handles=load();args=helper_arguments(effects)
    scoped=ns['exact_reconciled_caller'](*args,handles)
    assert scoped['historical_resource_observation']=='UNKNOWN_RETAINED'
    assert scoped['overall_resource_acceptance'] is False
    assert scoped['caller_terminal_raw_status']=='UNKNOWN_REQUIRES_ROOT_RECONCILIATION'
    assert scoped['caller_resource_unknown'] is True and scoped['observation_errors']==['ValueError']
    assert scoped['exact_historical_peak_or_exception_cause_proven'] is False
    assert scoped['independent_disposition']['sha256']==INPUTS['disposition_sha256']
    assert scoped['current_process_only_retirement']['sha256']==INPUTS['retirement_sha256']
    # These are the actual layers that carry nativefalse, not invented fields
    # added to the resource-audit helper's limited dictionary.
    disposition=json.loads(effects.files[INPUTS['paths']['disposition']])
    assert args[0]['native_release'] is False and args[0]['native_currentfree'] is None
    assert disposition['decision']['native_release'] is False and disposition['decision']['native_currentfree'] is None
    assert effects.namespace==[];close_all(handles,effects)
    ns,effects,handles=load()
    error=caught(lambda:ns['run_readback'](root_record(),handles))
    assert type(error) is InstalledBoundaryReached and str(error)=='STOP_BEFORE_INSTALLED_NAMESPACE'
    assert effects.namespace==[dict(path=INPUTS['expected_destination'],root_ancestors=True,directory=True)]
    assert set(effects.file_reads)==set(INPUTS['paths'].values())
    close_all(handles,effects)
    return dict(exact_nonce=INPUTS['nonce'],root_capsule_sha256=INPUTS['root_capsule']['sha256'],
        actual_FULL_sha256=INPUTS['full_sha256'],all_actual_metadata_gates=True,
        namespace_boundary_calls=1,installed_namespace_access=False,
        historical_resource_observation='UNKNOWN_RETAINED',overall_resource_acceptance=False,
        native_release=False,native_currentfree=None,original_unknown_unchanged=True)


def refused(identifier):
    ns,effects,handles=load();args=helper_arguments(effects)
    if identifier=='changed-nonce':
        args[2]='0'+args[2][1:]
        call=lambda:ns['exact_reconciled_caller'](*args,handles)
        diagnostic='UNKNOWN caller is not the exact reconciled current producer'
        entry='exact_reconciled_caller'
    elif identifier=='changed-caller':
        args[3]+=b' '
        call=lambda:ns['exact_reconciled_caller'](*args,handles)
        diagnostic='UNKNOWN caller is not the exact reconciled current producer'
        entry='exact_reconciled_caller'
    elif identifier=='unbound-UNKNOWN':
        root=args[0];root['caller_resource_observation']='UNBOUND_UNKNOWN'
        call=lambda:ns['run_readback'](root,handles)
        diagnostic='UNKNOWN caller is not the exact reconciled current producer'
        entry='run_readback'
    elif identifier=='changed-FULL':
        path=INPUTS['paths']['stdout'];lines=effects.files[path].splitlines(keepends=True)
        effects.files[path]=lines[0][:-1]+b' \n'+lines[1]
        effects.stats[path]['st_size']=len(effects.files[path])
        call=lambda:ns['run_readback'](args[0],handles)
        diagnostic='exact actual closed caller capture differs';entry='run_readback'
    elif identifier=='bad-tool-wait':
        root=args[0];root['tool_calls'][-1]['result']['exit_code']=1
        call=lambda:ns['run_readback'](root,handles)
        diagnostic='Root actual tool terminal is nonzero or still has a session';entry='run_readback'
    elif identifier in ('bad-keeper-wait','bad-lease'):
        # Whole unchanged check_data is the real owner of these strict guards.
        # Full run_readback would reject edited capture bytes even earlier.
        path=INPUTS['paths']['stdout'];full,final=[json.loads(x) for x in effects.files[path].splitlines()]
        if identifier=='bad-keeper-wait':
            full['result']['terminal_evidence']['keeper']['direct_wait_status']=1
            diagnostic='actual keeper/installer waits absent'
        else:
            final['lease_disposition']='UNKNOWN'
            diagnostic='actual producer/lease disposition incomplete'
        full_raw=ns['canon'](full);final['full_sha256']=hashlib.sha256(full_raw).hexdigest()
        stdout=full_raw+ns['canon'](final)
        request=json.loads(effects.files[INPUTS['paths']['request']])
        reservation=json.loads(effects.files[INPUTS['paths']['reservation']])
        terminal=copy.deepcopy(args[4]);terminal['caller_pid']=reservation['driver']['pid']
        call=lambda:ns['check_data'](stdout,terminal,request,reservation,effects.st(path))
        entry='check_data'
    else:raise AssertionError('unbound finite control')
    error=caught(call)
    assert type(error) is ValueError and str(error)==diagnostic
    assert effects.namespace==[], 'refusal must precede installed namespace boundary'
    close_all(handles,effects)
    return dict(id=identifier,actual_entrypoint=entry,diagnostic=diagnostic,namespace_boundary_calls=0)


def main():
    assert sys.argv[1:]==['exact-producer-tuple']
    result=dict(actual_tuple=exact_tuple(),rejections=[refused(name) for name in (
        'changed-nonce','changed-caller','changed-FULL','bad-tool-wait',
        'bad-keeper-wait','bad-lease','unbound-UNKNOWN')],
        real_FD_or_installed_access=False,issuer_Root_account_native_action=False,
        prior_FD_primary_AS_proofs_reused=True)
    expected=json.loads(checked(INPUTS['expected']))
    assert result==expected['result']
    print(json.dumps(dict(family='exact-producer-readback-boundary',status='PASS',result=result),sort_keys=True,separators=(',',':')))


if __name__=='__main__':main()
