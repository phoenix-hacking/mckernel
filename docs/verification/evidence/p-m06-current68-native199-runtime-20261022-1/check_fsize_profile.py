from pathlib import Path
import importlib.util,copy,json
R=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('owner',R/'native_diagnostic_container_owner.py');o=importlib.util.module_from_spec(s);s.loader.exec_module(o)
i=object.__new__(o.DiagnosticOwner);i.parent=Path('/home/holden/mckernel-work/scratch/p-m06-native199-261022-1/owner-parent');i.name='fixture';i.container='d'*64;i.nonce='a'*32;i.label='mckernel.native-diagnostic.owner='+i.nonce;i.owner_sha='b'*64;i.manifest_path='/home/holden/mckernel-work/scratch/p-m06-native199-261022-1/manifest.json';i.manifest_sha256='c'*64
argv=i._create_argv();assert ['--ulimit','fsize=33554432:33554432']==argv[argv.index('fsize=33554432:33554432')-1:argv.index('fsize=33554432:33554432')+1];assert '--pids-limit=512' in argv
config=dict(Hostname=i.container[:12],Domainname='',User='1000:1000',Image=o.IMAGE,WorkingDir=str(i.parent),Entrypoint=['/usr/bin/python3'],Cmd=i._inside_args(),Labels={'mckernel.native-diagnostic.owner':i.nonce},Tty=False,OpenStdin=False,StdinOnce=False,AttachStdin=False,AttachStdout=True,AttachStderr=True,Env=['HOME=/tmp','TMPDIR=/tmp','PYTHONDONTWRITEBYTECODE=1'])
h=dict(NetworkMode='none',Privileged=False,ReadonlyRootfs=True,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],Memory=12884901888,MemorySwap=12884901888,NanoCpus=4000000000,CpusetCpus='2-5',PidsLimit=512,CgroupParent='/mckernel-dev',Init=True,PidMode='',UTSMode='',UsernsMode='',IpcMode='private',Runtime='runc',AutoRemove=False,PublishAllPorts=False,RestartPolicy={'Name':'no','MaximumRetryCount':0},Tmpfs={'/tmp':'rw,nodev,nosuid,size=256m'},ShmSize=67108864,OomScoreAdj=0,LogConfig={'Type':'json-file','Config':{}},Ulimits=[dict(Hard=0,Name='core',Soft=0),dict(Hard=33554432,Name='fsize',Soft=33554432),dict(Hard=4096,Name='nofile',Soft=4096)],MaskedPaths=['/proc/kcore','/proc/keys','/proc/latency_stats','/proc/timer_list','/proc/scsi','/sys/firmware'],ReadonlyPaths=['/proc/bus','/proc/fs','/proc/irq','/proc/sys','/proc/sysrq-trigger'])
pairs=[(x,x,True)for x in [o.REPO,o.SCRATCH]+o.EXTRA_READONLY]+[(str(i.parent),str(i.parent),False)]
h['Mounts']=[dict(Type='bind',Source=x,Target=y,ReadOnly=ro)for x,y,ro in pairs]
row=dict(Id=i.container,Name='/'+i.name,Image=o.IMAGE,Path='/usr/bin/python3',Args=i._inside_args(),Config=config,HostConfig=h,Mounts=[dict(Type='bind',Source=x,Destination=y,RW=not ro,Propagation='rprivate')for x,y,ro in pairs],NetworkSettings={'Networks':{'none':{}},'Ports':{}})
i._profile(row,{'Config':{}});print('PASS actual _create_argv and complete production _profile fsize32MiB positive')
for label,change in [('missing',None),('wrong_soft',dict(Hard=33554432,Name='fsize',Soft=33554431)),('wrong_hard',dict(Hard=33554433,Name='fsize',Soft=33554432))]:
 x=copy.deepcopy(row);x['HostConfig']['Ulimits']=[v for v in x['HostConfig']['Ulimits']if v['Name']!='fsize']
 if change is not None:x['HostConfig']['Ulimits'].append(change)
 try:i._profile(x,{'Config':{}})
 except o.OwnerError as e:assert type(e)is o.OwnerError and str(e)=='ulimits';print('PASS exact fsize refusal',label)
 else:raise AssertionError(label)
print('PASS4 affected file-growth profile checks; inherited host NPROC untouched')
