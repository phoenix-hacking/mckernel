"""Case-specific joins over the immutable accepted root snapshot engine."""
import ast,hashlib,importlib.util,json,os,stat
from pathlib import Path
HERE=Path(__file__).resolve().parent
DATA=Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-native-snapshot-20261019-1/two-complete-cycle205-case-1')
ENGINE=Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-three-rounds-20261020-1/stage-preparation-1/root_manual_snapshot_three_round_native_db3.py')
ENGINE_SHA='eb04ed99b447bb5c0c159085dcee36e342123edba9b79a463b8991ee311e0dff'
raw=ENGINE.read_bytes()
if hashlib.sha256(raw).hexdigest()!=ENGINE_SHA:raise ValueError('pinned accepted snapshot engine')
spec=importlib.util.spec_from_file_location('accepted205_snapshot_engine',ENGINE);base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
base.N=HERE;base.OUTPUT=DATA/'root-live-preflight-1.json'
need=base.need
def checked3(r):
 need(set(r)=={'path','sha256','bytes'},'whole exact ref3')
 p=Path(r['path']);need(p.is_absolute() and p.resolve(strict=True)==p and not p.is_symlink(),'canonical report')
 data=p.read_bytes();need(len(data)==r['bytes']<=4<<20 and hashlib.sha256(data).hexdigest()==r['sha256'],'whole report bytes/hash')
 return json.loads(data)
def full(p):
 p=Path(p);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_size<=4<<20,'bounded current source');h=hashlib.sha256();n=0
  while True:
   block=os.read(fd,65536)
   if not block:break
   h.update(block);n+=len(block)
  z=os.fstat(fd);q=p.lstat();fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_size','st_nlink','st_mtime_ns','st_ctime_ns');need(all(getattr(a,k)==getattr(z,k)==getattr(q,k) for k in fields),'stable current source FD')
 finally:os.close(fd)
 return dict(path=str(p),device=a.st_dev,inode=a.st_ino,uid=a.st_uid,gid=a.st_gid,mode=oct(stat.S_IMODE(a.st_mode)),size=n,nlink=a.st_nlink,mtime_ns=a.st_mtime_ns,ctime_ns=a.st_ctime_ns,sha256=h.hexdigest())
def validate_case_roles(b):
 c=checked3(b['complete_case']);s=checked3(c['stage_review']);t=checked3(c['typed_composition_review'])
 need(s['schema']=='mckernel.independent-selected205-two-complete-cycle-actual-stage-review.v1' and s['status']=='PASS' and s['decision']=='PASS_ACTUAL_SELECTED205_TWO_CYCLE_STAGE_PRESERVATION_ONLY','actual complete-cycle stage role')
 need(t['schema']=='mckernel.independent-selected205-two-complete-cycle-actual-mandatory-consumer-preparation-review.v1' and t['status']=='PASS' and t['decision']=='PASS_ACTUAL_SELECTED205_TWO_CYCLE_MANDATORY_CONSUMER_AND_PARENT_ONLY','actual mandatory-cycle consumer role')
 need(t['stage_review']==c['stage_review'] and s['native_manifest']==t['stage_native_manifest']==c['stage_native_manifest'] and t['native_manifest']==c['manifest'],'stage original versus normalized COPY joins')
 need(t['runtime_case']==c['runtime_case'] and t['runtime_source_hashes']==c['runtime_source_hashes'] and t['parent_identity']==c['parent_identity'] and t['nonce']==c['nonce'],'whole runtime/45source/parent identity joins')
 need(t['runtime_source_count']==c['runtime_source_count']==len(c['runtime_source_hashes'])==45,'complete current source closure')
 for key in ('fixed_cycles','logger_seconds'):need(c['runtime_case'][key]=={'fixed_cycles':2,'logger_seconds':120}[key],'two complete cycles/common120logger')
 for key,ck in [('owner_argv','launch_argv'),('inside_argv','inside_argv'),('create_argv','container_create_argv'),('qemu_argv','qemu_argv'),('AF_UNIX_endpoints','unix_paths')]:need(t[key]==c[ck],'whole tested invocation '+key)
 for key in ('runtime_owner','runtime_runner','runtime_observer','mandatory_cycle_oracle','original_cycle_oracle'):need(t[key]==c['source_refs'][key],'whole actual source descriptor '+key)
 need(full(t['runtime_owner']['path'])==t['runtime_owner'],'exact typed runtime owner full11 before import')
 need(full(t['mandatory_cycle_oracle']['path'])==t['mandatory_cycle_oracle'],'mandatory exact retained oracle full11')
 need(c['source_refs']['mandatory_cycle_oracle']['sha256']==c['source_refs']['original_cycle_oracle']['sha256'],'oracle original/COPY identical bytes')
 tupledata=checked3(c['selected_tuple_manifest']);need(c['selected_tuple_manifest']['sha256']=='0f80ec37d15488b3365573222ad6ff811d795fb54b95d375b192f10049cb97c5','frozen selected205 tuple manifest')
 need(c['module_descriptors']==tupledata['current_module_original_descriptors'] and c['retained_module_descriptors']==tupledata['current_module_retained_descriptors'] and c['sdk_artifact_review']==tupledata['component_sdk_artifact'] and c['sdk_abi_review']==tupledata['component_sdk_ABI'],'whole matched3 original/retained SDK authority')
 need(c['image']==s['unchanged_image'] and c['modules']==s['unchanged_modules'],'stage full unchanged image/modules')
 spec=importlib.util.spec_from_file_location('actual_complete_cycle_snapshot_owner',t['runtime_owner']['path']);owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
 nd,manifest=owner.bound_manifest(c['manifest']['path'],c['manifest']['sha256'])
 need(nd._case==c['runtime_case'] and manifest['artifacts']['mckernel_image']['sha256']=='ff4fca457e9ffe50dc4eca930c5f91faf317eeee15bf0c2907067cffa77b23bb' and manifest['pair']['host_cpus']==[1,2] and manifest['pair']['cpus']==[0,1],'actual selected205 two-CPU mandatory consumer')
 need(manifest['modules']==c['modules'] and owner.SOURCE_HASHES==c['runtime_source_hashes'],'actual whole current runtime source/module joins')
 need(c['latest_physical']==b['physical_review'] and c['runtime_release'] is False,'genuine latest predecessor/no draft runtime authority')
 return c,owner
