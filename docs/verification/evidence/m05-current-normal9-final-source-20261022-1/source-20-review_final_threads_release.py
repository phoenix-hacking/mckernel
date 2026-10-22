"""Finite final-data check only; never invokes root, owner, backend or guest."""
from pathlib import Path
import argparse,hashlib,json,math,os,stat,time
R=Path(__file__).resolve().parent
CONFIG=R/'FINAL-IHK-LOGGING-CHECK-CONFIG.json'
OUTPUT=R/'FINAL-205-MATCHED-SDK-NATIVE-MACHINE-REVIEW.json'
STABLE=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
SCHEMA='mckernel.current-ihk-logging.final-check-config.v1'
STATUS='PASS_NON_TEMPORAL_CURRENT_IHK_LOGGING_NATIVE_CHECK_CONFIG'

def need(ok,label):
 if not ok:raise ValueError(label)

def read(path,expected,maxbytes=2*1024**2,root=False):
 path=Path(path)
 need(path.is_absolute() and path.resolve()==path,'canonical input path')
 fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as stream:
  before=os.fstat(stream.fileno());need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=maxbytes,'bounded regular input')
  if root:need(before.st_uid==before.st_gid==0 and stat.S_IMODE(before.st_mode)==0o644,'root-owned readable snapshot')
  raw=stream.read(maxbytes+1);after=os.fstat(stream.fileno());named=path.lstat()
  need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in STABLE),'stable input FD and path')
 need(len(raw)==before.st_size and hashlib.sha256(raw).hexdigest()==expected,'exact whole input hash')
 return json.loads(raw),dict(path=str(path),sha256=expected,bytes=len(raw)),before

def fresh(snapshot):
 value=snapshot['time_epoch'];need(type(value) in (int,float) and math.isfinite(value),'snapshot epoch')
 age=time.time()-value;need(0<=age<=60,'genuine snapshot older than 60 seconds or future');return age

