from pathlib import Path
import importlib.util,json,os,resource,time,signal,hashlib,sys
R=Path(__file__).resolve().parent;O=R/'actual-nm-source-probe-capture-1';O.mkdir(mode=0o700)
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py');s=importlib.util.spec_from_file_location('accepted_owned_capture',S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for number in m.STOP_SIGNALS:signal.signal(number,m.stop)
assert os.sched_getaffinity(0)=={6} and resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
p=R/'check_actual_nm_and_source_projection.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='2f4add1c416045f96e32b660db32f298952078b9e8e4a31094420d2afe3fb15b' and p.stat().st_size==5884
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());assert state['phase']=='running' and not state.get('pause_reason') and not state.get('stop_reason') and state['last_rate_limits']['primary']['usedPercent']<100
measured=[]
for root,floor,growth in [('/home/holden/mckernel-work',16<<30,1135842996),('/home/holden/mckernel-work/scratch',12<<30,64<<20)]:
 v=os.statvfs(root);free=v.f_bavail*v.f_frsize;assert free>=floor+growth;measured.append({'path':root,'free_bytes':free,'floor':floor,'growth':growth})
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;assert mem>=5<<30
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
import subprocess
scratch=Path('/home/holden/mckernel-work/scratch');mount=json.loads(subprocess.check_output(['/usr/bin/findmnt','-J','-o','SOURCE,TARGET,UUID,MAJ:MIN','-T',str(scratch)],text=True,timeout=10))['filesystems'][0];dev=scratch.stat().st_dev;assert mount['uuid']=='2a5768c8-718d-4914-bdc0-6b32c5a92a52' and mount['target']==str(scratch) and mount['maj:min']=='%d:%d'%(os.major(dev),os.minor(dev))
assert hashlib.sha256((R/'native_rust_exact_mckernel_image_offline.py').read_bytes()).hexdigest()=='319790fd648ea82c7ef3adc129cc9cc329c08ea23beed105fdfeeb6770f09d9a'
command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(p)]};m.write(O/'initial-command-and-admission.json',{'command':command,'profile':{'cpu':6,'jobs':1,'as':1<<30,'cpu_seconds':30,'wall_seconds':35,'kill_after':2,'fsize':32<<20,'core':0,'nofile':256},'measured_storage':measured,'measured_mem_available':mem,'phase':state['phase'],'pause_reason':state.get('pause_reason'),'used_percent':state['last_rate_limits']['primary']['usedPercent'],'uid':os.getuid(),'affinity':sorted(os.sched_getaffinity(0)),'interpreter':sys.executable})
def limits():
 for kind,val in [(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_AS,1<<30)]:resource.setrlimit(kind,(val,val))
begin=time.monotonic();rec=m.owned_capture(command,O,35,limits);m.write(O/'whole.json',{'record':rec,'elapsed_seconds':time.monotonic()-begin,'scope':'actual driver AST/helper/pure source crossrefs and saved failed-object nm metadata only; noowner.run/livevalidate/Docker/lock/compiler/sourcecopy'});ok=rec['returncode']==0 and rec['direct_child_joined'] and rec['group_absent'] and rec['error'] is None and rec['retirement_error'] is None;print(json.dumps({'returncode':rec['returncode'],'seconds':time.monotonic()-begin,'direct_joined':rec['direct_child_joined'],'group_absent':rec['group_absent'],'closed_streams':rec['closed_streams'],'error':rec['error'],'retirement_error':rec['retirement_error']}));raise SystemExit(0 if ok else 1)