def static_joins(b):
 for r in b['source_pins']:need(hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'],'frozen source')
 c,owner=validate_case_roles(b);meta=checked3(b['conditional_metadata']);proposal=checked3(meta['proposal']);pending=checked3(b['machine_pending'])
 need(meta['whole_case']==proposal['whole_case']==b['complete_case'],'whole current case in metadata/proposal')
 need(meta['parent_identity']==proposal['parent']['identity']==b['parent_identity']==pending['parent_identity'],'legacy live identity exact projection')
 need(meta['parent_full_stable_metadata']==proposal['parent']['full_authority']==c['parent_identity'],'whole actual parent descriptor retained')
 need(b['parent_identity']=={k:c['parent_identity'][k] for k in ('device','inode','uid','gid','mode')} and proposal['parent']['path']==c['parent_identity']['path'],'explicit accepted fivefield live API projection')
 need(pending['independent_static_execution_decision']==b['static_review'],'independent actual static review join');checked3(b['static_review'])
 expected=dict(cpuset=c['host_profile']['cpus'],cpus=c['host_profile']['CPU_count'],memory=c['host_profile']['memory_bytes'],memory_swap=c['host_profile']['memory_swap_bytes'],pids=c['host_profile']['pids_limit'],network=c['host_profile']['network'],mckernel_cpus=2)
 need(proposal['profile']==expected and expected==dict(cpuset='2-5',cpus=4,memory=12884901888,memory_swap=12884901888,pids=512,network='none',mckernel_cpus=2),'exact existing heavy profile/data projection')
 return proposal,owner
# Compile ONLY the literal accepted terminal function, changing its two old
# case identifiers to the genuine current three-round report contract. No
# physical/lease/owner/capture/mutex predicate is copied or relaxed.
tree=ast.parse(raw,str(ENGINE));function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='terminal_joins')
changes={'mckernel.independent-current-host-pair-205-two-rounds-physical-retirement.v1':'mckernel.independent-current-host-pair-205-three-rounds-physical-retirement.v1','PASS_SAMEBOOT_205_TWO_ROUNDS_SINGLE_OWNER_PHYSICAL_RETIREMENT_ONLY':'PASS_SAMEBOOT_205_THREE_ROUNDS_SINGLE_OWNER_PHYSICAL_RETIREMENT_ONLY'}
seen=[]
for node in ast.walk(function):
 if isinstance(node,ast.Constant) and type(node.value)is str and node.value in changes:seen.append(node.value);node.value=changes[node.value]
need(sorted(seen)==sorted(changes),'exact two source literal amendments')
exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(ENGINE),'exec'),base.__dict__)
base.static_joins=static_joins
globals().update({k:v for k,v in vars(base).items() if not k.startswith('__')})
if __name__=='__main__':raise SystemExit(base.main())