def main():
 ap=argparse.ArgumentParser(allow_abbrev=False)
 for name in ['config','machine','snapshot']:ap.add_argument('--'+name+'-sha256',required=True)
 a=ap.parse_args();need(os.getuid()==os.geteuid()==1000,'ordinary reviewer UID1000')
 for value in [a.config_sha256,a.machine_sha256,a.snapshot_sha256]:need(len(value)==64 and all(c in '0123456789abcdef' for c in value),'exact SHA256 argument')
 cfg,configref,_=read(CONFIG,a.config_sha256)
 need(cfg['schema']==SCHEMA and cfg['status']==STATUS,'approved fixed case config')
 need(not os.path.lexists(OUTPUT),'fresh final decision output')
 base,baseref,_=read(cfg['machine_base']['path'],cfg['machine_base']['sha256'])
 need(baseref==cfg['machine_base'] and base==cfg['machine_base_object'],'exact preclock physical/static base')
 need(base['runtime_release'] is False and base['fresh_live_preflight'] is None,'base has no premature runtime authority')
 snapshot,snapref,snapstat=read(cfg['snapshot_path'],a.snapshot_sha256,root=True)
 need(snapshot['status']=='PASS_LIVE_PREEXECUTION_SNAPSHOT','actual live snapshot PASS')
 fresh(snapshot)
 for key,value in cfg['snapshot_equal'].items():need(snapshot.get(key)==value,'snapshot static or predecessor join: '+key)
 for key in ['exclusive_heavy_accepted','root_mutex_snapshot_free','current_predecessor_container_absent']:need(snapshot.get(key) is True,'snapshot required live fact: '+key)
 usage=snapshot['included_usage_percent'];need(type(usage) in (int,float) and math.isfinite(usage) and 0<=usage<100,'included usage below current100percent')
 memory=snapshot['mem_available_bytes'];need(type(memory) is int and memory>=16*1024**3,'actual memory admission')
 floors={'/home/holden/mckernel':16*1024**3,'/home/holden/mckernel-work/scratch':12*1024**3}
 need(set(snapshot['capacity'])==set(floors),'two exact filesystem rows')
 for path,floor in floors.items():
  row=snapshot['capacity'][path]
  need(type(row['available_bytes']) is int and row['floor_bytes']==floor,'actual floor row')
  need(row['reserve_bytes']==679477248,'producer648MiB includes8MiB diagnostics')
  need(row['available_bytes']>=floor+679477248,'actual approved640MiB headroom')
 need(snapshot['released_paths_absent']==cfg['released_paths_absent'],'latest predecessor owned paths absent')
 need(type(snapshot['image_id']) is str and snapshot['image_id']==cfg['container_image_id'],'container image identity')
 machine,machref,_=read(cfg['machine_path'],a.machine_sha256)
 expected=dict(base,status='PASS_EXECUTION_RELEASE',runtime_release=True,fresh_live_preflight=snapref)
 need(machine==expected,'only three exact permitted late machine fields')
 need(type(machine['execution_count']) is int and machine['execution_count']==1 and machine['runtime_release'] is True,'one exact native invocation')
 parent=Path(cfg['parent']['path']);fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC|os.O_NOFOLLOW)
 with _directory(fd) as held:
  before=os.fstat(held);identity=dict(device=before.st_dev,inode=before.st_ino,uid=before.st_uid,gid=before.st_gid,mode=oct(stat.S_IMODE(before.st_mode)))
  need(identity==cfg['parent']['identity'] and not os.listdir(held),'current exact empty parent')
  after=os.fstat(held);named=parent.lstat();need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in STABLE),'stable current parent')
 for p in [cfg['attempt'],cfg['owner_evidence']]:need(not os.path.lexists(p),'fresh attempt and owner evidence')
 launch=cfg['launch_argv'];need(launch[0]=='/usr/bin/sudo' and launch[1]=='-A' and launch[2]=='/home/holden/anaconda3/bin/python3.9','exact pinned owner command')
 need(launch[launch.index('--owner-sha256')+1]==cfg['owner']['sha256'],'owner CLI pin')
 need(launch[launch.index('--manifest')+1]==cfg['manifest']['path'] and launch[launch.index('--manifest-sha256')+1]==cfg['manifest']['sha256'],'actual stage CLI pin')
 # Preclock config holds the actual source closure. Recheck the few runtime
 # source bytes only, never the full historical source/artifact authority.
 check_runtime_sources(cfg)
 age=fresh(snapshot)
 report=dict(schema='mckernel.independent-current-numa-exact-native-release-review.v1',
  status='PASS_EXACT_CURRENT_M05_SECOND_STOP_DIAGNOSTIC_NATIVE_RELEASE',
  decision='PASS_ONE_EXACT_CURRENT_M05_OWNER_AND_THREE_SUCCESS_ONLY_READBACKS',
  reviewer='current_numa_exact_bound_one_app_review',config=configref,machine_release=machref,execution_release=machref,
  snapshot=snapref,snapshot_age_seconds=age,expires_at_epoch=snapshot['time_epoch']+60,
  latest_physical=cfg['latest_physical'],module_authority=cfg['module_authority'],
  stage_acceptance=cfg['stage_acceptance'],actual_typed_composition=cfg['actual_typed_composition'],
  allowed_argv=launch,launch_argv=launch,owner_argv=launch,postjoin_readback=cfg['postjoin_readback'],
  execution_count=1,runtime_release=True,diagnostic_only=True,nonnull_FP_acceptance=False,
  application_acceptance=False,native_acceptance=False,guest_runs_observed=0,
  scope='Current053d image/sentinel33f launcher with accepted unchanged module tuple: exact M05 signal40B/empty/exit0 plus strict67 boot and second public-stop/resource protocol. No complete restoration, cycle or compute-C retirement credit.')
 raw=(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 fresh(snapshot)
 out=os.open(OUTPUT,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
 with os.fdopen(out,'wb') as f:os.fchmod(f.fileno(),0o600);f.write(raw);f.flush();os.fsync(f.fileno())
 print(json.dumps(dict(status=report['status'],path=str(OUTPUT),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),allowed_argv=launch,expires_at_epoch=report['expires_at_epoch']),sort_keys=True))
 return 0

class _directory:
 def __init__(self,fd):self.fd=fd
 def __enter__(self):return self.fd
 def __exit__(self,*args):os.close(self.fd)

def check_runtime_sources(cfg):
 rows=cfg['runtime_source_refs'];need(type(rows) is list,'mandatory runtime source rows')
 selected={row['path'] for row in rows if not row['path'].endswith('.json')}
 need('runtime_source_fd_identity_map' in cfg,'mandatory runtime source FD map descriptor')
 descriptor=cfg['runtime_source_fd_identity_map']
 need(type(descriptor) is dict and set(descriptor)=={'path','sha256','bytes'},'whole runtime source FD map descriptor')
 pinned,pinref,_=read(descriptor['path'],descriptor['sha256'])
 need(pinref==descriptor and pinned['schema']=='mckernel.current-native.selected-runtime-source-full-fd-identities.v1','exact runtime source FD map bytes/schema')
 identities=pinned['identities']
 need(type(identities) is dict and set(identities)==selected,'exact selected runtime source FD map set')
 for identity in identities.values():
  need(type(identity) is dict and set(identity)==set(STABLE) and all(type(identity[k]) is int for k in STABLE) and identity['st_nlink'] in (1,2),'complete exact selected source FD pin')
 for row in rows:
  _,actual,_=read(row['path'],row['sha256']) if row['path'].endswith('.json') else read_source(row,identities[row['path']])
  need(actual==row,'current runtime source bytes')
 return len(rows)

def read_source(row,expected_identity):
 path=Path(row['path']);need(path.resolve()==path,'canonical source')
 need(type(expected_identity) is dict and set(expected_identity)==set(STABLE) and all(type(expected_identity[k]) is int for k in STABLE) and expected_identity['st_nlink'] in (1,2),'mandatory complete exact source FD pin')
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 with os.fdopen(fd,'rb') as f:
  a=os.fstat(f.fileno());need(stat.S_ISREG(a.st_mode) and {k:getattr(a,k) for k in STABLE}==expected_identity,'exact selected source FD identity')
  raw=f.read(1024**2+1);b=os.fstat(f.fileno());c=path.lstat()
  need(all(getattr(a,k)==getattr(b,k)==getattr(c,k)==expected_identity[k] for k in STABLE),'stable runtime source and exact FD pin')
 need(len(raw)<=1024**2 and len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],'runtime source hash/bytes')
 return None,dict(path=str(path),sha256=row['sha256'],bytes=len(raw)),a

if __name__=='__main__':raise SystemExit(main())
