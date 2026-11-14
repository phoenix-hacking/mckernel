from pathlib import Path
import json,os,stat,fcntl,subprocess,hashlib,time
T=Path('/home/holden/mckernel-work/host-preparation/native-kmsg-read-abi-20261018-1/target-preparation-1/proof-bound-target-preparation-1');S=Path('/home/holden/mckernel-work/scratch')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def node(p):
 s=p.stat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid)
review=Path('/home/holden/mckernel-work/host-preparation/native-kmsg-boundary-review-20261018-1/PROOF-BOUND-IHK-SOURCE-PROFILE-RESULT.json');assert sha(review)=='0ebfcb51e96d784c7ac646985fc2f3295004e9d140dd483ce9021e306ee9a854'
a=Path('/home/holden/mckernel-work/host-preparation/native-kmsg-boundary-review-20261018-1/ORDINARY-IHK-MATERIALIZATION-PHASE-BUDGET-AMENDMENT.json');assert sha(a)=='e2e4947b900e30781b20337fe6406ec6269c04056780a7f3439f14b2d938b0ec'
budget=json.loads(a.read_text())['ordinary_reserve'];plan=json.loads((T/'ROOT-MATERIALIZATION-PLAN.json').read_text());assert sha(T/'ROOT-MATERIALIZATION-PLAN.json')==json.loads(review.read_text())['materialization_plan']['sha256'];assert sha(T/'request.DRAFT.json')==plan['request_draft']['sha256'];q=json.loads((T/'request.DRAFT.json').read_text());assert q['candidate_identity'] is None and q['input_identity'] is None
lock=Path('/run/lock/mckernel-development.lock');s=lock.stat();assert (s.st_dev,s.st_ino,s.st_uid,s.st_gid)==(27,4,0,0)
fd=os.open(lock,os.O_RDONLY|os.O_NOFOLLOW);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==q['boot_id']=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
 m=json.loads(subprocess.check_output(['/usr/bin/findmnt','-J','-T',str(S),'-o','TARGET,UUID,MAJ:MIN,FSTYPE'],timeout=10))['filesystems'];assert m==[{'target':str(S),'uuid':'2a5768c8-718d-4914-bdc0-6b32c5a92a52','maj:min':'7:36','fstype':'ext4'}]
 st=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());assert st['phase']=='running' and st['stop_reason'] is None and st['last_rate_limits']['primary']['usedPercent']<97
 before={}
 for name,path,floor in [('host','/',16*2**30),('scratch',str(S),12*2**30)]:
  v=os.statvfs(path);n=v.f_bavail*v.f_frsize;assert n>=floor+budget['total_bytes'];before[name]={'available_bytes':n,'floor_bytes':floor,'phase_reserve_bytes':budget['total_bytes'],'margin_after_floor_reserve':n-floor-budget['total_bytes']}
 assert node(Path(q['basis_identity']['path']))==q['basis_identity']
 for p in [q['candidate_root'],q['input_root'],q['owner_evidence_root'],q['lease_path'],q['common_exclusion_path'],str(S/'mckernel-heavy-operation.lock'),str(S/('nsd-a-'+q['nonce'])),str(T/'request.json')]:assert not os.path.lexists(p),p
 pairs=[]
 for rel,row in plan['input_tree']['files'].items():pairs.append((Path(plan['input_tree']['source'])/rel,Path(plan['input_tree']['destination'])/rel,row))
 for row in plan['candidate_tree']['modules']:pairs.append((Path(plan['candidate_tree']['source'])/'modules'/row['path'],Path(plan['candidate_tree']['destination'])/'modules'/row['path'],row))
 assert len(pairs)==35
 contents=[]
 for src,dest,row in pairs:
  assert src.resolve(strict=True)==src and src.is_file() and not src.is_symlink();s=src.stat();b=src.read_bytes();assert src.stat()==s and len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'];contents.append((src,dest,row,b,stat.S_IMODE(s.st_mode)))
 assert sum(len(x[3]) for x in contents)==949466
 for k in ['input_tree','candidate_tree']:Path(plan[k]['destination']).mkdir(mode=0o700)
 for rel in plan['candidate_tree']['empty_directories']:(Path(plan['candidate_tree']['destination'])/rel).mkdir(mode=0o700)
 copied=[]
 with (T/'root-materialize-1.journal.jsonl').open('x') as journal:
  for src,dest,row,b,mode in contents:
   dest.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
   with dest.open('xb') as f:f.write(b);f.flush();os.fchmod(f.fileno(),mode);os.fsync(f.fileno())
   assert sha(dest)==row['sha256'] and dest.stat().st_nlink==1;copied.append({'path':str(dest),'bytes':len(b),'sha256':row['sha256']});journal.write(json.dumps(copied[-1])+'\n');journal.flush();os.fsync(journal.fileno())
 q['candidate_identity']=node(Path(q['candidate_root']));q['input_identity']=node(Path(q['input_root']))
 with (T/'request.json').open('x') as f:json.dump(q,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 after={name:os.statvfs(path).f_bavail*os.statvfs(path).f_frsize for name,path in [('host','/'),('scratch',str(S))]}
 with (T/'root-materialize-1.receipt.json').open('x') as f:json.dump({'status':'PASS_EXACT_ORDINARY_MATERIALIZATION_ONLY','files':35,'bytes':949466,'copied':copied,'before':before,'after_available_bytes':after,'candidate_identity':q['candidate_identity'],'input_identity':q['input_identity'],'request_sha256':sha(T/'request.json'),'boot_id':q['boot_id'],'development_mutex':[27,4],'sdk_copies':0,'compiler_runs':0,'heavy_build_authority':False,'heavy_phase_reserve_bytes':1207959552},f,indent=2);f.write('\n')
 print(json.dumps({'status':'PASS_EXACT_ORDINARY_MATERIALIZATION_ONLY','files':35,'bytes':949466,'request_sha256':sha(T/'request.json')}))
finally:fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
