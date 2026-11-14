"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Narrow real production guard and complete Docker inspect-shape fixtures.
No Docker, root, compiler, VM, network, or actual runtime parent creation.
"""
from pathlib import Path
import importlib.util, copy, json, os, platform, resource, sys
R=Path(__file__).resolve().parent/'source'
def load(name):
    spec=importlib.util.spec_from_file_location('host_boundary_fixture_'+name,R/(name+'.py'))
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value
o=load('native_diagnostic_container_owner');t=load('long_transport')
def profile(MODE):
    BOUND=t.file_limit(MODE)
    i=object.__new__(o.DiagnosticOwner);i.parent=Path(t.HOST_OUTPUT['parent']);i.name='fixture';i.container='d'*64;i.nonce='a'*32;i.label='mckernel.native-diagnostic.owner='+i.nonce;i.owner_sha='b'*64;i.manifest_path='/home/holden/mckernel-work/scratch/p-m06-native199-261022-1/manifest.json';i.manifest_sha256='c'*64;i.long_requested=MODE;i.long_release='/fixture/long-release.json';i.long_release_sha='e'*64
    argv=i._create_argv();assert ['--ulimit',('fsize=%d:%d'%(BOUND,BOUND))]==argv[argv.index(('fsize=%d:%d'%(BOUND,BOUND)))-1:argv.index(('fsize=%d:%d'%(BOUND,BOUND)))+1];assert '--pids-limit=512' in argv
    config=dict(Hostname=i.container[:12],Domainname='',User='1000:1000',Image=o.IMAGE,WorkingDir=str(i.parent),Entrypoint=['/usr/bin/python3'],Cmd=i._inside_args(),Labels={'mckernel.native-diagnostic.owner':i.nonce},Tty=False,OpenStdin=False,StdinOnce=False,AttachStdin=False,AttachStdout=True,AttachStderr=True,Env=['HOME=/tmp','TMPDIR=/tmp','PYTHONDONTWRITEBYTECODE=1'])
    h=dict(CgroupnsMode='host',NetworkMode='none',Privileged=False,ReadonlyRootfs=True,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],Memory=12884901888,MemorySwap=12884901888,NanoCpus=4000000000,CpusetCpus='2-5',PidsLimit=512,CgroupParent='/mckernel-dev',Init=True,PidMode='',UTSMode='',UsernsMode='',IpcMode='private',Runtime='runc',AutoRemove=False,PublishAllPorts=False,RestartPolicy={'Name':'no','MaximumRetryCount':0},Tmpfs={'/tmp':'rw,nodev,nosuid,size=256m'},ShmSize=67108864,OomScoreAdj=0,LogConfig=copy.deepcopy(t.DOCKER_LOG) if MODE else {'Type':'json-file','Config':{}},Ulimits=[dict(Hard=0,Name='core',Soft=0),dict(Hard=BOUND,Name='fsize',Soft=BOUND),dict(Hard=4096,Name='nofile',Soft=4096)],MaskedPaths=['/proc/kcore','/proc/keys','/proc/latency_stats','/proc/timer_list','/proc/scsi','/sys/firmware'],ReadonlyPaths=['/proc/bus','/proc/fs','/proc/irq','/proc/sys','/proc/sysrq-trigger'])
    pairs=[(x,x,True)for x in [o.REPO,o.SCRATCH]+o.EXTRA_READONLY]+[(str(i.parent),str(i.parent),False)]
    h['Mounts']=[dict(Type='bind',Source=x,Target=y,ReadOnly=ro)for x,y,ro in pairs]
    row=dict(Id=i.container,Name='/'+i.name,Image=o.IMAGE,Path='/usr/bin/python3',Args=i._inside_args(),Config=config,HostConfig=h,Mounts=[dict(Type='bind',Source=x,Destination=y,RW=not ro,Propagation='rprivate')for x,y,ro in pairs],NetworkSettings={'Networks':{'none':{}},'Ports':{}})
    i._profile(row,{'Config':{}});print('PASS actual _create_argv and complete production _profile mode-specific FSIZE positive')
    for label,change in [('missing',None),('wrong_soft',dict(Hard=BOUND,Name='fsize',Soft=BOUND-1)),('wrong_hard',dict(Hard=BOUND+1,Name='fsize',Soft=BOUND))]:
     x=copy.deepcopy(row);x['HostConfig']['Ulimits']=[v for v in x['HostConfig']['Ulimits']if v['Name']!='fsize']
     if change is not None:x['HostConfig']['Ulimits'].append(change)
     try:i._profile(x,{'Config':{}})
     except o.OwnerError as e:assert type(e)is o.OwnerError and str(e)=='ulimits';print('PASS exact fsize refusal',label)
     else:raise AssertionError(label)
    return i, row
    print('PASS4 affected file-growth profile checks; inherited host NPROC untouched')


def refuses(label, fn, error=(ValueError, OSError, o.OwnerError)):
    try:fn()
    except error:print('PASS refusal',label)
    else:raise AssertionError('accepted '+label)

def main():
    assert resource.getrlimit(resource.RLIMIT_NPROC)==(126258,126258)
    fixture=Path(sys.argv[1]);fixture.mkdir(mode=0o700)
    parent=fixture/'p';parent.mkdir(mode=0o700)
    assert parent.stat().st_dev==66306
    # Exercise the same descriptor guard with explicitly bound temporary paths;
    # the public production wrapper remains fixed to the uncreated runtime path.
    assert t._host_directory(parent,str(parent),66306,fresh=True)==(66306,parent.stat().st_ino)
    binding=dict(t.HOST_OUTPUT,parent=str(parent),retention_parent=str(fixture))
    assert t._host_output(parent,binding,fresh=True)==(66306,parent.stat().st_ino)
    # Inside only the bound p directory is visible; no retention ancestor access.
    inside=dict(binding,retention_parent=str(fixture/'unmounted-base'))
    assert t._host_output(parent,inside)==(66306,parent.stat().st_ino)
    refuses('outer missing retention base',lambda:t._host_output(parent,inside,fresh=True))
    print('PASS real descriptor-walk host device/uid/gid/mode/fresh layout and inner mounted-parent-only path')
    refuses('production root rejects fixture parent',lambda:t.output_parent(parent))
    refuses('foreign parent',lambda:t._host_directory(parent,str(fixture/'foreign'),66306))
    refuses('wrong root device',lambda:t._host_directory(parent,str(parent),1828))
    parent.chmod(0o755)
    refuses('nonprivate parent',lambda:t._host_directory(parent,str(parent),66306))
    parent.chmod(0o700)
    link=fixture/'link';link.symlink_to(parent,target_is_directory=True)
    refuses('symlink parent',lambda:t._host_directory(link,str(link),66306))
    (fixture/'foreign-owner').write_text('retained fixture')
    refuses('nonfresh retention base',lambda:t._host_output(parent,binding,fresh=True))
    (parent/'unexpected').write_text('retained fixture')
    refuses('nonfresh parent',lambda:t._host_directory(parent,str(parent),66306,fresh=True))
    refuses('writable manifest nested in output',lambda:o._manifest_outside_writable_parent(parent/'manifest.json',parent))
    refuses('input outside readonly scratch',lambda:t.readonly_input(parent/'unexpected',parent))
    t.validate_profile(copy.deepcopy(t.TRANSPORT));print('PASS exact typed v2 profile with HOST output binding')
    for label,key,value in [('wrong-root','device',1828),('foreign-root','parent',str(parent)),('bool-device','device',True)]:
        p=copy.deepcopy(t.TRANSPORT);p['host_output'][key]=value
        refuses(label,lambda p=p:t.validate_profile(p))
    p=copy.deepcopy(t.TRANSPORT);p['schema']='mckernel.p12.long-transport-profile.v1'
    refuses('obsolete profile',lambda:t.validate_profile(p))
    i,row=profile(True)
    argv=i._create_argv();mounts=[argv[n+1]for n,a in enumerate(argv)if a=='--mount']
    assert 'type=bind,src='+str(i.parent)+',dst='+str(i.parent) in mounts
    assert 'type=bind,src='+o.SCRATCH+',dst='+o.SCRATCH+',readonly' in mounts
    assert not any(t.HOST_OUTPUT['retention_parent']==v.split(',')[1][4:] for v in mounts)
    print('PASS real LONG create/inspect mount boundary; owner-retention base not mounted')
    for which in ('requested','actual'):
        x=copy.deepcopy(row)
        if which=='requested':
            m=next(m for m in x['HostConfig']['Mounts']if m['Source']==o.SCRATCH);m['ReadOnly']=False
        else:
            m=next(m for m in x['Mounts']if m['Source']==o.SCRATCH);m['RW']=True
        refuses(which+' writable scratch input',lambda x=x:i._profile(x,{'Config':{}}))
    for which in ('requested','actual'):
        x=copy.deepcopy(row)
        if which=='requested':x['HostConfig']['Mounts'].append(dict(Type='bind',Source='/foreign',Target='/foreign',ReadOnly=False))
        else:x['Mounts'].append(dict(Type='bind',Source='/foreign',Destination='/foreign',RW=True,Propagation='rprivate'))
        refuses(which+' extra writable root',lambda x=x:i._profile(x,{'Config':{}}))
    assert '--log-driver=json-file' in argv and '--log-opt=max-size=16m' in argv and '--log-opt=max-file=2' in argv
    for config in (None, {'Type':'json-file','Config':{}}, {'Type':'local','Config':{}},
                   {'Type':'json-file','Config':{'max-size':'16m'}},
                   {'Type':'json-file','Config':{'max-size':'16m','max-file':'3'}},
                   {'Type':'json-file','Config':{'max-size':'16m','max-file':'2','compress':'true'}}):
        x=copy.deepcopy(row);x['HostConfig']['LogConfig']=config
        refuses('missing/wrong/unbounded Docker logging '+repr(config),lambda x=x:i._profile(x,{'Config':{}}))
    print('PASS actual complete LONG create/inspect finite Docker log configuration')
    # Preserve accepted SHORT32MiB semantics and its original logging admission.
    short,shortrow=profile(False)
    assert not any(a.startswith('--log-')for a in short._create_argv())
    original=t.resource.getrlimit
    for longmode in (True,False):
        bound=t.file_limit(longmode)
        t.resource.getrlimit=lambda kind,bound=bound:(bound,bound)
        assert t.require_fsize(longmode)==bound
        for pair in ((-1,-1),(bound-1,bound),(bound,bound+1)):
            t.resource.getrlimit=lambda kind,pair=pair:pair
            refuses('actual inherited FSIZE '+repr(pair),lambda longmode=longmode:t.require_fsize(longmode))
    t.resource.getrlimit=original
    print('PASS actual shared FSIZE consumer positive and wrong/infinite limits; all four runtime layers preserved')
    admission=dict(host_floor_bytes=16*2**30,scratch_floor_bytes=12*2**30,
                   remaining_backing_growth_bytes=15850532864,emergency_bytes=640*2**20,
                   campaign_bytes=256*2**20,scratch_input_growth_bytes=32*2**20)
    required=t.growth_requirements(admission)
    assert t.TRANSPORT['logical_growth_bytes']==(7*384+512+32+96)*2**20
    assert required['host_required_bytes']==16*2**30+15850532864+t.TRANSPORT['logical_growth_bytes']+896*2**20
    assert t.require_growth(admission,required['host_required_bytes'],required['scratch_required_bytes'],15850532864)==required
    refuses('HOST growth one byte short',lambda:t.require_growth(admission,required['host_required_bytes']-1,required['scratch_required_bytes'],15850532864))
    refuses('scratch floor one byte short',lambda:t.require_growth(admission,required['host_required_bytes'],required['scratch_required_bytes']-1,15850532864))
    refuses('understated full sparse gap',lambda:t.require_growth(admission,required['host_required_bytes'],required['scratch_required_bytes'],15850532865))
    for key in admission:
        x=dict(admission);del x[key]
        refuses('missing growth '+key,lambda x=x:t.growth_requirements(x))
    for key,value in (('emergency_bytes',0),('campaign_bytes',0),('host_floor_bytes',16*2**30-1),
                      ('scratch_floor_bytes',12*2**30-1),('remaining_backing_growth_bytes',-1),
                      ('scratch_input_growth_bytes',True)):
        x=dict(admission);x[key]=value
        refuses('invalid growth '+key,lambda x=x:t.growth_requirements(x))
    print('PASS coupled complete HOST growth exact boundary and all missing/reserve/floor/sparse-gap refusals')
    from unittest.mock import patch
    class ReachedQemu(Exception):pass
    class GrowthRefused(Exception):pass
    preflight=object.__new__(o.DiagnosticOwner)
    preflight.parent=parent;preflight.attempt=parent/'not-created';preflight.manifest_path='/fixture-manifest'
    preflight.manifest_sha256='a'*64;preflight.long_requested=True;preflight.long_release='/fixture-release'
    preflight.long_release_sha='b'*64;preflight.nonce='c'*32
    longmanifest={'pair':{},'pair_long_session':copy.deepcopy(t.PROFILE)}
    class Diagnostic:
        def expected_qemu_argv(self,*args):raise ReachedQemu()
    for refused in (False,True):
        seen=[]
        def checked_growth(value,path):
            assert value==admission and path==parent
            seen.append('growth')
            if refused:raise GrowthRefused()
            return required
        with patch.object(o,'private_parent',return_value=(66306,parent.stat().st_ino)), \
             patch.object(o,'bound_manifest',return_value=(Diagnostic(),longmanifest)), \
             patch.object(o,'_long_transport',return_value=t), \
             patch.object(t,'require_fsize',return_value=t.file_limit(True)), \
             patch.object(t,'validate_release',return_value={'storage_admission':admission}), \
             patch.object(t,'live_growth',side_effect=checked_growth):
            try:preflight._preflight()
            except (GrowthRefused if refused else ReachedQemu):pass
            else:raise AssertionError('actual outer preflight did not enforce growth before QEMU admission')
        assert seen==['growth']
    print('PASS actual outer _preflight positive consumes release budget; refusal propagates before QEMU/lease/create')
    # Exercise real outer preflight call ordering with a fixed existing guard fixture;
    # no root, Docker, filesystem admission or actual runtime source publication.
    import ast
    tree=ast.parse((R/'native_diagnostic_container_owner.py').read_text())
    cls=next(v for v in tree.body if isinstance(v,ast.ClassDef)and v.name=='DiagnosticOwner')
    method=next(v for v in cls.body if isinstance(v,ast.FunctionDef)and v.name=='_preflight')
    calls=[v for v in ast.walk(method)if isinstance(v,ast.Call)and isinstance(v.func,ast.Attribute)and v.func.attr=='live_growth']
    assert len(calls)==1
    # This source binding check supplements actual production guard calls above.
    print('PASS outer preflight consumes reviewed release storage_admission before acquisition/create')
    d=load('native_diagnostic');planned=Path(t.HOST_OUTPUT['parent'])/('attempt-'+'a'*32)
    socket=d._qmp_socket_path(planned);assert len(os.fsencode(socket))<=107
    print('PASS actual planned QMP predicate',len(os.fsencode(socket)),str(socket))
    refuses('overlong QMP',lambda:d._qmp_socket_path(Path('/'+'x'*108)),(d.DiagnosticError,))
    assert not Path(t.HOST_OUTPUT['retention_parent']).exists()
    print('PASS no runtime base created; no native or P12 acceptance')
if __name__=='__main__':main()
