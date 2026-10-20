"""Exact two ordinary source commands; parent conditional grant, no compiler."""
from pathlib import Path
import importlib.util,json,os,resource,time,signal,hashlib,sys,subprocess,datetime
R=Path(__file__).resolve().parent;N=R.parent;O=R/'source-materialization-capture-1'
planpath=N/'FRESH-FULL-PRODUCTION-RUST-NM-LINK-PROPOSAL.json'
assert hashlib.sha256(planpath.read_bytes()).hexdigest()=='25ae92015b668a060333929b8d24d328030b7d6e012f59716ba77ac1cfbd7232'
plan=json.loads(planpath.read_text());commands=plan['source_commands'];assert len(commands)==2
review=Path('/home/holden/mckernel-work/host-preparation/phase5-panic-free-full-image-driver-independent-review-20261020-1/EXACT-FOUR-DELTA-TWO-SOURCE-COMMAND-PRECHECK.json')
assert hashlib.sha256(review.read_bytes()).hexdigest()=='319e53d5ef3c4e9a04fd49e03ddf858fa1be7fabfb20b2f20484c54172361630'
assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
assert resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30)
assert sys.version_info[:3]==(3,9,12) and sys.executable=='/home/holden/anaconda3/bin/python3'
assert Path('/').is_relative_to(Path('/')) and not Path('/outside').is_relative_to(Path('/inside'))
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());assert state['phase']=='running' and not state.get('pause_reason') and not state.get('stop_reason') and state['last_rate_limits']['primary']['usedPercent']<100
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
scratch=Path('/home/holden/mckernel-work/scratch');argv=['/usr/bin/findmnt','-J','-o','SOURCE,TARGET,UUID,MAJ:MIN','-T',str(scratch)]
c=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10,check=True)
mount=json.loads(c.stdout)['filesystems'][0];dev=scratch.stat().st_dev
assert mount['target']==str(scratch) and mount['uuid']=='2a5768c8-718d-4914-bdc0-6b32c5a92a52' and mount['maj:min']=='%d:%d'%(os.major(dev),os.minor(dev)) and not c.stderr
breakdown={'copied_source_bytes':120821428,'source_bound_request_cap_bytes':33554432,'unchanged_capture_and_control_reserve_bytes':536870912,'emergency_reserve_bytes':67108864,'retained_old_image_postbuild_reserve_bytes':377487360};hostgrowth=sum(breakdown.values());assert hostgrowth==1135842996
measured=[]
for root,floor,growth in [('/home/holden',16<<30,hostgrowth),(str(scratch),12<<30,64<<20)]:
 v=os.statvfs(root);free=v.f_bavail*v.f_frsize;assert free>=floor+growth;measured.append({'path':root,'device':Path(root).stat().st_dev,'free_bytes':free,'floor_bytes':floor,'full_growth_bytes':growth,'required_bytes':floor+growth})
assert N.stat().st_dev==Path('/home/holden').stat().st_dev and N.stat().st_dev!=dev
mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024;assert mem>=5<<30
for command in commands:
 p=Path(command['argv'][-1]);assert command['argv'][:3]==['/home/holden/anaconda3/bin/python3','-I','-B'];assert hashlib.sha256(p.read_bytes()).hexdigest()==command['callable']['sha256'] and p.stat().st_size==command['callable']['bytes']
assert not (R/'materialized-source').exists() and not (R/'materialization-receipt.json').exists() and not (R/'image-request-SOURCE-BOUND-PROPOSAL.json').exists()
S=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py');s=importlib.util.spec_from_file_location('accepted_owned_capture',S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for number in m.STOP_SIGNALS:signal.signal(number,m.stop)
O.mkdir(mode=0o700)
m.write(O/'initial-command-and-admission.json',{'commands':commands,'parent_conditional_authorization':'Root granted exact25ae two source commands once after319e independent source precheck and explicit M03 CPU6 release; no compiler/root/Docker grant','review':{'path':str(review),'sha256':'319e53d5ef3c4e9a04fd49e03ddf858fa1be7fabfb20b2f20484c54172361630','bytes':review.stat().st_size},'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'boot_id':boot,'mount':mount,'findmnt':{'argv':argv,'returncode':c.returncode,'direct_child_joined':True,'stderr':c.stderr},'source_growth_breakdown':breakdown,'measured_storage':measured,'measured_mem_available':mem,'minimum_mem_available':5<<30,'used_percent':state['last_rate_limits']['primary']['usedPercent'],'phase':state['phase'],'pause_reason':state.get('pause_reason'),'stop_reason':state.get('stop_reason'),'actual_affinity':sorted(os.sched_getaffinity(0)),'uid':os.getuid(),'interpreter':sys.executable,'preserved_old_failed_image':str(N.parent/'gitlink-nine-copy-observer-correction-1/full-image-attempt-1')})
def limits():
 for kind,val in [(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_CORE,0),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_AS,1<<30)]:resource.setrlimit(kind,(val,val))
records=[];begin=time.monotonic()
for index,command in enumerate(commands,1):
 out=O/('command-'+str(index));out.mkdir(mode=0o700)
 row=m.owned_capture(command,out,35,limits);records.append(row);m.write(out/'closed-record.json',row)
 if row['returncode']!=0 or not row['direct_child_joined'] or not row['group_absent'] or not row['closed_streams'] or row['error'] is not None or row['retirement_error'] is not None:break
ok=len(records)==2 and all(row['returncode']==0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and row['error'] is None and row['retirement_error'] is None for row in records)
m.write(O/'whole.json',{'status':'PASS' if ok else 'FAIL','records':records,'elapsed_seconds':time.monotonic()-begin,'scope':'actual source materialization then identity proposal binding only; no compiler/root/ownership/Docker','CPU6_released_after_wholejoin':True})
print(json.dumps({'status':'PASS' if ok else 'FAIL','returncodes':[row['returncode'] for row in records],'elapsed_seconds':time.monotonic()-begin,'all_direct_joined':all(row['direct_child_joined'] for row in records),'all_groups_absent':all(row['group_absent'] for row in records),'closed_streams':all(row['closed_streams'] for row in records)}));raise SystemExit(0 if ok else 1)
