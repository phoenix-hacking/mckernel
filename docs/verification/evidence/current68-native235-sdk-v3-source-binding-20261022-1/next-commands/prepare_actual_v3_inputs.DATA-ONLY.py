from pathlib import Path
import json,hashlib,os,uuid,datetime
R=Path('/home/holden/mckernel');S=Path('/home/holden/mckernel-work/scratch');H=Path('/home/holden/mckernel-work/host-preparation/native-running-modules-host-output');D=Path('/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1')
PREP=R/'docs/verification/evidence/current68-native235-v3-host-control-sdk-preparation-20261022-1.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def node(p):
 s=p.stat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=s.st_mode&511,uid=s.st_uid,gid=s.st_gid)
def save(p,v):
 raw=v if isinstance(v,bytes)else(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
 with p.open('xb')as f:os.fchmod(f.fileno(),0o600);f.write(raw)
assert os.getuid()==os.geteuid()==os.getgid()==os.getegid()==1000
raw=PREP.read_bytes();assert sha(raw)=='c10aa8e755d4900cc607b77951ac2ff2657224a6ee7a183c86bf099716097a44';prep=json.loads(raw)
assert prep['source_identity']=='b3f80c34011dca51674b0566ea08a2aff0e23f3e65e5f82b5a96b7dad47c924c' and prep['host_fork_adoption_opt_in']is True
module_data={}
for row in prep['closure']:
 n=row['path'];assert not Path(n).is_absolute()and '..'not in Path(n).parts and n not in module_data
 b=Path(row['origin']).read_bytes();assert len(b)==row['bytes']and sha(b)==row['sha256'];module_data[n]=b
assert len(module_data)==68 and sum(map(len,module_data.values()))==1353815
input_data={'preparation.json':raw}
for row in prep['references'].values():
 n=Path(row['retained_copy']).name;assert n not in input_data;b=Path(row['retained_copy']).read_bytes();assert len(b)==row['bytes']and sha(b)==row['sha256'];input_data[n]=b
assert len(input_data)==15 and sum(map(len,module_data.values()))+sum(map(len,input_data.values()))<4*2**20
backing=S.parent/'scratch.ext4';bs=backing.stat();assert bs.st_ino==47468427 and bs.st_uid==bs.st_gid==0 and bs.st_size==110*2**30 and bs.st_nlink==1
hostfree=os.statvfs('/home/holden');scratchfree=os.statvfs(S);gap=bs.st_size-bs.st_blocks*512
assert hostfree.f_bavail*hostfree.f_frsize>=16*2**30+679477248+gap+269488128+4009754624
assert scratchfree.f_bavail*scratchfree.f_frsize>=14091616256+4*2**20
assert node(H)==json.loads(Path('/home/holden/mckernel-work/host-preparation/m05-sdk68-canonical-host-output-request-20261022-1/actual-sdk-host-output-build-attempt-1/request.json').read_bytes())['output_parent_identity'] and not H.is_symlink();assert all(not p.is_symlink()for p in (H.parent,*H.parents))
nonce='bc3cf0ecfe164d6bbcad77dd3bae8e16';c=H/('native-running-modules-candidate-'+nonce);i=S/('native-running-modules-inputs-'+nonce);e=H/('native-running-modules-owner-'+nonce);attempt=D/'actual-sdk-v3-build-attempt-1'
assert all(not os.path.lexists(p)for p in (c,i,e,attempt))
os.umask(0o077);c.mkdir(mode=0o700);i.mkdir(mode=0o700);attempt.mkdir(mode=0o700)
for n in ('modules','home','tmp'):(c/n).mkdir(mode=0o700)
for n,b in module_data.items():
 p=c/'modules'/n;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);save(p,b)
for n,b in input_data.items():save(i/n,b)
v=json.loads((D/'REQUEST.PAYLOAD-TEMPLATE.json').read_bytes());v['preparation']=dict(path=str(PREP),sha256=sha(raw));v['driver']['sha256']='2f34764cc2740eb950013654e0eb5ae27978631a3038e9dccdce0a942979b76c';v.update(nonce=nonce,request_path=str(attempt/'request.json'),input_root=str(i),candidate_root=str(c),owner_evidence_root=str(e),lease_path=str(S/'native-running-external-modules.lease.json'),common_exclusion_path=str(S/'native-running-external-modules-operational-exclusion.json'),basis_identity=node(S/'mckernel-exact-candidate-scratch-22-authority3-output'),candidate_identity=node(c),input_identity=node(i),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),output_parent_identity=node(H),backing_identity=dict(node(backing),size=bs.st_size,nlink=bs.st_nlink))
save(attempt/'request.json',v);save(attempt/'materialization.json',dict(status='EXACT68_MODULES_AND15_INPUTS_MATERIALIZED_NO_BUILD',nonce=nonce,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),module_files=68,input_files=15,module_bytes=sum(map(len,module_data.values())),input_bytes=sum(map(len,input_data.values())),request=dict(path=v['request_path'],sha256=sha((attempt/'request.json').read_bytes())),backing_identity=v['backing_identity'],compiler_runs=0,root_operations=0));print(json.dumps(dict(request=v['request_path'],sha256=sha((attempt/'request.json').read_bytes()),nonce=nonce)))
